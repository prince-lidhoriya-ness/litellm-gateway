# Production-readiness audit: token reduction in the LiteLLM gateway

**Date:** 2026-11-18
**Target:** `litellm-gateway` (LiteLLM 1.106.0 proxy, commit `d3a36e5`, clean working tree at start)
**Techniques audited:** prompt compression (`prompt_compression/`), provider-side caching (`context_engineering/cache.py`, `litellm_config.yaml`), context engineering (`context_engineering/`)
**Scripts and raw output:** `docs/audit-2026-11-18/experiments/` (see Appendix)

---

## 1. Verdict

**Not production-ready for multi-team traffic.** It is suitable for a pilot in shadow mode, and for enforce mode only on short, single-turn, prose-light requests with the compression route narrowed or disabled.

| Question | Answer (evidence in brackets) |
|---|---|
| Is the system genuinely production-ready? | **No.** Three Critical issues are verified: lossy prose compression changes identifiers, negations and conditions by default; the classification and compression calls cannot be interrupted, so long requests pay the full 10 s timeout for little or no benefit; and compression is serialised per worker. [Sections 2, 4, 5] |
| Is token reduction reliable across workloads? | **No. It is conditional on workload shape.** Measured: about 60% on long single-turn prose and about 60% on steady-state chat turns (through lossy compression); 0% on short prompts, code- and log-heavy requests, and requests above 32,000 tokens; 20–44% on tool-heavy agent loops, and only after about 6,700 tokens of tool output, and only from context-engineering masking. Prompt compression never touches tool results. [Section 3] |
| Does token reduction reduce output tokens? | **No, none of the three techniques does.** Output tokens were not measured against a provider and are not targeted. Response caching is opt-in per request and off by default. |
| Can it prevent or detect context loss during compression? | **No detection, no validation, no recovery.** The only quality gates are a 3.0x ratio cap and token-count gates. With the default rate of 0.4, 18 of 20 planted identifiers and facts came back altered (not verbatim), and 5 of 20 were lost outright, including a negation. [Section 2] |
| Does it recover automatically from excessive compression or context degradation? | **Partially, and only for context engineering.** Masked tool outputs keep a ref, and the original is restored when the ref is mentioned, but nothing restores it automatically and the model is not told how. Prompt compression has no recovery path. [Section 2.4] |
| Remaining risks before deployment | See the prioritised list in Section 7. The blockers are C1, C2, H1, H5, and the lack of a verified failover path (H6). |

**Credit where due.** The unit suites pass (231 prompt_compression, 20 observability, 142 context_engineering). Fail-open works: when the hook times out the original prompt is sent. Compressed outputs are cached per worker, so a warm turn costs about 100 ms against 6 s cold. The context-engineering stage is fast (under 0.5 s at 120,000 tokens) and handled 12 concurrent 20k-token requests in under 0.8 s each. Masking of old tool outputs does cut 20–60% of tokens on tool-heavy sessions, and between batch steps the byte-identical prefix is preserved (100% reuse).

---

## 2. Context preservation

### 2.1 Planted-fact survival under the production LLMLingua-2 call [VERIFIED]

