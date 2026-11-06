# LLMLingua (v1) and LongLLMLingua: evidence notes

Sources: LLMLingua = arXiv 2310.05736v2 (raw/papers_repo_raw/llmlingua.txt); LongLLMLingua = arXiv 2310.06839v2 (raw/papers_fetched_raw/longllmlingua-2310.06839.txt). Ledger: raw/ledger/llmlingua.jsonl. Anything marked "derived" is our arithmetic on quoted numbers, not printed in a paper.

## LLMLingua (v1, Jiang et al., EMNLP 2023)

Mechanism
- Coarse-to-fine token pruning: budget controller (demonstration-level selection), iterative token-level compression, distribution alignment. [LLv1-MECH-1, LLv1-MECH-2]
- Scoring is plain perplexity from a small LM (GPT-2 or LLaMA class); demonstrations are kept in descending perplexity order, tokens kept when above a dynamic threshold, per 100-token segment. [LLv1-MECH-3, LLv1-MECH-4, LLv1-MECH-5, LLv1-LAT-12]
- No trained keep/drop classifier; the only training is instruction-tuning the small LM on target-LLM outputs (alignment). [LLv1-MECH-6]
- Compressor models used: Alpaca-7B and GPT2-Alpaca (GPT2-small tuned on Alpaca); pre-trained LLaMA-7B appears only in the no-alignment ablation. [LLv1-MECH-7, LLv1-MECH-8, LLv1-MECH-10]
- Model size is stated only through the 7/175 parameter ratio used in a FLOPs estimate; GPT2-small size is not printed. [LLv1-MECH-9]
- Instruction and question are NOT left uncompressed: they get light fixed rates (0.85 and 0.9) while demonstrations absorb most of the budget. [LLv1-Q-1, LLv1-Q-2, LLv1-Q-3, LLv1-ABL-10]

I/O
- Text in, text out; no gradient flow through the target LLM; positioned for black-box/API LLMs. [LLv1-IO-1, LLv1-IO-2, LLv1-IO-4]
- Target LLMs: GPT-3.5-Turbo-0301 (all datasets) and Claude-v1.3 (GSM8K only, 1-shot and half-shot constraints). [LLv1-IO-3, LLv1-CL-30]
- Claude runs reuse Alpaca-7B, citing difficulty collecting alignment data. [LLv1-IO-7]
- Output is visibly garbled text (example 2366 to 117 tokens); GPT-4 can reconstruct it, GPT-3.5-Turbo struggles. [LLv1-IO-5, LLv1-IO-6, LLv1-LIM-4, LLv1-LIM-5]

Compression ratio and quality (GPT-3.5-Turbo unless noted; Table 2 columns = GSM8K EM/Tokens/ratio then BBH EM/Tokens/ratio)
- Headline: up to 20x, "only a 1.5 point drop" (this is GSM8K quarter-shot). [LLv1-CR-1, LLv1-CR-2]
- GSM8K full-shot 78.85 (2,366 tokens); LLMLingua 79.08 at 5x, 77.41 at 14x, 77.33 at 20x. BBH full-shot 70.07; LLMLingua 70.11 at 3x, 61.60 at 5x, 56.85 at 7x. [LLv1-CL-1, LLv1-CL-2, LLv1-CL-3, LLv1-CL-4]
- BBH drops 8.5 and 13.2 EM points at 5x and 7x; the authors blame hard subtasks such as tracking_shuffled_objects_seven_objects. [LLv1-CL-15, LLv1-CL-16]
- Zero-shot (instruction only) scores 48.75 (GSM8K) and 32.32 (BBH). [LLv1-CL-5]
- Caveat on the 20x claim: the "full-shot" GSM8K prompt is a long complex multi-step CoT prompt; a standard 8-shot 3-step CoT "Simple Prompt" scores 74.9 at 691 tokens, and the 20x prompt beats it by 2.43. [LLv1-CL-9, LLv1-CL-7, LLv1-CL-8] (Derived: 117 vs 691 tokens is roughly 6x fewer tokens, not 20x, against that baseline.)
- Caveat: a plain "1-shot" baseline scores 77.10 at 6x on GSM8K and 69.60 at 3x on BBH, close to LLMLingua at 1-shot budget. [LLv1-CL-6]
- Baselines at quarter-shot: Selective-Context 44.20 / 47.37, Sentence Selection 66.67 / 46.00, GPT-4 generation 56.33 / 26.81. [LLv1-CL-10, LLv1-CL-11, LLv1-CL-12]
- ShareGPT (conversation) and Arxiv-March23 (summarization), Table 1 columns = BLEU, Rouge1, Rouge2, RougeL, BS F1, Tokens, 1/tau per dataset: Constraint I gives 1.9x and 4x, Constraint II gives 3.3x and 9x. [LLv1-CL-17, LLv1-CL-18, LLv1-CL-19, LLv1-CL-20]
- These two datasets are scored against GPT-3.5-Turbo output from the uncompressed prompt, so there is no human-quality or task-accuracy metric. [LLv1-CL-23, LLv1-CL-24, LLv1-CL-25]
- Claude-v1.3 on GSM8K: 83.51 at 5x and 82.61 at 14x versus 81.8 for the simple prompt. [LLv1-CL-27, LLv1-CL-28, LLv1-CL-29]
- GPT2-Alpaca compressor on GSM8K: 77.02 at 5x, 76.27 at 18x; 2.06/0.99/1.06 EM points below Alpaca-7B. [LLv1-CL-31, LLv1-CL-32, LLv1-CL-33]

