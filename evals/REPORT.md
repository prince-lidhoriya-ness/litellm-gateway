# Evals: LiteLLM gateway with prompt compression

**Phase `litellm-eval`, 2026-11-08.** This runs the quality-gates toolkit's Gate 4 eval runner against the live gateway,
plus a scorer for the B2 benchmark results. Raw output is in `evals/results/litellm-eval/gate4.json` and
`compression.json`, in the quality-gates schema.

## 0. Update: re-run after both fixes (B3, phase `litellm-eval-b3`)

The two fixes from §4.1 and §4.2 were made, then the full benchmark was run again as **B3**: 680 capture requests, mock
and real-model throughput, and 170 real-model pairs. B3 ran the same dataset and scorer as B2.

**What changed in the code:**
- **Capacity:** the proxy now runs 2 workers × 4 torch threads (`LITELLM_NUM_WORKERS`, `PROMPT_COMPRESSION_TORCH_THREADS`
  in `docker-compose.quickstart.yml`), instead of 1 worker × 8 threads.
- **Sensitivity:**
  - The model no longer judges the instruction and question lines around a document. Rules still check them.
  - Each passage is scored on its own, in one batched model call (`check_many` / `score_many`), instead of
    200-token windows over the whole document.

**Result: all 23 live cases pass on both runs. The first run's p95 latency check missed by 84 ms; the rerun passed. The scorecard passes 17 of 19 checks:
the same two checks fail as before, but for different reasons.**

| Metric | B2 (before) | B3 (after) | Threshold | B3 |
|---|---:|---:|---|---|
| Live cases (Gate 4) | 23/23, p95 605 ms | 23/23, p95 2,084 ms, then 831 ms on rerun | p95 ≤ 2,000 | PASS (first run was warm-up noise) |
| Errors / timeouts | 0 | 0 | 0 | PASS |
| Prompt tokens saved (all) | 27.5% | 27.2% | ≥ 20% | PASS |
| qa / logs tokens saved | 35.4% / 63.0% | 34.0% / 63.0% | ≥ 25% / ≥ 40% | PASS |
| qa prompts changed | 97.5% | **100%** | ≥ 90% | PASS |
| Documents blocked whole by a borderline score | 1.25% | **0%** | ≤ 5% | PASS |
| Answers lost on changed prompts | 0 of 69 | 0 of 80 | 0 | PASS |
| Accuracy drop (all) | 0.0 pts | 0.6 pts (noise: flips on unchanged code/pii) | ≤ 2 | PASS |
| Real-model throughput gain | +38.9% | **+54.7%** | ≥ 0 | PASS |
| Mock req/s at c=8, compressed | 7.7 | **9.9 (+29%)** | — | — |
| Mock capacity ratio (compressed / baseline) | 0.241 | 0.282 | ≥ 0.5 | **FAIL** |
| False "sensitive" request labels | 0.150 (17 logs + 1 qa) | 0.233 (**0 logs** + 28 qa) | ≤ 0.10 | **FAIL** |
| PII kept verbatim | 100% | 100% | 100% | PASS |

**Capacity: improved, but still below target.**
- Compressed throughput rose by 29% in the full B3 run, and by 55% in the controlled test (8.4 → 12.9 req/s,
  `throughput_U_*`).
- The baseline also doubled with two workers, so the ratio only moved from 0.24 to 0.28.
- The remaining gap is the CPU cost of LLMLingua-2 and the classifier itself, not serialization. Reaching 0.5 needs a
  GPU, int8/ONNX models, or fewer LLMLingua-2 calls per request (§5).
- With real models the gateway is faster than without compression, by +55% throughput and −3.4 s mean latency.

