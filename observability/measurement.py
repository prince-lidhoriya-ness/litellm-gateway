"""Measurement before claims (reports/production-readiness-audit/STRATEGY.md, Phase 2.1 and 2.2).

One LiteLLM callback, registered FIRST in litellm_config.yaml `callbacks` so its pre-call hook sees the original request:

  pre-call   puts the request's conversation in an arm (prompt_compression/holdout.py) and writes it to the metadata
             before both optimisation stages run; a holdout conversation is then treated by both stages as in shadow
             mode. For a sampled share of optimised requests it keeps the original messages in memory (never in
             metadata, logs or spans).
  success    records what the provider billed, per arm: LiteLLM's response_cost (standard logging payload, which
             accounts for cached and cache-write tokens on providers that report them), prompt and cached tokens, and
             latency. For a sampled request whose prompt the stages changed, it starts a background quality check.

Quality check (2.2), off the request path and off by default (GATEWAY_QUALITY_SAMPLE_RATE=0). The same model is asked the
same request with the *original* messages (both stages opted out), and the two answers are compared:
  facts   identifiers and numbers with units of the original answer that the optimised answer lacks (fidelity.py);
          no call beyond the re-run
  judge   additionally a judge model (GATEWAY_QUALITY_JUDGE_MODEL) says EQUIVALENT or DIFFERENT. A ":free" judge
          model is refused unless GATEWAY_QUALITY_ALLOW_FREE_JUDGE=true: free tiers are rate-limited and can disappear
          (audit L2), and a judge that silently fails biases the sample.
The gateway's own calls carry metadata gateway_internal=true and land in arm "internal", so their cost is visible and
never mixed into the comparison. At most GATEWAY_QUALITY_MAX_INFLIGHT checks run at once; a sample that finds them busy
is dropped and counted, never queued.

Prometheus cannot group by conversation without unbounded label cardinality. Cost per conversation and p50/p95 latency
per arm come from LiteLLM's spend logs (observability/holdout_report.sql groups them by the conversation key this hook
writes into spend_logs_metadata). The counters here give the running totals per arm.
"""

import asyncio
import copy
import hashlib
import json
import logging
import os
import sys
import threading
import time
from collections import OrderedDict
from dataclasses import dataclass
from typing import Optional

from litellm.integrations.custom_logger import CustomLogger
from prometheus_client import Counter, Histogram

from prompt_compression import fidelity, holdout

logger = logging.getLogger("observability.measurement")

QUALITY_MODES = ("facts", "judge")
_OPT_OUT_KEYS = (("prompt_compression", False), ("context_engineering", False), ("disable_prompt_compression", True))

# ---- metrics (low-cardinality labels only: arm, mode, verdict, reason) ------------------------------------------------

REQUESTS = Counter("gateway_holdout_requests", "Answered requests by holdout arm.", ["arm", "mode"])
BILLED_USD = Counter("gateway_holdout_billed_usd",
                     "Provider-billed cost (LiteLLM response_cost) by holdout arm.", ["arm", "mode"])
PROMPT_TOKENS = Counter("gateway_holdout_prompt_tokens", "Provider-reported prompt tokens by holdout arm.",
                        ["arm", "mode"])
CACHED_TOKENS = Counter("gateway_holdout_cached_tokens", "Provider-reported cached prompt tokens by holdout arm.",
                        ["arm", "mode"])
CONVERSATIONS = Counter("gateway_holdout_conversations",
                        "Conversations started (requests with exactly one user message) by holdout arm.",
                        ["arm", "mode"])
LATENCY = Histogram("gateway_holdout_latency_seconds", "End-to-end request latency by holdout arm.", ["arm", "mode"],
                    buckets=(0.25, 0.5, 1, 2, 4, 8, 16, 32, 64, 128))
