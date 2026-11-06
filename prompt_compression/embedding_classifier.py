"""Supervised sensitivity classifier: sentence embedding (all-MiniLM-L6-v2) + logistic-regression head.

Replaces the zero-shot NLI model as the "model" step of sensitivity.py. The zero-shot model's P("sensitive") did not
separate the classes (0.38-0.67 for sensitive prompts, up to 0.57 for chit-chat and company prose; see
reports/playground-ab/REPORT.md), so most ordinary prompts were kept verbatim and nothing was compressed.

  encoder  sentence-transformers/all-MiniLM-L6-v2 (22M parameters, 384-d), mean pooling + L2 normalisation, loaded
           with plain transformers (no sentence-transformers dependency), CPU float32
  head     logistic regression trained by eval/train_sensitivity_head.py; weights, threshold and training metrics
           are in models/sensitivity_head.json (a few kB, versioned with the code)

Long texts are cut into windows of `max_chunk_tokens` encoder tokens; the score is the maximum over windows, so one
sensitive sentence in a long document is enough.
"""

import json
import math
import threading
from pathlib import Path
from typing import Optional

HEAD_PATH = Path(__file__).resolve().parent / "models" / "sensitivity_head.json"
DEFAULT_ENCODER = "sentence-transformers/all-MiniLM-L6-v2"
_ENCODER_MAX = 256  # all-MiniLM-L6-v2 was trained on sequences of up to 256 word pieces


def load_head(path: Path = HEAD_PATH) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


class EmbeddingEncoder:
    def __init__(self, model_name: str = DEFAULT_ENCODER):
        self.model_name = model_name
        self._tokenizer = None
        self._model = None
        self._lock = threading.Lock()

    def load(self) -> None:
        if self._model is not None:
            return
        with self._lock:
            if self._model is not None:
                return
            import torch
            from transformers import AutoModel, AutoTokenizer

            self._tokenizer = AutoTokenizer.from_pretrained(self.model_name)
            model = AutoModel.from_pretrained(self.model_name, dtype=torch.float32) if _accepts_dtype() else \
                AutoModel.from_pretrained(self.model_name, torch_dtype=torch.float32)
            model.eval()
            self._model = model

    @property
    def tokenizer(self):
        return self._tokenizer

    def chunks(self, text: str, max_tokens: int) -> list[str]:
        budget = max(16, min(max_tokens, _ENCODER_MAX - 2))
        enc = self._tokenizer(text, add_special_tokens=False, return_offsets_mapping=True)
        ids = enc["input_ids"]
        if len(ids) <= budget:
            return [text]
        out = []
        for start in range(0, len(ids), budget):
            offsets = enc["offset_mapping"][start:start + budget]
            piece = text[offsets[0][0]:offsets[-1][1]]
            if piece.strip():
                out.append(piece)
        return out or [text]

    def encode(self, texts: list[str]) -> list[list[float]]:
        import torch

        with self._lock, torch.inference_mode():
            batch = self._tokenizer(texts, padding=True, truncation=True, max_length=_ENCODER_MAX, return_tensors="pt")
            hidden = self._model(**batch).last_hidden_state
            mask = batch["attention_mask"].unsqueeze(-1).to(hidden.dtype)
            pooled = (hidden * mask).sum(1) / mask.sum(1).clamp(min=1e-9)
            pooled = torch.nn.functional.normalize(pooled, p=2, dim=1)
        return pooled.tolist()


def _accepts_dtype() -> bool:
    """transformers >= 4.56 takes `dtype`; older versions only `torch_dtype`."""
    import transformers

    major, minor = (int(x) for x in transformers.__version__.split(".")[:2])
    return (major, minor) >= (4, 56)


class EmbeddingSensitivityClassifier:
    """P(sensitive) for a text: max over windows of sigmoid(w . embedding + b)."""

    def __init__(self, head: Optional[dict] = None, encoder: Optional[EmbeddingEncoder] = None):
        self.head = head or load_head()
        self.encoder = encoder or EmbeddingEncoder(self.head["encoder"])
        self._w = self.head["coef"]
        self._b = self.head["intercept"]

    @property
    def model_name(self) -> str:
        return f"{self.head['encoder']}+{self.head['name']}"

    @property
    def threshold(self) -> float:
        return float(self.head["threshold"])

    def load(self) -> None:
        self.encoder.load()

    def prob_from_embedding(self, vector: list[float]) -> float:
        z = self._b + sum(w * x for w, x in zip(self._w, vector))
        return 1.0 / (1.0 + math.exp(-z))

    def score(self, text: str, max_chunk_tokens: int = 200) -> tuple[float, int]:
        pieces = self.encoder.chunks(text, max_chunk_tokens)
        vectors = self.encoder.encode(pieces)
        return max(self.prob_from_embedding(v) for v in vectors), len(pieces)
