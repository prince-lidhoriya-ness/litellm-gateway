# Notes: CPC, SCOPE, RateDistortion (ledger: raw/ledger/semantic_rd.jsonl)

Ids in [brackets] are ledger ids. Figures in sentences marked "(arithmetic)" are my differences/ratios computed from the cited ledger rows, not printed in the papers.
Sources: CPC = arXiv 2409.01227 (AAAI 2025 version v3), SCOPE = arXiv 2508.15813 v2 (COLM 2026) [SCP-76], RateDistortion = arXiv 2407.15504 v2 (Dec 2024).

---------------------------------------------------------------------------------------------------
## CPC - Context-aware Prompt Compression (Liskavets et al.)

Profile
- Mechanism: sentence-level, extractive, query-aware; a learned encoder scores each sentence by cosine similarity to the question, top sentences within the token budget are kept in original order [CPC-01, CPC-02].
- The encoder is trained, not a plain scorer: a pre-trained LLM fine-tuned with a contrastive loss plus masked-token loss on the authors' synthetic CQR dataset [CPC-03].
- Encoder size: Mistral-7B-Instruct-v0.2 with LoRA rank 16, trained on 2048 samples, batch 32, one A100 80G; wall-clock training time is not given [CPC-04, CPC-42, CPC-43].
- Training-data creation used gpt-3.5-turbo-instruct plus Phi-3-small-128k-instruct, seeded from WikiText/Wikipedia [CPC-44, CPC-49].
- I/O: output is a readable subset of the original sentences (design claim; no readability metric or user study) [CPC-06]. Closed models: not discussed explicitly, but Table 4 uses GPT-4o as the downstream model; text-in/text-out use is inferred from the mechanism [CPC-07].
- Ratios: token budgets 3,000 and 2,000, described as about 3x and 5x; table rows show 3x, 5x and 6x (LongLLMLingua at 2,000) [CPC-08, CPC-11, CPC-17, CPC-18]. No 10x result.
- Context loss, LongBench AVG (target LLM of Tables 2-3 NOT named [CPC-47]):
  - 3,000 tokens: CPC 50.0, LongLLMLingua 48.8, LLMLingua-2 42.2, LLMLingua 37.4, Selective-Context 32.0, uncompressed 44.0 [CPC-11, CPC-12, CPC-13, CPC-14, CPC-15, CPC-09].
  - 2,000 tokens: CPC 49.5, LongLLMLingua 48.0 (6x), LLMLingua-2 39.1, LLMLingua 34.6, Selective-Context 24.8 [CPC-17, CPC-18, CPC-19, CPC-20, CPC-21].
  - ZeroSCROLLS AVG at 2,000: CPC 33.8 vs LLMLingua-2 33.4 vs LongLLMLingua 32.5; uncompressed 32.5 [CPC-17, CPC-19, CPC-18, CPC-09]. CPC's margin over LLMLingua-2 there is 0.4 (arithmetic).
  - Summarization is CPC's weak column: Summ. 23.8 at 3,000 and 23.7 at 2,000, below uncompressed 26.5 and below LLMLingua-2 and LongLLMLingua [CPC-11, CPC-17, CPC-09, CPC-13, CPC-12, CPC-19, CPC-18, CPC-51]. Code column is above uncompressed (63.5 vs 54.2 at 3,000) [CPC-11, CPC-09].
  - Domain tasks at 2,000 tokens (no uncompressed baseline, no target LLM, Rouge variant unstated): Krapivin keyword recall 43.5 vs LLMLingua-2 36.7 vs LongLLMLingua 17.1; PubMed 27.59 vs 26.24 vs 24.31 [CPC-24, CPC-25, CPC-26].
  - GPT-4o backbone (Table 4): CPC 52.91, LLMLingua-2 40.69, LongLLMLingua 31.42 [CPC-27, CPC-28, CPC-29].
  - Encoder ablation: off-the-shelf MpNet-v2 embeddings reach AVG 47.2 at 2,000 tokens, i.e. above LLMLingua-2 and just below LongLLMLingua and trained CPC (compare CPC-17, CPC-18, CPC-19); the authors put the gap at 2.3% for MpNet-v2 and 6.6% for LLM2Vec [CPC-30, CPC-31].