QUALITY_SAMPLES = Counter("gateway_quality_samples", "Quality checks by outcome.", ["mode", "verdict"])
QUALITY_FACTS_MISSING = Histogram("gateway_quality_facts_missing",
                                  "Identifiers/numbers of the original answer missing from the optimised answer.",
                                  ["mode"], buckets=(0, 1, 2, 3, 5, 8, 13))
QUALITY_DROPPED = Counter("gateway_quality_dropped", "Sampled requests not checked.", ["reason"])


@dataclass(frozen=True)
class MeasurementSettings:
    holdout_share: float = 0.0          # GATEWAY_HOLDOUT_SHARE: conversations sent unoptimised (STRATEGY.md: 0.05)
    salt: str = ""                      # GATEWAY_HOLDOUT_SALT, else OBS_HASH_SALT; changing it reshuffles the arms
    quality_sample_rate: float = 0.0    # GATEWAY_QUALITY_SAMPLE_RATE: share of optimised requests checked (STRATEGY: 0.01)
    quality_mode: str = "facts"         # GATEWAY_QUALITY_MODE: facts | judge
    judge_model: str = ""               # GATEWAY_QUALITY_JUDGE_MODEL (a paid or self-hosted deployment)
    allow_free_judge: bool = False      # GATEWAY_QUALITY_ALLOW_FREE_JUDGE
    max_inflight: int = 2               # GATEWAY_QUALITY_MAX_INFLIGHT
    max_pending: int = 64               # GATEWAY_QUALITY_MAX_PENDING: originals kept in memory awaiting their answer
    pending_ttl_s: float = 600.0
    timeout_s: float = 120.0            # GATEWAY_QUALITY_TIMEOUT_S per model call of a check

    @classmethod
    def from_env(cls) -> "MeasurementSettings":
        def number(name, default):
            raw = os.getenv(name)
            return float(raw) if raw not in (None, "") else default

        share = number("GATEWAY_HOLDOUT_SHARE", 0.0)
        if not 0.0 <= share <= 0.5:
            raise ValueError("GATEWAY_HOLDOUT_SHARE must be between 0 and 0.5")
        rate = number("GATEWAY_QUALITY_SAMPLE_RATE", 0.0)
        if not 0.0 <= rate <= 1.0:
            raise ValueError("GATEWAY_QUALITY_SAMPLE_RATE must be between 0 and 1")
        mode = (os.getenv("GATEWAY_QUALITY_MODE") or "facts").strip().lower()
        if mode not in QUALITY_MODES:
            raise ValueError(f"GATEWAY_QUALITY_MODE must be one of {', '.join(QUALITY_MODES)}")
        settings = cls(
            holdout_share=share,
            salt=os.getenv("GATEWAY_HOLDOUT_SALT") or os.getenv("OBS_HASH_SALT") or "",
            quality_sample_rate=rate,
            quality_mode=mode,
            judge_model=(os.getenv("GATEWAY_QUALITY_JUDGE_MODEL") or "").strip(),
            allow_free_judge=(os.getenv("GATEWAY_QUALITY_ALLOW_FREE_JUDGE") or "").strip().lower() in ("1", "true", "yes"),
            max_inflight=max(1, int(number("GATEWAY_QUALITY_MAX_INFLIGHT", 2))),
            max_pending=max(1, int(number("GATEWAY_QUALITY_MAX_PENDING", 64))),
            timeout_s=number("GATEWAY_QUALITY_TIMEOUT_S", 120.0),
        )
        settings.validate()
        return settings

    def validate(self) -> None:
        if self.quality_sample_rate > 0 and self.quality_mode == "judge":
            if not self.judge_model:
                raise ValueError("GATEWAY_QUALITY_MODE=judge needs GATEWAY_QUALITY_JUDGE_MODEL")
            if self.judge_model.endswith(":free") and not self.allow_free_judge:
                raise ValueError("GATEWAY_QUALITY_JUDGE_MODEL is a free-tier model; point it at a paid or self-hosted "
                                 "deployment, or set GATEWAY_QUALITY_ALLOW_FREE_JUDGE=true (STRATEGY.md, L2)")


