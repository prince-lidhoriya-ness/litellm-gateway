# context_engineering

A context-engineering stage for every `chat/completions` request that passes through the LiteLLM proxy. It runs
**before** the existing prompt-compression hook (`prompt_compression/`) and decides what the context should contain:

- how full it is;
- which old tool outputs and turns can be represented more compactly;
- how to keep the prompt prefix byte-stable for provider prompt caching.

The compression stage then works on the result, exactly as before. The design and the reasoning behind each choice are
in [`../docs/context-engineering-blueprint.md`](../docs/context-engineering-blueprint.md).

The stage itself is pure Python. It needs no new package and makes no model call on the request path. It adds no
infrastructure: the optional shared store is the Redis the stack already runs.

## Request flow

```
Client request
  -> LiteLLM auth, limits, budgets
  -> context_engineering callback   (litellm_config.yaml: listed before the compression callback)
       gate        not chat / disabled / opt-out (metadata {"context_engineering": false}) / < MIN_TOKENS
       [redact]    only with REDACT_SENSITIVE=true: the same rules as the compression guardrail, so nothing
                   unredacted is stored or copied into a stub or summary
       engine, in a worker thread under CONTEXT_ENGINEERING_TIMEOUT_S:
         1 resolve model   window, provider, caching support          models.py
         2 analyze         categories, tokens, pinned messages         analyzer.py
         3 budget          utilization, oversized parts, techniques    budget.py       (A)
         4 cache plan      caching, freeze, JIT permission, breakpoints cache.py      (E)
         5 relocate        optional volatile system lines -> query      cache.py        (E, opt-in)
         6 mask            fold duplicates, mask old large outputs      masking.py      (C)
         7 history         re-measure; if still needed: JIT + compaction history.py   (B, D)
         8 report + hints  metadata["context_engineering"]
       each of 5-7: try/except + invariant check (validate.py); a failing stage is undone
  -> prompt_compression callback (existing; redaction guardrail, classify, select, LLMLingua-2, ratio-cap validation)
       honours hints.protected_indexes: the compaction summary is left verbatim and never dropped
  -> LiteLLM routing -> cache_control_injection_points (LiteLLM's built-in hook, for Anthropic-style providers)
  -> provider
  -> async_log_success_event: provider prompt-cache reads/writes, tokenizer calibration, metrics
```

**Why this order:**
- Masking runs before history work: it is the cheapest loss, and often enough on its own.
- History work re-measures after masking and runs only if the budget still says so.
- Compression runs last, on less text, so it makes fewer LLMLingua-2 calls.
- The two stages don't duplicate each other:
  - compression never touches tool outputs, and context engineering never touches prose inside a message;
  - compression's history route keeps working but must not drop the summary (it now skips protected indexes);
  - when context-engineering compaction is on, leave compression's `history` route off.

## Modules

| Module | Responsibility |
|---|---|
| `callback.py` | LiteLLM `CustomLogger`: gate, opt-out, optional redaction, timeout, fail open / closed, shadow mode, metadata, breakpoint injection, background summaries; success hook: provider usage, calibration, attribution |
| `engine.py` | Runs the stages in order, each isolated and validated; per-technique savings; report and hints |
| `settings.py` | Every environment variable, validated at startup |
| `structures.py` | Data passed between stages: `ModelInfo`, `ContextItem`, `ContextProfile`, `BudgetPlan`, `CachePlan`, `MaskRecord`, `HistoryRecord`, `ContextReport` |
| `models.py` | Window, provider and caching support of the target model (LiteLLM model map, proxy router) |
| `tokens.py` | Token estimates with a content-hash cache; calibration against provider usage |
| `analyzer.py` | Categories, pinned messages, tool-call graph, error outputs, prefix fingerprint, volatile content |
| `budget.py` | Effective target, category limits, pressure, oversized parts, techniques allowed |
| `cache.py` | Cache plan, breakpoints, volatile-line relocation, canonical tool order |
| `masking.py` + `extract.py` | Duplicate folding, batched masking, verbatim key-line stubs, ref restore |
| `history.py` | Turn segmentation, span selection, JIT + compaction orchestration |
| `retrieval.py` | BM25 / hybrid scoring of older turns |
| `compaction.py` | Extractive anchored summary; optional validated model-written summary |
| `store.py` | Memory / Redis / none store for originals |
| `validate.py` | Invariants checked after every sub-stage |
| `metrics.py` | Prometheus metrics, including the attribution family |
| `recover.py` | CLI: print a stored original by ref |

