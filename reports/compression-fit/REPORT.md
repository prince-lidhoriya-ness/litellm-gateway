# Which prompt compressor for which task

Decision report for the LiteLLM gateway, prepared 2026-11-05. It rests on twelve prompt-compression methods from the `llm-prompt-compression` research repo, ten primary papers fetched from arXiv (the repo's PDFs are mostly the wrong papers, section 3.0), and a local benchmark on this machine (CPU only, llama3.2:3b). Every number is tagged with its source: a paper and page, or a local run file. "Not reported" means the source does not say and nothing was estimated. The research repo was not changed and nothing was committed.

## 1. Answer first

**Is any single compressor suitable for all tasks? No.** Three independent kinds of evidence say so, and they agree.

1. **The papers** show the same method winning on one task and losing on another. LLMLingua-2 at 5x scores 58.9 on LongBench's Code column against 54.2 uncompressed, but 21.3 on its Synthetic column against 37.8 [L2-034: Table 2 p.7; L2-043: Table 2 p.7]. On NaturalQuestions with 20 documents at about 4x, a question-agnostic compressor (LLMLingua-2) scores 39.9 to 48.6 where a question-aware one (LongLLMLingua) scores 71.2 to 75.0 [L2-059: Table 11 p.18; LongLL-CL-4: Table 1 p.7]. The verdict also flips with the metric: LLMLingua-2 on MeetingBank has ROUGE-1 above the original and ROUGE-2 and BLEU well below it [L2-040: Table 1 p.6; L2-042: Table 1 p.6] (section 2).
2. **The local run** (same 40 items per family, same model, ratios matched to about 2x) found no token-level compressor that kept accuracy in all three families: 14 of 15 (method, family) cells lost at least 0.250, and the exception, the Selective-Context-style filter on code, lost 0.150 and cannot be separated from no loss at n=40 [local: raw/results/results.md table A]. The ranking of compressors changed between families, a GPT-2 version of LLMLingua v1 could not be told from random word dropping, and on 50 sensitive records no compressor kept all nine fields in more than 0.18 of records (sections 2.8, 6).
3. **The interface** rules methods out before quality is considered: five of the twelve (Gist, AutoCompressor, 500xCompressor, H2O, SnapKV) cannot reduce an API bill, because they change what the serving model itself consumes or stores (section 5).

**Recommended method per task family.** "Ratio limit" is the largest ratio at which a source shows a score within 2 points of uncompressed; where no source does, it is 1x. "Evidence" says whether the figure is from papers (P), the local run (L) or neither.

| Task family | Recommended | Fallback | Ratio limit | Expected loss at the limit | One-line reason | Evidence |
|---|---|---|---|---|---|---|
| Coding | Do not compress | Select whole blocks by relevance, about 2x | 1x at token level | none by definition; at 2x token level the local lookups lost 0.150 to 0.700 | Identifiers and keywords are split or dropped; papers' Code column and the local test disagree | P conflicting, L |
| Long-document QA and RAG | Question-aware: CPC or LongLLMLingua (GPU) | CPU only: drop whole passages by relevance to the question; LLMLingua-2 at 3x or less if the question is unavailable | 4x to 5x question-aware; 3x question-agnostic | question-aware about 0.7 points at 4x (worst NaturalQuestions position); agnostic 1.6 points at 3x on the LongBench average, 10.5 to 27.1 on NaturalQuestions at 3.9x | Without the question the compressor drops the answer-bearing text | P, L control |
| Multi-turn chat | Do not compress; drop the oldest whole turns | none | not established | unknown | No source measured a chat task metric | none |
| Summarization | LLMLingua-2 | SCOPE (no released code) | 3x | 0.2 points on LongBench summarization at 3x; MeetingBank ROUGE-2 and BLEU fall 3.70 and 4.97 points at 3.1x | Within 2 points on ROUGE-1-type scores, not on n-gram fidelity | P |
| Structured data (JSON, tables, logs) | Do not compress at token level; select relevant records or aggregate upstream | none | 1x token level; about 2x by record selection | at 2x token level: 0.250 to 0.825 lost locally | Field names are what disappears; no paper tested it | L only |
| Reasoning and math | LLMLingua-2 (or LLMLingua v1) on the few-shot demonstrations; drop demonstrations first | none | 14x on GSM8K-style, 3x on BBH-style | 1.06 points on GSM8K at 14x; 8.13 points on BBH at 5x | Compression sheds demonstrations; multi-step tasks degrade first | P |
| Sensitive or regulated content | Do not compress; redact upstream | none | 1x | at 2x LLMLingua-2 kept all nine fields in 0.00 of records | Fields are damaged, and names and IBANs survive anyway | L only |

Sources for the table, row by row; every difference is derived from the quoted values.

- Coding: local lookups lost 0.150 to 0.700 at 2x token level [local: raw/results/results.md table A code]; EHPC's code comparison [EH-054: Table 6 p.10; EH-053: Table 6 p.10]; the papers' Code column [L2-034: Table 2 p.7; L2-043: Table 2 p.7].
- Long-document QA and RAG: worst NaturalQuestions position 0.7 below the original at 4x (derived) [LongLL-CL-4: Table 1 p.7; LongLL-CL-2: Table 1 p.7]; LongBench average 1.6 below at 3x for the question-agnostic method (derived) [L2-035: Table 2 p.7; L2-043: Table 2 p.7]; NaturalQuestions at 3.9x 10.5 to 27.1 points below (derived) [L2-059: Table 11 p.18; L2-060: Table 11 p.18].
- Multi-turn chat: no source (section 4.3).
- Summarization: LongBench summarization 0.2 below at 3x (derived) [L2-035: Table 2 p.7; L2-043: Table 2 p.7]; MeetingBank ROUGE-2 3.70 and BLEU 4.97 below (derived) [L2-040: Table 1 p.6; L2-042: Table 1 p.6].
- Structured data: local losses of 0.250 to 0.825 at 2x [local: raw/results/results.md table A logs].
- Reasoning and math: GSM8K 1.06 below at 14x and BBH 8.13 below at 5x (derived) [L2-032: Table 3 p.7; L2-033: Table 3 p.7; L2-049: Table 3 p.7].
- Sensitive content: all nine fields intact in 0.00 of records [local: raw/results/results.md table D].

**Main trade-offs.**

- **Ratio against quality.** The supported ratios are small outside reasoning prompts: 3x to 5x on question-aware QA and summarization, 14x only on few-shot arithmetic demonstrations, and 1x wherever exact strings matter. No source supports a general "20x with little loss"; the repo's 98.5% retention figure is not printed in the paper (section 2.7).
- **Latency against compressor cost.** On the slow local target (prefill 23.6 ms per token) LLMLingua-2 at 2x cut the end-to-end median from 10.59 s to 7.22 s on QA, from 16.13 s to 12.30 s on logs and from 16.22 s to 11.96 s on code, compressor included; it costs 14.22 CPU-seconds per 1k input tokens. It saves wall time only if the target prefills slower than 9.1 ms per token, so on a fast hosted target the case is token cost, not latency; LLMLingua v1 with GPT-2 was slower than no compression on code (section 6.9) [local: raw/results/results.md table A and table G].
- **Wins on one metric only.** LLMLingua-2 wins ROUGE-1 and loses ROUGE-2 and BLEU [L2-040: Table 1 p.6; L2-042: Table 1 p.6]; CPC's "10.93x faster" is a median ratio against LongLLMLingua only, and LLMLingua-2 is faster than CPC [CPC-34: Table 5 p.7; CPC-39: Sec. 4.4 Latency evaluation p.7]; LLMLingua-2's 3x to 6x speed-up is for the compression step, the end-to-end speed-up being 1.6x to 2.9x [L2-072: Table 5 p.8; L2-070: Table 5 p.8].
- **Compressor cost for the best question-aware methods.** CPC and LongLLMLingua need a 7B model on a GPU; neither was run here. SCOPE and EHPC have no released code.

**What came from where.** Paper numbers: sections 2 to 5 (machine-verified quotes with page). Local numbers: section 6, from 840 main requests plus the post-hoc runs, all in `raw/`. Methods that cannot run here stay "from paper" (section 6.10). Sections 7 and 8 give the routing for our pipeline and the limits of the evidence.

**What this means for the gateway today.** Its `non_sensitive` route (LLMLingua-2, rate 0.6, digit protection) is the mildest setting I tested, and it still lost 0.575 accuracy on logs and JSON at only 1.22x, 0.125 on code at 1.32x, and 0.050 on QA at 1.67x [local: raw/results/results.md table A]. Digit protection on its own made no measurable difference. The classifier's importance labels do not tell the router whether the text will be read for exact strings, so the route needs a content-type guard before the compressor (section 7).

## 2. Where "one compressor for all" fails (evidence)

**Premise tested:** "any compressor works for any task". It fails the six tests below. Each uses numbers printed in a primary paper; the local run (section 2.8) adds a direct test on exact-string workloads. Every comparison here is a within-paper comparison, so it is not confounded by different models or benchmarks.

### 2.1 Question-agnostic compression collapses on RAG-style QA where question-aware compression does not

NaturalQuestions with 20 retrieved documents, GPT-3.5-Turbo, about 4x compression, accuracy by position of the answer-bearing document (1st / 5th / 10th / 15th / 20th):

| Compressor | Query use | 1st | 5th | 10th | 15th | 20th | Source |
|---|---|---|---|---|---|---|---|
| uncompressed (2,946 tokens) | - | 75.7 | 57.3 | 54.1 | 55.4 | 63.1 | [L2-060: Table 11 p.18; LongLL-CL-2: Table 1 p.7] |
| LLMLingua-2 (3.9x) | agnostic | 48.6 | 44.5 | 43.6 | 40.9 | 39.9 | [L2-059: Table 11 p.18] |
| LLMLingua v1 (3.8x) | agnostic | 25.5 | 27.5 | 23.5 | 26.5 | 30.0 | [LongLL-CL-5: Table 1 p.7] |
| Selective Context (3.7x) | agnostic | 31.4 | 19.5 | 24.7 | 24.1 | 43.8 | [SC-T05: Table 11 p.18] |
| LLMLingua-2+ hybrid (3.9x) | aware | 74.0 | 70.4 | 67.0 | 66.9 | 65.3 | [L2-062: Table 11 p.18] |
| LongLLMLingua (3.9x) | aware | 75.0 | 71.8 | 71.2 | 71.2 | 74.7 | [LongLL-CL-4: Table 1 p.7] |

- The question-agnostic rows are below the no-documents (zero-shot) score of 56.1 at every position (derived from [L2-061: Table 11 p.18]); the original prompt is below it too at the 5th, 10th and 15th positions (derived from [L2-060: Table 11 p.18; L2-061: Table 11 p.18]).
- Removing the question-aware parts of LongLLMLingua at 2x takes the 1st-position score from 77.2 to 42.1 [LongLL-ABL-2: Table 3 p.8; LongLL-ABL-3: Table 3 p.8].
- Caveat: which rows of the LLMLingua-2 paper's Table 11 were re-run and which were copied from the LongLLMLingua paper is not recoverable from the extracted text (dagger markers lost). The pattern is the same in the LongLLMLingua paper's own Table 1 [LongLL-CL-5: Table 1 p.7; LongLL-CL-4: Table 1 p.7].
- The LLMLingua-2 authors show other datasets where a question-agnostic compression drops the text the question needs (their Figs. 13-14) [L2-094: Appendix G p.13].

### 2.2 The same compressor gives opposite outcomes on different tasks

| Compressor, setting | Task | Compressed | Uncompressed | Source |
|---|---|---|---|---|
| LLMLingua-2, 5x, GPT-3.5-Turbo | LongBench Code column | 58.9 | 54.2 | [L2-034: Table 2 p.7; L2-043: Table 2 p.7] |
| LLMLingua-2, 5x | LongBench single-document QA | 29.8 | 39.7 | [L2-034: Table 2 p.7; L2-043: Table 2 p.7] |
| LLMLingua-2, 5x | LongBench Synthetic column | 21.3 | 37.8 | [L2-034: Table 2 p.7; L2-043: Table 2 p.7] |
| LLMLingua-2, 3x | LongBench Synthetic column | 21.4 | 37.8 | [L2-035: Table 2 p.7; L2-043: Table 2 p.7] |
| LLMLingua v1, 20x | GSM8K EM (quarter-shot) | 77.33 | 78.85 | [LLv1-CL-4: Table 2 p.6; LLv1-CL-1: Table 2 p.6] |
| LLMLingua v1, 7x | BBH EM | 56.85 | 70.07 | [LLv1-CL-4: Table 2 p.6; LLv1-CL-1: Table 2 p.6] |
| SnapKV 1,024, Mistral-7B-Instruct | GovReport | 25.89 | 32.85 | [SK-032: Table 1 p.9; SK-031: Table 1 p.9] |
| SnapKV 1,024, Mistral-7B-Instruct | LongBench Lcc (code) | 55.65 | 55.51 | [SK-032: Table 1 p.9; SK-031: Table 1 p.9] |

The LongBench column definitions are not given in the LLMLingua-2 paper; the LongLLMLingua appendix lists the categories as single-document QA, multi-document QA, summarization, few-shot learning, synthetic tasks and code completion [LongLL-CL-23: App. B.1 p.12]. The authors of LLMLingua attribute the BBH decline to hard reasoning sub-tasks such as `tracking_shuffled_objects_seven_objects` [LLv1-CL-16: Sec. 5.2 p.6], and report the drops as 8.5 and 13.2 points at 5x and 7x [LLv1-CL-15: Sec. 5.2 p.6]. A single "maximum safe ratio" does not exist: for LLMLingua v1 it is above 14x on GSM8K and below 5x on BBH under the same method and the same target model.

### 2.3 The verdict depends on which metric and which task column you read

- LLMLingua-2 on MeetingBank at 3.1x: ROUGE-1 48.64 vs 47.28 uncompressed, but ROUGE-2 22.96 vs 26.66 and BLEU 17.37 vs 22.34 [L2-040: Table 1 p.6; L2-042: Table 1 p.6].
- CPC at a 3,000-token budget: LongBench average 50.0 vs 44.0 uncompressed, yet its summarization column is 23.8 vs 26.5 [CPC-08: Sec. 4.4 p.6; CPC-11: Table 2 p.6; CPC-09: Table 2 p.6].
- The "Mistral-7B does better with compressed prompts than with the original" result (MeetingBank QA 76.22 vs 66.95) is attributed by the authors to the target model handling long prompts poorly [L2-051: Table 4 p.8; L2-052: Table 4 p.8; L2-053: Sec. 5 Mistral-7B as the Target LLM p.8]. A compressor can beat the baseline because the baseline is weak, which is a property of the target model.

### 2.4 Methods are not interchangeable at the interface level

- Soft-token and KV methods change what the *serving model* consumes. Gist output is key/value activations usable by the same fine-tuned model [GT-007: Sec. 2 p.2; GT-005: Sec. 3 p.3]; 500xCompressor output is per-layer KV values tied to one LLM [XC-003: Sec. 2.1 p.2; XC-004: Sec. 2.1 p.2]; AutoCompressor emits summary vectors [AC-004: Sec. 1 p.1; AC-005: Sec. 1 p.1]. None of the three papers discusses API-only models [GT-008: Sec. 8 p.9].
- H2O and SnapKV shrink the KV cache inside the generating model and save no prompt tokens: "Per-request token savings: none" for H2O in the ledger [H2-080: Appendix A p.20] and "no prompt-token reduction" for SnapKV [SK-070: Sec. 6 p.12]. SnapKV's own text says its design "does not cover the processing of the prompt inference" [SK-066: Sec. 6 p.12]. An API bill does not fall.
- EHPC produces text but needs a local LLM with attention access to score tokens; the paper uses Llama-3.1-8B [EH-020: Sec. 1 p.2; EH-024: Sec. 5.1 p.8].
- The domains differ as well. Gist was tested only on Alpaca+ instruction following with short instructions (up to 26x means a 26-token instruction into 1 token) [GT-009: Abstract p.1; GT-010: Figure 3 caption p.6; GT-063: Sec. 4.1 p.4]; 500xCompressor only on extractive QA over abstracts [XC-072: Sec. 3.1 p.3; XC-073: Sec. 3.1 p.3]; AutoCompressor on perplexity, 11 in-context-learning datasets and retrieval-augmented perplexity [AC-044: Table 4 header p.7; AC-053: Table 5 p.8]. A ratio from one of these says nothing about another.

### 2.5 Compression damages exact strings, and the papers show it

- LongLLMLingua: token pruning corrupted a year, giving "209" instead of "2019", until subsequence recovery restored it [LongLL-LIM-4: Fig. 7 p.18; LongLL-LIM-3: Sec. 4.4 p.5].
- SnapKV: without pooling, "the LLMs retrieve only the country code of a phone number and hallucinate the rest" [SK-006: Sec. 4.3 p.6].
- Gist: FLAN-T5-XXL answered "Culture" instead of the required "Arts & Culture" when a phrase had to be copied verbatim [GT-031: Sec. 5.1 p.7; GT-030: Sec. 5.1 p.7].
- 500xCompressor: regeneration swaps "Kato complexes" for "Kato modules"; no exact-match rate is reported [XC-050: Sec. 4.2 p.4; XC-053: Sec. 3.3 p.3].
- Selective Context: at a 0.65 reduction ratio gpt-3.5 refused 19 of 200 questions and its answers were 35% shorter [SC-049: Table 3 p.6; SC-051: Sec. 5.2 p.7].
- No paper in the set measured PII or identifier retention (section 4, family 7).

### 2.6 "Compression always saves time" is false in several measured cases

- Selective Context took 15.9 / 15.6 / 15.5 s at 2x / 3x / 5x on MeetingBank in the LLMLingua-2 authors' run, above the 14.9 s uncompressed end-to-end figure [SC-T07: Table 5 p.8; SC-T08: Appendix I p.14; SC-T09: Table 5 p.8; L2-070: Table 5 p.8].
- LongLLMLingua compression took 67.44 s versus 1.27 s for LLMLingua-2 on a 14,354-token subset [EH-084: Table 5 p.9; EH-085: Table 5 p.9; EH-088: Table 5 p.9].
- CPC's "10.93x faster" is the median compressor-stage time ratio against LongLLMLingua only; LLMLingua-2 is faster than CPC [CPC-34: Table 5 p.7; CPC-39: Sec. 4.4 p.7].
- Gist's 40% FLOPs saving is against no caching; against caching the instruction KV it is .11% in FLOPs and 1.0% in wall time [GT-046: Table 3 p.8; GT-045: Table 3 p.8].

### 2.7 Repo claims audited against the primary papers

| Repo claim (README / articles) | What the paper shows | Evidence |
|---|---|---|
| LLMLingua "20x compression with 98.5% accuracy retention" | "98.5%" is not printed. The paper says "up to 20x compression with only a 1.5 point performance drop" (GSM8K quarter-shot); BBH at 7x loses 13.2 points | [ART-RD-1: README line 24 web; LLv1-CR-2: Conclusion p.9; LLv1-CL-15: Sec. 5.2 p.6] |
| Latency "1.6x-5.7x with compression ratios of 2x-10x" | LLMLingua Table 6 gives 1.7x to 5.7x; 1.6x belongs to LLMLingua-2 at 2x | [ART-RD-2: README line 89 web; LLv1-LAT-4: Table 6 p.8; LLv1-LAT-6: Sec. 5.5 p.8; L2-070: Table 5 p.8] |
| "LongLLMLingua achieving 17.1% performance improvements at 4x" | Paper says up to 21.4% at the 10th answer position with about 4x fewer tokens; both 21.4 and 17.1 are point differences at one position (derived from Table 1) | [ART-RD-3: README line 81 web; LongLL-CR-1: Abstract p.1; LongLL-CR-4: Sec. 5 Main results p.6] |
| LLMLingua-2 "3x-6x faster" | Supported for the compression step (0.5 / 0.4 / 0.4 s vs 2.9 / 2.1 / 1.5 s); end-to-end speedup is 1.6x-2.9x | [L2-072: Table 5 p.8; L2-073: Sec. 5 Latency Evaluation p.8; L2-078: Table 5 p.8; L2-070: Table 5 p.8] |
| LLMLingua-2 "up to 20x", "90%+ performance" | Neither is printed; the largest ratio in a table is 14x (GSM8K) | [L2-032: Table 3 p.7; L2-033: Table 3 p.7] |
| CPC "10.93x faster inference than token-level methods" | Median compressor time ratio vs LongLLMLingua only; LLMLingua-2 is faster | [ART-CPC-01: Key Features 4 web; CPC-34: Table 5 p.7; CPC-36: Table 5 p.7] |
| Selective Context "parameter-free" | Needs a base LM (LLaMA-7B or GPT-3 curie) | [SC-003: Sec. 4.4 p.5; SC-004: Sec. 4.4 p.5] |
| AutoCompressor "segments up to 30,720 tokens" | 30,720 is a training/evaluation sequence length for OPT; the Llama-2 model was trained on 6,144 | [ART-A02: repo article web; AC-012: Sec. 4.2 p.4; AC-008: Sec. 4.3 p.5] |
| Gist "up to 26x" with "minimal quality loss" | 26-token instructions into 1 token; out-of-distribution win rate 45.8% / 42.5% (50% = parity) | [ART-G01: repo article web; GT-010: Figure 3 caption p.6; GT-023: Sec. 5 p.5; GT-024: Sec. 4.3 p.5] |
| 500xCompressor "retains 62-73% of capabilities" | Mean of five normalised extractive-QA F1 scores on LLaMa-3-8b-chat | [ART-X02: repo article web; XC-032: Abstract p.1; XC-036: Table 5 p.10] |
| "At least 2^n inference calls, forcing reliance on greedy approximations" (rate-distortion) | 2^len(x) is the cost of computing the theoretical benchmark for one prompt, not a cost of running or evaluating a compressor | [ART-RD-01: Limitations - Fundamental Algorithmic Limitations web] |
| Attention-based methods: "compatible with black-box model access through APIs" | Only EHPC emits text, and it needs a local LLM; H2O and SnapKV edit the KV cache inside the serving model | [EH-020: Sec. 1 p.2; EH-021: Sec. 3.4 p.6; H2-010: Appendix A System Details p.20; SK-015: Sec. 6 p.12] |

### 2.8 The local run tests the premise directly

The papers above are not run on one target with one set of items. The local check is: the same 40 items per family, the same model (llama3.2:3b on this CPU), compressors matched to about 2x. Its tables are in section 6; this section keeps only what bears on "any compressor works for any task". All numbers are local and carry their source.

**Test 1: does at least one token-level compressor keep quality at about 2x in every family?** No. The best token-level arm in each family still lost accuracy:

| Family | Best token-level arm | Accuracy (uncompressed) | Difference | Exact McNemar p | Ratio | Question-aware control: accuracy, ratio | Source |
|---|---|---|---|---|---|---|---|
| QA over distractor paragraphs | LLMLingua-2 (~2x) | 0.750 (1.000) | −0.250 | 0.002 | 2.37x | 1.000, 1.90x | [local: raw/results/results.md table A qa] |
| Lookups in logs and JSON | Selective-Context-style (2x) | 0.750 (1.000) | −0.250 | 0.002 | 2.08x | 0.950, 2.01x | [local: raw/results/results.md table A logs] |
| Lookups of constants in code | Selective-Context-style (2x) | 0.725 (0.875) | −0.150 | 0.146 | 2.14x | 0.900, 2.08x | [local: raw/results/results.md table A code] |

Across the 15 (arm, family) cells of the five token-level arms at about 2x or 3x, 14 lost at least 0.250 with a separable McNemar test; the one exception is the Selective-Context-style filter on code (−0.150, p 0.146), which the sample cannot separate from no loss at all [local: raw/results/results.md table A]. The gateway's own setting, which compresses less (rate 0.6 with digit protection; 1.67x, 1.22x and 1.32x), lost 0.050 on QA, 0.575 on logs and 0.125 on code; only the logs loss is separable [local: raw/results/results.md table A]. A 15-point difference is also about the smallest this sample can flag at all (section 8.2), so "not separable" there means "not resolved", not "harmless".

**Test 2: is the ranking of compressors the same on every task?** No. The Selective-Context-style filter beat LLMLingua-2 at 2x on logs (0.750 against 0.300) and on code (0.725 against 0.550), and both gaps are separable; on QA the order reverses (0.575 against 0.750) but the 0.175 gap is not separable (p 0.118). The ratios do not explain it: on logs and code the filter compressed more (2.08x and 2.14x against 1.79x and 1.98x) and still won [local: raw/results/results.md table A and table F]. A single "best compressor" would have been chosen differently depending on which family the benchmark contained.

**Test 3: does a more sophisticated compressor beat a naive one everywhere?** No. LLMLingua v1 with plain GPT-2 as scorer cannot be separated from dropping random words in any family (QA p 0.804, logs p 1.000, code p 0.238) nor pooled over all 120 items (p 0.392). LLMLingua-2 beat random dropping on QA but not on logs (p 0.302) or code (p 0.108) [local: raw/results/results.md table F]. This says something about the GPT-2 variant used here, not about the published LLMLingua (section 8.2), but it shows how little a compressor's name predicts.

**Test 4: does compression always make the request faster?** No. On this CPU target, LLMLingua v1 with GPT-2 took a median 18.27 s end to end on code items against 16.22 s uncompressed, and a p90 of 24.93 s against 20.64 s, because its compressor cost more than the prefill it saved; the other arms were faster than the baseline on this slow target [local: raw/results/results.md table A code]. The papers show the same effect for Selective Context and LongLLMLingua (section 2.6).

**Test 5: is compression safe for sensitive records?** No. On 50 synthetic case notes, no token-level compressor kept all nine sensitive fields in more than 0.18 of records, and LLMLingua-2 at 2x, with or without digit protection, and at the gateway's rate 0.6 kept them in none (section 6.5) [local: raw/results/results.md table D].

**Test 6: does the question-aware idea from the papers hold up locally?** Yes in direction. A selector that sees the question kept 1.000 of QA items, 0.950 of log and JSON items and 0.900 of code items at about 2x, where every question-agnostic arm lost at least 0.150 [local: raw/results/results.md table A]. The size of this advantage is not transferable: each synthetic question contains a rare token that also appears in the answer-bearing paragraph or record, which is the easiest case for lexical selection (section 8.2).

**Verdict of the local run.** The premise fails in all six respects it could be tested in. This does not show that every method fails everywhere: it shows that quality at a given ratio depends on the task, the metric and whether the compressor sees the question.

## 3. Method profiles (condensed from Part 1)

Reading guide. `[ID: Table, page]` points to a machine-verified quote in `raw/ledger/EVIDENCE_INDEX.md` (page = 1-based PDF page). "not reported" means the source does not print it; nothing is estimated. "(derived)" marks arithmetic on quoted numbers. Ratios are the papers' own definitions (words or tokens, see each profile). Where the repo article disagrees with the paper, the paper is used and the disagreement is listed in section 2.

### 3.0 Source quality in the research repo (read this first)

Only 3 of the 12 PDFs under `papers/` are real sources for compression methods. The others are different papers under the wrong name, so the repo articles for 7 of 9 methods had no checkable primary source. The real papers were fetched from arXiv with the user's approval (IDs checked against arXiv metadata, `raw/arxiv_meta_ids.xml`, SHA-256 in `raw/papers_fetched_sha256.txt`).

| Repo file | What it actually contains | Real paper used here |
|---|---|---|
| `llmlingua.pdf` | the real LLMLingua paper [LLv1-REP-1: p.1] | same |
| `500x-compressor.pdf` | the real 500xCompressor paper [XC-070: p.1] | same |
| `rate-distortion-framework.pdf` | the real rate-distortion paper (secondary evidence) | same |
| `llmlingua-2.pdf` (labelled arXiv:2403.11802) | Counting-Stars long-context benchmark [ART-001: repo article web] | arXiv:2403.12968 [L2-130: p.1] |
| `gist-tokens.pdf` (labelled arXiv:2401.09390) | a mathematics paper on q-Bernstein operators [ART-G07: repo article p.1] | arXiv:2304.08467 [GT-060: p.1] |
| `selective-context.pdf` (labelled arXiv:2502.14048) | an unrelated paper by Villardar [ART-013: repo article web] | arXiv:2310.06201 [SC-111: p.1] |
| `context-aware-prompting.pdf` | a Bosch manufacturing knowledge-graph paper, not CPC [ART-CPC-05: Note web] | arXiv:2409.01227 |
| `xrag.pdf`, `style-aware-prompt-generation.pdf` | cross-lingual RAG benchmark; federated vision-language prompt learning | not used (no compression method profiled from them) |
| (no PDF) AutoCompressor, SCOPE, EHPC/H2O/SnapKV | articles say "unable to locate the specific paper" | arXiv:2305.14788, 2508.15813, 2501.12959 / 2306.14048 / 2404.14469 |

### 3.1 LLMLingua (v1) — token pruning with a small LM

- **Mechanism.** Coarse-to-fine hard-prompt pruning: budget controller, iterative token-level compression, optional distribution alignment [LLv1-MECH-1: Abstract p.1]. Scores are perplexity from a small causal LM (GPT2-Alpaca or Alpaca-7B in the paper); there is no trained keep/drop classifier [LLv1-MECH-6: Sec. 4.3 p.5; LLv1-MECH-7: Sec. 5.1 Implementation Details p.5]. Needs: a small LM at inference.
- **Input/output.** Text in, text out, positioned for black-box LLMs [LLv1-IO-1: Sec. 1 p.1; LLv1-IO-4: Sec. 1 p.1]. Targets: GPT-3.5-Turbo-0301 and Claude-v1.3 (GSM8K only) [LLv1-IO-3: Sec. 5.1 Implementation Details p.5]. Output is visibly garbled; GPT-4 can reconstruct it, GPT-3.5-Turbo struggles [LLv1-IO-5: Figure 1 p.3; LLv1-IO-6: Figure 1 p.3].
- **Ratio.** Headline "up to 20x compression with little performance loss" [LLv1-CR-1: Abstract p.1], restated as "only a 1.5 point performance drop" [LLv1-CR-2: Conclusion p.9]; that is the GSM8K quarter-shot case. Datasets: GSM8K, BBH, ShareGPT, Arxiv-March23.
- **Quality loss (GPT-3.5-Turbo, EM).** GSM8K 79.08 at 5x and 77.41 at 14x vs 78.85 full-shot [LLv1-CL-2: Table 2 p.6; LLv1-CL-3: Table 2 p.6; LLv1-CL-1: Table 2 p.6]. BBH 70.11 at 3x and 61.60 at 5x vs 70.07 full-shot [LLv1-CL-2: Table 2 p.6; LLv1-CL-3: Table 2 p.6; LLv1-CL-1: Table 2 p.6]. Chat and summarization are scored only as similarity to the output of the uncompressed prompt: ShareGPT BLEU 27.36 at 1.9x and 19.55 at 3.3x [LLv1-CL-18: Table 1 p.6; LLv1-CL-20: Table 1 p.6; reference definition LLv1-CL-23: App. A.1 p.12].
- **Latency/compute.** Tesla V100 32 GB; GSM8K end-to-end 8.6 s baseline vs 4.9 / 2.3 / 1.3 s at 2x / 5x / 10x, compressor alone 0.8 / 0.3 / 0.2 s [LLv1-LAT-3: Table 6 p.8; LLv1-LAT-4: Table 6 p.8; LLv1-LAT-5: Table 6 p.8; LLv1-LAT-6: Sec. 5.5 p.8; LLv1-LAT-7: Table 6]. CPU latency: not reported.
- **Cost.** Table 7 (GPT-3.5-Turbo pricing): GSM8K 5.2 to 0.5, BBH 12.8 to 4.8, ShareGPT 0.7 to 0.3, Arxiv 1.3 to 0.2 dollars; the small-LM compute is not priced [LLv1-COST-1: Table 7 p.12; LLv1-COST-2: Table 7 p.12; LLv1-COST-3: Table 7 p.12; LLv1-COST-4: Appendix B p.12; LLv1-COST-5: Sec. 5.5 p.8].
- **Limitations.** Authors: notable drop at 25x-30x on GSM8K; tokenizer mismatch can mis-estimate length [LLv1-LIM-1: Limitations p.9; LLv1-LIM-2: Limitations p.10; LLv1-LIM-3: Limitations p.10]. Not tested: coding, long-document QA/RAG, structured data, PII [LLv1-TASK-4: Abstract p.1; LLv1-TASK-5: Abstract p.1; LLv1-TASK-6: Abstract p.1; LLv1-TASK-7: Abstract p.1]. Max input length: not reported.
- **Reproducibility.** Code linked, MIT, `pip install llmlingua` [LLv1-REP-1: Footnote 1 p.1; LLv1-REP-2: LICENSE web; LLv1-REP-3: README web]. The aligned GPT2-Alpaca checkpoint release is not stated [LLv1-REP-4: Sec. 5.1 p.5]. Local finding: llmlingua 0.2.2 raised `ValueError: too many values to unpack` on `transformers 5.20.1` when `iterative_size=50` (section 6.1).

### 3.2 LongLLMLingua — question-aware extension (README claim, not one of the 9 articles)

- **Mechanism.** LLMLingua plus question-aware coarse ranking, contrastive-perplexity token scoring, document reordering, dynamic per-document ratios and subsequence recovery [LongLL-MECH-1: Sec. 1 p.1; LongLL-MECH-3: Sec. 1 p.1; LongLL-MECH-5: Sec. 4.1 p.3; LongLL-MECH-7: Sec. 4.2 p.4]. Compressor LM: LLaMA-2-7B-Chat [LongLL-MECH-9: Sec. 5 Implementation details p.6].
- **Input/output.** Text to text; targets GPT-3.5-Turbo-0613 and LongChat-13B-16k [LongLL-IO-1: Sec. 5 Implementation details p.5; LongLL-IO-4: Footnote 6 p.5]. It depends on the question, so it must be re-run per question and the context cannot be cached [LongLL-IO-3: Limitation p.9; LongLL-LIM-1: Limitation p.9].
- **Quality (NaturalQuestions, 20 documents, accuracy by answer position 1st/5th/10th/15th/20th, GPT-3.5-Turbo).** Original 75.7 / 57.3 / 54.1 / 55.4 / 63.1; LongLLMLingua at 4x 75.0 / 71.8 / 71.2 / 71.2 / 74.7 [LongLL-CL-2: Table 1 p.7; LongLL-CL-4: Table 1 p.7]. At the first position the compressed score is slightly below the original (75.0 vs 75.7). Without the question-aware parts the first-position score falls to 42.1 from 77.2 at 2x [LongLL-ABL-2: Table 3 p.8; LongLL-ABL-3: Table 3 p.8]. LongBench average: 48.8 at 3x and 48.3 at 6x vs 44.0 uncompressed [LongLL-CL-16: Table 2 p.8; LongLL-CL-17: Table 2 p.8; LongLL-CL-18: Table 2 p.8].
- **README claim "17.1% improvement at 4x" (derived).** The abstract says "up to 21.4%" [LongLL-CR-1: Abstract p.1] at the 10th answer position [LongLL-CR-4: Sec. 5 p.6]. From Table 1, 75.5 (reorder) minus 54.1 (original) is 21.4 points and 71.2 minus 54.1 is 17.1 points [LongLL-CL-4: Table 1 p.7; LongLL-CL-2: Table 1 p.7]. Both are point differences at one answer position, not a mean percentage gain.
- **Latency/compute.** V100 32 GB, end-to-end against API calls [LongLL-HW-1: Appendix B.2 p.13; LongLL-LAT-1: Latency evaluation p.8]; authors say the method doubles LLMLingua's compute [LongLL-LAT-4: Limitation p.9]. A third party measured LongLLMLingua compression at 67.44 s versus 1.27 s for LLMLingua-2 on a 14,354-token subset [EH-084: Table 5 p.9; EH-085: Table 5 p.9; EH-088: Table 5 caption p.9; EH-086: Table 5 p.9; see section 3.7 for the table's caveats].
- **Cost.** Table (GPT-3.5-Turbo pricing, per 1,000 samples): NQ 4.6 to 1.3, LooGLE 93.6 to 5.6; compressor compute is not part of these costs [LongLL-COST-1: Table 9 p.17; LongLL-COST-2: Table 9 p.17; LongLL-COST-3: Table 9 p.17; LongLL-COST-4: Appendix D p.16].
- **Limitations.** Per-question recompression; weaker when the question-context relation is subtle [LongLL-LIM-1: Limitation p.9; LongLL-LIM-2: Limitation p.9]. Token pruning corrupts entities, e.g. a year answered as 209 instead of 2019 until subsequence recovery repairs it [LongLL-LIM-3: Sec. 4.4 p.5; LongLL-LIM-4: Figure 7 p.18]. Compressor input limit: not reported [LongLL-LIM-7: Appendix B.1 p.13]. Not tested: multi-turn chat, structured data, math, PII [LongLL-TASK-4: Sec. 1 contributions p.2; LongLL-TASK-5: Sec. 1 contributions p.2; LongLL-TASK-6: Sec. 1 contributions p.2; LongLL-TASK-7: Sec. 1 contributions p.2].
- **Reproducibility.** Same MIT repo as LLMLingua [LongLL-REP-2: LICENSE web]; LLaMA-2-7B-Chat licence not discussed [LongLL-REP-4: Sec. 5 footnote 9 p.6].

