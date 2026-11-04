"""Zero-shot prompt classifier: rules first, then an NLI model, with safe fallbacks.

Order of decisions for one text:
  1. rules.py hit                      -> sensitive (model is not called)
  2. model top score < min_confidence  -> critical (never lossy-compress on doubt)
  3. inference error                   -> critical
  4. otherwise                         -> model's top label
Long texts are split into token chunks; the most restrictive chunk label wins.
If the model cannot be loaded at all, classify() raises ClassifierUnavailable
so the caller's fail mode (open/closed) decides what happens to the request.
"""

import asyncio
import hashlib
import logging
import threading
import time
from collections import OrderedDict
from dataclasses import dataclass, field, replace
from typing import Optional

from prompt_compression import rules
from prompt_compression.labels import CRITICAL, LABEL_FORMATS, LESS_IMPORTANT, PRIORITY, SENSITIVE
from prompt_compression.settings import ClassifierSettings

logger = logging.getLogger("prompt_compression.classifier")

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

    zero_shot = pipeline("zero-shot-classification", model=model_name, device=-1, dtype=torch.float32)
    if quantize == "int8":
        from torch.ao.quantization import quantize_dynamic

        zero_shot.model = quantize_dynamic(zero_shot.model, {torch.nn.Linear}, dtype=torch.qint8)
    elif quantize != "none":
        raise ValueError("CLASSIFIER_QUANTIZE must be 'none' or 'int8'")
    return zero_shot


@dataclass(frozen=True)
class ClassificationResult:
    label: str
    score: float
    # "rules" | "model" | "fallback_low_confidence" | "fallback_error" | "empty"
    source: str
    model_name: str
    scores: dict = field(default_factory=dict)
    rule_hits: tuple = ()
    chunks: int = 0
    elapsed_ms: float = 0.0
    # Observability only: True when the result came from the LRU cache.
    cache_hit: bool = False


class PromptClassifier:
    def __init__(self, settings: Optional[ClassifierSettings] = None):
        self.settings = settings or ClassifierSettings.from_env()
        if self.settings.label_format not in LABEL_FORMATS:
            raise ValueError(f"CLASSIFIER_LABEL_FORMAT must be one of {sorted(LABEL_FORMATS)}")
        label_texts, self._template = LABEL_FORMATS[self.settings.label_format]
        self._candidate_labels = list(label_texts.values())
        self._text_to_label = {text: label for label, text in label_texts.items()}

        self._pipeline = None
        self._load_error: Optional[BaseException] = None
        self._load_lock = threading.Lock()
        self._infer_lock = threading.Lock()
        self._cache: OrderedDict = OrderedDict()
        self._cache_lock = threading.Lock()

    @property
    def model_name(self) -> str:
        suffix = f"@{self.settings.quantize}" if self.settings.quantize != "none" else ""
        return self.settings.model + suffix

    @property
    def loaded(self) -> bool:
        return self._pipeline is not None

    def load(self) -> None:
        """Load the model once. A failure is remembered; restart the process to retry."""
        if self._pipeline is not None:
            return
        with self._load_lock:
            if self._pipeline is not None:
                return
            if self._load_error is not None:
                raise ClassifierUnavailable(str(self._load_error)) from self._load_error
            started = time.perf_counter()
            try:
                self._pipeline = load_zero_shot_pipeline(self.settings.model, self.settings.quantize)
            except Exception as exc:
                self._load_error = exc
                logger.warning("classifier model failed to load: model=%s error=%s", self.settings.model, type(exc).__name__)
                raise ClassifierUnavailable(str(exc)) from exc
            logger.info(
                "classifier model loaded: model=%s seconds=%.1f", self.settings.model, time.perf_counter() - started
            )

    def cache_clear(self) -> None:
        with self._cache_lock:
            self._cache.clear()

    def _cache_key(self, text: str) -> str:
        digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
        return f"{self.model_name}|{self.settings.label_format}|{digest}"

    def _cache_get(self, key: str) -> Optional[ClassificationResult]:
        with self._cache_lock:
            result = self._cache.get(key)
            if result is not None:
                self._cache.move_to_end(key)
            return result

    def _cache_put(self, key: str, result: ClassificationResult) -> None:
        if self.settings.cache_size <= 0:
            return
        with self._cache_lock:
            self._cache[key] = result
            self._cache.move_to_end(key)
            while len(self._cache) > self.settings.cache_size:
                self._cache.popitem(last=False)

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
        with self._infer_lock:
            # One forward pass scores all label hypotheses of a chunk together.
            outputs = self._pipeline(
                pieces,
                candidate_labels=self._candidate_labels,
                hypothesis_template=self._template,
                batch_size=len(self._candidate_labels),
            )
        return outputs if isinstance(outputs, list) else [outputs]

    def classify(self, text: str) -> ClassificationResult:
        started = time.perf_counter()
        if not text or not text.strip():
            return ClassificationResult(LESS_IMPORTANT, 1.0, "empty", self.model_name)

        key = self._cache_key(text)
        cached = self._cache_get(key)
        if cached is not None:
            return replace(cached, cache_hit=True)

        hits = rules.rule_hits(text)
        if hits:
            result = ClassificationResult(
                SENSITIVE, 1.0, "rules", self.model_name, rule_hits=tuple(hits),
                elapsed_ms=round((time.perf_counter() - started) * 1000, 1),
            )
            self._cache_put(key, result)
            return result

        self.load()
        try:
            pieces = self.chunk(text)
            outputs = self._infer(pieces)
        except Exception as exc:
            # Not cached: a transient failure should not pin the prompt to critical forever.
            logger.warning("classifier inference failed, falling back to critical: error=%s", type(exc).__name__)
            return ClassificationResult(
                CRITICAL, 0.0, "fallback_error", self.model_name,
                elapsed_ms=round((time.perf_counter() - started) * 1000, 1),
            )

        chunk_results = []
        for output in outputs:
            scores = {self._text_to_label[lbl]: round(float(s), 4) for lbl, s in zip(output["labels"], output["scores"])}
            top_label = self._text_to_label[output["labels"][0]]
            top_score = float(output["scores"][0])
            if top_score < self.settings.min_confidence:
                chunk_results.append((CRITICAL, top_score, "fallback_low_confidence", scores))
            else:
                chunk_results.append((top_label, top_score, "model", scores))

        label, score, source, scores = min(chunk_results, key=lambda item: PRIORITY[item[0]])
        result = ClassificationResult(
            label, round(score, 4), source, self.model_name, scores=scores, chunks=len(pieces),
            elapsed_ms=round((time.perf_counter() - started) * 1000, 1),
        )
        self._cache_put(key, result)
        return result

    async def aclassify(self, text: str) -> ClassificationResult:
        return await asyncio.to_thread(self.classify, text)


_instance: Optional[PromptClassifier] = None
_instance_lock = threading.Lock()


def get_classifier() -> PromptClassifier:
    """Process-wide classifier, built from the environment on first use."""
    global _instance
    with _instance_lock:
        if _instance is None:
            _instance = PromptClassifier()
        return _instance