## Techniques

### A. Context Budget Manager (`budget.py`, `analyzer.py`, `tokens.py`, `models.py`)

**Measuring the context.**
- **Categories:** `system`, `tool_definitions`, `history`, `tool_output`, `retrieved` (JIT-kept turns and the
  summary), `current_query`.
- **Token counting:** tiktoken cl100k_base, plus 4 tokens of overhead per message, plus tool-call arguments and tool
  definitions. A per-worker LRU caches counts by content hash.
- **Window:** the model's `max_input_tokens` from LiteLLM's model map, or `CONTEXT_WINDOW_TOKENS`, or
  `CONTEXT_DEFAULT_WINDOW_TOKENS` for unknown names. Inside the proxy, model-group names are resolved to their
  deployment's model through the proxy router.

**The target.** `target = min(window − output reserve, window × CONTEXT_MAX_UTILIZATION) × (1 − CONTEXT_SAFETY_BUFFER)`.
The output reserve is the request's `max_tokens`, or `CONTEXT_RESERVED_OUTPUT_TOKENS`, capped at half the window.

**Pressure.** Utilization is estimated tokens divided by the target. Pressure is:
- `low` below 0.5 × threshold;
- `moderate` below the threshold (`CONTEXT_COMPACTION_THRESHOLD`);
- `high` from the threshold up to 1.0;
- `over` at 1.0 and above.

A category above its share of the target (`CONTEXT_BUDGET_SHARES`) is reported as *oversized*.

**What it triggers.** Duplicate folding always; masking always (or only under pressure with
`OBSERVATION_MASK_TRIGGER=pressure`); history work at `high`/`over` or when history is oversized. Every decision is
recorded in `report.decisions`. System messages, tool definitions and the current query are never reduced.

**Calibration.** The factor is the provider's `usage.prompt_tokens` divided by what was actually sent: this stage's
estimate minus what compression removed. It is applied per model, as a moving average.
- Observations outside [0.5, 3.0] are discarded. A mock reporting 1 token, a provider that excludes cached tokens, or a
  response from LiteLLM's cache would otherwise mislead it.
- The factor is applied only after 3 plausible observations.

### B. Just-in-time retrieval of older turns (`retrieval.py`, `history.py`), off by default

**How turns are split.**
- **Head (pinned):** the system block and the whole first turn.
- **Recent:** the last `CONTEXT_RECENT_TURNS` turns, always verbatim.
- **Older:** the turns in between. Only the oldest multiple of `CONTEXT_COMPACTION_BATCH_TURNS` of them is considered,
  so the span grows in steps.

A turn is a user message and everything up to the next one, so tool calls never lose their results.

**How turns are scored.** Each older turn is scored against the latest user message:
- **BM25:** `prompt_compression.selectors.rank_units`, the ranking the passages route already uses.
- **`hybrid`:** BM25 plus MiniLM cosine similarity, reusing the encoder the sensitivity check has already loaded. With
  no encoder it falls back to BM25.

At most `JIT_RETRIEVAL_MAX_TURNS` turns scoring above `JIT_RETRIEVAL_MIN_SCORE` are kept verbatim. Every other older
turn is represented in the summary: an index-level one when compaction is off, the full one when it is on. Nothing
disappears without a trace.

