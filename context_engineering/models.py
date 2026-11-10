"""What the gateway knows about the target model: context window, provider, prompt-caching support.

Inside the proxy, `data["model"]` is usually a model *group* name ("obs-priced-llama", "smart-cheap"). When the
LiteLLM proxy router is loaded, the group's first deployment gives the provider model ("ollama_chat/llama3.2:3b"),
which LiteLLM's model map knows. Everything here fails soft: an unknown model gets the default window and caching
support "unknown" (the cache planner then treats history as frozen, the safe choice).
"""

import logging
import sys
import threading
from typing import Optional

from context_engineering.settings import ContextSettings
from context_engineering.structures import ModelInfo

logger = logging.getLogger("context_engineering.models")

_cache: dict = {}
_lock = threading.Lock()


def _router_model(name: str) -> Optional[str]:
    """The provider model behind a proxy model group, without importing the proxy (tests, eval scripts)."""
    proxy = sys.modules.get("litellm.proxy.proxy_server")
    router = getattr(proxy, "llm_router", None) if proxy is not None else None
    if router is None:
        return None
    try:
        deployments = router.get_model_list(model_name=name) or []
    except Exception:
        return None
    for deployment in deployments:
        params = (deployment or {}).get("litellm_params") or {}
        if params.get("model"):
            return str(params["model"])
    return None


def _model_map_info(model: str) -> dict:
    try:
        import litellm

        return dict(litellm.get_model_info(model) or {})
    except Exception:
        return {}


def _provider(model: str) -> Optional[str]:
    try:
        import litellm

        return litellm.get_llm_provider(model)[1]
    except Exception:
        return None


def _supports_caching(info: dict) -> Optional[bool]:
    """True / False only when the model map says so explicitly. LiteLLM's supports_prompt_caching() answers False for
    any model without the flag (custom deployments, Ollama), which is "not known", not "known not to cache"; local
    servers such as Ollama reuse a byte-identical prefix on their own, so "unknown" (history frozen) is the safe label."""
    flag = info.get("supports_prompt_caching")
    return flag if isinstance(flag, bool) else None


def resolve(name: str, settings: ContextSettings) -> ModelInfo:
    name = str(name or "")
    key = (name, settings.window_tokens, settings.default_window_tokens, settings.cache_support)
    with _lock:
        if key in _cache:
            return _cache[key]
    resolved = _router_model(name) or name
    info = _model_map_info(resolved) if resolved else {}
    provider = _provider(resolved) if resolved else None
    if settings.window_tokens > 0:
        window, source = settings.window_tokens, "override"
    elif info.get("max_input_tokens"):
        window, source = int(info["max_input_tokens"]), "model_map"
    else:
        window, source = settings.default_window_tokens, "default"
    if settings.cache_support == "on":
        caching: Optional[bool] = True
    elif settings.cache_support == "off":
        caching = False
    else:
        caching = _supports_caching(info)     # not in the model map, or no flag: unknown, not "unsupported"
    result = ModelInfo(name=name, resolved=resolved, provider=provider, window=window, window_source=source,
                       supports_caching=caching)
    with _lock:
        if len(_cache) > 512:
            _cache.clear()
        _cache[key] = result
    return result


def clear_cache() -> None:
    with _lock:
        _cache.clear()