Ablation (GSM8K, 1-shot constraint, 5x; Table 3, target LLM not named in caption)
- Full 79.08; w/o budget controller 73.62; w/o iterative token-level 72.93; w/o dynamic ratio 77.26; random demonstration selection 72.78; w/o distribution alignment 78.62; stop-word removal 76.27 at only 1.3x. [LLv1-ABL-1, LLv1-ABL-2, LLv1-ABL-4, LLv1-ABL-5, LLv1-ABL-6, LLv1-ABL-7, LLv1-ABL-9]
- Budget controller variant definition: same ratio for all components. Alignment is worth 0.56 EM. [LLv1-ABL-3, LLv1-ABL-8]

Latency and compute (Table 6, GSM8K, V100-32G, seconds)
- Baseline 8.6 s; with LLMLingua 4.9 s (1.7x) at 2x, 2.3 s (3.3x) at 5x, 1.3 s (5.7x) at 10x; compressor-only 0.8 / 0.3 / 0.2 s. Authors summarise 1.7x to 5.7x. [LLv1-LAT-3, LLv1-LAT-4, LLv1-LAT-5, LLv1-LAT-6, LLv1-LAT-1, LLv1-LAT-7]
- Hardware: Tesla V100 (32GB) for everything. [LLv1-HW-1]
- Compute saving (about 4x at 5x) is a model estimate that assumes the small LM gets the same system optimizations, not a measurement. [LLv1-LAT-8, LLv1-LAT-9]
- Generated output also gets shorter as ratio rises. [LLv1-LAT-10]
- Training cost reported only for GPT2-Alpaca: about 150 minutes. [LLv1-LAT-11]

Cost (GPT-3.5-Turbo pricing, Table 7, GSM8K / BBH / ShareGPT / Arxiv)
- Original 5.2 / 12.8 / 0.7 / 1.3 dollars; compressed 0.5 / 4.8 / 0.3 / 0.2 dollars; small-LM compute not priced. [LLv1-COST-1, LLv1-COST-2, LLv1-COST-3, LLv1-COST-4, LLv1-COST-5]

Limitations (authors)
- Notable drop at 25x-30x on GSM8K; upper limit depends on prompt length, task, sentence count; tokenizer mismatch can underestimate length. [LLv1-LIM-1, LLv1-LIM-2, LLv1-LIM-3]
- Input lengths: Arxiv prompts are truncated to five sections of 10,000 characters; ShareGPT includes coding and multilingual chats but with no breakdown. [LLv1-LIM-6, LLv1-LIM-7]

Reproducibility
- Code link in paper; official repo is MIT licensed; README ships a pip package and names no v1 checkpoint; paper does not state a GPT2-Alpaca checkpoint release. [LLv1-REP-1, LLv1-REP-2, LLv1-REP-3, LLv1-REP-4]

