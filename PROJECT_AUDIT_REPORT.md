# LiteLLM Gateway — Technical Audit Report

| | |
|---|---|
| **Project** | `C:\Users\P7120489\litellm-gateway` (branch `main`, HEAD `f3adb5e`) |
| **Audit date** | 2026-11-09 |
| **Scope** | All tracked source, configuration, Docker/Compose, tests, eval and monitoring assets (233 tracked files; `reports/` data reviewed only where code or docs cite it) |
| **Method** | Line-by-line reading of every production module; both test suites run; 10 targeted probes run against the real project modules (with the project's own test doubles in place of the models); LiteLLM 1.106.0 / OpenTelemetry SDK source checked to confirm library defaults |
| **Changes to the project** | None. This report is the only file added. No secrets are reproduced here. |

Evidence labels used throughout:

- **VERIFIED**: reproduced by running code, or certain from reading the code and library source.
- **POTENTIAL**: the mechanism is in the code, but the impact depends on traffic or deployment and was not measured.
- **MISSING**: a capability that is not implemented.

---

## 1. Executive Summary

The project is a **LiteLLM proxy with a custom pre-call "prompt pipeline"**. The pipeline classifies, selects and compresses prompt text locally (rules, a MiniLM sensitivity classifier and LLMLingua-2) before the provider call. It comes with an observability layer (OTel spans, Prometheus metrics, JSON logs, Langfuse) and a full monitoring stack.

**The engineering is well above average for a prototype.** The pipeline is modular and fails open. Shadow mode exists. Exported telemetry is privacy-first. There are 207 unit tests and a threshold-driven eval harness. The design decisions are documented with measurements behind them.

**It is not production-ready yet.** The main reason is not the code quality. It is a set of verified behaviours that will hurt under real traffic and real conversations:

| # | Headline finding | Severity | Status |
|---|---|---|---|
| 1 | No upstream timeout, fallback, or cooldown is configured. LiteLLM's default request timeout is **6,000 s**. | High | VERIFIED |
| 2 | When the pipeline times out, the work keeps running. The orphaned thread keeps holding the single LLMLingua lock, so **later requests time out too** (cascading fail-open). | High | VERIFIED (probe V3) |
| 3 | Per-request compression work has no upper bound: the 6-call cap applies **per message**, so 41 messages meant 40 calls. | High | VERIFIED (probe V5) |
| 4 | Passage selection works **across the whole conversation**. It silently drops paragraphs from earlier assistant turns whenever they don't share words with the latest question, even though the "history" route is off. | High | VERIFIED (probe V1) |
| 5 | Selection ignores the task type. A "summarize the whole report" request lost 3 of 7 sections. | High | VERIFIED (probe V11) |
| 6 | `REDACT_SENSITIVE` has four bypasses: short prompts, a client opt-out flag, system/tool messages, and shadow mode. By default, "sensitive" only means "don't compress"; the data still goes to the provider. | High (when redaction is relied on) | VERIFIED (probes V2a–d) |
| 7 | The Docker image isn't reproducible: floating `main-stable` base, unpinned torch/llmlingua, `transformers<5` in the image vs `5.20.1` in tests, and model weights downloaded at runtime without a pinned revision. | High | VERIFIED |
| 8 | Each worker handles one model call at a time (global locks). Capacity with an instant model is 0.28× baseline, which is the project's own failing check. | Medium–High | VERIFIED (code + `evals/REPORT.md`) |
| 9 | There is no CI. 2 of 192 compression tests fail at HEAD. | Medium | VERIFIED |
| 10 | There is no response caching, even though Redis is deployed. Rewriting earlier turns per request also defeats provider prefix caching. | Medium | VERIFIED / POTENTIAL |

**Overall verdict: Pilot-ready, not production-ready.** It is safe to run internally in **shadow mode**, or in enforce mode for single-turn QA and log-analysis workloads. Before multi-user or multi-turn production traffic it needs the P0 items in §9: timeouts and fallbacks, bounded and cancellable pipeline work, conversation-aware selection, a pinned image and CI. That is roughly 1.5–2 engineer-weeks.

---

## 2. Project Architecture Overview

### 2.1 Components

| Component | Path | Purpose | Size |
|---|---|---|---|
| Gateway | `Dockerfile`, `docker-compose.quickstart.yml`, `litellm_config.yaml` | Stock LiteLLM proxy image plus torch-CPU and llmlingua; Postgres (keys, spend, models in DB); Redis | — |
| Prompt pipeline | `prompt_compression/` | Pre-call hook: gate → segment/classify → route → actions → reassemble | ~1,900 LOC |
| Observability | `observability/` | Subclass of the hook: spans, `prompt_pipeline_*` metrics, JSON/OTLP logs, Langfuse attribution | ~600 LOC |
| Monitoring | `monitoring/` | OTel Collector, Jaeger, Loki, Prometheus (15 alert rules), Alertmanager, Grafana (3 dashboards), exporters | config |
| Evals | `evals/`, `prompt_compression/eval/` | Live HTTP cases (gate4), benchmark scorers, threshold file, sensitivity-head training | ~1,500 LOC |
| Research data | `reports/` | Benchmark raw data and reports (9 MB) | data |

Two LiteLLM configs exist. `config.yaml` is a minimal sample. `litellm_config.yaml` is the one Compose mounts, as `/app/config.yaml`.

### 2.2 Request lifecycle (as implemented)

```
Client ──HTTP──▶ LiteLLM proxy (NUM_WORKERS=2, Postgres auth/spend, Redis)
                   │  auth (virtual key / master key), budgets, rate limits (LiteLLM built-ins)
                   ▼
   callbacks: otel, langfuse_otel, prometheus, ObservedPromptCompressionCallback
                   │
   async_pre_call_hook (event loop)
     ├─ obs wrapper: join all message text (originals), open span "prompt.pipeline"
     ├─ gate.check  (event loop): call type, enabled, metadata opt-out, tiktoken count of ALL text ≥ 50
     └─ asyncio.wait_for(asyncio.to_thread(pipeline.process), timeout=10 s)     ← worker thread
          1 segment   segmenter.split_segments → code | structured | exact | prose
          2 classify  rules.py + topics.py (every block), MiniLM+LR head on prose (batched, LRU cache)
          3 route     edges/sensitive/code/structured/exact → keep; logs/JSON → select records;
                      ≥6 candidate blocks across ALL messages → BM25 passage selection; prose → compress
          4 actions   redact (opt) → select records → select passages → LLMLingua-2 (ratio cap 3×)
          5 reassemble, report → metadata.prompt_compression + spend_logs_metadata
     ├─ timeout / error → fail open (original prompt) or 503 (fail closed)
     └─ obs wrapper: metrics, span attributes, Langfuse tags/trace_metadata, JSON log
                   ▼
   LiteLLM router → provider (Ollama / OpenRouter / mock; production models live in the DB)
                   ▼
   async_log_success/failure_event → JSON log "llm.request.*" with tokens, cost, latency, TTFT
```

### 2.3 Key dependencies

| Dependency | Tested version (`prompt_compression/requirements.txt`) | Version in the Docker image |
|---|---|---|
| litellm | 1.106.0 | whatever `main-stable` is at build time (`observability/requirements.txt:1` says 1.105.0) |
| transformers | 5.20.1 | `<5` (`Dockerfile:10`) |
| torch | 2.15.0 | latest CPU wheel, unpinned |
| llmlingua | 0.2.2 | unpinned |
| Models | `all-MiniLM-L6-v2`, `llmlingua-2-bert-base-multilingual-cased-meetingbank` | downloaded on first start, no `revision=` |

---

## 3. Existing Strengths

| Area | Strength | Evidence |
|---|---|---|
| Safety-first design | Fails open by default. Fail-closed is an option (503). Shadow mode reports what *would* change. Per-request opt-out. | `prompt_compression_callback.py:89-125` |
| Conservative compression | Only prose is compressed. Code, structured data, identifier-dense text, sensitive text, and the instruction and question edges stay byte-for-byte. `force_reserve_digit=True`. Ratio cap with a lighter retry. | `router.py:38-70`, `actions.py:157-172`, `compressor_adapter.py:60` |
| Lossless segmentation | `split_segments` guarantees `join(segments) == text`. | `segmenter.py` docstring; tests |
| Structural correctness | Roles and order are preserved. Tool calls/results, system messages and multimodal parts are untouched. JSON arrays stay valid after record selection. | `pipeline.py:41,220-226`, `actions.py:81-82` |
| Privacy in telemetry | `turn_off_message_logging`, salted hashes, rule-based scrubbing of every log field, no identity labels in Prometheus, bounded model-label cardinality, text capture opt-in and limited to "general". | `litellm_config.yaml:38-42`, `observability/privacy.py`, `metrics.py:509-518` |
| Observability depth | One trace per request with child spans per stage. Metrics for tokens, ratio, latency, failures, cache hits, model-load state and compute-cost estimate. 15 alert rules. 3 dashboards. | `observability/`, `monitoring/` |
| Evidence-driven tuning | Every threshold and route default cites a benchmark. The eval harness enforces 24 thresholds, covering quality (answers lost, key strings kept) and not just savings. | `settings.py:11-15`, `evals/thresholds.yaml`, `evals/REPORT.md` |
| Tests | 192 compression and 15 observability unit tests, fast (≈10 s), using model doubles. | §10 |
| Infra hygiene | Monitoring images pinned to exact versions. Monitoring ports bound to `127.0.0.1`. Redis password required. `.env` ignored and never committed. | `monitoring/docker-compose.monitoring.yml`, `.gitignore:2` |

---

## 4. Identified Bugs and Technical Flaws

Severity is defined as follows. **Critical**: data loss or breach likely in normal use. **High**: will cause incidents or wrong answers under realistic production use. **Medium**: degrades reliability, cost or operability. **Low**: hygiene.

No finding is rated Critical. With the default settings, nothing leaks or corrupts data in single-turn use.

### 4.1 Reliability and gateway

#### F-01 No upstream timeout, fallbacks or cooldowns are configured — **High** · VERIFIED
- **Where:** `litellm_config.yaml:1-45`. There is no `router_settings`, no `litellm_settings.request_timeout`, no `fallbacks`, no `num_retries` or `allowed_fails`, and no per-model `timeout`.
- **What:** LiteLLM's defaults apply. `DEFAULT_REQUEST_TIMEOUT_SECONDS = 6000.0` (`litellm/constants.py:587`), and retries come from the OpenAI client default of 2 (`router.py:1219`). Each model group has one deployment, so there is nothing to fall back to. The LLM-as-judge is a free OpenRouter tier model (`litellm_config.yaml:15-18`).
- **Impact:** A hung provider holds the client connection and a worker slot for up to 100 minutes. One provider outage means 100 % errors for that model group. Free-tier rate limits make judge-based evals flaky.
- **Fix:** Add `router_settings` with `timeout` (e.g. 60 s) and `stream_timeout`, `num_retries: 2`, `retry_policy` (no retry on 400/401/content-policy), `allowed_fails` + `cooldown_time`, and `fallbacks` / `context_window_fallbacks` per model group. Use `routing_strategy: latency-based-routing` or `usage-based-routing-v2` with Redis once there are two or more deployments.
- **Limitation:** Production models are stored in the DB (`STORE_MODEL_IN_DB=True`) and were not visible, so per-model settings set in the UI could not be audited.

#### F-02 A timed-out pipeline keeps running and blocks every following request — **High** · VERIFIED (probe V3)
- **Where:** `prompt_compression_callback.py:111-118` (`asyncio.wait_for(asyncio.to_thread(...))`), `compressor_adapter.py:30-31,59` (one `_call_lock` per process), `sensitivity.py:115` and `embedding_classifier.py:74` (inference locks).
- **What:** `wait_for` cancels only the awaiting coroutine. The worker thread can't be cancelled. It finishes the full pipeline in the background, still holding the global compressor lock.
- **Reproduction:** timeout 1 s, a compressor taking 1.5 s per call, 4 compressible messages. Request 1 went to `status=error` after 1.01 s. **Request 2, sent next, also went to `status=error` after 1.00 s**, because it was waiting for the lock held by request 1's orphaned thread. All 4 background calls completed after both requests had given up.
- **Impact:** Under load, one slow prompt makes later prompts fail open: they add up to 10 s of latency and save nothing. CPU is spent on results nobody will use, and the default thread pool (`min(32, cpu+4)`) can fill up with orphaned work.
- **Fix:** (a) Make the work cooperatively cancellable: pass a deadline into `PromptPipeline.process` and check it before each model call (`actions._compress` loop, `_check_many`). (b) Acquire the locks with a timeout derived from the remaining deadline. (c) Better still, use a bounded dedicated executor and a semaphore, and reject or skip at admission when the queue is full instead of after 10 s.

#### F-03 Per-request compression cost is unbounded — **High** · VERIFIED (probe V5)
- **Where:** `actions.py:136-141`. `max_compress_calls` is checked against `counters`, which `Outcome.counters(message)` scopes **per message**. `gate.py` has no upper bound on input size.
- **Reproduction:** one 41-message request produced **40 compressor calls**. The documented intent is "at most this many LLMLingua-2 calls per message (each costs about a second of CPU)" (`settings.py:121-122`).
- **Impact:** Long chats deterministically hit the 10 s timeout (≈1 s per call). Combined with F-02, that becomes a cheap latency amplifier: a client can send long histories and degrade the gateway for everyone.
- **Fix:** Add a request-level budget (`max_compress_calls_per_request`, plus a token budget for compressor input). Prioritise the longest runs across *all* messages, not per message. Add `PROMPT_COMPRESSION_MAX_INPUT_TOKENS`, above which the request is skipped as `too_large`.

#### F-04 Event-loop blocking in the hook — **Medium** · VERIFIED (probe V4)
- **Where:** `gate.py:49` (`all_text_tokens` on the loop), `observed_callback.py:121-125` (joins every message's text on the loop), `observed_callback.py:246` (`count_tokens` fallback on the loop).
- **Reproduction:** a 2 MB prompt took **183–214 ms** of synchronous tiktoken work in `gate.check` alone, before `to_thread`.
- **Impact:** While this runs, every other in-flight request on that worker stalls: streaming chunks, health checks, auth.
- **Fix:** Use a cheap pre-gate on `len(text)` (chars / 4 ≈ tokens) for the min-size and max-size checks. Do exact counting inside the worker thread. Build `originals` lazily, only when `capture_text` is on (hashes can be computed in the thread).

#### F-05 Each worker runs one model call at a time — **Medium–High** · VERIFIED
- **Where:** `compressor_adapter.py:31` (`PromptCompressor keeps per-call state on the instance, so calls are serialized`), `sensitivity.py:248,299`, `embedding_classifier.py:74`.
- **What:** Each worker holds one copy of each model (≈1 GB RAM, `docker-compose.quickstart.yml:41-46`), and every inference is serialised. Throughput scales only by adding workers, which also adds RAM and splits the threads.
- **Evidence:** The project's own result is "Mock capacity ratio 0.282 vs ≥ 0.5 — **FAIL**" (`evals/REPORT.md:35,104`).
- **Fix:** See §8.7. Move the models out of the proxy process into a small inference service with micro-batching, or keep N compressor instances in a pool. Skip compression when the queue is deep (adaptive admission). In the short term, use `CLASSIFIER_QUANTIZE=int8` (already supported) and ONNX Runtime for MiniLM.

### 4.2 Context engineering and correctness

#### F-06 Passage selection drops content from earlier conversation turns — **High** · VERIFIED (probe V1)
- **Where:** `pipeline.py:214-253` (units are collected from **every** non-preserved message), `router.py:44-78` (passage `candidates` span all messages; the only condition is "≥ 6 candidates and ≥ 100 tokens").
- **What:** In a multi-turn chat, every earlier assistant answer and user message is a "passage". BM25 against the *latest* question then removes about 50 % of their tokens. The `history` route is documented as "off because nothing was measured on chat history" (`selectors.py:10-11`), but the passages route does history trimming anyway, at paragraph level and without the turn-integrity rules of `trim_history`.
- **Reproduction:** 8 Q&A turns on 8 topics, then "regarding the database, what should we change?". **4 of 8 assistant turns had passages dropped**, and tokens went from 931 to 713.
- **Impact:** Silent context loss. Follow-ups such as "compare that with what you said about billing" or "use the earlier plan" lose their referent. Two other consequences: (a) the earlier assistant text changes with every new question, which breaks provider prefix caching (F-15); (b) the model sees a history that doesn't match what it actually said. None of the evals cover multi-turn chat (`evals/cases`, B2–B4 families are qa/logs/code/pii).
- **Fix:** Restrict passage and record selection to the **latest user message** (or to messages explicitly marked as documents). Treat everything earlier as history, governed only by the `history` route and its budget. Add a multi-turn eval family.

#### F-07 Selection ignores the task type, so summarisation loses content — **High** · VERIFIED (probe V11)
- **Where:** `router.py:73-78`, `selectors.py:23-29`. "summarize", "summary", "explain", "describe" and "list" are *stopwords*, so the remaining query terms drive a QA-style top-50 % selection.
- **Reproduction:** a 7-section report with "Summarize the whole report, focusing on risks." **3 sections were dropped** (revenue, churn, security).
- **Impact:** Wrong or incomplete answers for summarisation, translation, rewriting, review and "check the whole document" tasks. These are among the most common uses of long prompts.
- **Fix:** Add a task-intent check before selection: a cheap lexical classifier (summarize/translate/rewrite/review/all/whole/every → no selection, narrative compression only) or the existing MiniLM encoder with a second small head. Only enable selection for lookup or QA intents. Record `intent` in the report and metrics.

#### F-08 The tokenizer is fixed to cl100k_base for every model — **Low** · VERIFIED
- **Where:** `texts.py:8`.
- **Impact:** `min_tokens`, savings metrics and Langfuse token figures are approximate for Llama, Claude and Gemini (±10–25 %). Billing uses LiteLLM's own counts, so this only affects internal metrics.
- **Fix:** Label the metrics as `cl100k_estimate`, or use `litellm.token_counter(model=...)` for the reported numbers.

#### F-09 Unbounded embedding batch — **Low–Medium** · POTENTIAL
- **Where:** `embedding_classifier.py:118-121`, `sensitivity.py:299-300`. Every window of every group goes into one padded forward pass.
- **Impact:** A very long prompt can produce hundreds of 256-token windows in one tensor, causing a memory spike in a container without limits (F-12). Not measured.
- **Fix:** Use a mini-batch of about 32 windows, and cap windows per request (score a sample and fail safe to "sensitive" or "skip").

### 4.3 Code quality and maintainability

| ID | Finding | Location | Severity | Status |
|---|---|---|---|---|
| F-10 | **2 failing unit tests at HEAD.** Commit `4643804` replaced fixtures with `[..._PLACEHOLDER]` strings that the regexes can't match. | `prompt_compression/tests/test_rules.py:21-22` | Medium | VERIFIED |
| F-11 | Dead or misleading env vars: `COMPRESSION_THRESHOLD_CHARS`, `COMPRESSION_RATE`, `COMPRESSION_MODEL` are read nowhere. The model they name (xlm-roberta-large) isn't the one in use. | `.env.example:28-30` | Low | VERIFIED (grep) |
| F-12a | Stale references to modules that don't exist: `ai-features/compression.py`, `compression.compression_guardrail_instance`. | `Dockerfile:2`, `litellm_config.yaml:34-35`, `compressor_adapter.py:3` | Low | VERIFIED |
| F-13 | `configure_logging` forces `INFO` on both loggers and overrides `PROMPT_COMPRESSION_LOG_LEVEL`. | `observability/logs.py:610` vs `prompt_compression_callback.py:45` | Low | VERIFIED |
| F-14 | Kept-reason counters double count: an `exact` unit is counted under `kept.exact` and then re-assigned to `SELECT` when the passages route fires. | `router.py:62-64,73-78` | Low | VERIFIED (code) |
| — | Two configs (`config.yaml`, `litellm_config.yaml`) that can drift; the mounted one isn't the one the README sample shows. | root | Low | VERIFIED |
| — | No lint, type-check or formatter config (ruff/mypy/pyproject). Settings are parsed ad hoc in two packages with duplicated `_bool`/`_float`. | `prompt_compression/settings.py:21-35`, `observability/settings.py:6-17` | Low | VERIFIED |

---

## 5. Security Assessment

### 5.1 Findings

#### F-15S `REDACT_SENSITIVE` can be bypassed four ways — **High (if redaction is a control)** · VERIFIED (probes V2a–d)

With `REDACT_SENSITIVE=true` and a synthetic AWS-style key in the prompt:

| Probe | Path | Result |
|---|---|---|
| V2a | Prompt under `min_tokens` (11 tokens). The gate returns before the pipeline (`gate.py:49-50`). | Secret forwarded |
| V2b | Client sends `metadata: {"prompt_compression": false}` (`gate.py:32-39,47`). | Secret forwarded |
| V2c | Secret in a `system` (or `tool`) message. `PRESERVED_ROLES` are never visited (`pipeline.py:41,220`). | Secret forwarded |
| V2d | `PROMPT_COMPRESSION_MODE=shadow`. Messages aren't replaced (`prompt_compression_callback.py:122-125`). | Secret forwarded |
| — | Fail-open on timeout or error (`prompt_compression_callback.py:95`). | Original (unredacted) prompt forwarded (by design) |

Also: by default (`REDACT_SENSITIVE=false`) the sensitivity stage only decides **"do not compress"**. Detected PII, credentials and health data are forwarded verbatim to whichever provider the request targets, including third-party OpenRouter. That is a reasonable design for a compression feature, but it must not be described or relied on as DLP.

**Fix:** Split redaction out into its own guardrail (LiteLLM `guardrails:` with `mode: pre_call`, or a separate hook) that runs on **every** chat request and **every** role, ignores the compression opt-out, applies in shadow mode, and fails *closed*. Keep the opt-out for compression only. If DLP is a requirement, evaluate LiteLLM's Presidio guardrail against the rules layer.

#### Other security observations

| ID | Finding | Location | Severity | Status | Recommendation |
|---|---|---|---|---|---|
| F-16S | `/metrics` has no auth, and the proxy publishes on **all interfaces** when `LITELLM_BIND` is unset (the Compose default is empty). The shipped `.env.example` sets `127.0.0.1:`, so the risk depends on the deployment. | `litellm_config.yaml:40`, `docker-compose.quickstart.yml:30` | Medium | VERIFIED | Default `LITELLM_BIND` to `127.0.0.1:` in Compose itself. In production, put the proxy behind a reverse proxy/TLS and set `require_auth_for_metrics_endpoint: true`, or scrape over an internal network only. |
| F-17S | Postgres password falls back to `litellm` when `POSTGRES_PASSWORD` is unset. | `docker-compose.quickstart.yml:63,111` | Medium (DB isn't published) | VERIFIED | Use `${POSTGRES_PASSWORD:?…}` like the other secrets. |
| F-18S | `OBS_HASH_SALT` defaults to empty, which gives **unsalted** truncated SHA-256 of user and team ids. Guessable ids (emails) can be reversed by dictionary. A warning is logged, but startup continues. | `docker-compose.quickstart.yml:85`, `observability/settings.py:42`, `privacy.py:415-419` | Medium (privacy) | VERIFIED | Require a salt when `OBS_ENABLED=true` (fail start), or derive one from `LITELLM_SALT_KEY` via HMAC. Use HMAC-SHA256 instead of `salt+value`. |
| F-19S | Supply chain: floating base image, unpinned torch/llmlingua, HF models fetched at runtime without `revision=` or a hash. | `Dockerfile:3,9-10`, `embedding_classifier.py:47-49`, `compressor_adapter.py:49` | High | VERIFIED | Pin the image by digest, use a pip lock file with hashes, set `revision=` on `from_pretrained`, and bake the weights into the image (or a pre-seeded volume) with `HF_HUB_OFFLINE=1`. |
| F-20S | Key-shaped strings remain in git history (11 commits) and in `prompt_compression/eval/build_dataset.py:46` at HEAD. They are most likely synthetic fixtures (GitHub push protection flagged them once). | git history | Low (unconfirmed) | VERIFIED presence, not validity | Confirm none is a real key. If any is, rotate it and rewrite history. Generate fixtures at test time (e.g. `"sk-proj-" + "a"*40`) so scanners stay quiet. |
| F-21S | `OBS_CAPTURE_TEXT=true` exports pre/post text of "general" messages to OTel and Langfuse, scrubbed only by regex rules. Model false negatives would leak. | `observed_callback.py:250-253` | Low (opt-in, off by default) | VERIFIED | Keep it off in production; document it as debug-only, sampled, time-boxed. |
| F-22S | Provider `error_message` is logged. It's scrubbed by the rules and truncated to 500 chars, but some providers echo prompt fragments in errors. | `observed_callback.py:322-325` | Low | POTENTIAL | Log `error_class` and `error_code` only, or a hash of the message. |

### 5.2 Positive security controls observed
Master key and salt key are required (`:?`). Redis requires a password. `.env` is ignored and never committed. `turn_off_message_logging: true`. Content capture is off in OTel GenAI. Prometheus identity labels are excluded. Monitoring UIs are bound to localhost. Grafana sign-up and analytics are disabled. LiteLLM falls back from `general_settings.master_key` to the `LITELLM_MASTER_KEY` env var (`proxy_server.py:6923`), so auth stays on even though the mounted config omits `master_key`.

### 5.3 Not verified (limitations)
Virtual-key scopes, team budgets, RBAC and SSO live in the Postgres DB and LiteLLM UI, which weren't accessible. TLS termination isn't part of the repo. I couldn't check the configuration of the deployed LiteLLM version, because the image tag floats.

---

## 6. Performance and Scalability Assessment

### 6.1 Measured or documented figures (from the project's own reports)

| Metric | Value | Source |
|---|---|---|
| Pipeline overhead p50 / p95 | 22 ms / 432 ms | `evals/REPORT.md:196` |
| Worst single pipeline run | 3,767 ms (timeout 10 s) | `evals/REPORT.md:185` |
| Throughput, 2 workers × 4 threads, c=8, compressed | 12.7–13.1 req/s | `docker-compose.quickstart.yml:44-45` |
| Capacity vs. no compression (instant model) | **0.28×** (FAIL, threshold 0.5) | `evals/REPORT.md:35` |
| Real-model throughput gain (smaller prompts) | +38.9 % to +54.7 % | `evals/REPORT.md:33` |
| RAM per worker | ≈1 GB (models) | `docker-compose.quickstart.yml:41` |

So compression pays off when the downstream model is slow and expensive (real LLM latency dominates), and it is the bottleneck when the model is fast. The gateway's maximum throughput is bounded by the CPU inference in the proxy process.

### 6.2 Bottlenecks (in order of impact)

| Rank | Bottleneck | Finding |
|---|---|---|
| 1 | Global per-worker locks on compressor and encoder | F-05 |
| 2 | Orphaned work after timeout holding those locks | F-02 |
| 3 | Unbounded compression calls per request | F-03 |
| 4 | Synchronous tokenisation and text joins on the event loop | F-04 |
| 5 | `copy.deepcopy(messages)` per request (`pipeline.py:199`) and full per-message reports in `spend_logs_metadata` (`prompt_compression_callback.py:56-58`), which grow DB rows and log payloads linearly with message count | POTENTIAL, Low |
| 6 | No container memory or CPU limits, no gateway healthcheck or restart policy (`docker-compose.quickstart.yml:21-105`), so an OOM or hang isn't detected or recovered by Compose | VERIFIED, Medium |

### 6.3 Scalability readiness

| Concern | Status |
|---|---|
| Horizontal scaling of the proxy | Possible: Redis and Postgres are shared. Each replica loads ≈1 GB per worker. |
| Shared rate limits and budgets | Redis is wired (`docker-compose.quickstart.yml:98-100`). |
| Admission control / back-pressure for the pipeline | MISSING |
| Load balancing across deployments | MISSING (single deployment per model group in YAML; DB not visible) |
| GPU path | Not wired. `OBS_COMPUTE_DEVICE` affects only the cost estimate; `device_map="cpu"` is hard-coded (`compressor_adapter.py:49`). |

---

## 7. Context Engineering and Token Optimization Assessment

### 7.1 What is implemented

| Technique | Implemented | Quality |
|---|---|---|
| Content-type-aware segmentation (code/structured/exact/prose) | Yes | Strong, lossless |
| Token-level prose compression (LLMLingua-2), ratio cap, digit preservation | Yes | Good; capped at 3× |
| Query-aware passage selection (BM25) | Yes | Good for single-document QA; **wrong scope** for multi-turn (F-06), **wrong for non-QA tasks** (F-07) |
| Query-aware record (log/JSONL/CSV) line selection | Yes | Strong: needs identifier matches, keeps neighbours and headers, keeps JSON valid |
| Instruction/question edge protection | Yes | Good |
| History trimming by token budget | Yes, off by default | Correct turn and tool-call integrity; only drops whole turns (no summarisation) |
| Sensitivity-aware keep-verbatim | Yes | Good recall; head trained on only 385 samples (CV FPR 0.154, `models/sensitivity_head.json`) |
| Context-window-aware behaviour (target model limits) | **MISSING** | Nothing reads the target model's context window; no `context_window_fallbacks` |
| Conversation summarisation / compaction | **MISSING** | — |
| Provider prompt caching (`cache_control`, prefix stability) | **MISSING**, and actively undermined (F-15) | — |
| Response caching (exact or semantic) | **MISSING** | Redis deployed but `cache` not enabled |
| Information-loss safeguards at runtime | Partial | Ratio cap and protected kinds; no per-request quality signal, no "answer-bearing span" check |
| Task-intent detection | **MISSING** | F-07 |

#### F-15 Compression and selection defeat provider prefix caching — **Medium** · mechanism VERIFIED, cost impact POTENTIAL
OpenAI, Anthropic, Gemini and DeepSeek discount repeated **prefixes** by 50–90 %. Here, earlier turns are recompressed and re-selected on every request, against a query that changes each time (probe V1). So the prefix changes and the cache misses. For long multi-turn chats on caching-capable providers, this can cost more than compression saves. **Fix:** leave everything before the latest user message byte-stable (cache-friendly). Compress only the new content, and memoise compressed outputs by content hash so a turn compressed once is replayed identically on later requests.

#### F-16 No response cache — **Medium** · MISSING
`litellm_config.yaml` has no `cache: true` / `cache_params`, although Redis is deployed and the doc comments talk about "cache". Identical eval, agent-retry and dashboard queries pay full price. **Fix:** `litellm_settings: cache: true, cache_params: {type: redis, ttl: 600, supported_call_types: [acompletion]}`, opt-in per key or team. Note that the pre-call hook runs before the router call, so the cache key is computed over the *compressed* prompt. That only stays a stable key if compression is deterministic, which LLMLingua-2 argmax is.

### 7.2 Information-loss risk matrix

| Workload | Current behaviour | Risk |
|---|---|---|
| Single-turn QA over a document | Passage selection + compression, evaluated (0 answers lost in 80) | Low |
| Log / JSONL lookup by id | Record selection, evaluated | Low |
| Code questions | Code kept verbatim | Low |
| Summarise / translate / review a document | Passages dropped (F-07) | **High** |
| Multi-turn chat with references to earlier turns | Earlier turns thinned (F-06) | **High** |
| Agents / tool use | Tool messages preserved; assistant prose between tool calls is eligible for passages (F-06) | Medium |
| Prompts with system-level secrets | Not redacted (F-15S) | Medium (security, not loss) |

---

## 8. Missing Features and Improvement Opportunities

Each opportunity below builds on the existing architecture. Complexity: S ≈ ≤ 3 days, M ≈ 1–2 weeks, L ≈ > 2 weeks.

| # | Improvement | Benefit | Complexity | Expected impact |
|---|---|---|---|---|
| 8.1 | **Scope-aware selection**: passages and records only in the latest user message; history governed by a budget. | Removes F-06; enables prefix caching | S | Eliminates the main multi-turn loss path |
| 8.2 | **Task-intent gate** (lexical rules, then a MiniLM head reusing the loaded encoder): `lookup/qa` → selection allowed; `summarize/translate/rewrite/review/extract-all` → narrative compression only, or none | Removes F-07 | S–M | Prevents the most common silent-loss class |
| 8.3 | **Context-window-aware budgeting**: read `litellm.get_model_info(model)["max_input_tokens"]`; compress only as much as needed to fit (or to hit a cost target); otherwise leave the prompt alone. Combine with `context_window_fallbacks`. | Compression becomes need-driven, not always-on | M | Less loss on prompts that already fit; no context-overflow errors |
| 8.4 | **Cache-stable compression**: memoise compressed text by `(sha256(text), model, rate)` in Redis; never re-select history; optionally inject Anthropic `cache_control` on the stable prefix | Prefix-cache hits plus fewer LLMLingua calls (second request on the same history ≈ 0 ms) | M | Large cost and latency win for chats and agents |
| 8.5 | **Cost/latency/complexity routing**: a LiteLLM `async_pre_call_hook` or `router_settings` tag-routing that sends short, simple prompts to a small model and long or complex ones to a large one, with the intent and size signals the pipeline already computes | Lower spend at the same quality | M | Typically 30–60 % spend reduction on mixed traffic (validate with the existing eval harness) |
| 8.6 | **Online quality safeguards**: (a) a "key-string survival" check after compression (identifiers, numbers, and quoted strings of the query must still be in the prompt, otherwise revert that block). This is cheap and already scored offline as `key_strings_kept_pct`. (b) Sampled shadow comparisons with LLM-as-judge on 1 % of traffic, written to Langfuse scores. | Turns offline guarantees into runtime ones | S (a) / M (b) | Catches regressions before users do |
| 8.7 | **Inference service extraction**: move MiniLM and LLMLingua-2 to a sidecar (FastAPI or Triton/ONNX Runtime) with dynamic batching and a GPU option; the proxy calls it with a deadline | Fixes F-05 and F-02 structurally; proxy RAM drops ~1 GB/worker; scales independently | L | Capacity ratio from 0.28× toward ≥ 1× |
| 8.8 | **Admission control**: skip compression (status `skipped:busy`) when the pipeline queue or semaphore is saturated or the estimated work exceeds the remaining budget | Graceful degradation instead of timeouts | S | Removes cascading fail-open |
| 8.9 | **Response cache** (exact first, semantic later only if measured hit-rate justifies it) | Free repeat answers | S | Depends on traffic; high for evals and agents |
| 8.10 | **Observability additions**: pipeline queue depth and in-flight gauges; orphaned-thread counter; `intent` and `scope` labels; per-request (not per-message) span attributes as aggregates to stay under the 128-attribute limit (F-23); SLO dashboards (fail-open rate, added latency p95, savings vs. cost) | Faster diagnosis | S | — |
| 8.11 | **Unified settings** with pydantic-settings, validated at startup, printed (secrets masked) | Fewer config errors (F-11, F-13) | S | — |

#### F-23 OTel span attribute explosion — **Medium** · VERIFIED (code + SDK default)
`observed_callback.py:243-247` sets 5 attributes **per message** (`prompt.message.{i}.*`) on one span. The OTel SDK default limit is 128 attributes per span (`opentelemetry/sdk/trace/__init__.py:81-82`), so for conversations of about 24 messages or more, attributes are **silently dropped**, including the request-level ones set later (`prompt.tokens.*`, cost). Fix: emit per-message details as span *events* or a single JSON attribute, and set request-level attributes first.

---

## 9. Prioritized Improvement Roadmap

### P0 — Critical: fix before any production traffic

| Item | Findings | Effort |
|---|---|---|
| Configure `router_settings`: timeouts, stream timeouts, retries with a retry policy, cooldowns, fallbacks / `context_window_fallbacks`, ≥ 2 deployments for critical model groups | F-01 | 1 d |
| Make pipeline work deadline-aware and cancellable; lock acquisition with timeout; bounded executor + admission control | F-02, 8.8 | 2–3 d |
| Request-level caps: max compressor calls and tokens per request; max input size gate | F-03 | 0.5 d |
| Restrict passage selection to the latest user message; add a multi-turn eval family | F-06, 8.1 | 1–2 d |
| Task-intent gate (lexical v1) so summarise/translate/review requests skip selection; add a summarisation eval family | F-07, 8.2 | 1–2 d |
| Reproducible image: pin base by digest, lock file with hashes, align transformers/litellm with tested versions, pin HF revisions, bake weights, `HF_HUB_OFFLINE=1` | F-19S | 1 d |
| Add CI (lint, unit tests, `docker build`, secret scan); fix the 2 failing tests | F-10 | 1 d |

### P1 — High: reliability, security, performance

| Item | Findings | Effort |
|---|---|---|
| Separate redaction guardrail: all roles, ignores opt-out, active in shadow mode, fail-closed. Document that sensitivity ≠ DLP. | F-15S | 2 d |
| Gateway healthcheck (`/health/liveliness`), `restart: unless-stopped`, memory/CPU limits | §6.2 #6 | 0.5 d |
| Default `LITELLM_BIND=127.0.0.1:`; auth on `/metrics` or internal-only scraping; require `POSTGRES_PASSWORD` and `OBS_HASH_SALT`; HMAC hashing | F-16S, F-17S, F-18S | 0.5 d |
| Move tokenisation and text joins off the event loop | F-04 | 0.5 d |
| Fix span attribute explosion | F-23 | 0.5 d |
| Enable the Redis response cache (opt-in per key or team) | F-16 | 0.5 d |
| Replace the paid/free-tier judge with a stable deployment | F-01 | 0.5 d |

### P2 — Medium: architecture and optimisation

| Item | Findings | Effort |
|---|---|---|
| Cache-stable compression (memoise by content hash; byte-stable history) | F-15, 8.4 | 1 week |
| Context-window-aware, need-driven compression budget | 8.3 | 1 week |
| Online key-string survival check with block revert | 8.6a | 2–3 d |
| int8 / ONNX Runtime for MiniLM; compressor instance pool | F-05 | 3–5 d |
| Embedding mini-batching and window cap | F-09 | 0.5 d |
| Grow the sensitivity-head training set (385 → 2–5k, incl. multi-turn and multilingual); track drift via `prompt_pipeline_classifier_top_score` | §7.1 | 1 week |
| Cleanup: dead env vars, stale references, single config, unified settings, log-level fix, counter double count, lint/type config | F-11–F-14, 8.11 | 1–2 d |
| Trim `spend_logs_metadata` to request-level aggregates | §6.2 #5 | 0.5 d |

### P3 — Future enhancements

| Item | Effort |
|---|---|
| Inference sidecar with dynamic batching and GPU option | 2–3 weeks |
| Cost/latency/complexity-based model routing using pipeline signals | 1–2 weeks |
| Sampled online LLM-as-judge quality scoring into Langfuse | 1 week |
| Conversation compaction (summarise old turns with a cheap model, cache the summary) instead of dropping turns | 1–2 weeks |
| Semantic cache, only if exact-cache hit rate and traffic analysis justify it | 1 week |
| Question-aware neural selection (e.g. a cross-encoder; `cross-encoder/ms-marco-MiniLM-L-6-v2` is already in the local HF cache) to replace BM25 where there is no lexical overlap | 1–2 weeks |

---

## 10. Testing and Validation Results

### 10.1 Existing test suites (run during the audit)

Environment: `.venv-compression`, Python 3.12.10, litellm 1.106.0, transformers 5.20.1, llmlingua 0.2.2, Windows 11, CPU.

| Suite | Command | Result | Duration |
|---|---|---|---|
| `prompt_compression/tests` | `python -m pytest -q` | **190 passed, 2 failed** | 10.5 s |
| `observability/tests` | `python -m pytest -q` | **15 passed** | 9.0 s |

Failures:
- `test_rules.py::test_rule_hits[OPENAI_API_KEY=[OPENAI_API_KEY_PLACEHOLDER]-openai_style_key]`
- `test_rules.py::test_rule_hits[sk_live_[STRIPE_KEY_PLACEHOLDER]-stripe_key]`

Cause: the fixtures were rewritten to placeholders (commit `4643804`) that don't match the rule regexes. The rules themselves are fine; the tests are broken (F-10).

### 10.2 Audit probes (written for this audit, run against the real modules)

The probe script imports the project's pipeline, hook and gate and uses the project's own test doubles (`tests/fakes.py`: `StubDetector`, `StubCompressor`) in place of the ML models. It writes nothing into the project. It lives outside the repo, in the audit session's scratchpad (`audit_validate.py`), and can be recreated from the descriptions below.

| Probe | Hypothesis | Result |
|---|---|---|
| V1 | Passage selection acts on earlier assistant turns | **CONFIRMED**: 4/8 assistant turns had passages dropped (931 → 713 tokens) |
| V11 | "Summarize the whole report" still triggers QA selection | **CONFIRMED**: 3 of 7 sections dropped |
| V2a | Prompt below `min_tokens` skips redaction | **CONFIRMED**: secret forwarded (11 tokens) |
| V2b | Client opt-out skips redaction | **CONFIRMED** |
| V2c | System messages are never redacted | **CONFIRMED** |
| V2d | Shadow mode skips redaction | **CONFIRMED** |
| V3 | Timed-out work keeps running and blocks the next request | **CONFIRMED**: req 1 and req 2 both `error` at ~1.0 s; 4 compressor calls finished in the background |
| V5 | Compressor-call cap is per message | **CONFIRMED**: 40 calls for one 41-message request |
| V4 | Gate tokenises synchronously on the event loop | **CONFIRMED**: 183–214 ms for a 2 MB prompt |
| — | LiteLLM default request timeout | **CONFIRMED**: 6,000 s (`litellm/constants.py:587`) |
| — | OTel span attribute limit | **CONFIRMED**: 128 (`opentelemetry/sdk/trace/__init__.py:81-82`) |
| — | Auth remains on without `master_key` in the mounted config | **CONFIRMED**: env fallback (`proxy_server.py:6923`) |

### 10.3 Missing test scenarios

| Area | Missing scenario |
|---|---|
| Context | Multi-turn chats where the question refers to earlier turns; summarisation, translation and review intents; agent loops with assistant prose between tool calls |
| Reliability | Timeout followed by a second request (lock contention); many-message requests vs. timeout; provider timeout, fallback and cooldown behaviour |
| Security | Redaction across all roles, below `min_tokens`, with opt-out, in shadow mode, on fail-open |
| Performance | Concurrency/soak test against the real models (not mocks) asserting a fail-open rate under load; memory ceiling with very large prompts |
| Integration | A CI job that boots the proxy with the hook (mock provider exists in `prompt_compression/dev/mock_openai_server.py`) and runs `evals/cases` |
| Observability | Span attribute count on long conversations; metrics with `NUM_WORKERS>1` (multiprocess registry) |
| Regression | Golden-file tests of compressed output for a fixed model revision (detects model or library drift) |

### 10.4 What could not be verified

- The Docker stack wasn't started (no live provider, Postgres, Redis or monitoring run), so runtime figures come from the project's own reports, cited as such.
- Real LLMLingua-2 and MiniLM latency weren't re-measured. Probes used doubles; lock and timeout semantics don't depend on the model.
- DB-stored models, virtual keys, budgets and team settings weren't accessible.
- The eval pipelines (`evals/run_evals.sh`, benchmark scorers) weren't re-run; they need the running stack.
- Whether the key-shaped strings in git history are real credentials wasn't determined (values weren't inspected beyond pattern counts).

---

## 11. Overall Production Readiness Assessment

### 11.1 Scorecard

| Dimension | Score (1–5) | Rationale |
|---|---|---|
| Architecture & design | 4 | Clean staged pipeline, small focused modules, good docs; the only structural issue is in-process model inference |
| LLM gateway (routing, fallback, LB) | 2 | Relies entirely on LiteLLM defaults; no timeouts, fallbacks or redundancy configured |
| Context engineering | 3 | Excellent single-turn QA and logs; unsafe scope for multi-turn and non-QA intents |
| Performance | 2 | Serialised inference, orphaned work, unbounded per-request cost |
| Caching | 1 | None enabled; prefix caching undermined |
| Reliability | 2.5 | Strong fail-open semantics, but timeouts cascade; no healthchecks or limits |
| Security | 3 | Good secret hygiene and privacy-first telemetry; redaction bypasses; supply chain unpinned |
| Observability | 4.5 | Unusually complete; minor attribute-limit and log-level issues |
| Testing | 3.5 | Strong unit coverage with doubles; no CI, no integration, no multi-turn tests; 2 failing |
| Code quality | 4 | Readable, consistent, well commented; minor dead config |
| Deployment | 2 | Floating image, version drift between tested and shipped, no healthcheck, runtime model downloads |
| **Overall** | **≈ 2.9 / 5** | **Pilot-ready, not production-ready** |

### 11.2 Readiness by usage mode

| Mode | Ready? | Conditions |
|---|---|---|
| Internal pilot, `PROMPT_COMPRESSION_MODE=shadow` | **Yes** | Add F-01 timeouts |
| Enforce mode, single-turn QA and log analysis, low concurrency | **Conditionally** | P0: F-01, F-02, F-03, pinned image |
| Enforce mode, chat or agent products, multi-user | **No** | All P0 plus F-15S, healthchecks and limits |
| Used as a PII/DLP control | **No** | Needs a dedicated redaction guardrail (F-15S) |

### 11.3 Bottom line

The hard part, a measured and conservative compression pipeline with first-class observability, is done and done well. What's missing is mostly **operational hardening** (timeouts, fallbacks, bounded and cancellable work, a pinned image, CI) and **two scope errors in context selection** (conversation history and task intent). The P0 list fixes both and takes about 1.5–2 engineer-weeks. After that, the system would be a credible production gateway for the workloads it was evaluated on. Cache-stable compression and inference extraction are the steps that would make it cost-effective at scale.

---

## 12. Remediation Status (implemented 2026-11-09)

The fixes below were implemented after the audit, in the working tree (nothing committed). Every code change has a
regression test named after its finding (`prompt_compression/tests/test_audit_fixes.py`,
`observability/tests/test_audit_fixes.py`).

### 12.1 Findings fixed

| Finding | Fix | Where |
|---|---|---|
| F-01 no timeouts/retries/cooldowns | `router_settings`: timeout 120 s, stream_timeout 300 s, 2 retries with a per-error `retry_policy` (no retries on 400/401/content policy), `allowed_fails: 3`, `cooldown_time: 30`, shared Redis state; `litellm_settings.request_timeout: 600`; judge model gets its own timeout. Validated against LiteLLM 1.106.0's `Router` (all keys accepted). | `litellm_config.yaml` |
| F-02 timed-out work keeps running and blocks later requests | New `deadline.py`. The pipeline runs under a deadline of 90 % of `TIMEOUT_S`; every model call checks it; model locks are waited for only until it passes; compression that runs out of time stops and sends a valid partial result. Pipelines run in a bounded per-callback pool; admission control skips (`busy`) instead of queueing. | `deadline.py`, `prompt_compression_callback.py`, `compressor_adapter.py`, `sensitivity.py`, `actions.py` |
| F-03 unbounded per-request compression | `PROMPT_COMPRESSION_MAX_CALLS_PER_REQUEST` (12; runs longest-first over all messages; cache hits free) and `PROMPT_COMPRESSION_MAX_INPUT_TOKENS` (32,000 → `too_large`). | `actions.py`, `gate.py`, `settings.py` |
| F-04 event-loop blocking | Token counting moved into the worker (`gate.size_check`); the observability wrapper no longer joins all message text up front. | `gate.py`, `prompt_compression_callback.py`, `observed_callback.py` |
| F-06 selection across earlier turns | `PROMPT_COMPRESSION_SELECTION_SCOPE=latest_user` (default): passages and records are only selected from the latest user message. `all` restores the old behaviour. | `router.py`, `pipeline.py` |
| F-07 task-blind selection | New `intent.py` (lexical, conservative). Summarise/translate/rewrite/review/key-points/every/whole … → no selection. `PROMPT_COMPRESSION_INTENT_GATE` switch. Intent is in the report, span and logs. | `intent.py`, `router.py`, `pipeline.py` |
| F-09 unbounded embedding batch | Encoder runs in mini-batches (`CLASSIFIER_BATCH_SIZE`, 32). | `embedding_classifier.py` |
| F-10 failing tests, no CI | Fixtures assembled at runtime (tests pass); CI workflow with ruff, both test suites, Compose validation, image build + offline model load, gitleaks. | `tests/test_rules.py`, `.github/workflows/ci.yml`, `ruff.toml`, `.gitleaks.toml` |
| F-11/F-12a dead and stale config | Dead `COMPRESSION_*` vars removed; Langfuse documented as required; stale `ai-features` / `compression_guardrail_instance` references removed; `config.yaml` marked as the non-Docker sample. | `.env.example`, `Dockerfile`, `litellm_config.yaml`, `compressor_adapter.py`, `config.yaml` |
| F-13 log level forced to INFO | Level follows `OBS_LOG_LEVEL` / `PROMPT_COMPRESSION_LOG_LEVEL`. | `observability/logs.py`, `settings.py` |
| F-14 kept-reason double count | Exact units re-assigned to passages are no longer counted as kept. | `router.py` |
| F-15 prefix-cache instability | Scope fix (F-06) plus a per-worker LRU of compressed outputs (`PROMPT_COMPRESSION_CACHE_SIZE`, 512): earlier turns are replayed byte for byte. Verified with real models: history identical across two different questions. | `compressor_adapter.py` |
| F-16 no response cache | Redis response cache enabled in `default_off` mode (opt-in per request/key), TTL 600 s. | `litellm_config.yaml` |
| F-15S redaction bypasses | New `redaction.py` guardrail: runs first, on every message and role, ignores the compression opt-out and size gate, applies in shadow mode and when compression is disabled; a failure rejects with 503 regardless of fail mode. | `redaction.py`, `prompt_compression_callback.py` |
| F-16S `/metrics` exposure | `LITELLM_BIND` defaults to `127.0.0.1:` in Compose itself. | `docker-compose.quickstart.yml` |
| F-17S default Postgres password | `POSTGRES_PASSWORD` is required (gateway, db and the monitoring exporter). | both Compose files |
| F-18S unsalted hashes | HMAC-SHA256 hashing; when `OBS_HASH_SALT` is empty the key is derived from `LITELLM_SALT_KEY`. Note: hash values change once (dashboards keyed on old hashes restart). | `observability/privacy.py`, `settings.py` |
| F-19S supply chain | Base image pinned to `litellm/litellm:v1.106.0@sha256:2e4c03…` (the tested version); all packages pinned to the tested set (`docker/requirements-image.txt`); both models downloaded at build time at pinned commits and run offline (`HF_HUB_OFFLINE=1`); `trust_remote_code=False` everywhere (llmlingua's own default is **True**, found during the fix); `.dockerignore` keeps `.env` and the virtualenvs out of the build context. | `Dockerfile`, `docker/`, `.dockerignore`, `settings.py`, `compressor_adapter.py`, `embedding_classifier.py`, `sensitivity.py` |
| F-20S key-shaped literals | Split so scanners do not match; HEAD now has 0 key-pattern hits. | `eval/build_dataset.py`, `tests/test_rules.py` |
| F-22S provider error text in logs | Only `error_message_hash` and `error_message_chars` are logged. | `observed_callback.py` |
| F-23 span attribute overflow | Request-level attributes set first; per-message attributes only for the latest `OBS_MAX_SPAN_MESSAGES` (16) messages, the rest counted in `prompt.messages.attributes_omitted`. | `observed_callback.py` |
| §6.2 #5 spend-log bloat | Spend logs keep the request summary plus the latest `PROMPT_COMPRESSION_SPEND_LOG_MESSAGES` (8) per-message entries (the eval scorers still read entry 0). | `prompt_compression_callback.py` |
| §6.2 #6 no healthcheck/limits | Gateway healthcheck on `/health/liveliness` (image Python, no curl needed), `restart: unless-stopped` on all services, `mem_limit` / `cpus`. | `docker-compose.quickstart.yml` |

### 12.2 Validation after the fixes

| Check | Result |
|---|---|
| `prompt_compression` tests | **226 passed** (was 190 passed / 2 failed; 34 new tests) |
| `observability` tests | **20 passed** (was 15; 5 new tests) |
| `ruff check .` (CI rule set) | clean (2 unused imports removed) |
| `docker compose config` (quickstart, quickstart + monitoring) | valid |
| LiteLLM `Router` with the new `router_settings` | all keys accepted; `retry_policy` parsed |
| Original audit probes | V1, V11, V2a–d no longer reproduce. V5: 12 calls (capped, was 40). V3: background calls halved with a stub that ignores deadlines; real model locks are deadline-aware (unit tests `test_f02_*`). V4's probe times the function directly, which now runs in the worker, not on the loop. |
| Real-model smoke test (offline, pinned revisions) | lookup: 3 passages dropped, ratio 4.3×; "summarize the whole report": intent `transform`, 0 passages dropped; multi-turn: earlier turn byte-identical across two questions, served from the compression cache; 11-token prompt with an AWS key: redacted although below the size gate |

### 12.3 Not done, and why

| Item | Reason |
|---|---|
| Image build verified locally | The Docker daemon wasn't running on the audit machine. The CI `image` job builds the image and loads both baked models offline. |
| pip hashes (`--require-hashes`) | Versions are pinned; producing hashes needs a resolver run against PyPI for the image's Python. Do it with `pip-compile --generate-hashes` once the image builds. |
| Second deployments / real `fallbacks` | Needs real provider credentials. The template is in `router_settings`. |
| Replacing the free-tier judge | A model/cost decision for the owner (comment added). |
| F-05 structural fix (inference sidecar / compressor pool) | Large (P3). Admission control and deadlines now degrade gracefully instead of cascading. |
| P2/P3 enhancements (context-window budgeting, cost/latency routing, online key-string check, LLM-judge sampling, compaction, semantic cache, neural selector, larger sensitivity training set) | Improvements rather than defect fixes. They need design decisions and/or labelled data. |
| Live eval families for multi-turn and summarisation (`evals/cases`) | Covered by unit tests. Live cases need the running stack to record baselines. |
| F-08 tokenizer per model | Metrics are already labelled cl100k_base; billing uses LiteLLM's own counts. |
