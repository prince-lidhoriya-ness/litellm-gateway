"""Sensitivity check: is this text personal data, credentials, health, financial or private legal information?

This is the "sensitivity" half of the pipeline's "Segment and classify" stage (the other half is segmenter.py, which says
what kind of text a block is). Sensitive text goes to "Keep verbatim"; nothing else about its importance matters, so the
earlier four-way importance labels (critical, non_sensitive, less_important) no longer take part in any decision.

Order of decisions for one text:
  1. rules.py hit (identifiers, keys, cards ...) -> sensitive (the model is not called)
  2. topics.py hit (health, money, legal, ...)   -> sensitive, reported as rule hit "topic_<name>"
  3. model probability >= threshold (the maximum over the text's chunks) -> sensitive
  4. inference error                           -> sensitive (not cached, so a transient failure is retried)
  5. otherwise                                 -> not sensitive
If the model cannot be loaded at all, check() raises ClassifierUnavailable so the caller's fail mode (open/closed)
decides what happens to the request.

The model (step 3) depends on SENSITIVITY_BACKEND:
  embedding (default)  all-MiniLM-L6-v2 sentence embedding + a logistic-regression head trained on labelled prompts
                       (embedding_classifier.py, eval/train_sensitivity_head.py). Held out: test recall 0.973 at a
                       false-positive rate of 0.072; a fresh 100-prompt holdout 1.0 / 0.083; company prose 0.0.
  nli                  the earlier zero-shot NLI model, a softmax over four candidate labels (labels.py). Its
                       P("sensitive") does not separate the classes: at 0.35 it reached 0.97 recall only by flagging
                       about two thirds of ordinary prompts (and 0.79 of company prose), so almost nothing was
                       compressed. Kept for comparison and rollback.
Results: eval/results/sensitivity_head.md and reports/playground-ab/REPORT.md.
"""

import hashlib
import logging
import threading
import time
from collections import OrderedDict
from dataclasses import dataclass, replace
from typing import Optional

from prompt_compression import deadline as deadlines
from prompt_compression import rules
from prompt_compression.labels import LABEL_FORMATS, SENSITIVE
from prompt_compression.settings import NLI_DEFAULT_THRESHOLD, SensitivitySettings
from prompt_compression.topics import topic_hits


def deterministic_hits(text: str) -> list[str]:
    """rules.py hits, then topics.py hits as "topic_<name>": everything decided without a model."""
    if not text or not text.strip():
        return []
    return list(rules.rule_hits(text)) + [f"topic_{name}" for name in topic_hits(text)]

logger = logging.getLogger("prompt_compression.sensitivity")

SENSITIVE_CATEGORY = "sensitive"
GENERAL_CATEGORY = "general"

# NLI models are trained on <=512-token pairs; some tokenizers report a huge sentinel instead.
MAX_MODEL_TOKENS = 512


class ClassifierUnavailable(RuntimeError):
    """The NLI model could not be loaded."""


def load_zero_shot_pipeline(model_name: str, quantize: str = "none"):
    """CPU zero-shot pipeline in float32, optionally with int8 dynamic quantization of Linear layers.

    transformers 5 keeps the checkpoint dtype by default and several DeBERTa-v3
    NLI checkpoints ship fp16 weights, which run roughly 10x slower on CPU.
    """
    import torch
    from transformers import pipeline

    zero_shot = pipeline(
        "zero-shot-classification", model=model_name, device=-1, dtype=torch.float32, trust_remote_code=False
    )
    if quantize == "int8":
        from torch.ao.quantization import quantize_dynamic

        zero_shot.model = quantize_dynamic(zero_shot.model, {torch.nn.Linear}, dtype=torch.qint8)
    elif quantize != "none":
        raise ValueError("CLASSIFIER_QUANTIZE must be 'none' or 'int8'")
    return zero_shot


@dataclass(frozen=True)
class Sensitivity:
    sensitive: bool
    # P(sensitive) from the model; 1.0 for a rules hit; 0.0 when the model was not asked.
    score: float
    # "rules" | "model" | "error" | "empty" | "none" (rules only, no hit)
    source: str
    model_name: str = ""
    rule_hits: tuple = ()
    chunks: int = 0
    elapsed_ms: float = 0.0
    # Observability only: True when the result came from the LRU cache.
    cache_hit: bool = False