Tasks tested
- Reasoning/math (GSM8K, BBH), multi-turn chat (ShareGPT, 575 samples), summarization (Arxiv-March23, 500 items). [LLv1-TASK-1, LLv1-TASK-2, LLv1-TASK-3, LLv1-TASK-8]
- Not tested: coding, long-document QA/RAG, structured data, sensitive/PII content. [LLv1-TASK-4, LLv1-TASK-5, LLv1-TASK-6, LLv1-TASK-7]

## LongLLMLingua (Jiang et al., 2023, v2 Aug 2024)

Mechanism
- Built on LLMLingua as backbone; adds question-aware coarse ranking (question perplexity given each document plus a restrictive statement), contrastive-perplexity token scoring, document reordering, dynamic per-document ratios, subsequence recovery. [LongLL-MECH-1, LongLL-MECH-2, LongLL-MECH-3, LongLL-MECH-4, LongLL-MECH-5, LongLL-MECH-6, LongLL-MECH-7, LongLL-MECH-8]
- Compressor LM: LLaMA-2-7B-Chat; GPT2-dolly in the "GPT2-small" ablation; baselines LLMLingua and Selective-Context also use LLaMA-2-7B-Chat here. [LongLL-MECH-9, LongLL-MECH-10, LongLL-MECH-15]
- Instruction/question are lightly compressed (0.85, 0.9), segment size 200, reorder used only on NaturalQuestions. [LongLL-MECH-12, LongLL-MECH-13, LongLL-MECH-11]

I/O
- Target LLMs: GPT-3.5-Turbo-0613 (16k variant above 4k tokens) and LongChat-13B-16k; framework shown with black-box LLMs. [LongLL-IO-1, LongLL-IO-4, LongLL-IO-2]
- Question-aware, so it must be re-run per question and the context cannot be cached. [LongLL-IO-3, LongLL-LIM-1]

Quality (NaturalQuestions 20 docs, accuracy, GPT-3.5-Turbo columns first; Table 1 columns 1st/5th/10th/15th/20th = answer position, then Reorder)
- Original prompt: 75.7 / 57.3 / 54.1 / 55.4 / 63.1 (2,946 tokens, 4.1 s): U-shaped lost-in-the-middle. [LongLL-CL-2, LongLL-POS-1, LongLL-POS-2]
- LongLLMLingua 2x: 77.2 / 72.9 / 70.8 / 70.5 / 70.6, Reorder 76.2, 1.4x speedup; 4x: 75.0 / 71.8 / 71.2 / 71.2 / 74.7, Reorder 75.5, 2.0x speedup. [LongLL-CL-3, LongLL-CL-4]
- At 4x the 1st-position score (75.0) is below the original (75.7); the gain comes from middle positions. [LongLL-CL-4, LongLL-CL-2] (derived comparison)
- Headline 21.4% at around 4x fewer tokens, answer at 10th position. [LongLL-CR-1, LongLL-CR-4] (Derived: 75.5 reorder minus 54.1 original = 21.4, so it is points not percent; 71.2 minus 54.1 = 17.1 points at the 10th position without reorder.)
- LLMLingua v1 under this benchmark: 25.5 / 27.5 / 23.5 / 26.5 / 30.0 at 4x, 39.7 ... at 2x; authors say it can fall below zero-shot. [LongLL-CL-5, LongLL-CL-6, LongLL-CL-10, LongLL-CL-9]
- Reordering gives a flat 76.2 at every answer position (2x). [LongLL-POS-3]
- Coarse ranker alone at 4x (71.1 / 70.7 / 69.3 / 68.7 / 68.5) is already close to full method. [LongLL-CL-8]
- LongBench (GPT-3.5-Turbo; AVG; original 44.0 at 10,295 tokens, 15.6 s): LongLLMLingua 48.8 at 3x, 48.3 at 6x; Code column 54.2 original, 55.2 and 56.7 compressed; LLMLingua v1 37.4 at 3x and 34.6 at 5x. [LongLL-CL-16, LongLL-CL-17, LongLL-CL-18, LongLL-CL-19, LongLL-CL-20, LongLL-CL-23]
- LongBench with LongChat-13b: original AVG 30.5, LongLLMLingua 35.5 at 6x. [LongLL-CL-24, LongLL-CL-25]
- ZeroSCROLLS (AVG; original 32.5 at 9,788 tokens): LongLLMLingua 33.0 at 3x and 32.7 at 6x. [LongLL-CL-27, LongLL-CL-28, LongLL-CL-29]
- MuSiQue (F1, 2x): original 45.8, LongLLMLingua 51.2, LLMLingua 40.1. [LongLL-CL-33, LongLL-CL-34, LongLL-CL-35]
- LooGLE long-dependency QA (original 30,546 tokens): original AVG 22.6, LongLLMLingua 32.1 at 10x, LLMLingua 17.3 at 9x. [LongLL-CL-36, LongLL-CL-37, LongLL-CL-38, LongLL-CL-39]

