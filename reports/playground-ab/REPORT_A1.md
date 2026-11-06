# Prompt-compression A/B test through the LiteLLM Playground (run A1)

System under test: the LiteLLM proxy's `/v1/chat/completions` endpoint — the same endpoint the Admin UI
**Playground** calls — with the `prompt_compression` pipeline (`rules → embedding-based sensitivity
classifier → router → LLMLingua-2 compressor`) wrapped by `observability.observed_callback`. Baseline arm:
the identical request with `metadata.prompt_compression=false`, which makes the gate skip the pipeline and
forward the original prompt unchanged.

Every number below is computed by `scripts/analyze.py` from a file in `raw/`. Reproduce with:

```
.venv-compression/Scripts/python reports/playground-ab/scripts/ab_eval.py capture --run-id A1 --families qa logs code pii --limit 20
.venv-compression/Scripts/python reports/playground-ab/scripts/ab_eval.py llm     --run-id A1 --families qa logs code pii --limit 20
.venv-compression/Scripts/python reports/playground-ab/scripts/ab_eval.py throughput --run-id A1 --model obs-mock --levels 1 2 4 8 --per-level 20
.venv-compression/Scripts/python reports/playground-ab/scripts/analyze.py --run-id A1
```

## 1. Executive summary

- **Token reduction is small and concentrated in one content family.** Across 100 paired real-model requests
  (`raw/llm_A1.jsonl`), prompt tokens fell **1.10%** overall (42,489 → 42,022), entirely driven by the `qa`
  (prose) family at **5.19%** (9,005 → 8,538); `logs`, `code` and `pii` showed ~0% change. On the subset of
  11/100 items the pipeline actually rewrote, the reduction was **11.63%** — compression works as designed,
  it just rarely fires, because most of this dataset is code, log lines, or sensitive records that the
  router is built to protect verbatim.
- **Output quality held up on exactly the prompts that changed.** Accuracy on the 11-item "changed" subset
  was **100% → 100%** (no loss). Family-level accuracy moved from 92.0% → 93.0% overall (lost 1 / gained 2,
  McNemar p=1.0 — not significant at n=100). 96/100 compressed and baseline responses were byte-identical.
  Zero pipeline errors or timeouts across 100 real-model pairs and 80 mock-model pairs.
- **Compression adds real latency and cuts throughput sharply.** Paired mean latency rose **+1.25 s**
  (95% CI 0.35–2.21 s, excludes 0 → real effect) on top of a ~17.7 s baseline dominated by local CPU-only
  LLM inference. In a pure pipeline-overhead measurement against a zero-latency mock model, compression
  added a **p50 of 0.61 s / p95 of 2.65 s** per request. Under concurrent load (mock model, no LLM noise),
  compressed-arm throughput was **58–85% lower** than baseline at every concurrency level tested (1/2/4/8)
  and essentially flat as concurrency increased — a sign the classifier + LLMLingua-2 step is CPU-bound and
  doesn't parallelize on this host (8 vCPUs, Intel i7-10610U @1.8GHz).
- **Verdict: works as designed, but is not a net win on this representative mix.** The safety behaviour
  (protect code/structured/sensitive content, fail open, no accuracy loss where it did compress) is sound.
  As a cost/latency optimization it only pays off for prose-heavy, non-sensitive prompts; on a dataset
  that is 75% logs/code/PII it trades a ~1% token/cost saving for a measurable latency and throughput
  penalty. See §5 for the specific trade-offs and a confound in the raw data.

## 2. Scope and what "through the Playground" means here

The task asked for a baseline-vs-compressed comparison over a representative dataset, run through the
LiteLLM Playground. The Playground UI itself has no way to bulk-replay a dataset or flip a per-request
`metadata.prompt_compression` flag, so it is not practical for statistically meaningful A/B testing — it is
a single-request manual tool. Two things were therefore done:

1. **Manual Playground spot-check** (this session, browser-driven): selected model `obs-priced-llama` in
   the Chat tab, sent a qa-family prompt verbatim through the real UI. The assistant replied `7867`
   (correct), with the UI's own telemetry showing `In: 317` tokens sent to the model against an original
   prompt of 329 cl100k tokens — i.e., compression was visibly active and the answer was still correct.
   This confirms the pipeline behaves the same way through the UI as through the API.
2. **Scripted A/B replay against the identical endpoint** (`reports/playground-ab/scripts/ab_eval.py`,
   pre-existing in this repo and built explicitly for this purpose — see its module docstring), for the
   statistical comparison this report is based on. It calls the same `/v1/chat/completions` route with the
   same virtual key as the Playground, varying only `metadata.prompt_compression`.

## 3. Methodology

### 3.1 Code and configuration under test

| Item | Value |
|---|---|
| Git HEAD | `98266be29c14bbe86b6dd3c82d290856bd272bdb` (2026-11-04 12:25 +0530) |
| Working tree | Dirty: `prompt_compression/`, `observability/`, `litellm_config.yaml`, `docker-compose.quickstart.yml`, `reports/`, `tests/` have local changes (see `git status`). No changes were made to pipeline code during this run. |
| Active callback | `litellm_settings.callbacks` in `litellm_config.yaml`: `["otel", "langfuse_otel", "prometheus", "observability.observed_callback.observed_prompt_compression_instance"]` (wraps `prompt_compression.prompt_compression_callback`) |
| Pipeline settings | All `PROMPT_COMPRESSION_*` / `SENSITIVITY_*` / `CLASSIFIER_*` env vars are **unset** in `docker-compose.quickstart.yml` → every value in `prompt_compression/settings.py` is at its code default: rate 0.4, routes `narrative` only (`passages`/`records`/`history` disabled), sensitivity backend `embedding` (sensitivity-head, not the older zero-shot NLI), min tokens 50, timeout 10 s, fail mode `open`, edge-protection on. |
| Legacy env vars (`COMPRESSION_RATE`, `COMPRESSION_THRESHOLD_CHARS`, `COMPRESSION_MODEL` in `.env`) | **Not used by the active pipeline** — these belong to the old single-file `ai-features/compression.py` compressor, which is not the registered callback. |
| Classifier / compressor models observed at runtime | `sentence-transformers/all-MiniLM-L6-v2+sensitivity-head-v1` (classify), `microsoft/llmlingua-2-bert-base-multilingual-cased-meetingbank` (compress) |
| Models under test | `obs-mock` (local FastAPI echo server, `prompt_compression/dev/mock_openai_server.py` on host `:4010` — isolates pipeline overhead from model latency); `obs-priced-llama` (Ollama `llama3.2:3b` Q4_K_M, temperature 0, seed 7, max_tokens 24, test prices `$1e-6`/input and `$2e-6`/output token — **not real provider prices**, set only so spend is non-zero) |
| Gateway | `litellm-gateway-litellm-1` container, LiteLLM UI v1.105.0, Python 3.13.16, 8 vCPUs, Intel Core i7-10610U @1.80GHz (`docker exec ... nproc` / `cpuinfo`) |

### 3.2 Test dataset

`reports/compression-fit/data/{qa,logs,code,pii}.jsonl` — four families designed to cover distinct content
types the router treats differently:

| Family | n available | n tested | Content |
|---|---:|---:|---|
| `qa` | 40 | 20–25 | Mixed narrative + factual passages, single-fact question |
| `logs` | 40 | 20–25 | Structured log-line records, question about a specific line |
| `code` | 40 | 20–25 | Code snippets embedded in prose, question about the code |
| `pii` | 50 | 20–25 | Records containing case numbers / identifiers (sensitive) |

Each item is wrapped in a fixed instruction + document + question template (`build_prompt`), with a random
per-request nonce so provider-side prompt caching can't equalize the two arms.

### 3.3 Arms and passes

