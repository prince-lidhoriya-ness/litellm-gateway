"""Environment-driven observability settings. Every variable is in monitoring/monitoring.env.example."""

import os
from dataclasses import dataclass


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
            hash_salt=os.getenv("OBS_HASH_SALT") or "",
            compute_device=(os.getenv("OBS_COMPUTE_DEVICE") or "cpu").strip().lower(),
            cpu_hourly_rate_usd=_float("OBS_CPU_HOURLY_RATE_USD", 0.10),
            gpu_hourly_rate_usd=_float("OBS_GPU_HOURLY_RATE_USD", 0.0),
            # Client-supplied model names beyond this many distinct values are bucketed as "other".
            max_model_label_values=int(_float("OBS_MAX_MODEL_LABEL_VALUES", 50)),
        )

    @property
    def hourly_rate_usd(self) -> float:
        return self.gpu_hourly_rate_usd if self.compute_device == "gpu" else self.cpu_hourly_rate_usd
