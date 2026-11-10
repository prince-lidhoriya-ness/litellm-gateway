"""Cache-aware construction (provider support, breakpoints, volatile prefix, tools order) and the invariant checks."""

from context_engineering import cache, validate
from context_engineering.analyzer import analyze, volatile_hits
from context_engineering.structures import ModelInfo

from .builders import agent_conversation, settings

LONG_SYSTEM = "You are the payments assistant. " + " ".join(f"Policy {i}: follow the runbook step {i}." for i in range(300))


def info(provider, caching, name="m"):
    return ModelInfo(name, name, provider, 200000, "model_map", caching)


def request(system=LONG_SYSTEM, **extra):
    return {"messages": [{"role": "system", "content": system}, {"role": "user", "content": "hi"}], **extra}


def plan_for(provider, caching, req=None, **overrides):
    req = req or request()
    return cache.plan(analyze(req["messages"]), info(provider, caching), settings(**overrides), req)


def test_caching_support_is_reported_per_provider():
    assert plan_for("openai", True).caching == "supported"
    assert plan_for("ollama_chat", False).caching == "unsupported"
    assert plan_for(None, None).caching == "unknown"


def test_history_is_frozen_unless_the_provider_is_known_not_to_cache():
    assert plan_for("openai", True).freeze_history and plan_for(None, None).freeze_history
    assert not plan_for("ollama_chat", False).freeze_history
    assert plan_for("ollama_chat", False, freeze_history="always").freeze_history


def test_jit_is_allowed_only_where_it_cannot_break_a_cached_prefix():
    assert plan_for("ollama_chat", False).jit_allowed
    assert not plan_for("anthropic", True).jit_allowed and not plan_for(None, None).jit_allowed
    assert plan_for("anthropic", True, jit_on_caching_providers=True).jit_allowed


def test_breakpoints_are_added_only_for_anthropic_style_providers_with_a_long_system_prompt():
    assert plan_for("anthropic", True).breakpoints == [{"location": "message", "role": "system"}]
    assert plan_for("bedrock", True).breakpoints
    assert plan_for("openai", True).breakpoints is None             # automatic caching, nothing to add
    assert plan_for("anthropic", False).breakpoints is None         # model without caching
    short = plan_for("anthropic", True, request(system="short"))
    assert short.breakpoints is None and any("below" in d for d in short.decisions)
    assert plan_for("anthropic", True, inject_breakpoints=False).breakpoints is None


def test_existing_cache_control_is_respected():
    with_points = request(cache_control_injection_points=[{"location": "message", "role": "user"}])
    assert plan_for("anthropic", True, with_points).breakpoints is None
    with_marker = request()
    with_marker["messages"][0] = {"role": "system", "content": [
        {"type": "text", "text": LONG_SYSTEM, "cache_control": {"type": "ephemeral"}}]}
    assert plan_for("anthropic", True, with_marker).breakpoints is None


def test_disabled_plan_changes_nothing():
    plan = plan_for("anthropic", True, prefix_cache_enabled=False)
    assert not plan.enabled and plan.breakpoints is None and not plan.freeze_history


def test_volatile_content_in_the_system_prompt_is_detected():
    assert set(volatile_hits("Current time: 2026-11-10T10:22:31Z, session id: 9f8e")) >= {"iso_datetime", "request_id"}
    assert volatile_hits("You are a helpful assistant.") == []
    req = request(system=LONG_SYSTEM + "\nToday is 2026-11-10 10:22.")
    plan = plan_for("openai", True, req)
    assert any("volatile content" in d for d in plan.decisions)


def test_volatile_lines_can_be_moved_to_the_end_of_the_query():
    messages = [{"role": "system", "content": "Be precise.\nCurrent time: 2026-11-10T10:22:31Z"},
                {"role": "user", "content": "What changed today?"}]
    moved, count = cache.relocate_volatile(messages, analyze(messages))
    assert moved[0]["content"] == "Be precise."
    assert moved[1]["content"].startswith("What changed today?") and "2026-11-10T10:22:31Z" in moved[1]["content"]
    assert count == [(0, 1)] and messages[0]["content"].endswith("Z")       # input untouched
    assert validate.check(messages, moved, frozenset({"system_edit", "query_suffix"})) == []
    assert "system" in validate.check(messages, moved)


def test_a_system_prompt_that_is_only_volatile_is_not_emptied():
    messages = [{"role": "system", "content": "2026-11-10T10:22:31Z"}, {"role": "user", "content": "hi"}]
    assert cache.relocate_volatile(messages, analyze(messages))[0] is messages


def test_tools_can_be_put_in_a_canonical_order():
    tools = [{"type": "function", "function": {"name": n}} for n in ("zeta", "alpha", "mid")]
    assert [t["function"]["name"] for t in cache.canonical_tools(tools)] == ["alpha", "mid", "zeta"]
    duplicate = tools + [{"type": "function", "function": {"name": "alpha"}}]
    assert cache.canonical_tools(duplicate) is duplicate


def test_scope_all_in_compression_is_reported(monkeypatch):
    monkeypatch.setenv("PROMPT_COMPRESSION_SELECTION_SCOPE", "all")
    assert any("SELECTION_SCOPE=all" in d for d in plan_for("openai", True).decisions)


# ---- invariants --------------------------------------------------------------------------------------------------

def test_unchanged_messages_pass_every_invariant():
    messages = agent_conversation(3)
    assert validate.check(messages, list(messages)) == []


def test_a_changed_system_message_or_query_is_caught():
    messages = agent_conversation(3) + [{"role": "user", "content": "and now?"}]
    edited = [dict(m) for m in messages]
    edited[0]["content"] = "other"
    assert "system" in validate.check(messages, edited)
    edited = [dict(m) for m in messages]
    edited[-1]["content"] = "changed"
    assert "query" in validate.check(messages, edited)


def test_an_orphaned_tool_result_is_caught():
    messages = agent_conversation(3)
    broken = [m for m in messages if not m.get("tool_calls") or m["tool_calls"][0]["id"] != "call_1"]
    assert "tool_pairing" in validate.check(messages, broken)


def test_removing_a_call_and_its_result_together_is_allowed():
    messages = agent_conversation(3)
    kept = [m for m in messages if m.get("tool_call_id") != "call_0"
            and not (m.get("tool_calls") and m["tool_calls"][0]["id"] == "call_0")]
    assert "tool_pairing" not in validate.check(messages, kept)


def test_a_changed_current_step_and_growth_are_caught():
    messages = agent_conversation(3, pending_last=True)
    edited = [dict(m) for m in messages]
    edited[-1]["content"] = "short"
    assert "current_step" in validate.check(messages, edited)
    grown = [dict(m) for m in messages]
    grown[3]["content"] = grown[3]["content"] * 2
    assert "no_growth" in validate.check(messages, grown)


def test_unknown_roles_and_unserialisable_content_are_caught():
    messages = agent_conversation(1)
    assert "roles" in validate.check(messages, messages + [{"role": "robot", "content": "x"}])
    bad = [dict(m) for m in messages]
    bad[1]["content"] = object()
    assert "serialisable" in validate.check(messages, bad)


def test_client_orphans_already_present_do_not_count():
    messages = [{"role": "system", "content": "s"}, {"role": "user", "content": "u"},
                {"role": "tool", "tool_call_id": "ghost", "content": "r"}, {"role": "assistant", "content": "a"}]
    assert validate.check(messages, list(messages)) == []