**Traceability.**
- Every turn has a `turn_<sha12>` ref, its original message indexes in the report, and a store entry.
- Mentioning a ref in a message keeps that turn verbatim on the next request.

**Fallback.** If scoring fails, the history is left unchanged.

**Caching providers.** On a provider that caches prompts, or one whose caching is unknown, JIT is skipped by default
(`JIT_RETRIEVAL_ON_CACHING_PROVIDERS=false`). Query-dependent selection would change the cached prefix on every request.

### C. Observation masking (`masking.py`, `extract.py`, `store.py`)

**Eligible outputs.** `tool`/`function` results with text content that are not after the last assistant message (the
current step) and not already gateway stubs.

**Duplicates.** A later byte-identical output becomes `[gateway: duplicate of observation obs_… (message #n) …]`.
The first copy stays, so no information is lost and the prefix does not change.

**Age masking.**
- Of the eligible outputs larger than `OBSERVATION_MAX_TOKENS`, the newest `OBSERVATION_KEEP_RECENT` stay in full.
- Older ones are masked in batches of `OBSERVATION_MASK_BATCH`, so consecutive requests share a byte-identical prefix
  (tested).
- Never masked:
  - error outputs among the newest `OBSERVATION_ERROR_GUARD` tool results (active debugging);
  - any output whose ref is mentioned by the latest user or assistant message (this is how a model or user asks for
    it back).

**The stub.** The role, `tool_call_id` and `name` are kept. The stub holds a header with the ref, the tool, the size and
whether the original was stored, then a JSON structure line (keys and lengths only), then **verbatim** key lines:
- error lines;
- lines naming an identifier the following assistant message mentions;
- the first and last lines.

Nothing is paraphrased. Refs are `obs_` plus the first 12 hex digits of sha256(content), so they are deterministic.

**Recovery of originals.**
- **Store by ref:** `CONTEXT_STORE=memory` (per worker) or `redis` (shared). Redis never receives content with a rules
  or topic hit unless `CONTEXT_STORE_ALLOW_SENSITIVE=true`.
- **In-conversation:** mentioning the ref restores the original on the next request.
- **CLI:** `python -m context_engineering.recover <ref>` reads the Redis store.
- **The client's own copy:** the client keeps the full original history and re-sends it, so masking never removes
  anything permanently.

### D. Context compaction (`compaction.py`, `history.py`), off by default

**Trigger.** Utilization ≥ `CONTEXT_COMPACTION_THRESHOLD`, or history over its share, after masking. Older turns that
are not protected and not retrieved are replaced, all together, by **one** user-role message at the position of the
first of them. Protected turns are those with a sensitivity rules or topic hit, or a mentioned ref.

**`extractive` (default).** No LLM call. Every line is copied verbatim from the compacted turns, in these sections:
- instructions and constraints;
- open tasks and questions;
- decisions;
- tool calls with their arguments;
- identifiers, files and values;
- code and data blocks: verbatim up to `CONTEXT_COMPACTION_VERBATIM_BLOCK_TOKENS`, larger ones referenced by turn ref;
- tool results (errors);
- turn index: refs, indexes, and the first words of the user message and of the answer.

Constraints and open tasks are never trimmed to fit `CONTEXT_COMPACTION_MAX_SUMMARY_TOKENS`.

**`llm`.** The extractive summary is used at once. A summary of the same span is requested in the background from
`CONTEXT_COMPACTION_MODEL`, through the proxy router with compression and context engineering switched off. It replaces
the extractive one on a later request only if:
- every identifier it contains occurs in the originals;
- it contains no instruction-shaped text the originals lack;
- it is shorter than the span.

The verbatim constraints and the turn index are always appended to it. Summaries are cached by the hash of the exact
span, so a span is summarized once and a summary is applied only to a request containing that span.