- Latency (compressor stage only, one A100, average over a LongBench sample; units not stated in Table 5 caption, Figure 3 axis is seconds) [CPC-33, CPC-38, CPC-62]:
  - CPC avg 0.28 / median 0.15; LLMLingua-2 avg 0.23 / median 0.1; LLMLingua avg 4.73 / median 1.47; LongLLMLingua avg 7.70 / median 1.64 [CPC-35, CPC-36, CPC-37, CPC-34].
  - Relative to CPC: LongLLMLingua 27.5x average and 10.93x median; LLMLingua 16.89x and 9.8x; LLMLingua-2 0.82x and 0.67x (i.e. faster than CPC) [CPC-34, CPC-37, CPC-36, CPC-39].
  - The "10.93x" in the abstract/README is therefore the MEDIAN compressor-time ratio versus LongLLMLingua only, on a LongBench sample [CPC-34, CPC-39].
  - CPC latency scales linearly with input length, plotted up to roughly 16k tokens [CPC-40, CPC-41].
- Cost: uncompressed LongBench prompts average 10,295 tokens; extra compute is a local 7B encoder pass, no extra LLM API call (inferred); end-to-end target-LLM saving is not measured [CPC-45].
- Limitations stated by authors: none (no limitations section) [CPC-46]. Authors criticise generative compressors as high-latency [CPC-05].
- Reproducibility: code and dataset announced; Apache-2.0 per the repo LICENSE file; dataset on Hugging Face per README [CPC-52, CPC-53, CPC-54].
- Tasks: long-doc QA, summarization (LongBench/ZeroSCROLLS, PubMed, MeetingBank, SummScreen), keyword extraction, code completion via LongBench Code column [CPC-55, CPC-56, CPC-57]. Not tested: multi-turn chat, structured data, reasoning/math, PII [CPC-58, CPC-59, CPC-60].

Not reported (CPC)
- Target LLM for Tables 2 and 3; token budget and meaning of Table 4 columns [CPC-47, CPC-27].
- How a "question" is defined for code completion, summarization and synthetic tasks [CPC-48].
- Maximum input length of the compressor; languages; inference memory; training wall-clock; data-generation dollar cost [CPC-50, CPC-49, CPC-42, CPC-44].
- End-to-end latency including the target LLM; any readability or faithfulness metric [CPC-45, CPC-06].
- Uncompressed baseline for Table 3 domain tasks [CPC-24].
- Any limitations section [CPC-46].

Article vs paper disagreements (CPC)
- ART-CPC-01 (10.93x "faster inference compared to token-level methods": actually median compressor time vs LongLLMLingua; LLMLingua-2 is faster).
- ART-CPC-02 (2x-10x: only ~3x-6x tested).
- ART-CPC-03 (readability: design property, not measured).
- ART-CPC-04 (legal/medical: no legal data; only PubMed summarization).
- ART-CPC-05, ART-CPC-06 (repo defect: paper exists; repo PDF is a different Bosch paper).
- ART-CPC-07 (better training efficiency than SCOPE: contradicted, SCOPE is training-free).
- ART-CPC-08 (lower compression ratios than token-level: not supported).
- ART-CPC-09 (article omits that CPC needs the question).