| Pass | Model | Purpose | Raw file | Pairs |
|---|---|---|---|---:|
| `capture` | `obs-mock` | Ground truth: exact text the gateway forwarded, exact cl100k token counts, pipeline-only latency (no model noise) | `raw/capture_A1.jsonl` | 80 |
| `llm` | `obs-priced-llama` | Real end-to-end: answer accuracy, provider-reported tokens, full-stack latency, cost | `raw/llm_A1.jsonl` | 100 |
| `throughput` | `obs-mock` | Concurrency sweep (1/2/4/8 workers, 20 requests/level/arm) for RPS and tail latency under load | `raw/throughput_A1_obs-mock.jsonl` | — |

All passes ran against the same running container, same model configs, same dataset, no code changes
in between.

### 3.4 Data-quality note (disclosed, not hidden)

The `llm_A1.jsonl` file was built incrementally across two sessions. During the extension run in this
session, the gateway container was unexpectedly recreated mid-run (see §5), which (a) produced 28 duplicate
`(item, arm)` rows for items 16–19 of each family — **removed** before analysis (`200→` deduplicated to
exactly one row per pair, verified complete: 100 unique items × 2 arms, all HTTP 200) — and (b) left those
same items running under extra CPU contention (a concurrent duplicate process plus a manual Playground
request). Measured effect: mean latency for items 16–19 (36/200 rows) is ~30–50% higher than for items 0–15
(164/200 rows) in **both** arms. This inflates the absolute latency figures in §4.2 somewhat but the paired
comparison (compressed − baseline, computed per item) is far less sensitive to shared background load than
the absolute numbers are, since contention hits both arms of a pair together.

## 4. Results

### 4.1 Token reduction

**Ground truth (capture mode, mock model, exact text comparison — `raw/capture_A1.jsonl`, n=80 pairs):**

| Family | n | Prompts changed | Tokens (orig → sent, cl100k) | Reduction |
|---|---:|---:|---|---:|
| qa | 20 | 8/20 (40%) | 6,720 → 6,418 | **4.49%** |
| logs | 20 | 0/20 | 10,754 → 10,754 | 0.00% |
| code | 20 | 0/20 | 10,546 → 10,546 | 0.00% |
| pii | 20 | 0/20 | 3,936 → 3,936 | 0.00% |
| **All** | **80** | **8/80 (10%)** | **31,956 → 31,654** | **0.95%** |

Key facts (identifiers/numbers the question depends on) were preserved in **100%** of prompts in both arms
in all four families (`key_strings_kept_pct` / `key_strings_kept_baseline_pct`), and the ground-truth answer
string remained present in the sent prompt in 100% of compressed cases (`answer_in_prompt_pct`).

**Real model (llm mode, `obs-priced-llama`, provider-reported `usage` — `raw/llm_A1.jsonl`, n=100 pairs):**

| Family | n | Prompt tokens (baseline → compressed) | Reduction | Total tokens reduction |
|---|---:|---|---:|---:|
| qa | 25 | 9,005 → 8,538 | **5.19%** | 5.13% |
| logs | 25 | 14,125 → 14,127 | −0.01% (noise) | −0.01% |
| code | 25 | 13,819 → 13,819 | 0.00% | 0.00% |
| pii | 25 | 5,540 → 5,538 | 0.04% | 0.04% |
| **All** | **100** | **42,489 → 42,022** | **1.10%** | **1.09%** |
| *Changed subset only* | *11* | *(11/100 items were actually rewritten)* | **11.63%** | — |

The real-model numbers corroborate the mock-model ground truth: token savings are real, modest in
aggregate, and concentrated almost entirely in prose. At the test prices configured for `obs-priced-llama`
($1e-6/input, $2e-6/output token — not real provider prices), this is **$0.4325 → $0.4278 per 1,000
requests** (**1.08%** cost reduction).

### 4.2 Performance

**End-to-end latency, real model, paired per item (`llm` pass, n=100):**