**Sensitivity labels: the logs problem is fixed. A new, narrower qa false positive appeared.**
- All 17 false labels on logs prompts are gone. They came from the question line.
- The documents that a borderline score kept whole now compress, so qa prompts changed went from 97.5% to 100%.
- The 28 qa labels all come from one kind of sentence: a leadership succession such as *"After 6 years under …, leadership
  passed to … in 2009, who remains chief executive."*
  - The head scores these 0.38 to 0.69, reading them as employment news.
  - When a document was scored in 200-token windows, they were diluted. Scored as a passage on their own, they cross
    0.37.
- Impact is small:
  - Only that one passage (about 25 tokens) is kept verbatim.
  - Savings and answers are unaffected.
  - What is wrong is the request's `category` on dashboards.
- **Next fix:** add public leadership and succession sentences as hard negatives and retrain the head with
  `eval/train_sensitivity_head.py`, then re-check recall on the held-out sets. An alternative is to label a request
  sensitive only when sensitive text is more than a small share of it.

### 0.1 Retrained sensitivity head v2 (B4, phase `litellm-eval-b4`)

The next fix above was done:
- Training changes (`prompt_compression/eval/sensitivity_train.jsonl`):
  - Added 26 public leadership-history sentences as hard negatives. They were written fresh, not copied from the benchmark.
  - Added 14 confidential or personal employment and commercial items as positives, so the head still flags
    "the CEO is being pushed out, staff haven't been told".
- The trainer now also evaluates qa documents one passage at a time, the way the gateway scores them.
- The new threshold is 0.36.
- The gateway was restarted, and both workers loaded `sensitivity-head-v2`.

**Held-out checks (none used for training, `eval/results/sensitivity_head.md`):**

| Set | Head v1 recall / FPR | Head v2 recall / FPR |
|---|---|---|
| test (148) | 0.973 / 0.072 | 0.973 / 0.099 |
| fresh holdout (100) | 1.000 / 0.083 | 1.000 / 0.117 |
| qa company prose (112) | – / 0.000 | – / 0.000 |
| qa passages, one at a time (360) | flagged 28 of 40 docs | – / 0.006 |
| PII case notes (50) | 1.000 | 1.000 |

**Benchmark capture, 680 requests (B3 = head v1, B4 = head v2; `evals/score_capture.py B3 B4`):**

| Metric | B3 | B4 | Threshold | B4 |
|---|---:|---:|---|---|
| False "sensitive" request labels | 0.233 (28 qa) | **0.017 (2 qa)** | ≤ 0.10 | **PASS** |
| qa tokens saved (cl100k) | 36.6% | 38.9% | — | — |
| All tokens saved (cl100k) | 29.0% | 29.4% | — | — |
| qa / logs prompts changed | 100% / 100% | 100% / 100% | — | — |
| Key strings and answer kept in the prompt | 100% / 100% | 100% / 100% | 100 | PASS |
| PII kept verbatim | 100% | 100% | 100 | PASS |
| Errors | 0 | 0 | 0 | PASS |
| Live cases (Gate 4) | 23/23 | 23/23, p95 705 ms | p95 ≤ 2,000 | PASS |

**Status:**
- The sensitivity check now passes.
- The cost is a few more false alarms on general prose: 3 more of 111 on test, 2 more of 60 on holdout. Such text is kept
  verbatim, which costs some savings, but recall is unchanged.
- The real-model run (llm) was not repeated for B4. Head v2 changes only which passages are kept verbatim, and capture
  shows the answer and key strings reach the model in 100% of prompts. Re-run `ab_eval.py llm --run-id B4` before
  relying on accuracy numbers for v2.
- **One check still fails: capacity (0.28 vs ≥ 0.5).** That needs faster models (§5).
- Rollback: `git checkout prompt_compression/models/sensitivity_head.json`, or set `SENSITIVITY_THRESHOLD`.

Raw results: `evals/results/litellm-eval-b3/`, `litellm-eval-b3r/` (rerun), `litellm-eval-b4/` (Gate 4 with head v2; its
`compression.json` still scores the B3 run); benchmark files `reports/playground-ab/raw/*_B3*`, `capture_B4.jsonl`.
The sections below are the original B2 evaluation.