Unverified or ambiguous table columns (CPC)
- Table 2 "Tokens 1/?" column: the symbol is lost in the raw text; values read as 3x/5x/6x [CPC-10, CPC-11, CPC-18].
- Table 2 has two LongLLMLingua rows per budget (retrieval-based vs compression-based group); Table 1 uses the compression-based one [CPC-12, CPC-16, CPC-22].
- Table 1 prints a different LLMLingua number than Table 2 for the same method; Table 1's setting is not stated [CPC-22, CPC-14].
- Table 3 header is garbled in the raw text; column order taken from the caption/text order; "Rouge" variant unspecified [CPC-24, CPC-32].
- Table 4 caption says "larger encoder" but the text says GPT-4o is the backbone; no Original row and no budget [CPC-27].
- Table 5 absolute unit unstated; the avg/median relative columns are consistent with the absolute columns (7.70/0.28 = 27.5 and 1.64/0.15 = 10.93, arithmetic on CPC-34, CPC-35).
- Abstract says "up to 10.93x" although Table 5 prints 27.5x for the average; internal inconsistency in how "up to" is used [CPC-34, CPC-39].

---------------------------------------------------------------------------------------------------
## SCOPE - generative chunk-and-summarize compression (Zhang, Wang, Wang)

Profile
- Mechanism: training-free, generative; semantic chunking, chunk ranking by similarity to the WHOLE document, per-chunk dynamic ratio, abstractive rewrite of each chunk, reassembly in original order [SCP-01, SCP-06, SCP-08, SCP-83, SCP-11].
- Models: small pre-trained summarizer (default bart-large-cnn; Pegasus and Llama-3-8B-Instruct also tried), All-MiniLM embedder, a BERT NER model for keywords; no parameter counts are given in the paper [SCP-02, SCP-03, SCP-04, SCP-81, SCP-82, SCP-56, SCP-57].
- Query-aware or agnostic: AGNOSTIC; Algorithm 1 takes only text and ratio, relevance is to the full document, and QA contexts are compressed before the question is used [SCP-05, SCP-06, SCP-07].
- Output: rewritten (generated) text with original separators restored, not a subset of original tokens; no factuality/hallucination metric reported [SCP-11, SCP-72].
- Closed models: all main results use GPT-4o-mini as the downstream LLM, plus Qwen-2.5; the compressor needs no target-model access (inferred) [SCP-12].
- Ratios tested: 5x, 3x, 2x only; these are target ratios, post-compression lengths are not tabulated [SCP-13, SCP-14, SCP-08].
- Context loss, ROUGE-1 (GPT-4o-mini / Qwen-2.5):
  - GovReport uncompressed 43.78 / 27.97; at 5x SCOPE_N 43.59 / 26.52, SCOPE_D 43.73 / 27.14, LLMLingua-2 40.46 / 25.10, LongLLMLingua 36.68 / 25.97 [SCP-26, SCP-29, SCP-30, SCP-27, SCP-28].
  - GovReport at 2x: SCOPE_N 43.79 / 26.60, SCOPE_D 43.75 / 27.38, LLMLingua-2 43.60 / 26.06, LongLLMLingua 40.77 / 26.67, PartPrompt 41.79 / 27.76 [SCP-33, SCP-34, SCP-31, SCP-32, SCP-35]. At 2x the GPT-4o-mini gap between SCOPE and LLMLingua-2 is 0.2 or less (arithmetic).
  - Arxiv uncompressed 40.49 / 41.23; at 5x SCOPE_N 37.75 / 36.26, SCOPE_D 37.80 / 38.33, LLMLingua-2 35.53 / 34.11, LongLLMLingua 32.58 / 31.07; at 2x SCOPE_N 38.66 / 37.07, LLMLingua-2 38.14 / 36.37 [SCP-16, SCP-19, SCP-20, SCP-17, SCP-18, SCP-23, SCP-21].
  - PubMed (biomedical papers) uncompressed 40.22; 5x SCOPE_N 38.03 vs LLMLingua-2 35.86 [SCP-47, SCP-49, SCP-48]. Multi-News 5x: SCOPE 36.84 vs LLMLingua-2 34.80, no uncompressed row [SCP-51, SCP-52].
  - QA (F1, GPT-4o-mini): Trivia-QA uncompressed 86.08; 5x SCOPE_N 85.31, LLMLingua-2 83.58, LongLLMLingua 80.79 [SCP-37, SCP-40, SCP-38, SCP-39]. MultiFieldQA-en uncompressed 54.20; 5x SCOPE_N 41.39, SCOPE_D 43.54, LLMLingua-2 36.23, LongLLMLingua 27.03; 2x SCOPE_N 47.52, SCOPE_D 47.15, LLMLingua-2 46.96, LongLLMLingua 35.10 [SCP-37, SCP-40, SCP-41, SCP-38, SCP-39, SCP-44, SCP-45, SCP-42, SCP-43]. So long-document QA keeps a 6.7 F1 deficit at 2x for SCOPE_N (arithmetic on SCP-37, SCP-44).
  - Authors' claims: advantage grows with ratio; variation across ratios is small [SCP-54, SCP-53, SCP-85]. The printed tables only partly bear out the "within 1%" claim [SCP-53, SCP-85].
  - Keyword module matters for QA (Trivia-QA 2x: 86.07 with, 85.36 without) [SCP-55]; compressed Trivia-QA can beat the original, speculated to be rewriting salience [SCP-46].
