"""classify -> route -> compress over an OpenAI-style messages list.

Never touched: system/developer messages, tool and function results, assistant
messages that carry tool_calls/function_call, non-text content parts (images,
audio), and anything outside data["messages"] such as tool definitions. Roles
and order are kept; only the text of eligible messages changes.
"""

import copy
import logging
import time
from contextlib import nullcontext
from dataclasses import dataclass, field
from typing import Optional

import tiktoken

try:
    # Spans are no-ops unless the host process (e.g. the LiteLLM proxy with OTel) configures a provider.
    from opentelemetry import trace as _otel_trace

    _tracer = _otel_trace.get_tracer("prompt_compression")
except ImportError:  # OTel is optional for the pipeline itself
    _tracer = None

from prompt_compression.classifier import PromptClassifier, get_classifier
from prompt_compression.compressor_adapter import LLMLinguaCompressor
from prompt_compression.labels import most_restrictive
from prompt_compression import rules
from prompt_compression.router import build_routes
from prompt_compression.settings import PipelineSettings

logger = logging.getLogger("prompt_compression.pipeline")

PRESERVED_ROLES = frozenset({"system", "developer", "tool", "function"})
# Same encoding LLMLingua-2 reports origin/compressed tokens with (gpt-3.5-turbo).
_ENCODING = tiktoken.get_encoding("cl100k_base")


def count_tokens(text: str) -> int:
    return len(_ENCODING.encode(text)) if text else 0


def _span(name: str, attributes: dict):
    """Child span of whatever span is current; never carries message text."""
    if _tracer is None:
        return nullcontext()
    return _tracer.start_as_current_span(name, attributes=attributes)


def _set_attributes(span, attributes: dict) -> None:
    if span is not None and hasattr(span, "set_attributes"):
        span.set_attributes(attributes)


@dataclass
class PipelineReport:
    request_category: Optional[str] = None
    classifier_model: str = ""
    compression_model: str = ""
    tokens_before: int = 0
    tokens_after: int = 0
    elapsed_ms: float = 0.0
    messages: list = field(default_factory=list)

    @property
    def ratio(self) -> float:
        return round(self.tokens_before / self.tokens_after, 3) if self.tokens_after else 1.0

    def as_metadata(self) -> dict:
        return {
            "category": self.request_category,
            "classifier_model": self.classifier_model,
            "compression_model": self.compression_model,
            "tokens_before": self.tokens_before,
            "tokens_after": self.tokens_after,
            "compression_ratio": self.ratio,
            "elapsed_ms": self.elapsed_ms,
            "messages": self.messages,
        }


def _text_parts(message: dict) -> list[tuple[Optional[int], str]]:
    """(part index or None for a plain string, text) for every text segment."""
    content = message.get("content")
    if isinstance(content, str):
        return [(None, content)]
    if isinstance(content, list):
        return [
            (i, part.get("text", ""))
            for i, part in enumerate(content)
            if isinstance(part, dict) and part.get("type") == "text" and isinstance(part.get("text"), str)
        ]
    return []


def _set_text(message: dict, part_index: Optional[int], text: str) -> None:
    if part_index is None:
        message["content"] = text
    else:
        message["content"][part_index]["text"] = text


def _all_text_tokens(messages: list) -> int:
    return sum(count_tokens(text) for message in messages for _, text in _text_parts(message))


