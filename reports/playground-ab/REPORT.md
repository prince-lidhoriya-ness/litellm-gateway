# Prompt compression: baseline vs optimized, tested through the LiteLLM Playground endpoint

**Run of record: B2** (2026-11-06). Earlier run A1 (full write-up in `REPORT_A1.md`) and the in-process token-budget runs
are kept as "before the fixes" references. Every number below comes from a file in `raw/`, computed by `scripts/analyze.py`
or `scripts/token_budget.py`.

## 1. Verdict

**The implementation achieves meaningful token reduction and a real end-to-end performance improvement, with no
measured loss of answer quality, after two fixes made during this test.** The trade-off is CPU work inside the gateway,
which caps gateway throughput when the model is very fast.

| Metric (170 paired real-model requests, `llama3.2:3b`) | Baseline | Compressed | Change |
|---|---:|---:|---:|
| Prompt (input) tokens | 70,102 | 50,845 | **−27.5%** |
| Total tokens | 70,765 | 51,501 | **−27.2%** |
| Prompt tokens on compressible content (qa + logs, n=80) | 36,911 | 17,633 | **−52.2%** |
| Answer accuracy, all families | 88.2% (150/170) | 88.2% (150/170) | 0 pts, McNemar p = 1.0 |
| Accuracy on the 69 prompts compression actually changed | 100% | 100% | 0 lost, 0 gained |
| Mean latency, paired per item | 13.09 s | 9.60 s | **−3.49 s** (95% CI −4.23 to −2.74) |
| p50 latency | 13.26 s | 7.33 s | −45% |
| Throughput with the real model, concurrency 1 / 4 | 0.062 / 0.072 req/s | 0.100 / 0.100 req/s | **+60% / +39%** |
| Pipeline overhead per request (echo model, so no LLM time) | — | p50 22 ms, mean 72 ms, p95 432 ms | added cost |
| Gateway throughput with an instant echo model | 30–32 req/s | 6.8–7.7 req/s | **−76%** (the trade-off) |
| Cost at the configured test prices | $0.0714 | $0.0522 | −27.0% |

- **Token reduction is meaningful but content-dependent.** Prose QA documents save 35%, log records 63%. Code saves 0%,
  because no route exists for it. PII records save 0% on purpose: sensitive text is kept verbatim.
- **It is faster end to end.** Fewer prompt tokens means less model prefill. Saved model time (−3.5 s mean) is about 50×
  the added pipeline time (+0.07 s mean). The gain will be smaller on a fast hosted GPU model, but the token and cost
  saving holds.
- **Before the fixes, the same test was not a win.** In run A1, tokens fell only 1.1% and latency rose 1.25 s. Two
  causes, both fixed (§5):
  - the zero-shot sensitivity model flagged most ordinary prompts as sensitive;
  - the two selection routes that produce most of the savings were switched off.

## 2. What was tested, and how the Playground fits in

**System under test.** The LiteLLM proxy (container `litellm-gateway-litellm-1`, image `litellm-gateway:llmlingua`,
8 vCPU Intel i7-10610U, CPU only), endpoint `/v1/chat/completions`. This is the same endpoint and virtual key the Admin UI
Playground uses. The `prompt_compression` pipeline runs as an `async_pre_call_hook`, wrapped by
`observability.observed_callback`:

```
gate -> segment + classify (rules.py, topics.py, embedding sensitivity head) -> router -> keep | select records/passages | LLMLingua-2 -> reassemble -> model
```

**The two arms.** Each item is sent twice, in random order:
- **Baseline:** the request with `metadata.prompt_compression = false`. The gate skips the pipeline and the original
  prompt goes to the model unchanged.
- **Compressed:** the identical request without that flag.

Nothing else differs between the arms.

**The Playground.** It is a single-request chat UI. It cannot replay a dataset or set the per-request flag, so:

1. **Manual Playground checks** (browser pane, signed in by the user) confirmed the behaviour through the real UI:
   - Before the fixes, an ordinary business-prose prompt was labelled `sensitive` and left uncompressed. Diagnosing this
     led to fix 1 in §5.
   - After the sensitivity fix, the same prompt scored 0.13 against the 0.37 threshold, was labelled `general`, and was
     compressed from 157 to 98 tokens (1.6×). The pipeline metadata and spend log showed the same result.