### 3.3 LLMLingua-2 — learned keep/drop token classifier

- **Mechanism.** Binary token classification (keep/discard) with a bidirectional Transformer encoder, trained on GPT-4-distilled compressions of MeetingBank; at inference it keeps the top-scoring words in original order [L2-001: Sec. 4 p.5; L2-002: Sec. 4.2 p.6]. Two encoders: xlm-roberta-large (355M parameters) and multilingual-BERT (110M) [L2-003: Sec. 5 Implementation Details p.6; L2-004: Appendix H p.14; L2-005: Appendix H p.14]. Needs a trained 110M-355M classifier; no LLM call at inference.
- **Input/output.** Text to text, hard text of original words, no target-LLM internals needed (inferred from mechanism) [L2-002: Sec. 4.2 p.6; L2-082: Sec. 4.1 p.5]. Target LLMs: GPT-3.5-Turbo (default) and Mistral-7B [L2-021: Sec. 1 Contributions p.2; L2-022: Sec. 5 Implementation Details p.6]. Task-agnostic: compress once, reuse for any query [L2-009: Abstract p.1; L2-024: Sec. 1 p.1].
- **Ratio (GPT-3.5-Turbo, question-agnostic).** MeetingBank 3.1x; LongBench and ZeroSCROLLS 3x-5x; GSM8K up to 14x; BBH 3x-5x [L2-040: Table 1 p.6; L2-034: Table 2 p.7; L2-035: Table 2 p.7; L2-032: Table 3 p.7; L2-033: Table 3 p.7; L2-049: Table 3 p.7; L2-050: Table 3 p.7].
- **Quality loss.** MeetingBank QA EM 86.92 vs 87.75 original at 3.1x; Rouge1 48.64 vs 47.28; Rouge2 22.96 vs 26.66 [L2-040: Table 1 p.6; L2-042: Table 1 p.6]. LongBench average 39.1 at 5x and 42.4 at 3x vs 44.0; single-document QA 29.8 and 35.5 vs 39.7; Synthetic 21.3 and 21.4 vs 37.8; Code 58.9 and 62.8 vs 54.2 [L2-034: Table 2 p.7; L2-035: Table 2 p.7; L2-043: Table 2 p.7]. GSM8K 79.08 at 5x and 77.79 at 14x vs 78.85; BBH 70.02 at 3x and 61.94 at 5x vs 70.07 [L2-032: Table 3 p.7; L2-033: Table 3 p.7; L2-049: Table 3 p.7; L2-050: Table 3 p.7]. NaturalQuestions-20 at 3.9x, question-agnostic: 48.6 / 44.5 / 43.6 / 40.9 / 39.9 vs original 75.7 / 57.3 / 54.1 / 55.4 / 63.1 [L2-059: Table 11 p.18; L2-060: Table 11 p.18]. LongBench-Zh at 5x: single-doc 46.7 vs 61.2 [L2-057: Table 10 p.17; L2-058: Table 10 p.17].
- **Latency/compute.** V100 32 GB, MeetingBank: compressor 0.5 / 0.4 / 0.4 s at 2x / 3x / 5x vs 2.9 / 2.1 / 1.5 s for LLMLingua; end-to-end 14.9 s uncompressed vs 9.4 / 7.5 / 5.2 s (1.6x / 2.1x / 2.9x); the table's target LLM is not stated [L2-070: Table 5 p.8; L2-071: Table 5 p.8; L2-072: Table 5 p.8; L2-073: Sec. 5 Latency Evaluation p.8; L2-078: Table 5 p.8]. Peak GPU memory 2.1 GB vs 16.6 GB (LLMLingua) and 26.5 GB (Selective Context) [L2-074: Appendix I p.14; L2-075: Appendix I p.14; L2-076: App. I p.14]. CPU latency: not reported.
- **Cost.** Tokens per request MeetingBank 970 vs 3,003 and LongBench 1,954 vs 10,295 [L2-080: Table 1 p.6; L2-081: Table 2 p.7; L2-042: Table 1 p.6; L2-043: Table 2 p.7]. No extra LLM call at inference (inferred); GPT-4 is used only offline to build training labels [L2-082: Sec. 4.1 p.5; L2-083: Appendix A p.11].
- **Limitations.** Authors: trained on MeetingBank only; adding 50k TriviaQA-wiki examples helped "not that significant" [L2-090: Limitations p.9; L2-091: Limitations / Table 6 p.9]. English training, only Chinese tested outside English [L2-092: Appendix J p.14; L2-093: Appendix J p.14]. The paper's failure figures show other datasets' compressions dropping question-relevant text; no LLMLingua-2 failure case is shown [L2-094: Appendix G p.13]. Distillation chunks are at most 512 tokens; an inference input limit is not reported [L2-013: Sec. 3.1 Chunk-Wise Compression p.4]. Not tested: multi-turn chat, structured data, PII [L2-114: Limitations p.9; L2-115: Limitations p.9; L2-117: Limitations p.9].
- **Reproducibility.** Code and the compression dataset released; MIT repo and HF card [L2-100: Abstract footnote p.1; L2-101: Sec. 6 p.9; L2-102: GitHub About/Resources web; L2-103: model card web].

### 3.4 Selective Context — self-information filtering

