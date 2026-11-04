"""Test doubles for the transformers pipeline, the classifier and LLMLingua."""

import re

from prompt_compression.classifier import ClassificationResult, ClassifierUnavailable
from prompt_compression.compressor_adapter import CompressionOutput
from prompt_compression.pipeline import count_tokens


class FakeTokenizer:
    """Whitespace tokenizer with offsets, shaped like a fast HF tokenizer."""

    is_fast = True
    model_max_length = 512

    def __call__(self, text, add_special_tokens=False, return_offsets_mapping=False):
        spans = [m.span() for m in re.finditer(r"\S+", text)]
        encoding = {"input_ids": list(range(len(spans)))}
        if return_offsets_mapping:
            encoding["offset_mapping"] = spans
        return encoding


class FakeZeroShotPipeline:
    """Picks the label whose candidate text is mapped by `keyword_to_label`, else a flat distribution."""

    def __init__(self, keyword_scores, default_scores, raise_on=None):
        self.tokenizer = FakeTokenizer()
        self.keyword_scores = keyword_scores
        self.default_scores = default_scores
        self.raise_on = raise_on
        self.calls = []

    def __call__(self, sequences, candidate_labels, hypothesis_template, **kwargs):
        self.calls.append(list(sequences))
        outputs = []
        for sequence in sequences:
            if self.raise_on and self.raise_on in sequence:
                raise RuntimeError("boom")
            scores = self.default_scores
            for keyword, keyword_scores in self.keyword_scores.items():
                if keyword in sequence:
                    scores = keyword_scores
                    break
            ranked = sorted(zip(candidate_labels, scores), key=lambda item: -item[1])
            outputs.append({"sequence": sequence, "labels": [l for l, _ in ranked], "scores": [s for _, s in ranked]})
        return outputs


class StubClassifier:
    """Classifier double: label chosen by keyword in the text."""

    model_name = "stub-classifier"

    def __init__(self, keyword_labels, default="non_sensitive", unavailable=False):
        self.keyword_labels = keyword_labels
        self.default = default
        self.unavailable = unavailable

    def load(self):
        if self.unavailable:
            raise ClassifierUnavailable("stub cannot load")

    def classify(self, text):
        if self.unavailable:
            raise ClassifierUnavailable("stub cannot load")
        for keyword, label in self.keyword_labels.items():
            if keyword in text:
                return ClassificationResult(label, 0.9, "model", self.model_name)
        return ClassificationResult(self.default, 0.9, "model", self.model_name)


class StubCompressor:
    """Keeps every other word, which is enough to see that compression happened."""

    model_name = "stub-compressor"

    def __init__(self):
        self.calls = []

    def load(self):
        pass

    def compress(self, text, route):
        self.calls.append((text, route.label, route.rate))
        words = text.split()
        kept = " ".join(words[::2])
        return CompressionOutput(kept, count_tokens(text), count_tokens(kept))