- Latency (per document, averaged over 2x/3x/5x): GovReport SCOPE 4.20 s, PartPrompt 4.49 s, LongLLMLingua 2.79 s; Arxiv 3.39 s, 3.96 s, 2.15 s (order inferred) [SCP-59, SCP-60]. LLMLingua-2 timing is not given; summarization is the slowest step [SCP-62, SCP-61].
- Hardware: one A100 80GB, 3 AMD Rome cores, 64GB RAM; whether timing ran on GPU is not stated [SCP-63].
- Cost: no training; only small local models, no large-LLM call during compression [SCP-64, SCP-84, SCP-03].
- Limitations: no limitations section; conclusion limited to "evaluated settings" [SCP-71]. Samples of at most 2,000 records, Trivia-QA from the train split, MultiFieldQA-en only 150 rows, English-only data [SCP-68, SCP-69, SCP-70]. Safeguard for over-short rewrites exists [SCP-72]. Chunk size 400-700 (800 in one place) [SCP-65, SCP-66]; max input length not reported, long inputs handled by segment-averaged embeddings [SCP-67].
- Reproducibility: paper footnote says code is available, but the repo README said only "code coming soon." on 2026-11-05 and no LICENSE file was visible; models used are public [SCP-73, SCP-74, SCP-75].
- Tasks tested: long-document summarization and QA only [SCP-77, SCP-78]. Not tested: coding, multi-turn chat, structured data, reasoning/math, PII [SCP-78, SCP-80]. Legal text only as part of MultiFieldQA-en; biomedical = PubMed [SCP-79, SCP-47].

Not reported (SCOPE)
- Parameter counts, memory footprint, GPU-vs-CPU timing; latency of LLMLingua-2, LLMLingua and Selective-Context [SCP-04, SCP-63, SCP-59].
- Max input length; actual achieved compression ratios; end-to-end target-LLM cost/latency saving [SCP-67, SCP-14, SCP-84].
- Factual-consistency/hallucination evaluation of rewritten text [SCP-72, SCP-11].
- Limitations section; code and license [SCP-71, SCP-74].
- Qwen-2.5 results for MultiFieldQA-en [SCP-36].

Article vs paper disagreements (SCOPE)
- ART-SCP-01 (BART: supported with caveats), ART-SCP-02 (no training overhead: supported, but runtime overhead exists), ART-SCP-03 (training-free: supported), ART-SCP-04 (2x-10x: only 2x-5x tested), ART-SCP-05 (legal/medical: no legal-specific test), ART-SCP-06 (repo defect: paper exists, code not released), ART-SCP-07 (slower than removal methods: supported), ART-SCP-08 (lower compression than token-level: not supported), ART-SCP-09 ("importance" is similarity to the whole document, not query relevance).
- Cross-article: ART-CPC-07.