2. **A scripted A/B replay** (`scripts/ab_eval.py`) produced the statistics. It calls the same endpoint with the same key
   as the Playground, so a request from the script and one typed into the Playground take the same path.

## 3. Methodology

### 3.1 Dataset (`reports/compression-fit/data/`)

| Family | n | Content | Question / answer | What the router should do |
|---|---:|---|---|---|
| `qa` | 40 | Multi-paragraph business documents with one key fact among filler paragraphs | Single fact (number, name) | Select passages and compress prose |
| `logs` | 40 | Application log blocks (JSON lines, key=value) | Value from one specific record | Select the records the question names |
| `code` | 40 | Source files with surrounding prose | Fact about the code | Keep code verbatim |
| `pii` | 50 | Customer case notes with names, e-mails, phones and a `CASE-` reference | "What is the case reference number?" | Keep verbatim (sensitive) |

All 170 items were used. Each prompt is built as follows:

```
[req:<random 8-hex nonce>]
Answer the question using only the document below. …
Document:
<context>
Question: <q>
Answer:
```

The nonce is a fresh random value per request, with the same length in both arms. It defeats Ollama's prefix cache.

**Scoring.** An answer is correct when the expected answer string appears in the response (normalised). Families are
interleaved and the arm order is shuffled per item, so drift on the CPU host does not favour either arm.

### 3.2 Configuration under test (B2)

| Setting | Value |
|---|---|
| Sensitivity | rules.py → topics.py lexicon → `sentence-transformers/all-MiniLM-L6-v2` + trained logistic head, threshold 0.37 (`SENSITIVITY_BACKEND=embedding`) |
| Routes | `narrative,passages,records` |
| Guards | passages: ≥ 6 passages of ≥ 100 tokens, keep 50%; records: ≥ 10 lines, 1 context line |
| LLMLingua-2 | `microsoft/llmlingua-2-bert-base-multilingual-cased-meetingbank`, rate 0.4, max ratio 3.0, min 200 chars, max 6 calls |
| Gate / safety | min 50 tokens, timeout 10 s, fail **open**, mode **enforce**, edges protected (instruction and question never compressed) |
| Models | `obs-priced-llama`: Ollama `llama3.2:3b`, temperature 0, seed 7, max_tokens 24, test prices $1e-6 input / $2e-6 output per token (not real prices). `obs-mock`: local echo server on :4010 that returns the exact forwarded text |
| Code | git HEAD `98266be` plus the uncommitted working tree including this session's changes (§5). Nothing was changed during B2 |

### 3.3 Passes

| Pass | Model | Measures | File | Size |
|---|---|---|---|---:|
| `llm` | obs-priced-llama | accuracy, provider-reported tokens, end-to-end latency | `raw/llm_B2.jsonl` | 170 pairs |
| `capture` | obs-mock | exact forwarded text, key strings kept, pipeline-only overhead | `raw/capture_B2.jsonl` | 170 pairs |
| `throughput` | obs-mock | req/s at concurrency 1/4/8, 24 requests per level per arm | `raw/throughput_B2_obs-mock.jsonl` | 6 rows |
| `throughput` | obs-priced-llama | req/s at concurrency 1/4, 12 requests per level per arm | `raw/throughput_B2_obs-priced-llama.jsonl` | 4 rows |

**Data quality.**
- There were 0 HTTP errors, timeouts or fail-open events in 340 `llm` rows and 340 `capture` rows.
- The run was interrupted once by a session end and resumed from saved `(item, arm)` rows. No pair is duplicated.
- 35 of the 340 `llm` rows did not get their spend-log metadata joined (the per-row pipeline report; shown as `missing`
  in the status counts). Token counts come from the provider's `usage` field and are complete for all rows.

### 3.4 Statistics

- **Accuracy:** McNemar's exact test on discordant pairs.
- **Latency:** mean of the per-item paired difference (compressed − baseline) with a bootstrap 95% CI. Pairing cancels
  shared background load.