## 1. Verdict (B2, before the fixes)

**The app works as intended and the compression gives real gains: 40 of 42 checks pass.** Two checks fail, and both
point to component changes worth making before the gateway serves high-traffic, fast models:

| Part | Checks | Result |
|---|---:|---|
| Gate 4: live HTTP cases on the running gateway | 23 cases + 4 gate checks | **PASS**: 23/23 cases, 0 critical failures, p95 605 ms |
| Benchmark scorecard (B2 results vs `evals/thresholds.yaml`) | 19 checks | **FAIL**: 17/19 pass |
| Overall | 42 | **FAIL** on 2 checks: gateway capacity and false "sensitive" labels |

**What the evals confirm:**
- Every request is answered with no errors or timeouts.
- Token savings are 27% on the mixed workload, 52% on prose and logs.
- No answers were lost on the prompts that compression changed. Key facts reached the model in 100% of prompts.
- End-to-end latency is 3.5 s faster with the real model.
- Opt-out works. Code, PII, health text, system prompts and history are kept verbatim.

**What needs changing (§4):**
- **Capacity (high):** compression runs its models one call at a time inside one proxy process. In front of an instant
  model, the gateway delivers 24% of its uncompressed throughput.
- **Sensitivity labelling (medium):**
  - 15% of non-sensitive requests are labelled sensitive.
  - One borderline score kept a whole document uncompressed.
  - The score near the threshold changes with irrelevant text: the same document scores 0.22 to 0.38 depending only on
    its 8-character request tag.

## 2. What was evaluated

| Part | Tool | Input | What it proves |
|---|---|---|---|
| Live functional evals | `quality-gates/gates/gate4.py` (Gate 4, unchanged logic) | `evals/cases/litellm-gateway.yaml`, 23 cases generated by `evals/build_cases.py` from the benchmark dataset and the B2 capture run | The deployed gateway behaves correctly request by request, right now |
| Benchmark scorecard | `evals/score_results.py` (writes a gate-style `compression.json` through quality-gates `common.finish`) | `reports/playground-ab/raw/*_B2*` (680 paired requests, throughput runs) | The B2 numbers meet explicit acceptance thresholds |

**How the live cases check what reached the model.** Most cases call `obs-mock`, a capture mock that answers with the
exact messages the gateway forwarded, so a case can assert on the compressed prompt itself:
- the answer and the question must be present;
- a passage or log line that B2 dropped must be absent;
- with the opt-out flag, that same text must still be there.

One case calls the real model (`llama3.2:3b`) and checks its answer.

**Small changes made to run this:**
- **`gates/gate4.py`** gained two backward-compatible options:
  - `EVALS_DIR`, so a suite can live in the app's repository;
  - `{{env:NAME}}` substitution, so the API key stays out of the YAML.

  The default `evals/` suite still loads unchanged (smoke-tested). The copy in `jenkins-101/quality-gates` was not
  updated.
- **`evals/services.yaml`** uses `127.0.0.1` and not `localhost`: on Windows, `localhost` tries IPv6 first and added
  about 2 s to every call, which made the first run fail its p95 check.

## 3. Results

### 3.1 Gate 4: live cases (23/23 pass)

| Group | Cases | Checks |
|---|---|---|
| Health and access | liveness, readiness, auth-required, models, unknown-model | Gateway up and ready, 401 without a key, 400/404 (not 500) for an unknown model |
| Gate | short-prompt-untouched | A prompt under 50 tokens is forwarded unchanged |
| QA compression | qa-000, qa-001, qa-010 (compressed + opt-out) | Answer and question reach the model, an unneeded passage is dropped; opt-out forwards everything |
| Log selection | logs-000 (key=value), logs-005 (JSON records), compressed + opt-out | Answer line kept, an unrelated record dropped; opt-out unchanged |
| Kept verbatim | code-000, code-004, pii-000, pii-001 | Four sentences or lines across each document, plus the question, all present |
| Safety | sensitive-passage-kept | A health passage added to a long document is never dropped or compressed |
| Conversation | system-and-history-kept | System prompt and earlier turns survive when the last turn is compressed |
| Real model | real-model-answer | `llama3.2:3b` answers `7867` correctly from the compressed prompt |