class PromptPipeline:
    def __init__(
        self,
        settings: Optional[PipelineSettings] = None,
        classifier: Optional[PromptClassifier] = None,
        compressor: Optional[LLMLinguaCompressor] = None,
    ):
        self.settings = settings or PipelineSettings.from_env()
        self.classifier = classifier or get_classifier()
        self.compressor = compressor or LLMLinguaCompressor(self.settings.compression_model)
        self.routes = build_routes(self.settings)

    def load(self) -> None:
        self.classifier.load()
        self.compressor.load()

    def process(self, messages: list) -> tuple[list, PipelineReport]:
        started = time.perf_counter()
        new_messages = copy.deepcopy(messages)
        report = PipelineReport(
            classifier_model=self.classifier.model_name, compression_model=self.compressor.model_name
        )
        report.tokens_before = _all_text_tokens(messages)

        last_user_index = max((i for i, m in enumerate(messages) if m.get("role") == "user"), default=None)
        categories = []

        for index, message in enumerate(new_messages):
            role = message.get("role")
            entry = {"index": index, "role": role}
            if role in PRESERVED_ROLES or message.get("tool_calls") or message.get("function_call"):
                entry["action"] = "preserved_role"
                report.messages.append(entry)
                continue
            parts = _text_parts(message)
            if not parts:
                entry["action"] = "no_text"
                report.messages.append(entry)
                continue

            text = "\n".join(part_text for _, part_text in parts)
            with _span("prompt.classify", {"prompt.message.index": index, "prompt.message.role": role or ""}) as span:
                result = self.classifier.classify(text)
                _set_attributes(span, {
                    "prompt.classifier.label": result.label,
                    "prompt.classifier.score": result.score,
                    "prompt.classifier.source": result.source,
                    "prompt.classifier.model": result.model_name,
                    "prompt.classifier.rule_hits": list(result.rule_hits),
                    "prompt.classifier.chunks": result.chunks,
                    "prompt.classifier.cache_hit": result.cache_hit,
                    **{f"prompt.classifier.scores.{label}": score for label, score in result.scores.items()},
                })
            route = self.routes[result.label]
            with _span("prompt.route", {
                "prompt.route.label": route.label,
                "prompt.route.compress": route.compress,
                "prompt.route.rate": route.rate,
                "prompt.route.redact": route.redact,
            }):
                pass
            categories.append(result.label)
            entry.update(
                {
                    "category": result.label,
                    "score": result.score,
                    "scores": dict(result.scores),
                    "source": result.source,
                    "rule_hits": list(result.rule_hits),
                    "classify_ms": result.elapsed_ms,
                    "chunks": result.chunks,
                    "cache_hit": result.cache_hit,
                }
            )

            actions = []
            redactions = 0
            compress_ms = 0.0
            for part_index, part_text in parts:
                new_text = part_text
                if route.redact:
                    new_text, redacted_rules, count = rules.redact_with_count(new_text)
                    redactions += count
                    if redacted_rules:
                        actions.append("redacted")
                if route.compress:
                    if index == last_user_index and self.settings.preserve_last_user:
                        actions.append("preserved_last_user")
                    elif len(new_text) < self.settings.min_chars:
                        actions.append("below_min_chars")
                    else:
                        with _span("prompt.compress", {"prompt.route.label": route.label, "prompt.route.rate": route.rate}) as span:
                            compress_started = time.perf_counter()
                            output = self.compressor.compress(new_text, route)
                            compress_ms += (time.perf_counter() - compress_started) * 1000
                            _set_attributes(span, {
                                "prompt.tokens.before": output.origin_tokens,
                                "prompt.tokens.after": output.compressed_tokens,
                            })
                        if output.text.strip():
                            new_text = output.text
                            actions.append("compressed")
                if new_text != part_text:
                    _set_text(message, part_index, new_text)

            entry["redactions"] = redactions
            entry["compress_ms"] = round(compress_ms, 1)
            entry["tokens_before"] = count_tokens(text)
            entry["tokens_after"] = sum(count_tokens(t) for _, t in _text_parts(message))
            entry["action"] = "+".join(dict.fromkeys(actions)) or "unchanged"
            report.messages.append(entry)

        report.request_category = most_restrictive(categories) if categories else None
        report.tokens_after = _all_text_tokens(new_messages)
        report.elapsed_ms = round((time.perf_counter() - started) * 1000, 1)
        return new_messages, report
