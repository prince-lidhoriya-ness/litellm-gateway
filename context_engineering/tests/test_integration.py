"""Context engineering together with the existing prompt-compression stage, through LiteLLM's own pre-call loop.

The compression stage runs with the test doubles of prompt_compression/tests (a keyword sensitivity detector and a
compressor that keeps every other word), so these tests need no models and show exactly what each stage changed.
"""

import asyncio
import copy
import itertools
import json
from pathlib import Path

import pytest
import yaml

from context_engineering import callback as cb
from context_engineering.engine import ContextEngine
from context_engineering.store import MemoryStore
from context_engineering.structures import SUMMARY_MARKER
from prompt_compression.pipeline import PromptPipeline
from prompt_compression.prompt_compression_callback import PromptCompressionCallback
from prompt_compression.tests.fakes import StubCompressor, StubDetector
from prompt_compression.tests.test_pipeline import settings as pc_settings

from .builders import agent_conversation, json_output, log_output, long_chat, settings

GATEWAY = Path(__file__).resolve().parents[2]


def compression(**overrides):
    s = pc_settings(**{"routes": frozenset({"narrative"}), **overrides})
    pipeline = PromptPipeline(settings=s, detector=StubDetector(), compressor=StubCompressor())
    return PromptCompressionCallback(pipeline=pipeline, settings=s)


def context(**overrides):
    s = settings(**overrides)
    return cb.ContextEngineeringCallback(engine=ContextEngine(s, store=MemoryStore()), settings=s)


async def chain(callbacks, data):
    for callback in callbacks:
        data = await callback.async_pre_call_hook(user_api_key_dict=None, cache=None, data=data, call_type="acompletion")
    return data


def run(callbacks, data):
    return asyncio.run(chain(callbacks, data))


def test_the_compaction_summary_reaches_the_provider_verbatim():
    chat = long_chat(14)
    out = run([context(compaction_enabled=True, window_tokens=8000), compression()], {"model": "m", "messages": chat})
    ce = out["metadata"]["context_engineering"]
    pc = out["metadata"]["prompt_compression"]
    index = ce["summary_index"]
    entry = next(e for e in pc["messages"] if e["index"] == index)
    assert entry["action"] == "preserved_context_engineering"
    assert out["messages"][index]["content"].startswith(SUMMARY_MARKER)
    # compression still works on everything else (the stub drops every other word of long prose)
    assert pc["tokens_after"] < pc["tokens_before"]


def test_without_the_hint_the_summary_would_have_been_compressed():
    chat = long_chat(14)
    ce_only = run([context(compaction_enabled=True, window_tokens=8000)], {"model": "m", "messages": chat})
    summary = ce_only["messages"][ce_only["metadata"]["context_engineering"]["summary_index"]]["content"]
    stripped = copy.deepcopy(ce_only)
    stripped["metadata"]["context_engineering"]["hints"] = {}
    out = run([compression()], stripped)
    assert out["messages"][ce_only["metadata"]["context_engineering"]["summary_index"]]["content"] != summary


def test_context_engineering_disabled_gives_exactly_the_compression_only_result():
    chat = long_chat(14)
    alone = run([compression()], {"model": "m", "messages": copy.deepcopy(chat)})
    both = run([context(enabled=False), compression()], {"model": "m", "messages": copy.deepcopy(chat)})
    assert both["messages"] == alone["messages"] and "context_engineering" not in both["metadata"]


def test_below_the_size_gate_the_request_is_unchanged_by_context_engineering():
    data = {"model": "m", "messages": [{"role": "user", "content": "short question about billing"}]}
    alone = run([compression()], copy.deepcopy(data))
    both = run([context(min_tokens=1000), compression()], copy.deepcopy(data))
    assert both["messages"] == alone["messages"]


def test_structured_data_code_logs_and_tool_payloads_stay_byte_identical():
    code = "```python\ndef settle(batch_id: str, retries: int = 3) -> bool:\n    return ledger.commit(batch_id, retries)\n```"
    logs = log_output(12)
    data_block = json_output(5)
    messages = agent_conversation(9, output=lambda c=itertools.count(): log_output(120, tag=f"t{next(c)}"))
    messages.append({"role": "user", "content": f"Here is the code:\n\n{code}\n\nThe log:\n\n{logs}\n\nOrders:\n\n"
                                                f"{data_block}\n\nWhy does settle fail for batch B-77?"})
    out = run([context(), compression(protect_edges=True)], {"model": "gpt-4o-mini", "messages": messages})
    final_query = out["messages"][-1]["content"]
    for block in (code, logs, data_block):
        assert block in final_query
    for before, after in zip(messages, out["messages"]):
        if before.get("tool_calls"):
            assert after["tool_calls"] == before["tool_calls"]          # tool inputs untouched
        if before["role"] == "tool":
            assert after["tool_call_id"] == before["tool_call_id"]
    masked = out["metadata"]["context_engineering"]["masked"]
    assert masked and all(out["messages"][r["index"]]["content"].startswith("[gateway: observation") for r in masked)