- **Noise floor:** the `code` and `pii` prompts are not changed by compression, so their two arms receive identical text
  apart from the nonce. Any accuracy difference there is model noise, and it measures how large a change must be to be
  real.

## 4. Results (run B2)

### 4.1 Token reduction

**Provider-reported tokens (`llm` pass):**

| Family | n | Prompt tokens, baseline → compressed | Prompt Δ | Total tokens Δ | Prompts reduced | Mean ratio |
|---|---:|---|---:|---:|---:|---:|
| qa | 40 | 14,389 → 9,296 | **−35.4%** | −35.1% | 34/40 | 1.55× |
| logs | 40 | 22,522 → 8,337 | **−63.0%** | −62.6% | 35/40 | 2.75× |
| code | 40 | 22,153 → 22,162 | 0.0% | 0.0% | 0/40 | 1.00× |
| pii | 50 | 11,038 → 11,050 | 0.0% | 0.0% | 0/50 (by design) | 1.00× |
| **All** | **170** | **70,102 → 50,845** | **−27.5%** | **−27.2%** | 69/170 | 1.54× |
| Changed prompts only | 69 | — | **−52.5%** | — | — | — |

Notes:
- The ±9–12 token differences on code and pii are nonce tokenisation noise.
- Completion tokens are almost unchanged (663 → 656). Answers stay the same length, so total-token savings track
  prompt-token savings.
- For "prompts reduced", the pipeline report was missing for 5 qa and 5 logs rows (§3.3). With the echo model, where
  every row has a report, 39/40 qa prompts and 40/40 logs prompts changed.

**Exact forwarded text (`capture` pass, cl100k tokens):**

| Family | Changed | Tokens, original → sent | Δ | Key strings kept | Answer still in prompt |
|---|---:|---|---:|---:|---:|
| qa | 39/40 | 13,396 → 8,309 | −38.0% | 100% | 100% |
| logs | 40/40 | 21,531 → 7,349 | −65.9% | 100% | 100% |
| code | 0/40 | 21,160 → 21,160 | 0% | 100% | 100% |
| pii | 0/50 | 9,812 → 9,812 | 0% | 100% | 100% |
| **All** | 79/170 | 65,899 → 46,630 | **−29.2%** | **100%** | **100%** |

Every identifier, number and expected answer the question depends on reached the model in every compressed prompt.

**Router actions taken (pipeline metadata):**

| Family | Action |
|---|---|
| qa | `selected_passages` 27, `selected_passages+compressed` 7, `sensitive` 1 |
| logs | `selected_records` 35 |
| code | `guarded` 36 (code and structured blocks kept verbatim) |
| pii | `sensitive` 46 (kept verbatim) |

Most of the savings come from dropping whole passages and records that the question does not need. LLMLingua-2 token
compression contributes the smaller share.

### 4.2 Performance

**End-to-end latency, paired per item (`llm` pass):**

| Family | p50 base → comp | p95 base → comp | Mean Δ (95% CI) |
|---|---|---|---|
| qa | 11.16 → 7.42 s | 14.19 → 9.62 s | **−3.81 s** (−4.29, −3.35) |
| logs | 17.70 → 6.35 s | 23.92 → 9.40 s | **−11.38 s** (−12.38, −10.50) |
| code | 17.24 → 17.28 s | 22.26 → 21.16 s | +0.33 s (−0.44, 1.10), not significant |
| pii | 6.97 → 7.06 s | 8.81 → 9.04 s | +0.01 s (−0.27, 0.29), not significant |
| **All** | **13.26 → 7.33 s** | **21.51 → 18.98 s** | **−3.49 s** (−4.23, −2.74) |

On a CPU-served model, latency is dominated by prompt prefill. Cutting a logs prompt by 63% cuts its latency by 64%.
Where nothing is removed (code, pii), the added overhead is too small to measure next to model time.

**Pipeline overhead alone (`capture` pass, echo model, compressed minus baseline latency):**

