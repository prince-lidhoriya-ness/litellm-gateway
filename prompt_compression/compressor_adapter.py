"""Thin adapter over llmlingua.PromptCompressor (LLMLingua-2), used unmodified.

Builds and calls it as PromptCompressor(model_name, device_map="cpu", use_llmlingua2=True) and
compress_prompt([text], rate=..., force_reserve_digit=True).

Three things around the call (PROJECT_AUDIT_REPORT.md, F-02, F-15, F-19S):
  * the model loads at a pinned Hugging Face revision and with trust_remote_code=False (llmlingua's default is True);
  * the call lock is taken only until the request's deadline (deadline.py), so a request never queues behind a
    timed-out one past its own deadline;
  * outputs are remembered in a small LRU keyed by (text, rate): an earlier conversation turn is compressed once and
    then replayed byte for byte, which saves the CPU and keeps the prompt prefix stable for provider prompt caching.
"""

import hashlib
import logging
import threading
import time
from collections import OrderedDict
from dataclasses import dataclass
from typing import Optional

from prompt_compression import deadline as deadlines
from prompt_compression.settings import DEFAULT_COMPRESSION_MODEL, DEFAULT_COMPRESSION_REVISION, resolve_revision

logger = logging.getLogger("prompt_compression.compressor")


@dataclass(frozen=True)
class CompressionOutput:
    text: str
    origin_tokens: int
    compressed_tokens: int
    # True when the output came from the cache (no model call was made).
    cached: bool = False


class LLMLinguaCompressor:
    def __init__(self, model_name: str, revision: Optional[str] = None, cache_size: int = 512):
        self.model_name = model_name
        self.revision = resolve_revision(model_name, revision, DEFAULT_COMPRESSION_MODEL, DEFAULT_COMPRESSION_REVISION)
        self._compressor = None
        self._load_error: Optional[BaseException] = None
        self._load_lock = threading.Lock()
        # PromptCompressor keeps per-call state on the instance, so calls are serialized.
        self._call_lock = threading.Lock()
        self._cache_size = max(0, cache_size)
        self._cache: OrderedDict = OrderedDict()
        self._cache_lock = threading.Lock()

    @property
    def loaded(self) -> bool:
        return self._compressor is not None

    def load(self) -> None:
        if self._compressor is not None:
            return
        with self._load_lock:
            if self._compressor is not None:
                return
            if self._load_error is not None:
                raise RuntimeError(f"compressor unavailable: {self._load_error}") from self._load_error
            started = time.perf_counter()
            try:
                from llmlingua import PromptCompressor

                self._compressor = PromptCompressor(
                    model_name=self.model_name, device_map="cpu", use_llmlingua2=True,
                    model_config={"revision": self.revision, "trust_remote_code": False},
                )
            except Exception as exc:
                self._load_error = exc
                logger.warning("compressor failed to load: model=%s error=%s", self.model_name, type(exc).__name__)
                raise
            logger.info("compressor loaded: model=%s revision=%s seconds=%.1f", self.model_name, self.revision,
                        time.perf_counter() - started)

    @staticmethod
    def _key(text: str, rate: float) -> str:
        return f"{rate:.4f}|{hashlib.sha256(text.encode('utf-8')).hexdigest()}"

    def compress(self, text: str, rate: float) -> CompressionOutput:
        """`rate` is the fraction of tokens kept. Digits are always reserved: a dropped number is a silent change."""
        key = self._key(text, rate)
        if self._cache_size:
            with self._cache_lock:
                hit = self._cache.get(key)
                if hit is not None:
                    self._cache.move_to_end(key)
                    return CompressionOutput(hit.text, hit.origin_tokens, hit.compressed_tokens, cached=True)
        self.load()
        with deadlines.acquire(self._call_lock, "compressor"):
            result = self._compressor.compress_prompt([text], rate=rate, force_reserve_digit=True)
        required_keys = {"compressed_prompt", "origin_tokens", "compressed_tokens"}
        missing_keys = required_keys.difference(result)
        if missing_keys:
            raise ValueError(f"LLMLingua returned an incomplete result; missing: {', '.join(sorted(missing_keys))}")
        output = CompressionOutput(result["compressed_prompt"], result["origin_tokens"], result["compressed_tokens"])
        self._remember(key, output)
        return output

    def _remember(self, key: str, output: CompressionOutput) -> None:
        if self._cache_size:
            with self._cache_lock:
                self._cache[key] = output
                self._cache.move_to_end(key)
                while len(self._cache) > self._cache_size:
                    self._cache.popitem(last=False)

    def compress_many(self, texts: list, rate: float) -> tuple[list, int]:
        """Compress several texts at one rate in a single model call (LLMLingua-2 takes a list of contexts and returns
        one compressed text per context). Texts found in the cache are not sent. Returns (outputs in order, model calls
        made: 0 or 1). Used by identifier-safe compression, which splits a prose run at its identifier spans."""
        outputs: list = [None] * len(texts)
        misses = []
        for position, text in enumerate(texts):
            key = self._key(text, rate)
            hit = None
            if self._cache_size:
                with self._cache_lock:
                    hit = self._cache.get(key)
                    if hit is not None:
                        self._cache.move_to_end(key)
            if hit is not None:
                outputs[position] = CompressionOutput(hit.text, hit.origin_tokens, hit.compressed_tokens, cached=True)
            else:
                misses.append(position)
        if not misses:
            return outputs, 0
        self.load()
        batch = [texts[position] for position in misses]
        with deadlines.acquire(self._call_lock, "compressor"):
            # use_context_level_filter=False is required: compress_prompt defaults it to True, and with more than one
            # context LLMLingua-2 then drops whole contexts (measured: two contexts in, one out). A single context is
            # exempt inside llmlingua, which is why compress() never needed it.
            result = self._compressor.compress_prompt(batch, rate=rate, force_reserve_digit=True,
                                                      use_context_level_filter=False)
        compressed = result.get("compressed_prompt_list")
        if not isinstance(compressed, list) or len(compressed) != len(batch):
            raise ValueError("LLMLingua returned no per-context result (compressed_prompt_list)")
        for position, text, piece in zip(misses, batch, compressed):
            # LLMLingua reports token totals for the whole batch only; per piece the length in words is a stand-in
            # (the caller measures the joined run with its own tokenizer).
            output = CompressionOutput(piece, len(text.split()), len(piece.split()))
            self._remember(self._key(text, rate), output)
            outputs[position] = output
        return outputs, 1
