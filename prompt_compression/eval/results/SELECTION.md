# Classifier selection (2026-11-03)

Hardware: Intel Core i7-10610U (4 cores, 1.8 GHz), 32 GB RAM, CPU only, torch 2.15.0+cpu,
transformers 5.20.1, Python 3.12.10. One benchmark process at a time; latency is per prompt
(all 4 label hypotheses in one batched forward pass), after 3 warm-up calls. Models run in float32.

Dataset: `eval/classifier_dataset.jsonl`, 220 hand-written examples (55 per class, 38 hard negatives).
Fixed split (seed 13): dev 72 (18 per class), test 148 (37 per class). The test set was scored only
for the final comparison below.

## Step 2: baseline label format (dev)

| model | format | sensitive recall | macro-F1 | p95 ms |
|---|---|---|---|---|
| typeform/distilbert-base-uncased-mnli | plain | 0.389 | 0.185 | 221.5 |
| typeform/distilbert-base-uncased-mnli | **descriptive** | **0.889** | **0.288** | 236.5 |

Descriptive wins on both metrics, so it is the protocol format for the test comparison.

## Step 3: candidates checked

| model | encoder | params | license | card NLI result | source | status |
|---|---|---|---|---|---|---|
| MoritzLaurer/deberta-v3-base-zeroshot-v2.0 | DeBERTa-v3 | 184M | MIT | 28-task zero-shot mean F1 0.643 (bart-large-mnli: 0.497) | https://huggingface.co/MoritzLaurer/deberta-v3-base-zeroshot-v2.0 | shortlisted |
| MoritzLaurer/DeBERTa-v3-base-mnli-fever-anli | DeBERTa-v3 | 184M | MIT | MNLI-m 0.903, MNLI-mm 0.903, ANLI-all 0.579 | https://huggingface.co/MoritzLaurer/DeBERTa-v3-base-mnli-fever-anli | shortlisted |
| MoritzLaurer/deberta-v3-xsmall-zeroshot-v1.1-all-33 | DeBERTa-v3 | 71M | MIT | MNLI-m 0.925 (binary NLI, not comparable to 3-way) | https://huggingface.co/MoritzLaurer/deberta-v3-xsmall-zeroshot-v1.1-all-33 | shortlisted |
| MoritzLaurer/deberta-v3-large-zeroshot-v2.0 | DeBERTa-v3 | 435M | MIT | 28-task mean F1 0.673 | https://huggingface.co/MoritzLaurer/deberta-v3-large-zeroshot-v2.0 | not shortlisted: 2.4x base, and base already misses 300 ms here |
| MoritzLaurer/DeBERTa-v3-large-mnli-fever-anli-ling-wanli | DeBERTa-v3 | 435M | MIT | MNLI-m 0.912 | https://huggingface.co/MoritzLaurer/DeBERTa-v3-large-mnli-fever-anli-ling-wanli | not shortlisted: same reason |
| MoritzLaurer/mDeBERTa-v3-base-xnli-multilingual-nli-2mil7 | mDeBERTa-v3 | 279M | MIT | XNLI (multilingual) | https://huggingface.co/MoritzLaurer/mDeBERTa-v3-base-xnli-multilingual-nli-2mil7 | not shortlisted: bigger than base, eval set is English |
| cross-encoder/nli-deberta-v3-base | DeBERTa-v3 | 184M | Apache-2.0 | MNLI-mm 0.900 | https://huggingface.co/cross-encoder/nli-deberta-v3-base | not shortlisted: same size/latency class as the two base models |
| tasksource/ModernBERT-base-nli | ModernBERT | 150M | Apache-2.0 | - | https://huggingface.co/tasksource/ModernBERT-base-nli | not shortlisted: outside the listed encoder families |
| vllm-sr/d3-* (newest zero-shot uploads on the Hub) | Qwen3.5 decoder | 4.5B-8.4B | Apache-2.0 | - | https://huggingface.co/vllm-sr/d3-flash | excluded: not BERT-family, far beyond CPU budget |
| typeform/distilbert-base-uncased-mnli (baseline) | DistilBERT | 67M | **not stated on card ("License: Unknown")** | MNLI 0.820 / MNLI-mm 0.820 | https://huggingface.co/typeform/distilbert-base-uncased-mnli | baseline |

