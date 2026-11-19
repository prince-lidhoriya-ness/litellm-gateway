# LiteLLM Gateway: remediation strategy for the production-readiness audit

| | |
|---|---|
| Input | `reports/production-readiness-audit/REPORT.md` (2026-11-18), checked against the code at `d3a36e5` |
| Scope | Every finding (C1, H1–H7, M1–M8, L1–L4) plus three issues the audit did not list (N1–N3, §0) |
| Approach | Each recommendation names the code that causes the problem, the change, and what it costs |

---

## 0. Summary

**The core problem is one mistake in design, not a long list of bugs.** The gateway applies **query-dependent, lossy, silent** removal (`records` and `passages` selection, age-based masking) by default. It also gives most of its CPU budget to the one stage that saves the least (LLMLingua-2 on prose). The fix is to change the order of preference:

1. **Lossless, query-independent reductions first.** Duplicate folding, log template folding and pressure-only masking. These are deterministic, cache-stable, and do not depend on how the question is worded.
2. **Lossy reductions only when the context does not fit** (a budget need, not a savings goal). They must be visible to the model (omission markers) and checked by a fidelity guard that reverts them per unit.
3. **Token-level compression (LLMLingua-2) leaves the synchronous default path.** It stays available as an opt-in, out-of-process, identifier-safe stage.

That one change resolves or reduces C1, H1, H3, H4, H5, M3, M7 and M8 together. The remaining findings (H2, H6, M1, M2, M4–M6) are separate and mostly about configuration or measurement.

### Issues the audit did not list (found while checking the code)

| ID | Finding | Evidence | Severity |
|---|---|---|---|
| **N1** | **The EKS image does not contain the gateway code.** The `Dockerfile` installs packages and model weights but never `COPY`s `prompt_compression/`, `context_engineering/` or `observability/`. Compose bind-mounts them (`docker-compose.quickstart.yml`, the `volumes:` block). `k8s/deployment.yaml` mounts only `config.yaml`, and `docs/aws-eks-deployment.md:48` builds that same Dockerfile. As written, the proxy on EKS cannot import its callbacks. | CODE | Critical (deploy) |
| **N2** | **EKS runs in `enforce` mode with every default lossy route on.** `k8s/configmap.yaml` sets no `PROMPT_COMPRESSION_*` or `CONTEXT_ENGINEERING_*` variables, so the code defaults apply: `mode=enforce`, routes `narrative,passages,records`, `mask_trigger=always`. The audit's own verdict says this is unsafe for production. | CODE | High |
| **N3** | **Store health changes stub bytes, and so breaks the prefix cache.** `masking.build_stub` (`context_engineering/masking.py:68`) writes `original stored` or `original not stored` into the stub header. If Redis flaps, the same observation produces a different stub and every later token misses the provider cache. The store is also never needed for correctness. The client resends the full history, and recovery by mentioning a ref works by simply *not masking* that message on the next request (`masking.requested_refs`). | CODE | Medium |

---

## 1. Proposed solutions, by finding

### C1. Record and passage selection deletes the answer silently

**Cause in code.** `unit_selectors.select_records` keeps lines that contain a question identifier, plus `context_lines=1` neighbours on each side (`settings.py:173`). `actions._select_records` (`actions.py:74`) writes back only the kept lines: no marker, no copy. An identifier is "any token with a digit, `_`, `-` or `.`" (`_query_identifiers`, `unit_selectors.py:102`), so `503` qualifies and `checkout` does not. That is why the outcome flips with the wording of the question.

**Solution: replace "keep what matches" with "fold what repeats" for logs, and make any remaining selection evidence-aware, marked and guarded.**

1. **New default for logs and CI output: log template folding (lossless in intent, independent of the question).**
   * Normalise each line to a template by masking timestamps, hex ids, UUIDs, numbers and quoted values (a Drain-style template; about 100 lines of plain Python, no model).
   * Collapse runs of consecutive lines with the same template into one representative line plus a marker: `[gateway: 37 similar lines folded, template "GET /api/orders/<*> 200 <*>ms", first 10:02:11, last 10:04:58]`.
   * Never fold a line that matches the severity pattern already in `context_engineering/extract.py` (`_ERROR_LINE`: ERROR, FATAL, Exception, Traceback, exit code ≠ 0, and so on). Never fold the first or last occurrence of a template.
   * Why: CI and service logs are dominated by repeated templates. Folding saves on case D, where selection saved 0%, and does not depend on the question. Case C keeps the DB-pool line because it is an ERROR line. The output is byte-stable for a given log, which suits the prefix cache.