- **Mechanism.** Self-information of each token from a base causal LM, merged into lexical units (token, phrase, sentence), then low-information units dropped by a percentile threshold [SC-001: Sec. 1 p.2; SC-002: Sec. 3 p.3; SC-007: Sec. 3.3 p.3]. Base LM: LLaMA-7B, or GPT-3 curie for OpenAI targets [SC-003: Sec. 4.4 p.5; SC-004: Sec. 4.4 p.5]; so it needs a small or medium LM, not "parameter-free" in the article's sense. Phrase units are spaCy noun chunks [SC-006: Sec. 3.2 p.3].
- **Input/output.** Text to text; compressed text was given to GPT-3.5 and GPT-4 [SC-010: Sec. 4.2 p.4; SC-011: Sec. 4.2 p.4]. Output is ungrammatical hard text [SC-008: Fig. 2 p.3].
- **Ratio.** Reduction ratios 0.2, 0.35, 0.5, 0.65, 0.8 of lexical units; test items under 2,048 tokens [SC-020: Sec. 4.4 p.5; SC-083: Sec. 4.1 p.4].
- **Quality loss.** Only agreement with the full-context LLM's own answer; no gold labels [SC-042: Sec. 4 p.4; SC-043: Sec. 4.3 p.5]. Table 1: BERTScore-F1 .909 uncompressed, .887 at 0.5, .863 at 0.8 [SC-030: Table 1 p.6; SC-033: Table 1 p.6; SC-035: Table 1 p.6]. Faithfulness at ratio 0.65: 19 refusals out of 200 and answers 35% shorter [SC-049: Table 3 p.6; SC-051: Sec. 5.2 p.7]. Third-party re-run (LLaMA-2-7B base, other authors): MeetingBank EM 66.28 at 2.5x vs 87.75; LongBench average 24.8 at 5x vs 44.0; GSM8K 53.98 at 5x vs zero-shot 48.75 [SC-T01: Table 1 p.6; SC-T02: Table 2 p.7; SC-T04: Table 3 p.7; L2-042: Table 1 p.6; L2-043: Table 2 p.7; L2-049: Table 3 p.7; L2-050: Table 3 p.7].
- **Latency/compute.** Own paper: one case study, GPU not stated, 46.1 ms to build the context [SC-060: Fig. 6 p.8; SC-062: Fig. 6 p.8]. Third-party V100 run: 15.9 / 15.6 / 15.5 s at 2x / 3x / 5x on MeetingBank, above the 14.9 s uncompressed end-to-end figure [SC-T07: Table 5 p.8; SC-T08: Appendix I p.14; SC-T09: Sec. 5 Baselines p.7; L2-070: Table 5 p.8].
- **Limitations.** Noun-phrase boundaries only, best percentile varies by task and has no selection tool [SC-080: Sec. 7 p.9; SC-081: Sec. 7 p.9; SC-082: Sec. 7 p.9]. Three custom test sets, contexts under 2,048 tokens [SC-083: Sec. 4.1 p.4]. Not tested: coding, structured data, math, PII [SC-101: Sec. 4.1 p.4; SC-102: Sec. 4.1 p.4; SC-103: Sec. 4.1 p.4; SC-104: Sec. 4.1 p.4; SC-105: Sec. 4.1 p.4].
- **Reproducibility.** Code on GitHub, README says MIT [SC-090: Abstract p.1; SC-091: README web].

### 3.5 CPC — query-aware sentence selection with a trained encoder

- **Mechanism.** Sentence-level, extractive, query-aware: an encoder scores each sentence against the question; top sentences within the budget are kept in order [CPC-01: Abstract p.1; CPC-02: Sec. 3.4 Inference p.5]. The encoder is Mistral-7B-Instruct-v0.2 with LoRA, contrastive plus masked-token loss, trained on one A100 80 GB [CPC-03: Sec. 3.3 p.5; CPC-04: Sec. 4.2 p.5].
- **Input/output.** Readable subset of original sentences (design claim, not measured) [CPC-06: Sec. 1 p.2]. Text to text; use with closed models is inferred (Table 4 uses GPT-4o) [CPC-07: Sec. 4.4 Larger backbone p.7]. Needs the question at compression time.
- **Ratio.** Budgets of 3,000 and 2,000 tokens, shown as 3x and 5x; no 10x result [CPC-08: Sec. 4.4 p.6; CPC-11: Table 2 p.6; CPC-17: Table 2 p.6].
- **Quality loss.** LongBench average 50.0 at 3,000 tokens and 49.5 at 2,000 vs 44.0 uncompressed; the target LLM is not named [CPC-08: Sec. 4.4 p.6; CPC-11: Table 2 p.6; CPC-17: Table 2 p.6; CPC-09: Table 2 p.6; CPC-47: Sec. 4.3 p.5]. Summarization is the weak column: 23.8 vs 26.5 uncompressed [CPC-11: Table 2 p.6; CPC-09: Table 2 p.6]. Code column 63.5 vs 54.2 [CPC-11: Table 2 p.6; CPC-09: Table 2 p.6].
- **Latency/compute.** Compressor stage only, A100: CPC average 0.28 and median 0.15 vs LongLLMLingua 7.70 / 1.64 and LLMLingua-2 average 0.23 / median 0.1 [CPC-35: Table 5 p.7; CPC-34: Table 5 p.7; CPC-36: Table 5 p.7; CPC-37: Table 5 p.7]. The "10.93x" headline is the median ratio against LongLLMLingua only, and LLMLingua-2 is faster than CPC [CPC-34: Table 5 p.7; CPC-39: Sec. 4.4 Latency evaluation p.7]. End-to-end saving on the target LLM: not reported [CPC-45: Table 2 p.6].
- **Limitations.** No limitations section [CPC-46: Sec. 5 Conclusion p.8]. Max input length, languages, memory: not reported [CPC-50: Sec. 4.2 p.5]. Not tested: multi-turn chat, structured data, reasoning, PII [CPC-58: Sec. 4.1 p.5; CPC-59: Sec. 4.1 p.5; CPC-60: Sec. 4.1 p.5].
- **Reproducibility.** Code and CQR dataset released, Apache-2.0 [CPC-52: Abstract p.1; CPC-53: LICENSE web].

### 3.6 SCOPE — generative chunk-and-summarize

- **Mechanism.** Training-free, generative: semantic chunking, chunk ranking, per-chunk dynamic ratio, abstractive rewrite of each chunk with a small summarizer (default bart-large-cnn), reassembly in order [SCP-01: Abstract p.1; SCP-02: Sec. 1 p.1; SCP-08: Sec. 3.3.1 p.5; SCP-11: Sec. 3.3.2 p.6]. Query-agnostic [SCP-05: Algorithm 1 p.4; SCP-06: Sec. 3.3.1 p.5].
- **Input/output.** Rewritten (generated) text, not a subset of original tokens; no factuality metric reported [SCP-11: Sec. 3.3.2 p.6; SCP-72: Sec. 3.3.2 p.6]. Downstream LLM in all main results: GPT-4o-mini, plus Qwen-2.5 [SCP-12: Sec. 4.1 p.7].
- **Ratio.** 2x, 3x, 5x target ratios only [SCP-13: Sec. 4.2 p.8; SCP-14: Sec. 4 p.6].
- **Quality loss (ROUGE-1, GPT-4o-mini).** GovReport uncompressed 43.78; SCOPE 43.59 and 43.73 at 5x; LLMLingua-2 40.46 [SCP-26: Table 2 p.7; SCP-29: Table 2 p.7; SCP-30: Table 2 p.7; SCP-27: Table 2 p.7]. Arxiv uncompressed 40.49; SCOPE 37.75 at 5x and 38.66 at 2x [SCP-16: Table 1 p.6; SCP-19: Table 1 p.6; SCP-23: Table 1 p.6]. QA (F1): MultiFieldQA-en uncompressed 54.20; SCOPE 41.39 at 5x and 47.52 at 2x [SCP-37: Table 3 p.8; SCP-40: Table 3 p.8; SCP-44: Table 3 p.8].
- **Latency/compute.** One A100 80 GB; per document GovReport 4.20 s (SCOPE) vs 2.79 s (LongLLMLingua); LLMLingua-2 timing: not reported [SCP-59: Sec. 4.5 p.10; SCP-60: Sec. 4.5 p.10; SCP-63: Sec. 4 p.6].
- **Limitations.** No limitations section; at most 2,000 records per dataset, English only; max input length: not reported [SCP-71: Sec. 5 p.10; SCP-68: Sec. 4.1 p.7; SCP-70: App. A.2 p.13; SCP-67: Sec. 3.3.1 p.5]. Not tested: coding, multi-turn chat, structured data, reasoning, PII [SCP-78: Sec. 1 p.2; SCP-80: Sec. 4.1 p.7].
- **Reproducibility.** Paper footnote says code is available, but the official repo README read "code coming soon." on 2026-11-05 and had no licence [SCP-73: Footnote 1 p.1; SCP-74: README web]. Models are public, so a re-implementation is possible [SCP-75: Sec. 1 p.2].

### 3.7 EHPC — attention-head token pruning (text output, needs a local evaluator LLM)

- **Mechanism.** Training-free token deletion driven by attention of a few "evaluator heads" in middle layers (layer 13 of 32 for Llama-3.1-8B), found once per model with a synthetic needle task [EH-001: Abstract p.1; EH-003: Sec. 3.1 p.4; EH-007: Sec. 1 p.2; EH-008: Sec. 4 Existence p.7; EH-009: Appendix B p.15]. Needs a local open-weight LLM with attention access; the evaluator can differ from the answering model [EH-020: Sec. 1 p.2; EH-022: Sec. 3.4 p.6]. Scores use the end of the prompt, so the question must be last [EH-012: Sec. 3.3 p.5].
- **Input/output.** Shortened natural-language text with fragments [EH-004: Sec. 3.4 p.6; EH-006: Appendix G p.19]; authors say it "can be applied to API-based black-box large models" [EH-021: Sec. 3.4 p.6]. Target LLM behind Table 4: not named [EH-026: Sec. 5.1 p.8].
- **Ratio.** 3x (2,892 tokens) and 5x (2,004 tokens) on LongBench [EH-041: Table 4 p.8; EH-042: Table 4 p.8].
- **Quality loss.** LongBench average 49.7 at 3x and 49.6 at 5x vs 44.0; code 63.0 and 61.9 vs 54.2; summarization 25.1 vs 26.5 [EH-041: Table 4 p.8; EH-042: Table 4 p.8; EH-040: Table 4 p.8]. Against KV-cache methods on Llama-3.1-8B (printed averages): EHPC 35.23 at a 1,024 budget vs 38.32 full KV; RepoBench-P 42.8 vs 49.25; the authors say prompt compression "exhibits a decline in performance on code-related tasks and few-shot learning tasks" [EH-054: Table 6 p.10; EH-053: Table 6 p.10; EH-066: Table 6 p.10]. The printed LongBench average for EHPC at 3x (49.7) is below the mean of the six category columns in its own row (50.7, derived from [EH-041: Table 4 p.8]); the cause is not explained.
- **Latency/compute.** 14,354-token RepoBench-P subset compressed to 2,048 tokens, one 40 GB-VRAM GPU (type not named), 5 repeats: EHPC compression 0.88 s, total 1.99 s vs 2.16 s for the full prompt to ChatGPT-3.5-Turbo (inference time borrowed from another paper); LongLLMLingua 67.44 s; LLMLingua-2 1.27 s [EH-049: Sec. 5.1 Compression Latency p.9; EH-083: Table 5 p.9; EH-084: Table 5 p.9; EH-085: Table 5 p.9; EH-086: Table 5 p.9; EH-087: Sec. 5.1 Compression Latency p.9; EH-088: Table 5 caption p.9; EH-089: Table 5 p.9].
- **Limitations.** English LongBench only; no limitations section [EH-110: Appendix D.2 p.16]. Not tested: multi-turn chat, structured data, math, PII [EH-136: Appendix D.2 p.16].
- **Reproducibility.** No code, checkpoint or licence in the paper, the NeurIPS poster page or the arXiv page (checked 2026-11-05) [EH-120: Appendix B p.14; EH-121: NeurIPS 2025 poster page web; EH-122: arXiv abs page web].

### 3.8 Gist Tokens — soft gist prefix inside a fine-tuned model

- **Mechanism.** The LM is instruction-fine-tuned with gist tokens and an attention mask that forces the prompt into the gist prefix; no extra training cost beyond instruction tuning [GT-001: Abstract p.1; GT-002: Abstract p.1; GT-055: Sec. 3 p.3]. Base models LLaMA-7B and FLAN-T5-XXL [GT-006: Sec. 4.2 p.4].
- **Input/output.** Output is key/value activations on the gist tokens, usable only by the same fine-tuned model (inferred from mechanism); API-only models: not discussed [GT-007: Sec. 2 p.2; GT-005: Sec. 3 p.3; GT-008: Sec. 8 p.9].
- **Ratio.** "Up to 26x" is the average prompt length of the Human split over 1 gist token; the compressed prompts are short instructions of about 20-26 tokens, not documents; max sequence length 512 [GT-009: Abstract p.1; GT-010: Figure 3 caption p.6; GT-011: Sec. 4.1 p.4; GT-037: Appendix B p.13].
- **Quality loss.** Seen split near-identical to the uncompressed control; on the out-of-distribution Human split the ChatGPT win rate falls to 45.8% (LLaMA-7B) and 42.5% (FLAN-T5-XXL), where 50% is parity [GT-022: Sec. 5 p.5; GT-023: Sec. 5 p.5; GT-024: Sec. 4.3 p.5]. Human evaluation: LLaMA-7B 52.3% (CI 46.1-58.4) and FLAN-T5-XXL 40.6% (CI 34.6-46.8) [GT-027: Table 2 p.7; GT-028: Table 2 p.7]. Verbatim-copy failure: FLAN-T5 answered "Culture" instead of "Arts & Culture" [GT-030: Sec. 5.1 p.7; GT-031: Sec. 5.1 p.7].
- **Latency/compute.** One forward step on one A100: wall-time saving 6.8% vs no caching and 1.0% vs caching the instruction KV; FLOPs saving 40% vs no caching and .11% vs instruction caching [GT-045: Table 3 p.8; GT-046: Table 3 p.8]. Training on 4 A100-80GB, about 7 h (LLaMA-7B) and 25 h (FLAN-T5-XXL) [GT-039: Appendix B p.13; GT-040: Appendix B p.13; GT-041: Appendix B p.13].
- **Cost.** No prompt-token saving at the API (not an API method); storage: up to 26x more prompts cached than with full-instruction caching [GT-053: Sec. 6 p.8].
- **Limitations.** Loses instruction nuance; long and many-shot prompts not tested [GT-033: Sec. 8 p.9; GT-036: Sec. 8 p.9]. Only Alpaca+ instruction following was tested; not tested: coding, document QA, chat, summarization, structured data, math, PII [GT-063: Sec. 4.1 p.4; GT-064: Sec. 4.1 p.4].
- **Reproducibility.** Code, data, checkpoints released; code Apache-2.0, data partly CC BY-NC 4.0, LLaMA checkpoints are weight diffs needing base LLaMA-7B [GT-057: Appendix B p.13; GT-058: GitHub README (WebFetch) web; GT-059: GitHub README (WebFetch) web].

### 3.9 AutoCompressor — recursive summary vectors

- **Mechanism.** A pretrained LM is adapted to emit summary vectors for each segment; vectors from earlier segments are concatenated and prepended to later ones [AC-001: Abstract p.1; AC-003: Sec. 1 p.2; AC-004: Sec. 1 p.1]. Unsupervised language-modelling objective [AC-002: Abstract p.1]. OPT-1.3B/2.7B and Llama-2-7B (LoRA) [AC-006: Sec. 4 p.4; AC-007: Sec. 4.3 p.5; AC-008: Sec. 4.3 p.5].
- **Input/output.** Soft summary vectors, usable by the same model (inferred); no API support (inferred) [AC-004: Sec. 1 p.1; AC-005: Sec. 1 p.1].
- **Ratio.** 2,048 tokens to 50 vectors (40 tokens per vector) for OPT-2.7B; 4,096 to 100 for Llama-2 [AC-017: Sec. 4.1 p.4; AC-018: Sec. 4.3 p.5]. "30,720" is a training and evaluation sequence length for OPT, not a segment length; the Llama-2 model was trained on 6,144 [AC-012: Sec. 4.2 p.4; AC-013: Abstract p.1; AC-008: Sec. 4.3 p.5].
- **Quality loss.** Perplexity gains of only 1.6%-5.6% vs the no-context baseline [AC-026: Table 1 p.5]. In-context learning: summary vectors beat plain demonstrations on 8 of 11 tasks, but the Llama-2 AutoCompressor is worse than its initialisation on zero-shot and slightly worse on ICL [AC-049: Sec. 5 p.7; AC-050: Sec. 5 p.7; AC-051: Sec. 5 p.7; AC-052: Sec. 5 p.7]. No document-QA accuracy was reported [AC-079: Sec. 1 p.2].
- **Latency/compute.** Training on one A100 80 GB; storage 5 TB per 10B-token domain; compressor encoding time: not reported [AC-010: Sec. 1 p.2; AC-060: Sec. 6.1 p.8; AC-063: Sec. 6.2 p.9].
- **Limitations.** Only OPT up to 2.7B and Llama-7B; summary vectors lose information vs full attention [AC-066: Limitations p.9; AC-067: Limitations p.9]. Not tested: coding, document QA, chat, summarization, structured data, math, PII [AC-079: Sec. 1 p.2].
- **Reproducibility.** Code and checkpoints public [AC-070: footnote 1 p.1; AC-072: GitHub README (WebFetch) web]; no licence found on the GitHub page (absence only, WebFetch) [AC-071: GitHub page (WebFetch) web].

### 3.10 500xCompressor — KV-value soft tokens

- **Mechanism.** Encoder is a frozen LLM with trainable LoRA (about 0.25% extra parameters); the decoder is the same frozen LLM; output is per-layer KV values of 1, 4 or 16 tokens [XC-001: Abstract p.1; XC-002: Sec. 2.1 p.2; XC-003: Sec. 2.1 p.2]. Only LLaMa-3-8b-chat evaluated [XC-010: Sec. 4.1 p.4].
- **Input/output.** KV values tied to that LLM, model internals required (inferred) [XC-004: Sec. 2.1 p.2; XC-005: Sec. 2.1 p.3].
- **Ratio.** 6x to 480x from compressing 96-480-token abstracts into 16, 4 or 1 tokens [XC-012: Abstract p.1; XC-013: Sec. 4.1 p.4; XC-014: Sec. 1 p.1].
- **Quality loss.** The abstract's 62.26%-72.89% [XC-032: Abstract p.1] is the Average-F1 column of Table 5, normalised so the uncompressed Instruct row is 100: 16 tokens 72.89, 4 tokens 67.12, 1 token 62.26 [XC-033: Table 5 caption p.10; XC-034: Table 5 p.10; XC-036: Table 5 p.10; XC-038: Table 5 p.10; XC-040: Table 5 p.10]. It is the mean of five per-benchmark scores (derived from the row in XC-036), on LLaMa-3-8b-chat and extractive QA only. Loses to ICAE on some benchmarks [XC-022: Table 2 p.6; XC-025: Table 2 p.6]. Regeneration is not exact: "Kato modules" for "Kato complexes" [XC-049: Table 1 p.5; XC-050: Sec. 4.2 p.4]; no exact-match rate is reported [XC-053: Sec. 3.3 p.3].
- **Latency/compute.** Inference speed, memory, storage and hardware: not reported [XC-055: Sec. 5 p.7; XC-056: Sec. 5 p.7; XC-060: Table 3 caption p.9].
- **Limitations.** No limitations section [XC-062: Sec. 7 Conclusions p.7]. Not tested: coding, chat, summarization, structured data, math, PII, long documents [XC-074: Sec. 3.1 p.3].
- **Reproducibility.** Paper says open source [XC-065: Availability Statement p.7]; README: CC BY 4.0, but HF datasets and models "not open to the public", adapters on LLaMa-3-8b-Instruct [XC-066: GitHub README (WebFetch) web; XC-067: GitHub README (WebFetch) web; XC-068: GitHub README (WebFetch) web].

### 3.11 H2O — KV-cache eviction (inside the serving engine)

- **Mechanism.** Eviction policy for the generating model's KV cache that keeps recent tokens plus accumulated-attention "heavy hitters", budget split evenly [H2-001: Abstract p.1; H2-003: Sec. 5.1 Baselines p.7; H2-004: Appendix C.9 p.27]. Operates on the token-generation phase; prefill still runs in full [H2-002: Sec. 2 p.3; H2-006: Appendix A p.20].
- **Input/output.** Output is a smaller KV cache, not text; implemented by modifying a white-box OPT engine; no API or closed-model discussion [H2-013: Abstract p.1; H2-010: Appendix A System Details p.20; H2-012: Appendix A p.20].
- **Ratio.** 5-10x smaller KV cache, budgets of 4%, 10%, 20%, 60% of prompt length [H2-020: Sec. 5.1 p.7; H2-021: Appendix A Experiment Details p.20; H2-022: Sec. 5.1 Main Results p.8].
- **Quality loss.** Table 1 (5-shot): H2O 79.22 / 85.00 / 43.80 / 71.67 vs full cache 80.09 / 81.00 / 44.80 / 71.51 (the caption names no model) [H2-032: Table 1 p.8; H2-033: Table 1]. Summarization (XSUM, CNN/DM) only as plots, no numbers [H2-038: Sec. 5.1 Main Results p.8; H2-031: Appendix A p.20].
- **Latency/compute.** Up to 29x throughput vs DeepSpeed and Accelerate and 3x vs FlexGen, up to 1.9x lower latency at equal batch; most of it comes from larger batches and avoiding CPU offload [H2-063: Abstract p.1; H2-063b: Abstract p.1; H2-077: Sec. 5.2 Results p.9; H2-076: Sec. 5.2 Results p.9]. Per-request prompt-token saving: none [H2-080: Appendix A p.20].
- **Limitations.** Not tested: coding, multi-turn chat, structured data, PII, long-context benchmarks [H2-110: Sec. 5.1 Setup p.7]. Re-runs by other authors show PassageRetrieval collapsing (97.73 full vs 71.34 at a 1,024 budget) [EH-053: Table 6 p.10; EH-058: Table 6 p.10].
- **Reproducibility.** Code released, MIT badge [H2-100: Abstract p.1; H2-101: GitHub repo page web].

### 3.12 SnapKV — KV-cache selection after prefill (inside the serving engine)