**Safety nets.**
- A summary bigger than `CONTEXT_COMPACTION_MAX_SUMMARY_RATIO` × the span is not used.
- A stage that breaks an invariant is undone.
- The compression stage keeps the summary verbatim (`protected_indexes`).

### E. Cache-aware prompt construction (`cache.py`, `callback.py`)

**Caching support** comes from the model-map flag (`supports_prompt_caching`):
- an explicit True is `supported` and an explicit False is `unsupported`;
- no flag at all (custom deployments, Ollama) is `unknown`;
- `PREFIX_CACHE_PROVIDER_SUPPORT` overrides all of this.

**History is frozen** (no per-question rewrites of earlier messages) unless the model is known not to cache. The
compression stage already keeps history byte-stable on its own: `PROMPT_COMPRESSION_SELECTION_SCOPE=latest_user`, plus
its cache of compressed outputs. This stage warns when that scope is `all`. Masking and compaction move in batches,
and JIT is off on caching providers.

**Breakpoints.** For Anthropic, Bedrock and Vertex providers with caching, CE adds
`cache_control_injection_points: [{location: message, role: system}]` when:
- the system prompt is at least `PREFIX_CACHE_BREAKPOINT_MIN_TOKENS` long;
- the request carries no `cache_control` of its own.

LiteLLM's own `anthropic_cache_control_hook` places the marker. OpenAI and Gemini cache automatically and get nothing
added.

**Volatile system-prompt content** (dates, times, uuids, request ids, unix timestamps) is detected and counted. With
`PREFIX_CACHE_RELOCATE_VOLATILE=true`, those lines move to the end of the latest user message.
`PREFIX_CACHE_CANONICAL_TOOLS=true` sorts tool definitions by name.

**Measurement.** The provider's cache reads (`usage.prompt_tokens_details.cached_tokens`, or
`cache_read_input_tokens`) and cache writes (`cache_creation_input_tokens`) go to metrics and logs.

### F. Context partitioning: not implemented

A proxy cannot decompose a task, run sub-agents and merge their results without becoming an agent framework. The
blueprint (§4.3) found no benefit at the proxy layer that would justify the coordination overhead.

## What the stage reports

`metadata["context_engineering"]`, and a copy with bounded lists in `spend_logs_metadata`, holds:

| Group | Fields |
|---|---|
| Outcome | `status` (ok / shadow / skipped / error) |
| Model and caching | `model`, `window`, `window_source`, `caching` |
| Tokens | `tokens_before`, `tokens_after`, `tokens_saved`, `by_category_before` / `_after` |
| Budget | `utilization_before` / `_after`, `pressure`, `oversized`, `techniques`, `decisions` |
| Masking | `masked` (index, ref, reason, tool, tool_call_id, tokens, stored) |
| History | `history` (action, ref, original indexes, tokens, score), `summary_index`, `summary_source` |
| Cache | `volatile_prefix`, `breakpoints_added` |
| Failures | `stages_failed`, `invariant_violations` |
| Timing and identity | `stage_ms`, `elapsed_ms`, `conversation_key` (salted hash), `prefix_sha` |
| Hand-off | `hints` |

It never contains message text. Log lines carry only counts and labels.

**Prometheus metrics** (served at `/metrics` next to `prompt_pipeline_*`):

| Group | Metrics |
|---|---|
| Requests and tokens | `context_engine_requests{status,pressure}`, `_tokens_before/_after{category}`, `_tokens_saved{technique}`, `_shadow_tokens_saved{technique}` |
| What was changed | `_masked{reason}`, `_history_turns{action}`, `_breakpoints_added{provider}` |
| Timing and utilization | `_duration_seconds{status}`, `_utilization{stage}` |
| Failures | `_failures{mode,reason}`, `_stage_undone{stage}` |
| Cache | `_volatile_prefix{pattern}`, `_provider_cached_tokens{provider}`, `_provider_cache_write_tokens{provider}`, `_provider_prompt_tokens{provider}` |
| Context size and history | `_context_tokens{stage}` (histogram, before / after), `_restored{kind}` (observations / turns kept because their ref was mentioned), `_compactions{source}` (extractive / index / model), `_retrieval_score{backend}` (histogram of retrieved-turn relevance) |
| **Attribution** | `gateway_optimization_tokens{technique}` and `gateway_optimization_saved_usd{technique}` (ESTIMATE: tokens × the answering model's input price from LiteLLM's model map; for the cache, input price minus cache-read price) |

