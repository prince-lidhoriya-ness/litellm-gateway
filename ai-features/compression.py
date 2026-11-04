"""LiteLLM proxy callback: compress long chat messages with LLMLingua-2.

Registered in litellm_config.yaml as
    litellm_settings:
      callbacks: ["compression.compression_guardrail_instance"]

Mounted into the gateway image at /app/compression.py by
docker-compose.quickstart.yml (see Dockerfile, which adds llmlingua and a
CPU-only torch build on top of the stock LiteLLM image). Unlike
prompt_compression/ (the full classify -> route -> compress pipeline used by
config.yaml), this is a single-file, classification-free compressor meant for
the docker-compose quickstart: any message whose content is at least
COMPRESSION_THRESHOLD_CHARS long is compressed at a fixed rate with
LLMLingua-2 before the request reaches the model.

Fails open: if the compressor can't be loaded or a compression call raises,
the original message content is sent unchanged and a warning is logged.
"""

import logging
import os

from litellm.integrations.custom_logger import CustomLogger

logger = logging.getLogger("compression")
if not logger.handlers:
    _handler = logging.StreamHandler()
    _handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    logger.addHandler(_handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False

CHAT_CALL_TYPES = frozenset({"completion", "acompletion"})


def _float_env(name: str, default: float) -> float:
    try:
        return float(os.environ[name])
    except (KeyError, ValueError):
        return default


def _int_env(name: str, default: int) -> int:
    try:
        return int(os.environ[name])
    except (KeyError, ValueError):
        return default


class CompressionGuardrail(CustomLogger):
    """Compresses long message content with LLMLingua-2 before the provider call."""

    def __init__(self):
        super().__init__()
        self.threshold_chars = _int_env("COMPRESSION_THRESHOLD_CHARS", 4000)
        self.rate = _float_env("COMPRESSION_RATE", 0.5)
        self.model_name = os.getenv("COMPRESSION_MODEL", "microsoft/llmlingua-2-xlm-roberta-large-meetingbank")
        self._compressor = None
        self._compressor_error: Exception | None = None

    def _load_compressor(self):
        if self._compressor is None and self._compressor_error is None:
            try:
                from llmlingua import PromptCompressor

                self._compressor = PromptCompressor(
                    model_name=self.model_name,
                    device_map="cpu",
                    use_llmlingua2=True,
                )
            except Exception as exc:
                self._compressor_error = exc
                logger.warning("prompt compression disabled: model load failed error=%s", type(exc).__name__)
        return self._compressor

    def _compress_text(self, text: str) -> str:
        if len(text) < self.threshold_chars:
            return text
        compressor = self._load_compressor()
        if compressor is None:
            return text
        try:
            result = compressor.compress_prompt([text], rate=self.rate)
        except Exception as exc:
            logger.warning("prompt compression failed, sending original text unchanged: %s", type(exc).__name__)
            return text
        return result.get("compressed_prompt", text)

    async def async_pre_call_hook(self, user_api_key_dict, cache, data: dict, call_type):
        if call_type not in CHAT_CALL_TYPES or not isinstance(data.get("messages"), list):
            return data

        for message in data["messages"]:
            content = message.get("content")
            if isinstance(content, str) and content:
                message["content"] = self._compress_text(content)

        return data


compression_guardrail_instance = CompressionGuardrail()