Gate checks: pass rate 1.00 (min 0.95), critical failures 0 (max 0), tool errors 0, p95 latency 605 ms (max 2,000).

### 3.2 Benchmark scorecard (17/19 pass)

| Area | Metric | Value | Threshold | Result |
|---|---|---:|---|---|
| Reliability | errors, timeouts, fail-open events (680 requests) | 0 | max 0 | PASS |
| | worst pipeline time | 3,767 ms | max 5,000 (half the timeout) | PASS |
| Tokens | prompt-token reduction, mixed workload | 27.5% | min 20 | PASS |
| | reduction on qa + logs | 52.2% | min 40 | PASS |
| | qa / logs reduction | 35.4% / 63.0% | min 25 / 40 | PASS |
| | qa prompts changed | 97.5% | min 90 | PASS |
| | code / pii reduction (informational) | 0% / 0% | — | by design (no code route; PII protected) |
| Quality | answers lost on changed prompts (69) | 0 | max 0 | PASS |
| | accuracy drop, all families | 0.0 pts (88.2% → 88.2%) | max 2 | PASS |
| | key strings / answer still in prompt | 100% / 100% | min 100 | PASS |
| Performance | mean latency change, real model | −3.49 s | max 0 | PASS |
| | real-model throughput gain (worst of c=1, c=4) | +38.9% | min 0 | PASS |
| | pipeline overhead p50 / p95 | 22 ms / 432 ms | max 100 / 1,000 | PASS |
| | **capacity with an instant model (c=8)** | **0.24× baseline** | min 0.5 | **FAIL** |
| Sensitivity | **non-sensitive requests labelled sensitive** | **15% (18/120)** | max 10% | **FAIL** |
| | requests left uncompressed by that label | 1.25% (1/80) | max 5% | PASS |
| | PII forwarded verbatim | 100% | min 100 | PASS |

**Notes on the data:**
- The only answer changes were on prompts compression did not touch: code lost 1, and pii lost 9 / gained 10. This is
  the model's own run-to-run noise, not an effect of compression.
- Spend-log metadata is missing for 18 compressed `llm` rows. Their token counts come from the provider and are
  complete.

## 4. Findings and recommended component changes

### 4.1 HIGH: gateway capacity is capped by serialized model inference

**Evidence.** With an instant (echo) model the gateway serves 30–32 req/s uncompressed, but only 6.8–7.7 req/s with
compression. That rate barely rises from concurrency 1 to 8. The pipeline already runs in a worker thread
(`asyncio.to_thread`), but:
- every embedding call holds `EmbeddingSensitivityClassifier._lock` (`embedding_classifier.py:74`);
- every LLMLingua-2 call holds `_call_lock` (`compressor_adapter.py:59`);
- the proxy runs one process.

So at most one model call runs at a time for the whole gateway. With the slow local model this does not show:
throughput rose 39–60%. In front of fast hosted models, it becomes the bottleneck.

**Change, in order of effort:**
1. **Run more proxy workers or replicas** (for example `--num_workers 4`, or more containers behind the load
   balancer). Each worker loads its own MiniLM and LLMLingua-2 copy, roughly 1 GB of RAM per worker. This is a config
   change only.
2. **Batch the classifier.** Score all of a request's runs in one forward pass instead of one locked call per run.
3. **Lighter models.** Use ONNX Runtime or int8 builds of MiniLM and LLMLingua-2, which allow parallel sessions
   without the instance lock.
