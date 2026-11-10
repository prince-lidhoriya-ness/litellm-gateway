"""Token estimation for budgeting.

Counts use tiktoken cl100k_base (prompt_compression.texts.count_tokens), the encoding the compression stage reports
with. That is exact for OpenAI-family models and an estimate for others, so the budget keeps a safety buffer and a
per-model calibration factor learned from the provider's own `usage.prompt_tokens` (clamped to [0.5, 3.0]).

Unlike the compression stage, which counts only message text, the budget also counts what the provider bills:
assistant tool-call arguments, tool definitions and a small per-message overhead.
"""

import hashlib
import json
import threading
from collections import OrderedDict

from prompt_compression.texts import count_tokens, text_parts

# OpenAI's chat format adds about this many tokens per message for role and separators.
MESSAGE_OVERHEAD = 4
_CACHE_SIZE = 4096
_CALIBRATION_BOUNDS = (0.5, 3.0)
_CALIBRATION_WEIGHT = 0.2      # EWMA weight of a new observation


class _TokenCache:
    """Token counts by content hash: repeated turns of a conversation are counted once per worker."""

    def __init__(self, size: int = _CACHE_SIZE):
        self._size = size
        self._data: OrderedDict = OrderedDict()
        self._lock = threading.Lock()

    def count(self, text: str) -> int:
        if not text:
            return 0
        if len(text) < 64:
            return count_tokens(text)
        key = hashlib.sha1(text.encode("utf-8", "surrogatepass")).digest()
        with self._lock:
            if key in self._data:
                self._data.move_to_end(key)
                return self._data[key]
        tokens = count_tokens(text)
        with self._lock:
            self._data[key] = tokens
            if len(self._data) > self._size:
                self._data.popitem(last=False)
        return tokens


_cache = _TokenCache()


def text_tokens(text: str) -> int:
    return _cache.count(text)


def message_text(message: dict) -> str:
    return "\n".join(text for _, text in text_parts(message))


def tool_calls_text(message: dict) -> str:
    calls = message.get("tool_calls") or []
    parts = []
    for call in calls:
        if isinstance(call, dict):
            function = call.get("function") or {}
            parts.append(f"{function.get('name', '')} {function.get('arguments', '')}")
    function_call = message.get("function_call")
    if isinstance(function_call, dict):
        parts.append(f"{function_call.get('name', '')} {function_call.get('arguments', '')}")
    return "\n".join(parts)


def message_tokens(message: dict) -> int:
    return MESSAGE_OVERHEAD + text_tokens(message_text(message)) + text_tokens(tool_calls_text(message))


def messages_tokens(messages: list) -> int:
    return sum(message_tokens(m) for m in messages)


def tools_tokens(tools) -> int:
    if not tools:
        return 0
    try:
        return text_tokens(json.dumps(tools, ensure_ascii=False))
    except (TypeError, ValueError):
        return 0


class Calibration:
    """Per-model ratio of provider-reported prompt tokens to this module's estimate.

    An observation outside [0.5, 3.0] is discarded rather than clamped: it means the usage figure does not describe this
    prompt (a mock provider reporting 1 token, a provider that leaves cached tokens out of prompt_tokens, a response
    served from LiteLLM's cache). The factor stays 1.0 until `_MIN_SAMPLES` plausible observations have been seen."""

    def __init__(self, min_samples: int = 3):
        self._ratios: dict = {}
        self._samples: dict = {}
        self._min_samples = min_samples
        self._lock = threading.Lock()

    def factor(self, model: str) -> float:
        with self._lock:
            if self._samples.get(model, 0) < self._min_samples:
                return 1.0
            return self._ratios.get(model, 1.0)

    def record(self, model: str, estimated: int, reported: int) -> bool:
        if not model or estimated <= 0 or not reported or reported <= 0:
            return False
        low, high = _CALIBRATION_BOUNDS
        ratio = reported / estimated
        if not low <= ratio <= high:
            return False
        with self._lock:
            previous = self._ratios.get(model)
            self._ratios[model] = ratio if previous is None else (1 - _CALIBRATION_WEIGHT) * previous + _CALIBRATION_WEIGHT * ratio
            self._samples[model] = self._samples.get(model, 0) + 1
        return True


CALIBRATION = Calibration()