| Family | Mean | p50 | p95 | 95% CI of the mean |
|---|---:|---:|---:|---|
| qa | 235 ms | 104 ms | 722 ms | 149–330 ms |
| logs | 20 ms | 20 ms | 42 ms | 14–25 ms |
| code | 28 ms | 21 ms | 59 ms | 21–36 ms |
| pii | 18 ms | 17 ms | 39 ms | 15–21 ms |
| **All** | **72 ms** | **22 ms** | **432 ms** | 48–99 ms |

Classification and selection cost about 20 ms. The qa tail comes from LLMLingua-2 calls, about 0.2–1 s each on this CPU.
In the real-model run the worst single pipeline time was 3.8 s, which is under the 10 s fail-open budget.

**Throughput:**

| Model | Concurrency | Baseline req/s | Compressed req/s | Δ | p50 latency, base → comp |
|---|---:|---:|---:|---:|---|
| llama3.2:3b | 1 | 0.062 | 0.100 | **+60%** | 16.6 → 8.5 s |
| llama3.2:3b | 4 | 0.072 | 0.100 | **+39%** | 56.3 → 42.5 s |
| echo mock | 1 | 30.0 | 6.8 | −77% | 0.03 → 0.06 s |
| echo mock | 4 | 30.1 | 7.2 | −76% | 0.13 → 0.41 s |
| echo mock | 8 | 31.9 | 7.7 | −76% | 0.24 → 0.75 s |

- **With a real model**, the system handles more requests per second because each request costs the model less.
- **With an instant model**, the pipeline becomes the bottleneck. It holds the proxy at about 7 req/s on this 8-vCPU
  host, barely rising with concurrency, because the model inference inside the hook is CPU-bound in one proxy worker.
  This is the capacity cost of the feature. A deployment in front of fast hosted models at high request rates needs
  more proxy workers or replicas, or a GPU, to keep the same headroom.
- The mock rows use a shuffled mix of 24 qa, logs and code items.

### 4.3 Output quality

| Family | n | Accuracy base → comp | Lost | Gained | Identical responses | Prompt changed? |
|---|---:|---|---:|---:|---:|---|
| qa | 40 | 100% → 100% | 0 | 0 | 37/40 | yes (−35%) |
| logs | 40 | 100% → 100% | 0 | 0 | 40/40 | yes (−63%) |
| code | 40 | 87.5% → 85.0% | 1 | 0 | 38/40 | no |
| pii | 50 | 70% → 72% | 9 | 10 | 26/50 | no |
| **All** | **170** | **88.2% → 88.2%** | 10 | 10 | 141/170 | — |
| **Changed prompts only** | **69** | **100% → 100%** | **0** | **0** | — | yes (−52.5%) |

- **No regression where compression acted.** On all 69 prompts the pipeline rewrote, accuracy was 100% in both arms:
  0 answers lost and 0 gained. On logs, all 40 responses were byte-identical across arms.
- **Every discordant pair came from unchanged prompts.** All 10 lost and 10 gained answers are in code and pii, where
  the two arms sent the same text apart from the nonce. The pii swings (9 lost, 10 gained, only 26/50 identical
  responses) are the 3B model's own instability on those notes. That is the noise floor of this test. It also shows the
  qa and logs results are not luck: they changed the prompt heavily and moved no answers.
- **Relevance:** answers were short and extractive (max 24 tokens), so "relevant" and "correct" coincide here.
  Completion lengths match across arms (663 vs 656 tokens), so compression did not make the model ramble or truncate.
- **Not significant:** McNemar p = 1.0 overall and in every family.

## 5. Before vs after: what was fixed during the test

### 5.1 Run A1, the configuration as found (`raw/results_A1.json`, 100 pairs)

| Metric | A1 (before) | B2 (after) |
|---|---:|---:|
| Prompt token reduction, all | 1.1% | **27.5%** |
| qa / logs reduction | 5.2% / 0.0% | **35.4% / 63.0%** |
| Requests labelled `sensitive` | 81/100 (all 25 qa) | 64/152 with a report (46 pii + 17 logs + 1 qa) |
| Mean latency Δ (paired) | +1.25 s (CI 0.35–2.21) | **−3.49 s** (CI −4.23 to −2.74) |
| Pipeline overhead p50 (echo model) | 610 ms | **22 ms** |
| Accuracy, all, base → comp | 92% → 93% | 88.2% → 88.2% (different item set: 170 vs 100) |