- **Mechanism.** Per head, keeps top-voted prefix positions (pooled) plus the whole observation window; compression applied once after the prompt is processed [SK-001: Abstract p.1; SK-002: Abstract p.1; SK-003: Sec. 4.1 p.5; SK-005: Listing 1 p.5]. Fine-tuning free [SK-001: Abstract p.1]; needs a source-level change to attention code [SK-010: Figure 6 caption p.7; SK-011: Sec. 1 p.2].
- **Input/output.** KV cache, not text; tested only on open-weight models; no API discussion [SK-012: Sec. 5.3 p.9; SK-015: Sec. 6 p.12].
- **Ratio.** KV budgets of 1,024 / 2,048 / 4,096 on about 13k-token LongBench inputs (92% / 68% compression) [SK-020: Sec. 5.3 p.9; SK-034: Table 1 p.9].
- **Quality loss (Mistral-7B-Instruct, full KV vs SnapKV 1,024).** GovReport 32.85 to 25.89; code flat (Lcc 55.51 vs 55.65, RepoBench-P 52.88 vs 51.87) [SK-031: Table 1 p.9; SK-032: Table 1 p.9]. Failure example: only the country code of a phone number retrieved and the rest hallucinated without pooling [SK-006: Sec. 4.3 p.6].
- **Latency/compute.** A100 80 GB: at 16k input, batch 2, baseline above 100 ms/token vs under 40 ms (3.6x) [SK-060: Figure 7 caption p.8; SK-061: Sec. 5.1.2 p.7; SK-063: Sec. 5.1.2 p.8]. Prefill is not accelerated: "SnapKV's design does not cover the processing of the prompt inference" [SK-066: Sec. 6 p.12]. No prompt-token saving [SK-070: Sec. 6 p.12].
- **Limitations.** Cannot extend a model's long-context ability [SK-069: Sec. 6 p.12]. Not tested: math, structured data, PII [SK-103: Sec. 5.3 p.9].
- **Reproducibility.** Repo Apache-2.0; the paper text has no link to its own code [SK-091: GitHub repo page web; SK-090: Sec. 5.5 footnote p.11].

## 4. Task-fit analysis

**Rule used.** A method counts as *supported* for a family at a ratio only if a source shows the task score within 2 points of the uncompressed score at that ratio ("points" are percentage points of accuracy, EM, F1 or ROUGE). A method is *opposed* if a source shows a larger drop. If no source tested a method on the family, it is listed as untested and is never called suitable. Ratios are each source's own definition (section 3). Compressor cost is stated next to latency and tokens saved.

**What the local check can and cannot say about a 2-point margin.** With 40 items one item is 2.5 points, and an exact McNemar test needs a gap of at least 15 points at n=40 (section 8.2). So the local run can show that a method *lost* 15 points or more, and it can show "no item lost"; it cannot establish that a loss is below 2 points. Where the text says "within 2 points" for a local arm, read it as "no worse than the baseline on this sample, interval given".

### 4.1 Coding

- **Supported.** In the papers' LongBench "Code" column, compression with GPT-3.5-Turbo scores above the original: LLMLingua-2 58.9 at 5x and 62.8 at 3x against 54.2 [L2-034: Table 2 p.7; L2-035: Table 2 p.7; L2-043: Table 2 p.7]; CPC 63.5 [CPC-11: Table 2 p.6; CPC-09: Table 2 p.6]; EHPC 63.0 at 3x and 61.9 at 5x [EH-041: Table 4 p.8; EH-042: Table 4 p.8; EH-040: Table 4 p.8]. The LLMLingua-2 paper does not describe the column; the LongLLMLingua appendix lists code completion among LongBench's six categories [LongLL-CL-23: Appendix B.1 p.12]. SnapKV leaves code flat (Lcc 55.65 against 55.51 at a 1,024-token KV budget) but saves no prompt tokens [SK-031: Table 1 p.9; SK-032: Table 1 p.9; SK-070: Sec. 6 p.12]. Locally, query-aware selection of whole code blocks at 2.08x scored 0.900 against 0.875 uncompressed [local: raw/results/results.md table A code].
- **Opposed.** On Llama-3.1-8B, EHPC's own comparison shows RepoBench-P at 42.8 for prompt compression against 49.25 for the full cache, and the authors write that prompt compression "exhibits a decline in performance on code-related tasks and few-shot learning tasks" [EH-054: Table 6 p.10; EH-053: Table 6 p.10; EH-066: Sec. 5.2 Results p.10]. Locally, on exact lookup of a constant's value in a Python module, LLMLingua-2 at 2x scored 0.550 against 0.875 (difference −0.325, p 0.001), at 3x 0.450, LLMLingua v1 with GPT-2 0.175, random word drop 0.325; the Selective-Context-style filter scored 0.725 (difference −0.150, p 0.146, not separable from the baseline) [local: raw/results/results.md table A code].
- **Ratio before the score falls by more than 2 points.** The sources disagree, so no token-level ratio is supported: the papers' Code column shows no loss up to 5x for LLMLingua-2 and EHPC (GPT-3.5-Turbo), while EHPC's Llama-3.1-8B comparison shows a drop of 6.45 points (derived from [EH-054: Table 6 p.10; EH-053: Table 6 p.10]) and no token-level arm kept the local lookup task within 15 points at about 2x. For selection of whole blocks, the local control at 2.08x got 2 items wrong that the baseline had right and 3 right that the baseline had wrong (derived from tables A and E, n=40; the interval does not exclude a loss of several points), and CPC reports 3x on the Code column [CPC-08: Sec. 4.4 p.6; CPC-11: Table 2 p.6].
- **Latency and cost, including the compressor.** Locally (CPU target), LLMLingua-2 at 2x costs 2.16 s median and 3.63 s p90 of compressor wall time and 7.17 CPU-seconds on average per code request; end-to-end p50 was 11.96 s against 16.22 s uncompressed, so the speed gain on a slow target comes with the loss above. LLMLingua v1 with GPT-2 was slower than no compression (p50 18.27 s) [local: raw/results/results.md table A code].
- **Failure mode to watch.** Identifiers are split and keywords dropped: at 2x LLMLingua-2 inserted 27.1 stray " _ " per file and kept only 0.16 of `def ` and 0.43 of `return`; `MAX_` constants were never intact (0.00) [local: raw/results/results.md table H]. In all 18 wrong answers at 2x the answer string was still in the compressed text (spaces ignored), so the model misread damaged code rather than lacking the value [local: raw/results/results.md table E].
- **How thin the evidence is.** Thin and contradictory. No paper tests exact identifier recall; the Code column is undescribed; the one local test is a synthetic lookup of constants and says nothing about code generation or editing.

### 4.2 Long-document QA and RAG

- **Supported (question-aware methods).** LongLLMLingua at about 4x on NaturalQuestions with 20 documents scores 75.0 / 71.8 / 71.2 / 71.2 / 74.7 by answer position against 75.7 / 57.3 / 54.1 / 55.4 / 63.1 uncompressed [LongLL-CL-4: Table 1 p.7; LongLL-CL-2: Table 1 p.7]; LongBench average 48.8 at 3x and 48.3 at 6x against 44.0 [LongLL-CL-16: Table 2 p.8; LongLL-CL-17: Table 2 p.8; LongLL-CL-18: Table 2 p.8]. CPC: 50.0 at a 3,000-token budget and 49.5 at 2,000 against 44.0, target LLM not named [CPC-08: Sec. 4.4 p.6; CPC-11: Table 2 p.6; CPC-17: Table 2 p.6; CPC-09: Table 2 p.6; CPC-47: Sec. 4.3 p.5]. EHPC: 49.7 at 3x and 49.6 at 5x [EH-041: Table 4 p.8; EH-042: Table 4 p.8; EH-040: Table 4 p.8]. Locally, a question-aware block selector kept all 40 QA items right at 1.90x [local: raw/results/results.md table A qa].
- **Opposed (question-agnostic methods).** LLMLingua-2 at 3.9x on the same 20-document task scores 48.6 / 44.5 / 43.6 / 40.9 / 39.9 [L2-059: Table 11 p.18; L2-060: Table 11 p.18]; LLMLingua v1 at 3.8x scores 25.5 to 30.0 [LongLL-CL-5: Table 1 p.7]; Selective Context at 3.7x scores 19.5 to 43.8 [SC-T05: Table 11 p.18]. Locally, LLMLingua-2 at 2x scored 0.750 and at 3x 0.625 against 1.000; the Selective-Context-style filter 0.575; LLMLingua v1 0.250; random drop 0.300 [local: raw/results/results.md table A qa].
- **Ratio before the score falls by more than 2 points.** Question-aware: at least 4x on NaturalQuestions-20 (worst position 0.7 points below the original, derived from [LongLL-CL-4: Table 1 p.7; LongLL-CL-2: Table 1 p.7]) and at least 5x to 6x on the LongBench average (CPC at its 2,000-token budget, LongLLMLingua at 6x). Question-agnostic: LLMLingua-2 is within 2 points only on the LongBench average at 3x (42.4 against 44.0, derived from [L2-035: Table 2 p.7; L2-043: Table 2 p.7]); at 5x the average is 39.1 and on the 20-document task every position loses at least 10 points. Locally no question-agnostic arm stayed within 15 points at about 2x.
- **Latency and cost, including the compressor.** LongLLMLingua's compressor stage takes 7.70 s on average and 1.64 s at the median on an A100, CPC 0.28 s and 0.15 s, LLMLingua-2 0.23 s and 0.1 s [CPC-35: Table 5 p.7; CPC-34: Table 5 p.7; CPC-36: Table 5 p.7; CPC-37: Table 5 p.7]; on a 14,354-token subset LongLLMLingua took 67.44 s against 1.27 s for LLMLingua-2 [EH-084: Table 5 p.9; EH-085: Table 5 p.9; EH-088: Table 5 caption p.9]. A question-aware method must be re-run for every question and its output cannot be cached [LongLL-IO-3: Limitation p.9; LongLL-LIM-1: Limitation p.9]. API cost per 1,000 samples falls from 4.6 to 1.3 on NaturalQuestions with the compressor's compute not priced [LongLL-COST-1: Table 9 p.17; LongLL-COST-2: Table 9 p.17; LongLL-COST-3: Table 9 p.17; LongLL-COST-4: Appendix D p.16].
- **Failure mode to watch.** A compressor that does not see the question drops the passage that holds the answer; LLMLingua-2's authors show this on other datasets [L2-094: Appendix G p.13]. Question-aware pruning can still corrupt an entity ("209" for "2019") and is weaker when the question and the passage are only loosely related [LongLL-LIM-3: Sec. 4.4 p.5; LongLL-LIM-4: Figure 7 p.18; LongLL-LIM-2: Limitation p.9].
- **How thin the evidence is.** Moderate for the direction (three papers and the local control agree), thin for the size. The target LLMs differ between papers, CPC does not name its own, and the local control works only because each synthetic question names a rare token that appears in the answer-bearing paragraph; real questions share less vocabulary with their evidence, so the local 1.000 is a best case for lexical selection and says nothing about CPC or LongLLMLingua themselves.

### 4.3 Multi-turn chat

- **Supported.** No method. The only compressed multi-turn test is LLMLingua v1 on ShareGPT, where all rounds but the last form the prompt, and it is scored as similarity to the answer the uncompressed prompt produced, not against a task answer: BLEU 27.36 at 1.9x and 19.55 at 3.3x [LLv1-CL-18: Table 1 p.6; LLv1-CL-20: Table 1 p.6; LLv1-CL-23: Appendix A.1 p.12]. A similarity-to-self score cannot show whether the answer got worse.
- **Opposed.** No direct evidence either way. Selective Context at a 0.65 reduction ratio made gpt-3.5 refuse 19 of 200 questions and shortened its answers by 35% [SC-049: Table 3 p.6; SC-051: Sec. 5.2 p.7].
- **Ratio before the score falls by more than 2 points.** Not determinable from any source.
- **Latency and cost, including the compressor.** Not measured on chat by any source. The local per-token costs in section 6.9 apply to any text, but they say nothing about quality.
- **Failure mode to watch.** Compression applied to the history changes what the assistant "remembers"; LongLLMLingua, LLMLingua-2, CPC, SCOPE, EHPC, Gist, AutoCompressor, 500xCompressor and H2O all state or imply that multi-turn chat was not tested [LongLL-TASK-4: Sec. 1 contributions p.2; L2-114: Limitations p.9; CPC-58: Sec. 4.1 p.5; SCP-78: Sec. 1 p.2; EH-136: Appendix D.2 p.16; GT-064: Sec. 4.1 p.4; AC-079: Sec. 1 p.2; XC-074: Sec. 3.1 p.3; H2-110: Sec. 5.1 Setup p.7].
- **How thin the evidence is.** Empty. Not run locally either (no multi-turn family in the local check).

### 4.4 Summarization

- **Supported.** LLMLingua-2 on the LongBench summarization column, GPT-3.5-Turbo: 25.3 at 5x and 26.3 at 3x against 26.5 [L2-034: Table 2 p.7; L2-035: Table 2 p.7; L2-043: Table 2 p.7]; EHPC 25.1 against 26.5 [EH-041: Table 4 p.8; EH-040: Table 4 p.8]. SCOPE, GPT-4o-mini, ROUGE-1: GovReport 43.59 and 43.73 at 5x against 43.78; Arxiv 38.66 at 2x against 40.49 [SCP-29: Table 2 p.7; SCP-30: Table 2 p.7; SCP-26: Table 2 p.7; SCP-23: Table 1 p.6; SCP-16: Table 1 p.6]. SCOPE has no released code (section 5.3).
- **Opposed.** CPC's summarization column is 23.8 against 26.5 [CPC-11: Table 2 p.6; CPC-09: Table 2 p.6]; SCOPE at 5x on Arxiv is 37.75 against 40.49 [SCP-19: Table 1 p.6; SCP-16: Table 1 p.6]; in the SCOPE authors' own run LLMLingua-2 at 5x scores 40.46 on GovReport [SCP-27: Table 2 p.7]; SnapKV on GovReport 25.89 against 32.85 (KV cache, no prompt tokens saved) [SK-032: Table 1 p.9; SK-031: Table 1 p.9]. The metric matters: LLMLingua-2 at 3.1x on MeetingBank has ROUGE-1 48.64 against 47.28 but ROUGE-2 22.96 against 26.66 and BLEU 17.37 against 22.34 [L2-040: Table 1 p.6; L2-042: Table 1 p.6].
- **Ratio before the score falls by more than 2 points.** LLMLingua-2: 3x to 5x on the LongBench summarization column and 3.1x on MeetingBank ROUGE-1; the n-gram metrics on MeetingBank fall by 3.70 (ROUGE-2) and 4.97 (BLEU) points (derived from [L2-040: Table 1 p.6; L2-042: Table 1 p.6]), and the SCOPE authors' run of LLMLingua-2 shows a 3.32-point loss at 5x on GovReport (derived) [SCP-27: Table 2 p.7; SCP-26: Table 2 p.7]. Planning figure: up to 3x. SCOPE: 5x on GovReport, 2x on Arxiv (1.83 points, derived from [SCP-23: Table 1 p.6; SCP-16: Table 1 p.6]).
- **Latency and cost, including the compressor.** LLMLingua-2 end-to-end on MeetingBank, V100: 14.9 s uncompressed against 7.5 s at 3x, compressor 0.4 s; tokens per request 970 against 3,003 [L2-070: Table 5 p.8; L2-071: Table 5 p.8; L2-072: Table 5 p.8; L2-073: Sec. 5 Latency Evaluation p.8; L2-078: Table 5 p.8; L2-080: Table 1 p.6; L2-081: Table 2 p.7; L2-042: Table 1 p.6]. SCOPE takes 4.20 s per GovReport document on an A100 against 2.79 s for LongLLMLingua [SCP-59: Sec. 4.5 p.10; SCP-60: Sec. 4.5 p.10].
- **Failure mode to watch.** ROUGE-1 can hide lost n-grams; SCOPE rewrites text and reports no factuality metric [SCP-72: Sec. 3.3.2 p.6]; the two disagree on LLMLingua-2 at 5x (within 2 points on the LongBench column, 3.32 below on GovReport (derived)).
- **How thin the evidence is.** Moderate for LLMLingua-2 to 3x, thin above. No human or factuality evaluation anywhere; not run locally.

### 4.5 Structured data (JSON, tables, logs)

- **Supported.** No paper. At least nine sources state that structured data was not tested [LLv1-TASK-6: Abstract p.1; LongLL-TASK-5: Sec. 1 contributions p.2; L2-115: Limitations p.9; CPC-59: Sec. 4.1 p.5; EH-136: Appendix D.2 p.16; SC-103: Sec. 4.1 p.4; H2-110: Sec. 5.1 Setup p.7; SK-103: Sec. 5.3 p.9; GT-064: Sec. 4.1 p.4]. Locally, a record-level, question-aware selector kept 0.95 of log lines and 0.95 of JSON items at 2.01x [local: raw/results/results.md table I].
- **Opposed.** Locally, on lookups of a value in 20 plain log lines or 20 JSON records, LLMLingua-2 at 2x scored 0.20 on log lines and 0.40 on JSON; the Selective-Context-style filter 0.55 on log lines and 0.95 on JSON; LLMLingua v1 0.20 and 0.20; random drop 0.15 and 0.20 [local: raw/results/results.md table I]. Over all 40 items LLMLingua-2 at 2x scored 0.300 against 1.000 uncompressed (p<0.001) [local: raw/results/results.md table A logs].
- **Ratio before the score falls by more than 2 points.** None supported for token-level compression. Selecting whole records, about 2x, is supported only by the local control, on 20 items per record type (interval 0.76 to 0.99) and only for questions that name the record they ask about.
- **Latency and cost, including the compressor.** LLMLingua-2 at 2x: 2.15 s median and 3.30 s p90 compressor wall time, 7.06 CPU-seconds per request; end-to-end p50 12.30 s against 16.13 s uncompressed [local: raw/results/results.md table A logs].
- **Failure mode to watch.** The field names are what disappears: LLMLingua-2 at 2x kept 0.00 of every `svc=`, `req=`, `status=`, `latency_ms=`, `user=` and `region=` key, so the model sees bare numbers and cannot tell which is the latency [local: raw/results/results.md table H]. The Selective-Context-style filter kept the identifiers (0.90 of items with every key string) but still lost 25 points on the 40 items [local: raw/results/results.md table C and table A logs].
- **How thin the evidence is.** Local only, synthetic, one 3B target, and the query-aware control exploits question words that appear in the record. A question such as "why did latency spike" would not name a record.

### 4.6 Reasoning and math

- **Supported.** LLMLingua v1 on GSM8K (8-shot chain-of-thought, GPT-3.5-Turbo, exact match) scores 79.08 at 5x, 77.41 at 14x and 77.33 at 20x against 78.85 uncompressed [LLv1-CL-2: Table 2 p.6; LLv1-CL-3: Table 2 p.6; LLv1-CL-4: Table 2 p.6; LLv1-CL-1: Table 2 p.6]; LLMLingua-2 scores 79.08 at 5x and 77.79 at 14x [L2-032: Table 3 p.7; L2-049: Table 3 p.7]. On BBH, LLMLingua v1 is 70.11 at 3x and LLMLingua-2 70.02 at 3x against 70.07 [LLv1-CL-2: Table 2 p.6; L2-033: Table 3 p.7; L2-049: Table 3 p.7].
- **Opposed.** BBH at 5x falls to 61.60 (LLMLingua v1) and 61.94 (LLMLingua-2), and LLMLingua v1 reaches 56.85 at 7x [LLv1-CL-3: Table 2 p.6; L2-033: Table 3 p.7; LLv1-CL-4: Table 2 p.6]. A third-party run of Selective Context scores 53.98 on GSM8K at 5x [SC-T04: Table 3 p.7].
- **Ratio before the score falls by more than 2 points.** GSM8K: up to 20x for LLMLingua v1 (1.52 points below, derived from [LLv1-CL-4: Table 2 p.6; LLv1-CL-1: Table 2 p.6]) and 14x for LLMLingua-2 (1.06 points below, derived from [L2-032: Table 3 p.7; L2-049: Table 3 p.7]). BBH: 3x for both; the loss at 5x is 8.47 points for LLMLingua v1 (derived from [LLv1-CL-3: Table 2 p.6; LLv1-CL-1: Table 2 p.6]). A trivial baseline that keeps only one demonstration scores 77.10 on GSM8K at 6x [LLv1-CL-6: Table 2 p.6], 1.75 points below full-shot (derived), so a 5x to 6x saving needs no compressor at all; LLMLingua v1's advantage shows only at 14x to 20x, where it holds 77.41 to 77.33.
- **Latency and cost, including the compressor.** LLMLingua v1 on a V100: GSM8K end-to-end 8.6 s baseline against 4.9 / 2.3 / 1.3 s at 2x / 5x / 10x, compressor alone 0.8 / 0.3 / 0.2 s [LLv1-LAT-3: Table 6 p.8; LLv1-LAT-4: Table 6 p.8; LLv1-LAT-5: Table 6 p.8; LLv1-LAT-6: Sec. 5.5 p.8; LLv1-LAT-7: Table 6 p.8]. On CPU, section 6.9 gives the local cost of LLMLingua-2 and of a GPT-2 scorer.
- **Failure mode to watch.** Multi-step sub-tasks degrade first; the authors name `tracking_shuffled_objects_seven_objects` [LLv1-CL-16: Sec. 5.2 p.6]. In LLMLingua v1 the demonstrations absorb most of the compression and the question is compressed only lightly [LLv1-MECH-3: Sec. 4.1 p.4; LLv1-Q-1: Sec. 5.1 Implementation Details p.5].
- **How thin the evidence is.** Two papers, one target model (GPT-3.5-Turbo), two benchmarks, and the compressed object is a few-shot prompt. A zero-shot prompt has no demonstrations to remove (inferred). Not run locally.

### 4.7 Sensitive and regulated content

