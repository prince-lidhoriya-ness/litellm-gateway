import logging
import os
import sys
from pathlib import Path

import pytest

# LiteLLM's model map ships with the package; never fetch it from the network during tests.
os.environ.setdefault("LITELLM_LOCAL_MODEL_COST_MAP", "True")
# Importing prompt_compression's callback builds the hook; keep it from loading models at import time.
os.environ.setdefault("PROMPT_COMPRESSION_EAGER_LOAD", "false")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

GATEWAY_DIR = Path(__file__).resolve().parents[2]
if str(GATEWAY_DIR) not in sys.path:
    sys.path.insert(0, str(GATEWAY_DIR))

_PREFIXES = ("CONTEXT_", "OBSERVATION_", "JIT_RETRIEVAL_", "PREFIX_CACHE_", "REDACT_SENSITIVE",
             "PROMPT_COMPRESSION_SELECTION_SCOPE")


@pytest.fixture(autouse=True)
def _clean_environment(monkeypatch):
    """Every test starts from the code defaults, whatever the developer's shell exports."""
    for name in list(os.environ):
        if name.startswith(_PREFIXES):
            monkeypatch.delenv(name, raising=False)
    from context_engineering import models

    models.clear_cache()
    yield
    models.clear_cache()


@pytest.fixture(autouse=True)
def _propagate_logs_to_caplog():
    loggers = [logging.getLogger(name) for name in ("context_engineering", "prompt_compression")]
    previous = [logger.propagate for logger in loggers]
    for logger in loggers:
        logger.propagate = True
    yield
    for logger, value in zip(loggers, previous):
        logger.propagate = value