### 5.2 Fix 1: the sensitivity check flagged ordinary prompts

**Cause.** The zero-shot NLI model `typeform/distilbert-base-uncased-mnli` could not separate sensitive from ordinary
text. At its 0.35 threshold it kept 97% recall only by flagging 68% of non-sensitive test prompts (76% on dev) and 79% of
plain company prose. Examples it flagged: "Convert 72 degrees Fahrenheit to Celsius", "The river flows through three
countries". Evidence: `raw/sensitivity_variants.json`, `raw/sensitivity_decisions.json`.

**Fix** (`prompt_compression/sensitivity.py`, `topics.py`, `embedding_classifier.py`):
- `rules.py` patterns, then a `topics.py` lexicon (health, abuse, employment, personal finance, legal, identity,
  non-public company news), then a trained head on MiniLM sentence embeddings.
- The head's threshold is 0.37, the largest value with 5-fold cross-validated recall ≥ 0.95.
- The NLI backend stays available through `SENSITIVITY_BACKEND=nli`.

| Decision (rules or topics or head) | Recall | False-positive rate |
|---|---:|---:|
| Test set (37 sensitive / 111 not) | 0.973 | 0.072 |
| Fresh holdout, written before scoring (40 / 60) | 1.000 | 0.083 |
| qa prose paragraphs (112, none sensitive) | — | 0.000 |
| pii notes (50, all sensitive) | 1.000 | — |
| Old NLI backend, test set | 0.973 | 0.676 |

Scoring time is about 16 ms per text, against about 0.5 s for the NLI model.

### 5.3 Fix 2: the routes that give most of the savings were off

**Cause.** The configuration as found ran only the `narrative` route (LLMLingua-2 on prose):
- **logs:** never touched, because log lines are exact text by design.
- **qa:** most prose runs fell under the 200-character minimum.
- **passages/records routes:** off, and their guards (300 tokens / 20 lines) were too high to fire on typical prompts
  even when switched on.

`scripts/token_budget.py` runs the real pipeline in-process on the same prompts and shows the effect of each change:

| Config | Routes | min_chars | Passage / record guards | qa saved | logs saved | qa pipeline ms |
|---|---|---:|---|---:|---:|---:|
| before | narrative | 200 | 300 / 20 | 11.1% | 0.0% | 994 |
| C1 | narrative | 100 | 300 / 20 | 20.8% | 0.0% | 2,972 |
| C2 | all three | 100 | 300 / 20 | 20.8% | 0.0% | 3,030 |
| **C3 (adopted)** | **all three** | **200** | **100 / 10** | **39.1%** | **66.1%** | **250** |
| C4 | all three | 100 | 100 / 10 | 45.1% | 66.1% | 1,555 |

- **C3 was adopted.** The passage/record guards of 100 tokens / 10 lines are the ones `prompt_compression/eval/guard_eval.py`
  validated at accuracy 1.000. C3 is also faster than "before", because selection drops text before LLMLingua-2 has to
  process it. B2 confirms C3 end to end on the real model (§4).
- **C4 was rejected.** It adds 6 points on qa for 6× the pipeline time, and its 100-character minimum is not
  quality-validated.
- **Files changed:** `prompt_compression/settings.py` (defaults), `prompt_compression.env.example`, `prompt_compression/README.md`,
  `docker-compose.quickstart.yml`.
- **Also fixed there:** the compose file had a stale bind mount of `ai-features/compression.py`, which no longer exists,
  and it broke container restarts. The mount was removed, and the env vars are now passed through.

## 6. Trade-offs and limitations

1. **Gateway CPU and capacity.** The hook runs two CPU models in the proxy process. In front of an instant model,
   throughput fell from 30 to 7 req/s (−76%). In front of the slow local model it rose 39–60%.
   - The break-even depends on model speed and prompt size.
   - For fast hosted models at high request rates, budget extra proxy workers or replicas, or a GPU.
   - On the qa family, the 95th-percentile overhead is about 0.7 s.
