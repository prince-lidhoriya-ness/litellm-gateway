"""Prometheus metrics for the context-engineering stage (served by LiteLLM's /metrics next to prompt_pipeline_*).

Low-cardinality labels only: no user, key, team, conversation or request ids.
"""

try:
    from prometheus_client import Counter, Histogram
except ImportError:  # metrics are optional for the stage itself
    Counter = Histogram = None

_BUCKETS = (0.001, 0.0025, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5)


class _Noop:
    def labels(self, *args, **kwargs):
        return self

    def inc(self, *args, **kwargs):
        pass

    def observe(self, *args, **kwargs):
        pass


def _counter(name, doc, labels):
    return Counter(name, doc, labels) if Counter else _Noop()


def _histogram(name, doc, labels, buckets):
    return Histogram(name, doc, labels, buckets=buckets) if Histogram else _Noop()


REQUESTS = _counter("context_engine_requests", "Requests seen by the context-engineering stage.", ["status", "pressure"])
TOKENS_BEFORE = _counter("context_engine_tokens_before", "Estimated prompt tokens before the stage.", ["category"])
TOKENS_AFTER = _counter("context_engine_tokens_after", "Estimated prompt tokens after the stage.", ["category"])
TOKENS_SAVED = _counter("context_engine_tokens_saved", "Estimated prompt tokens removed, by technique.", ["technique"])
SHADOW_TOKENS_SAVED = _counter("context_engine_shadow_tokens_saved",
                               "Tokens the stage would have removed in shadow mode.", ["technique"])
MASKED = _counter("context_engine_masked", "Tool outputs masked or folded.", ["reason"])
HISTORY_TURNS = _counter("context_engine_history_turns", "Older turns by history decision.", ["action"])
DURATION = _histogram("context_engine_duration_seconds", "Time spent in the stage.", ["status"], _BUCKETS)
UTILIZATION = _histogram("context_engine_utilization", "Estimated utilization of the effective target.", ["stage"],
                         (0.1, 0.25, 0.5, 0.7, 0.8, 0.9, 1.0, 1.25, 1.5, 2.0, 4.0))
FAILURES = _counter("context_engine_failures", "Stage failures by fail mode and reason.", ["mode", "reason"])
STAGE_UNDONE = _counter("context_engine_stage_undone", "Sub-stages undone after an error or invariant failure.",
                        ["stage"])
VOLATILE_PREFIX = _counter("context_engine_volatile_prefix", "Requests whose system prompt holds volatile content.",
                           ["pattern"])
BREAKPOINTS = _counter("context_engine_breakpoints_added", "Requests given cache_control injection points.", ["provider"])
PROVIDER_CACHED_TOKENS = _counter("context_engine_provider_cached_tokens",
                                  "Prompt tokens the provider served from its prompt cache (usage).", ["provider"])
PROVIDER_CACHE_WRITE_TOKENS = _counter("context_engine_provider_cache_write_tokens",
                                       "Prompt tokens the provider wrote to its prompt cache (usage).", ["provider"])
PROVIDER_PROMPT_TOKENS = _counter("context_engine_provider_prompt_tokens",
                                  "Prompt tokens reported by the provider for requests the stage saw.", ["provider"])
CONTEXT_TOKENS = _histogram("context_engine_context_tokens", "Estimated context size per request.", ["stage"],
                            (500, 1000, 2000, 4000, 8000, 16000, 32000, 64000, 128000, 256000))
RESTORED = _counter("context_engine_restored", "Originals kept in full because their ref was mentioned.", ["kind"])
COMPACTIONS = _counter("context_engine_compactions", "History compaction operations, by summary source.", ["source"])
RETRIEVAL_SCORE = _histogram("context_engine_retrieval_score", "Relevance score of retrieved older turns.", ["backend"],
                             (0.1, 0.25, 0.5, 1.0, 2.0, 4.0, 8.0, 16.0))

# Attribution: one family for every optimisation, recorded once per successful request after the provider answered, so
# the techniques never overlap. The context-engineering techniques are measured stage by stage (report
# saved_by_technique), prompt_compression is what the compression stage removed from the context-engineering output, and
# provider_cache is the prompt tokens the provider served from its cache (discounted, not removed).
ATTRIBUTED_TOKENS = _counter("gateway_optimization_tokens",
                             "Prompt tokens saved (or, for provider_cache, served from cache) by technique.", ["technique"])
ATTRIBUTED_USD = _counter("gateway_optimization_saved_usd",
                          "ESTIMATE: attributed tokens x the model's input price (cache: price minus cache-read price).",
                          ["technique"])
