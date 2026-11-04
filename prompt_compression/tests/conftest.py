import logging
import os
import sys
from pathlib import Path

import pytest

# Importing the callback module builds the LiteLLM hook; keep it from loading models at import time.
os.environ.setdefault("PROMPT_COMPRESSION_EAGER_LOAD", "false")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

GATEWAY_DIR = Path(__file__).resolve().parents[2]
if str(GATEWAY_DIR) not in sys.path:
    sys.path.insert(0, str(GATEWAY_DIR))


@pytest.fixture(autouse=True)
def _propagate_logs_to_caplog():
    # The callback module stops propagation so proxy logs are not doubled; caplog listens on the root logger.
    module_logger = logging.getLogger("prompt_compression")
    previous = module_logger.propagate
    module_logger.propagate = True
    yield
    module_logger.propagate = previous
