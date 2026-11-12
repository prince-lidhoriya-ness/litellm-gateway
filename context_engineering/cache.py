"""Cache-aware prompt construction.

Providers that cache prompts (Anthropic and Bedrock with cache_control breakpoints, OpenAI and Gemini automatically)
reuse the longest byte-identical prefix of a request. Anything that edits an earlier message makes everything after it
full price again. So this stage:
  * decides whether the target model caches prompts (LiteLLM's model map; PREFIX_CACHE_PROVIDER_SUPPORT overrides)
  * treats history as frozen (no per-question rewrites before the latest user message). The compression stage already
    honours this on its own (PROMPT_COMPRESSION_SELECTION_SCOPE=latest_user, its default, plus its cache of compressed
    outputs); this stage reports a warning when that scope is set to "all"
  * keeps the other stages cache-friendly: masking and compaction move in batches, and query-dependent JIT
    retrieval is off on caching providers unless JIT_RETRIEVAL_ON_CACHING_PROVIDERS=true
  * adds `cache_control_injection_points` (LiteLLM's built-in hook) for Anthropic-style providers, when the request has
    none and the system prompt is long enough to be cached
  * reports volatile content (dates, uuids, request ids) in the system prompt, and with PREFIX_CACHE_RELOCATE_VOLATILE
    moves those lines to the end of the latest user message, so the stable part stays stable
  * with PREFIX_CACHE_CANONICAL_TOOLS sorts tool definitions by name, so a client that reorders them still hits
Freezing never changes what the provider receives on the current request beyond that; it only stops later rewrites.
"""

import copy
import os

from context_engineering import analyzer
from context_engineering.settings import ContextSettings
from context_engineering.structures import CachePlan, ContextProfile, ModelInfo

# Providers whose caching needs explicit cache_control breakpoints (LiteLLM's anthropic_cache_control_hook).
BREAKPOINT_PROVIDERS = frozenset({"anthropic", "bedrock", "bedrock_converse", "vertex_ai", "vertex_ai_beta"})
RELOCATED_HEADER = "[Moved from the system prompt by the gateway for prompt-cache stability]"


def plan(profile: ContextProfile, model: ModelInfo, settings: ContextSettings, request: dict) -> CachePlan:
    if not settings.prefix_cache_enabled:
        return CachePlan(False, "unknown", False, settings.jit_enabled, None, ("prefix cache optimization disabled",))
    caching = {True: "supported", False: "unsupported", None: "unknown"}[model.supports_caching]
    decisions = [f"provider caching {caching} for {model.resolved or model.name or 'unknown model'}"]
    if settings.freeze_history == "always":
        freeze = True
    elif settings.freeze_history == "never":
        freeze = False
    else:
        freeze = caching != "unsupported"
    jit_allowed = caching == "unsupported" or settings.jit_on_caching_providers
    breakpoints = None
    if settings.inject_breakpoints and caching == "supported" and model.provider in BREAKPOINT_PROVIDERS:
        if request.get("cache_control_injection_points") or _has_cache_control(request.get("messages") or []):
            decisions.append("breakpoints: the request already carries cache_control")
        elif profile.system_tokens < settings.breakpoint_min_tokens:
            decisions.append(f"breakpoints: system prompt {profile.system_tokens} tokens, below "
                             f"{settings.breakpoint_min_tokens}")
        else:
            breakpoints = [{"location": "message", "role": "system"}]
            decisions.append("breakpoints: cache_control on the system prompt")
    if profile.volatile:
        decisions.append(f"volatile content in the system prompt: {', '.join(profile.volatile)}")
    # The compression stage keeps earlier turns byte-stable on its own (selection only in the latest user message,
    # compressed outputs replayed from its cache). Its "all" scope rewrites history per question: report it.
    if freeze and (os.getenv("PROMPT_COMPRESSION_SELECTION_SCOPE") or "").strip().lower() == "all":
        decisions.append("warning: PROMPT_COMPRESSION_SELECTION_SCOPE=all rewrites earlier turns per question; "
                         "the cached prefix will not be reused")
    return CachePlan(True, caching, freeze, jit_allowed, breakpoints, tuple(decisions))


def _has_cache_control(messages: list) -> bool:
    for message in messages:
        if isinstance(message, dict) and message.get("cache_control"):
            return True
        content = message.get("content") if isinstance(message, dict) else None
        if isinstance(content, list) and any(isinstance(p, dict) and p.get("cache_control") for p in content):
            return True
    return False


def relocate_volatile(messages: list, profile: ContextProfile) -> tuple[list, list]:
    """Move volatile lines of string system messages to the end of the latest user message. Returns (messages, moved
    line count per system message index). Only whole lines move; list-content system messages are left alone."""
    if not profile.volatile or profile.last_user_index is None:
        return messages, []
    out = list(messages)
    moved_lines, moved = [], []
    for index, message in enumerate(messages):
        if message.get("role") not in analyzer.SYSTEM_ROLES or not isinstance(message.get("content"), str):
            continue
        keep, take = [], []
        for line in message["content"].split("\n"):
            (take if analyzer.volatile_hits(line) else keep).append(line)
        if take and any(line.strip() for line in keep):
            out[index] = {**message, "content": "\n".join(keep)}
            moved_lines.extend(take)
            moved.append((index, len(take)))
    if not moved_lines:
        return messages, []
    user = copy.deepcopy(out[profile.last_user_index])
    suffix = "\n\n" + RELOCATED_HEADER + "\n" + "\n".join(moved_lines)
    if isinstance(user.get("content"), str):
        user["content"] = user["content"] + suffix
    elif isinstance(user.get("content"), list):
        user["content"] = list(user["content"]) + [{"type": "text", "text": suffix.lstrip()}]
    else:
        return messages, []
    out[profile.last_user_index] = user
    return out, moved


def canonical_tools(tools):
    """Tool definitions sorted by function name, when every tool has a unique name; otherwise unchanged."""
    if not isinstance(tools, list) or len(tools) < 2:
        return tools
    names = [((t or {}).get("function") or {}).get("name") if isinstance(t, dict) else None for t in tools]
    if any(not n for n in names) or len(set(names)) != len(names):
        return tools
    return [tool for _, tool in sorted(zip(names, tools), key=lambda pair: pair[0])]