`exp2_fidelity.py` builds 20 planted items, each one sentence inside a ~90-word prose paragraph, joins them, and compresses them in one call through `LLMLinguaCompressor` (the gateway's own adapter, `force_reserve_digit=True`). Survival is measured two ways: `exact` (the string appears verbatim) and `normalized` (the string appears after removing all whitespace, which separates formatting damage from information loss).

| Rate | Ratio | Exact survival | Normalized survival | Lost outright |
|---|---|---|---|---|
| **0.4 (gateway default)** | 2.52x | **2/20** | 15/20 | inline code `client.post(url, timeout=30)`, inline code `Exporter.retries`, negation "must not be deployed", bound "more than 3 times", condition "Only enable the response cache" |
| 0.6 | 1.70x | 4/20 | 19/20 | condition "Only enable the response cache" |

Identifiers are rewritten rather than dropped, which is why exact survival is far below normalized survival (18 of 20 not verbatim): `ESC-20417` became `ESC - 20417`, `184,500` became `184, 500`, `10.42.7.19` became `10. 42. 7. 19`, `2026-03-14` became `2026 - 03 - 14`, `MAX_RETRY_LIMIT` became `MAX _ RETRY _ LIMIT`, and `E_CONN_RESET_0x7f` became `E _ CONN _ RESET _ 0x7f`. A downstream consumer that expects the exact string (a grep, a config key, a copy-paste into a tool call) breaks silently.

The negation loss is the most serious item here. A reader who sees "The fix ... before the staging test has passed" without "must not" will act on the opposite instruction.

Root cause, from code:
- `prompt_compression/router.py:77-83` marks every prose unit for compression, and the segmenter only protects a paragraph when its exact-word share reaches 15% (`prompt_compression/segmenter.py:262-264`). A paragraph with one identifier is prose.
- `prompt_compression/settings.py:140` sets the default rate to 0.4. `settings.py:132` protects only the first and last paragraph of the latest user message (`protect_edges`), so the middle of the question is compressed.
- `prompt_compression/compressor_adapter.py:92` reserves digits (`force_reserve_digit=True`), but nothing reserves identifiers, negations or conditions.

### 2.2 Whole-workload check through the real hooks [VERIFIED]

`exp1_workloads.py` runs the production `ContextEngineeringCallback` then `PromptCompressionCallback` with the same `async_pre_call_hook` LiteLLM awaits, on synthetic workloads. In the lookup and summarise cases, the planted `ESC-20417` and `184,500` were rewritten or lost (see 2.1). In the code-heavy case the planted code and logs were kept byte for byte, which is correct.

### 2.3 Detection and fallback [CODE]

What exists:
- Ratio cap: `prompt_compression/actions.py:183-196`. A run that compresses more than 3.0x is retried once at a lighter rate; if it still exceeds the cap, the run is left unchanged.
- Empty or non-shrinking outputs are discarded (`actions.py:194-195`).
- Protected units: sensitive blocks, code, structured data, exact-text paragraphs, and the compaction summary (`pipeline.py` `_protected_indexes`).
- Reassembly keeps the original text if the joined result is empty (`pipeline.py:352`).

What does not exist:
- No semantic or lexical validation after compression. Nothing checks that identifiers, numbers, negations or conditions from the input still appear in the output.
- No second pass, no re-run at a higher rate when a fact is lost, and no per-message revert on quality failure.
- The "budget" caps (`max_compress_calls` 6 per message, `max_compress_calls_per_request` 12) bound cost, not quality. When the cap is reached the remaining prose is sent uncompressed, silently, and the choice depends on the order in which runs are considered (longest first; see Section 4).

### 2.4 Context engineering: masked tool outputs [VERIFIED for the stub; CODE for restore]

`exp5_gate_and_stub.py` masks a 630-token `read_file`-style tool output with the production masking code (error guard disabled so the output is eligible):

```
[gateway: observation obs_a76e59a9cac7 masked by gateway | tool=read_file | 630 tokens, 45 lines | original stored]
Key lines (verbatim):
exporter/batch.py:352: rows = read_rows(path)
exporter/batch.py:53: log.error('reset: %s', exc)
tests/test_export.py:185: log.error('reset: %s', exc)
exporter/config.py:351: resp = self.client.post(self.url, json=payload, timeout=30)
exporter/client.py:758: resp = self.client.post(self.url, json=payload, timeout=30)
exporter/config.py:716: log.error('reset: %s', exc)
tests/test_export.py:744: resp = self.client.post(self.url, json=payload, timeout=30)
[Full output omitted to save context. To restore it, mention obs_a76e59a9cac7 in a message, or call the tool again.]
```

The stub is 204 tokens against 630, and keeps 7 of 45 lines.

Consequences:
- An agent that read a file, then ten tool calls later must edit it exactly (for example, a string replacement), sees only seven lines. It must call the tool again or the edit fails.
- Restore works only when the ref appears in the latest user or assistant message (`context_engineering/masking.py:34-41`, `:137-141`). The stub's footer asks the reader to do this, but nothing in the gateway instructs the model. There is no restore tool.
- The error guard (`masking.py:130-133`) keeps any output containing words such as "error" or "exception" among the newest three tool results in full. In a debugging session that is most outputs, which costs tokens rather than losing them.
- The store (`context_engineering/store.py`, default `CONTEXT_STORE=memory`) is written on the request path (`masking.py:154-157`) but read only by `context_engineering/recover.py`. Restore through the request path re-sends the original from the client's own history, so it does not depend on the store. Per-worker memory means stored copies are lost on restart and are not shared across replicas.

---

## 3. Token reduction reliability

### 3.1 Single-turn workloads through the real hooks [VERIFIED; cl100k estimates, not provider counts]

From `exp1_workloads.py` (`exp1_results.json`). Input and output counts are cl100k_base tokens over message text and tool-call arguments, the same measure the gateway reports.

| Workload | Input tokens | After CE+PC | Reduction | Which technique | Notes |
|---|---|---|---|---|---|
| W1 short question | 9 | 9 | 0% | none | Skipped: below the 50-token gate |
| W2 long document, one lookup question | 3,673 | 1,430 | **61%** | prose compression | One LLMLingua call on a 3.7k-token run took 6.1 s cold. Intent detected as `transform` from a transform term in the document's first paragraph, so passage selection was off. |
| W3 long document, "summarise the whole document" | 3,740 | 1,440 | **62%** | prose compression | Both planted facts were rewritten or lost |
| W4 code-heavy review (fenced code, 40 log lines) | 2,190 | 2,190 | **0%** | none | Code and log lines kept verbatim (correct, and it means no saving) |
| W5 debugging session, 8 messages | 431 | 294 | 32% | prose compression | Code lines in the paragraph kept; one planted identifier rewritten |
| W6 agentic tool loop, 12 tool results of about 600 tokens | 8,070 | 6,369 | **21%** | context engineering masking only | Prompt compression: 0% (never touches tool results) |
| W7 30-turn prose chat | 5,258 | 3,098 | **41%** | prose compression | Cold cache: 12 calls stopped at the request budget (7.8 s); a second cold run stopped at the deadline after 11 calls (9.3 s) |
| W8 long prose, 28,478 tokens | 28,478 | 28,478 | **0%** | none | 9–10 s spent in classification and then the deadline or the 10 s timeout |

### 3.2 Multi-turn behaviour [VERIFIED; `exp3_multiturn.py`]

Requests were replayed as a growing conversation, one worker's state carried across turns. "Prefix reuse" is the share of the previous sent request that is still a byte-identical message prefix of the current sent request (message granularity, so a lower bound on what a token-level provider cache could reuse).

| Variant | Requests | Reduction (first to last) | Mean prefix reuse | Turns below 95% reuse | Hook wall time (median / max) |
|---|---|---|---|---|---|
| Chat, CE then PC | 24 | 47% → 63% | 87.2% (min 18.3%) | 14 of 23 comparisons | 2.9 s / 6.8 s |
| Chat, PC only | 24 | similar | 79.4% (min 0.5%) | 13 of 23 | 3.2 s / **10.5 s** (2 requests hit the 10 s timeout and were sent uncompressed) |
| Chat, CE only | 24 | 0% | 100% | 0 | < 10 ms |
| Agent loop, CE then PC | 21 | 0% → 20–44% after masking starts (about 6,700 tokens) | 87.0% (min 1.3%) | 3 of 20 (the masking batch steps) | 39 ms / 88 ms |
| Agent loop, PC only | 21 | 0% | 100% | 0 | 17 ms / 53 ms |

Interpretation:
- **Chat, steady state.** From about the 30th message on, reuse is 94–97%. The loss is always the previous latest user message. The first changed message index in every comparison is that user message. Cause: `router.py:50-52` protects the edges of the latest user message only, so on the next request that message is no longer protected and is compressed. The provider cache therefore misses from that message onward every turn.
- **Chat, early turns.** Reuse falls to 18–58% for the first few turns, while each new turn's runs are compressed for the first time.
- **Chat, timeouts.** In the PC-only run, requests 24 and 26 timed out at 10.02 s and 10.45 s and were sent raw. At request 28 the same message was compressed again, so reuse fell to 0.5%. A timeout therefore costs a later cache miss as well as the latency.
- **Agent loop, masking batches.** Masking happens in batches of four (`masking.py:145`). Between batches reuse is 100%. At each batch step reuse falls to 1.3%, 14.3% and 24.1%, because the oldest newly masked output is near the start of the conversation and everything after it changes. The batch rule reduces how often the cache is invalidated, not how much is invalidated.
- **Agent loop, prompt compression.** Prompt compression contributes nothing here: tool results are never compressed and assistant prose is under the 200-character minimum.

### 3.3 Where token usage stays flat or rises [VERIFIED unless marked]

- Below 50 tokens (`gate.py`), and below 1,000 tokens for context engineering (`context_engineering/callback.py:149-151`).
- Code, structured data, logs, and identifier-dense paragraphs: kept verbatim by design (W4 at 0%).
- Tool results under prompt compression: never compressed; under context engineering, only outputs above 400 tokens and older than the newest three, and not while an error guard applies.
- Above 32,000 text tokens prompt compression is skipped (`settings.py:122`, `gate.py:56`). Measured: 36,142 and 43,470 tokens were skipped in 84–87 ms.
- Between 28,000 and 32,000 tokens the gate passes but the work does not fit the 10 s timeout. Measured at 29,023 tokens: 10.0 s, timeout, no reduction (`exp5`). This is the expensive region, not the cheap one.
- Turns that are already compressed do not get smaller on later turns; new turns add their own cost.
- A subtle accounting trap: context engineering's own counter includes tool definitions and 4 tokens of per-message overhead, and my comparison does not. For the 5k-token agent case, the stage reported 5,630 after and my measure gave 5,316 before. The difference is exactly 238 tool-definition tokens plus 76 overhead tokens, so there was no increase. Any dashboard that compares the two counters directly will show spurious increases.
- Output tokens: unaffected by all three techniques. Not measured against a provider.
- Cached tokens: see Section 6.

### 3.4 Savings figures in the repo [CODE]

- `context_engineering/callback.py:271-295` credits the prompt-compression saving as estimated removed tokens (cl100k) priced at the input rate, and provider cache reads at (input price minus cache-read price). Cache-write tokens, which cost more than plain input on Anthropic-style providers, are recorded as a metric but not netted against the savings.
- The compression numbers in `evals/REPORT.md` and `reports/` are the project's own measurements on its own benchmarks. They were not reproduced here, because the benchmark inputs were not re-run against a live model.

---

## 4. Production scalability

### 4.1 Concurrency on one worker [VERIFIED; `exp4_concurrency.py`]

| Scenario | Outcome |
|---|---|
| Baseline, one idle request, about 1,450 tokens | 8.7 s end to end (includes classification), one LLMLingua call |
| Wave 1: 8 simultaneous cold requests | 1 compressed (8.7 s); **4 skipped as busy (unchanged, 0 ms)**; 2 stopped at the deadline with zero calls (9.0 s, no benefit); 1 **timed out at 10.0 s and was sent raw** |
| Work still running after the batch returned | 3.3 s (wave 1), 4.4 s (wave 2): the orphaned pipeline holds the LLMLingua lock after the hook has responded |
| Wave 2: 4 requests launched right after wave 1 | 1 compressed (7.5 s); 2 deadline (9.0 s); 1 timed out (10.0 s) |

Throughput derived from `exp2` scaling, compression alone: about 200–350 prose tokens per second per worker on this CPU (224 tokens in 1.4 s, 896 in 4.4 s, 2,240 in 6.4 s). The full hook also runs classification, so the end-to-end cost is higher than this figure implies (the idle request above). That is the whole budget of one worker, because `LLMLinguaCompressor` serialises calls behind one lock (`prompt_compression/compressor_adapter.py:45`, `:91`).

Consequences:
- Under bursts, most requests are either sent unchanged (admission: `prompt_compression_callback.py:221`, `max_concurrency` 4) or spend the full deadline waiting for the lock. Both are silent to the client, and the second case adds about 9 s of latency for no saving.
- With `NUM_WORKERS=2` and replicas 2–6 (`docker-compose.quickstart.yml:58`, `k8s/deployment.yaml:7`, `k8s/hpa.yaml`), each replica has its own compressor, its own 512-entry cache, and its own calibration state (`context_engineering/tokens.py:92-125`). A request that lands on a cold worker pays the full cost again.
- This is the structural issue the prior audit called F-05; it is still open. The remediation in `PROJECT_AUDIT_REPORT.md` section 12 made the failure graceful, not fast.

### 4.2 Context engineering under concurrency and at size [VERIFIED; `exp4` parts B and C]

- Serial timing: 5k tokens 79 ms; 20k 104 ms; 60k 287 ms; 120k 453 ms. All within the 2 s stage timeout, with masking of 24, 84 and 176 outputs respectively.
- Twelve simultaneous 20k-token requests: all succeeded; batch 0.94 s; median 509 ms, maximum 760 ms.

On this machine the stage does not need an admission control. Its blocking work runs on asyncio's default thread pool, which will saturate on a smaller host, so the claim should be retested on the real container size.

### 4.3 Other scalability notes [CONFIG / CODE]

- Redis is shared for rate limits, budgets and the response cache (`litellm_config.yaml`), so those are consistent across replicas. The prompt-compression and context-engineering state (caches, calibration, memory store) is not shared.
- Each worker loads about 1 GB of models (`docker-compose.quickstart.yml:32`), and the container limit is 6 GB with 8 CPUs. The compose comment says to size the limit to `NUM_WORKERS`.

---

## 5. Failure handling

| Mechanism | Status | Evidence |
|---|---|---|
| Hook timeouts and fail-open | **Works.** Original prompt forwarded | Timeouts observed at 10.0 s in waves and multi-turn runs; `prompt_compression_callback.py:236-239` |
| Pipeline deadline | **Partial.** Checked between model calls, not inside them | The classification batch (`sensitivity.py:307-308`) and each LLMLingua call (`compressor_adapter.py:92`) run to completion. Measured overrun to the 10 s backstop |
| Orphaned work after timeout | **Partial.** Work continues 3–4 s after the hook returns and holds the compressor lock | Section 4.1 |
| Context-engineering timeout (2 s) | **Works at measured sizes** | No timeouts up to 120k tokens on this CPU |
| Redaction failure | **Fail-closed** (503) | `prompt_compression_callback.py:167-171` |
| Compression admission | **Works, but silently degrades** | 4 of 8 requests unchanged under burst |
| LiteLLM retries, cooldowns, timeouts | **Configured, not exercised.** `router_settings`: timeout 120 s, stream 300 s, `num_retries` 2, per-error retry policy, `allowed_fails` 3, `cooldown_time` 30 s, Redis state | `litellm_config.yaml`. Not run against failing providers |
| Provider failover | **Not configured.** One deployment per model group in the YAML, `fallbacks: []`, and the comment says real fallbacks need a second deployment | `litellm_config.yaml` (CONFIG) |
| Cache failures | Response cache is Redis (`default_off`). Context-engineering store writes never raise, and a failed Redis write returns False | `context_engineering/store.py`. Not exercised |
| Rate limits | Shared in Redis (LiteLLM) | CONFIG |

---

## 6. Provider-side caching and cost

- **Prefix stability.** Section 3.2. Steady-state chat reuse is 94–97% of the previous request; agent loops are 100% between masking batches and collapse at each batch step; both collapse after a timeout.
- **Applicability to the configured models [CONFIG].** The configured models are Ollama (`obs-priced-llama`), a local mock, and a free OpenRouter model. None of them caches prompts. `context_engineering/cache.py:28` injects `cache_control` only for anthropic, bedrock, bedrock_converse, vertex_ai and vertex_ai_beta. So **provider-side cached-token savings cannot be verified in this repository**. The cached-token accounting in `callback.py:249-259` reads `prompt_tokens_details.cached_tokens` and `cache_read_input_tokens`, which is correct for those providers, but it has never been run against one.
- **Response cache.** `litellm_config.yaml` sets `cache_params.mode: default_off`, so no request gets a cached answer unless it asks. This gives zero automatic output-token saving.
- **Cost attribution.** Savings are estimates (Section 3.4) and cache-write surcharges are not netted. Treat dollar figures from `gateway_optimization_*` as indicative only until provider usage is reconciled.

---

## 7. Prioritised issues

Status key: **VERIFIED** = reproduced by an experiment in this audit; **CODE** = derived from code reading, not measured; **CONFIG** = from configuration; **UNVERIFIED** = not exercised.

### Critical

| ID | Issue | Status | Evidence | Fix (see Section 8) |
|---|---|---|---|---|
| **C1** | Lossy prose compression changes meaning and identifiers by default: negations and conditions dropped, identifiers rewritten, no validation or recovery | VERIFIED | 2.1, 2.2 | R1, R2 |
| **C2** | Classification and compression cannot be interrupted, so a long prose request spends the full 10 s timeout for little or no saving; long chats add about 2–3 s per request in steady state and up to 10 s on a cold worker | VERIFIED | 3.1 (W7, W8), 3.2, 3.3, 4.1 | R3, R4, R8 |

### High

| ID | Issue | Status | Evidence | Fix |
|---|---|---|---|---|
| **H1** | Compression is serialised per worker; under bursts most requests are unchanged or wait the whole deadline; orphaned pipelines hold the lock after the hook returns (F-05, still open) | VERIFIED | 4.1 | R4 |
| **H2** | Prefix caching is broken every turn by compressing the previous latest user message; masking batches invalidate the suffix; timeouts flip representation | VERIFIED | 3.2, 6 | R5, R6 |
| **H3** | The size gate creates a cliff: 28–32k tokens pay the full timeout for nothing, and above 32k no compression happens at all, so the largest contexts see no benefit | VERIFIED | 3.3, `exp5` | R8 |
| **H4** | Context engineering masking hides file contents that agents need to edit exactly; restore depends on the ref being mentioned and nothing tells the model how | VERIFIED (stub); CODE (restore) | 2.4 | R7 |
| **H5** | Privacy defaults: `REDACT_SENSITIVE` is off (`settings.py:129`, compose default empty); `turn_off_message_logging: false` in `litellm_config.yaml:45` with the file's own comment saying prompts then reach Langfuse, Jaeger and logs, while the compose file's comment assumes content is scrubbed | CONFIG | `litellm_config.yaml`, `docker-compose.quickstart.yml:127-128` | R9 |
| **H6** | No verified failover: one deployment per group, `fallbacks: []`; retry and cooldown settings are present but not exercised | CONFIG / UNVERIFIED | `litellm_config.yaml` | R10 |

### Medium

| ID | Issue | Status | Evidence | Fix |
|---|---|---|---|---|
| **M1** | Per-worker caches and a per-request budget that counts only cache misses make the compressed set depend on which worker served the request and on the order of runs; cold replicas diverge from warm ones | VERIFIED (W7 cold 11 runs, warm 21 runs) | `actions.py:145-152`, `:173-180`; `exp1b` | R5 |
| **M2** | Savings are estimates: cl100k counts, cache-write cost not netted, output tokens not measured | CODE | 3.4 | R11 |
| **M3** | Intent gate is lexical; common words in the first or last paragraph ("every", "each", "review", "all the") switch passage selection off, including for lookup questions over long documents | VERIFIED (W2 classified `transform`) | `intent.py:19-26`, `exp1b` | R12 |
| **M4** | Tests use fakes; there is no quality test on planted facts, negations, deadlines or prefix stability, so C1 and C2 would not fail CI | CODE | `prompt_compression/tests`, `.github/workflows/ci.yml` | R12 |
| **M5** | Calibration is per worker and only affects history decisions when compaction or JIT is enabled, so it is harmless by default but nondeterministic if enabled | CODE | `tokens.py:92-125`, `budget.py` | R13 |
| **M6** | Compaction (extractive and LLM) and JIT retrieval are off by default and not tested here | UNVERIFIED | `context_engineering/settings.py:125,98` | R13 |

### Low

| ID | Issue | Status | Evidence | Fix |
|---|---|---|---|---|
| **L1** | No output-token technique; response cache is opt-in | CONFIG | `litellm_config.yaml` cache section | Document; set expectations |
| **L2** | The error guard keeps any output that contains "error" among the newest three tool results in full, which costs tokens in debugging sessions | VERIFIED (stub) | `masking.py:130-133` | Tune the guard to tool exit status, not keywords |
| **L3** | Stub footer depends on the model noticing a ref; no system-prompt instruction | CODE | `masking.py:81` | R7 |

### Not a finding

- Context-engineering latency and concurrency at the sizes tested (Section 4.2).
- Fail-open for prompt compression (Section 5).
- Warm-cache compression is fast (about 100 ms warm vs 6 s cold for a 3.7k-token run).

---

## 8. Recommendations (concrete, code-level)

Ordered by impact on the Critical and High items. Each has a test that should fail before the change and pass after it, so it can gate CI.

**R1. Stop compressing text that carries meaning (C1).**
- Default `PROMPT_COMPRESSION_PRESERVE_LAST_USER=true` and extend it to the whole latest user message, not only its edges (`settings.py:130`, `router.py:50-52`).
- Default `PROMPT_COMPRESSION_RATE` to at least 0.6 (exp2: 19/20 normalized survival vs 15/20 at 0.4), or keep 0.4 only for the assistant prose route.
- Add a fact-preservation guard in `actions._compress_with_cap` (`actions.py:183-196`): extract identifiers, numbers, paths, e-mails, and sentences containing negation or condition words (`not`, `never`, `must`, `only`, `unless`, `do not`, `before`, `after`, `more than`) from the input run; after compression, compare normalised (whitespace-free, lower-case) forms; if any are missing, revert that run to the original and count it in the report.
- Test: `exp2_fidelity.py` expressed as a pytest case, with a required survival threshold.

**R2. Make compression fidelity measurable (C1, M4).**
- Put `exp2`-style planted-fact tests in `prompt_compression/tests` with real model fixtures under a marker, so CI can run them on the pinned revision.
- Add a per-request `fact_loss` field to the metadata so dashboards show it.

**R3. Make the work interruptible and bounded (C2).**
- In `sensitivity.check_many` (`sensitivity.py:307-308`), score in windows and call `deadlines.current().check("classifier")` between windows, instead of one batch under the lock.
- Before classification, cap the prose that will be classified and compressed per request (for example 4,000 tokens, the rest sent unchanged) so the work fits the budget. Measure first: on this CPU an idle request of about 1,450 tokens took 8.7 s end to end, so the 10 s timeout is reached at roughly 1.5–2.5k tokens.
- Test: a 28k-token prose request must return within the deadline plus 0.5 s with a `deadline` reason and no overrun.

**R4. Remove the per-worker compression bottleneck (H1, F-05).**
- Run compression in a separate inference service (or a pool of N compressor processes per worker sized to the cores), behind a queue with an explicit wait budget.
- Until then, set `PROMPT_COMPRESSION_MAX_CONCURRENCY=1` per worker and a short per-request prose budget, and expose the `busy` rate as a metric so teams know when they are not being compressed.
- Do not let an orphaned pipeline hold the lock after the caller has returned (the deadline should abort the pending call or the lock should be released with a cancellation flag).

**R5. Make compression decisions order-independent and shared (H2, M1).**
- Compute the compressed form of each message once, keyed by a hash of its original text and the rate, in Redis (shared across workers and replicas), and reuse it. Do not let the per-request budget depend on which runs were cached: count all runs, or budget by tokens rather than by calls.
- A message's representation should change only at a defined event (its first appearance, or a compaction), never because a timeout or a cache miss happened.

**R6. Stop rewriting the previous user message (H2).**
- Do not apply narrative compression to user messages at all. Compress assistant prose once, when it is first sent. This removes the per-turn break at the previous user message (Section 3.2) and keeps user text verbatim, which also helps R1.
- Test: a 20-turn chat must have 100% prefix reuse between turns except where compaction is intentionally triggered.

**R7. Make masking recoverable and cache-friendly (H4, L3, H2).**
- Add a gateway tool, `restore_observation(ref)`, injected only when masking is active, and state the mechanism in the system prompt the gateway adds. Without it the ref is only useful to a human.
- Exempt file-read and edit tools from masking by tool name (`read_file`, `view`, `edit` and equivalents), since their exact content is needed later.
- Change batching to mask a span once, at a fixed point (for example, everything older than N tool results), so the masked set grows in one step per session instead of in batches that invalidate the suffix each time. Accept one cache rewrite per session and document it.
- Tune `OBSERVATION_ERROR_GUARD` to tool exit status rather than keywords (L2).

**R8. Fix the size-gate cliff (C2, H3).**
- Align `PROMPT_COMPRESSION_MAX_INPUT_TOKENS` with the latency budget: at the measured rate it should be around 4,000–8,000 prose tokens, not 32,000. Above it, skip with `too_large` as now; below it, the work fits.
- For requests between the two, send the prompt unchanged and say so in the metadata, rather than running into the timeout.

**R9. Make privacy the default (H5).**
- Set `REDACT_SENSITIVE=true` in `docker-compose.quickstart.yml` and `.env.example`, and document the four bypasses the prior audit listed as now closed.
- Set `turn_off_message_logging: true` in `litellm_config.yaml` unless the Langfuse host is self-hosted and approved for prompt content; resolve the contradiction with the compose comment.

**R10. Verify routing and failover (H6).**
- Add a second deployment per model group (different provider or region) and set `fallbacks` and `context_window_fallbacks`, as the file's own comment describes.
- Load test with a failing primary (for example, a mock that returns 429 and then 500) and record retry, cooldown and failover behaviour.

**R11. Measure what is saved (M2, L1).**
- Record provider `usage` (prompt, completion, cached-read, cache-write) per request in the spend ledger, and compute savings from the difference against a shadow-mode baseline, not from cl100k estimates.
- Net cache-write surcharges against cache-read savings.

**R12. Tighten intent and tests (M3, M4).**
- Replace the first-and-last-paragraph intent check with the question sentence only, or with the question plus its immediate context, so document words do not switch selection off for lookups.
- Add the CI tests listed in R1, R2, R3 and R6 as gates.

**R13. Fence off the lossy history techniques (M5, M6).**
- Keep compaction and JIT off until they have their own fact-survival and prefix-stability tests. If enabled, make calibration a configuration value rather than a per-worker EWMA.

### Order of work

1. R9 (privacy defaults) and R8 (gate threshold): config and one constant, same day.
2. R1 and R6 (stop compressing meaning-bearing and user text): removes most of C1 and most of H2.
3. R3 and R4 (interruptible work, bounded concurrency): removes C2 and H1 for the worst cases.
4. R7 (masking): removes H4 and most of the batch cache loss.
5. R5, R10, R11, R12: the rest of the Medium items and the failover verification.

Expected effect, if these are done: prompt compression stops being the default source of savings, and the savings come mainly from context engineering on tool-heavy sessions and from warm prefix caching. Expect lower headline reduction figures (fewer tokens removed from prose) and fewer silent meaning changes.

---

## 9. What was not verified

- **Provider behaviour.** No LLM provider was called. No provider `usage` figures exist in the repo's runs, so provider-side cached-token savings and output tokens are unmeasured.
- **Answer quality.** Fact survival is a proxy. Whether a model answers correctly from compressed text was not tested.
- **Hardware.** All timings are from one Windows CPU machine. Container sizes differ (`k8s/deployment.yaml` requests 4 CPU, limits 8 CPU). Relative effects (serialisation, deadline overrun, warm-up) should hold; absolute latencies will not.
- **Synthetic workloads.** Prose was generated from a 20-sentence bank; tool outputs from a template. Real traffic will have different sentence structure, and the segmenter's code and exact-text rules are sensitive to it.
- **Failover, retries, cooldowns.** Configuration reviewed; not exercised.
- **Admission under sustained load.** Bursts of 8–12 were measured; a sustained rate was not.
- **The repo's own benchmark claims** (for example, 39–66% from selection in `evals/REPORT.md`) were not re-run.

---

## Appendix A. Reproduction

Interpreter: the compression venv, which is the only one with `llmlingua` and `pytest`. Offline Hugging Face cache with the pinned LLMLingua-2 and MiniLM models.

```bash
cd /c/Users/P7120489/litellm-gateway
export HF_HUB_OFFLINE=1 TOKENIZERS_PARALLELISM=false LITELLM_LOCAL_MODEL_COST_MAP=True
.venv-compression/Scripts/python.exe -m pytest -q prompt_compression/tests
```

```bash
cd /c/Users/P7120489/litellm-gateway
.venv-compression/Scripts/python.exe docs/audit-2026-11-18/experiments/exp1_workloads.py
.venv-compression/Scripts/python.exe docs/audit-2026-11-18/experiments/exp2_fidelity.py
.venv-compression/Scripts/python.exe docs/audit-2026-11-18/experiments/exp3_multiturn.py
.venv-compression/Scripts/python.exe docs/audit-2026-11-18/experiments/exp4_concurrency.py
.venv-compression/Scripts/python.exe docs/audit-2026-11-18/experiments/exp5_gate_and_stub.py
```

Results (JSON and raw output) are in `docs/audit-2026-11-18/experiments/`. The scripts set the gateway path to `C:\Users\P7120489\litellm-gateway`; change `GW` in each file if the checkout moves.

## Appendix B. Files

| File | Contents |
|---|---|
| `experiments/exp1_workloads.py` | Single-turn workloads through the real hooks |
| `experiments/exp1b_debug.py` | Cold and warm compression cache; where reductions come from |
| `experiments/exp2_fidelity.py` | Planted-fact survival under the production LLMLingua-2 adapter |
| `experiments/exp3_multiturn.py` | Growing conversations: prefix reuse, latency, variants |
| `experiments/exp4_concurrency.py` | Concurrent compression waves, orphan drain, CE timing and concurrency |
| `experiments/exp5_gate_and_stub.py` | Size-gate timing and a masked tool-output stub |
| `experiments/*_results.json`, `*_out.txt` | Raw outputs |