Unverified or ambiguous table columns (SCOPE)
- Tables 1-2: each metric printed twice, GPT then QWEN; "Original" row is the 1x baseline [SCP-15, SCP-16].
- Table 3: third column is Trivia-QA with Qwen-2.5; MultiFieldQA-en has no Qwen column [SCP-36].
- Table 1/2 BLEU values exceed ROUGE-1 in the same row (e.g. 62.46 vs 43.78 for GovReport original), which is unusual; BLEU implementation not described [SCP-26].
- Table 10 is "Longbench GovReport", a different dataset from Table 2 "GovReport-Summarization" (ROUGE-1 about 28 vs 43.6) [SCP-56, SCP-29].
- Tables 8 and 9 have no Original row [SCP-51, SCP-58].
- Section 4.5 Arxiv runtimes are not labelled by method; order inferred; unit "per document" is my reading [SCP-60, SCP-59].
- The "up to 800 tokens" (Sec. 3.1) vs "400 to 700 tokens" (Sec. 4) chunk limits [SCP-66, SCP-65].
- v2 of the paper (Aug 2026) is what was read; the repo article may describe an earlier version [SCP-76].

---------------------------------------------------------------------------------------------------
## RateDistortion - "Fundamental Limits of Prompt Compression" (Nagle et al.)  (secondary evidence)

What is evaluated
- A theory plus benchmark paper: it formalises prompt compression as a distortion-rate linear program with an efficient dual algorithm; the only new compressors are the authors' QuerySelect and Adaptive QuerySelect (query-aware, variable-rate LLMLingua-2 variants) [RD-01, RD-39, RD-09].
- Scope: token-level hard-prompt methods for black-box models; soft-prompt methods excluded; the paper asserts all literature methods work by token pruning, which CPC (sentence pruning) fits but abstractive SCOPE does not (inference) [RD-01, RD-02, RD-03, RD-54].
- Compressors compared: Selective Context, LLMLingua, "LLMLingua Query" (the query-aware extension, cited as [JWL+23] = LongLLMLingua), LLMLingua-2. CPC and SCOPE are not evaluated [RD-09, RD-10, RD-54].
- Target LLM: only Mistral 7B Instruct v0.2, kept fixed and hidden from the compressors (a simulated black box) [RD-06].
- Datasets: (a) synthetic binary-string prompts of four to ten tokens with seven bit-string queries, 1400 validation examples; (b) ten GPT-4 sentences (largest 15 tokens) with four queries each; (c) NarrativeQA summaries (hundreds of tokens, about 3,500 samples) [RD-13, RD-14, RD-17, RD-15, RD-55, RD-16].
- Metrics: log loss and 0/1 loss (synthetic); RougeL and BertScore (natural language) [RD-12]. "Rate" is the expected compressed/original length fraction, not an "Nx" ratio [RD-58]; swept from 0.04 to 1.0 [RD-31].
- Important caveat: on the synthetic set every compressor was fine-tuned on the training split, so those curves are not off-the-shelf behaviour; NL experiments use published HF checkpoints [RD-21, RD-24].