2. **Identifier selection becomes an opt-in second step, used only when folding is not enough to fit the budget.** When it runs:
   * Keep every severity line and its ±3 neighbours, whatever matches.
   * **Correlation expansion, one hop.** From the matched lines, take the other identifiers they carry (trace ids, request ids, the order's payment id) and keep every line that shares one. This is how a human follows `ord-7731` → `pay-…` → `db-pool`.
   * Keep a time window around the matches, ±N seconds when lines have timestamps, instead of a fixed number of lines.
   * Raise `record_context_lines` to 3.
3. **Omission markers, always.** Every dropped span is replaced by one line, for example `[gateway: lines 41–118 omitted (78 lines, 3,120 tokens); kept: lines matching ord-7731, all ERROR/WARN lines ±3. Ask the user for the full log if the answer is not here.]`. Passages get the same treatment: `[gateway: 5 of 12 passages omitted: "Billing", "Appendix B", …]` (the first heading or the first 8 words of each).
4. **Add a diagnostic intent (see M3).** A question that asks *why* or about a failure never triggers selection.
5. Change the default `DEFAULT_ROUTES` (`settings.py:23`) to `narrative` only until the fidelity guard (H4) is live. Then add `logfold` as a new default route, and keep `records` and `passages` opt-in per team.

**Trade-offs.** Folding saves less than selection on "find one id" lookups (perhaps 40–70% instead of 98%). That is the right trade: the 98% figure came with a 1/5 key-fact rate. Markers cost about 30–60 tokens. Correlation expansion can keep more lines than needed on chatty logs; the budget check decides whether a lighter step runs.

### H1. Masking runs without budget pressure, and the model cannot recover

**Cause.** `mask_trigger="always"` (`context_engineering/settings.py:115`, read in `budget.py:70`) makes masking unconditional. The stub (`masking.py:81`) tells the model to "mention obs_…", which a model inside a single completion cannot do. In case H the stub carried no value, and the model invented one.

**Solution.**
1. **Default `OBSERVATION_MASK_TRIGGER=pressure`.** Mask only when `tool_output` is over its share or pressure is `high`/`over`. Case H, at 14% utilisation, is then untouched.
2. **An anti-fabrication sentence in every stub:** `Values not shown above are unknown to you; do not guess them. Re-run the tool (same arguments) if you need them.` The stub already says "call the tool again". Making the *don't guess* part explicit addresses the failure mode that matters, which is a plausible wrong value. It is cheap and deterministic.
3. **Richer key lines.** Add lines that contain a key named in *any* later user or assistant message, not only the first follow-up (`_follow_up`). Recompute only when a new mask batch is created, so stubs stay byte-stable.
4. **Measure loss directly:** a `gateway_ce_refetch_total` counter. It increments when a tool call after masking has the same `(name, arguments)` as a masked observation. A rising re-fetch rate means masking is too aggressive.
5. **Optional, phase 4: a gateway-resolved `gateway_expand(ref)` tool, non-streaming only, opt-in per key.** The gateway has the original in the *current request*, so it needs no store. The flow:
   * `async_post_call_success_hook` sees a response whose only tool call is `gateway_expand`.
   * The gateway re-issues the call with that one observation unmasked.
   * The extra call shows up in the usage it reports.

   Trade-offs: adding a tool definition changes the cached prefix, so inject it into every request for that key, not only when masking ran. It also doubles latency on the turns that use it. Streaming needs `async_post_call_streaming_iterator_hook` buffering, so leave streaming out.

### H2. Token reduction is reported as if it were cost reduction

**Cause.** `TOKENS_SAVED` and `ATTRIBUTED_USD` (`context_engineering/callback.py`, `_attribute`) multiply estimated tokens by the list price. Masking churn that pushes up cache writes is never subtracted.

**Solution.**
1. **A holdout randomised by conversation, not by request.** Hash `conversation_key` (already computed in `analyzer`) into an arm. Send 5% of conversations entirely unoptimised (shadow for both stages). Prefix caching is per conversation, so a per-request split mixes the arms inside one cache and biases the result.
2. **Report billed cost from LiteLLM's `response_cost`** (`standard_logging_object["response_cost"]`, which already accounts for cached and cache-write tokens on supported providers). Compare **cost per conversation** and **p50/p95 latency** between arms. Retire `ATTRIBUTED_USD` as the headline; keep it only as a diagnostic.
3. **Per-provider policy (R6).** For `BREAKPOINT_PROVIDERS` (`cache.py`), when the client sends its own `cache_control`, apply masking only at pressure `over` (needed to fit), never to save. For automatic-prefix providers (OpenAI, Gemini), pressure-trigger masking is enough.

**Trade-off.** 5% of traffic gets no savings. This is the only way to produce a defensible dollar figure.

### H3. LLMLingua-2 corrupts exact strings

**Cause.** LLMLingua-2 joins word-pieces and adds spaces around `-`, `_` and `.` (`NIMBUS - 5044`, `3. 11. 4`). `force_reserve_digit=True` (`compressor_adapter.py`) keeps the digits but not their spacing.

**Solution: identifier-safe span splitting, then a byte-exact check.**
1. Before compressing a prose run, cut it at identifier spans: `extract.identifiers` patterns plus ISO dates, semantic versions, `UPPER_SNAKE`, `kebab-ids` and `x.y` section numbers. Send only the text *between* spans to the model, and re-join with the spans byte for byte. Identifiers never reach the model, so they cannot be corrupted.
2. Post-check: every identifier in the input run must appear byte-exact in the output. If one does not, discard the compression of that run and keep it as it was. Count each case in `gateway_pc_fidelity_revert_total{reason="identifier"}`.
3. Do not use placeholder substitution (swapping ids for `@@1@@`). LLMLingua-2 drops or splits placeholders unpredictably.

**Trade-off.** Slightly lower ratios, because the model sees shorter pieces. More calls per run can be batched into one `compress_prompt` call with a list of texts.

### H4. No quality validation, adaptive rate or fallback

**Solution: a fidelity guard after each lossy action, with per-unit revert. A single new module, `fidelity.py`, shared by both stages.**

For every unit that a lossy action changed (compressed, selected or folded):

1. Compute `R`, the "must-survive" strings of the *removed* text:
   * identifiers and numbers with units;
   * every severity line;
   * any string from `R` that also appears in the latest user message, the system prompt or the last two assistant turns. These are the referenced strings.
2. If a referenced string is missing from the output:
   * compress: retry once at `min(1.0, rate + 0.25)`;
   * otherwise, or on a second failure: **revert that unit only**. The rest of the request keeps its savings.
3. Emit `fidelity_checked`, `fidelity_retry` and `fidelity_revert` counters per action, in metrics and in the metadata report.
4. **A sampled quality check.** On 1% of enforce-mode requests, `async_log_success_event` (off the request path) asks a paid judge model whether the optimised and original prompts give equivalent answers, or does a cheaper string-match check for key facts. The result goes to a `quality_delta` metric. Replace the free OpenRouter judge (L2) first.

**Trade-off.** It adds a few milliseconds of regex work per lossy unit, and some savings are given up. Per-unit revert keeps most of them.

### H5. Savings and latency depend on load

**Cause.** CPU LLMLingua-2 inside each proxy worker, with `max_concurrency=4` and `busy`-skip (`prompt_compression_callback.py`, `_admit`). Cold calls take 2–9 s.

**Solution, in order of preference.**
1. **Take LLMLingua-2 off the default synchronous path** (see §3). After C1 is fixed, most savings come from folding, deduplication and pressure masking. All three are pure Python and take milliseconds.
2. Where a team opts in to `narrative`, run the compressor and the sensitivity encoder in a **separate inference service**: ONNX Runtime int8 export of the BERT-base token classifier, a small batching server, optionally on GPU. The proxy keeps admission and fail-open behaviour, with an HTTP call under the existing deadline. Proxy workers stop paying about 1 GB of RAM per model copy (compose comment, `mem_limit`), and the inference pool scales on its own queue depth.
3. **Precompress earlier turns asynchronously.** After a response is logged, compress the user turn that has just become history and put the result into the existing LRU (`compressor_adapter._cache`), or into a shared Redis cache keyed by `(sha, rate, model_rev)`. The next request then gets a cache hit, with no compression on the critical path. Without a shared cache, the per-worker LRU misses on cross-replica requests.
4. Alert on `skipped:busy`. Size to peak load, not average.

### H6. No tiers, failover or per-team controls in version control

**Solution.** Move model definitions to GitOps. Keep `STORE_MODEL_IN_DB` for keys, teams and budgets, but not models. Define:

```yaml
model_list:                         # each tier: >= 2 independent deployments (provider or region)
  - model_name: tier-fast           # e.g. a small hosted model, region A
    litellm_params: {model: ..., rpm: ..., tpm: ...}
    model_info: {max_input_tokens: 128000}       # required for every deployment (see M2)
  - model_name: tier-fast           # same group, second provider/region
    ...
  - model_name: tier-standard ...
  - model_name: tier-reasoning ...
router_settings:
  routing_strategy: simple-shuffle   # with rpm/tpm weights; latency-based once measured
  fallbacks: [{"tier-standard": ["tier-fast"]}, {"tier-reasoning": ["tier-standard"]}]
  context_window_fallbacks: [{"tier-fast": ["tier-standard"]}]
  content_policy_fallbacks: [...]
```

Per team: a virtual key with a `models` allowlist (the tiers), plus `max_budget`, `budget_duration`, `tpm_limit` and `rpm_limit`. Use team-level metadata to choose the optimisation profile (§3.4).

Test failover in CI against `obs-mock` plus a fault-injecting mock that returns 500, 429 or a timeout.

### H7. Placeholders and incomplete evidence in the project's own report

Do not cite `reports/context-engineering/REPORT.md` until it is completed with:
* the conversation-randomised holdout (H2);
* the fidelity counters (H4);
* a quality run on at least one production-tier model, n ≥ 200 per workload class.

Until then, remove the `QUALITY_SECTION`, `CACHE_SECTION` and `VALIDATION_SECTION` placeholders or mark them "not measured".

### Medium and low findings

| ID | Solution | Trade-off |
|---|---|---|
| **M1** CE store outage slows every request | Default `CONTEXT_STORE=none` on the request path. The store is not needed for correctness (N3). If Redis is wanted for the recovery CLI: write fire-and-forget on one background thread with a bounded queue (drop when full), a circuit breaker (open after 3 failures, half-open after 30 s), and a 50 ms socket timeout instead of 0.5 s (`store.py:81,85`). **Remove `stored` / `not stored` from the stub header** (N3). | The CLI recovery (`recover.py`) is best-effort. It already was. |
| **M2** Unknown models get a 32k window; window taken from the first deployment | `models._router_model` (`models.py:33`): use the **minimum** `max_input_tokens` across all deployments in the group and across its `context_window_fallbacks` targets. At startup, fail if any deployment lacks `model_info.max_input_tokens` and the model map does not know it. Log `window_source=default` as a warning metric. | A group is sized by its smallest member, which is the safe choice. |
| **M3** The intent gate is a keyword list | Three intents instead of two: `lookup`, `diagnose` (why, fail, error, root cause, wrong, broke, debug, investigate, crash, slow) and `transform`. **Selection runs only on a positive `lookup`**: the question names an identifier that matches ≤ 30% of units *and* has no diagnose or transform term. Everything else is `transform`, the conservative default. Do not use an ML intent model: a lexical gate whose default is safe is more predictable, and the mistake it makes (a missed saving) is cheap. | Fewer selections, which is intended. |
| **M3b** "Extract all …" was labelled sensitive and saved 0% | The `topics.py` and `rules.py` hits are correct to protect. Add a regression case to `eval/` so the sensitive / not-sensitive behaviour is pinned. | None |
| **M4** Sticky model-load failure; liveness ignores model state | `compressor_adapter.load` (`compressor_adapter.py:60-71`): replace the permanent `_load_error` with retry and exponential back-off (1 s → 5 min cap). Each worker writes `/tmp/gw-ready/<pid>` once its models are loaded. Add a k8s `startupProbe` plus an exec readiness probe that requires `NUM_WORKERS` marker files, plus a `gateway_model_loaded{model}` gauge. Liveness stays on `/health/liveliness`: a dead compressor fails open, so the pod should not be killed. | Slightly more complex probes. |
| **M5** Response cache has no per-team scoping | Keep `mode: default_off`. Before any team enables it, confirm on 1.106 whether the cache key includes the key or team. If not, set a per-team namespace in a pre-call hook (`data["cache"]["namespace"] = team_id`) **and verify it**. Move the cache to its own Redis database or instance, separate from rate limits and router state. | One more Redis endpoint. |
| **M6** Debug settings in the committed config | Split the config: `litellm_config.base.yaml` + `overlays/{dev,prod}.yaml` (or kustomize). Prod sets `turn_off_message_logging: true` and `require_auth_for_metrics_endpoint: true`. A CI test loads the prod overlay and fails if either is false. | One more file. |
| **M7** CE throughput under concurrency | The engine calls `analyzer.analyze` up to 4 times per request (`engine.py`: `profile`, inside `run_mask`, `after_mask`, `final`). Re-analyse only the messages that changed (an incremental profile keyed by message index and sha). Pass the per-message token counts to the compression stage through `hints` instead of re-tokenising in `gate.size_check`. | Moderate refactor; covered by the existing test suites. |
| **M8** HPA on CPU, 120 s model load | `startupProbe` (failureThreshold × period = 180 s) instead of `initialDelaySeconds`. Scale on custom metrics through the Prometheus adapter (in-flight pipelines, busy-skip rate, p95 latency), not CPU. Once LLMLingua leaves the proxy, CPU scaling is fine again for the proxy, and the inference service scales on queue depth. | Needs prometheus-adapter. |
| **L1** `cl100k_base` for every model | Keep the estimate plus calibration (it is already labelled). Key calibration by the *resolved* model. Report `estimate/provider` drift as a metric. | None |
| **L2** Free judge model | Point at a paid or self-hosted deployment before H4's sampled judge goes live. | Cost of about 1% of traffic. |
| **L3** No load or soak tests | Nightly: k6 or Locust against `obs-mock` at 1/8/32 concurrency for 30 min. Assert p95 overhead and zero 5xx; assert that busy-skip stays under target. | CI minutes. |
| **L4** Volatile system prompts break caching | Keep relocation off by default; it changes the prompt. Alert when `VOLATILE_PREFIX` fires for a key with `cache_control` and route that team to the owners. Turn `canonical_tools` on for agent profiles: it only reorders, and the change is safe. | None |

---

## 2. Implementation strategy (prioritised)

Each phase has an exit criterion. Do not start the next phase before it is met.

### Phase 0: make it deployable and safe (days 1–3)

| Step | Change | Why first |
|---|---|---|
| 0.1 | `Dockerfile`: `COPY prompt_compression context_engineering observability /app/` (N1). Keep the compose bind mounts for development only. | Without it EKS cannot start the callbacks. |
| 0.2 | `k8s/configmap.yaml`: `PROMPT_COMPRESSION_MODE=shadow`, `CONTEXT_ENGINEERING_MODE=shadow`, `PROMPT_COMPRESSION_ROUTES=narrative`, `OBSERVATION_MASK_TRIGGER=pressure`, `CONTEXT_STORE=none` (N2, C1, H1, M1). | Removes every default-on silent loss on day one. Shadow mode still produces the data for phase 2. |
| 0.3 | Prod config overlay with `turn_off_message_logging: true` and `require_auth_for_metrics_endpoint: true`, plus the CI assertion (M6). | Privacy before real traffic. |
| 0.4 | Remove `stored` / `not stored` from the stub header (N3). | A one-line change that stops cache churn. |

**Exit:** the image starts on a staging EKS namespace, all 393 tests pass, and shadow metrics flow.

### Phase 1: correctness of what is lossy (weeks 1–2)

| Step | Change |
|---|---|
| 1.1 | Omission markers in `_select_records` and `_select_passages`. Make them the only output form of a selection (C1.3). |
| 1.2 | `fidelity.py` with per-unit revert and counters (H4), wired into `actions.execute` after every action. |
| 1.3 | Identifier-safe span splitting in `_compress` plus a byte-exact post-check (H3). |
| 1.4 | Three-way intent with a conservative default (M3). |
| 1.5 | Log template folding as a new `logfold` route (C1.1). Selection gains severity retention, correlation expansion, a time window and `record_context_lines=3` (C1.2). |
| 1.6 | Stub anti-fabrication sentence and richer key lines (H1.2–3). Add the `refetch` counter (H1.4). |
| 1.7 | Rerun `exp2`, `exp6`, `exp7` and `exp8` from the audit as **regression tests**: the root cause kept at every distance, identifiers byte-exact, case H answered without invention. Add them to CI. |

**Exit:** the audit's failure cases C, H, G and J pass on the 3B model *and* on one production-tier model, and `fidelity_revert` is under 5% of lossy units in shadow.

### Phase 2: measurement before claims (weeks 2–4, overlapping)

| Step | Change |
|---|---|
| 2.1 | Conversation-randomised holdout plus `response_cost`-based reporting (H2). |
| 2.2 | Sampled LLM-judge quality check on a paid judge (H4.4, L2). |
| 2.3 | Two weeks of shadow on real traffic. Join the would-have-saved figures with provider usage, per team and per workload class. |
| 2.4 | Complete or retract the CE report sections (H7). |

**Exit:** a per-team table of billed cost per conversation, p95 latency and quality delta, holdout against treatment. **Only now** turn on `enforce`, per team, through profiles (§3.4).

### Phase 3: capacity and routing (weeks 3–6)

| Step | Change |
|---|---|
| 3.1 | GitOps model tiers, fallbacks, `context_window_fallbacks`, per-team keys and budgets, and a fault-injection test (H6). |
| 3.2 | Group-minimum window resolution plus the startup check for `max_input_tokens` (M2). |
| 3.3 | Model-load retry, readiness marker, `startupProbe` (M4, M8). |
| 3.4 | Separate the response cache from rate limits; check the team scoping of the cache key (M5). |
| 3.5 | For teams that enable `narrative`: an ONNX int8 inference service plus async precompression into a shared cache (H5). Otherwise, remove the model from the proxy image. |
| 3.6 | HPA on custom metrics; nightly soak test (M8, L3). |

### Phase 4: optional improvements (after phase 2 data)

* Merge both hooks into one optimiser (§3.2).
* A `gateway_expand` tool for non-streaming agent keys (H1.5).
* Incremental analysis in CE (M7).
* Decide on the sensitivity classifier from the data (§3.3).

---

## 3. Architectural improvements

### 3.1 Target pipeline

```
request
  │
  ├─ [guardrail] redaction (REDACT_SENSITIVE) ────────────── fail-closed, always first, unchanged
  │
  ├─ [gate] chat? enabled? opt-out? size? profile(team/key) ── cheap, on the event loop
  │
  ├─ [lossless, query-independent]  ← always, when enabled
  │     dedupe identical tool outputs (pointer, earlier copy stays)
  │     log template folding (severity lines never folded)
  │     canonical tool order (agent profile)
  │
  ├─ [budget] utilisation vs group-minimum window
  │     fits?  ──────────────────────────────────────────────── forward
  │     doesn't fit / pressure high ▼
  │
  ├─ [lossy, pressure-only, cheapest loss first]
  │     1. mask old large tool outputs (batched, byte-stable stubs + "don't guess")
  │     2. evidence-aware record / passage selection (lookup intent only) + omission markers
  │     3. history compaction (extractive), JIT (non-caching providers only)
  │     4. LLMLingua-2 on prose (opt-in profile, remote service, identifier-safe)
  │     each unit → fidelity guard → retry lighter → revert unit
  │
  ├─ [cache] breakpoints for Anthropic-style providers (unchanged)
  │
  └─ provider call (router: tier group → deployments → fallbacks / context_window_fallbacks)
        │
        └─ async_log_success_event: response_cost, cached tokens, calibration,
           holdout arm, fidelity + refetch counters, 1% judge sample
```

Two principles drive the ordering. First, **savings come from the lossless layer; the lossy layer exists to make a request fit, not to cut cost.** Second, **anything that depends on the question runs only on the latest user message and only on a positive lookup intent.** That is what makes behaviour predictable across wordings and keeps the provider prefix stable.

### 3.2 Hooks: one orchestrating hook instead of two coupled ones

Today the CE and compression hooks are two `CustomLogger`s whose order is a YAML list (`litellm_config.yaml` `callbacks`). They talk through `metadata["context_engineering"]["hints"]`. Each tokenises, deep-copies and enforces its own timeout and fail mode.

**Recommended (phase 4):** keep `context_engineering/` and `prompt_compression/` as libraries, and register **one** `gateway_optimizer` hook that:
* parses and tokenises once, then passes one `Profile` to every stage;
* runs the stages in the code-enforced order of §3.1 under **one** deadline and **one** fail mode;
* uses the fidelity guard from both stages;
* writes one metadata report (`gateway_optimization`) with stable keys for dashboards. Keep the old keys for a release.

Use these LiteLLM hook points:

| Hook | Use |
|---|---|
| `async_pre_call_hook` | The optimiser (as now) |
| `async_post_call_success_hook` | Optional `gateway_expand` resolution (non-streaming) |
| `async_log_success_event` / `async_log_failure_event` | Accounting, calibration, holdout, judge sampling (as now, extended) |
| Built-in `cache_control_injection_points` | Keep (already used) |
| Router `fallbacks` / `context_window_fallbacks` | Replace any temptation to "compress harder" when a request does not fit: send it to a larger window instead |

Trade-off: a medium refactor. The existing invariants in `validate.py` and the 393 tests are the safety net. Do it after phase 2, so the merge does not hide behaviour changes that the measurement should see.

### 3.3 Component decisions: keep, change or remove

| Component | Decision | Reason |
|---|---|---|
| **LLMLingua-2** (`compressor_adapter.py`) | **Demote**: off the default path; an opt-in profile on a remote ONNX service with identifier-safe splitting | The project's own settings comment says prose-only compression saved 11% (QA) and 0% (logs). It costs 2–9 s of cold CPU, depends on load, and corrupts identifiers. The best value per CPU-second is elsewhere. |
| **BM25 record / passage selectors** (`unit_selectors.py`) | **Keep the code, change the role**: pressure-only, lookup-only, evidence-aware, marked, guarded | BM25 is cheap and deterministic. The danger was silent deletion by default, not BM25 itself. |
| **Log template folding** | **Add** (new route `logfold`) | Question-independent and cache-stable. Saves on exactly the workloads (CI, service logs) where selection either saved nothing or broke the answer. |
| **Intent gate** (`intent.py`) | **Change**: three-way, default to `transform` | A safe default beats a longer keyword list. |
| **Sensitivity classifier** (MiniLM + LR head) | **Keep for now, then re-evaluate** | It guards lossy compression of personal facts, which is a fidelity concern. With LLMLingua-2 off by default and selection pressure-only, far fewer units reach a lossy step, so its value drops. In phase 2, measure rules plus topics alone against the model on `eval/sensitivity_*`. If the recall gap is under about 2 points, remove the model from the proxy and save about 0.5 GB per worker and the 300 ms budget. |
| **Deterministic rules / topics** (`rules.py`, `topics.py`) | **Keep unchanged** | Cheap, auditable, and the base of the redaction guardrail. |
| **Observation masking** | **Keep, change the trigger to pressure, fix the stub** | Sound design (batches, verbatim key lines, error guard). Only the trigger and the stub wording are wrong. |
| **Duplicate folding** | **Keep, always on** | Lossless; the earlier copy stays. |
| **Compaction / JIT** | **Keep off by default** | No data yet. Enable per profile after phase 2 shows quality parity. |
| **Context store** | **Default `none`; Redis optional, async, behind a circuit breaker** | Not needed for correctness (N3). It blocked the request path (M1). |
| **Cache planner and breakpoints** (`cache.py`) | **Keep** | Correct and conservative. |
| **Prompt-compression response cache (LRU)** | **Keep; add an optional shared Redis tier for async precompression** | Makes earlier-turn compression free on the critical path. |

### 3.4 Optimisation profiles per team or key (replaces global env switches)

The audit's main scenario is several teams with different workloads, and global env variables cannot express that. Read a `gateway_profile` from key or team metadata (LiteLLM `metadata` on the key or team) and map it to settings:

| Profile | Lossless | Masking | Selection | LLMLingua-2 | Typical team |
|---|---|---|---|---|---|
| `safe` (default) | on | pressure | off | off | Backend, DevOps, agents |
| `chat` | on | pressure | passages (lookup only) | opt-in | General chat, Ticket |
| `aggressive` | on | pressure | records + passages | on (remote) | Batch summarisation with a measured quality delta |
| `off` | – | – | – | – | Judges, evals, regulated flows |

The env variables stay as **upper bounds**: a profile can never enable a route the environment has disabled. Operations keeps a single kill switch.

---

## 4. Things that must never change

These are guarantees the current code enforces and the strategy depends on. Any change that weakens one is a release blocker, whatever it saves.

### Message integrity
1. **System and developer messages are never modified by a lossy step.** `validate.py`; `PRESERVED_ROLES` in `pipeline.py`. Volatile-line relocation stays opt-in and stays the only exception.
2. **The latest user message is never reduced by context engineering. Its first and last paragraphs are never compressed** (`protect_edges`).
3. **Tool calls and tool results stay paired. Roles and message order are preserved. `tool_call_id` and `name` survive masking.** `validate.check` runs after every stage, and a violating stage is undone.
4. **Code blocks, structured data and identifier-dense text never go to token-level compression** (`router.py`).
5. **Non-text content parts (images, audio), tool definitions and every request field other than `messages` stay untouched by compression.** Tools may only be reordered under `canonical_tools`.
6. **Nothing invented enters the context.** Stubs, summaries and markers contain only verbatim lines from the input plus gateway-labelled metadata (`extract.py`'s determinism rule). No LLM paraphrase on the synchronous path.

### Failure behaviour
7. **Fail-open forwards the original request; fail-closed returns 503. Never a half-processed request.** A stage that fails or times out is undone, not partly applied.
8. **The redaction guardrail fails closed regardless of `fail_mode`, runs before every other stage, and runs in shadow mode too.**
9. **Every optimisation is bounded**: per-request deadline, admission control (`busy` skips, never queues), a cap on compressor calls. No optimisation can make a request wait longer than its configured budget.
10. **Shadow mode sends exactly the original request** and writes no hints that change downstream behaviour.

### Determinism and cache stability
11. **The same input gives byte-identical output** (refs are content hashes, stubs are deterministic, the compression LRU replays, masks move in batches). No timestamp, store state, worker id or random value may enter prompt text (this is why N3 is fixed).
12. **Earlier turns are never re-selected against a new question** (`selection_scope=latest_user`).

### Privacy and supply chain
13. **No prompt text in logs, metrics, spans or spend metadata.** Only hashes, counts, labels and refs. `OBS_CAPTURE_TEXT` stays off in production.
14. **Text with a sensitivity hit is never sent to lossy compression, never dropped as a history turn, and never written to an out-of-process store** unless explicitly allowed.
15. **Models load at pinned revisions with `trust_remote_code=False`. The image runs offline** (`HF_HUB_OFFLINE=1`), with the base image pinned by digest.

### Control and honesty
16. **Per-request opt-out always works** (`metadata.prompt_compression=false`, `context_engineering=false`), and judge and eval traffic always uses it.
17. **Every lossy removal is visible to the model (marker) and to operations (counter).** After phase 1 this becomes a new invariant: a silent deletion is a bug.
18. **Reported savings say what they are.** Estimated tokens are labelled as estimates; dollars come only from provider-billed `response_cost` against a holdout. No claim of zero context loss, 100% reduction, or failure-free operation.
19. **Optimisation never replaces routing.** When a request does not fit, the answer is `context_window_fallbacks` to a larger window, not unbounded compression.