**Attribution without double counting.** `gateway_optimization_tokens` is recorded once per answered request, in the
success hook, with `technique` one of:

| Technique | What is counted |
|---|---|
| `deduplication`, `masking` | Per stub: tokens before minus after |
| `compaction` (or `jit_retrieval` when only JIT ran) | The token difference across the history stage |
| `prompt_compression` | What the compression stage removed from the context-engineering output |
| `provider_cache` | The prompt tokens the provider reported as served from its cache. These are discounted, not removed, so they are not part of "tokens saved" |

Each stage works on the previous stage's output, so the parts add up to the total reduction.
`context_engine_tokens_saved{technique}` is the stage's own view at pre-call time (also recorded in shadow mode as
`_shadow_tokens_saved`). Use `gateway_optimization_*` for attribution across stages.

**Compression-side additions** (`observability/metrics.py`):
- `prompt_pipeline_validation_rejects{label}`: blocks that the ratio-cap validation rejected and left as they were.
- `prompt_pipeline_compress_stopped{reason}`: compression that stopped early at its deadline or call cap and sent the
  rest unchanged.

These sit next to the existing `prompt_pipeline_failures{mode,reason}` (fail open or closed).

**Dashboard:** `monitoring/grafana/dashboards/gw-context-engineering.json`, generated by
`monitoring/grafana/build_dashboards.py`. It shows:
- tokens saved and estimated USD by technique;
- provider cache hit rate;
- context size and utilization p50 / p95;
- preparation latency and end-to-end latency at p50 / p90 / p95;
- masked, folded and restored counts;
- history decisions and compactions;
- retrieval relevance and the pressure mix;
- compression validation rejects, early stops and fallbacks;
- a Loki panel of the stage's log lines.

## Configuration

Every variable, its default and its meaning: [`../context_engineering.env.example`](../context_engineering.env.example).
Feature flags:

- `CONTEXT_ENGINEERING_ENABLED`
- `CONTEXT_BUDGET_ENABLED`
- `OBSERVATION_MASKING_ENABLED`
- `JIT_RETRIEVAL_ENABLED`
- `CONTEXT_COMPACTION_ENABLED`
- `PREFIX_CACHE_OPTIMIZATION_ENABLED`

**Per-request opt-out:** `"metadata": {"context_engineering": false}` or `{"disable_context_engineering": true}`. The
compression opt-out (`"prompt_compression": false`) is separate; internal calls such as the judge or the summarizer
should set both.

**Rollout:**
1. `CONTEXT_ENGINEERING_MODE=shadow` first: everything is computed and reported, and the original is forwarded.
2. Then `enforce` with the defaults (masking only).
3. Then turn on `CONTEXT_COMPACTION_ENABLED` (and, for non-caching models, `JIT_RETRIEVAL_ENABLED`) after checking the
   reports on your own traffic.

## Running

Without Docker (from `litellm-gateway/`, venv as in `prompt_compression/README.md`):

```bash
.venv-compression/Scripts/python prompt_compression/dev/mock_openai_server.py --port 4010
# second shell; PYTHONUTF8=1 avoids a Windows console crash on LiteLLM's startup banner
PYTHONUTF8=1 MOCK_LLM_API_BASE=http://127.0.0.1:4010/v1 MOCK_LLM_API_KEY=mock LITELLM_MASTER_KEY=sk-local \
  .venv-compression/Scripts/litellm --config config.yaml --port 4000
```