- **Supported.** No method. At least eleven sources state that sensitive or PII content was not tested [LLv1-TASK-7: Abstract p.1; LongLL-TASK-7: Sec. 1 contributions p.2; L2-117: Limitations p.9; CPC-60: Sec. 4.1 p.5; SCP-80: Sec. 4.1 p.7; EH-136: Appendix D.2 p.16; GT-064: Sec. 4.1 p.4; AC-079: Sec. 1 p.2; XC-074: Sec. 3.1 p.3; H2-110: Sec. 5.1 Setup p.7; SC-105: Sec. 4.1 p.4].
- **Opposed.** Locally, on 50 synthetic case notes with nine sensitive fields, no compressor kept every field: LLMLingua-2 at 2x kept all nine fields in 0.00 of records (date of birth, address, e-mail, phone and case reference each survived in 0.00 of records, diagnosis in 0.66); the Selective-Context-style filter 0.18 at only 1.63x; LLMLingua v1 and random drop 0.00 [local: raw/results/results.md table D].
- **Ratio before the score falls by more than 2 points.** None; 1x is the only ratio any source supports.
- **Latency and cost, including the compressor.** Not worth measuring; compression buys tokens at the price of silently altered identity data.
- **Failure mode to watch.** Two opposite errors. Fields are damaged (LLMLingua-2 at 2x turned the date of birth "14/04/1984" into "14 1984" and cut an e-mail address to "elif nakamura24" in the first record [local: raw/results/examples.txt]), and fields that should have been removed survive (LLMLingua-2 at 2x left 1.00 of names and 1.00 of IBANs in place [local: raw/results/results.md table D]). Compression is neither a safe way to keep sensitive data intact nor a redaction method.
- **How thin the evidence is.** Local only, synthetic records, one language, verbatim-string survival rather than a downstream task.

## 5. Constraint matrix (methods against operating constraints)

How to read it. Each cell starts with a rating, then the fact, then its source. Ratings: **Yes** / **No** / **Partial** (works with a stated condition) / **Not reported** (the source does not say; nothing is estimated) / **N/A** (the question does not apply to this kind of method). `[ID]` is a machine-verified paper quote (page and table in `raw/ledger/EVIDENCE_INDEX.md`); `[local: ...]` is a number from this report's own run on this machine (CPU only), which exists only for the three methods that run here. Ratings marked "(inferred)" follow from the mechanism, not from a sentence in the paper. The LiteLLM effort column is my judgement from the gateway's existing integration pattern: a pre-call hook that calls a text-in, text-out compressor in a worker thread under a timeout [local: raw/gateway_facts.txt].

### 5.1 Interface and training

| Method | Works with a closed-API target (no model internals) | Needs training or fine-tuning | Output readable by a human | Keeps exact strings |
|---|---|---|---|---|
| LLMLingua v1 | **Yes**: text in, text out, aimed at black-box LLMs [LLv1-IO-1: Sec. 1 p.1; LLv1-IO-4: Sec. 1 p.1] | **Partial**: needs a small causal LM; its alignment step is instruction tuning of that LM [LLv1-MECH-2: Abstract p.1; LLv1-MECH-6: Sec. 4.3 p.5] | **Partial**: visibly garbled; GPT-4 can reconstruct it, GPT-3.5-Turbo struggles [LLv1-IO-5: Figure 1 p.3; LLv1-IO-6: Figure 1 p.3] | **No**: local, with plain GPT-2 as scorer, all key strings verbatim in 0.28 of QA, 0.15 of log and 0.05 of code items [local: raw/results/results.md table C] |
| LongLLMLingua | **Yes**: GPT-3.5-Turbo and LongChat targets; re-run for every question [LongLL-IO-1: Sec. 5 Implementation details p.5; LongLL-IO-4: Footnote 6 p.5; LongLL-IO-3: Limitation p.9] | **No** extra training, but needs a 7B scorer (LLaMA-2-7B-Chat) [LongLL-MECH-9: Sec. 5 Implementation details p.6] | **Partial** (inferred from token-level pruning) [LongLL-MECH-3: Sec. 1 p.1] | **No**: pruning turned "2019" into "209" until subsequence recovery was added [LongLL-LIM-3: Sec. 4.4 p.5; LongLL-LIM-4: Figure 7 p.18] |
| LLMLingua-2 | **Yes**: hard text of original words; GPT-3.5-Turbo and Mistral-7B targets [L2-002: Sec. 4.2 p.6; L2-021: Sec. 1 Contributions p.2; L2-022: Sec. 5 Implementation Details p.6] | **Pre-trained**: a trained keep/drop classifier is released, so the user trains nothing [L2-001: Sec. 4 p.5; L2-103: model card web] | **Partial**: local output has stray spaces and dropped punctuation, 27.1 spurious " _ " per code file at 2x [local: raw/results/results.md table H] | **No**: local, 0.00 of log and code items keep all key strings verbatim at 2x and 3x [local: raw/results/results.md table C] |
| Selective Context | **Yes**: output given to GPT-3.5 and GPT-4 [SC-010: Sec. 4.2 p.4; SC-011: Sec. 4.2 p.4] | **No**: an off-the-shelf base LM scores tokens [SC-003: Sec. 4.4 p.5; SC-004: Sec. 4.4 p.5] | **No**: ungrammatical [SC-008: Fig. 2 p.3] | **Partial**: local re-implementation keeps all key strings in 0.93 of QA, 0.90 of log and 1.00 of code items; structure inside lines is not kept (table H) [local: raw/results/results.md table C] |
| CPC | **Yes** (inferred): the paper runs it with GPT-4o as backbone [CPC-07: Sec. 4.4 Larger backbone p.7] | **Yes**: LoRA on a 7B encoder, one A100 80 GB; code and data released, checkpoint release not stated [CPC-03: Sec. 3.3 p.5; CPC-04: Sec. 4.2 p.5; CPC-52: Abstract p.1] | **Yes** (design claim, no user study) [CPC-06: Sec. 1 p.2] | **Yes** (inferred): whole sentences are kept or dropped [CPC-01: Abstract p.1; CPC-02: Sec. 3.4 Inference p.5]; not measured |
| SCOPE | **Yes**: GPT-4o-mini is the main downstream model [SCP-12: Sec. 4.1 p.7] | **No**: training-free, with a public summarizer model (bart-large-cnn by default) [SCP-01: Abstract p.1; SCP-04: Sec. 4 p.6] | **Yes**: generated text [SCP-11: Sec. 3.3.2 p.6] | **No**: abstractive rewrite, no factuality metric reported [SCP-11: Sec. 3.3.2 p.6; SCP-72: Sec. 3.3.2 p.6] |
| EHPC | **Partial**: needs a local LLM with attention access; authors state it can serve API-based models [EH-020: Sec. 1 p.2; EH-021: Sec. 3.4 p.6] | **No**: training-free, one-time search for evaluator heads [EH-001: Abstract p.1; EH-007: Sec. 1 p.2] | **Partial**: fragments [EH-004: Sec. 3.4 p.6; EH-006: Appendix G p.19] | **Not reported** (token deletion) [EH-136: Appendix D.2 p.16] |
| Gist Tokens | **No**: output is activations usable only by the fine-tuned model; API models not discussed [GT-007: Sec. 2 p.2; GT-005: Sec. 3 p.3; GT-008: Sec. 8 p.9] | **Yes**: instruction fine-tuning with gist tokens [GT-001: Abstract p.1; GT-055: Sec. 3 p.3] | **No**: soft tokens | **No**: FLAN-T5-XXL answered "Culture" for "Arts & Culture" [GT-030: Sec. 5.1 p.7; GT-031: Sec. 5.1 p.7] |
| AutoCompressor | **No** (inferred): summary vectors for the same model [AC-004: Sec. 1 p.1; AC-005: Sec. 1 p.1] | **Yes**: fine-tuned, unsupervised objective [AC-001: Abstract p.1; AC-002: Abstract p.1] | **No**: vectors | **Not reported** [AC-079: Sec. 1 p.2] |
| 500xCompressor | **No** (inferred): KV values tied to one LLM [XC-004: Sec. 2.1 p.2; XC-005: Sec. 2.1 p.3] | **Yes**: LoRA encoder, about 0.25% extra parameters [XC-001: Abstract p.1; XC-002: Sec. 2.1 p.2] | **No**: KV values | **No**: "Kato modules" for "Kato complexes"; no exact-match rate [XC-049: Table 1 p.5; XC-050: Sec. 4.2 p.4; XC-053: Sec. 3.3 p.3] |
| H2O | **No**: edits the KV cache of a white-box engine [H2-010: Appendix A System Details p.20; H2-012: Appendix A p.20] | **No**: no training or fine-tuning in the experiments [H2-009: Sec. 2 p.3] | **N/A**: the prompt text is not changed [H2-013: Abstract p.1] | **Partial**: PassageRetrieval 97.73 full cache vs 71.34 at a 1,024 budget in a third-party run [EH-053: Table 6 p.10; EH-058: Table 6 p.10] |
| SnapKV | **No**: open-weight models only [SK-012: Sec. 5.3 p.9; SK-015: Sec. 6 p.12] | **No**: fine-tuning free, but needs a source-level change to attention code [SK-001: Abstract p.1; SK-010: Figure 6 caption p.7] | **N/A**: KV cache, not text [SK-012: Sec. 5.3 p.9] | **Partial**: only the country code of a phone number retrieved without pooling [SK-006: Sec. 4.3 p.6] |

### 5.2 Compute and input limits

CPU numbers are measured here (4 torch threads, Intel i7-10610U, no GPU) and are the only CPU numbers in this report; every other CPU cell is "not measured" because the method needs a 7B-class model, model internals, or code that is not released. GPU numbers are the papers' own, on their hardware.

| Method | Compressor on CPU | Compressor on GPU | Maximum input length |
|---|---|---|---|
| LLMLingua v1 | **Slow**: 13.25 ms wall and 34.48 CPU-s per 1k input tokens with GPT-2 small; p90 wall 14.32 s on code items, above the gateway's 10 s timeout [local: raw/results/results.md table G and table A] | **Yes**: V100 32 GB, compressor 0.8 / 0.3 / 0.2 s at 2x / 5x / 10x on GSM8K [LLv1-LAT-3: Table 6 p.8; LLv1-LAT-5: Table 6 p.8; LLv1-LAT-6: Sec. 5.5 p.8; LLv1-LAT-7: Table 6 p.8] | **Not reported** [LLv1-LAT-4: Table 6 p.8] |
| LongLLMLingua | **Not measured** (7B scorer) | **Yes**: V100 32 GB [LongLL-HW-1: Appendix B.2 p.13]; compressor stage 7.70 s average and 1.64 s median on an A100 in CPC's table; 67.44 s on a 14,354-token subset in EHPC's table [CPC-35: Table 5 p.7; CPC-34: Table 5 p.7; EH-084: Table 5 p.9; EH-088: Table 5 caption p.9] | **Not reported** [LongLL-LIM-7: Appendix B.1 p.13] |
| LLMLingua-2 | **Yes**: 4.67 ms wall and 14.22 CPU-s per 1k input tokens (mBERT, 110M) [local: raw/results/results.md table G]; model load 3.79 s and 103 MB resident memory added [local: raw/results/load_costs.txt] | **Yes**: V100 32 GB, 0.5 / 0.4 / 0.4 s at 2x / 3x / 5x; peak memory 2.1 GB [L2-072: Table 5 p.8; L2-073: Sec. 5 Latency Evaluation p.8; L2-074: Appendix I p.14] | **Not reported**; its training chunks are at most 512 tokens [L2-013: Sec. 3.1 Chunk-Wise Compression p.4] |
| Selective Context | **Yes** (re-implementation with GPT-2): 4.62 ms wall and 13.04 CPU-s per 1k input tokens [local: raw/results/results.md table G]; the paper's own code was not run | **Slow in a third-party run**: 15.9 / 15.6 / 15.5 s on V100, peak memory 26.5 GB [SC-T07: Table 5 p.8; SC-T08: Appendix I p.14; SC-T09: Sec. 5 Baselines p.7; L2-076: Sec. 5 Latency Evaluation p.8] | **Partial**: tested on items under 2,048 tokens [SC-083: Sec. 4.1 p.4] |
| CPC | **Not measured** (7B encoder) | **Yes**: A100, average 0.28 s and median 0.15 s for the compressor stage [CPC-35: Table 5 p.7; CPC-34: Table 5 p.7] | **Not reported** [CPC-50: Sec. 4.2 p.5] |
| SCOPE | **Not measured** (no released code) | **Yes**: A100 80 GB, 4.20 s per GovReport document [SCP-59: Sec. 4.5 p.10; SCP-60: Sec. 4.5 p.10] | **Not reported** [SCP-67: Sec. 3.3.1 p.5] |
| EHPC | **Not measured** (needs a local 8B evaluator) | **Yes**: a 40 GB-VRAM GPU, 0.88 s to compress a 14,354-token prompt to 2,048 tokens [EH-083: Table 5 p.9; EH-084: Table 5 p.9; EH-085: Table 5 p.9; EH-086: Table 5 p.9; EH-087: Sec. 5.1 Compression Latency p.9; EH-088: Table 5 caption p.9; EH-089: Sec. 5.1 Compression Latency p.9; EH-049: Sec. 5.1 Compression Latency p.9] | **Partial**: 14,354 tokens in the timing subset [EH-084: Table 5 p.9] |
| Gist Tokens | **N/A**: model-internal | **Yes**: A100; training about 7 h (LLaMA-7B) on 4 A100 80 GB [GT-045: Table 3 p.8; GT-039: Appendix B p.13] | **Partial**: maximum sequence length 512 [GT-037: Appendix B p.13] |
| AutoCompressor | **N/A**: model-internal | **Not reported** for encoding; training on one A100 80 GB [AC-010: Sec. 1 p.2] | **Partial**: 2,048 tokens into 50 vectors (OPT-2.7B), 4,096 into 100 (Llama-2) [AC-017: Sec. 4.1 p.4; AC-018: Sec. 4.3 p.5] |
| 500xCompressor | **N/A**: model-internal | **Not reported** [XC-055: Sec. 5 p.7; XC-056: Sec. 5 p.7; XC-060: Table 3 caption p.9] | **Partial**: 96 to 480 tokens compressed into 16, 4 or 1 token [XC-012: Abstract p.1; XC-013: Sec. 4.1 p.4; XC-014: Sec. 1 p.1] |
| H2O | **N/A**: inside the serving engine | **N/A**: engine-level; up to 29x throughput versus other engines, no per-request prompt-token saving [H2-063: Abstract p.1; H2-080: Appendix A p.20] | **Not reported**; budgets of 4% to 60% of the prompt [H2-020: Sec. 5.1 p.7; H2-021: Appendix A Experiment Details p.20; H2-022: Sec. 5.1 Main Results p.8] |
| SnapKV | **N/A**: inside the serving engine | **Yes**: A100 80 GB; decoding below 40 ms per token against above 100 ms at 16k input, batch 2; prefill not accelerated [SK-060: Figure 7 caption p.8; SK-061: Sec. 5.1.2 p.7; SK-063: Sec. 5.1.2 p.8; SK-066: Sec. 6 p.12] | **Partial**: about 13k-token LongBench inputs, 16k in the latency test [SK-020: Sec. 5.3 p.9; SK-034: Table 1 p.9; SK-060: Figure 7 caption p.8] |

### 5.3 Language coverage, licence and effort to integrate in the LiteLLM gateway

| Method | Languages | Licence | Effort in the LiteLLM gateway (judgement) |
|---|---|---|---|
| LLMLingua v1 | **Not reported**: English datasets; ShareGPT mixes languages, no breakdown [LLv1-LIM-7: Appendix A.1 p.12] | **MIT**, `pip install llmlingua` [LLv1-REP-1: Footnote 1 p.1; LLv1-REP-2: LICENSE web; LLv1-REP-3: README web] | **Medium**: fits the hook, but the v1 path crashed on the installed transformers 5.20.1 and the pinned 4.46.3 overlay conflicts with LiteLLM 1.106.0's pins on huggingface-hub and tokenizers [local: raw/gateway_facts.txt] |
| LongLLMLingua | **Not reported** | **MIT** (same repo); the licence of the LLaMA-2-7B-Chat scorer is not discussed [LongLL-REP-2: LICENSE web; LongLL-REP-4: Sec. 5 footnote 9 p.6] | **High**: a 7B scorer service and a per-question call that cannot be cached [LongLL-IO-3: Limitation p.9; LongLL-LIM-1: Limitation p.9] |
| LLMLingua-2 | **Partial**: multilingual encoders; trained on English only; Chinese is the only other language tested [L2-003: Sec. 5 Implementation Details p.6; L2-092: Appendix J p.14; L2-093: Appendix J p.14] | **MIT** [L2-100: Abstract footnote p.1; L2-101: Sec. 6 p.9; L2-102: GitHub About/Resources web; L2-103: model card web] | **Low**: already wrapped by a 71-line adapter called from the pre-call hook with a 10 s timeout [local: raw/gateway_facts.txt] |
| Selective Context | **Not reported** (mixed-language ShareGPT, no breakdown) [SC-084: Sec. 4.1 p.4] | **MIT** per the README [SC-090: Abstract p.1; SC-091: README web] | **Medium** (inferred): text in and out, but a base LM and a noun-chunker [SC-006: Sec. 3.2 p.3] have to be packaged |
| CPC | **Not reported**; trained on synthetic questions over English Wikipedia [CPC-49: Sec. 3.2 p.3] | **Apache-2.0** [CPC-53: LICENSE web] | **High**: a 7B encoder service on an A100-class GPU, and the question has to be extracted from the messages [CPC-03: Sec. 3.3 p.5; CPC-04: Sec. 4.2 p.5] |
| SCOPE | **English only** [SCP-70: App. A.2 p.13] | **None**: the official repository read "code coming soon." on 2026-11-05 [SCP-73: Footnote 1 p.1; SCP-74: README web] | **Not possible today** as released code; models are public, so a re-implementation is possible [SCP-75: Sec. 1 p.2] |
| EHPC | **English only** (LongBench English subsets) [EH-110: Appendix D.2 p.16] | **None found**: no code or checkpoint [EH-120: Appendix B p.14; EH-121: NeurIPS 2025 poster page web; EH-122: arXiv abs page web] | **Not possible today**; would also need a local 8B model [EH-020: Sec. 1 p.2] |
| Gist Tokens | **Not reported** | **Apache-2.0** code; data partly CC BY-NC 4.0; LLaMA weight diffs need the base model [GT-057: Appendix B p.13; GT-058: GitHub README (WebFetch) web; GT-059: GitHub README (WebFetch) web] | **Not possible** with API targets [GT-008: Sec. 8 p.9] |
| AutoCompressor | **Not reported** | **None found** on the GitHub page (absence only) [AC-071: GitHub page (WebFetch) web] | **Not possible** with API targets [AC-005: Sec. 1 p.1] |
| 500xCompressor | **Not reported** | **CC BY 4.0** README; models and datasets "not open to the public" [XC-066: GitHub README (WebFetch) web; XC-067: GitHub README (WebFetch) web; XC-068: GitHub README (WebFetch) web] | **Not possible**: no released model [XC-067: GitHub README (WebFetch) web] |
| H2O | **Not reported** | **MIT** badge [H2-100: Abstract p.1; H2-101: GitHub repo page web] | **N/A at the gateway**: a change to the serving engine, not a prompt rewrite [H2-010: Appendix A System Details p.20] |
| SnapKV | **Not reported** | **Apache-2.0** [SK-091: GitHub repo page web] | **N/A at the gateway**: a source-level change to attention code [SK-010: Figure 6 caption p.7] |

**Reading across the matrix.** Only the text-in, text-out methods (LLMLingua v1, LongLLMLingua, LLMLingua-2, Selective Context, CPC, SCOPE, and EHPC with a local evaluator) can sit in front of a closed API. Of those, LLMLingua-2 is the only one that runs on CPU at a measured, modest cost, ships under a permissive licence, and is already integrated. CPC and LongLLMLingua, the two methods with the strongest question-aware results, need a GPU-hosted 7B model; SCOPE and EHPC have no released code. Gist, AutoCompressor, 500xCompressor, H2O and SnapKV cannot reduce an API bill at all, because they change what the serving model itself consumes or stores.

## 6. Local check results

**Everything in this section is LOCAL** (run on this machine, CPU only) unless a line carries a paper tag. Every table below is copied by script from `raw/results/results.md`, so each row can be traced to that file; the last column names the table. The local check covers the methods that run here: LLMLingua-2, LLMLingua v1 (with GPT-2), a Selective-Context-style filter, two controls, and two post-hoc LLMLingua-2 variants. Every other method stays "from paper" (section 6.10).

### 6.1 What was run

- **Same inputs, same target.** 40 test items for each of three families (QA over distractor paragraphs, lookups in structured logs and JSON records, lookups of constants in Python modules), each with one reference answer and an exact string to check, plus 50 synthetic case notes with nine sensitive fields each for a survival check that needs no model. Items use invented names and random hex or numeric identifiers, so the target cannot answer from memory. The same prompt goes to the same model, llama3.2:3b (Q4_K_M) through Ollama on an Intel Core i7-10610U with no GPU, at temperature 0 and with a unique nonce per request so that no prompt prefix is cached [local: raw/env.json]. Only the document is compressed; the instruction and the question are always sent verbatim.
- **Arms.** Uncompressed; LLMLingua-2 (the multilingual-BERT checkpoint) at about 2x and about 3x; LLMLingua v1 with plain GPT-2 as the scoring model; a Selective-Context-style filter (my re-implementation of the filtering step with GPT-2, word units); a random word-drop control; a question-aware TF-IDF block selector as a control. Two post-hoc arms were added after the main results were seen: LLMLingua-2 with `force_reserve_digit` at about 2x, and LLMLingua-2 at the gateway's literal `non_sensitive` setting (rate 0.6, digit protection).
- **Matched ratio.** Each arm's requested rate was calibrated on 30 development items so that the achieved ratio in cl100k tokens is about 2x (about 3x for the LLMLingua-2 3x arm). Achieved ratios differ by family and are printed next to every result; they are not identical, so a gap between two arms in a family can partly reflect a different ratio.
- **Metrics.** Accuracy is "the reference string appears in the normalised answer", with a Wilson 95% interval; differences from the baseline use a paired exact McNemar test; latency is end to end (compressor wall time plus model wall time) as p50 and p90 over items; compressor CPU time is the process CPU time of the compression call. Intervals and p-values are in the tables; the bootstrap intervals for differences and for latency percentiles are in `raw/results/results.md`.
- **Setup problem worth knowing.** `llmlingua` 0.2.2 raised `ValueError: too many values to unpack` in its v1 path on `transformers` 5.20.1, so the v1 arm and all other arms ran against a pinned `transformers` 4.46.3 overlay kept outside the gateway's virtual environment [local: raw/env.json]. LiteLLM 1.106.0 pins `huggingface-hub` and `tokenizers` versions that this overlay does not satisfy [local: raw/gateway_facts.txt], so running the v1 path inside the gateway needs dependency work.