Question-aware contribution (ablations)
- NQ 2x: full 77.2 at 1st position; without question-awareness 42.1; with SBERT 73.2; without question-aware fine-grained 75.8; without dynamic ratio 74.4; without subsequence recovery 76.7; GPT2-small 74.6. [LongLL-ABL-2, LongLL-ABL-3, LongLL-ABL-4, LongLL-ABL-5, LongLL-ABL-6, LongLL-ABL-7, LongLL-ABL-8]
- LongBench AVG: full 48.3; without question-awareness 37.4; without question-aware fine-grained 44.2; GPT2-small 43.0; without reordering 48.0. [LongLL-ABL-10, LongLL-ABL-11, LongLL-ABL-12, LongLL-ABL-13, LongLL-ABL-14, LongLL-ABL-15, LongLL-ABL-16]

Latency and hardware
- End-to-end on V100-32G against API calls; time includes compression; compressor-only time not broken out; speedup grows to 2.6x. [LongLL-LAT-1, LongLL-LAT-2, LongLL-LAT-3, LongLL-HW-1, LongLL-CR-3]
- LongLLMLingua is stated to double LLMLingua's compute. [LongLL-LAT-4]

Cost (GPT-3.5-Turbo pricing, per 1,000 samples)
- Original 4.6 / 31.5 / 30.6 / 3.8 / 93.6; LongLLMLingua 1.3 / 3.0 / 3.2 / 1.8 / 5.6 (NQ multi-doc, LongBench, ZeroSCROLLS, MuSiQue, LooGLE); 94.0% on LooGLE. [LongLL-COST-1, LongLL-COST-2, LongLL-COST-3, LongLL-COST-5, LongLL-CR-2]
- Small-LM compute is not part of these costs. [LongLL-COST-4]

Limitations (authors and examples)
- Per-question re-compression; may weaken when context-question relation is complex or subtle. [LongLL-LIM-1, LongLL-LIM-2]
- Token pruning corrupts entities; recovery needed (example 209 became 2019). [LongLL-LIM-3, LongLL-LIM-4]
- Code case study: response lacks the if-wrapper of the ground truth. [LongLL-LIM-5, LongLL-LIM-6]
- LooGLE prompts average 24,005 tokens; compressor input limit not stated. [LongLL-LIM-7]

Reproducibility
- Code link in paper; same MIT repo with LongLLMLingua snippet; compressor is LLaMA-2-7B-Chat (license not discussed). [LongLL-REP-1, LongLL-REP-2, LongLL-REP-3, LongLL-REP-4]

Tasks tested
- Long-document QA/RAG (NaturalQuestions, LongBench, ZeroSCROLLS, MuSiQue, LooGLE); coding (LongBench Code, lcc case) and summarization inside LongBench/ZeroSCROLLS. [LongLL-TASK-1, LongLL-TASK-2, LongLL-TASK-3, LongLL-CL-23]
- Not tested: multi-turn chat, structured data, math reasoning, sensitive/PII content. [LongLL-TASK-4, LongLL-TASK-5, LongLL-TASK-6, LongLL-TASK-7]

## Not reported
- GPT2-small and Alpaca-7B exact parameter counts (only the 7/175 ratio); Alpaca-7B alignment compute; release of aligned checkpoints. [LLv1-MECH-9, LLv1-LAT-11, LLv1-REP-4]
- Compressor maximum input length and memory use, for both papers; how 24k-30k-token prompts are fed to the small LM. [LongLL-LIM-7]
- LongLLMLingua compressor-only latency (only end-to-end incl. API time) and compressor GPU cost in the dollar tables. [LongLL-LAT-2, LongLL-COST-4]
- Per-language, per-scenario (coding vs chitchat) results for ShareGPT; any human evaluation. [LLv1-LIM-7, LLv1-CL-23]
- Whether distribution alignment was applied in the LongLLMLingua experiments. [LongLL-MECH-14]
- Any 20x+ number other than GSM8K; Figure 3 values beyond 20x are plot-only (not in text).
- Coding, long-doc QA/RAG, structured data and PII for LLMLingua v1; chat, structured data, math and PII for LongLLMLingua. [LLv1-TASK-4, LLv1-TASK-5, LLv1-TASK-6, LLv1-TASK-7, LongLL-TASK-4, LongLL-TASK-5, LongLL-TASK-6, LongLL-TASK-7]