What it shows vs the optimal bound (no per-ratio numbers are printed in text; figure curves were not extractable here)
- Synthetic set: most existing methods are far from the theoretical limit; only the authors' Adaptive QuerySelect beats the optimal query-agnostic curve, so LLMLingua, LLMLingua-2 and Selective Context do not [RD-18, RD-19] (Fig. 1, p.4).
- Query conditioning helps substantially (QuerySelect vs LLMLingua-2) [RD-20] (Fig. 1, p.4). LLMLingua Query was mixed versus vanilla LLMLingua [RD-22] (p.16).
- Small NL set (Fig. 6, p.18): gap between all algorithms and optimal strategies is significant; even query-aware methods are far from the query-agnostic optimum [RD-24, RD-57]. Optimal strategies could reach much lower distortion with roughly 70% (query-aware) and 40% (query-agnostic) fewer tokens [RD-25]. Only LLMLingua-2-based methods (including the authors' variants) beat no compression, and only at higher rates [RD-26]. The authors' methods are best at low rates (high compression) [RD-56]. The evidence rests on ten prompts [RD-15, RD-55].
- NarrativeQA (Fig. 7, p.20; D.2, p.41): the "optimal" is only a beam-search upper bound (C = 4000, B = 5); LLMLingua-2-based methods beat the query-agnostic bound at most rates, yet the query-aware gap stays large; authors' methods are better below rate 0.5 and merely competitive above [RD-27, RD-28, RD-29, RD-30].
- Optimal curves eventually fall below the no-compression baseline [RD-23].
- Compressor time per prompt (Table 6, seconds, hardware unspecified): NarrativeQA Selective Context 1.043, LLMLingua 0.510, LLMLingua Query 1.060, LLMLingua-2 0.113; small set 0.049, 0.273, 0.530, 0.044 [RD-32, RD-33, RD-34, RD-35, RD-36]. Authors' query-aware compressor trained in 1-2 hours on one A100 [RD-38].

Query-aware vs query-agnostic
- Query-aware: compressor also receives the query; query-agnostic: prompt only; the framework assumes a query is always supplied to the target LLM [RD-07, RD-08].

The 2^n claim and NP-hardness
- Condition: building D_x needs one target-LLM call per candidate compressed prompt; restricted to pruned prompts that is 2^len(x) candidates, and the unrestricted candidate set is far larger (vocabulary 32,000) [RD-40, RD-41, RD-42].
- It is the cost of computing the theoretical benchmark curve for a prompt, impractical at hundreds of tokens; it is not stated as a cost of running or evaluating a compressor [RD-43].
- The authors use beam search (an upper bound, O(BN^2) nodes; about 10^6 calls and 11.5 days for a 100-token prompt at 1 s per call) [RD-44, RD-45].
- The LP itself is called simple and the dual algorithm efficient once D_x is known; NP-hardness is never discussed [RD-39, RD-46].

Not reported (RateDistortion)
- Numeric values of any curve at a given compression ratio; per-method gap sizes [RD-18, RD-25].
- Any result for CPC, SCOPE, LongLLMLingua by name, coding, chat, structured data, summarization, PII tasks [RD-54, RD-17].
- Target LLMs other than Mistral 7B; hardware for Table 6 timings [RD-06, RD-32].
- NP-hardness or any complexity-class statement [RD-46].
- Own-repo license: WebFetch of github.com/acnagle/fundamental-limits showed no LICENSE file or badge; weights said to be on Hugging Face (acnagle/QuerySelect) [RD-53, RD-52].
- Stated limitations are only: study the method exhaustively on NL data; metric choice is an open problem; short-prompt data are hard to find [RD-47, RD-49, RD-48].

Article/README vs paper disagreements (RateDistortion)
- ART-RD-01 (README "at least 2^n inference calls, forcing reliance on greedy approximations": 2^len(x) is the benchmark-computation cost under pruning; beam search; no NP-hardness).
- ART-RD-02 (README "far below optimal bounds, particularly at high compression ratios": paper shows gap on toy data only; no high-ratio statement; LLMLingua-2-based beat the agnostic bound on NarrativeQA).

Unverified or ambiguous items (RateDistortion)
- All headline results are in figures (Fig. 1, 4, 6, 7, 17); no numbers in text except 70%/40% and axis values; I could not render the PDF figures, so no curve values were read [RD-18, RD-25].
- "LLMLingua Query" is assumed to be the LongLLMLingua-style query-aware extension; the paper never labels it "LongLLMLingua" [RD-09, RD-10].
- "LLMLingua-2 methods" in the no-compression statement includes the authors' QuerySelect variants, so it is not a statement about plain LLMLingua-2 alone [RD-26].
- Table 6 hardware is not specified; machines in App. C.1 include RTX 4090 workstations and a DGX [RD-32, RD-37].
- Third-party facts from WebFetch summaries not verbatim: the CPC README lists Mistral-7B and Llama-1B LoRA adapters on Hugging Face and no license line in the README; CPC GitHub page shows Apache-2.0; SCOPE repo page shows only a README. Treat these as unverified secondary summaries beyond the ledger quotes [CPC-53, CPC-54, SCP-74].