### 6.2 Quality, ratio and latency by family

**QA over distractor paragraphs** (40 items)

| arm | answer-contains acc [95% Wilson] | Δ vs base [95% boot CI] | McNemar p | ctx ratio (cl100k) | prompt ratio (target tok) | e2e p50 s [CI] | e2e p90 s [CI] | compressor wall p50/p90 s | compressor CPU mean s | Source |
|---|---|---|---|---|---|---|---|---|---|---|
| uncompressed | 1.000 [0.912, 1.000] | - | - | 1.00x | 1.00x | 10.59 [10.03, 11.24] | 13.27 [11.97, 14.16] | 0.00/0.00 | 0.00 | [local: raw/results/results.md table A qa] |
| LLMLingua-2 (~2x) | 0.750 [0.598, 0.858] | -0.250 [-0.400, -0.125] | 0.002 | 2.37x | 1.81x | 7.22 [6.87, 7.69] | 8.47 [8.09, 10.19] | 0.89/1.37 | 3.38 | [local: raw/results/results.md table A qa] |
| LLMLingua-2 (~3x) | 0.625 [0.470, 0.758] | -0.375 [-0.525, -0.225] | <0.001 | 3.16x | 2.12x | 6.50 [6.32, 7.00] | 8.72 [7.37, 10.09] | 0.91/1.77 | 3.37 | [local: raw/results/results.md table A qa] |
| LLMLingua-2 + digit protection (~2x, post-hoc) | 0.725 [0.572, 0.839] | -0.275 [-0.425, -0.150] | 0.001 | 2.34x | 1.79x | 7.51 [7.28, 7.83] | 10.29 [8.35, 11.45] | 0.78/0.87 | 3.13 | [local: raw/results/results.md table A qa] |
| LLMLingua-2 at the gateway non_sensitive setting (rate 0.6 + digits, post-hoc) | 0.950 [0.835, 0.986] | -0.050 [-0.125, +0.000] | 0.500 | 1.67x | 1.45x | 8.51 [8.31, 9.02] | 9.63 [9.27, 11.21] | 0.83/1.24 | 2.92 | [local: raw/results/results.md table A qa] |
| LLMLingua v1/GPT-2 (~2x) | 0.250 [0.142, 0.402] | -0.750 [-0.875, -0.600] | <0.001 | 2.36x | 1.81x | 8.07 [7.56, 9.37] | 11.67 [9.87, 12.36] | 1.56/4.11 | 6.22 | [local: raw/results/results.md table A qa] |
| Selective-Context-style (2x) | 0.575 [0.422, 0.715] | -0.425 [-0.575, -0.275] | <0.001 | 1.86x | 1.56x | 7.91 [7.47, 8.20] | 9.79 [9.09, 10.66] | 0.72/1.23 | 2.75 | [local: raw/results/results.md table A qa] |
| random word drop (2x) | 0.300 [0.181, 0.454] | -0.700 [-0.825, -0.550] | <0.001 | 1.83x | 1.54x | 7.15 [6.87, 7.75] | 9.25 [7.99, 10.14] | 0.00/0.00 | 0.00 | [local: raw/results/results.md table A qa] |
| query-aware TF-IDF (2x) | 1.000 [0.912, 1.000] | +0.000 [+0.000, +0.000] | 1.000 | 1.90x | 1.58x | 6.89 [6.55, 7.70] | 9.23 [8.26, 10.64] | 0.00/0.01 | 0.01 | [local: raw/results/results.md table A qa] |

**Lookups in logs and JSON records** (40 items)

| arm | answer-contains acc [95% Wilson] | Δ vs base [95% boot CI] | McNemar p | ctx ratio (cl100k) | prompt ratio (target tok) | e2e p50 s [CI] | e2e p90 s [CI] | compressor wall p50/p90 s | compressor CPU mean s | Source |
|---|---|---|---|---|---|---|---|---|---|---|
| uncompressed | 1.000 [0.912, 1.000] | - | - | 1.00x | 1.00x | 16.13 [15.48, 16.93] | 20.76 [18.07, 23.65] | 0.00/0.00 | 0.00 | [local: raw/results/results.md table A logs] |
| LLMLingua-2 (~2x) | 0.300 [0.181, 0.454] | -0.700 [-0.825, -0.550] | <0.001 | 1.79x | 1.62x | 12.30 [11.84, 13.03] | 16.10 [14.17, 19.31] | 2.15/3.30 | 7.06 | [local: raw/results/results.md table A logs] |
| LLMLingua-2 (~3x) | 0.225 [0.123, 0.375] | -0.775 [-0.900, -0.650] | <0.001 | 2.53x | 2.08x | 10.33 [9.47, 11.46] | 13.45 [12.39, 15.14] | 2.08/3.61 | 6.88 | [local: raw/results/results.md table A logs] |
| LLMLingua-2 + digit protection (~2x, post-hoc) | 0.350 [0.221, 0.505] | -0.650 [-0.800, -0.500] | <0.001 | 1.71x | 1.56x | 12.53 [12.16, 13.48] | 16.43 [15.08, 17.51] | 1.72/3.03 | 6.53 | [local: raw/results/results.md table A logs] |
| LLMLingua-2 at the gateway non_sensitive setting (rate 0.6 + digits, post-hoc) | 0.425 [0.285, 0.578] | -0.575 [-0.725, -0.425] | <0.001 | 1.22x | 1.18x | 15.30 [14.49, 16.18] | 18.83 [17.15, 18.95] | 1.42/2.31 | 5.41 | [local: raw/results/results.md table A logs] |
| LLMLingua v1/GPT-2 (~2x) | 0.200 [0.105, 0.348] | -0.800 [-0.925, -0.675] | <0.001 | 2.43x | 2.03x | 13.59 [12.81, 14.43] | 17.20 [15.14, 24.57] | 4.85/8.54 | 14.93 | [local: raw/results/results.md table A logs] |
| Selective-Context-style (2x) | 0.750 [0.598, 0.858] | -0.250 [-0.400, -0.125] | 0.002 | 2.08x | 1.81x | 11.17 [10.61, 12.38] | 14.43 [13.50, 15.39] | 1.62/3.49 | 5.60 | [local: raw/results/results.md table A logs] |
| random word drop (2x) | 0.175 [0.087, 0.320] | -0.825 [-0.925, -0.700] | <0.001 | 1.86x | 1.66x | 9.98 [9.55, 10.64] | 13.17 [12.11, 14.59] | 0.00/0.00 | 0.00 | [local: raw/results/results.md table A logs] |
| query-aware TF-IDF (2x) | 0.950 [0.835, 0.986] | -0.050 [-0.125, +0.000] | 0.500 | 2.01x | 1.76x | 9.65 [9.07, 10.00] | 11.88 [11.07, 14.10] | 0.01/0.01 | 0.01 | [local: raw/results/results.md table A logs] |

**Lookups of constants in Python modules** (40 items)

| arm | answer-contains acc [95% Wilson] | Δ vs base [95% boot CI] | McNemar p | ctx ratio (cl100k) | prompt ratio (target tok) | e2e p50 s [CI] | e2e p90 s [CI] | compressor wall p50/p90 s | compressor CPU mean s | Source |
|---|---|---|---|---|---|---|---|---|---|---|
| uncompressed | 0.875 [0.739, 0.945] | - | - | 1.00x | 1.00x | 16.22 [14.74, 18.29] | 20.64 [19.41, 24.18] | 0.00/0.00 | 0.00 | [local: raw/results/results.md table A code] |
| LLMLingua-2 (~2x) | 0.550 [0.398, 0.693] | -0.325 [-0.475, -0.175] | 0.001 | 1.98x | 1.72x | 11.96 [11.34, 12.58] | 15.12 [13.99, 16.59] | 2.16/3.63 | 7.17 | [local: raw/results/results.md table A code] |
| LLMLingua-2 (~3x) | 0.450 [0.307, 0.602] | -0.425 [-0.575, -0.275] | <0.001 | 2.81x | 2.22x | 9.94 [9.52, 10.41] | 12.14 [10.90, 13.49] | 2.09/3.40 | 6.99 | [local: raw/results/results.md table A code] |
| LLMLingua-2 + digit protection (~2x, post-hoc) | 0.575 [0.422, 0.715] | -0.300 [-0.450, -0.150] | 0.002 | 1.98x | 1.72x | 10.77 [10.22, 11.94] | 14.92 [13.08, 16.31] | 1.58/1.76 | 6.27 | [local: raw/results/results.md table A code] |
| LLMLingua-2 at the gateway non_sensitive setting (rate 0.6 + digits, post-hoc) | 0.750 [0.598, 0.858] | -0.125 [-0.275, +0.025] | 0.180 | 1.32x | 1.26x | 14.78 [14.14, 15.53] | 16.83 [16.11, 17.77] | 1.74/2.34 | 6.46 | [local: raw/results/results.md table A code] |
| LLMLingua v1/GPT-2 (~2x) | 0.175 [0.087, 0.320] | -0.700 [-0.825, -0.550] | <0.001 | 1.73x | 1.56x | 18.27 [16.69, 19.81] | 24.93 [20.69, 29.60] | 6.76/14.32 | 21.52 | [local: raw/results/results.md table A code] |
| Selective-Context-style (2x) | 0.725 [0.572, 0.839] | -0.150 [-0.325, +0.025] | 0.146 | 2.14x | 1.83x | 11.84 [11.25, 12.66] | 14.43 [13.51, 15.30] | 2.43/4.56 | 7.79 | [local: raw/results/results.md table A code] |
| random word drop (2x) | 0.325 [0.201, 0.480] | -0.550 [-0.725, -0.350] | <0.001 | 1.98x | 1.73x | 9.35 [8.93, 9.69] | 12.82 [11.71, 14.28] | 0.00/0.00 | 0.00 | [local: raw/results/results.md table A code] |
| query-aware TF-IDF (2x) | 0.900 [0.769, 0.960] | +0.025 [-0.075, +0.125] | 1.000 | 2.08x | 1.80x | 9.05 [8.56, 9.68] | 12.53 [10.21, 13.71] | 0.01/0.01 | 0.02 | [local: raw/results/results.md table A code] |

**The two post-hoc LLMLingua-2 arms (added after the main results were seen).**

- **Digit protection (`force_reserve_digit`) at about 2x changed nothing measurable.** Accuracy was 0.725 on QA, 0.350 on logs and 0.575 on code, against 0.750, 0.300 and 0.550 for the same model without it at the same ratio; the pairs are not separable in any family or pooled (p 1.000, 0.688, 1.000 and 0.754) [local: raw/results/results.md table A and table F]. It kept the digits of national identifiers (1.00 instead of 0.94) but left every structural key as it was (table H, identical rows).
- **The gateway's literal `non_sensitive` setting (rate 0.6 with digit protection) compressed less and still lost accuracy where the text is structured.** Its achieved ratios were 1.67x on QA, 1.22x on logs and 1.32x on code (mean 1.40x). QA scored 0.950 (difference −0.050, p 0.500, two items of 40), code 0.750 (−0.125, p 0.180), and logs 0.425 (−0.575, p<0.001); pooled over 120 items 0.708 against 0.958 uncompressed (−0.250, p<0.001) [local: raw/results/results.md table A, table B and table G]. At 1.22x it still removed every one of the six log field names (0.00 of `svc=`, `req=`, `status=`, `latency_ms=`, `user=` and `region=`) [local: raw/results/results.md table H]. The milder setting spares prose and not structure.

### 6.3 Pooled over the three families

| arm | n | acc [95% Wilson] | Δ vs base [95% boot CI] | McNemar p | Source |
|---|---|---|---|---|---|
| uncompressed | 120 | 0.958 [0.906, 0.982] | - | - | [local: raw/results/results.md table B] |
| LLMLingua-2 (~2x) | 120 | 0.533 [0.444, 0.620] | -0.425 [-0.517, -0.333] | <0.001 | [local: raw/results/results.md table B] |
| LLMLingua-2 (~3x) | 120 | 0.433 [0.348, 0.523] | -0.525 [-0.617, -0.433] | <0.001 | [local: raw/results/results.md table B] |
| LLMLingua-2 + digit protection (~2x, post-hoc) | 120 | 0.550 [0.461, 0.636] | -0.408 [-0.500, -0.317] | <0.001 | [local: raw/results/results.md table B] |
| LLMLingua-2 at the gateway non_sensitive setting (rate 0.6 + digits, post-hoc) | 120 | 0.708 [0.622, 0.782] | -0.250 [-0.333, -0.167] | <0.001 | [local: raw/results/results.md table B] |
| LLMLingua v1/GPT-2 (~2x) | 120 | 0.208 [0.145, 0.289] | -0.750 [-0.825, -0.675] | <0.001 | [local: raw/results/results.md table B] |
| Selective-Context-style (2x) | 120 | 0.683 [0.596, 0.760] | -0.275 [-0.367, -0.183] | <0.001 | [local: raw/results/results.md table B] |
| random word drop (2x) | 120 | 0.267 [0.196, 0.352] | -0.692 [-0.775, -0.600] | <0.001 | [local: raw/results/results.md table B] |
| query-aware TF-IDF (2x) | 120 | 0.950 [0.895, 0.977] | -0.008 [-0.050, +0.033] | 1.000 | [local: raw/results/results.md table B] |

Pooled over 120 items, the question-aware control matched the baseline (accuracy 0.950 against 0.958, difference −0.008, p 1.000), while every token-level arm at about 2x or 3x lost between −0.275 (Selective-Context-style) and −0.750 (LLMLingua v1) [local: raw/results/results.md table B]. Pooling hides the family structure (section 2.8, test 2), so read the per-family tables first.

### 6.4 Where the evidence went

Retention of the answer and key strings in the compressed text (no model involved, all 40 items per family):

| family | arm | answer string verbatim | answer ws-insensitive | all key strings verbatim | n | Source |
|---|---|---|---|---|---|---|
| qa | LLMLingua-2 (~2x) | 0.78 [0.62, 0.88] | 0.90 | 0.78 | 40 | [local: raw/results/results.md table C] |
| qa | LLMLingua-2 (~3x) | 0.75 [0.60, 0.86] | 0.88 | 0.65 | 40 | [local: raw/results/results.md table C] |
| qa | LLMLingua-2 + digit protection (~2x, post-hoc) | 0.82 [0.68, 0.91] | 0.95 | 0.80 | 40 | [local: raw/results/results.md table C] |
| qa | LLMLingua-2 at the gateway non_sensitive setting (rate 0.6 + digits, post-hoc) | 0.88 [0.74, 0.95] | 1.00 | 0.88 | 40 | [local: raw/results/results.md table C] |
| qa | LLMLingua v1/GPT-2 (~2x) | 0.28 [0.16, 0.43] | 0.28 | 0.28 | 40 | [local: raw/results/results.md table C] |
| qa | Selective-Context-style (2x) | 0.93 [0.80, 0.97] | 0.93 | 0.93 | 40 | [local: raw/results/results.md table C] |
| qa | random word drop (2x) | 0.45 [0.31, 0.60] | 0.45 | 0.40 | 40 | [local: raw/results/results.md table C] |
| qa | query-aware TF-IDF (2x) | 1.00 [0.91, 1.00] | 1.00 | 1.00 | 40 | [local: raw/results/results.md table C] |
| logs | LLMLingua-2 (~2x) | 0.50 [0.35, 0.65] | 0.82 | 0.00 | 40 | [local: raw/results/results.md table C] |
| logs | LLMLingua-2 (~3x) | 0.50 [0.35, 0.65] | 0.78 | 0.00 | 40 | [local: raw/results/results.md table C] |
| logs | LLMLingua-2 + digit protection (~2x, post-hoc) | 0.50 [0.35, 0.65] | 0.78 | 0.00 | 40 | [local: raw/results/results.md table C] |
| logs | LLMLingua-2 at the gateway non_sensitive setting (rate 0.6 + digits, post-hoc) | 0.50 [0.35, 0.65] | 0.93 | 0.00 | 40 | [local: raw/results/results.md table C] |
| logs | LLMLingua v1/GPT-2 (~2x) | 0.50 [0.35, 0.65] | 0.50 | 0.15 | 40 | [local: raw/results/results.md table C] |
| logs | Selective-Context-style (2x) | 0.90 [0.77, 0.96] | 0.90 | 0.90 | 40 | [local: raw/results/results.md table C] |
| logs | random word drop (2x) | 0.70 [0.55, 0.82] | 0.70 | 0.25 | 40 | [local: raw/results/results.md table C] |
| logs | query-aware TF-IDF (2x) | 1.00 [0.91, 1.00] | 1.00 | 1.00 | 40 | [local: raw/results/results.md table C] |
| code | LLMLingua-2 (~2x) | 0.70 [0.55, 0.82] | 1.00 | 0.00 | 40 | [local: raw/results/results.md table C] |
| code | LLMLingua-2 (~3x) | 0.70 [0.55, 0.82] | 0.97 | 0.00 | 40 | [local: raw/results/results.md table C] |
| code | LLMLingua-2 + digit protection (~2x, post-hoc) | 0.70 [0.55, 0.82] | 1.00 | 0.00 | 40 | [local: raw/results/results.md table C] |
| code | LLMLingua-2 at the gateway non_sensitive setting (rate 0.6 + digits, post-hoc) | 0.70 [0.55, 0.82] | 1.00 | 0.00 | 40 | [local: raw/results/results.md table C] |
| code | LLMLingua v1/GPT-2 (~2x) | 0.40 [0.26, 0.55] | 0.40 | 0.05 | 40 | [local: raw/results/results.md table C] |
| code | Selective-Context-style (2x) | 1.00 [0.91, 1.00] | 1.00 | 1.00 | 40 | [local: raw/results/results.md table C] |
| code | random word drop (2x) | 0.62 [0.47, 0.76] | 0.62 | 0.60 | 40 | [local: raw/results/results.md table C] |
| code | query-aware TF-IDF (2x) | 1.00 [0.91, 1.00] | 1.00 | 1.00 | 40 | [local: raw/results/results.md table C] |

Share of the original's structural strings that survive verbatim:

| arm | `logs:svc=` | `logs:req=` | `logs:status=` | `logs:latency_ms=` | `logs:user=` | `logs:region=` | `code:def ` | `code:return` | `code:MAX_` | spurious ` _ ` per code file | Source |
|---|---|---|---|---|---|---|---|---|---|---|---|
| LLMLingua-2 (~2x) | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.16 | 0.43 | 0.00 | 27.1 | [local: raw/results/results.md table H] |
| LLMLingua-2 (~3x) | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.03 | 0.09 | 0.00 | 18.8 | [local: raw/results/results.md table H] |
| LLMLingua-2 + digit protection (~2x, post-hoc) | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.16 | 0.43 | 0.00 | 27.1 | [local: raw/results/results.md table H] |
| LLMLingua-2 at the gateway non_sensitive setting (rate 0.6 + digits, post-hoc) | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.49 | 0.91 | 0.00 | 45.6 | [local: raw/results/results.md table H] |
| LLMLingua v1/GPT-2 (~2x) | 0.08 | 0.10 | 0.07 | 0.16 | 0.17 | 0.12 | 0.13 | 0.36 | 0.06 | 0.0 | [local: raw/results/results.md table H] |
| Selective-Context-style (2x) | 0.53 | 1.00 | 0.10 | 0.53 | 1.00 | 0.24 | 0.03 | 0.78 | 0.52 | 0.0 | [local: raw/results/results.md table H] |
| random word drop (2x) | 0.56 | 0.49 | 0.55 | 0.59 | 0.57 | 0.56 | 0.58 | 0.53 | 0.56 | 0.0 | [local: raw/results/results.md table H] |
| query-aware TF-IDF (2x) | 0.50 | 0.50 | 0.50 | 0.50 | 0.50 | 0.50 | 0.46 | 0.46 | 0.55 | 0.0 | [local: raw/results/results.md table H] |

Wrong answers split into evidence lost in compression and evidence present but still misread:

| family | arm | wrong | evidence lost | evidence present | wrong where base was right | Source |
|---|---|---|---|---|---|---|
| qa | LLMLingua-2 (~2x) | 10 | 4 | 6 | 10 | [local: raw/results/results.md table E] |
| qa | LLMLingua-2 (~3x) | 15 | 5 | 10 | 15 | [local: raw/results/results.md table E] |
| qa | LLMLingua-2 + digit protection (~2x, post-hoc) | 11 | 2 | 9 | 11 | [local: raw/results/results.md table E] |
| qa | LLMLingua-2 at the gateway non_sensitive setting (rate 0.6 + digits, post-hoc) | 2 | 0 | 2 | 2 | [local: raw/results/results.md table E] |
| qa | LLMLingua v1/GPT-2 (~2x) | 30 | 29 | 1 | 30 | [local: raw/results/results.md table E] |
| qa | Selective-Context-style (2x) | 17 | 3 | 14 | 17 | [local: raw/results/results.md table E] |
| qa | random word drop (2x) | 28 | 22 | 6 | 28 | [local: raw/results/results.md table E] |
| qa | query-aware TF-IDF (2x) | 0 | 0 | 0 | 0 | [local: raw/results/results.md table E] |
| logs | LLMLingua-2 (~2x) | 28 | 7 | 21 | 28 | [local: raw/results/results.md table E] |
| logs | LLMLingua-2 (~3x) | 31 | 9 | 22 | 31 | [local: raw/results/results.md table E] |
| logs | LLMLingua-2 + digit protection (~2x, post-hoc) | 26 | 9 | 17 | 26 | [local: raw/results/results.md table E] |
| logs | LLMLingua-2 at the gateway non_sensitive setting (rate 0.6 + digits, post-hoc) | 23 | 3 | 20 | 23 | [local: raw/results/results.md table E] |
| logs | LLMLingua v1/GPT-2 (~2x) | 32 | 20 | 12 | 32 | [local: raw/results/results.md table E] |
| logs | Selective-Context-style (2x) | 10 | 4 | 6 | 10 | [local: raw/results/results.md table E] |
| logs | random word drop (2x) | 33 | 12 | 21 | 33 | [local: raw/results/results.md table E] |
| logs | query-aware TF-IDF (2x) | 2 | 0 | 2 | 2 | [local: raw/results/results.md table E] |
| code | LLMLingua-2 (~2x) | 18 | 0 | 18 | 14 | [local: raw/results/results.md table E] |
| code | LLMLingua-2 (~3x) | 22 | 1 | 21 | 17 | [local: raw/results/results.md table E] |
| code | LLMLingua-2 + digit protection (~2x, post-hoc) | 17 | 0 | 17 | 13 | [local: raw/results/results.md table E] |
| code | LLMLingua-2 at the gateway non_sensitive setting (rate 0.6 + digits, post-hoc) | 10 | 0 | 10 | 7 | [local: raw/results/results.md table E] |
| code | LLMLingua v1/GPT-2 (~2x) | 33 | 24 | 9 | 28 | [local: raw/results/results.md table E] |
| code | Selective-Context-style (2x) | 11 | 0 | 11 | 9 | [local: raw/results/results.md table E] |
| code | random word drop (2x) | 27 | 15 | 12 | 24 | [local: raw/results/results.md table E] |
| code | query-aware TF-IDF (2x) | 4 | 0 | 4 | 2 | [local: raw/results/results.md table E] |

Two different failure modes show up. **Evidence deleted:** LLMLingua v1 with GPT-2 and the random control lost the answer itself in most wrong answers (LLMLingua v1: 29 of 30 on QA, 20 of 32 on logs, 24 of 33 on code; random: 22 of 28, 12 of 33, 15 of 27) [local: raw/results/results.md table E]. **Evidence kept, context destroyed:** the Selective-Context-style filter retained the answer string in 0.93, 0.90 and 1.00 of QA, log and code items, yet lost 14 of 17, 6 of 10 and 11 of 11 wrong answers to misreading, not to deletion; LLMLingua-2 at 2x did the same on code (18 of 18 wrong answers with the answer still present once spaces are ignored) [local: raw/results/results.md table C and table E]. In structured text the loss is the key names: LLMLingua-2 at 2x kept none of the six log field names, and the Selective-Context-style filter kept `latency_ms=` in only 0.53 of the occurrences, although the log questions ask about exactly such a field [local: raw/results/results.md table H]. Retaining the answer string is therefore necessary but not sufficient.

### 6.5 Sensitive fields

| arm | ctx ratio | name | dob | address | email | phone | national_id | iban | diagnosis | case_ref | ALL_FIELDS_INTACT | Source |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| LLMLingua-2 (~2x) | 2.37x | 1.00 | 0.00 | 0.00 | 0.00 | 0.00 (ws 1.00) | 0.94 | 1.00 | 0.66 | 0.00 (ws 0.78) | 0.00 | [local: raw/results/results.md table D] |
| LLMLingua-2 (~3x) | 3.47x | 0.98 | 0.00 | 0.00 | 0.00 | 0.00 (ws 0.52) | 0.86 | 0.76 | 0.66 | 0.00 | 0.00 | [local: raw/results/results.md table D] |
| LLMLingua-2 + digit protection (~2x, post-hoc) | 2.32x | 1.00 | 0.00 | 0.00 | 0.00 | 0.00 (ws 1.00) | 1.00 | 1.00 | 0.66 | 0.00 (ws 0.52) | 0.00 | [local: raw/results/results.md table D] |
| LLMLingua-2 at the gateway non_sensitive setting (rate 0.6 + digits, post-hoc) | 1.61x | 1.00 | 0.00 (ws 1.00) | 0.00 | 0.00 (ws 0.04) | 0.00 (ws 1.00) | 1.00 | 1.00 | 0.66 | 0.00 (ws 1.00) | 0.00 | [local: raw/results/results.md table D] |
| LLMLingua v1/GPT-2 (~2x) | 1.73x | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.04 | 0.84 | 0.00 | 0.00 | [local: raw/results/results.md table D] |
| Selective-Context-style (2x) | 1.63x | 1.00 | 1.00 | 0.40 | 1.00 | 1.00 | 0.96 | 1.00 | 0.52 | 1.00 | 0.18 | [local: raw/results/results.md table D] |
| random word drop (2x) | 1.82x | 0.30 | 0.58 | 0.12 | 0.52 | 0.20 | 0.14 | 0.42 | 0.40 | 0.52 | 0.00 | [local: raw/results/results.md table D] |

No arm kept all nine fields in more than 0.18 of records, including both post-hoc variants (0.00). LLMLingua-2 at 2x kept names (1.00), IBANs (1.00) and national identifiers (0.94) but none of the dates of birth, addresses, e-mail addresses, phone numbers or case references verbatim; phone numbers were present once spaces are ignored (1.00 with spaces ignored), so the damage is partly formatting and partly deletion (an e-mail address cut to its local part, a date of birth reduced to "14 1984"; digit protection restored "04" but not the slashes) [local: raw/results/results.md table D; raw/results/examples.txt]. At the gateway's literal setting (1.61x) dates of birth, phone numbers and case references survive once spaces are ignored (1.00 each), e-mail addresses do not (0.04), and still no record is intact verbatim. The Selective-Context-style filter was the best at 0.18 and its weak fields were addresses (0.40) and diagnoses (0.52). Two cautions: survival is not redaction, because LLMLingua-2 leaves names and IBANs in place; and the metric is verbatim survival, not whether a downstream task still works.

### 6.6 The structured family by record type

| arm | log lines (n=20) | JSON records (n=20) | Source |
|---|---|---|---|
| uncompressed | 1.00 [0.84, 1.00] | 1.00 [0.84, 1.00] | [local: raw/results/results.md table I] |
| LLMLingua-2 (~2x) | 0.20 [0.08, 0.42] | 0.40 [0.22, 0.61] | [local: raw/results/results.md table I] |
| LLMLingua-2 (~3x) | 0.10 [0.03, 0.30] | 0.35 [0.18, 0.57] | [local: raw/results/results.md table I] |
| LLMLingua-2 + digit protection (~2x, post-hoc) | 0.25 [0.11, 0.47] | 0.45 [0.26, 0.66] | [local: raw/results/results.md table I] |
| LLMLingua-2 at the gateway non_sensitive setting (rate 0.6 + digits, post-hoc) | 0.30 [0.15, 0.52] | 0.55 [0.34, 0.74] | [local: raw/results/results.md table I] |
| LLMLingua v1/GPT-2 (~2x) | 0.20 [0.08, 0.42] | 0.20 [0.08, 0.42] | [local: raw/results/results.md table I] |
| Selective-Context-style (2x) | 0.55 [0.34, 0.74] | 0.95 [0.76, 0.99] | [local: raw/results/results.md table I] |
| random word drop (2x) | 0.15 [0.05, 0.36] | 0.20 [0.08, 0.42] | [local: raw/results/results.md table I] |
| query-aware TF-IDF (2x) | 0.95 [0.76, 0.99] | 0.95 [0.76, 0.99] | [local: raw/results/results.md table I] |

### 6.7 Pairs the sample cannot separate

Exact McNemar p at or above 0.05; no correction for the number of comparisons (section 8.2). A pair that is not listed was separable, and a pair that is listed is not shown to be equal.

| family | A | B | A-only right | B-only right | acc diff A-B | p | Source |
|---|---|---|---|---|---|---|---|
| qa | LLMLingua-2 (~2x) | LLMLingua-2 (~3x) | 6 | 1 | +0.125 | 0.125 | [local: raw/results/results.md table F] |
| qa | LLMLingua-2 (~2x) | LLMLingua-2 + digit protection (~2x, post-hoc) | 2 | 1 | +0.025 | 1.000 | [local: raw/results/results.md table F] |
| qa | LLMLingua-2 (~2x) | Selective-Context-style (2x) | 11 | 4 | +0.175 | 0.118 | [local: raw/results/results.md table F] |
| qa | LLMLingua-2 (~3x) | LLMLingua-2 + digit protection (~2x, post-hoc) | 1 | 5 | -0.100 | 0.219 | [local: raw/results/results.md table F] |
| qa | LLMLingua-2 (~3x) | Selective-Context-style (2x) | 10 | 8 | +0.050 | 0.815 | [local: raw/results/results.md table F] |
| qa | LLMLingua-2 + digit protection (~2x, post-hoc) | Selective-Context-style (2x) | 10 | 4 | +0.150 | 0.180 | [local: raw/results/results.md table F] |
| qa | LLMLingua-2 at the gateway non_sensitive setting (rate 0.6 + digits, post-hoc) | query-aware TF-IDF (2x) | 0 | 2 | -0.050 | 0.500 | [local: raw/results/results.md table F] |
| qa | LLMLingua v1/GPT-2 (~2x) | random word drop (2x) | 7 | 9 | -0.050 | 0.804 | [local: raw/results/results.md table F] |
| logs | LLMLingua-2 (~2x) | LLMLingua-2 (~3x) | 5 | 2 | +0.075 | 0.453 | [local: raw/results/results.md table F] |
| logs | LLMLingua-2 (~2x) | LLMLingua-2 + digit protection (~2x, post-hoc) | 2 | 4 | -0.050 | 0.688 | [local: raw/results/results.md table F] |
| logs | LLMLingua-2 (~2x) | LLMLingua-2 at the gateway non_sensitive setting (rate 0.6 + digits, post-hoc) | 0 | 5 | -0.125 | 0.062 | [local: raw/results/results.md table F] |
| logs | LLMLingua-2 (~2x) | LLMLingua v1/GPT-2 (~2x) | 8 | 4 | +0.100 | 0.388 | [local: raw/results/results.md table F] |
| logs | LLMLingua-2 (~2x) | random word drop (2x) | 10 | 5 | +0.125 | 0.302 | [local: raw/results/results.md table F] |
| logs | LLMLingua-2 (~3x) | LLMLingua-2 + digit protection (~2x, post-hoc) | 1 | 6 | -0.125 | 0.125 | [local: raw/results/results.md table F] |
| logs | LLMLingua-2 (~3x) | LLMLingua v1/GPT-2 (~2x) | 6 | 5 | +0.025 | 1.000 | [local: raw/results/results.md table F] |
| logs | LLMLingua-2 (~3x) | random word drop (2x) | 7 | 5 | +0.050 | 0.774 | [local: raw/results/results.md table F] |
| logs | LLMLingua-2 + digit protection (~2x, post-hoc) | LLMLingua-2 at the gateway non_sensitive setting (rate 0.6 + digits, post-hoc) | 1 | 4 | -0.075 | 0.375 | [local: raw/results/results.md table F] |
| logs | LLMLingua-2 + digit protection (~2x, post-hoc) | LLMLingua v1/GPT-2 (~2x) | 11 | 5 | +0.150 | 0.210 | [local: raw/results/results.md table F] |
| logs | LLMLingua-2 + digit protection (~2x, post-hoc) | random word drop (2x) | 11 | 4 | +0.175 | 0.118 | [local: raw/results/results.md table F] |
| logs | LLMLingua v1/GPT-2 (~2x) | random word drop (2x) | 8 | 7 | +0.025 | 1.000 | [local: raw/results/results.md table F] |
| code | LLMLingua-2 (~2x) | LLMLingua-2 (~3x) | 5 | 1 | +0.100 | 0.219 | [local: raw/results/results.md table F] |
| code | LLMLingua-2 (~2x) | LLMLingua-2 + digit protection (~2x, post-hoc) | 0 | 1 | -0.025 | 1.000 | [local: raw/results/results.md table F] |
| code | LLMLingua-2 (~2x) | random word drop (2x) | 17 | 8 | +0.225 | 0.108 | [local: raw/results/results.md table F] |
| code | LLMLingua-2 (~3x) | LLMLingua-2 + digit protection (~2x, post-hoc) | 0 | 5 | -0.125 | 0.062 | [local: raw/results/results.md table F] |
| code | LLMLingua-2 (~3x) | random word drop (2x) | 15 | 10 | +0.125 | 0.424 | [local: raw/results/results.md table F] |
| code | LLMLingua-2 + digit protection (~2x, post-hoc) | Selective-Context-style (2x) | 1 | 7 | -0.150 | 0.070 | [local: raw/results/results.md table F] |
| code | LLMLingua-2 + digit protection (~2x, post-hoc) | random word drop (2x) | 18 | 8 | +0.250 | 0.076 | [local: raw/results/results.md table F] |
| code | LLMLingua-2 at the gateway non_sensitive setting (rate 0.6 + digits, post-hoc) | Selective-Context-style (2x) | 4 | 3 | +0.025 | 1.000 | [local: raw/results/results.md table F] |
| code | LLMLingua-2 at the gateway non_sensitive setting (rate 0.6 + digits, post-hoc) | query-aware TF-IDF (2x) | 2 | 8 | -0.150 | 0.109 | [local: raw/results/results.md table F] |
| code | LLMLingua v1/GPT-2 (~2x) | random word drop (2x) | 6 | 12 | -0.150 | 0.238 | [local: raw/results/results.md table F] |
| code | Selective-Context-style (2x) | query-aware TF-IDF (2x) | 3 | 10 | -0.175 | 0.092 | [local: raw/results/results.md table F] |
| pooled | LLMLingua-2 (~2x) | LLMLingua-2 + digit protection (~2x, post-hoc) | 4 | 6 | -0.017 | 0.754 | [local: raw/results/results.md table F] |
| pooled | LLMLingua-2 at the gateway non_sensitive setting (rate 0.6 + digits, post-hoc) | Selective-Context-style (2x) | 23 | 20 | +0.025 | 0.761 | [local: raw/results/results.md table F] |
| pooled | LLMLingua v1/GPT-2 (~2x) | random word drop (2x) | 21 | 28 | -0.058 | 0.392 | [local: raw/results/results.md table F] |

The sample cannot tell LLMLingua v1 with GPT-2 from random word dropping in any family or pooled; it cannot tell LLMLingua-2 at 2x from 3x in any family (QA p 0.125, logs p 0.453, code p 0.219), so the extra loss from 2x to 3x is not resolved at n=40; and on code it cannot separate the Selective-Context-style filter from the question-aware control (p 0.092) even though the point estimates differ by 0.175 [local: raw/results/results.md table F]. These are statements about what 40 items can resolve, not findings of equality.

### 6.8 Local versus paper

| Claim | From paper | Local | Verdict |
|---|---|---|---|
| Question-aware selection beats question-agnostic on QA | NaturalQuestions with 20 documents at about 4x: LLMLingua-2 scores 39.9 to 48.6, LongLLMLingua 71.2 to 75.0 [L2-059: Table 11 p.18; LongLL-CL-4: Table 1 p.7] | LLMLingua-2 at 2x scores 0.750; the question-aware control 1.000 [local: raw/results/results.md table A qa] | Agree in direction. The control is a lexical best case, so the local size means little |
| Token-level pruning corrupts exact strings | "209" for "2019" until subsequence recovery [LongLL-LIM-3: Sec. 4.4 p.5; LongLL-LIM-4: Figure 7 p.18] | LLMLingua-2 at 2x keeps every key string in 0.00 of log items and 0.00 of code items [local: raw/results/results.md table C] | Agree |
| Compression does not always save time | Selective Context 15.5 to 15.9 s against 14.9 s uncompressed end to end [SC-T07: Table 5 p.8; SC-T08: Appendix I p.14; SC-T09: Sec. 5 Baselines p.7; L2-070: Table 5 p.8] | LLMLingua v1 with GPT-2: 18.27 s against 16.22 s at the median on code items [local: raw/results/results.md table A code] | Agree |
| Compression holds or improves a code score | LongBench Code column: LLMLingua-2 58.9 at 5x against 54.2 [L2-034: Table 2 p.7; L2-043: Table 2 p.7] | Lookups of constants in code: LLMLingua-2 loses −0.325 at 1.98x [local: raw/results/results.md table A code] | Disagree. Different tasks (completion against exact lookup); neither generalises to the other |
| LLMLingua v1 keeps quality at high ratios | GSM8K 79.08 at 5x against 78.85 [LLv1-CL-2: Table 2 p.6; LLv1-CL-1: Table 2 p.6] | The GPT-2 variant at about 2x cannot be separated from random word dropping [local: raw/results/results.md table F] | Not comparable: a weaker scorer, different tasks. No conclusion about published LLMLingua |
| Selective Context is a weak baseline | Third-party run: MeetingBank EM 66.28 at 2.5x against 87.75 [SC-T01: Table 1 p.6; L2-042: Table 1 p.6] | The word-level re-implementation is the best token-level arm on logs and code [local: raw/results/results.md table A] | Not comparable: different implementation (word units, GPT-2) and tasks |
| LLMLingua-2 is reusable for any later question | Compress once, use for any query [L2-009: Abstract p.1] | The same compressed text loses 0.250 of QA accuracy at 2x, where the control that sees the question loses none [local: raw/results/results.md table A qa] | The convenience has a price whenever the evidence depends on the question |

### 6.9 Latency and compressor cost

| arm | compressor wall, ms per input token | compressor CPU-s per 1k input tokens | mean ratio | break-even target prefill, ms/token | Source |
|---|---|---|---|---|---|
| LLMLingua-2 (~2x) | 4.67 | 14.22 | 2.05x | 9.1 | [local: raw/results/results.md table G] |
| LLMLingua-2 (~3x) | 4.70 | 13.94 | 2.83x | 7.3 | [local: raw/results/results.md table G] |
| LLMLingua-2 + digit protection (~2x, post-hoc) | 3.63 | 12.88 | 2.01x | 7.2 | [local: raw/results/results.md table G] |
| LLMLingua-2 at the gateway non_sensitive setting (rate 0.6 + digits, post-hoc) | 3.50 | 11.96 | 1.40x | 12.2 | [local: raw/results/results.md table G] |
| LLMLingua v1/GPT-2 (~2x) | 13.25 | 34.48 | 2.18x | 24.4 | [local: raw/results/results.md table G] |
| Selective-Context-style (2x) | 4.62 | 13.04 | 2.03x | 9.1 | [local: raw/results/results.md table G] |
| random word drop (2x) | 0.00 | 0.00 | 1.89x | none (compressor cost about 0) | [local: raw/results/results.md table G] |
| query-aware TF-IDF (2x) | 0.01 | 0.04 | 2.01x | none (compressor cost about 0) | [local: raw/results/results.md table G] |

- **What the target costs here.** Prefill takes a median 23.6 ms per prompt token and decoding 73.2 ms per token on this CPU [local: raw/results/results.md table G]. A 2x cut therefore saves seconds: LLMLingua-2 at 2x lowered the end-to-end median from 10.59 s to 7.22 s on QA, from 16.13 s to 12.30 s on logs and from 16.22 s to 11.96 s on code, compressor time included [local: raw/results/results.md table A].
- **What the compressor costs.** LLMLingua-2 at 2x needs 4.67 ms of wall time and 14.22 CPU-seconds per 1k input tokens, about three times the wall time because four threads are busy (derived); the Selective-Context-style filter 4.62 ms and 13.04 CPU-seconds; LLMLingua v1 with GPT-2 13.25 ms and 34.48 CPU-seconds; the two controls cost nothing measurable [local: raw/results/results.md table G]. Its p90 compressor wall time on code was 14.32 s, above the gateway's 10 s timeout (section 7.4) [local: raw/results/results.md table A code].
- **Break-even.** Compression saves wall time only if the target's own prefill is slower than the break-even column of the table: 9.1 ms per token for LLMLingua-2 at 2x and 24.4 for LLMLingua v1 against a local target at 23.6, which is why v1 was a net loss on code and LLMLingua-2 a gain [local: raw/results/results.md table G]. For a target that prefills faster than 9.1 ms per token, a CPU-hosted LLMLingua-2 call would add latency instead of removing it (derived). The prefill speed of a hosted API was not measured here (not reported), so the latency case for a hosted target is open and only the token-cost case remains.
- **Latency is not quality.** The faster arms are mostly the ones that lost accuracy; speed and accuracy have to be read together in table A.

| family | items | identical responses | same right/wrong verdict | LLM wall p50, main run s | LLM wall p50, repeat s | repeat / main | Source |
|---|---|---|---|---|---|---|---|
| qa | 40 | 40 | 40 | 10.59 | 10.77 | 1.02x | [local: raw/results/results.md table J] |
| logs | 40 | 39 | 39 | 16.13 | 15.99 | 0.99x | [local: raw/results/results.md table J] |
| code | 40 | 38 | 39 | 16.22 | 15.54 | 0.96x | [local: raw/results/results.md table J] |

In the later session the same 120 uncompressed prompts, with fresh nonces, gave identical answers for 117 items (40, 39 and 38 per family) and the same right or wrong verdict for 118 (40, 39 and 39) (derived totals) [local: raw/results/results.md table J]. So the target is not perfectly repeatable at temperature 0, and a difference of one or two items between two arms is within run-to-run noise. The median model wall time was within 4% of the main run (1.02x, 0.99x and 0.96x), so the later sessions are comparable on model latency. Compressor timing is less stable: the same LLMLingua-2 model cost 4.67 ms of wall time per input token in the main pass and 3.63 and 3.50 ms in the two later sessions, about a quarter less (derived from table G), so compressor timings are indicative, not exact.

### 6.10 Methods not run locally (they stay "from paper")

