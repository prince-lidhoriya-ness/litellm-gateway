"""Thin adapter over llmlingua.PromptCompressor (LLMLingua-2), used unmodified.

Mirrors how ai-features/promptCompression/.../app.py builds and calls it:
PromptCompressor(model_name, device_map="cpu", use_llmlingua2=True) and
compress_prompt([text], rate=..., force_tokens=[...]).
"""

import logging
import threading
import time
from dataclasses import dataclass
from typing import Optional

from prompt_compression.router import Route

logger = logging.getLogger("prompt_compression.compressor")


@dataclass(frozen=True)
class CompressionOutput:
    text: str
    origin_tokens: int
    compressed_tokens: int


class LLMLinguaCompressor:
    def __init__(self, model_name: str):
        self.model_name = model_name
        self._compressor = None
        self._load_error: Optional[BaseException] = None
        self._load_lock = threading.Lock()
        # PromptCompressor keeps per-call state on the instance, so calls are serialized.
        self._call_lock = threading.Lock()

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

                self._compressor = PromptCompressor(model_name=self.model_name, device_map="cpu", use_llmlingua2=True)
            except Exception as exc:
                self._load_error = exc
                logger.warning("compressor failed to load: model=%s error=%s", self.model_name, type(exc).__name__)
                raise
            logger.info("compressor loaded: model=%s seconds=%.1f", self.model_name, time.perf_counter() - started)

    def compress(self, text: str, route: Route) -> CompressionOutput:
        self.load()
        with self._call_lock:
            result = self._compressor.compress_prompt(
                [text],
                rate=route.rate,
                force_tokens=list(route.force_tokens),
                force_reserve_digit=route.force_reserve_digit,
            )
        required_keys = {"compressed_prompt", "origin_tokens", "compressed_tokens"}
        missing_keys = required_keys.difference(result)
        if missing_keys:
            raise ValueError(f"LLMLingua returned an incomplete result; missing: {', '.join(sorted(missing_keys))}")
        return CompressionOutput(result["compressed_prompt"], result["origin_tokens"], result["compressed_tokens"])