## Article vs paper disagreements
- llmlingua.md: 98.5% at moderate compression; 20x minimal loss; per-LLM encoder training; no model training needed; RAG with maintained quality; lost-in-the-middle; beyond-20x degradation; Microsoft Teams use case; GPT-2-small/LLaMA-7B sentence elimination. [ART-LL-1, ART-LL-2, ART-LL-3, ART-LL-4, ART-LL-5, ART-LL-6, ART-LL-7, ART-LL-8, ART-LL-9]
- README and report.txt: 20x with 98.5% retention; 1.6x-5.7x latency; LongLLMLingua 17.1% at 4x; summarization at 20x; chat at 4x-9x; math degrades beyond 10x. [ART-RD-1, ART-RP-1, ART-RD-2, ART-RP-2, ART-RD-3, ART-RP-3, ART-RD-4, ART-RD-5, ART-RD-6]
- Summary of the three requested checks: (1) 98.5% is not printed anywhere; paper says "1.5 point drop" at 20x on GSM8K only (derived retention 77.33 / 78.85 is about 98.1%, and BBH at 7x keeps about 81%). (2) Paper says 1.7x to 5.7x, not 1.6x. (3) Paper says 21.4% (points) at the 10th position; 17.1 is the 4x no-reorder 10th-position point difference. Derived values are our arithmetic.

## Unverified or ambiguous table columns
- LLMLingua Table 2 and Table 3 print different token counts (446 vs 439) for the same 1-shot 79.08 row. [LLv1-CL-2, LLv1-ABL-1]
- Text in Sec. 5.2 lists "9x and 3.3x" with ShareGPT first, but Table 1 gives 3.3x to ShareGPT and 9x to Arxiv-March23. [LLv1-CL-22, LLv1-CL-20]
- LLMLingua Table 3 caption does not name the target LLM (assumed GPT-3.5-Turbo from the setup, not stated). [LLv1-ABL-1]
- LongLLMLingua Table 1 zero-shot row is garbled in extraction (56.1 35.0 15 196x 1.1 3.7x); column mapping not certain. [LongLL-CL-9]
- LongLLMLingua Table 6 (ZeroSCROLLS, 2,000 tokens, LLMLingua row): latency 4.8 s printed with speedup 0.3x versus 12.2 s original, internally inconsistent. [LongLL-CL-30]
- Abstract says 1.4x-2.6x for "about 10k tokens at 2x-6x", but the 1.4x row is the 2,946-token NaturalQuestions 2x row; LongBench/ZeroSCROLLS give 1.5x to 2.6x at 3x to 6x. [LongLL-CR-3, LongLL-CL-3, LongLL-CL-17, LongLL-CL-18, LongLL-CL-28, LongLL-CL-29]
- Appendix C.2 says the maximum question-aware drop is 35.8 points; Table 4 synthetic column is 53.0 to 18.0 (a 35.0 gap, derived); the 35.8 is not reproducible from the printed table. [LongLL-ABL-15, LongLL-ABL-3, LongLL-ABL-11]
- LongLLMLingua per-task metrics for LongBench and ZeroSCROLLS are not itemised in the tables (scores only); NaturalQuestions metric is accuracy per the Figure 1b axis. [LongLL-CL-13]
- LongLLMLingua Table 3 row labelled "w/ Document Reordering" is presumably the reorder variant (flat 76.2); label is as printed. [LongLL-POS-3]
- Original-prompt GPT-3.5-Turbo versions differ: LLMLingua uses 0301, LongLLMLingua uses 0613 (16k above 4k tokens); numbers across the two papers are not directly comparable. [LLv1-IO-3, LongLL-IO-1, LongLL-IO-4]
