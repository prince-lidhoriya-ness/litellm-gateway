"""Test doubles for the transformers pipeline, the sensitivity detector and LLMLingua."""

import re

from prompt_compression import rules
from prompt_compression.compressor_adapter import CompressionOutput
from prompt_compression.sensitivity import ClassifierUnavailable, Sensitivity
from prompt_compression.texts import count_tokens


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
    """Scores the four candidate labels (descriptive order: sensitive, critical, non_sensitive, less_important).

    `keyword_scores` maps a keyword to the score list used when the keyword is in the text, else `default_scores`."""

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


class StubDetector:
    """Sensitivity detector double: the real rules, plus a keyword list standing in for the NLI model."""

    model_name = "stub-detector"

    def __init__(self, sensitive_keywords=(), unavailable=False):
        self.sensitive_keywords = tuple(sensitive_keywords)
        self.unavailable = unavailable
        self.checked = []          # texts sent to check(): what the "model" was asked about

    def load(self):
        if self.unavailable:
            raise ClassifierUnavailable("stub cannot load")

    def rules_only(self, text):
        hits = tuple(rules.rule_hits(text)) if text and text.strip() else ()
        if hits:
            return Sensitivity(True, 1.0, "rules", self.model_name, rule_hits=hits)
        return Sensitivity(False, 0.0, "none", self.model_name)

    def check(self, text):
        if self.unavailable:
            raise ClassifierUnavailable("stub cannot load")
        self.checked.append(text)
        hits = tuple(rules.rule_hits(text))
        if hits:
            return Sensitivity(True, 1.0, "rules", self.model_name, rule_hits=hits)
        if any(keyword in text for keyword in self.sensitive_keywords):
            return Sensitivity(True, 0.9, "model", self.model_name, chunks=1)
        return Sensitivity(False, 0.1, "model", self.model_name, chunks=1)


class RateStubCompressor:
    """Keeps the fraction `rate` of the words, evenly spread: a lighter rate compresses less."""

    model_name = "rate-stub-compressor"

    def __init__(self, floor=None):
        self.calls = []
        # Never keep a smaller share than `floor`, whatever the rate (simulates a compressor that over-compresses).
        self.floor = floor

    def load(self):
        pass

    def compress(self, text, rate):
        self.calls.append((text, rate))
        words = text.split()
        share = rate if self.floor is None else min(rate, self.floor)
        keep = max(1, round(len(words) * share))
        step = len(words) / keep
        kept = " ".join(words[int(i * step)] for i in range(keep))
        return CompressionOutput(kept, count_tokens(text), count_tokens(kept))


class StubCompressor:
    """Keeps every other word, which is enough to see that compression happened."""

    model_name = "stub-compressor"

    def __init__(self):
        self.calls = []

    def load(self):
        pass

    def compress(self, text, rate):
        self.calls.append((text, rate))
        words = text.split()
        kept = " ".join(words[::2])
        return CompressionOutput(kept, count_tokens(text), count_tokens(kept))
