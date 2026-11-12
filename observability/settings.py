"""Environment-driven observability settings. Every variable is in monitoring/monitoring.env.example."""

import os
from dataclasses import dataclass

from observability.privacy import derive_salt


def _bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None or value.strip() == "":
        return default
    return value.strip().lower() in ("1", "true", "yes", "on")


def _float(name: str, default: float) -> float:
    value = os.getenv(name)
    return float(value) if value not in (None, "") else default


@dataclass(frozen=True)
class ObservabilitySettings:
    enabled: bool
    service_name: str
    otlp_logs_endpoint: str
    log_json: bool
    capture_text: bool
    hash_salt: str
    compute_device: str
    cpu_hourly_rate_usd: float
    gpu_hourly_rate_usd: float
    max_model_label_values: int
    # Messages that get per-message span attributes; the rest are counted in prompt.messages.attributes_omitted. The OTel
    # SDK keeps at most 128 attributes per span and silently drops the rest (PROJECT_AUDIT_REPORT.md, F-23).
    max_span_messages: int = 16
    # Where the hashing key came from: "OBS_HASH_SALT", "LITELLM_SALT_KEY" (derived) or "" (none: unkeyed hashes).
    hash_salt_source: str = ""
    log_level: str = "INFO"

    @classmethod
    def from_env(cls) -> "ObservabilitySettings":
        return cls(
            enabled=_bool("OBS_ENABLED", True),
            service_name=os.getenv("OBS_SERVICE_NAME") or os.getenv("OTEL_SERVICE_NAME") or "litellm-gateway",
            # e.g. http://otel-collector:4318/v1/logs; empty = stdout JSON only.
            otlp_logs_endpoint=os.getenv("OBS_OTLP_LOGS_ENDPOINT") or "",
            log_json=_bool("OBS_LOG_JSON", True),
            # Pre/post-compression text on spans, only for non_sensitive / less_important.
            capture_text=_bool("OBS_CAPTURE_TEXT", False),
            hash_salt=_hash_salt()[0],
            hash_salt_source=_hash_salt()[1],
            compute_device=(os.getenv("OBS_COMPUTE_DEVICE") or "cpu").strip().lower(),
            cpu_hourly_rate_usd=_float("OBS_CPU_HOURLY_RATE_USD", 0.10),
            gpu_hourly_rate_usd=_float("OBS_GPU_HOURLY_RATE_USD", 0.0),
            # Client-supplied model names beyond this many distinct values are bucketed as "other".
            max_model_label_values=int(_float("OBS_MAX_MODEL_LABEL_VALUES", 50)),
            max_span_messages=max(0, int(_float("OBS_MAX_SPAN_MESSAGES", 16))),
            # The JSON loggers used to be forced to INFO, ignoring PROMPT_COMPRESSION_LOG_LEVEL (F-13).
            log_level=(os.getenv("OBS_LOG_LEVEL") or os.getenv("PROMPT_COMPRESSION_LOG_LEVEL") or "INFO").strip().upper(),
        )

    @property
    def hourly_rate_usd(self) -> float:
        return self.gpu_hourly_rate_usd if self.compute_device == "gpu" else self.cpu_hourly_rate_usd


def _hash_salt() -> tuple:
    """(key, source): OBS_HASH_SALT, else a key derived from LITELLM_SALT_KEY (always set for the proxy), else none."""
    explicit = os.getenv("OBS_HASH_SALT") or ""
    if explicit:
        return explicit, "OBS_HASH_SALT"
    litellm_salt = os.getenv("LITELLM_SALT_KEY") or ""
    if litellm_salt:
        return derive_salt(litellm_salt), "LITELLM_SALT_KEY"
    return "", ""