class SensitivityDetector:
    def __init__(self, settings: Optional[SensitivitySettings] = None):
        self.settings = settings or SensitivitySettings.from_env()
        if self.settings.label_format not in LABEL_FORMATS:
            raise ValueError(f"CLASSIFIER_LABEL_FORMAT must be one of {sorted(LABEL_FORMATS)}")
        label_texts, self._template = LABEL_FORMATS[self.settings.label_format]
        self._candidate_labels = list(label_texts.values())
        self._text_to_label = {text: label for label, text in label_texts.items()}

        self._pipeline = None
        self._classifier = None
        if self.settings.backend == "embedding":
            from prompt_compression.embedding_classifier import EmbeddingSensitivityClassifier

            # Reads the head JSON; the encoder loads in load().
            self._classifier = EmbeddingSensitivityClassifier(
                revision=self.settings.encoder_revision, batch_size=self.settings.batch_size
            )
            default_threshold = self._classifier.threshold
        else:
            default_threshold = NLI_DEFAULT_THRESHOLD
        self.threshold = self.settings.threshold if self.settings.threshold is not None else default_threshold
        self._load_error: Optional[BaseException] = None
        self._load_lock = threading.Lock()
        self._infer_lock = threading.Lock()
        self._cache: OrderedDict = OrderedDict()
        self._cache_lock = threading.Lock()

    @property
    def model_name(self) -> str:
        if self._classifier is not None:
            return self._classifier.model_name
        suffix = f"@{self.settings.quantize}" if self.settings.quantize != "none" else ""
        return self.settings.model + suffix

    @property
    def loaded(self) -> bool:
        return self._model_ready

    @property
    def _model_ready(self) -> bool:
        if self._classifier is not None:
            return self._classifier.encoder._model is not None
        return self._pipeline is not None

    def load(self) -> None:
        """Load the model once. A failure is remembered; restart the process to retry."""
        if self._model_ready:
            return
        with self._load_lock:
            if self._model_ready:
                return
            if self._load_error is not None:
                raise ClassifierUnavailable(str(self._load_error)) from self._load_error
            started = time.perf_counter()
            try:
                if self._classifier is not None:
                    self._classifier.load()
                else:
                    self._pipeline = load_zero_shot_pipeline(self.settings.model, self.settings.quantize)
            except Exception as exc:
                self._load_error = exc
                logger.warning("sensitivity model failed to load: model=%s error=%s", self.model_name, type(exc).__name__)
                raise ClassifierUnavailable(str(exc)) from exc
            logger.info("sensitivity model loaded: model=%s seconds=%.1f", self.model_name, time.perf_counter() - started)

    # ---- cache ---------------------------------------------------------------------------------------------

    def cache_clear(self) -> None:
        with self._cache_lock:
            self._cache.clear()

    def _cache_key(self, text: str) -> str:
        digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
        return f"{self.model_name}|{self.settings.label_format}|{self.threshold}|{digest}"

    def _cache_get(self, key: str) -> Optional[Sensitivity]:
        with self._cache_lock:
            result = self._cache.get(key)
            if result is not None:
                self._cache.move_to_end(key)
            return result

    def _cache_put(self, key: str, result: Sensitivity) -> None:
        if self.settings.cache_size <= 0:
            return
        with self._cache_lock:
            self._cache[key] = result
            self._cache.move_to_end(key)
            while len(self._cache) > self.settings.cache_size:
                self._cache.popitem(last=False)

    # ---- model ---------------------------------------------------------------------------------------------

    def chunk(self, text: str) -> list[str]:
        """Split text into pieces that fit the model window, on token boundaries."""
        tokenizer = self._pipeline.tokenizer
        model_max = getattr(tokenizer, "model_max_length", MAX_MODEL_TOKENS) or MAX_MODEL_TOKENS
        budget = max(16, min(self.settings.max_chunk_tokens, min(model_max, MAX_MODEL_TOKENS) - 64))
        encoding = tokenizer(text, add_special_tokens=False, return_offsets_mapping=tokenizer.is_fast)
        input_ids = encoding["input_ids"]
        if len(input_ids) <= budget:
            return [text]
        pieces = []
        for start in range(0, len(input_ids), budget):
            window = slice(start, start + budget)
            if tokenizer.is_fast:
                offsets = encoding["offset_mapping"][window]
                piece = text[offsets[0][0] : offsets[-1][1]]
            else:
                piece = tokenizer.decode(input_ids[window])
            if piece.strip():
                pieces.append(piece)
        return pieces or [text]

    def _infer(self, pieces: list[str]) -> list[dict]:
        with deadlines.acquire(self._infer_lock, "classifier"):
            # One forward pass scores all label hypotheses of a chunk together.
            outputs = self._pipeline(
                pieces,
                candidate_labels=self._candidate_labels,
                hypothesis_template=self._template,
                batch_size=len(self._candidate_labels),
            )
        return outputs if isinstance(outputs, list) else [outputs]

    # ---- public --------------------------------------------------------------------------------------------

    def rules_only(self, text: str) -> Sensitivity:
        """Deterministic rules, no model: used for blocks that stay verbatim anyway (code, data, identifiers)."""
        hits = deterministic_hits(text)
        if hits:
            return Sensitivity(True, 1.0, "rules", self.model_name, rule_hits=tuple(hits))
        return Sensitivity(False, 0.0, "none", self.model_name)

    def check(self, text: str) -> Sensitivity:
        started = time.perf_counter()
        if not text or not text.strip():
            return Sensitivity(False, 0.0, "empty", self.model_name)

        key = self._cache_key(text)
        cached = self._cache_get(key)
        if cached is not None:
            return replace(cached, cache_hit=True)

        hits = deterministic_hits(text)
        if hits:
            result = Sensitivity(
                True, 1.0, "rules", self.model_name, rule_hits=tuple(hits),
                elapsed_ms=round((time.perf_counter() - started) * 1000, 1),
            )
            self._cache_put(key, result)
            return result

        self.load()
        try:
            if self._classifier is not None:
                with deadlines.acquire(self._infer_lock, "classifier"):
                    top, chunks = self._classifier.score(text, self.settings.max_chunk_tokens)
            else:
                pieces = self.chunk(text)
                outputs = self._infer(pieces)
        except deadlines.DeadlineExceeded:
            raise                     # the request is out of time: the hook's fail mode decides, not "sensitive"
        except Exception as exc:
            # Not cached: a transient failure should not pin the text to "sensitive" forever.
            logger.warning("sensitivity inference failed, treating the text as sensitive: error=%s", type(exc).__name__)
            return Sensitivity(
                True, 1.0, "error", self.model_name, elapsed_ms=round((time.perf_counter() - started) * 1000, 1)
            )

        if self._classifier is None:
            top = 0.0
            for output in outputs:
                scores = {self._text_to_label[lbl]: float(s) for lbl, s in zip(output["labels"], output["scores"])}
                top = max(top, scores.get(SENSITIVE, 0.0))
            chunks = len(pieces)
        result = Sensitivity(
            top >= self.threshold, round(top, 4), "model", self.model_name, chunks=chunks,
            elapsed_ms=round((time.perf_counter() - started) * 1000, 1),
        )
        self._cache_put(key, result)
        return result

    def check_many(self, texts: list[str]) -> list[Sensitivity]:
        """check() for several texts; with the embedding backend the model scores all uncached ones in one batch.
        Each result's elapsed_ms is its share of the batch time, so summing them gives the time spent."""
        if self._classifier is None:
            return [self.check(text) for text in texts]
        started = time.perf_counter()
        results: list = [None] * len(texts)
        todo = []
        for i, text in enumerate(texts):
            if not text or not text.strip():
                results[i] = Sensitivity(False, 0.0, "empty", self.model_name)
                continue
            key = self._cache_key(text)
            cached = self._cache_get(key)
            if cached is not None:
                results[i] = replace(cached, cache_hit=True)
                continue
            hits = deterministic_hits(text)
            if hits:
                results[i] = Sensitivity(True, 1.0, "rules", self.model_name, rule_hits=tuple(hits))
                self._cache_put(key, results[i])
                continue
            todo.append((i, key))
        if todo:
            self.load()
            try:
                with deadlines.acquire(self._infer_lock, "classifier"):
                    scored = self._classifier.score_many([texts[i] for i, _ in todo], self.settings.max_chunk_tokens)
            except deadlines.DeadlineExceeded:
                raise
            except Exception as exc:
                logger.warning("sensitivity inference failed, treating the text as sensitive: error=%s", type(exc).__name__)
                scored = None
            share = round((time.perf_counter() - started) * 1000 / len(todo), 1)
            for n, (i, key) in enumerate(todo):
                if scored is None:
                    results[i] = Sensitivity(True, 1.0, "error", self.model_name, elapsed_ms=share)
                    continue
                top, chunks = scored[n]
                results[i] = Sensitivity(top >= self.threshold, round(top, 4), "model", self.model_name, chunks=chunks,
                                         elapsed_ms=share)
                self._cache_put(key, results[i])
        return results


_instance: Optional[SensitivityDetector] = None
_instance_lock = threading.Lock()


def get_detector() -> SensitivityDetector:
    """Process-wide detector, built from the environment on first use."""
    global _instance
    with _instance_lock:
        if _instance is None:
            _instance = SensitivityDetector()
        return _instance
