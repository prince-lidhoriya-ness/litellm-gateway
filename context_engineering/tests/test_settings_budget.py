"""Feature flags, settings validation, token estimation, model resolution and the budget manager."""

import pytest

from context_engineering import budget, models, tokens as tk
from context_engineering.analyzer import analyze
from context_engineering.settings import ContextSettings, parse_shares
from context_engineering.structures import CURRENT_QUERY, HISTORY, SYSTEM, TOOL_DEFINITIONS, TOOL_OUTPUT, ModelInfo

from .builders import agent_conversation, long_chat, settings


def model(window=10000, caching=None, provider="openai"):
    return ModelInfo("m", "m", provider, window, "override", caching)


# ---- settings and feature flags ----------------------------------------------------------------------------------

def test_defaults_turn_on_the_low_risk_techniques_only():
    s = ContextSettings.from_env()
    assert s.enabled and s.mode == "enforce" and s.budget_enabled and s.masking_enabled and s.prefix_cache_enabled
    assert not s.jit_enabled and not s.compaction_enabled
    assert s.store_backend == "memory" and s.fail_mode == "open"


def test_every_feature_flag_is_read_from_the_environment(monkeypatch):
    for name in ("CONTEXT_ENGINEERING_ENABLED", "CONTEXT_BUDGET_ENABLED", "OBSERVATION_MASKING_ENABLED",
                 "PREFIX_CACHE_OPTIMIZATION_ENABLED"):
        monkeypatch.setenv(name, "false")
    for name in ("JIT_RETRIEVAL_ENABLED", "CONTEXT_COMPACTION_ENABLED"):
        monkeypatch.setenv(name, "true")
    s = ContextSettings.from_env()
    assert not (s.enabled or s.budget_enabled or s.masking_enabled or s.prefix_cache_enabled)
    assert s.jit_enabled and s.compaction_enabled


def test_thresholds_are_configurable(monkeypatch):
    monkeypatch.setenv("CONTEXT_MAX_UTILIZATION", "0.5")
    monkeypatch.setenv("CONTEXT_RECENT_TURNS", "2")
    monkeypatch.setenv("JIT_RETRIEVAL_MAX_TURNS", "5")
    monkeypatch.setenv("CONTEXT_COMPACTION_THRESHOLD", "0.6")
    monkeypatch.setenv("CONTEXT_SAFETY_BUFFER", "0.2")
    monkeypatch.setenv("OBSERVATION_MAX_TOKENS", "900")
    monkeypatch.setenv("CONTEXT_BUDGET_SHARES", "tool_output=0.5,history=0.2")
    s = ContextSettings.from_env()
    assert (s.max_utilization, s.recent_turns, s.jit_max_turns, s.compaction_threshold, s.safety_buffer,
            s.observation_max_tokens) == (0.5, 2, 5, 0.6, 0.2, 900)
    assert s.shares == {"tool_output": 0.5, "history": 0.2}


@pytest.mark.parametrize("name,value", [
    ("CONTEXT_ENGINEERING_MODE", "sometimes"), ("CONTEXT_MAX_UTILIZATION", "1.5"), ("CONTEXT_RECENT_TURNS", "0"),
    ("CONTEXT_STORE", "s3"), ("CONTEXT_BUDGET_SHARES", "bogus=0.1"), ("OBSERVATION_MASK_BATCH", "0"),
])
def test_invalid_settings_are_rejected_at_startup(monkeypatch, name, value):
    monkeypatch.setenv(name, value)
    with pytest.raises(ValueError):
        ContextSettings.from_env()


def test_shares_parser():
    assert parse_shares("history=0.3; tool_output=0.4") == {"history": 0.3, "tool_output": 0.4}


# ---- token estimation --------------------------------------------------------------------------------------------

def test_token_estimate_counts_text_tool_calls_and_overhead():
    plain = {"role": "user", "content": "hello world"}
    with_call = {"role": "assistant", "content": None, "tool_calls": [
        {"id": "c", "type": "function", "function": {"name": "read_file", "arguments": '{"path": "src/app.py"}'}}]}
    assert tk.message_tokens(plain) == tk.MESSAGE_OVERHEAD + tk.text_tokens("hello world")
    assert tk.message_tokens(with_call) > tk.MESSAGE_OVERHEAD
    assert tk.tools_tokens([{"type": "function", "function": {"name": "x", "parameters": {}}}]) > 0
    assert tk.tools_tokens(None) == 0


def test_token_cache_returns_the_same_count():
    text = "the quick brown fox " * 50
    assert tk.text_tokens(text) == tk.text_tokens(text) > 0


