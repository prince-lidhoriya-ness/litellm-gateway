"""Structured JSON logs with trace_id, span_id and request_id on every line.

Applies to the `prompt_compression` and `observability` loggers. Output goes to
stdout (container logs) and, when OBS_OTLP_LOGS_ENDPOINT is set, over OTLP to the
collector, which forwards to Loki; OTel's LoggingHandler attaches the active
trace context to each record. Extra fields pass through privacy.scrub().
"""

import contextvars
import json
import logging
from datetime import datetime, timezone

from observability.privacy import scrub
from observability.settings import ObservabilitySettings

try:
    from opentelemetry import trace
except ImportError:  # pragma: no cover - OTel ships with the LiteLLM image
    trace = None

request_id_var: contextvars.ContextVar = contextvars.ContextVar("obs_request_id", default=None)

LOGGER_NAMES = ("prompt_compression", "observability")
# Standard LogRecord attributes; anything else on a record is an event field.
_RECORD_ATTRS = frozenset(vars(logging.LogRecord("", 0, "", 0, "", None, None))) | {"message", "asctime", "taskName"}


def current_trace_ids() -> tuple:
    if trace is None:
        return None, None
    context = trace.get_current_span().get_span_context()
    if not context.is_valid:
        return None, None
    return format(context.trace_id, "032x"), format(context.span_id, "016x")


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        trace_id, span_id = current_trace_ids()
        payload = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(timespec="milliseconds"),
            "level": record.levelname,
            "logger": record.name,
            "event": getattr(record, "event", None) or "log",
            "message": scrub(record.getMessage()),
            "trace_id": getattr(record, "trace_id", None) or trace_id,
            "span_id": getattr(record, "span_id", None) or span_id,
            "request_id": getattr(record, "request_id", None) or request_id_var.get(),
        }
        for key, value in vars(record).items():
            if key not in _RECORD_ATTRS and key not in payload:
                payload[key] = scrub(value)
        if record.exc_info:
            payload["error_class"] = record.exc_info[0].__name__ if record.exc_info[0] else None
        return json.dumps(payload, default=str)


_configured = False


def configure_logging(settings: ObservabilitySettings) -> None:
    """Idempotent: switch the pipeline loggers to JSON and add the OTLP log exporter."""
    global _configured
    if _configured:
        return
    _configured = True

    formatter = JsonFormatter() if settings.log_json else None
    handlers = []
    if settings.otlp_logs_endpoint:
        try:
            from opentelemetry.exporter.otlp.proto.http._log_exporter import OTLPLogExporter
            from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
            from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
            from opentelemetry.sdk.resources import Resource

            provider = LoggerProvider(resource=Resource.create({"service.name": settings.service_name}))
            provider.add_log_record_processor(
                BatchLogRecordProcessor(OTLPLogExporter(endpoint=settings.otlp_logs_endpoint))
            )
            otlp_handler = LoggingHandler(level=logging.INFO, logger_provider=provider)
            otlp_handler.setFormatter(JsonFormatter())
            handlers.append(otlp_handler)
        except Exception as exc:  # never block the proxy on telemetry
            logging.getLogger("observability").warning("OTLP log export disabled: %s", type(exc).__name__)

    for name in LOGGER_NAMES:
        logger = logging.getLogger(name)
        if not any(isinstance(h, logging.StreamHandler) for h in logger.handlers):
            logger.addHandler(logging.StreamHandler())
        logger.setLevel(getattr(logging, settings.log_level, logging.INFO))
        logger.propagate = False
        for handler in logger.handlers:
            if formatter is not None and isinstance(handler, logging.StreamHandler):
                handler.setFormatter(formatter)
        for handler in handlers:
            if handler not in logger.handlers:
                logger.addHandler(handler)


def event(logger: logging.Logger, name: str, level: int = logging.INFO, **fields) -> None:
    """Log one named event; fields become JSON keys (stdout) and OTLP attributes (Loki).

    Fields are scrubbed here because OTel's LoggingHandler copies record extras verbatim.
    Values must be scalars or lists of scalars (OTLP attribute types).
    """
    extra = {k: scrub(v) for k, v in fields.items() if v is not None}
    logger.log(level, name, extra={"event": name, **extra})