def _fraction(text: str) -> float:
    return int(hashlib.sha256(text.encode("utf-8", "surrogatepass")).hexdigest()[:8], 16) / 0x100000000


def _get(obj, name):
    if obj is None:
        return None
    if isinstance(obj, dict):
        return obj.get(name)
    return getattr(obj, name, None)


def _metadata_dicts(data: dict) -> list:
    return [data[key] for key in ("metadata", "litellm_metadata") if isinstance(data.get(key), dict)]


def _opted_out(data: dict) -> bool:
    for metadata in _metadata_dicts(data):
        for key, value in _OPT_OUT_KEYS:
            if metadata.get(key) is value or str(metadata.get(key)).lower() == str(value).lower():
                return True
    return False


def _internal(metadata: dict) -> bool:
    return metadata.get("gateway_internal") in (True, "true", "True")


def answer_text(response) -> str:
    """The answer's text plus its tool calls (JSON), from a LiteLLM ModelResponse or a dict."""
    try:
        choice = response["choices"][0] if isinstance(response, dict) else response.choices[0]
        message = choice["message"] if isinstance(choice, dict) else choice.message
        get = message.get if isinstance(message, dict) else (lambda name, default=None: getattr(message, name, default))
        parts = [get("content") or ""]
        calls = get("tool_calls") or []
        if calls:
            parts.append(json.dumps([c if isinstance(c, dict) else c.model_dump() for c in calls], sort_keys=True,
                                    default=str))
        return "\n".join(part for part in parts if part)
    except Exception:
        return ""


def missing_facts(original_answer: str, optimised_answer: str) -> list:
    """Identifiers and numbers with units the original answer gives and the optimised one does not."""
    return fidelity.missing(fidelity.must_survive(original_answer), optimised_answer)


JUDGE_INSTRUCTIONS = (
    "You compare two answers to the same request. Reply with exactly one word: EQUIVALENT if both give the same facts, "
    "values and conclusion (wording may differ), DIFFERENT if either gives a fact, value or conclusion the other does "
    "not or contradicts it."
)


def parse_verdict(text: str) -> str:
    upper = (text or "").upper()
    has_equivalent, has_different = "EQUIVALENT" in upper, "DIFFERENT" in upper
    if has_equivalent == has_different:
        return "unparsed"
    return "equivalent" if has_equivalent else "different"