| Family | Baseline p50 | Compressed p50 | Baseline p95 | Compressed p95 | Mean diff (95% CI) |
|---|---:|---:|---:|---:|---|
| qa | 14.10 s | 13.99 s | 21.18 s | 27.43 s | +1.00 s (−0.20, 2.09) |
| logs | 21.18 s | 20.81 s | 33.84 s | 38.77 s | +1.10 s (−0.42, 2.61) |
| code | 20.23 s | 20.02 s | 37.67 s | 48.27 s | **+2.51 s (0.40, 5.19)** |
| pii | 9.01 s | 9.30 s | 27.31 s | 26.03 s | +0.39 s (−1.71, 2.38) |
| **All** | **17.55 s** | **17.94 s** | **32.64 s** | **38.10 s** | **+1.25 s (0.35, 2.21)** |

Absolute latencies are dominated by CPU-only local Ollama inference (seconds, not the pipeline itself), and
are inflated for a subset of items by the contention noted in §3.4. The all-family mean difference (+1.25 s,
CI excludes 0) and the code-family difference are statistically distinguishable from zero; qa/logs/pii are
not at this sample size. p95 consistently worsens more than p50 (fat right tail from compression calls).

**Pipeline-only overhead, no model noise (`capture` pass, mock model, n=80):**

| Family | Overhead mean | p50 | p95 | 95% CI |
|---|---:|---:|---:|---|
| qa | 1.645 s | 0.953 s | 3.593 s | (1.149, 2.165) |
| logs | 0.697 s | 0.604 s | 1.051 s | (0.579, 0.848) |
| code | 0.539 s | 0.492 s | 0.952 s | (0.455, 0.627) |
| pii | 0.532 s | 0.516 s | 0.760 s | (0.467, 0.596) |
| **All** | **0.853 s** | **0.610 s** | **2.649 s** | **(0.697, 1.04)** |

Even when nothing is rewritten (logs/code/pii), every request still pays for classification (≈0.5 s): the
pipeline runs segmentation + sensitivity scoring before deciding to leave the text alone.

**Throughput under concurrent load (mock model, 20 requests/level, `raw/throughput_A1_obs-mock.jsonl`):**

| Concurrency | Baseline RPS | Compressed RPS | Compressed vs baseline |
|---:|---:|---:|---:|
| 1 | 1.43 | 0.61 | −57% |
| 2 | 3.83 | 0.59 | −85% |
| 4 | 4.21 | 0.90 | −79% |
| 8 | 3.21 | 1.04 | −68% |

Baseline throughput scales up to ~4x as concurrency increases (I/O-bound passthrough), while compressed-arm
throughput stays essentially flat (0.6–1.0 RPS) regardless of concurrency — consistent with the
classifier/LLMLingua-2 step being CPU-bound and not parallelizing across concurrent requests on this
8-vCPU host. This is the clearest performance finding: **under load, the pipeline is a throughput
bottleneck**, independent of whatever it saves in tokens.

### 4.3 Output quality

| Family | n | Accuracy (baseline → compressed) | Lost | Gained | Same response |
|---|---:|---|---:|---:|---:|
| qa | 25 | 100% → 100% | 0 | 0 | 25/25 |
| logs | 25 | 96% → 96% | 1 | 1 | 23/25 |
| code | 25 | 80% → 80% | 0 | 0 | 25/25 |
| pii | 25 | 92% → 96% | 0 | 1 | 23/25 |
| **All** | **100** | **92% → 93%** | **1** | **2** | **96/100** |
| *Changed subset (compression actually fired)* | *11* | *100% → 100%* | *0* | *0* | — |

McNemar's exact test on the 3 discordant pairs (1 lost + 2 gained) gives p=1.0 — no statistically
significant accuracy change at n=100, and **zero regressions on the subset where compression actually
altered the prompt**, which is the cleanest read of "does compression hurt quality": it doesn't, here.
Zero pipeline errors or timeouts across all 180 pairs (100 llm + 80 capture).

### 4.4 Why most families show ~0% reduction (routing behaviour, not a defect)

`kept_reasons` and `actions` from the pipeline's own per-request report explain the family split:

- **logs**: segmented as `structured` (25 occurrences) — structured/tabular content is never sent through
  LLMLingua-2 by design (token-level compression damages field names/identifiers; see
  `reports/compression-fit/REPORT.md` §4/§7, the design rationale this pipeline is built on).
- **code**: segmented as `code` (221 occurrences) — code is always kept verbatim.
- **pii**: 100% classified `sensitive` (edge=25, sensitive=50 kept-reasons) — the sensitivity gate
  (embedding classifier + sensitivity-head) keeps it verbatim rather than risk compressing a protected span.
- **qa**: the only family that is mostly plain prose with low "exact-text density" — 11/25 items were
  routed to `compressed` (LLMLingua-2, `narrative` route), the rest kept for edge-protection or sensitivity.

`PROMPT_COMPRESSION_ROUTES` defaults to `narrative` only; `records` (selective log-line dropping) and
`passages` (BM25 passage selection) are implemented but disabled in this deployment's config, so the
`logs`/long-document families get no benefit from those routes in this test.

## 5. Trade-offs and limitations

- **Net effect is latency/throughput cost for a small, prose-only token saving.** On a dataset that is 75%
  logs/code/PII (realistic for many production traffic mixes), the pipeline saves ~1% of tokens/cost but
  measurably adds latency (+1.25 s mean, CI excludes 0) and sharply reduces throughput under concurrent load
  (−58% to −85% RPS). It is a net win only when traffic skews toward long, non-sensitive, non-structured
  prose and token cost matters more than latency/throughput headroom.
- **CPU is the bottleneck, not a provider.** This test ran the classifier and LLMLingua-2 on CPU
  (Intel i7-10610U, 8 vCPUs, no GPU). A GPU-backed deployment would likely narrow the latency/throughput gap
  substantially; these results should not be read as an upper bound on the architecture's potential, only as
  this configuration's measured behaviour.
- **Unplanned container restart mid-run** (`docker-compose.quickstart.yml` bind-mounts
  `./ai-features/compression.py`, a file no longer present in the working tree — `git status` shows it
  deleted; `ai-features/` no longer exists on disk at all) caused the recreate to fail once with
  `OCI runtime create failed: ... not a directory` before succeeding on retry. This is a **pre-existing
  repository inconsistency, unrelated to the pipeline under test or to this report's changes** — the
  active callback doesn't use `ai-features/compression.py` at all (see §3.1) — but it introduced the data
  duplication and contention noise disclosed in §3.4, and is worth fixing independently (e.g. drop that
  volume line from `docker-compose.quickstart.yml`, or restore an empty placeholder file) so future runs
  don't risk a failed container recreate.
- **Sample size.** 100 llm-mode pairs (25/family) and 80 capture-mode pairs (20/family) are enough to see
  the aggregate effects above, but family-level accuracy deltas (e.g. pii 92%→96%) are not statistically
  distinguishable from noise at n=25; treat per-family accuracy numbers as directional, not conclusive.
- **`passages`/`records`/`history` routes untested.** This run only exercises the default `narrative` route.
  The `logs` family in particular might show real reduction with `records` enabled — not measured here.

## 6. Verdict

The pipeline **does what its design intends**: it never compressed code, structured logs, or PII in this
test, it failed cleanly with zero errors/timeouts across 180 requests, and it produced zero accuracy
regressions on the 11 items it actually rewrote. That is a legitimate, working safety-first implementation.

It is **not, however, a net performance or cost win on a representative mixed-content workload** as
currently configured: aggregate token/cost reduction is ~1%, while mean latency increases by over a second
per request and throughput under concurrent load drops by more than half. The implementation is best
understood as a targeted optimization for long, non-sensitive prose prompts — where it reduces tokens by
~11% with no measured quality loss — rather than a general-purpose compressor for arbitrary gateway traffic.
Whether to run it in production should depend on how much of that production traffic actually looks like
the `qa` family here versus the `logs`/`code`/`pii` families, and whether CPU headroom exists for the
added classification + compression work on every request.
