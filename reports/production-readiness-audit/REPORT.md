# LiteLLM Gateway: production-readiness and token-reduction reliability audit

| | |
|---|---|
| Project | `litellm-gateway`, branch `feature/context-engineering` at `d3a36e5` (audit files added on `audit/production-readiness`, nothing committed) |
| Date | 2026-11-18 |
| Method | Read every production module (`context_engineering/`, `prompt_compression/`, `observability/`, configs, Compose, k8s). Ran all three test suites. Ran the **real hooks with the real models** (offline, pinned revisions) on workloads written for this audit, plus a local provider (Ollama, llama3.2:3b). Scripts and raw outputs: `reports/production-readiness-audit/scripts/` |
| Not done | No hosted-provider run (no API keys), no Docker/Redis/Postgres stack run, no live LiteLLM proxy run, no real traffic. Anything that needs those is marked **not verified**. |

Evidence labels: **MEASURED** (I ran it and saw it), **CODE** (certain from reading the code, not run), **PROJECT** (the project's own report, not reproduced), **NOT VERIFIED**.

---

## 1. Verdict

| Question | Answer |
|---|---|
| Is the system production-ready? | **No.** It is a well-engineered pilot. It is safe in **shadow mode**, or in enforce mode for single-turn, low-stakes lookups. It is not ready for multi-team production traffic (debugging, RCA, agent loops) with the default settings. |
| Is token reduction reliable across workloads? | **No. It is conditional.** Measured savings ranged from 0% to 98% on near-identical inputs, depending on question phrasing, tool-output size, prompt size, and how many other requests were in flight (§3). |
| Can it prevent or detect context loss during compression? | **Partly, and only for structural loss.** Invariants protect system prompts, the latest query, tool-call pairing and JSON validity. **Nothing detects semantic loss**: no key-string survival check, no omission marker for dropped records or passages, no quality validation. |
| Does it automatically recover from over-compression? | **No.** There is no second pass, no adaptive rate, no fallback to the uncompressed prompt, and no model-accessible way to ask for dropped content. Recovery is manual: someone must mention an `obs_`/`turn_` ref in a message. Dropped log lines and passages (prompt compression) have no ref at all. |
| Can I claim savings in dollars? | **Not yet.** All dollar figures in the project are estimates from list prices. The interaction with provider prefix caching can turn a 39–51% token reduction into a cost *increase* (§3.4, modelled). |

Never-claim list, supported by the evidence below: 100% token reduction, zero context loss, failure-free operation. None is supported.

---

## 2. What is guaranteed, conditional, or unsupported

### Guaranteed (enforced in code and covered by tests; I re-ran 393 tests, all pass)

| Behaviour | Where |
|---|---|
| System/developer messages unchanged (CE) and never compressed (PC) | `validate.py`, `pipeline.py` `PRESERVED_ROLES` |
| Latest user message unchanged by CE; first and last paragraph of it protected from PC | `validate.py`, `settings.protect_edges` |
| Tool calls and results stay paired; roles and order preserved | `validate.py` |
| Code blocks, structured data and identifier-dense text are never sent to LLMLingua-2 | `router.py` |
| Digits reserved in LLMLingua-2 output; 3× ratio cap per block with one lighter retry | `compressor_adapter.py`, `actions.py` |
| A failing or timed-out stage forwards the original request (fail-open) or returns 503 (fail-closed) | MEASURED, exp5 |
| Compression is bounded per request: 4 pipelines per worker, 12 model calls, 90% deadline | `prompt_compression_callback.py` |

### Conditional (only happens when a condition is met)

| Claim | Condition I found |
|---|---|
| Compression saves tokens | Request ≥ 50 tokens; prose ≥ 200 chars **or** a log/JSON block ≥ 10 lines **and** a question containing an identifier-like word that matches ≤ 30% of lines; passages route needs ≥ 6 passage blocks; not a "transform" intent; not flagged sensitive; compressor capacity free at that moment |
| Context engineering saves tokens | Request ≥ 1,000 tokens; tool outputs > 400 tokens, older than the newest 3, and in batches of 4 (`masking.py`); compaction and JIT are **off** by default |
| Cache-aware construction helps | Provider caches by prefix; `cache_control` is only injected on the **system** message for Anthropic/Bedrock/Vertex, and only if the system prompt is ≥ 1,024 tokens |
| Lost content is recoverable | Only masked tool outputs and compacted turns, only if a message mentions the ref |

### Unsupported or unmeasured

* Provider prompt-cache savings on Anthropic, OpenAI or Gemini (the README says so itself).
* Any dollar saving from a real invoice.
* Answer-quality parity on a production-grade model (the project's quality run used a 3B model and is incomplete).
* Tier routing, per-team budgets and provider failover: none is configured in this repository.

---

## 3. Measured results

All token counts are the project's own estimate (tiktoken `cl100k_base`, `context_engineering.tokens.messages_tokens`) unless stated. Workloads are mine, not the project's benchmark set. Scripts: `exp1.py` … `exp7.py`.

### 3.1 Token reduction and context retention by workload (real hooks, CE then compression)

| Case (domain) | Tokens before → after | Saved | Key facts kept | Notes |
|---|---|---|---|---|
| A. Short question (any) | 14 → 14 | **0%** | n/a | Below both size gates |
| B. React component + "why does it loop?" (frontend) | 657 → 657 | **0%** | 2/2 | Code is kept verbatim. Correct, but no saving |
| C. 160-line service log + "why did order ord-7731 fail?" (backend) | 5,613 → 255 | **95.5%** | **1/5** | **Root-cause line dropped**, see §3.2 |
| D. 220-line CI log + "which step failed and why?" (devops) | 4,654 → 4,654 | **0%** | 3/3 | Question has no identifier, so nothing is selected |
| E. 10-email ticket thread + "what order number?" (ticket) | 1,416 → 994 | 29.8% | 4/4 | 4.4 s of compression CPU |
| F. Same thread + "summarize the whole thread" (ticket) | 1,419 → 787 | 44.5% | 4/4 | Intent gate stops selection; prose is compressed |
| G. 12-paragraph memo + "minimum idle timeout?" | 1,402 → 514 | 63.3% | value kept, **identifier corrupted** | `IDLE_TIMEOUT_SECONDS` became `IDLE _ TIMEOUT _ SECONDS` |
| H. Agent debug loop, 8 tool calls, question about an old config dump | 10,954 → 6,111 | 44.2% | **0/2** | Masked at 14% context utilization; the asked-for line is gone |
| I. 14-turn DevOps chat, constraint stated in turn 1 | 2,395 → 1,001 | 58.2% | 3/3 | Early constraints survived (first turn is pinned), 9.2 s of compression CPU |
| J. Identifiers in prose (ticket id, RFC, port, version) | 622 → 254 | 59.2% | 1/5 exact | `NIMBUS-5044` → `NIMBUS - 5044`, `3.11.4` → `3. 11. 4`, `section 5.2` → `section 5. 2` |

### 3.2 Silent deletion of answer-bearing records (the most serious finding)

The `records` route keeps lines that contain an identifier from the question, plus **one** neighbour on each side, and deletes everything else. It writes no marker and stores nothing.

Controlled test (`exp2.py`): same 160-line log, question names `ord-7731`, root-cause line moved to a varying distance from the matched line:

| Root cause is… | Tokens | Root cause kept? |
|---|---|---|
| 1 line away (before or after) | 5,608 → 113 | yes |
| 2, 3, 5, 10, 30 lines away (either side) | 5,608 → 113 | **no** |

Phrasing flips the outcome. "Why did order ord-7731 fail?" → 98% saved, root cause lost. "Why did the checkout fail?" → 0% saved, root cause kept. "What went wrong with the 503 errors?" → 98% saved, root cause lost (the digits in `503` count as an identifier). "Review these logs and tell me why ord-7731 failed" → 0% saved (intent gate).

So **the same prompt either saves nothing or removes the cause, depending on wording**, and the model receives no hint that anything was removed.

### 3.3 Real model, provider-reported tokens and answer correctness (Ollama llama3.2:3b, temperature 0)

Each case was sent twice to the same model: the original messages, and what the gateway hooks produced. "Provider tokens" is Ollama's `prompt_eval_count`, so the savings below are **provider-reported, not estimated**; they agree with the gateway's own estimate within about 4%. Correctness is a string check on the answer. One run per cell at temperature 0, so this shows possible failures, not their rate. (`exp6.py`, `exp6.json`)

| Case | Provider tokens: original → gateway | Original answer | Gateway answer |
|---|---|---|---|
| C. Log, root cause 3 lines from the matched line | 5,634 → 276 (−95%) | Correct | **Incomplete**: blamed the payment timeout, never mentioned the exhausted DB pool (the line was deleted) |
| H. Agent loop, old config value | 10,871 → 6,028 (−45%) | Correct (`17`, with the comment) | **Wrong, fabricated**: stated `100` and invented a comment. The stub carried no value, and the model made one up |
| G. Memo, minimum idle timeout | 1,423 → 535 (−62%) | Correct (900) | Correct |
| E. Ticket, order number | 1,437 → 1,015 (−29%) | Correct | Correct |
| I. 14-turn chat, early constraints | 2,426 → 979 (−60%) | Correct | Correct |
| J. Identifiers in prose | 645 → 277 (−57%) | Correct | Correct, but echoed the corrupted `NIMBUS - 5044` |

Result: 4 of 6 cases kept the answer. The 2 that failed are exactly the two where content was **removed rather than compressed**, and both are default-on behaviours. The H failure is the worst kind: a plausible wrong value, not a refusal. Latency figures from this run are not reported: the machine was running other experiments at the same time.

### 3.4 Prefix-cache interaction in agent loops (modelled from real gateway output)

`exp3.py` runs the real context engine over a 24-round tool loop and measures how much of each request is byte-identical to the previous one (what a provider prefix cache can reuse). Cost uses Anthropic-style pricing (read 0.1×, write 1.25×) and OpenAI-style (read 0.5×). **This is a model of provider billing, not an invoice.**

| Tool output size | Tokens saved | Cost, Anthropic-style cache | Cost, OpenAI-style cache | Rounds with < 90% prefix reuse |
|---|---|---|---|---|
| ~250 tokens | 0% | 0% | 0% | 0 of 23 |
| ~600 tokens | 38.8% | **+54.2%** | −30.3% | 5 of 23 (reuse as low as 12%) |
| ~1,500 tokens | 50.9% | **+34.7%** | −43.2% | 5 of 23 (reuse as low as 5.6%) |

Each masking batch rewrites an early message, so everything after it misses the cache. If the client uses explicit cache breakpoints (Anthropic), the token reduction can raise the bill. If only the gateway's single system-prompt breakpoint is used, history is never cached and the saving is real. Either way, **tokens saved is not cost saved**, and the gateway reports the former.

### 3.5 Concurrency (one worker, real compressor, distinct 1,400-token prose requests; `exp4.py`)

| Concurrent requests | Statuses | Tokens saved | Slowest request |
|---|---|---|---|
| 1 | 1 compressed | 64.0% | 2.4 s |
| 4 | 3 compressed, 1 stopped at deadline (partial) | 48.4% | 9.5 s |
| 8 | 3 compressed (1 partial), **4 skipped "busy"** | 32.2% | 9.7 s |
| 16 | 3 compressed, **12 skipped**, 1 timed out | 14.1% | 10.0 s |
| 32 | 3 compressed, **29 skipped** | 7.5% | 9.0 s |

Degradation is graceful (no errors, no cascading failure; the earlier audit's lock-starvation bug is fixed). But **savings are load-dependent**, and the work that does run costs 2–9 s of CPU latency per cold request. Docker defaults to 2 workers, which doubles these capacities; it does not change the shape.

### 3.6 Failure handling (`exp5.py`)

| Scenario | Result |
|---|---|
| CE engine raises, `fail_mode=open` / `closed` | Original forwarded / HTTP 503 (MEASURED) |
| Compressor raises, open / closed | Original forwarded, `status=error` / HTTP 503 (MEASURED) |
| Redis store down (`CONTEXT_STORE=redis`) | Each store write blocks ~0.5 s; the CE hook hits its 2 s timeout on **every** request and fails open: **CE is silently off and each request is 2 s slower** (MEASURED) |
| Compressor fails to load | `_load_error` is sticky; every request fails open until restart; the liveness probe does not notice (CODE) |
| Provider failure | `fallbacks: []`, one deployment per group; retries and cooldowns are configured but there is nowhere to fall back to (CODE) |

---

## 4. Findings, by priority

### Critical

**C1. Default-on record/passage selection silently deletes content and cannot detect or recover it.**
`records` and `passages` are on by default (`settings.py` `DEFAULT_ROUTES`). Deleted lines leave no marker, no ref and no stored copy (`actions.py` `_select_records`, `_select_passages`). The model therefore answers confidently from partial evidence.
Evidence: §3.2 (root cause lost at distance ≥ 2; 98% reduction), case C.
Impact: wrong root-cause analysis for Backend/DevOps/Ticket teams; the failure is invisible in metrics (it counts as a successful 95% saving).
Fix: see R1–R3.

### High

**H1. Masking removes tool output with no budget need and no model-accessible recovery.** `mask_trigger` defaults to `always`, so masking ran at 14% utilization (case H, MEASURED). The stub says "mention `obs_…` in a message", but the model has no tool to do that, and a chat client cannot loop. The project's own quality run shows 12/14 correct under CE vs 13/13 baseline, both failures in `agent_tools` (PROJECT, small n).

**H2. Token reduction is reported, cost reduction is not measured, and they can diverge.** §3.4 (modelled). Prefix-cache effects were never measured against a real provider (README, CE report §7). Gateway metrics count estimated tokens, not what the provider billed.

**H3. Exact-string corruption by LLMLingua-2.** Versions, ISO dates, ticket ids, config keys inside prose get split with spaces (§3.1 G, J; in `exp8.py`, only 5 of 10 ISO dates and 5 of 10 hyphenated names such as `team-search` survived byte-exact). The project documented this once (`NIMBUS-5044`) and listed the fix as future work. There is no post-compression key-string check.

**H4. No quality validation, adaptive compression, or second pass.** The only compression validators are the 3× ratio cap and "output not longer than input". Nothing compares what was removed against what the question needs, and nothing retries with a lighter rate or falls back to the original when a check fails.

**H5. Savings and latency depend on load.** §3.5. A cold compressible request costs 2–9 s of CPU; under a burst of 8 on one worker, half skip compression. This breaks capacity planning for "token reduction" targets and adds latency that can exceed the LLM time saved.

**H6. The stated scenario (multiple teams, routing tiers, provider failover) is not implemented in this repository.** `litellm_config.yaml` has three test models (local Ollama, a free-tier judge, a mock), no `routing_strategy`, no tiers, no per-team keys or budgets, `fallbacks: []`. Production models live in the DB (`STORE_MODEL_IN_DB`) and were not visible to this audit.

**H7. Evidence gaps in the project's own report.** `reports/context-engineering/REPORT.md` still contains the literal placeholders `QUALITY_SECTION`, `CACHE_SECTION` and `VALIDATION_SECTION`. The quality data (`raw/quality.jsonl`) has 55 of ~64 planned rows and one 3B model.

### Medium

* **M1. CE store outage degrades every request** (§3.6). Use a circuit breaker and a short, non-blocking write.
* **M2. Unknown model aliases get a 32,768-token window and "unknown" caching** (`models.py`, `CONTEXT_DEFAULT_WINDOW_TOKENS`). Inside the proxy, resolution goes through the router's first deployment, so a group mixing models of different windows is sized by the first one (CODE; I did not run a live proxy).
* **M3. Intent gate is a keyword list.** "Extract all …" is caught; "Extract the action items" and "What are the deadlines?" are not (`exp7.py`). In that probe both prompts were labelled `lookup`, and the loss came from compression, not selection (passage dropping needs ≥ 6 passage blocks). The gate is a keyword list, not a safety mechanism. Side effect: the "Extract all …" prompt was labelled `sensitive` and saved 0%, while the near-identical prompts saved 38%.
* **M4. Sticky compressor/classifier load failure** and a liveness probe that ignores model state (CODE).
* **M5. Response cache (`mode: default_off`) has no namespace or per-team scoping in config.** Whether LiteLLM's key includes the team is NOT VERIFIED here; confirm before enabling for several teams. Cache and rate limits share one Redis.
* **M6. Committed config has `turn_off_message_logging: false`** and `require_auth_for_metrics_endpoint: false`. Both carry comments saying to change them for production.
* **M7. CE costs throughput under concurrency** (PROJECT: 46.5 → 26.7 req/s at c=8 on an instant mock; GIL-bound pure Python).
* **M8. K8s: HPA scales on CPU; each new pod needs ~120 s to load models.** Compression CPU bursts during scale-out will hit the "busy" skip path.

### Low

* L1. Token estimates are `cl100k_base` for every model; calibration and a 10% buffer absorb it (the metrics are labelled as such).
* L2. The default judge model is a free OpenRouter tier model.
* L3. No load or soak test in CI; tests are unit-level with model doubles.
* L4. `canonical_tools` and volatile-line relocation are off; volatile system prompts (dates, request ids) silently defeat provider caching and are only reported as a metric.

---

## 5. Recommendations

### Architecture

* **R1. Make every lossy removal visible and reversible.** When records or passages are dropped, insert a one-line marker (`[gateway: 148 of 160 lines omitted; kept lines matching ord-7731 ±1]`) and store the original under a ref, as CE already does for tool outputs.
* **R2. Always keep severity lines.** In logs keep every `ERROR`/`FATAL`/`WARN`/`Exception`/`Traceback` line (and their ±3 neighbours) regardless of identifier match. Increase `record_context_lines` from 1 to at least 3 for time-ordered logs.
* **R3. Add a post-compression guard with fallback.** After any lossy stage extract exact strings from the *removed* text (identifiers, versions, dates, numbers, error lines) and check whether the question or recent turns reference them; if a referenced string is missing, retry at a lighter rate, then send the original. Emit a `validation_fallback` counter.
* **R4. Give the model a recovery path.** Expose a `retrieve_observation(ref)` tool for clients that can route tool calls, and have the stub say when it is not available. Track the **re-fetch rate** (same tool and args after masking) as the loss signal.
* **R5. Mask only under pressure.** Set `OBSERVATION_MASK_TRIGGER=pressure` by default so a 128k-window request at 14% utilization is left alone.
* **R6. Decide per provider, not globally.** For providers where the client sets explicit breakpoints, disable masking that rewrites older turns, or move mask boundaries to cache-friendly points. Measure with real keys: provider `cached_tokens` and billed cost per request, before and after.
* **R7. Separate capacity from savings.** Run compression in a sidecar pool (or at least expose a "skipped: busy" rate alert and size workers to peak, not average). Prefer asynchronous precompression of earlier turns.
* **R8. Close the routing gap.** Define tier model groups, per-team keys and budgets, `fallbacks` and `context_window_fallbacks` in version control, and test failover with a fault-injected provider.

### Code-level

* `prompt_compression/actions.py`: emit omission markers and write dropped units to a store (`_select_records`, `_select_passages`).
* `prompt_compression/compressor_adapter.py`: pass identifier-shaped tokens (`[A-Za-z0-9]+[-_.][A-Za-z0-9]+`, ISO dates, versions) as forced tokens, or post-check them.
* `context_engineering/store.py`: add a circuit breaker; never let a store write exceed a few milliseconds on the request path.
* `compressor_adapter.py`: retry model load after a back-off; surface `compressor.loaded` in `/health/readiness`.
* `prompt_compression/intent.py`: replace the keyword list with a conservative default of "transform" when the question has no identifier.
* Complete the CE report (`QUALITY_SECTION`, `CACHE_SECTION`, `VALIDATION_SECTION`) with a larger run on a production-grade model.

### Rollout

1. Run in `shadow` mode on real traffic for two weeks; join `saved_by_technique` with provider-reported usage.
2. Enable only context-engineering dedupe and compression of prose for Ticket and general chat; keep `records`/`passages` and masking off for Backend and DevOps until R1–R5 land.
3. Add an automatic sampled A/B (1–5% of requests sent uncompressed) with an LLM-judge or string-match check to produce a measured quality delta.

---

## 6. What remains risky before production

1. Silent loss in logs and debugging sessions (C1, H1).
2. Cost claims that were never measured against a provider (H2).
3. Load-dependent behaviour (H5) and no provider failover or tiers (H6).
4. Exact-string corruption in tickets and chat (H3).
5. The project's own evidence is incomplete (H7).

## 7. Limits of this audit

Synthetic workloads; one local 3B model; one run per measurement on an 8-core Windows laptop; cache cost is modelled; no live proxy, Redis, Postgres, Docker or hosted provider; production model definitions in the DB were not visible. Results show what can happen, not how often it happens in your traffic.