- **LongLLMLingua** and **CPC**: need a 7B scoring or encoder model, which this CPU-only machine cannot serve at a useful speed; their numbers are in sections 3 to 5.
- **SCOPE** and **EHPC**: no released code at the time of checking (2026-11-05) [SCP-74: README web; EH-120: Appendix B p.14].
- **Gist Tokens**, **AutoCompressor**, **500xCompressor**: need fine-tuned or white-box models and change what the serving model consumes [GT-005: Sec. 3 p.3; AC-004: Sec. 1 p.1; XC-004: Sec. 2.1 p.2].
- **H2O** and **SnapKV**: operate inside the serving engine's KV cache and save no prompt tokens [H2-080: Appendix A p.20; SK-070: Sec. 6 p.12].
- **LLMLingua v1 as published** (instruction-aligned small LM or LLaMA-scale scorer): the local arm uses plain GPT-2 and is a weaker variant [LLv1-MECH-6: Sec. 4.3 p.5].
- **Selective Context as published**: the local arm is a word-level re-implementation, not the authors' code.

## 7. Recommendations for our pipeline

### 7.1 Decision rule

Route on **what the prompt contains and what it will be used for** first, on sensitivity second, and only then choose a method and a ratio cap. The gateway today routes only on the second step: a zero-shot classifier labels each message `sensitive`, `critical`, `non_sensitive` or `less_important`; the first two are never compressed, `non_sensitive` goes to LLMLingua-2 at rate 0.6 with digit protection, and `less_important` at rate 0.3 [local: raw/gateway_facts.txt]. That is not enough, because the label says nothing about whether the text will be read for exact strings. In the local check, LLMLingua-2 at about 2x lost 0.250 of the QA accuracy, 0.700 of the log accuracy and 0.325 of the code accuracy, whatever an importance label would have said about those documents; the `non_sensitive` setting itself (rate 0.6, digit protection) lost 0.050, 0.575 and 0.125 at 1.67x, 1.22x and 1.32x [local: raw/results/results.md table A].

The rate in the gateway is the fraction of tokens kept, not a ratio. On the local development items rate 0.6 reached 1.35x, rate 0.33 reached 2.39x and rate 0.28 reached 2.78x, so the gateway's 0.3 sits between the 2.39x of rate 0.33 and the 2.78x of rate 0.28 on this kind of text, and the ratio depends on the text type (QA 1.68x, logs 1.24x at rate 0.6) [local: raw/results/calibration_summary.txt].

### 7.2 Routing per request category

| Request category | What to do | Method and setting | Ratio cap | Basis |
|---|---|---|---|---|
| Sensitive or regulated content (personal data, health, finance, credentials) | Never compress. Redact upstream if policy requires it. Compression does not remove data and does not keep it intact. | none | 1x | local table D; no paper tested it (section 4.7) |
| Source code, diffs, stack traces, configuration, shell commands | Never compress at token level. If the prompt is too long, drop whole files or functions by relevance to the request. | none; block-level selection as a fallback | 1x token level | local table A code and table H; papers conflict (section 4.1) |
| JSON, tables, logs, CSV, key=value text, id-heavy text | Never compress at token level. Select the relevant records or aggregate upstream. | record-level selection only when the question names the record | 1x token level; about 2x record level | local tables A logs, H and I; no paper tested it (section 4.5) |
| Text whose exact wording matters: numbers, dates, identifiers, quotations, contract clauses, tool-call arguments and outputs | Keep verbatim. | none | 1x | local; LongLLMLingua's "209" for "2019" [LongLL-LIM-3: Sec. 4.4 p.5; LongLL-LIM-4: Figure 7 p.18]; SnapKV's phone-number failure [SK-006: Sec. 4.3 p.6] |
| Multi-turn chat history | Keep the recent turns verbatim; when space runs out drop the oldest whole turns. No token pruning of turns. | none | 1x | no source measured a chat task (section 4.3) |
| Question over long documents or retrieved passages (RAG) | Compress with the question in view, or drop whole passages by relevance. With a GPU: CPC (Apache-2.0, 0.15 s median [CPC-34: Table 5 p.7; CPC-35: Table 5 p.7; CPC-53: LICENSE web]) or LongLLMLingua (MIT, 7B scorer, slower). CPU only: passage dropping as the local control did; LLMLingua-2 only if the text must be compressed without the question, at 3x or less. | question-aware, or LLMLingua-2 | 4x to 5x question-aware; 3x question-agnostic | papers (section 4.2); local control is a lexical best case |
| Summarizing long narrative text (transcripts, reports, articles) | LLMLingua-2 with digit protection; check n-gram fidelity on your own data, not only ROUGE-1. | LLMLingua-2 | 3x | papers (section 4.4); not run locally |
| Few-shot reasoning prompts | Drop demonstrations first; then LLMLingua-2 up to 14x on GSM8K-style demonstrations, 3x on BBH-style. | demonstration selection, then LLMLingua-2 | 14x GSM8K-style, 3x BBH-style | papers (section 4.6); not run locally |
| Anything else, or a task type the router cannot name | Do not compress (fail safe). The classifier already returns `critical` when it is unsure [local: raw/gateway_facts.txt]. | none | 1x | rule of this report |

### 7.3 What to keep uncompressed, always

1. The system prompt and the user's current question or instruction. The local check never compressed them, and the LLMLingua paper compresses them only lightly [LLv1-Q-1: Sec. 5.1 Implementation Details p.5]. The environment variable `PROMPT_COMPRESSION_PRESERVE_LAST_USER` is `false` by default [local: raw/gateway_facts.txt]; set it to `true`.
2. Code, configuration and anything inside a code fence.
3. Numbers, dates, identifiers, URLs, e-mail addresses, quotations and anything with `key=value` or JSON structure.
4. Tool-call arguments and tool results.
5. Sensitive or regulated content, and any message the classifier is unsure about.

### 7.4 Settings and costs to check in the gateway

- **Add a content-type guard before the compressor.** Detect code fences, JSON or log structure, tables, `key=value` density and digit or identifier density, and send those to "do not compress". The classifier's labels do not do this.
- **Digit protection is cheap but it is not protection.** The gateway sets it only for `non_sensitive`; `less_important` does not [local: raw/gateway_facts.txt]. Locally it changed accuracy by no separable amount (section 6.2) and kept national identifiers (1.00 against 0.94) while leaving every field name, date format and e-mail address as damaged as before. Keep it on if you like, and do not count on it for exact-string work.
- **Latency is not the reason to compress on a fast target.** On this CPU, LLMLingua-2 saves wall time only if the target's own prefill is slower than 9.1 ms per prompt token, and the local target takes 23.6 ms per token (derived from table G in section 6.9). A hosted API's prefill speed was not measured here; if it is faster than the break-even, a CPU-hosted LLMLingua-2 call adds latency and the only gain is the token bill. Treat the benefit as cost until measured.
- **The classifier is the larger fixed cost.** The earlier local pipeline run found that the classifier costs 3.21 ms per token on every request and reaches the 10 s budget at about 3,095 tokens, so the practical compression window is about 50 to 3,100 tokens [local: raw/pipeline_proof_facts.txt].
- **Respect the timeout.** The compressor call has a 10 s budget. LLMLingua v1 with GPT-2 took a p90 of 14.32 s on code items here, so it would time out and fall open to the uncompressed prompt [local: raw/gateway_facts.txt; raw/results/results.md table A code]. Do not swap it in.
- **Keep the per-request opt-out.** Requests can already switch compression off with `prompt_compression: false` in the metadata [local: raw/gateway_facts.txt].

### 7.5 Before enabling any route

Evaluate the route on your own prompts with the harness in `scripts/` (Appendix A): 30 to 50 items with reference answers or exact-match checks, the same inputs and target model with and without compression, accuracy with an interval, and the compressor's CPU time. Accept a route only if the interval for the loss excludes more than 2 points; with 40 items it cannot do that unless the loss is zero or the sample is larger, so use more items for the routes that matter. Run it in shadow first (compress, log the saving and the answer agreement, send the original) before it changes what the model sees.

### 7.6 What would change these recommendations

A GPU host (CPC and LongLLMLingua become available), a hosted target with fast prefill (latency argument disappears), real traffic in which questions share little vocabulary with their evidence (the local control's advantage shrinks), and a sample large enough to resolve 2 points: about 590 paired items if 3% of items differ between the compressed and uncompressed runs, and about 1,180 if 6% differ (normal approximation for a paired comparison, 80% power, 5% two-sided level; derived, not simulated here).

## 8. Limitations

### 8.1 What the sources did not cover

- **Repo integrity.** Six of the twelve PDFs in `papers/` are unrelated to compression and three more are different papers under a compression paper's name (section 3.0). The report therefore rests on ten papers fetched from arXiv with the user's approval, plus three real repo papers. Facts about licences and code release (25 lines, marked "web" in the evidence index) come from fetching official GitHub and Hugging Face pages on 2026-11-05; they are summaries, not script-verified quotes.
- **No paper tests the workloads that matter most here.** Structured data (JSON, tables, logs), multi-turn chat with a task metric, and PII or other regulated content have no direct test in any of the twelve papers (section 4). Coding is covered only by a LongBench "Code" column whose contents the LLMLingua-2 paper does not describe [L2-112: Table 2 header p.7].
- **Different targets and benchmarks.** Numbers come from GPT-3.5-Turbo, GPT-4o-mini, Mistral-7B, LLaMA and OPT variants, on different benchmarks, at ratios measured in words or tokens. Cross-paper comparisons are indicative only. CPC and EHPC do not name the target LLM behind their main tables [CPC-47: Sec. 4.3 p.5; EH-026: Sec. 5.1 p.8].
- **Copied baseline rows.** Tables in the LLMLingua-2 and CPC papers reuse rows from the LongLLMLingua paper; the dagger markers that say which rows were re-run were lost in text extraction, so some comparisons may mix runs [L2-043: Table 2 p.7; L2-044: Table 2 p.7].
- **Figures with no numbers.** The rate-distortion paper's results, H2O's summarization results and AutoCompressor's re-ranking results are plots only; no value was read from them [RD-18: Figure 1 caption p.4; H2-038: Sec. 5.1 Main Results p.8; AC-064: Figure 4 caption p.9].
- **Extraction method.** Ten papers were read by five extraction agents; every quoted number was machine-checked as a verbatim substring of its stated page (section 6 and Appendix A), and I re-read the quotes behind the interpretive claims used most (21.4 vs 17.1 points, 10.93x, 62-73%, EHPC average). Derived arithmetic is marked "(derived)". The agents' wider interpretive statements that I did not re-check are not used as evidence.

### 8.2 What the local check could not establish

- **Synthetic, templated data.** Items use invented names, random hex ids and random identifiers so that the target cannot answer from memory and every answer is an exact string. This makes them harder on exact strings and more regular in prose than real documents, so absolute accuracies are not comparable to any paper's numbers; only the within-run comparison between arms is meaningful.
- **One small target model on CPU.** llama3.2:3b (Q4_K_M) through Ollama, temperature 0, one run per item and arm. Latency percentiles are across items, so they mix length variation with machine noise; no per-item repeats were made. A GPU or a hosted API changes the latency picture completely (section 6.9).
- **Sample size.** 40 items per family (50 PII records). With 40 paired items, an exact McNemar test at p<0.05 needs a difference of at least 15 points (6 discordant items all in one direction) and typically 20-25 points (derived by enumeration, 8 to 20 discordant items); section 6 states which pairs the data cannot separate.
- **Methods run locally are close variants, not the reference systems.** LLMLingua-2 is the multilingual-BERT checkpoint, not the xlm-roberta-large model [L2-004: Appendix H p.14; L2-005: Appendix H p.14]. LLMLingua v1 used plain GPT-2 small without the paper's instruction-tuned alignment (the paper's own no-alignment ablation costs 0.56 EM points on GSM8K) [LLv1-ABL-8: Sec. 5.4 p.7] and ran on an overlaid transformers 4.46.3 because llmlingua 0.2.2 crashes on 5.20.1. The Selective-Context-style filter is my re-implementation of the filtering step: word units instead of spaCy noun phrases, GPT-2 instead of LLaMA-7B. The query-aware arm is a TF-IDF block selector used as a control; it is not CPC, which needs a trained 7B encoder.
- **Mostly default settings.** The main LLMLingua-2 arms were run with defaults. Two post-hoc arms test the `force_reserve_digit` option that the gateway's `non_sensitive` route sets (below). The documented `force_tokens` option, which could protect separators or key names, was not tested; the gateway's own `code` and `sensitive` presets in the Streamlit demo force only keywords such as `def` and `password` [local: raw/gateway_facts.txt]. Tuned settings may do better on structured text.
- **The question is outside the compressor in every arm.** Only the document is compressed; the instruction and the question are sent verbatim. That is the best case for a compressor: the LLMLingua paper compresses instruction and question lightly rather than not at all [LLv1-Q-1: Sec. 5.1 Implementation Details p.5].
- **Lenient answer metric.** An item is correct if the reference string appears in the normalised answer. A boundary-aware match credits at most 2 items fewer in any family and arm (the post-hoc rate-0.6 arm on QA, 0.950 against 0.900), and the 3B model answers in a few characters, so hedging is not a visible problem [local: raw/results/metric_check.txt]. Strict exact match is lower for QA (the model answers in a sentence) and is stored in `raw/results/results.json`.
- **Many pairwise tests, no correction.** Section 6.7 lists pairs by exact McNemar p-values at 0.05 without adjusting for the number of comparisons; a pair marked separable is a weaker claim than it looks, and a pair marked not separable is not evidence of equality.
- **Run-to-run noise.** Repeating the uncompressed baseline gave different answers for 3 of 120 items at temperature 0 and a different right or wrong verdict for 2 [local: raw/results/results.md table J]. Compressor wall time per token for the same LLMLingua-2 model was about a quarter lower in the two later sessions than in the main pass (section 6.9), so compressor timings are indicative only.
- **Prefix caching is defeated on purpose.** Every request carries a unique nonce so that Ollama cannot reuse a cached prefix. A hosted API that caches prompts would show smaller savings from compression, and none of this is measured here.
- **Ratios are matched on pooled dev data, not per family.** Each arm's requested rate was calibrated so that the pooled dev set reached about 2x; per-family achieved ratios differ by a few tenths, and are printed next to every result.
- **Methods not run locally.** Gist, AutoCompressor, 500xCompressor, H2O, SnapKV (need model internals and fine-tuned or white-box models), CPC (7B LoRA encoder, GPU), SCOPE (no released code), EHPC (no released code, needs a local 8B model) and LongLLMLingua (7B scoring model) stay "from paper".
- **No dollar cost.** The local target costs nothing per token, so only tokens saved are reported; API cost is the saved tokens times the provider's price, which is not measured here.
- **Process disclosures.** (1) A first compression pass was stopped after 12 records, before any model output existed, because a nominal 50% word keep gave unequal token ratios across methods; the three affected arms were then calibrated like the other two and the pass was rerun from scratch. (2) The LLM run was interrupted once by a tool interruption and resumed; the 14 results produced before the interruption use identical prompts and settings and were kept. (3) Calibration was done in two stages (Appendix A). (4) After the main results were in, I added two arms I had not planned, because the gateway's `non_sensitive` route uses `force_reserve_digit=True` and my main LLMLingua-2 arms did not: `ll2d_2x` (that option at about 2x) and `ll2g_gw` (the route's literal rate 0.6). They are marked "post-hoc" everywhere. They were compressed and sent in later sessions; the uncompressed baseline was repeated once in the first of those sessions to check determinism and drift (section 6.9), but not in the second, so the latency of `ll2g_gw` is compared with the main-run baseline only. (5) The bootstrap intervals use a fresh generator with a fixed seed per call, a change made after the first analysis pass and before any number was written into this report.

## Appendix A. Reproduce the local check

Everything lives under `C:\Users\P7120489\litellm-gateway\reports\compression-fit\` (the LiteLLM gateway checkout). Nothing under the research repo was changed and nothing was committed or pushed. No API key is needed or used: the target model is local and scoring is deterministic.

**Environment (full record in `raw/env.json`)**

```text
OS            Windows 11 Pro (10.0.26200), CPU-only (no CUDA): Intel Core i7-10610U, 4 cores / 8 threads, 32 GB RAM, Intel UHD graphics
Python        3.12.10 (gateway .venv-compression), torch 2.15.0+cpu (4 intra-op threads), llmlingua 0.2.2, numpy 2.5.4, scipy 1.18.1, scikit-learn 1.9.1, tiktoken 0.14.0
Overlay       transformers 4.46.3, tokenizers 0.20.3, huggingface-hub 0.26.5  (installed with --target into reports/compression-fit/.pylib; the venv's own transformers 5.20.1 is untouched)
Target LLM    Ollama 0.40.14, llama3.2:3b (Q4_K_M, digest a80c4f17acd5), temperature 0, seed 7, num_predict 24, num_ctx 4096
Compressors   microsoft/llmlingua-2-bert-base-multilingual-cased-meetingbank (HF cache), openai-community/gpt2 (downloaded 2026-11-05, snapshot 607a30d7)
```

**Commands, in the order they were run** (from `C:\Users\P7120489\litellm-gateway`, Git Bash)

```bash
# 0. one-time setup
./.venv-compression/Scripts/python.exe -m pip install --target reports/compression-fit/.pylib "transformers==4.46.3" "tokenizers==0.20.3" "huggingface-hub==0.26.5"
./.venv-compression/Scripts/python.exe -c "from huggingface_hub import snapshot_download as s; s('openai-community/gpt2', allow_patterns=['config.json','generation_config.json','model.safetensors','tokenizer.json','vocab.json','merges.txt','tokenizer_config.json'])"

# 1. data (deterministic; SHA-256 in raw/data_sha256.txt)
python reports/compression-fit/scripts/gen_data.py

# 2. calibrate requested rates on DEV items, then compress every TEST item (timed, one process, machine otherwise idle)
export PYTHONPATH="C:/Users/P7120489/litellm-gateway/reports/compression-fit/.pylib" HF_HUB_OFFLINE=1
./.venv-compression/Scripts/python.exe reports/compression-fit/scripts/compress_all.py --calibrate --only ll2,ll1        # stage 1 (copy kept as raw/calibration_ll2_ll1_only.json)
./.venv-compression/Scripts/python.exe reports/compression-fit/scripts/compress_all.py --calibrate --only sc,rand,qaware --run   # stage 2 + timed pass -> raw/compressed.jsonl

# 3. same prompts to the same local model, one request at a time (resumable) -> raw/llm_runs.jsonl
python reports/compression-fit/scripts/run_llm.py

# 3b. post-hoc arms, added after the main results were seen (run one after the other, never together: both measure latency)
bash reports/compression-fit/scripts/posthoc_run.sh    # ll2d_2x: rate calibrated to ~2x, plus a repeat of the baseline -> raw/llm_runs_posthoc.jsonl
bash reports/compression-fit/scripts/posthoc_run2.sh   # ll2g_gw: literal gateway rate 0.6 + digit protection -> raw/llm_runs_posthoc.jsonl

# 4. statistics and tables -> raw/results/results.json, results.md, rows.csv, load_costs.txt, examples.txt
./.venv-compression/Scripts/python.exe reports/compression-fit/scripts/analyze.py
python reports/compression-fit/scripts/metric_check.py        # does the lenient answer metric hide anything? -> raw/results/metric_check.txt

# 5. report (section 6 is generated from raw/results/results.md; the other sections are written by hand and linted)
python reports/compression-fit/scripts/fill_section6.py
python reports/compression-fit/scripts/build_report.py && python reports/compression-fit/scripts/lint_report.py
```

Stage 1 was run with an earlier revision of `compress_all.py` that had `--calibrate` without `--only`; the final script is a superset. To reproduce exactly, keep the chosen rates in `raw/calibration.json` rather than re-calibrating.

**Paper evidence** (all checks are scripts, no network needed after the download):

```bash
python reports/compression-fit/scripts/verify_ledger.py      # every ledger quote must be a verbatim substring of its stated PDF page
python reports/compression-fit/scripts/build_evidence_index.py   # raw/ledger/EVIDENCE_INDEX.md
```

Downloads made with the user's approval on 2026-11-05: ten arXiv PDFs (2403.12968, 2304.08467, 2310.06201, 2305.14788, 2409.01227, 2508.15813, 2501.12959, 2306.14048, 2404.14469, 2310.06839; 13 MB; SHA-256 in `raw/papers_fetched_sha256.txt`) and the GPT-2 weights listed above. Raw text extracted with `pdftotext -raw` is in `raw/papers_repo_raw/` and `raw/papers_fetched_raw/`.

**Files**

| Path | Content |
|---|---|
| `REPORT.md` | this report (ledger ids expanded to table and page) |
| `REPORT_SOURCE.md`, `report_src/` | unexpanded source that `lint_report.py` checks |
| `raw/ledger/*.jsonl`, `EVIDENCE_INDEX.md` | machine-verified paper quotes with page |
| `raw/ledger/*_notes.md` | per-paper extraction notes written by the extraction agents |
| `data/*.jsonl` | benchmark items (test and dev) |
| `raw/compressed.jsonl` | every compressed context with wall and CPU time |
| `raw/llm_runs.jsonl` | every target-model response with timings and token counts (main run, 840 requests) |
| `raw/llm_runs_posthoc.jsonl` | the baseline repeat and the two post-hoc arms |
| `raw/final_sha256.txt` | SHA-256 of the final compressed and model-output files (the earlier `raw/compressed_sha256.txt` covers the main pass only, before the post-hoc arms were appended) |
| `raw/results/` | statistics, tables, per-row CSV, `metric_check.txt`, `load_costs.txt`, `examples.txt` |
| `report_tpl/06_local.tpl.md` | prose of section 6; its tables are copied from `raw/results/results.md` by `scripts/fill_section6.py` |
| `raw/calibration.json`, `raw/compressor_env.json`, `raw/env.json` | calibration grid, loaded-model costs, environment |
| `raw/gateway_facts.txt`, `raw/pipeline_proof_facts.txt` | integration facts and prior local measurements quoted in the report |
| `scripts/` | all code used |