def test_calibration_needs_plausible_samples_and_is_smoothed():
    cal = tk.Calibration(min_samples=3)
    assert cal.record("m", 1000, 1) is False          # a mock reporting 1 token: discarded, not clamped
    assert cal.record("m", 100, 1000) is False        # ratio 10: discarded
    assert cal.record("m", 0, 100) is False
    for _ in range(2):
        cal.record("m", 1000, 1300)
    assert cal.factor("m") == 1.0                     # not yet enough samples
    cal.record("m", 1000, 1300)
    assert cal.factor("m") == pytest.approx(1.3)
    cal.record("m", 1000, 1000)                       # EWMA towards 1.0
    assert 1.0 < cal.factor("m") < 1.3
    assert cal.factor("unknown") == 1.0


# ---- model resolution --------------------------------------------------------------------------------------------

def test_model_window_and_caching_come_from_the_litellm_model_map():
    info = models.resolve("gpt-4o-mini", ContextSettings())
    assert info.window_source == "model_map" and info.window > 100000 and info.supports_caching is True
    local = models.resolve("ollama_chat/llama3.2:3b", ContextSettings())
    # No flag in the model map: unknown (Ollama reuses a byte-identical prefix locally), not "known not to cache".
    assert local.supports_caching is None and local.provider == "ollama_chat"


def test_unknown_models_get_the_default_window_and_unknown_caching():
    info = models.resolve("smart-cheap", ContextSettings(default_window_tokens=12345))
    assert (info.window, info.window_source, info.supports_caching) == (12345, "default", None)


def test_window_and_caching_overrides():
    info = models.resolve("gpt-4o-mini", ContextSettings(window_tokens=5000, cache_support="off"))
    assert (info.window, info.window_source, info.supports_caching) == (5000, "override", False)


# ---- budget manager ----------------------------------------------------------------------------------------------

def test_categories_are_accounted_separately():
    tools = [{"type": "function", "function": {"name": "read_logs", "parameters": {"type": "object"}}}]
    profile = analyze(agent_conversation(3), tools)
    assert profile.totals[SYSTEM] > 0 and profile.totals[TOOL_DEFINITIONS] > 0
    assert profile.totals[TOOL_OUTPUT] > profile.totals[HISTORY] > 0
    assert profile.totals[CURRENT_QUERY] > 0
    assert profile.total_tokens == sum(profile.totals.values())


def test_target_keeps_the_output_reserve_and_the_safety_buffer():
    s = settings(max_utilization=1.0, safety_buffer=0.1, reserved_output_tokens=1000)
    target, reserve = budget.target_tokens(model(10000), s)
    assert reserve == 1000 and target == int(9000 * 0.9)
    target, reserve = budget.target_tokens(model(10000), s, max_tokens=3000)
    assert reserve == 3000 and target == int(7000 * 0.9)
    _, reserve = budget.target_tokens(model(10000), s, max_tokens=999999)
    assert reserve == 5000                              # never more than half the window


def test_pressure_levels_and_triggers():
    s = settings(compaction_enabled=True, window_tokens=0)
    chat = long_chat(14)
    low = budget.plan(analyze(chat), model(10**6), s)
    assert low.pressure == "low" and "history" not in low.techniques and {"dedupe", "mask"} <= low.techniques
    high = budget.plan(analyze(chat), model(5000), s)
    assert high.pressure == "over" and "history" in high.techniques
    assert any("utilization" in d for d in high.decisions)


def test_oversized_components_are_identified_and_recorded():
    plan = budget.plan(analyze(agent_conversation(6)), model(60000), settings())
    assert TOOL_OUTPUT in plan.oversized
    assert any(d.startswith("oversized: tool_output") for d in plan.decisions)


def test_mask_trigger_pressure_masks_only_when_needed():
    s = settings(mask_trigger="pressure")
    small = budget.plan(analyze(agent_conversation(1)), model(10**6), s)
    big = budget.plan(analyze(agent_conversation(6)), model(60000), s)
    assert "mask" not in small.techniques and "mask" in big.techniques


def test_budget_disabled_keeps_only_the_triggers_that_need_no_budget():
    plan = budget.plan(analyze(long_chat(14)), model(3000), settings(budget_enabled=False, compaction_enabled=True))
    assert not plan.enabled and "history" not in plan.techniques and "mask" in plan.techniques


def test_calibration_factor_scales_utilization():
    profile = analyze(long_chat(6))
    one = budget.plan(profile, model(20000), settings(), calibration=1.0)
    two = budget.plan(profile, model(20000), settings(), calibration=2.0)
    assert two.utilization == pytest.approx(2 * one.utilization, rel=0.01)