## Step 4: held-out test comparison (protocol format = descriptive)

| model | sensitive recall | sensitive precision | macro-F1 | p50 ms | p95 ms | params | passes switch rule? |
|---|---|---|---|---|---|---|---|
| **typeform/distilbert-base-uncased-mnli (baseline)** | **0.919** | 0.374 | 0.307 | 139.6 | 194.4 | 67M | - |
| MoritzLaurer/deberta-v3-base-zeroshot-v2.0 | 0.460 | 1.000 | 0.445 | 450.1 | 691.5 | 184M | no: recall lower, latency over budget |
| MoritzLaurer/DeBERTa-v3-base-mnli-fever-anli | 0.054 | 0.500 | 0.322 | 468.3 | 763.6 | 184M | no: recall lower, latency over budget |
| MoritzLaurer/deberta-v3-xsmall-zeroshot-v1.1-all-33 | 0.000 | 0.000 | 0.284 | 139.8 | 213.6 | 71M | no: recall lower, macro-F1 lower |

Supplementary, not used for the decision (plain labels, which the DeBERTa models prefer on dev):

| model | sensitive recall | macro-F1 | p95 ms |
|---|---|---|---|
| MoritzLaurer/deberta-v3-base-zeroshot-v2.0 | 0.405 | 0.392 | 495.6 |
| MoritzLaurer/DeBERTa-v3-base-mnli-fever-anli | 0.730 | 0.519 | 892.3 |
| MoritzLaurer/deberta-v3-xsmall-zeroshot-v1.1-all-33 | 0.811 | 0.291 | 213.3 |

Even in their best format, every candidate has lower sensitive recall than the baseline (0.919),
and the two that gain macro-F1 miss the 300 ms p95 budget on this CPU.

Also tried on dev to fit the budget: int8 dynamic quantization of the two base models
(`--quantize int8`). Macro-F1 fell to 0.12-0.26 and p95 stayed at 394-561 ms, so it was dropped.

**Decision: keep the baseline `typeform/distilbert-base-uncased-mnli`, descriptive labels.**
Rule: switch only if sensitive recall is not lower, macro-F1 is at least +0.02, and p95 <= 300 ms.
No candidate met it.

## Production classifier on test (rules + confidence fallback 0.6 + chunking)

`test__full-pipeline__typeform--distilbert-base-uncased-mnli.json`: macro-F1 0.333, p50 114.7 ms,
p95 162.9 ms. Label recall for `sensitive` drops to 0.540 because low-confidence sensitive
predictions fall back to `critical`; routing outcome is what matters:

| | result |
|---|---|
| gold sensitive kept uncompressed (sensitive or critical) | 37/37 |
| gold sensitive or critical kept uncompressed | 73/74 |
| rule hits | 19, all on gold sensitive (0 false positives on test) |
| gold non_sensitive / less_important that get compressed | **6/74** |
| decisions by source | 118 low-confidence fallback, 19 rules, 11 model |

The baseline's top score is below 0.6 for about 90% of prompts (test deciles: 0.38 ... 0.60),
so with `CLASSIFIER_MIN_CONFIDENCE=0.6` the pipeline is safe but compresses little.
Dev-set trade-off (model-only predictions, threshold applied afterwards; 36 protected / 36 compressible):

| threshold | protected wrongly compressed | compressible compressed |
|---|---|---|
| 0.30 | 5/36 | 14/36 |
| 0.40 | 3/36 | 13/36 |
| 0.45 | 2/36 | 8/36 |
| 0.50 | 1/36 | 3/36 |
| 0.60 (default) | 0/36 | 2/36 |