With Docker: `docker compose -f docker-compose.quickstart.yml up -d`. The package is mounted like `prompt_compression/`
and `litellm_config.yaml` registers it. To run compression alone, remove the
`context_engineering.callback.context_engineering_instance` entry or set `CONTEXT_ENGINEERING_ENABLED=false`.

## Tests

```bash
cd context_engineering && LITELLM_LOCAL_MODEL_COST_MAP=True ../.venv-compression/Scripts/python -m pytest -q
```

| File | Covers |
|---|---|
| `test_settings_budget.py` | feature flags, threshold parsing and validation, token estimation, calibration, model-map windows and caching, budget target, pressure, oversized parts, triggers |
| `test_masking.py` | batches and hysteresis, byte-identical prefixes, determinism, refs, tool-call pairing, verbatim key lines, JSON structure, duplicates, current step, error guard, ref-based restore, store recovery, Redis sensitivity rule, multi-part content |
| `test_history.py` | turn segmentation, compaction span and batch, verbatim constraints, decisions, tasks and code, recovery, ref restore, sensitive turns, ratio fallback, JIT relevance, limits and threshold, JIT on caching providers, retrieval failure, hybrid scoring, llm mode, summary validation, size cap |
| `test_cache_validate.py` | caching support, freeze, JIT permission, breakpoints per provider, existing cache_control, volatile detection and relocation, canonical tools, compression-scope warning, every invariant |
| `test_engine.py` | stage order, flags, input never mutated, stage failure and invariant undo, determinism, idempotence, cross-request prefix stability, breakpoints, llm-mode scheduling |
| `test_callback.py` | gate, opt-outs, shadow, metadata without text, bounded spend log, fail open, timeout, fail closed, init failure, breakpoint injection, redaction before storage, provider cache usage and calibration, LiteLLM hook requirements |
| `test_integration.py` | CE + the real compression callback (stub models): summary kept verbatim, disabled CE equals compression alone, structured data and tool payloads byte-identical, five model configurations, failure isolation, history route, LiteLLM's own `ProxyLogging.pre_call_hook` loop, the proxy's config loader, config and compose wiring |
| `test_attribution.py` | per-technique savings add up to the stage total, compaction vs JIT credit, retrieved / restored counts, success-hook attribution once per request (shadow and skipped cases), model-map prices |

`prompt_compression/tests/test_context_hints.py` covers the compression side of the hint.

**Benchmark:** `../reports/context-engineering/REPORT.md` (four configurations, 46 items; scripts and raw rows next
to it).

## Known limitations

- **Token estimates** are cl100k_base. Non-OpenAI tokenizers differ, which the calibration factor and the safety buffer
  absorb. The window comes from LiteLLM's model map, which can lag new models: set `CONTEXT_WINDOW_TOKENS` when it does.
- **Extractive compaction** keeps instructions, decisions, tasks, identifiers and small code verbatim. It drops ordinary
  explanatory prose of older turns, which is recoverable by ref. The sentence patterns are English-only heuristics, and
  "open tasks" has false positives (a sentence containing "unresolved").
- **`llm` compaction** makes one background model call per new span. Its cost is not counted against the caller's
  budget. Use a local model (the default config has `obs-priced-llama`) to keep text inside the host.
- **The memory store** is per worker: a ref stored by one worker is not readable by another, or by `recover.py`. Use
  `CONTEXT_STORE=redis` for a shared store. The client's own copy of the history is always the ground truth.
- **Breakpoint injection** is verified up to LiteLLM accepting the request key (unit test, and LiteLLM's own hook code).
  It has not been verified against a live Anthropic or Bedrock endpoint here (no key available).
- **Inserted user-role messages.** The compaction summary is a user-role message. Providers that require strictly
  alternating roles get two consecutive user messages, which LiteLLM merges for Anthropic.
- **The `Dockerfile` does not need changes** (no new packages). The image build itself was not rerun here.