class MeasurementCallback(CustomLogger):
    def __init__(self, settings: Optional[MeasurementSettings] = None, completion=None):
        super().__init__()
        self.settings = settings or MeasurementSettings.from_env()
        self._completion = completion            # tests inject a fake; production uses the proxy router
        self._pending: OrderedDict = OrderedDict()   # litellm_call_id -> (stored_at, original messages)
        self._pending_lock = threading.Lock()
        self._inflight = 0
        self._tasks: set = set()

    # ---- pre-call: the arm, and the original of a sampled request -----------------------------------------------

    async def async_pre_call_hook(self, user_api_key_dict, cache, data: dict, call_type):
        try:
            self._decide(data)
        except Exception as exc:              # measurement never breaks a request
            logger.warning("measurement: pre-call failed: %s", type(exc).__name__)
        return data

    def _decide(self, data: dict) -> None:
        if holdout.decision(data) is not None or not isinstance(data.get("messages"), list):
            return
        key = holdout.conversation_key(data, self.settings.salt)
        if any(_internal(metadata) for metadata in _metadata_dicts(data)):
            arm = holdout.INTERNAL
        elif _opted_out(data):
            arm = holdout.EXCLUDED
        else:
            arm = holdout.assign(key, self.settings.holdout_share)
        holdout.write(data, arm, key, holdout.user_turn(data))
        call_id = data.get("litellm_call_id")
        if (arm == holdout.TREATMENT and call_id and self.settings.quality_sample_rate > 0
                and _fraction(f"quality\x1f{call_id}") < self.settings.quality_sample_rate):
            self._remember(str(call_id), copy.deepcopy(data["messages"]))

    def _remember(self, call_id: str, messages: list) -> None:
        now = time.monotonic()
        with self._pending_lock:
            self._pending[call_id] = (now, messages)
            while len(self._pending) > self.settings.max_pending:
                self._pending.popitem(last=False)
                QUALITY_DROPPED.labels("pending_full").inc()

    def _take(self, call_id: str) -> Optional[list]:
        with self._pending_lock:
            entry = self._pending.pop(call_id, None)
            cutoff = time.monotonic() - self.settings.pending_ttl_s
            for stale in [k for k, (stored, _) in self._pending.items() if stored < cutoff]:
                self._pending.pop(stale, None)
                QUALITY_DROPPED.labels("expired").inc()
        return entry[1] if entry else None

    # ---- after the provider answered ----------------------------------------------------------------------------

    async def async_log_success_event(self, kwargs, response_obj, start_time, end_time):
        try:
            self._record(kwargs, response_obj, start_time, end_time)
            self._maybe_check(kwargs, response_obj)
        except Exception as exc:
            logger.warning("measurement: success accounting failed: %s", type(exc).__name__)

    async def async_log_failure_event(self, kwargs, response_obj, start_time, end_time):
        call_id = kwargs.get("litellm_call_id")
        if call_id:
            self._take(str(call_id))

    @staticmethod
    def _spend_metadata(kwargs: dict) -> dict:
        payload = kwargs.get("standard_logging_object") or {}
        spend = (payload.get("metadata") or {}).get("spend_logs_metadata") or {}
        if not spend:
            spend = ((kwargs.get("litellm_params") or {}).get("metadata") or {}).get("spend_logs_metadata") or {}
        return spend if isinstance(spend, dict) else {}

    @staticmethod
    def _mode(spend: dict) -> str:
        """enforce when either stage applied its output, shadow when they only reported, none when neither ran."""
        statuses = {(spend.get(key) or {}).get("status") for key in ("context_engineering", "prompt_compression")}
        if "ok" in statuses:
            return "enforce"
        return "shadow" if "shadow" in statuses else "none"

    def _record(self, kwargs: dict, response_obj, start_time, end_time) -> None:
        spend = self._spend_metadata(kwargs)
        decision = spend.get(holdout.METADATA_KEY) or {}
        arm = decision.get("arm") if decision.get("arm") in holdout.ARMS else "unassigned"
        request_metadata = (kwargs.get("litellm_params") or {}).get("metadata") or {}
        if _internal(request_metadata):
            # The gateway's own calls (quality re-runs, judge) go to the router directly, so no pre-call hook gave them
            # an arm; they carry gateway_internal instead.
            arm = holdout.INTERNAL
        mode = self._mode(spend)
        payload = kwargs.get("standard_logging_object") or {}
        REQUESTS.labels(arm, mode).inc()
        cost = payload.get("response_cost")
        if isinstance(cost, (int, float)) and cost > 0:
            BILLED_USD.labels(arm, mode).inc(float(cost))
        prompt_tokens = payload.get("prompt_tokens")
        if isinstance(prompt_tokens, int) and prompt_tokens > 0:
            PROMPT_TOKENS.labels(arm, mode).inc(prompt_tokens)
        usage = _get(response_obj, "usage")
        cached = _get(_get(usage, "prompt_tokens_details"), "cached_tokens") or _get(usage, "cache_read_input_tokens") or 0
        if isinstance(cached, int) and cached > 0:
            CACHED_TOKENS.labels(arm, mode).inc(cached)
        if decision.get("turn") == 1:
            CONVERSATIONS.labels(arm, mode).inc()
        try:
            LATENCY.labels(arm, mode).observe(max(0.0, (end_time - start_time).total_seconds()))
        except Exception:
            pass

    # ---- quality check -------------------------------------------------------------------------------------------

    def _maybe_check(self, kwargs: dict, response_obj) -> None:
        call_id = kwargs.get("litellm_call_id")
        original = self._take(str(call_id)) if call_id else None
        if original is None:
            return
        spend = self._spend_metadata(kwargs)
        changed = any(
            (spend.get(key) or {}).get("status") == "ok"
            and int((spend.get(key) or {}).get("tokens_before") or 0) > int((spend.get(key) or {}).get("tokens_after") or 0)
            for key in ("context_engineering", "prompt_compression")
        )
        if not changed:
            QUALITY_DROPPED.labels("not_optimised").inc()
            return
        if self._inflight >= self.settings.max_inflight:
            QUALITY_DROPPED.labels("busy").inc()
            return
        optimised = answer_text(response_obj)
        payload = kwargs.get("standard_logging_object") or {}
        model = payload.get("model_group") or kwargs.get("model")
        params = {name: value for name, value in (kwargs.get("optional_params") or {}).items()
                  if name in ("temperature", "max_tokens", "max_completion_tokens", "top_p", "tools", "tool_choice",
                              "response_format", "seed")}
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            QUALITY_DROPPED.labels("no_loop").inc()
            return
        self._inflight += 1
        task = loop.create_task(self._check(str(call_id), model, original, params, optimised))
        self._tasks.add(task)
        task.add_done_callback(self._done)

    def _done(self, task) -> None:
        self._tasks.discard(task)
        self._inflight = max(0, self._inflight - 1)

    async def _complete(self, model: str, messages: list, **params):
        metadata = {"prompt_compression": False, "context_engineering": False, "gateway_internal": True,
                    "tags": ["gateway:quality_check"]}
        if self._completion is not None:
            return await self._completion(model=model, messages=messages, metadata=metadata, **params)
        proxy = sys.modules.get("litellm.proxy.proxy_server")
        router = getattr(proxy, "llm_router", None) if proxy is not None else None
        if router is not None:
            return await router.acompletion(model=model, messages=messages, metadata=metadata, **params)
        import litellm

        return await litellm.acompletion(model=model, messages=messages, metadata=metadata, **params)

    async def _check(self, call_id: str, model: str, original: list, params: dict, optimised: str) -> Optional[str]:
        mode = self.settings.quality_mode
        try:
            rerun = await asyncio.wait_for(self._complete(model, original, **params), self.settings.timeout_s)
            baseline = answer_text(rerun)
            lost = missing_facts(baseline, optimised)
            QUALITY_FACTS_MISSING.labels(mode).observe(len(lost))
            verdict = "facts_match" if not lost else "facts_missing"
            if mode == "judge":
                question = next((holdout.message_text(m) for m in reversed(original)
                                 if isinstance(m, dict) and m.get("role") == "user"), "")
                first, second = (baseline, optimised) if _fraction(f"order\x1f{call_id}") < 0.5 else (optimised, baseline)
                judged = await asyncio.wait_for(self._complete(self.settings.judge_model, [
                    {"role": "system", "content": JUDGE_INSTRUCTIONS},
                    {"role": "user", "content": f"Request:\n{question}\n\nAnswer 1:\n{first}\n\nAnswer 2:\n{second}"},
                ], temperature=0, max_tokens=64), self.settings.timeout_s)
                verdict = parse_verdict(answer_text(judged))
            QUALITY_SAMPLES.labels(mode, verdict).inc()
            logger.info("measurement: quality check mode=%s verdict=%s facts_missing=%d", mode, verdict, len(lost))
            return verdict
        except Exception as exc:
            QUALITY_SAMPLES.labels(mode, "error").inc()
            logger.warning("measurement: quality check failed: %s", type(exc).__name__)
            return "error"


_instance: Optional[MeasurementCallback] = None


def __getattr__(name: str):
    # Built on first access (LiteLLM resolves the callback path from litellm_config.yaml), not at import.
    global _instance
    if name == "measurement_instance":
        if _instance is None:
            _instance = MeasurementCallback()
        return _instance
    raise AttributeError(name)