@pytest.mark.parametrize("model,caching", [
    ("gpt-4o-mini", "supported"), ("anthropic/claude-sonnet-4-5", "supported"),
    ("ollama_chat/llama3.2:3b", "unknown"), ("smart-cheap", "unknown"), ("openai/mock-echo", "unknown"),
])
def test_different_model_configurations(model, caching):
    data = {"model": model, "messages": agent_conversation(9, output=lambda c=itertools.count(): log_output(
        120, tag=f"m{next(c)}"))}
    out = run([context(compaction_enabled=True, jit_enabled=True), compression()], data)
    ce = out["metadata"]["context_engineering"]
    assert ce["status"] == "ok" and ce["caching"] == caching and ce["invariant_violations"] == []
    assert out["metadata"]["prompt_compression"]["status"] in ("ok", "skipped")


def test_a_failing_context_stage_leaves_compression_working():
    callback = context()

    def boom(*args, **kwargs):
        raise RuntimeError("bug")
    callback._engine.process = boom
    chat = long_chat(6)
    alone = run([compression()], {"model": "m", "messages": copy.deepcopy(chat)})
    both = run([callback, compression()], {"model": "m", "messages": copy.deepcopy(chat)})
    assert both["metadata"]["context_engineering"]["status"] == "error"
    assert both["messages"] == alone["messages"]


def test_compression_history_route_never_drops_the_protected_summary():
    chat = long_chat(14)
    ce_out = run([context(compaction_enabled=True, window_tokens=8000)], {"model": "m", "messages": chat})
    index = ce_out["metadata"]["context_engineering"]["summary_index"]
    summary = ce_out["messages"][index]
    out = run([compression(routes=frozenset({"narrative", "history"}), history_max_tokens=300,
                           history_keep_messages=2)], ce_out)
    assert summary in out["messages"]


def test_through_litellm_proxy_logging_in_config_order():
    """LiteLLM's own pre-call loop (ProxyLogging.pre_call_hook) with both callbacks, as litellm_config.yaml lists them."""
    import litellm
    from litellm.caching.caching import DualCache
    from litellm.proxy._types import UserAPIKeyAuth
    from litellm.proxy.utils import ProxyLogging

    previous = litellm.callbacks
    litellm.callbacks = [context(compaction_enabled=True, window_tokens=8000), compression()]
    try:
        logging_obj = ProxyLogging(user_api_key_cache=DualCache())
        data = {"model": "m", "messages": long_chat(14), "metadata": {}}
        out = asyncio.run(logging_obj.pre_call_hook(user_api_key_dict=UserAPIKeyAuth(), data=data,
                                                    call_type="acompletion"))
    finally:
        litellm.callbacks = previous
    index = out["metadata"]["context_engineering"]["summary_index"]
    assert out["metadata"]["context_engineering"]["status"] == "ok"
    assert next(e for e in out["metadata"]["prompt_compression"]["messages"] if e["index"] == index)["action"] == \
        "preserved_context_engineering"
    json.dumps(out["messages"])


def test_the_proxy_config_loader_finds_the_callback():
    from litellm.proxy.types_utils.utils import get_instance_fn

    instance = get_instance_fn("context_engineering.callback.context_engineering_instance",
                               str(GATEWAY / "litellm_config.yaml"))
    assert type(instance).__name__ == "ContextEngineeringCallback"


@pytest.mark.parametrize("config", ["litellm_config.yaml", "config.yaml"])
def test_config_files_register_context_engineering_before_compression(config):
    callbacks = yaml.safe_load((GATEWAY / config).read_text(encoding="utf-8"))["litellm_settings"]["callbacks"]
    ce = callbacks.index("context_engineering.callback.context_engineering_instance")
    compression_entry = next(i for i, c in enumerate(callbacks) if "prompt_compression" in c)
    assert ce < compression_entry


def test_compose_mounts_the_package():
    compose = yaml.safe_load((GATEWAY / "docker-compose.quickstart.yml").read_text(encoding="utf-8"))
    service = compose["services"]["litellm"]
    assert "./context_engineering:/app/context_engineering" in service["volumes"]
    assert "CONTEXT_ENGINEERING_ENABLED" in service["environment"]