4. **For high traffic,** move the pipeline into a separate model service that scales on its own, with the gateway
   hook calling it.

**Re-measure** with the same throughput run and the `mock_capacity_ratio` check (target ≥ 0.5).

### 4.2 MEDIUM: false "sensitive" labels from the model, and unstable borderline decisions

**Evidence.**
- **The 17 logs labels:** all 17 are the question line ("What was the user id of request req-caa067?", "What is the
  customer id of order ORD-6035?"). The model reads these lookups as personal-data requests. The line is
  edge-protected, so it is never changed anyway. Only the request's category is wrong: savings are unaffected, but
  dashboards and alerts that count "sensitive" requests are inflated.
- **qa-028:** one prose run scored 0.383 against the 0.37 threshold, and all 11 blocks of the document were kept
  verbatim (331 tokens unsaved).
- **Instability:** re-scoring qa-028 while changing only the 8-character `[req:…]` tag gives 0.22 to 0.38. A decision
  this close to the threshold flips on irrelevant text.

**Change:**
1. **Don't send edge-protected units to the model** (the instruction and the question). They are kept verbatim
   regardless, and rules and topics still run on them, so safety is unchanged. This removes all 17 false labels. A
   one-line change in `PromptPipeline._classify` (`pipeline.py:151`).
2. **Decide per passage when the `passages` route is active,** not per run. Score each passage, batched, and protect
   only the flagged ones. A borderline score then protects one paragraph instead of the whole document.
3. **Optionally, strip volatile prefixes before scoring,** such as request tags and timestamps. Retrain the head with
   real labelled traffic collected in shadow mode, rather than the self-written set.

**Re-measure** with the `false_sensitive_rate` and `savings_blocked_rate` checks, and re-run
`eval/train_sensitivity_head.py` to confirm recall stays ≥ 0.95.

### 4.3 LOW: no savings on code

Code is about a third of the benchmark's tokens and saves 0%. This is by design: the exact-text guard keeps code
verbatim, and token-level compression damaged code in the research report. If code-heavy traffic matters, a
selection-style `code` route is the candidate. It would drop functions or classes the question doesn't name, the way
`records` drops log lines. It needs its own guard evaluation before use.

### 4.4 LOW: LLMLingua-2 is the whole latency tail

- On qa, classification takes about 100 ms at p50. LLMLingua-2 adds 0.5–1.1 s on the 7 of 34 changed prompts where it
  runs (worst case qa-032: 1,251 ms, two calls).
- Selection gives most of the savings (§3.2), so a stricter `PROMPT_COMPRESSION_MAX_CALLS`, or skipping LLMLingua-2
  after a passage selection, trades a few points of qa savings for a much lower p95.
- Measure it with `reports/playground-ab/scripts/token_budget.py` before changing the default.

## 5. Not covered by these evals (next additions)

- **Fault injection live:** the timeout case with `reports/pipeline-proof/scripts/inject_timeout.override.yml` restarts
  the gateway, so it is not part of the default suite.
- **Questions selection could get wrong:** vague or multi-hop questions ("summarise everything", facts split across
  passages). This is where the passage and record routes carry real risk.
- **Other request shapes:** streaming responses, tool calls, and non-English text.
- **Real traffic:** run `PROMPT_COMPRESSION_MODE=shadow` and score the logged reports with the same thresholds.

## 6. Reproduce

From `litellm-gateway/`, with the gateway on :4000 and Ollama running. The script starts the capture mock itself and
reads the key from `.env` without printing it.

```bash
bash evals/run_evals.sh litellm-eval
```

To regenerate the cases after the dataset or a benchmark run changes:

```bash
.venv-compression/Scripts/python evals/build_cases.py
```

To score another benchmark run:

```bash
RUN=B3 bash evals/run_evals.sh litellm-eval-b3
```

The exit code is 0 when every check passes and 1 otherwise, so it can run as a Jenkins stage next to the other gates.
