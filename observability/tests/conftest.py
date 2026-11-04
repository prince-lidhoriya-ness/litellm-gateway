import os
import sys
from pathlib import Path

import pytest

os.environ.setdefault("PROMPT_COMPRESSION_EAGER_LOAD", "false")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

GATEWAY_DIR = Path(__file__).resolve().parents[2]
if str(GATEWAY_DIR) not in sys.path:
    sys.path.insert(0, str(GATEWAY_DIR))

from opentelemetry import trace  # noqa: E402
from opentelemetry.sdk.trace import TracerProvider  # noqa: E402
from opentelemetry.sdk.trace.export import SimpleSpanProcessor  # noqa: E402
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter  # noqa: E402

# One global provider for the whole session (OTel allows setting it once), like LiteLLM V2 does at startup.
SPAN_EXPORTER = InMemorySpanExporter()
_provider = TracerProvider()
_provider.add_span_processor(SimpleSpanProcessor(SPAN_EXPORTER))
trace.set_tracer_provider(_provider)


@pytest.fixture
def spans():
    SPAN_EXPORTER.clear()
    yield SPAN_EXPORTER
    SPAN_EXPORTER.clear()