2. **Selection risk.** Most of the savings come from dropping whole passages and log records. The question must name
   what it needs.
   - On this dataset, the needed text was kept 100% of the time.
   - Vague or multi-hop questions (for example "summarise everything", or a fact split across passages) are where
     selection could drop needed context. They are not covered here.
   - The guards make selection fire only on long material, and the question and instruction are never altered.
3. **No savings on code.** No code route exists, so code-heavy prompts pay the 20–60 ms check and save nothing.
   This is a design gap, not a defect.
4. **Sensitive prompts are never compressed.** This is intended. The pii family therefore saves 0%.
5. **Sensitivity labelling quirks.**
   - Lookup questions such as "What was the user id of request req-…" are flagged by the head (17 logs requests labelled
     `sensitive`). Only the request label is affected: the question line is kept anyway, and the records were still
     selected.
   - About 7–8% of ordinary prompts are false alarms (company revenue, mortgage-rate news). Those are kept verbatim and
     only cost savings, never correctness.
   - I wrote both the training set and the holdout, so these numbers may be optimistic. Run in
     `PROMPT_COMPRESSION_MODE=shadow` on real traffic first and check the labels.
6. **Test scope.**
   - One 3B model on CPU, single-turn prompts, short extractive answers, and synthetic but representative documents.
   - Latency gains will be smaller on GPU-served or hosted models. Token and cost reductions carry over.
   - Free-form generation quality (summaries, long answers) was not scored.
7. **Open issues outside the test.**
   - Two placeholder-key tests in `prompt_compression/tests/test_rules.py` fail, and were failing before this work. The
     suite otherwise passes: 182 passed in `prompt_compression`, 15 in `observability`.
   - DB-stored models fail to decrypt ("Unsupported provider"), which suggests a salt-key mismatch. This does not affect
     the config-file models used here.

## 7. Conclusion

- **Token reduction:** yes. Prompt and total tokens fell 27% across a mixed workload, 52% on the prompts the pipeline
  acts on, and up to 63% on logs. Every key fact reached the model.
- **Performance:** yes end to end on this deployment: −3.5 s mean latency and +39–60% throughput with the real model.
  The pipeline's own cost is 22 ms at p50 and 0.43 s at p95. Against an instant model, it lowers the gateway's capacity
  ceiling by about 4×.
- **Quality:** no measured impact. On the 69 changed prompts, 0 answers were lost and 0 gained. Every accuracy difference
  in the run came from prompts compression did not change.
- **Recommendation:** adopt the B2 configuration, which is now the code default:
  - run in `shadow` mode on real traffic first, to confirm the sensitivity labels and selection on real questions;
  - size proxy CPU for the added work;
  - add a code route if code-heavy traffic is significant.

## 8. Reproduce

From `litellm-gateway/`, with the gateway up and the echo mock running:

```bash
.venv-compression/Scripts/python reports/pipeline-proof/scripts/capture_mock.py --port 4010
```

```bash
.venv-compression/Scripts/python reports/playground-ab/scripts/ab_eval.py llm --run-id B2
```

```bash
.venv-compression/Scripts/python reports/playground-ab/scripts/ab_eval.py capture --run-id B2
```

```bash
.venv-compression/Scripts/python reports/playground-ab/scripts/ab_eval.py throughput --run-id B2 --model obs-mock --levels 1 4 8 --per-level 24
```

```bash
.venv-compression/Scripts/python reports/playground-ab/scripts/ab_eval.py throughput --run-id B2 --model obs-priced-llama --levels 1 4 --per-level 12
```

```bash
.venv-compression/Scripts/python reports/playground-ab/scripts/analyze.py --run-id B2
```

```bash
.venv-compression/Scripts/python reports/playground-ab/scripts/token_budget.py --tag C3
```

```bash
.venv-compression/Scripts/python -m prompt_compression.eval.train_sensitivity_head
```

The runs resume automatically: rows already saved for an `(item, arm)` pair are skipped.
