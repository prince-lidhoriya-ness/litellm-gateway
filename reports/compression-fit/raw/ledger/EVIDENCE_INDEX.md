# Evidence index (every quote below was machine-verified against the stated PDF page by scripts/verify_ledger.py)

1156 entries. Page = 1-based PDF page of the raw-mode text in raw/papers_*_raw/.


## 500xCompressor

- **XC-001** (mechanism) Adds approximately 0.25% extra parameters (the LoRA weights of the encoder).  
  value: `0.25%` metric: additional parameters task:  conditions:   
  source: 500x-compressor.txt p.1 Abstract  
  quote: `The 500xCompres- sor introduces approximately 0.25% additional parameters`
- **XC-002** (mechanism) Encoder = frozen LLM plus trainable LoRA parameters; decoder = the original frozen LLM (same weights). LoRA rank/alpha are not given in the text.  
  value: `` metric:  task:  conditions: LLaMa-3-8b-chat  
  source: 500x-compressor.txt p.2 Sec. 2.1  
  quote: `The encoder is the frozen LLM LLM with trainable LoRA parameters Lora, while the decoder is the original frozen LLM LLM`
- **XC-003** (io) Output form: the per-layer K V values of the compressed tokens, not just their embeddings.  
  value: `` metric:  task:  conditions:   
  source: 500x-compressor.txt p.2 Sec. 2.1  
  quote: `the information in the text is encoded into the compressed tokens, whose K V values in each layer of the LLM HC are output and passed to the decoder`
- **XC-004** (io) The decoder consumes the encoder's KV values; the paper does not discuss closed/API LLMs (inferred from mechanism: needs access to the model's KV cache internals, so not usable with an API-only LLM).  
  value: `` metric:  task:  conditions: inferred from mechanism  
  source: 500x-compressor.txt p.2 Sec. 2.1  
  quote: `During pretraining, the inputs of the decoder are the K V values of the compressed tokens from the encoder`
- **XC-005** (io) Both encoder and decoder are the same original LLM, which is left unchanged in the decoder; compressed KV values are therefore tied to that LLM (same-model use inferred from mechanism).  
  value: `` metric:  task:  conditions: inferred from mechanism  
  source: 500x-compressor.txt p.3 Sec. 2.1  
  quote: `The training process ensures no data leakage, as the origi- nal LLM parameters in both the encoder and decoder remain unchanged, and no additional parameters are introduced in the decoder`
- **XC-006** (io) Compressed prompts can be used by the original LLM without fine-tuning it.  
  value: `` metric:  task:  conditions:   
  source: 500x-compressor.txt p.1 Abstract  
  quote: `could be utilized by the original large lan- guage model (LLM) without requiring fine-tuning`
- **XC-007** (mechanism) Difference from ICAE: decoder input is the KV values of the compressed tokens, not their embeddings.  
  value: `` metric:  task:  conditions:   
  source: 500x-compressor.txt p.3 Sec. 2.1  
  quote: `The decoder of ICAE input is the embeddings for the compressed tokens, whereas 500xCom- pressor uses the K V values for the compressed tokens`
- **XC-008** (latency_compute) Authors' assertion (not measured): KV values encapsulate more information, do not increase inference time and have small impact on GPU memory.  
  value: `` metric:  task:  conditions:   
  source: 500x-compressor.txt p.3 Sec. 2.1  
  quote: `K V values could encapsulate more information, do not increase inference time, and have small impact on GPU memory us- age`
- **XC-009** (mechanism) Authors position the method as akin to Prefix Tuning (compressing into KV values of prefixed special tokens), i.e. an existing idea applied to text compression.  
  value: `` metric:  task:  conditions:   
  source: 500x-compressor.txt p.6 Sec. 5  
  quote: `500xCompressor, akin to Prefix Tuning, compresses texts into the K V values of pre- fixed special tokens`
- **XC-010** (mechanism) Only one base LLM is evaluated: LLaMa-3-8b-chat (regeneration experiment).  
  value: `LLaMa-3-8b-chat` metric:  task: Arxiv Corpus regeneration conditions:   
  source: 500x-compressor.txt p.4 Sec. 4.1  
  quote: `Figure 3 (left) presents the results for LLaMa-3-8b-chat in regenerating the original Arxiv abstracts from the com- pressed tokens`
- **XC-011** (mechanism) QA experiment also uses LLaMa-3-8b-chat.  
  value: `LLaMa-3-8b-chat` metric:  task: ArxivQA conditions:   
  source: 500x-compressor.txt p.4 Sec. 4.2  
  quote: `Figure 3 (right) shows the results for LLaMa-3-8b-chat in answering extractive ArxivQA questions based on the com- pressed texts`
- **XC-012** (compression_ratio) Headline ratio range 6x to 480x.  
  value: `6x to 480x` metric: compression ratio task: Arxiv Corpus / ArxivQA conditions: LLaMa-3-8b-chat  
  source: 500x-compressor.txt p.1 Abstract  
  quote: `achieves compression ratios ranging from 6x to 480x`
- **XC-013** (compression_ratio) Ratios come from compressing 96-480-token abstracts into 16, 4 or 1 compressed tokens (96/16 = 6x at the low end, 480/1 = 480x at the high end).  
  value: `1, 4, 16 tokens; 96-480 tokens` metric: compression ratio task: Arxiv Corpus / ArxivQA conditions: LLaMa-3-8b-chat  
  source: 500x-compressor.txt p.4 Sec. 4.1  
  quote: `Compressed tokens numbering 1, 4, and 16 were used to compress 96, 192, 288, 384, and 480 tokens, achieving compression ratios from 6x to 480x`
- **XC-014** (limitation) Compressor input is about 500 tokens per compressed prompt (test texts 96-480 tokens); no longer-input results.  
  value: `~500 tokens` metric: tokens task:  conditions:   
  source: 500x-compressor.txt p.1 Sec. 1  
  quote: `This method compresses prompts of approximately 500 tokens into a minimum of one token`
- **XC-015** (limitation) Test abstracts are 96, 192, 288, 384 or 480 tokens long.  
  value: `96-480` metric: tokens task: Arxiv Corpus test conditions:   
  source: 500x-compressor.txt p.3 Sec. 3.1  
  quote: `stracts with lengths of at least 96, 192, 288, 384, and 480 tokens are selected and grouped to test the regeneration per- formance`
- **XC-016** (compression_ratio) Authors' claim: ratios significantly exceed previous work reporting less than 50x.  
  value: `< 50x (prior)` metric:  task:  conditions: claim by authors  
  source: 500x-compressor.txt p.2 Sec. 1  
  quote: `These ratios significantly surpass previous research, which reported ratios of less than 50x`
- **XC-017** (compression_ratio) Not all compressed tokens are used equally: regeneration quality is similar going from 16 to 4 tokens and drops noticeably at 1 token.  
  value: `` metric: ROUGE-L-F task: Arxiv Corpus regeneration conditions: LLaMa-3-8b-chat  
  source: 500x-compressor.txt p.5 Sec. 4.3  
  quote: `When the number of compressed tokens decreases from 16 to 4, the regenerated texts by 500xCompressor exhibit similar Rouge-l-f scores`
- **XC-018** (context_loss) Gold standard 'Instruct' (full uncompressed context plus instruction): the baseline for the capability percentages. Table 2 columns per header: ArxivQA F1, EM; SQuAD F1, EM; RE (relation extraction) F1, EM; HotpotQA F1, EM; RACE F1, EM; Average F1, EM. Row labels in the raw text lost the multiplication sign and subscript: '50016' = 500xCompressor with 16 compressed tokens, '5004' = 4 tokens, '5001' = 1 token.  
  value: `55.90 13.74 70.65 36.79 71.36 53.15 69.37 43.19 39.52 13.94 61.36 32.16` metric: F1; EM task: ArxivQA, SQuAD, RE, HotpotQA, RACE conditions: LLaMa-3-8b-chat, full context + instruction  
  source: 500x-compressor.txt p.6 Table 2  
  quote: `Instruct 55.90 13.74 70.65 36.79 71.36 53.15 69.37 43.19 39.52 13.94 61.36 32.16`
- **XC-019** (context_loss) Gold standard 'Zero-shot' (full context, no instruction). Table 2 columns per header: ArxivQA F1, EM; SQuAD F1, EM; RE (relation extraction) F1, EM; HotpotQA F1, EM; RACE F1, EM; Average F1, EM. Row labels in the raw text lost the multiplication sign and subscript: '50016' = 500xCompressor with 16 compressed tokens, '5004' = 4 tokens, '5001' = 1 token.  
  value: `28.41 0.04 29.95 1.02 25.75 1.39 29.32 3.42 15.31 0.59 25.75 1.29` metric: F1; EM task: ArxivQA, SQuAD, RE, HotpotQA, RACE conditions: LLaMa-3-8b-chat, full context, no instruction  
  source: 500x-compressor.txt p.6 Table 2  
  quote: `Zero-shot 28.41 0.04 29.95 1.02 25.75 1.39 29.32 3.42 15.31 0.59 25.75 1.29`
- **XC-020** (context_loss) 500xCompressor, 16 compressed tokens. Table 2 columns per header: ArxivQA F1, EM; SQuAD F1, EM; RE (relation extraction) F1, EM; HotpotQA F1, EM; RACE F1, EM; Average F1, EM. Row labels in the raw text lost the multiplication sign and subscript: '50016' = 500xCompressor with 16 compressed tokens, '5004' = 4 tokens, '5001' = 1 token.  
  value: `40.77 14.00 50.01 28.59 68.73 50.44 41.68 22.99 35.42 10.97 45.32 25.40` metric: F1; EM task: ArxivQA, SQuAD, RE, HotpotQA, RACE conditions: LLaMa-3-8b-chat, 16 tokens  
  source: 500x-compressor.txt p.6 Table 2  
  quote: `Ours (50016) 40.77 14.00 50.01 28.59 68.73 50.44 41.68 22.99 35.42 10.97 45.32 25.40`
- **XC-021** (context_loss) ICAE baseline, 16 compressed tokens. Table 2 columns per header: ArxivQA F1, EM; SQuAD F1, EM; RE (relation extraction) F1, EM; HotpotQA F1, EM; RACE F1, EM; Average F1, EM. Row labels in the raw text lost the multiplication sign and subscript: '50016' = 500xCompressor with 16 compressed tokens, '5004' = 4 tokens, '5001' = 1 token.  
  value: `38.70 13.44 51.94 30.37 65.94 44.64 42.11 24.57 23.69 9.49 44.48 24.50` metric: F1; EM task: ArxivQA, SQuAD, RE, HotpotQA, RACE conditions: LLaMa-3-8b-chat, ICAE 16 tokens  
  source: 500x-compressor.txt p.6 Table 2  
  quote: `ICAE (50016) 38.70 13.44 51.94 30.37 65.94 44.64 42.11 24.57 23.69 9.49 44.48 24.50`
- **XC-022** (context_loss) Difference (500xCompressor minus ICAE) at 16 tokens: negative on SQuAD and HotpotQA, so the method is not uniformly better. Delta symbol lost in raw text; row follows the 16-token ICAE row.  
  value: `2.06 0.56 -1.92 -1.78 2.79 5.80 -0.42 -1.57 1.73 1.48 0.84 0.89` metric: F1; EM delta task: ArxivQA, SQuAD, RE, HotpotQA, RACE conditions: LLaMa-3-8b-chat  
  source: 500x-compressor.txt p.6 Table 2  
  quote: `2.06 0.56 -1.92 -1.78 2.79 5.80 -0.42 -1.57 1.73 1.48 0.84 0.89`
- **XC-023** (context_loss) 500xCompressor, 4 compressed tokens. Table 2 columns per header: ArxivQA F1, EM; SQuAD F1, EM; RE (relation extraction) F1, EM; HotpotQA F1, EM; RACE F1, EM; Average F1, EM. Row labels in the raw text lost the multiplication sign and subscript: '50016' = 500xCompressor with 16 compressed tokens, '5004' = 4 tokens, '5001' = 1 token.  
  value: `38.30 10.64 49.66 27.54 63.72 45.69 36.86 19.69 21.49 7.86 42.00 22.28` metric: F1; EM task: ArxivQA, SQuAD, RE, HotpotQA, RACE conditions: LLaMa-3-8b-chat, 4 tokens  
  source: 500x-compressor.txt p.6 Table 2  
  quote: `Ours (5004) 38.30 10.64 49.66 27.54 63.72 45.69 36.86 19.69 21.49 7.86 42.00 22.28`
- **XC-024** (context_loss) ICAE baseline, 4 compressed tokens (ICAE beats 500xCompressor on RE, HotpotQA at 4 tokens). Table 2 columns per header: ArxivQA F1, EM; SQuAD F1, EM; RE (relation extraction) F1, EM; HotpotQA F1, EM; RACE F1, EM; Average F1, EM. Row labels in the raw text lost the multiplication sign and subscript: '50016' = 500xCompressor with 16 compressed tokens, '5004' = 4 tokens, '5001' = 1 token.  
  value: `33.31 7.54 47.48 26.49 67.28 50.91 40.39 23.75 20.06 6.82 41.70 23.10` metric: F1; EM task: ArxivQA, SQuAD, RE, HotpotQA, RACE conditions: LLaMa-3-8b-chat, ICAE 4 tokens  
  source: 500x-compressor.txt p.6 Table 2  
  quote: `ICAE (5004) 33.31 7.54 47.48 26.49 67.28 50.91 40.39 23.75 20.06 6.82 41.70 23.10`
- **XC-025** (context_loss) Difference (500xCompressor minus ICAE) at 4 tokens; negative on RE, HotpotQA and the EM average.  
  value: `4.98 3.10 2.17 1.05 -3.56 -5.22 -3.53 -4.06 1.43 1.03 0.30 -0.81` metric: F1; EM delta task: ArxivQA, SQuAD, RE, HotpotQA, RACE conditions: LLaMa-3-8b-chat  
  source: 500x-compressor.txt p.6 Table 2  
  quote: `4.98 3.10 2.17 1.05 -3.56 -5.22 -3.53 -4.06 1.43 1.03 0.30 -0.81`
- **XC-026** (context_loss) 500xCompressor, 1 compressed token (the extreme setting). Table 2 columns per header: ArxivQA F1, EM; SQuAD F1, EM; RE (relation extraction) F1, EM; HotpotQA F1, EM; RACE F1, EM; Average F1, EM. Row labels in the raw text lost the multiplication sign and subscript: '50016' = 500xCompressor with 16 compressed tokens, '5004' = 4 tokens, '5001' = 1 token.  
  value: `29.73 10.60 42.86 22.75 63.09 45.31 37.47 21.13 21.75 7.56 38.98 21.47` metric: F1; EM task: ArxivQA, SQuAD, RE, HotpotQA, RACE conditions: LLaMa-3-8b-chat, 1 token  
  source: 500x-compressor.txt p.6 Table 2  
  quote: `Ours (5001) 29.73 10.60 42.86 22.75 63.09 45.31 37.47 21.13 21.75 7.56 38.98 21.47`
- **XC-027** (context_loss) ICAE baseline, 1 compressed token. Table 2 columns per header: ArxivQA F1, EM; SQuAD F1, EM; RE (relation extraction) F1, EM; HotpotQA F1, EM; RACE F1, EM; Average F1, EM. Row labels in the raw text lost the multiplication sign and subscript: '50016' = 500xCompressor with 16 compressed tokens, '5004' = 4 tokens, '5001' = 1 token.  
  value: `20.50 3.40 27.20 10.66 44.46 27.10 22.44 9.38 13.71 4.16 25.66 10.94` metric: F1; EM task: ArxivQA, SQuAD, RE, HotpotQA, RACE conditions: LLaMa-3-8b-chat, ICAE 1 token  
  source: 500x-compressor.txt p.6 Table 2  
  quote: `ICAE (5001) 20.50 3.40 27.20 10.66 44.46 27.10 22.44 9.38 13.71 4.16 25.66 10.94`
- **XC-028** (context_loss) Difference (500xCompressor minus ICAE) at 1 token: positive everywhere.  
  value: `9.23 7.20 15.66 12.09 18.62 18.21 15.02 11.74 8.03 3.40 13.31 10.53` metric: F1; EM delta task: ArxivQA, SQuAD, RE, HotpotQA, RACE conditions: LLaMa-3-8b-chat  
  source: 500x-compressor.txt p.6 Table 2  
  quote: `9.23 7.20 15.66 12.09 18.62 18.21 15.02 11.74 8.03 3.40 13.31 10.53`
- **XC-029** (context_loss) Table 2 caption says the first lines are gold standards (the raw text shows two gold rows: Zero-shot and Instruct; the caption's 'three' may count the header).  
  value: `` metric:  task:  conditions:   
  source: 500x-compressor.txt p.6 Table 2 caption  
  quote: `The first three lines represent gold stan- dards`
- **XC-030** (context_loss) Gold standards: zero-shot full context and instruct full context.  
  value: `` metric:  task:  conditions:   
  source: 500x-compressor.txt p.3 Sec. 3.2  
  quote: `Two gold standards were used: zero-shot full context and instruct full context`
- **XC-031** (context_loss) Zero-shot gold standard gives the whole text without instructions; Instruct gives instructions.  
  value: `` metric:  task:  conditions:   
  source: 500x-compressor.txt p.3 Sec. 3.2  
  quote: `For zero-shot full context, the entire text was given to the LLM without instruction to guide the ex- tractive QA tasks`
- **XC-032** (context_loss) Abstract: the LLM retained 62.26-72.89% of its capabilities versus non-compressed prompts.  
  value: `62.26-72.89%` metric: % of capability task: five QA benchmarks conditions: LLaMa-3-8b-chat  
  source: 500x-compressor.txt p.1 Abstract  
  quote: `retained 62.26-72.89% of its capabilities compared to using non-compressed prompts`
- **XC-033** (context_loss) Table 5 is the 'normalized' table that produces the abstract's percentages; its normalisation basis is not stated in the text (the Instruct row is fixed at 100, consistent with normalising to the Instruct full-context scores of Table 2).  
  value: `` metric:  task:  conditions:   
  source: 500x-compressor.txt p.10 Table 5 caption  
  quote: `Table 5: Normalized evaluation results across five benchmarks focusing on various capabilities`
- **XC-034** (context_loss) Normalised Instruct row = 100 for every column. Table 5 (normalised; same column order as Table 2; values are % of the 'Instruct' full-context score, which is fixed at 100). Row labels '50016', '5004', '5001' = 16, 4, 1 compressed tokens.  
  value: `100 for all columns` metric: % of Instruct task: five QA benchmarks conditions: LLaMa-3-8b-chat  
  source: 500x-compressor.txt p.10 Table 5  
  quote: `Instruct 100 100 100 100 100 100 100 100 100 100 100 100`
- **XC-035** (context_loss) Normalised Zero-shot full-context gold standard: average F1 42.06 (so the compressed model beats no-instruction full context). Table 5 (normalised; same column order as Table 2; values are % of the 'Instruct' full-context score, which is fixed at 100). Row labels '50016', '5004', '5001' = 16, 4, 1 compressed tokens.  
  value: `50.82 0.29 42.39 2.77 36.08 2.61 42.27 7.92 38.74 4.25 42.06 3.57` metric: % of Instruct (F1; EM) task: five QA benchmarks conditions: LLaMa-3-8b-chat  
  source: 500x-compressor.txt p.10 Table 5  
  quote: `Zero-shot 50.82 0.29 42.39 2.77 36.08 2.61 42.27 7.92 38.74 4.25 42.06 3.57`
- **XC-036** (context_loss) 500xCompressor with 16 tokens retains 72.89% (average F1) and 81.29% (average EM) of Instruct full-context; this is the upper end of the abstract range. Table 5 (normalised; same column order as Table 2; values are % of the 'Instruct' full-context score, which is fixed at 100). Row labels '50016', '5004', '5001' = 16, 4, 1 compressed tokens.  
  value: `72.93 101 70.79 77.70 96.31 94.89 60.09 53.23 64.34 78.72 72.89 81.29` metric: % of Instruct (F1; EM) task: five QA benchmarks conditions: LLaMa-3-8b-chat, 16 tokens  
  source: 500x-compressor.txt p.10 Table 5  
  quote: `Ours (50016) 72.93 101 70.79 77.70 96.31 94.89 60.09 53.23 64.34 78.72 72.89 81.29`
- **XC-037** (context_loss) ICAE with 16 tokens retains 71.16% (average F1). Table 5 (normalised; same column order as Table 2; values are % of the 'Instruct' full-context score, which is fixed at 100). Row labels '50016', '5004', '5001' = 16, 4, 1 compressed tokens.  
  value: `69.23 97.81 73.51 82.56 92.40 83.98 60.70 56.88 59.95 68.08 71.16 77.86` metric: % of Instruct (F1; EM) task: five QA benchmarks conditions: LLaMa-3-8b-chat, ICAE 16 tokens  
  source: 500x-compressor.txt p.10 Table 5  
  quote: `ICAE (50016) 69.23 97.81 73.51 82.56 92.40 83.98 60.70 56.88 59.95 68.08 71.16 77.86`
- **XC-038** (context_loss) 500xCompressor with 4 tokens retains 67.12% (average F1). Table 5 (normalised; same column order as Table 2; values are % of the 'Instruct' full-context score, which is fixed at 100). Row labels '50016', '5004', '5001' = 16, 4, 1 compressed tokens.  
  value: `68.51 77.43 70.29 74.87 89.29 85.96 53.13 45.58 54.38 56.38 67.12 68.04` metric: % of Instruct (F1; EM) task: five QA benchmarks conditions: LLaMa-3-8b-chat, 4 tokens  
  source: 500x-compressor.txt p.10 Table 5  
  quote: `Ours (5004) 68.51 77.43 70.29 74.87 89.29 85.96 53.13 45.58 54.38 56.38 67.12 68.04`
- **XC-039** (context_loss) ICAE with 4 tokens retains 66.01% (average F1). Table 5 (normalised; same column order as Table 2; values are % of the 'Instruct' full-context score, which is fixed at 100). Row labels '50016', '5004', '5001' = 16, 4, 1 compressed tokens.  
  value: `59.58 54.87 67.21 71.99 94.28 95.78 58.23 55.00 50.75 48.93 66.01 65.32` metric: % of Instruct (F1; EM) task: five QA benchmarks conditions: LLaMa-3-8b-chat, ICAE 4 tokens  
  source: 500x-compressor.txt p.10 Table 5  
  quote: `ICAE (5004) 59.58 54.87 67.21 71.99 94.28 95.78 58.23 55.00 50.75 48.93 66.01 65.32`
- **XC-040** (context_loss) 500xCompressor with 1 token retains 62.26% (average F1) and 65.48% (average EM): the lower end of the abstract range; ArxivQA F1 only 53.18% of Instruct. Table 5 (normalised; same column order as Table 2; values are % of the 'Instruct' full-context score, which is fixed at 100). Row labels '50016', '5004', '5001' = 16, 4, 1 compressed tokens.  
  value: `53.18 77.14 60.66 61.84 88.40 85.25 54.01 48.92 55.03 54.25 62.26 65.48` metric: % of Instruct (F1; EM) task: five QA benchmarks conditions: LLaMa-3-8b-chat, 1 token  
  source: 500x-compressor.txt p.10 Table 5  
  quote: `Ours (5001) 53.18 77.14 60.66 61.84 88.40 85.25 54.01 48.92 55.03 54.25 62.26 65.48`
- **XC-041** (context_loss) ICAE with 1 token retains only 40.90% (average F1). Table 5 (normalised; same column order as Table 2; values are % of the 'Instruct' full-context score, which is fixed at 100). Row labels '50016', '5004', '5001' = 16, 4, 1 compressed tokens.  
  value: `36.67 24.74 38.50 28.97 62.30 50.98 32.35 21.73 34.70 29.83 40.90 31.25` metric: % of Instruct (F1; EM) task: five QA benchmarks conditions: LLaMa-3-8b-chat, ICAE 1 token  
  source: 500x-compressor.txt p.10 Table 5  
  quote: `ICAE (5001) 36.67 24.74 38.50 28.97 62.30 50.98 32.35 21.73 34.70 29.83 40.90 31.25`
- **XC-042** (context_loss) Authors' text: on ArxivQA 500xCompressor beats ICAE by 2.06-9.23 (reported with % sign) in F1 and 0.56-7.20 in EM; these equal the Table 2 deltas in absolute points.  
  value: `2.06-9.23; 0.56-7.20` metric: F1; EM task: ArxivQA conditions: LLaMa-3-8b-chat  
  source: 500x-compressor.txt p.4 Sec. 4.2  
  quote: `500xCompressor outperforms ICAE on the ArxivQA dataset, showing improvements of 2.06-9.23% in F1 score and 0.56-7.20% in EM`
- **XC-043** (context_loss) At 1 token the largest gain over ICAE is 18.62 points F1 on relation extraction.  
  value: `18.62` metric: F1 task: RE conditions: LLaMa-3-8b-chat, 1 token  
  source: 500x-compressor.txt p.5 Sec. 4.2  
  quote: `compression, 500xCompressor surpasses ICAE across all benchmarks, with the most significant improvement being an 18.62% increase in F1 score for relation extraction`
- **XC-044** (context_loss) Authors concede the advantage over ICAE does not hold consistently outside information extraction.  
  value: `` metric:  task:  conditions: LLaMa-3-8b-chat  
  source: 500x-compressor.txt p.5 Sec. 4.2  
  quote: `For information extraction, higher com- pression ratios accentuate the advantage of 500xCompres- sor. However, this trend does not consistently hold for other benchmarks`
- **XC-045** (context_loss) Anomaly: HotpotQA and RACE scores improve when going from 4 to 1 compressed token.  
  value: `` metric:  task: HotpotQA; RACE conditions: LLaMa-3-8b-chat  
  source: 500x-compressor.txt p.5 Sec. 4.2  
  quote: `No- tably, the performance of 500xCompressor even improves in HotpotQA and RACE from 5004 to 5001, despite the quadrupled compression ratio`
- **XC-046** (context_loss) Regeneration (text reconstruction) quality is reported only as ROUGE-L-F / BLEU differences over ICAE in text; the absolute scores are in Figure 3 only (not in the text).  
  value: `12.18% to 18.96%` metric: ROUGE-L-F difference vs ICAE task: Arxiv Corpus regeneration conditions: LLaMa-3-8b-chat  
  source: 500x-compressor.txt p.4 Sec. 4.1  
  quote: `The Rouge-l-f for 500xCompressor exceed those for ICAE at all compression ratios, with differences ranging from 12.18% to 18.96%`
- **XC-047** (context_loss) BLEU difference vs ICAE for regeneration.  
  value: `12.41% to 26.50%` metric: BLEU difference vs ICAE task: Arxiv Corpus regeneration conditions: LLaMa-3-8b-chat  
  source: 500x-compressor.txt p.4 Sec. 4.1  
  quote: `Similarly, the BLEU score differences range from 12.41% to 26.50%`
- **XC-048** (context_loss) Regeneration quality falls quickly with fewer compressed tokens.  
  value: `` metric:  task: Arxiv Corpus regeneration conditions: LLaMa-3-8b-chat  
  source: 500x-compressor.txt p.4 Sec. 4.1  
  quote: `When the number of compressed tokens is small, the qual- ity of the regenerated text decreases rapidly`
- **XC-049** (context_loss) Regenerated text is not exact: at 96 tokens into 4 tokens, 500xCompressor changes terms (e.g. 'Kato modules ... complexes' swapped). Quote is the 500xCompressor column of Table 1.  
  value: `` metric:  task: Arxiv abstract, 96 tokens -> 4 tokens conditions: LLaMa-3-8b-chat  
  source: 500x-compressor.txt p.5 Table 1  
  quote: `that Kato modules of logarithmic de Rham-Witt complexes satisfy functo- rial properties similar to Rost's cycle complexes`
- **XC-050** (limitation) Authors acknowledge regeneration errors on specific terms: 'Kato modules' regenerated instead of 'Kato complexes'.  
  value: `` metric:  task: Arxiv abstract conditions: LLaMa-3-8b-chat  
  source: 500x-compressor.txt p.4 Sec. 4.2  
  quote: `500xCompres- sor incorrectly regenerates "Kato modules" instead of "Kato complexes"`
- **XC-051** (limitation) Table 1 caption lists the error types that occur in outputs: mistakes, information loss, hallucinations and paraphrasing.  
  value: `` metric:  task:  conditions: LLaMa-3-8b-chat  
  source: 500x-compressor.txt p.5 Table 1 caption  
  quote: `Differences between the gold standard and the output include mistakes (red, containing incorrect text), information loss (yellow and italic, missing some text)`
- **XC-052** (context_loss) Authors claim a 'drill down analysis' shows proper nouns, names and numbers can be accurately compressed and retrieved; no dedicated drill-down table or numbers appear in this version of the text, only the single Table 1 example.  
  value: `` metric:  task:  conditions: claim by authors  
  source: 500x-compressor.txt p.2 Sec. 1  
  quote: `Drill down analy- sis demonstrates that complex information, such as proper nouns, special names, and numbers, could be accurately compressed and retrieved`
- **XC-053** (limitation) Text regeneration is scored only with ROUGE-L-F and BLEU; no exact-match rate of regenerated text is reported (EM is used only for QA answers).  
  value: `not reported` metric: exact match of regenerated text task: Arxiv Corpus regeneration conditions: LLaMa-3-8b-chat  
  source: 500x-compressor.txt p.3 Sec. 3.3  
  quote: `Rouge-l-f (Recall-Oriented Understudy for Gisting Evalu- ation) and BLEU (Bilingual Evaluation Understudy) scores were used to evaluate the difference between the regenerated text and the original text`
- **XC-054** (limitation) Only baseline is ICAE (a soft-prompt method); no comparison with hard-prompt/token-pruning methods or with Gist/AutoCompressor results.  
  value: `` metric:  task:  conditions:   
  source: 500x-compressor.txt p.3 Sec. 3.2  
  quote: `Considering the soft prompt methods and no fine-tuning for decoding, ICAE was chosen as the baseline`
- **XC-055** (latency_compute) Inference speed-up is not measured: authors assume it equals ICAE's for equal numbers of compressed tokens.  
  value: `not reported` metric:  task:  conditions:   
  source: 500x-compressor.txt p.7 Sec. 5  
  quote: `Both 500xCompressor and ICAE exhibit similar improve- ments in inference speed by compressing natural language tokens into a small number of compressed tokens`
- **XC-056** (latency_compute) Explicitly states inference-speed improvements are not analysed.  
  value: `not reported` metric:  task:  conditions:   
  source: 500x-compressor.txt p.7 Sec. 5  
  quote: `Therefore, inference speed im- provements are not analyzed in this paper`
- **XC-057** (latency_compute) Qualitative claim only: replacing many text tokens by few compressed tokens speeds up answering.  
  value: `` metric:  task:  conditions:   
  source: 500x-compressor.txt p.3 Sec. 2.2  
  quote: `By replacing the original text tokens with compressed to- kens, the speed of answering questions is increased`
- **XC-058** (cost) Training schedule: total steps per setting (pretraining 16/4/1 tokens then fine-tuning 16/4/1), warm-up, learning rate, batch size 4. Column order per Table 3 header.  
  value: `pretrain 42000/66600/103800 steps; finetune 20000/15000/10000 steps; lr 1e-4 then 5e-5; batch 4` metric: steps task: Arxiv Corpus; ArxivQA conditions: 16 / 4 / 1 compressed tokens  
  source: 500x-compressor.txt p.9 Table 3  
  quote: `Total steps 42000 66600 103800 20000 15000 10000 Warm-up steps 300 300 300 300 300 300 Learning rate 1e-4 1e-4 1e-4 5e-5 5e-5 5e-5 Batch size 4 4 4 4 4 4`
- **XC-059** (cost) Training data size: Arxiv Corpus 2,353,924 train abstracts; ArxivQA 250,000 train QA pairs, 5,000 test pairs (columns Train/Dev/Test per Table 4).  
  value: `2353924; 250000` metric: records task: Arxiv Corpus; ArxivQA conditions:   
  source: 500x-compressor.txt p.9 Table 4  
  quote: `Number of data records 2353924 3000 2500 250000 2500 5000`
- **XC-060** (hardware) GPU type, GPU count, memory and wall-clock training time are not reported; the closest content is the training-parameter table.  
  value: `not reported` metric:  task:  conditions:   
  source: 500x-compressor.txt p.9 Table 3 caption  
  quote: `Table 3: Training parameters for 500xCompressor and ICAE`
- **XC-061** (limitation) Authors' admitted limitation: pretrained/fine-tuned on relatively small corpora and QA datasets (Arxiv abstracts, ArxivQA).  
  value: `` metric:  task:  conditions:   
  source: 500x-compressor.txt p.7 Sec. 7 Conclusions  
  quote: `Although 500xCompressor has shown good generalization ability on downstream tasks, it was pretrained and fine-tuned on rel- atively small corpora and QA datasets`
- **XC-062** (limitation) There is no dedicated limitations section; the future-work paragraph of the Conclusions is the nearest.  
  value: `not reported` metric:  task:  conditions:   
  source: 500x-compressor.txt p.7 Sec. 7 Conclusions  
  quote: `Future work would involve more extensive experi- ments and exploration of additional applications`
- **XC-063** (limitation) Applications like in-context learning, reasoning, personalised LLMs, RAG and role-playing are listed as future work, i.e. not evaluated.  
  value: `` metric:  task:  conditions:   
  source: 500x-compressor.txt p.7 Sec. 7 Conclusions  
  quote: `compressed texts could be applied in var- ious contexts, including in-context learning, reasoning, per- sonalized LLMs, RAG, and even role-playing`
- **XC-064** (limitation) Abstract: not all compressed tokens are equally utilised.  
  value: `` metric:  task:  conditions:   
  source: 500x-compressor.txt p.1 Abstract  
  quote: `This study also shows that not all the compressed tokens are equally utilized`
- **XC-065** (reproducibility) Paper states code, datasets, models and demo are open-sourced on GitHub.  
  value: `` metric:  task:  conditions:   
  source: 500x-compressor.txt p.7 Availability Statement  
  quote: `The code, datasets, models, and demo related to this study have been uploaded to the open source community at https://github.com/ZongqianLi/500xCompressor`
- **XC-066** (reproducibility) Official repo README (via WebFetch): licensed CC BY 4.0. Quote as returned by WebFetch.  
  value: `CC BY 4.0` metric:  task:  conditions:   
  source: https://github.com/ZongqianLi/500xCompressor GitHub README (WebFetch)  
  quote: `licensed under the Creative Commons Attribution 4.0 International License`
- **XC-067** (reproducibility) Official repo README (via WebFetch): Hugging Face datasets and models exist but are not open to the public, which conflicts with the paper's 'open source community' wording. Quote as returned by WebFetch.  
  value: `` metric:  task:  conditions:   
  source: https://github.com/ZongqianLi/500xCompressor GitHub README (WebFetch)  
  quote: `Datasets and models were uploaded to Huggingface but are not open to the public.`
- **XC-068** (reproducibility) Official repo README (via WebFetch): released models are LoRA adapters on LLaMa-3-8b-Instruct (paper text says LLaMa-3-8b-chat). Quote as returned by WebFetch.  
  value: `LLaMa-3-8b-Instruct` metric:  task:  conditions:   
  source: https://github.com/ZongqianLi/500xCompressor GitHub README (WebFetch)  
  quote: `LLaMa-3-8b-Instruct`
- **XC-069** (reproducibility) Official repo README (via WebFetch) says the paper was accepted at ACL 2025 Main; the supplied paper text (arXiv v1, 6 Aug 2024) states no venue. Quote as returned by WebFetch.  
  value: `ACL 2025 Main` metric:  task:  conditions:   
  source: https://github.com/ZongqianLi/500xCompressor GitHub README (WebFetch)  
  quote: `The paper was accepted by ACL 2025 Main.`
- **XC-070** (reproducibility) Paper title and affiliation (University of Cambridge).  
  value: `` metric:  task:  conditions:   
  source: 500x-compressor.txt p.1 title page  
  quote: `500xCompressor: Generalized Prompt Compression for Large Language Models Zongqian Li1, Yixuan Su1, Nigel Collier1 1University of Cambridge`
- **XC-071** (reproducibility) arXiv stamp of the supplied text: v1, 6 Aug 2024 (no venue string).  
  value: `2408.03094v1` metric:  task:  conditions:   
  source: 500x-compressor.txt p.1 title page stamp  
  quote: `arXiv:2408.03094v1 [cs.CL] 6 Aug 2024`
- **XC-072** (tasks_tested) Benchmarks: ArxivQA and SQuAD (information extraction), RelationExtraction (relation extraction).  
  value: `` metric: F1; EM task: ArxivQA, SQuAD, RE conditions:   
  source: 500x-compressor.txt p.3 Sec. 3.1  
  quote: `ArxivQA and SQuAD (Rajpurkar et al. 2016) for information extrac- tion, RelationExtraction (Levy et al. 2017) for relation ex- traction`
- **XC-073** (tasks_tested) Benchmarks (cont.): HotpotQA (multi-hop reasoning) and RACE (reading comprehension).  
  value: `` metric: F1; EM task: HotpotQA, RACE conditions:   
  source: 500x-compressor.txt p.3 Sec. 3.1  
  quote: `HotpotQA (Yang et al. 2018) for multi-hop reason- ing, and RACE (Lai et al. 2017) for reading comprehension`
- **XC-074** (tasks_tested) Only the five extractive-QA benchmarks plus Arxiv-abstract regeneration were evaluated; not tested: coding, multi-turn chat, summarization, structured data (JSON/tables/logs), math reasoning, PII/sensitive content, long documents beyond ~500 tokens; RAG listed only as future work (XC-063).  
  value: `not tested in paper` metric:  task: coding; long-document QA/RAG; multi-turn chat; summarization; structured data; reasoning/math; sensitive/PII conditions: dataset list quoted  
  source: 500x-compressor.txt p.3 Sec. 3.1  
  quote: `five benchmarks were used to eval- uate the compression models for various abilities: ArxivQA and SQuAD (Rajpurkar et al. 2016) for information extrac- tion`
- **XC-075** (tasks_tested) Evaluation texts (Arxiv Corpus and ArxivQA test) were published after January 2024, so they postdate LLaMA-3's training data (strict unseen design); SQuAD/RE/HotpotQA/RACE are classic datasets and may overlap with LLM training data.  
  value: `` metric:  task: Arxiv Corpus; ArxivQA conditions: LLaMa-3-8b-chat  
  source: 500x-compressor.txt p.2 Sec. 1  
  quote: `The evaluation texts in the Arxiv Corpus and ArxivQA dataset were published af- ter January 2024`

## ARTICLE

- **AR-001** (disagreement) RESOLVED: the three papers exist and are in the corpus (EHPC arXiv 2501.12959, H2O arXiv 2306.14048, SnapKV arXiv 2404.14469); see EH-001, H2-001, SK-001 for their method statements.  
  value: `` metric:  task:  conditions: repo article vs primary papers  
  source: attention-based-methods.md Note line 3  
  quote: `we were unable to locate the specific papers that introduced these methods`
- **AR-002** (disagreement) DISAGREES on grouping: the EHPC paper itself separates 'implicit' KV-cache methods (H2O, SnapKV) from 'explicit' token-reduction methods and puts EHPC in the explicit group that works on text (EH-028, EH-029, EH-030). H2O and SnapKV edit the serving model's KV cache (H2-010, SK-004).  
  value: `` metric:  task:  conditions: repo article vs primary papers  
  source: attention-based-methods.md Algorithm Overview  
  quote: `These methods include Evaluator Head-Based Prompt Compression (EHPC), H2O (Heavy-Hitter Oracle), and SnapKV`
- **AR-003** (disagreement) DISAGREES for EHPC: the article table labels all attention-based methods 'KV cache optimization', but EHPC outputs a shorter text prompt (EH-003, EH-021); only H2O and SnapKV optimize the KV cache (H2-001, SK-001).  
  value: `` metric:  task:  conditions: repo article vs primary papers  
  source: attention-based-methods.md Comparison table  
  quote: `| **Focus** | Prompt compression | KV cache optimization |`
- **AR-004** (disagreement) WRONG for EHPC, PARTLY right for others. EHPC is pre-processing: a separate local LLM pass over the prompt scores tokens, then the shortened prompt goes to the answering model (EH-091, EH-022). H2O evicts during decoding (H2-002, H2-006). SnapKV compresses once after the prompt is processed with no updates during decoding (SK-008, SK-066).  
  value: `` metric:  task:  conditions: repo article vs primary papers  
  source: attention-based-methods.md Comparison table  
  quote: `| **Processing Stage** | Pre-processing | During inference |`
- **AR-005** (disagreement) DISAGREES for H2O and SnapKV, qualified for EHPC: only EHPC's text output can be sent to an API model, and EHPC still needs a local LLM with attention access to score tokens (EH-020, EH-021). H2O needs a modified white-box engine (H2-010, H2-012); SnapKV needs edits inside the model's attention code and was tested only on open-weight models (SK-010, SK-012, SK-015).  
  value: `` metric:  task:  conditions: repo article vs primary papers  
  source: attention-based-methods.md Use Cases item 4  
  quote: `Compatible with black-box model access through APIs`
- **AR-006** (disagreement) DISAGREES for H2O and SnapKV, qualified for EHPC; same evidence as AR-005. The paper also does not state which target model produced EHPC's Table 4 results (EH-026) and gives no dollar-cost figures (EH-101).  
  value: `` metric:  task:  conditions: repo article vs primary papers  
  source: attention-based-methods.md Advantages item 6  
  quote: `Suitable for use with commercial APIs where model access is limited`
- **AR-007** (disagreement) NOT SUPPORTED as 'any' model: EHPC must re-identify evaluator heads per model via a pilot experiment (EH-009, EH-010) and was tested on Llama-3.1-8B, CodeLlama-7B, Phi-3.5-mini; H2O was validated on OPT, LLaMA, GPT-NeoX with the implementation built on an OPT white-box engine (H2-010, H2-050); SnapKV on LWM, LongChat, Mistral, Mixtral, Command-R and its repo supports Llama, Mistral, Mixtral (SK-012, SK-091).  
  value: `` metric:  task:  conditions: repo article vs primary papers  
  source: attention-based-methods.md Advantages item 4  
  quote: `Work with any Transformer-based model`
- **AR-008** (disagreement) SUPPORTED with caveats: EHPC is called training-free (EH-001) but needs a one-time pilot calibration per model on synthetic NIAH data (EH-007); SnapKV is fine-tuning-free (SK-001); H2O evaluates pre-trained models without training but does not use the phrase (H2-009).  
  value: `` metric:  task:  conditions: repo article vs primary papers  
  source: attention-based-methods.md EHPC Key Features  
  quote: `1. **Training-Free**: No additional training required`
- **AR-009** (disagreement) MIXED: only H2O does dynamic eviction while decoding (H2-006). SnapKV compresses once after prefill and does not update during decoding (SK-008). EHPC is a one-shot pre-processing step before inference (EH-091).  
  value: `` metric:  task:  conditions: repo article vs primary papers  
  source: attention-based-methods.md Advantages item 3  
  quote: `Dynamic compression during inference`
- **AR-010** (disagreement) PARTLY wrong: the EHPC abstract says it uses the first few layers up to the evaluator layer (EH-002) but the heads themselves sit in the middle layers (layer 13 of 32 for Llama-3.1-8B, layer 17 for Phi-3.5-mini) (EH-008, EH-009, EH-010).  
  value: `` metric:  task:  conditions: repo article vs primary papers  
  source: attention-based-methods.md EHPC section  
  quote: `EHPC identifies specific attention heads in early Transformer layers that naturally select important tokens.`
- **AR-011** (disagreement) PARTLY wrong: EHPC does not just keep top-scoring tokens; scores come from a few evaluator heads over an end-of-prompt observation window and neighbouring tokens are kept together by pooling (EH-005, EH-011, EH-012).  
  value: `` metric:  task:  conditions: repo article vs primary papers  
  source: attention-based-methods.md EHPC technical details  
  quote: `Skims input by selecting only tokens with high attention scores`
- **AR-012** (disagreement) INACCURATE: H2O keeps heavy hitters PLUS the most recent tokens, split evenly, and keeping only heavy hitters degrades quality (H2-003, H2-007). SnapKV keeps ALL tokens of the observation window plus pooled/clustered voted positions per head, and selecting only the highest weights is insufficient (SK-003, SK-006).  
  value: `` metric:  task:  conditions: repo article vs primary papers  
  source: attention-based-methods.md H2O and SnapKV section  
  quote: `retaining only high-attention tokens based on empirical observations that small token subsets account for majority attention weights`
- **AR-013** (disagreement) INACCURATE (same sentence in the repo README): see AR-012 for what H2O and SnapKV actually keep.  
  value: `` metric:  task:  conditions: repo article vs primary papers  
  source: README.md README section 4  
  quote: `retaining only high-attention tokens based on empirical observations that small token subsets account for majority attention weights`
- **AR-014** (disagreement) DISAGREES for H2O and SnapKV: both require changes inside the inference engine or model attention code (H2-010, SK-010). Only EHPC leaves the answering model unmodified (EH-021, EH-022) but needs its own local evaluator LLM (EH-020).  
  value: `` metric:  task:  conditions: repo article vs primary papers  
  source: attention-based-methods.md Performance Characteristics item 4  
  quote: `Work with existing models without modification`
- **AR-015** (disagreement) DISAGREES for H2O and SnapKV: they are unusable where model modification is not possible (H2-010, H2-012, SK-010, SK-015).  
  value: `` metric:  task:  conditions: repo article vs primary papers  
  source: attention-based-methods.md Significance item 1  
  quote: `Where model modification is not possible`
- **ART-001** (disagreement) Repo defect: article links arXiv:2403.11802, which is the Counting-Stars benchmark paper. The real LLMLingua-2 paper is arXiv:2403.12968 (L2-130); papers/llmlingua-2.pdf in the repo is the wrong document (verified by reading the repo PDF text: its first page reads Counting-Stars by Song et al.).  
  value: `` metric:  task:  conditions:   
  source: llmlingua-2.md repo article  
  quote: `[Paper (arXiv:2403.11802)](../papers/llmlingua-2.pdf)`
- **ART-002** (disagreement) Repo README lists the paper as 'Huang et al., arXiv:2403.11802, Dec 2024'; the real paper is first-authored by Zhuoshi Pan (L2-131 title page) with identifier arXiv:2403.12968 (L2-130). Author, id and date in the README are wrong.  
  value: `` metric:  task:  conditions:   
  source: README.md repo article  
  quote: `*Huang et al., arXiv:2403.11802, Dec 2024*`
- **ART-003** (disagreement) Article says 3x-6x faster than original LLMLingua. Paper abstract says 3x-6x faster than existing prompt compression methods (L2-077) and Table 5 shows compressor latency only on V100-32G on MeetingBank (L2-072, SC-T07); end-to-end speedup is 1.6x-2.9x at 2x-5x compression (L2-030, L2-071). Direction supported; scope is compression-step latency, not end-to-end.  
  value: `` metric:  task:  conditions:   
  source: llmlingua-2.md repo article  
  quote: `3. **Efficiency**: 3x-6x faster performance than original LLMLingua`
- **ART-004** (disagreement) Article says up to 20x compression with minimal performance loss. No 20x result exists in the paper: tested ratios in LLMLingua-2's own tables top out at 14x (GSM8K half-shot, L2-032) with 5x on LongBench (L2-034); 15x is only stated as possible when combined with LLMLingua's budget controller, without a results table (L2-031). Losses are not minimal on every task: LongBench Synth. 21.3 vs 37.8 original (L2-034, L2-043), NaturalQuestions question-agnostic below zero-shot (L2-059, L2-061).  
  value: `` metric:  task:  conditions:   
  source: llmlingua-2.md repo article  
  quote: `4. **Compression Ratio**: Achieves up to 20x compression with minimal performance loss`
- **ART-005** (disagreement) Article says maintains 90%+ performance at moderate compression. The paper makes no such statement (no '90%' anywhere). Its tables mix cases above and below that level (e.g. MeetingBank QA near parity L2-040/L2-042; LongBench AVG 39.1 vs 44.0 at 5x L2-034/L2-043; BBH 61.94 vs 70.07 at 5x L2-033/L2-049; NaturalQuestions 39.9-48.6 vs 54.1-75.7 L2-059/L2-060). Ratios of these numbers are extractor arithmetic, not paper claims.  
  value: `` metric:  task:  conditions:   
  source: llmlingua-2.md repo article  
  quote: `4. **Compression Quality**: Maintains 90%+ performance at moderate compression levels`
- **ART-006** (disagreement) Article says it requires teacher models like GPT-4 for training. Supported only in the sense that the training labels were distilled from GPT-4-32k (L2-008, L2-083); the paper states the resulting dataset is publicly released (L2-101) and inference needs no GPT-4 call (L2-082). Training the released recipe from scratch on a new domain would need a teacher again.  
  value: `` metric:  task:  conditions:   
  source: llmlingua-2.md repo article  
  quote: `1. **Data Distillation Dependency**: Requires access to high-quality teacher models (like GPT-4) for training`
- **ART-007** (disagreement) Article lists compressing lengthy code prompts as a use case. The paper has no code-specific experiment: the only code-related item is a 'Code' column in the LongBench table header whose contents and metric are not described (L2-112); training data is English meeting transcripts only (L2-090). On that column LLMLingua-2 scored 58.9 vs 54.2 original at 5x (L2-034, L2-043) while a no-context baseline scored 36.2 (L2-044).  
  value: `` metric:  task:  conditions:   
  source: llmlingua-2.md repo article  
  quote: `4. **Code Processing**: Compress lengthy code prompts for faster processing`
- **ART-008** (disagreement) Article says model-specific encoders are still required for optimal performance. The paper uses one compressor (xlm-roberta-large or mBERT, L2-003) trained once on MeetingBank, evaluated with two target LLMs (GPT-3.5-Turbo, Mistral-7B) without per-target retraining (L2-021, L2-023), and claims generalisation across LLMs. It does not say a target-specific encoder is needed (only two targets were tested).  
  value: `` metric:  task:  conditions:   
  source: llmlingua-2.md repo article  
  quote: `2. **Encoder Architecture**: Still requires model-specific encoders for optimal performance`
- **ART-009** (disagreement) Article lists chat history compression as a use case. The paper does not test multi-turn chat or conversation data at all (L2-114).  
  value: `` metric:  task:  conditions:   
  source: llmlingua-2.md repo article  
  quote: `3. **Chat Applications**: Speed up response times by compressing conversation history`
- **ART-010** (disagreement) Article says it mitigates lost-in-the-middle issues. In Table 11 question-agnostic LLMLingua-2 degrades steadily with answer-document position (48.6 to 39.9, L2-059) and sits below the original at the first position (L2-060) and below the zero-shot score (L2-061); only the question-aware hybrid LLMLingua-2+ exceeds the original at positions 5-20 (L2-062). The paper never claims to mitigate lost-in-the-middle.  
  value: `` metric:  task:  conditions:   
  source: llmlingua-2.md repo article  
  quote: `2. **Extended Context Support**: Mitigates "lost in the middle" issues in long prompts`
- **ART-011** (disagreement) Article says LLMLingua-2 is more robust than Gist Tokens and 500xCompressor out of domain. The paper compares only with Selective-Context, LLMLingua, SBERT, OpenAI embeddings, LongLLMLingua, BM25, Gzip and GPT-4 compression (L2-056 and tables); no Gist or 500xCompressor comparison exists.  
  value: `` metric:  task:  conditions:   
  source: llmlingua-2.md repo article  
  quote: `- More robust than both in out-of-domain scenarios`
- **ART-012** (disagreement) Article claims lower API costs from shorter prompt AND generation lengths. The paper reports prompt token counts only (L2-080, L2-081); it reports no generation length and no dollar cost (not reported).  
  value: `` metric:  task:  conditions:   
  source: llmlingua-2.md repo article  
  quote: `1. **Cost Efficiency**: Reduces both prompt and generation lengths, lowering API costs`
- **ART-013** (disagreement) Repo defect: article links arXiv:2502.14048, an unrelated paper by Villardar (Semantic Decomposition and Selective Context Filtering). The real Selective Context paper is Li et al., EMNLP 2023, arXiv:2310.06201 (SC-110, SC-111).  
  value: `` metric:  task:  conditions:   
  source: selective-context.md repo article  
  quote: `[Paper (arXiv:2502.14048)](../papers/selective-context.pdf)`
- **ART-014** (disagreement) README attributes Selective Context to 'Villardar, arXiv:2502.14048, Feb 2025'; the real paper is Li, Dong, Lin, Guerin, arXiv:2310.06201, Oct 2023 (SC-110, SC-111).  
  value: `` metric:  task:  conditions:   
  source: README.md repo article  
  quote: `*Villardar, arXiv:2502.14048, Feb 2025*`
- **ART-015** (disagreement) Article says Selective Context is currently limited to noun phrase boundaries. The paper supports token, phrase and sentence lexical units (SC-001, SC-009); noun-phrase merging via spaCy is its phrase-level implementation, found best (SC-056), and the authors list reliance on phrase-boundary detection and absence of verb phrases as a limitation (SC-080, SC-081). The 'noun-phrase-only' statement is a partial reading of a limitation, not a restriction on token/sentence modes.  
  value: `` metric:  task:  conditions:   
  source: selective-context.md repo article  
  quote: `- Currently limited to noun phrase boundaries for syntactic preservation`
- **ART-016** (disagreement) Article says Selective Context generally gets lower compression ratios than trained methods. The paper compares only against random deletion and the full context (no trained methods; SC-036 to SC-041) and treats the reduction ratio as a user-set parameter from 0.2 to 0.8 (SC-020); quality, not ratio, is what degrades at high reduction (SC-035, SC-050). In the LLMLingua-2 paper the SC baseline was run at the same ratios as other methods (SC-T01 to SC-T04), so the ratio is not inherently lower; its quality is lower there.  
  value: `` metric:  task:  conditions:   
  source: selective-context.md repo article  
  quote: `2. **Lower Compression Ratios**: Generally achieves lower compression than trained methods`
- **ART-017** (disagreement) Article calls the method parameter-free, standalone and lightweight. The paper needs a base causal LM forward pass (LLaMA-7B or GPT-3 curie, SC-003/SC-004) plus spaCy and NLTK; in the LLMLingua-2 paper's run the SC baseline used a LLaMA-2-7B SLM, 26.5GB GPU memory and 15.5-15.9 s in the MeetingBank latency table on a V100-32G (SC-T08, SC-T07, SC-T09). It is training-free, not model-free.  
  value: `` metric:  task:  conditions:   
  source: selective-context.md repo article  
  quote: `- **Parameter-Free Design**: No model training required, making it lightweight and accessible`
- **ART-018** (disagreement) Article says SpaCy syntactic parsing preserves grammatical structure. The paper uses spaCy only to merge tokens into noun chunks and shows filtered output that is not grammatical (SC-006, SC-008); dependency-tree filtering is only a speculated improvement (SC-081).  
  value: `` metric:  task:  conditions:   
  source: selective-context.md repo article  
  quote: `- **Syntactic Parsing**: Incorporates SpaCy syntactic parsing to preserve grammatical structure`
- **ART-A01** (disagreement) [CONTRADICTED] The paper exists: 'Adapting Language Models to Compress Contexts' (Chevalier, Wettig, Ajith, Chen; arXiv:2305.14788, EMNLP 2023 per the 500xCompressor reference list), with code at princeton-nlp/AutoCompressors. (paper ids: AC-080, AC-081, AC-087, AC-070)  
  value: `CONTRADICTED` metric:  task:  conditions: AutoCompressor article line 3  
  source: autocompressor.md repo article  
  quote: `we were unable to locate the specific paper that introduced this method`
- **ART-A02** (disagreement) [CONTRADICTED] 30,720 tokens is the fine-tuning/evaluation sequence length for OPT-1.3B/2.7B only (20 compression steps over 1,024-2,048-token segments), not a segment size; the Llama-2-7B AutoCompressor was trained on 6,144-token sequences. (paper ids: AC-012, AC-013, AC-014, AC-015, AC-008)  
  value: `CONTRADICTED` metric:  task:  conditions: AutoCompressor article line 7  
  source: autocompressor.md repo article  
  quote: `It processes segments up to 30,720 tokens by iteratively compressing sub-prompts and using summary vectors as soft prompts`
- **ART-A03** (disagreement) [SUPPORTED (qualified)] Training uses an unsupervised language-modelling objective, so no labels are needed, but it still requires fine-tuning the base LM (full fine-tune of OPT on 2B tokens; LoRA on Llama-2-7B with 15B tokens). (paper ids: AC-002, AC-006, AC-007, AC-008)  
  value: `SUPPORTED (qualified)` metric:  task:  conditions: AutoCompressor article line 16  
  source: autocompressor.md repo article  
  quote: `Works without requiring labeled training data`
- **ART-A04** (disagreement) [PARTIAL] Summary vectors beat 150-token plain ICL on 8/11 tasks and 750-token plain ICL on 8 tasks, but the fine-tuned Llama-2 AutoCompressor has substantially worse zero-shot accuracy on some tasks and slightly worse ICL than the Llama-2 initialisation (e.g. SST-2 zero-shot 67.7 vs 87.2); RTE/Subj stay better with 750 plain tokens. (paper ids: AC-038, AC-043, AC-046, AC-048, AC-049, AC-050, AC-051, AC-052)  
  value: `PARTIAL` metric:  task:  conditions: AutoCompressor article line 28  
  source: autocompressor.md repo article  
  quote: `Maintains performance on in-context learning tasks while reducing inference costs`
- **ART-A05** (disagreement) [NOT TESTED] No codebase-analysis task exists in the paper; GitHub appears only as one Pile/RedPajama subdomain in perplexity evaluation, with no per-domain numbers reported. (paper ids: AC-073, AC-074, AC-075, AC-082, AC-079)  
  value: `NOT TESTED` metric:  task:  conditions: AutoCompressor article line 70  
  source: autocompressor.md repo article  
  quote: `Working with large software codebases`
- **ART-A06** (disagreement) [NOT TESTED] No legal-document task exists in the paper; FreeLaw appears only as one Pile subdomain in perplexity evaluation, with no per-domain numbers reported. (paper ids: AC-073, AC-074, AC-079)  
  value: `NOT TESTED` metric:  task:  conditions: AutoCompressor article line 69  
  source: autocompressor.md repo article  
  quote: `Processing extensive legal briefs and case files`
- **ART-A07** (disagreement) [NOT STATED IN PAPER (consistent with mechanism)] Paper never discusses API/black-box LLMs; AutoCompressors are fine-tuned open LMs that emit and consume soft prompts, so API-only use is excluded by mechanism (inference). (paper ids: AC-004, AC-005)  
  value: `NOT STATED IN PAPER (consistent with mechanism)` metric:  task:  conditions: AutoCompressor article line 77  
  source: autocompressor.md repo article  
  quote: `Cannot work with black-box commercial LLMs accessed via APIs`
- **ART-A08** (disagreement) [PARTIAL] Paper reports throughput gains (1.7x vs REPLUG top-2 with 512-token passages) and says 'inexpensive'; it gives no dollar or end-to-end cost, and quality is below full-text retrieval at top-10 (REPLUG 8.30% vs Fused Summaries 3.74% perplexity gain). (paper ids: AC-055, AC-056, AC-057, AC-058, AC-065)  
  value: `PARTIAL` metric:  task:  conditions: AutoCompressor article line 62  
  source: autocompressor.md repo article  
  quote: `Dramatically reduces costs for long-form applications`
- **ART-A09** (disagreement) [NOT SUPPORTED] Longest tested context is 30,720 tokens; authors note summary accumulation is still quadratic in segment count and that summary vectors lose information relative to full attention. (paper ids: AC-012, AC-036, AC-067, AC-068)  
  value: `NOT SUPPORTED` metric:  task:  conditions: AutoCompressor article line 83  
  source: autocompressor.md repo article  
  quote: `Scales to arbitrary prompt lengths through recursive processing`
- **ART-CPC-01** (disagreement) PARTLY MISLEADING. Paper: 10.93x is the MEDIAN relative compression-stage time of LongLLMLingua vs CPC (avg 27.5x), measured on an A100 over a LongBench sample; it is not target-LLM inference speed, and the token-level LLMLingua-2 is faster than CPC (0.67x median). See CPC-34, CPC-36, CPC-39, CPC-38.  
  value: `10.93x` metric:  task:  conditions:   
  source: context-aware-prompt-compression.md Key Features 4  
  quote: `Achieves up to 10.93x faster inference compared to token-level methods`
- **ART-CPC-02** (disagreement) NOT SUPPORTED beyond ~6x. Paper tests 3,000/2,000-token budgets (about 3x and 5x; LongLLMLingua row 6x); no 10x. See CPC-08, CPC-17, CPC-18.  
  value: `2x-10x` metric:  task:  conditions:   
  source: context-aware-prompt-compression.md Performance Characteristics 4  
  quote: `Typically achieves 2x-10x compression while maintaining quality`
- **ART-CPC-03** (disagreement) SUPPORTED AS DESIGN PROPERTY, NOT MEASURED. CPC outputs original sentences and the authors state readability is preserved, but the paper reports no readability metric or human study. See CPC-06.  
  value: `` metric:  task:  conditions:   
  source: context-aware-prompt-compression.md Performance Characteristics 2  
  quote: `Maintains human readability better than token-based compressors`
- **ART-CPC-04** (disagreement) NOT SUPPORTED. Paper tests no legal data; medical content is PubMed paper summarization only (Rouge, no uncompressed baseline, no faithfulness metric, target LLM unstated); also CPC is question-conditioned. See CPC-24, CPC-47, CPC-60.  
  value: `` metric:  task:  conditions:   
  source: context-aware-prompt-compression.md Use Cases 2  
  quote: `Legal and Medical Document Processing**: Where meaning preservation is critical`
- **ART-CPC-05** (disagreement) REPO DEFECT. The paper exists: CPC is arXiv:2409.01227 (AAAI 2025, Liskavets et al., 'Prompt Compression with Context-Aware Sentence Encoding for Fast and Improved LLM Inference'; see CPC-52). The repo's papers/context-aware-prompting.pdf is a different Bosch manufacturing-knowledge paper (see ART-CPC-06).  
  value: `` metric:  task:  conditions:   
  source: context-aware-prompt-compression.md Note  
  quote: `we were unable to locate the specific paper that introduced this method`
- **ART-CPC-06** (disagreement) REPO DEFECT. README entry 8 links papers/context-aware-prompting.pdf, titled 'Enhancing Manufacturing Knowledge Access with LLMs and Context-aware Prompting' (knowledge-graph retrieval, Bosch authors); it is not the CPC compression paper (see ART-CPC-05 and CPC-52).  
  value: `` metric:  task:  conditions:   
  source: README.md Papers list item 8  
  quote: `Enhancing Manufacturing Knowledge Access with LLMs and Context-aware Prompting`
- **ART-CPC-07** (disagreement) CONTRADICTED. CPC needs a trained 7B-class LoRA encoder (single A100), whereas SCOPE is training-free; the 2024 CPC paper contains no comparison with SCOPE. See CPC-04, CPC-43, SCP-03.  
  value: `` metric:  task:  conditions:   
  source: context-aware-prompt-compression.md vs. Other Semantic Approaches  
  quote: `CPC generally offers better training efficiency and more principled approach to semantic preservation.`
- **ART-CPC-08** (disagreement) NOT SUPPORTED. The paper compares at equal token budgets and never states CPC achieves lower compression ratios than token-level methods (LongLLMLingua actually compresses slightly more at 2,000 tokens). See CPC-17, CPC-18.  
  value: `` metric:  task:  conditions:   
  source: context-aware-prompt-compression.md Limitations 2  
  quote: `Generally achieves lower compression ratios than token-level methods`
- **ART-CPC-09** (disagreement) INCOMPLETE. 'Context-aware' means sentence embeddings are computed in the context of the whole document, and compression REQUIRES the question (query-aware). The article never says CPC needs a question, which matters for summarization/chat uses. See CPC-01, CPC-02, CPC-48.  
  value: `` metric:  task:  conditions:   
  source: context-aware-prompt-compression.md Key Features 2  
  quote: `Considers the broader context when making compression decisions`
- **ART-G01** (disagreement) [PARTIAL] Paper reports up to 26x, but only for ~26-token instructions compressed into 1 gist token (Alpaca+ Human split), not documents; quality there is 'slight drops' (LLaMA ROUGE-L 23.9 vs 27.0, ChatGPT win 45.8%; FLAN-T5 win 42.5%). (paper ids: GT-009, GT-011, GT-012, GT-016, GT-020, GT-023, GT-028)  
  value: `PARTIAL` metric:  task:  conditions: Gist Tokens article line 27  
  source: gist-tokens.md repo article  
  quote: `Enables up to 26x compression ratios with minimal quality loss`
- **ART-G02** (disagreement) [PARTIAL] Paper's 40% FLOPs saving is against no caching, for a single decode step with a short prompt; against instruction (KV) caching in LLaMA-7B it is 0.11% FLOPs and ~1% wall time; wall time gain vs no caching is 4.2% (FLAN-T5) / 6.8% (LLaMA). (paper ids: GT-045, GT-046, GT-047, GT-048, GT-049, GT-050)  
  value: `PARTIAL` metric:  task:  conditions: Gist Tokens article line 63  
  source: gist-tokens.md repo article  
  quote: `Up to 40% reduction in computational requirements`
- **ART-G03** (disagreement) [PARTIAL] Human evaluation covered only 100 of the 252 Human-split prompts with 3 annotators each: LLaMA-7B gist win rate 52.3% (CI 46.1-58.4) vs the positive control, but FLAN-T5-XXL 40.6% (CI 34.6-46.8, below parity). Baseline is the instruction-finetuned positive control, not the original model. (paper ids: GT-026, GT-027, GT-028, GT-025)  
  value: `PARTIAL` metric:  task:  conditions: Gist Tokens article line 64  
  source: gist-tokens.md repo article  
  quote: `Minimal quality loss in human evaluations`
- **ART-G04** (disagreement) [NOT STATED IN PAPER (consistent with mechanism)] Paper never discusses black-box or API LLMs; the method requires finetuning the LM with gist masks and caching its KV activations, so API-only use is ruled out by mechanism (inference), not by a paper statement. (paper ids: GT-005, GT-008, GT-004)  
  value: `NOT STATED IN PAPER (consistent with mechanism)` metric:  task:  conditions: Gist Tokens article line 80  
  source: gist-tokens.md repo article  
  quote: `Cannot work with black-box commercial LLMs accessed via APIs`
- **ART-G05** (disagreement) [CONTRADICTED] The article links the wrong paper: arXiv:2401.09390 is not Gist Tokens. The real paper is 'Learning to Compress Prompts with Gist Tokens' by Mu, Li, Goodman, arXiv:2304.08467 (NeurIPS 2023). (paper ids: GT-060, GT-061, GT-067)  
  value: `CONTRADICTED` metric:  task:  conditions: Gist Tokens article line 3  
  source: gist-tokens.md repo article  
  quote: `[Paper (arXiv:2401.09390)](../papers/gist-tokens.pdf)`
- **ART-G06** (disagreement) [CONTRADICTED] README labels the PDF 'GIST: Generalizable In-Context Learning with Scalar Transformers' by 'Zhang et al.', arXiv:2401.09390; no such Gist paper exists in the supplied sources; the real title/authors/ID are in GT-060/GT-061. (paper ids: GT-060, GT-061)  
  value: `CONTRADICTED` metric:  task:  conditions: repo README.md lines 218-219  
  source: README.md repo article  
  quote: `**[GIST: Generalizable In-Context Learning with Scalar Transformers](./papers/gist-tokens.pdf)** *Zhang et al., arXiv:2401.09390, Jan 2024*`
- **ART-G07** (disagreement) [REPO DEFECT] The repo's papers/gist-tokens.pdf (text extract papers/gist-tokens.txt, page 1) is an unrelated mathematics paper on the nonlinear q-Bernstein operator of max-product kind, so the repo's Gist article cannot have been derived from it. (paper ids: GT-060)  
  value: `REPO DEFECT` metric:  task:  conditions: pdftotext default-mode extract in the research repo (outside the standard raw-mode set); page 1  
  source: gist-tokens.txt p.1 repo article  
  quote: `ON BETTER APPROXIMATION ORDER FOR THE NONLINEAR q-BERNSTEIN OPERATOR OF MAXIMUM PRODUCT KIND`
- **ART-G08** (disagreement) [PARTIAL] Paper changes only the attention mask (~10 lines of code) and adds one gist token to the vocabulary; there is no architecture change, but the LM itself must be finetuned. (paper ids: GT-002, GT-004, GT-062)  
  value: `PARTIAL` metric:  task:  conditions: Gist Tokens article line 15  
  source: gist-tokens.md repo article  
  quote: `Requires modifications to the model architecture during training`
- **ART-G09** (disagreement) [SUPPORTED (loosely)] The sentence is in the repo's report.txt (not README.md). Paper abstract reports 40% FLOPs with 4.2% wall time; Table 3 gives 4.2% (FLAN-T5-XXL) and 6.8% (LLaMA-7B) vs no caching. The report's explanation 'implementation overhead and hardware characteristics' is not the paper's; the paper cites memory (HBM) time and small scale. (paper ids: GT-009, GT-044, GT-045, GT-047, GT-049)  
  value: `SUPPORTED (loosely)` metric:  task:  conditions: repo report.txt lines 130-132  
  source: report.txt repo article  
  quote: `40% FLOPs reduction may yield only 4% latency improvement`
- **ART-G10** (disagreement) [PARTIAL] Paper says up to 26x more prompts than full-instruction caching in the same storage (not 'memory'), for ~26-token instructions into one gist token; the paper notes KV-cache memory is negligible at the tested prompt lengths. (paper ids: GT-053, GT-054, GT-011)  
  value: `PARTIAL` metric:  task:  conditions: repo README.md line 90  
  source: README.md repo article  
  quote: `particularly for caching scenarios where 26x more prompts can be stored in equivalent memory`
- **ART-LL-1** (disagreement) Article says '98.5% accuracy at moderate compression'; the paper never prints 98.5%, and its 20x result is the extreme quarter-shot GSM8K setting with a 1.5 EM-point drop (see LLv1-CR-2, LLv1-CL-4, LLv1-CL-1).  
  value: `` metric:  task:  conditions: article-vs-paper  
  source: llmlingua.md Technical Details  
  quote: `Maintains 98.5% accuracy at moderate compression levels`
- **ART-LL-2** (disagreement) Article says 'up to 20x compression with minimal performance loss' without task scope; paper shows 20x only on GSM8K, with BBH losing 13.2 EM points at 7x (LLv1-CL-14/15).  
  value: `` metric:  task:  conditions: article-vs-paper  
  source: llmlingua.md Technical Details  
  quote: `Up to 20x compression with minimal performance loss`
- **ART-LL-3** (disagreement) Article says encoders must be trained per target LLM; paper's alignment ablation shows only 0.56 EM from alignment (LLv1-ABL-8), and the Alpaca-7B small LM was reused for Claude citing difficulty collecting alignment data (LLv1-IO-7, LLv1-CL-27).  
  value: `` metric:  task:  conditions: article-vs-paper  
  source: llmlingua.md Limitations  
  quote: `Requires training specific encoders for each target LLM`
- **ART-LL-4** (disagreement) Article says no model training needed; paper instruction-tunes the small LM for alignment (GPT2-Alpaca trained about 150 minutes), though it does not train or modify the target LLM (LLv1-LAT-11, LLv1-MECH-6).  
  value: `` metric:  task:  conditions: article-vs-paper  
  source: llmlingua.md Comparison with Other Methods  
  quote: `No requirement for model training or modification`
- **ART-LL-5** (disagreement) Article recommends LLMLingua for RAG with maintained quality; the LongLLMLingua paper shows v1 LLMLingua well below the original prompt on NaturalQuestions RAG and below zero-shot (LongLL-CL-5, LongLL-CL-10); LLMLingua v1 paper itself tests no RAG (LLv1-TASK-5).  
  value: `` metric:  task:  conditions: article-vs-paper  
  source: llmlingua.md Use Cases  
  quote: `Reduce retrieval context size while maintaining quality`
- **ART-LL-6** (disagreement) Article credits LLMLingua with mitigating lost in the middle; the LLMLingua v1 paper never mentions the issue, its only related remark is a speculative longer-context statement (LLv1-LIM-8). The position analysis belongs to LongLLMLingua (LongLL-POS-1, LongLL-POS-3).  
  value: `` metric:  task:  conditions: article-vs-paper  
  source: llmlingua.md Performance Characteristics  
  quote: `Mitigating "lost in the middle" issues in long prompts`
- **ART-LL-7** (disagreement) Article says performance degrades beyond 20x; the paper's own limitation names notable drops at 25x-30x on GSM8K only, and notes the limit depends on prompt and task (LLv1-LIM-1, LLv1-LIM-2).  
  value: `` metric:  task:  conditions: article-vs-paper  
  source: llmlingua.md Limitations  
  quote: `Performance degrades beyond 20x compression ratios`
- **ART-LL-8** (disagreement) Article lists the Microsoft Teams 40k-token meeting deployment as an LLMLingua use case; nothing in the LLMLingua v1 paper text mentions it.  
  value: `` metric:  task:  conditions: article-vs-paper  
  source: llmlingua.md Use Cases  
  quote: `Microsoft Teams uses this approach for meeting analysis, processing 40k+ token conversations with substantial efficiency gains`
- **ART-LL-9** (disagreement) Article says the coarse stage eliminates sentences using GPT-2-small or LLaMA-7B; paper uses Alpaca-7B and GPT2-Alpaca (GPT2-small tuned on Alpaca), with LLaMA-7B only in the no-alignment ablation, and the coarse step selects whole demonstrations (LLv1-MECH-7, LLv1-MECH-8, LLv1-MECH-4).  
  value: `` metric:  task:  conditions: article-vs-paper  
  source: llmlingua.md Algorithm Overview  
  quote: `Eliminates entire sentences based on perplexity scores calculated using small language models (GPT-2-small or LLaMA-7B)`
- **ART-RD-01** (disagreement) PARTLY SUPPORTED, MISLEADING CONDITION. The paper's 2^len(x) count is the number of target-LLM calls to compute the exact optimal distortion-rate curve for ONE prompt restricted to pruned candidates (unrestricted needs far more); it is a cost of computing the theoretical benchmark, not a cost of running or evaluating any compressor. The paper approximates with beam search (an upper bound, not 'greedy'), and never claims NP-hardness. See RD-40, RD-42, RD-43, RD-44, RD-46.  
  value: `2^n` metric:  task:  conditions:   
  source: README.md Limitations - Fundamental Algorithmic Limitations  
  quote: `Optimal compression evaluation requires at least 2^n inference calls, forcing reliance on greedy approximations`
- **ART-RD-02** (disagreement) UNVERIFIED / OVER-GENERAL. Paper says most existing token-level methods are far from the limit (RD-18) on a synthetic binary set (4-10 tokens), a 10-prompt NL set and a beam-search upper bound on NarrativeQA; it does not state that the gap is largest at high compression ratios (no numbers printed), and on NarrativeQA LLMLingua-2-based methods beat the agnostic upper bound (RD-27). CPC and SCOPE were not evaluated.  
  value: `` metric:  task:  conditions:   
  source: README.md Limitations - Fundamental Algorithmic Limitations  
  quote: `Current methods perform far below optimal compression bounds, particularly at high compression ratios`
- **ART-RD-1** (disagreement) README: '20x with 98.5% accuracy retention'. Paper: 20x appears only on GSM8K quarter-shot with a 1.5 EM-point drop out of a full-shot score (LLv1-CR-2, LLv1-CL-1, LLv1-CL-4); BBH at 7x loses 13.2 points (LLv1-CL-15); ShareGPT and Arxiv-March23 reach only 3.3x and 9x (LLv1-CL-20). '98.5%' is not printed and appears to restate the '1.5 point' drop as a percentage.  
  value: `` metric:  task:  conditions: article-vs-paper  
  source: README.md README line 24  
  quote: `achieving up to 20x compression ratios with 98.5% accuracy retention`
- **ART-RD-2** (disagreement) README: latency 1.6x-5.7x at 2x-10x. Paper Table 6 (GSM8K, V100-32G, 8.6 s baseline) shows 1.7x at 2x up to 5.7x at 10x and the text says 1.7x to 5.7x (LLv1-LAT-4, LLv1-LAT-6); 1.6x is not printed in the LLMLingua paper (1.6x does appear as a LongLLMLingua LongBench speedup at 3x, LongLL-CL-17). It is a single-benchmark API measurement, not deployment data.  
  value: `` metric:  task:  conditions: article-vs-paper  
  source: README.md README line 89  
  quote: `Range from 1.6x-5.7x with compression ratios of 2x-10x`
- **ART-RD-3** (disagreement) README: LongLLMLingua gives 17.1% improvement at 4x. Paper abstract and text say 21.4% with around 4x fewer tokens, for the answer at the 10th position (LongLL-CR-1, LongLL-CR-4); the text never prints 17.1%. In Table 1 (LongLL-CL-4, LongLL-CL-2) 17.1 equals the 10th-position difference 71.2 minus 54.1, i.e. accuracy points, not a percent change (our arithmetic). Original-prompt accuracy at the 1st position is higher than the 4x compressed 1st position (75.7 vs 75.0).  
  value: `` metric:  task:  conditions: article-vs-paper  
  source: README.md README line 81  
  quote: `LongLLMLingua achieving 17.1% performance improvements at 4x compression`
- **ART-RD-4** (disagreement) README: summarization tolerates up to 20x. Paper: Arxiv-March23 summarization tested only up to 9x (similarity to GPT-3.5 output); 20x is GSM8K math (LLv1-CL-20, LLv1-CL-4).  
  value: `` metric:  task:  conditions: article-vs-paper  
  source: README.md README line 80  
  quote: `Summarization tasks**: Tolerate up to 20x compression with minimal performance loss`
- **ART-RD-5** (disagreement) README: conversational tasks work at 4x-9x. Paper: ShareGPT conversation tested only at 1.9x and 3.3x; 4x-9x are the Arxiv-March23 summarization ratios (LLv1-CL-18, LLv1-CL-20).  
  value: `` metric:  task:  conditions: article-vs-paper  
  source: README.md README line 83  
  quote: `Conversational applications**: Perform well at 4x-9x compression ratios`
- **ART-RD-6** (disagreement) README: math reasoning degrades faster beyond 10x. Paper: GSM8K EM is within 1.52 points of full-shot at 20x (LLv1-CL-14); the sharp loss is on BBH already at 5x-7x (LLv1-CL-15), so the claim is not supported as stated.  
  value: `` metric:  task:  conditions: article-vs-paper  
  source: README.md README line 82  
  quote: `Show greater sensitivity, with performance degrading faster beyond 10x compression`
- **ART-RP-1** (disagreement) report.txt repeats the same 20x/98.5% claim; same paper evidence (LLv1-CR-2, LLv1-CL-1, LLv1-CL-4, LLv1-CL-15).  
  value: `` metric:  task:  conditions: article-vs-paper  
  source: report.txt report.txt line 32  
  quote: `achieving up to 20x compression ratios with 98.5% accuracy retention`
- **ART-RP-2** (disagreement) report.txt repeats the 1.6x-5.7x latency claim; paper says 1.7x to 5.7x (LLv1-LAT-4, LLv1-LAT-6).  
  value: `` metric:  task:  conditions: article-vs-paper  
  source: report.txt report.txt line 130  
  quote: `range from 1.6x-5.7x with compression ratios of 2x-10x`
- **ART-RP-3** (disagreement) report.txt repeats the 17.1% at 4x claim; paper says 21.4% (LongLL-CR-1, LongLL-CR-4); 17.1 is only recoverable as a points difference at the 10th position (LongLL-CL-4, LongLL-CL-2).  
  value: `` metric:  task:  conditions: article-vs-paper  
  source: report.txt report.txt line 120  
  quote: `LongLLMLingua achieving 17.1% performance improvements at 4x compression`
- **ART-SCP-01** (disagreement) SUPPORTED WITH CAVEATS. BART is the default summarizer (bart-large-cnn named); Pegasus and Llama-3-8B-Instruct were also tested as backbones, and the pipeline also needs an embedding model (All-MiniLM) and an NER model. See SCP-04, SCP-56.  
  value: `` metric:  task:  conditions:   
  source: scope.md Algorithm Overview  
  quote: `using pre-trained BART models for chunk rewriting`
- **ART-SCP-02** (disagreement) SUPPORTED. 'Requires no additional training'; but inference-time overhead exists: SCOPE averaged 4.20 s (GovReport) vs LongLLMLingua 2.79 s. See SCP-03, SCP-59.  
  value: `` metric:  task:  conditions:   
  source: scope.md How It Works 4  
  quote: `Avoids the training overhead required by learned methods`
- **ART-SCP-03** (disagreement) SUPPORTED. The paper's abstract calls SCOPE training-free. See SCP-01.  
  value: `` metric:  task:  conditions:   
  source: scope.md Key Features 4  
  quote: `Leverages pre-trained models without additional training`
- **ART-SCP-04** (disagreement) NOT SUPPORTED. The paper evaluates only 2x, 3x and 5x; no 10x result exists. See SCP-13.  
  value: `2x-10x` metric:  task:  conditions:   
  source: scope.md Performance Characteristics 3  
  quote: `Typically achieves 2x-10x compression while maintaining quality`
- **ART-SCP-05** (disagreement) NOT SUPPORTED. No legal-specific evaluation: legal documents are only one document type inside the 150-row MultiFieldQA-en set; biomedical = PubMed paper summarization; SCOPE is abstractive and no factual-consistency metric is reported. See SCP-79, SCP-72, SCP-68.  
  value: `` metric:  task:  conditions:   
  source: scope.md Use Cases 4  
  quote: `Legal and Medical Texts**: Where precise meaning preservation is required`
- **ART-SCP-06** (disagreement) REPO DEFECT. The paper exists: SCOPE is arXiv:2508.15813 (Zhang, Wang, Wang; COLM 2026 version v2), but its official repo contained only 'code coming soon.' when fetched. See SCP-76, SCP-74.  
  value: `` metric:  task:  conditions:   
  source: scope.md Note  
  quote: `we were unable to locate the specific paper that introduced this method`
- **ART-SCP-07** (disagreement) SUPPORTED. Paper reports higher compression latency than LongLLMLingua (4.20 s vs 2.79 s on GovReport; no LLMLingua-2 timing given). See SCP-59.  
  value: `` metric:  task:  conditions:   
  source: scope.md Limitations 3  
  quote: `Generative rewriting may be slower than removal-based methods`
- **ART-SCP-08** (disagreement) NOT SUPPORTED. Paper compares at equal ratios; it makes no claim that SCOPE reaches lower maximum compression than token-level methods. See SCP-13.  
  value: `` metric:  task:  conditions:   
  source: scope.md Limitations 1  
  quote: `Generally achieves lower compression than token-level methods`
- **ART-SCP-09** (disagreement) INACCURATE. 'Importance' is chunk similarity to the whole-document embedding, adjusted by chunk length; no question is used (query-agnostic). See SCP-05, SCP-06, SCP-08.  
  value: `` metric:  task:  conditions:   
  source: scope.md Technical Details  
  quote: `Employs dynamic compression ratios based on content importance scoring`
- **ART-X01** (disagreement) [SUPPORTED (conditions)] 6x to 480x holds for 96-480-token Arxiv abstracts compressed into 16/4/1 tokens with LLaMa-3-8b-chat only. (paper ids: XC-012, XC-013, XC-010)  
  value: `SUPPORTED (conditions)` metric:  task:  conditions: 500xCompressor article line 7  
  source: 500x-compressor.md repo article  
  quote: `achieving unprecedented compression ratios from 6x to 480x`
- **ART-X02** (disagreement) [PARTIAL] 62.26-72.89% is the average normalised F1 over five extractive-QA benchmarks relative to full-context-with-instruction (Table 5), with 72.89% at 16 tokens and 62.26% at 1 token; it is not tied to 480x (benchmark context lengths other than ArxivQA are not stated). EM averages are 65.48-81.29. (paper ids: XC-032, XC-033, XC-036, XC-040, XC-018)  
  value: `PARTIAL` metric:  task:  conditions: 500xCompressor article line 21  
  source: 500x-compressor.md repo article  
  quote: `Maintains 62-73% of original capabilities even at extreme compression`
- **ART-X03** (disagreement) [PARTIAL] LoRA is required (trainable in the encoder, ~0.25% extra parameters), but there is no separate encoder-decoder network: the encoder is the frozen LLM plus LoRA and the decoder is the same unmodified LLM. (paper ids: XC-002, XC-001, XC-005)  
  value: `PARTIAL` metric:  task:  conditions: 500xCompressor article line 77  
  source: 500x-compressor.md repo article  
  quote: `Requires specific encoder-decoder architecture with LoRA`
- **ART-X04** (disagreement) [NOT ANALYZED IN PAPER] The paper gives no storage, memory or latency measurements; it says inference-speed improvements are not analysed. The stored object is per-layer KV values of 1-16 tokens (XC-003); its size is not reported. (paper ids: XC-055, XC-056, XC-060)  
  value: `NOT ANALYZED IN PAPER` metric:  task:  conditions: 500xCompressor article line 43  
  source: 500x-compressor.md repo article  
  quote: `Suitable for scenarios where storage/memory is the primary constraint`
- **ART-X05** (disagreement) [NOT ANALYZED IN PAPER] Prompt-caching capacity is not measured; the only memory statement is an unmeasured claim that KV values have small impact on GPU memory. (paper ids: XC-055, XC-056, XC-008)  
  value: `NOT ANALYZED IN PAPER` metric:  task:  conditions: 500xCompressor article line 94  
  source: 500x-compressor.md repo article  
  quote: `Enabling more prompts to be cached in equivalent memory`
- **ART-X06** (disagreement) [CONTRADICTED] The paper does not claim to be first to use KV values: it describes itself as akin to Prefix Tuning and an adaptation of ICAE, and Gist Tokens (2023) already compress prompts into key/value activations (GT-007) as noted in the AutoCompressor paper (AC-085). (paper ids: XC-009, XC-007, GT-007, AC-085)  
  value: `CONTRADICTED` metric:  task:  conditions: 500xCompressor article line 85  
  source: 500x-compressor.md repo article  
  quote: `First to successfully use KV values for compression`
- **ART-X07** (disagreement) [NOT IN PAPER TEXT; SUPPORTED BY OFFICIAL REPO] Cambridge affiliation is in the paper. ACL 2025 is not in the supplied paper text (arXiv v1, Aug 2024); the official GitHub README (via WebFetch) says ACL 2025 Main. (paper ids: XC-070, XC-071, XC-069)  
  value: `NOT IN PAPER TEXT; SUPPORTED BY OFFICIAL REPO` metric:  task:  conditions: 500xCompressor article line 7  
  source: 500x-compressor.md repo article  
  quote: `Developed by Cambridge University and accepted at ACL 2025`
- **ART-X08** (disagreement) [OVERSTATED] The paper only says previous work reported ratios below 50x; it does not say that 480x was impossible. (paper ids: XC-016)  
  value: `OVERSTATED` metric:  task:  conditions: 500xCompressor article line 83  
  source: 500x-compressor.md repo article  
  quote: `480x compression ratios were previously impossible`
- **ART-X09** (disagreement) [PARTIAL] README ties 480x to the 62-73% retention figure; the 62.26% corresponds to 1 compressed token averaged over five QA benchmarks whose context lengths are not all stated, and 72.89% to 16 tokens. (paper ids: XC-040, XC-036, XC-013, XC-032)  
  value: `PARTIAL` metric:  task:  conditions: repo README.md line 73  
  source: README.md repo article  
  quote: `The 500xCompressor pushes boundaries with 480x compression ratios, though extreme compression comes with significant performance trade-offs (retaining 62-73% of capabilities)`

## AutoCompressor

- **AC-001** (mechanism) AutoCompressor adapts a pretrained LM to compress long contexts into short summary vectors that are consumed by the model as soft prompts.  
  value: `` metric:  task:  conditions: OPT-1.3B/2.7B and Llama-2-7B  
  source: autocompressor-2305.14788.txt p.1 Abstract  
  quote: `These language models are capable of compressing long contexts into com- pact summary vectors, which are then acces- sible to the model as soft prompts`
- **AC-002** (mechanism) Training is unsupervised (language-modelling objective over segmented documents); no labels.  
  value: `` metric:  task:  conditions:   
  source: autocompressor-2305.14788.txt p.1 Abstract  
  quote: `Summary vectors are trained with an unsupervised objec- tive, whereby long documents are processed in segments, and summary vectors from all previ- ous segments are used in language modeling`
- **AC-003** (mechanism) Summary accumulation: summary vectors of all segments are concatenated, so the summary length grows with document length.  
  value: `` metric:  task:  conditions:   
  source: autocompressor-2305.14788.txt p.2 Sec. 1  
  quote: `we introduce summary accumulation, in which sum- mary vectors from all segments are concatenated to produce the summary of the entire document`
- **AC-004** (io) Output form: summary vectors = short soft prompts obtained from the output states of the LM (one or two orders of magnitude shorter than the source text).  
  value: `` metric:  task:  conditions:   
  source: autocompressor-2305.14788.txt p.1 Sec. 1  
  quote: `Summary vectors are short soft prompts (Lester et al., 2021), one or two orders of magnitude shorter than the pre-compressed plain text, that are obtained from the output states of a language model`
- **AC-005** (io) The paper does not discuss closed/API LLMs. Summary vectors are produced by, and fed back as soft prompts into, the same fine-tuned open LM (inferred from mechanism: needs model internals; not usable with an API-only LLM).  
  value: `` metric:  task:  conditions: inferred from mechanism  
  source: autocompressor-2305.14788.txt p.1 Sec. 1  
  quote: `Summary vectors are short soft prompts (Lester et al., 2021), one or two orders of magnitude shorter than the pre-compressed plain text, that are obtained from the output states of a language model`
- **AC-006** (mechanism) OPT AutoCompressors (1.3B, 2.7B): trained by fine-tuning the OPT model on 2B tokens of the Pile.  
  value: `2B tokens` metric:  task: Pile conditions: OPT-1.3B / OPT-2.7B  
  source: autocompressor-2305.14788.txt p.4 Sec. 4  
  quote: `We conduct our main experiments and ablations with OPT models (Zhang et al., 2022) of 1.3B or 2.7B parameters, fine-tuned on 2B tokens from the Pile (Gao et al., 2020)`
- **AC-007** (mechanism) Llama-2-7B AutoCompressor: base model frozen; only summary-token embeddings and attention weights (via LoRA) are trained.  
  value: `` metric:  task:  conditions: Llama-2-7B  
  source: autocompressor-2305.14788.txt p.5 Sec. 4.3  
  quote: `We fine-tune a 7B-parameter Llama-2 model as an AutoCompressor on a single GPU by freezing the model and optimizing only the sum- mary token embeddings and the attention weights via LoRA`
- **AC-008** (cost) Llama-2-7B AutoCompressor training data: 15B tokens of RedPajama in sequences of 6,144 tokens, 50 summary tokens.  
  value: `15B tokens; 6,144-token sequences; 50 summary tokens` metric:  task: RedPajama conditions: Llama-2-7B  
  source: autocompressor-2305.14788.txt p.5 Sec. 4.3  
  quote: `The model is trained on 15B tokens from RedPajama (TogetherAI, 2023), split into sequences of 6,144 tokens`
- **AC-009** (mechanism) LoRA settings for Llama-2-7B AutoCompressor: dimension 16 on the QKV and Out projections.  
  value: `16` metric: LoRA dimension task:  conditions: Llama-2-7B  
  source: autocompressor-2305.14788.txt p.13 Appendix A.3  
  quote: `We use a LoRA dimension of 16 applied to the QKV- and Out-projections`
- **AC-010** (hardware) Fine-tuning hardware: a single NVIDIA A100 80GB GPU, on sequences from 6,144 up to 30,720 tokens.  
  value: `1x A100 80GB` metric:  task:  conditions: OPT-2.7B and Llama-2-7B  
  source: autocompressor-2305.14788.txt p.2 Sec. 1  
  quote: `models on sequences from 6,144 up to 30,720 tokens with a single NVIDIA A100 GPU of 80GB memory`
- **AC-011** (hardware) All experiments used one A100 80GB GPU with Flash Attention.  
  value: `1x A100 80GB` metric:  task:  conditions:   
  source: autocompressor-2305.14788.txt p.13 Appendix A  
  quote: `We conduct our experiments using a sin- gle NVIDIA A100 80GB GPU`
- **AC-012** (limitation) Longest trained/evaluated sequence is 30,720 tokens (OPT-1.3B/2.7B only), processed as 20 compression steps over shorter segments (AC-014); 30,720 is a sequence length, not a segment length.  
  value: `30,720; 20 steps` metric: tokens task: Books3 (train), Gutenberg (OOD) conditions: OPT-1.3B/2.7B  
  source: autocompressor-2305.14788.txt p.4 Sec. 4.2  
  quote: `We fine-tune OPT-1.3B and OPT-2.7B as AutoCompressors on 2B tokens but train on se- quences of 30,720 tokens with 20 compression steps`
- **AC-013** (limitation) Abstract states the 30,720-token figure as the fine-tuning sequence length for OPT and Llama-2.  
  value: `30,720` metric: tokens task:  conditions: OPT and Llama-2 (see AC-007/AC-008 for the Llama-2 length)  
  source: autocompressor-2305.14788.txt p.1 Abstract  
  quote: `We fine-tune OPT and Llama-2 models on se- quences of up to 30,720 tokens`
- **AC-014** (limitation) Segment length during training is 1,024-2,048 tokens (OPT-2.7B 8K experiment).  
  value: `1,024-2,048` metric: tokens task:  conditions: OPT-2.7B  
  source: autocompressor-2305.14788.txt p.4 Sec. 4.1  
  quote: `over four segments, each ranging from 1,024 to 2,048 tokens`
- **AC-015** (limitation) The base Llama-2-7B context window is 4,096 tokens; the Llama-2 AutoCompressor's training sequence length is in AC-008.  
  value: `4,096` metric: tokens task:  conditions: Llama-2-7B  
  source: autocompressor-2305.14788.txt p.5 Sec. 4.3  
  quote: `which has a context window of 4,096 tokens`
- **AC-016** (limitation) Llama-2 AutoCompressor evaluated on the final 2,048 tokens of 8,192-token documents only.  
  value: `8,192` metric: tokens task: RedPajama domains conditions: Llama-2-7B  
  source: autocompressor-2305.14788.txt p.5 Sec. 4.3  
  quote: `All models are evaluated on the final 2,048 tokens of 8,192-token documents`
- **AC-017** (compression_ratio) OPT-2.7B: 2,048 tokens compressed into 50 summary vectors = 40 tokens per summary vector.  
  value: `40 tokens/vector; 50 vectors` metric:  task: Pile conditions: OPT-2.7B  
  source: autocompressor-2305.14788.txt p.4 Sec. 4.1  
  quote: `Compressing 2,048 tokens into 50 summary vectors achieves a compression rate of 40 tokens per summary vector`
- **AC-018** (compression_ratio) Llama-2-7B: a 4,096-token context into 100 summary vectors matches Extended Full Attention given only 512 plain tokens (perplexity), i.e. summary vectors are lossy relative to plain text.  
  value: `4,096 tokens -> 100 vectors` metric: perplexity task: RedPajama conditions: Llama-2-7B  
  source: autocompressor-2305.14788.txt p.5 Sec. 4.3  
  quote: `compressing a 4,096-token context into 100 summary vectors achieves simi- lar perplexity to the Extended Full Attention base- line with 512 plain text tokens`
- **AC-019** (compression_ratio) ICL setup: each segment holds as many demonstrations as fit in 750 tokens.  
  value: `750 tokens/segment` metric:  task: 11 classification/MCQ datasets conditions: Llama-2-7B AutoCompressor  
  source: autocompressor-2305.14788.txt p.6 Sec. 5  
  quote: `For each segment, we include as many demonstrations as possible until we reach 750 tokens`
- **AC-020** (compression_ratio) ICL: 1, 2 or 3 segments of demonstrations compressed into 50, 100 or 150 summary vectors.  
  value: `50/100/150 vectors` metric:  task: 11 classification/MCQ datasets conditions: Llama-2-7B AutoCompressor  
  source: autocompressor-2305.14788.txt p.6 Sec. 5  
  quote: `we evaluate the effect of compressing 1, 2 or 3 segments of demonstrations into 50, 100 or 150 summary vectors`
- **AC-021** (compression_ratio) Each 50-vector summary corresponds to a 750-token segment of demonstrations.  
  value: `50 vectors per 750 tokens` metric:  task: ICL conditions: Llama-2-7B AutoCompressor  
  source: autocompressor-2305.14788.txt p.7 Table 4 caption  
  quote: `Each summary is 50 tokens-long and corresponds to a segment of 750 tokens' worth of demonstrations`
- **AC-022** (compression_ratio) Retrieval corpora were split into passages of 512 or 50 tokens (the compressed variants are in AC-086).  
  value: `512 or 50 tokens` metric:  task: Pile retrieval conditions: OPT-2.7B AutoCompressor  
  source: autocompressor-2305.14788.txt p.8 Sec. 6.1  
  quote: `We index 10B tokens for each domain, which are split into pas- sages of 512 or 50 tokens`
- **AC-023** (compression_ratio) Re-ranking passages are only ~100 words so compression is low; authors still report speedups with less performance loss than smaller models.  
  value: `` metric:  task: NQ passage re-ranking conditions: OPT-2.7B AutoCompressor, 20 or 50 summary tokens  
  source: autocompressor-2305.14788.txt p.9 Sec. 6.2  
  quote: `only 100 words long, resulting in low compres- sion rates, summary vectors substantially speed up the inference, while sacrificing on performance less than smaller models`
- **AC-024** (compression_ratio) Number of summary tokens was ablated (Table 7, AC-025): more summary vectors did not help; 50 was best overall.  
  value: `kappa = 50 best` metric: perplexity task: Pile 8K docs conditions: OPT-2.7B  
  source: autocompressor-2305.14788.txt p.6 Sec. 4.4  
  quote: `Surprisingly, we find that performance does not increase with longer soft prompts, and = 50 performs the best overall`
- **AC-025** (context_loss) Table 7 held-out perplexity (columns = 0, 2048, 4096, 6144 compressed tokens; row label = number of summary tokens, kappa symbol lost in raw text): gains from compression are small (e.g. 7.37 -> 6.93 at 50 vectors).  
  value: `20 7.36 7.05 7.01 7.00 | 50 7.37 6.99 6.94 6.93 | 70 7.41 7.01 6.97 6.95 | 100 7.48 7.07 7.01 7.00` metric: perplexity task: Pile 8 domains, 8,192-token docs conditions: OPT-2.7B AutoCompressor  
  source: autocompressor-2305.14788.txt p.14 Table 7  
  quote: `20 7.36 7.05 7.01 7.00 50 7.37 6.99 6.94 6.93 70 7.41 7.01 6.97 6.95 100 7.48 7.07 7.01 7.00`
- **AC-026** (context_loss) Table 1 AutoCompressor row (OPT-2.7B), perplexity of final 2,048 tokens conditioned on summary vectors. Raw text concatenates perplexity with the perplexity gain (e.g. '6.142.2%' = 6.14 and 2.2%); column mapping: in-domain context 128/512/2048/4096/6144 tokens, then out-of-domain same; split inferred from raw text.  
  value: `in-domain 6.14, 6.04, 5.98, 5.94, 5.93 (gains 2.2%, 3.8%, 4.8%, 5.4%, 5.6%); out-of-domain 8.39, 8.26, 8.17, 8.12, 8.10 (1.6%, 3.2%, 4.2%, 4.8%, 5.0%)` metric: perplexity (gain vs fine-tuned OPT without context) task: Pile 8K docs, last 2,048 tokens conditions: OPT-2.7B AutoCompressor, 50 summary vectors per 2,048-token segment  
  source: autocompressor-2305.14788.txt p.5 Table 1  
  quote: `AutoCompressor 6.142.2% 6.043.8% 5.984.8% 5.945.4% 5.93 5.6% 8.391.6% 8.263.2% 8.174.2% 8.124.8% 8.10 5.0%`
- **AC-027** (context_loss) Table 1 Extended Full Attention baseline row (plain text context, OPT-2.7B fine-tuned to 4,096 positions); '-' = not applicable beyond 4,096 tokens.  
  value: `in-domain 6.33, 6.15, 5.94; out-of-domain 8.57, 8.28, 7.93` metric: perplexity (gain) task: Pile 8K docs conditions: OPT-2.7B Extended FA (up to 2,048 extra plain tokens)  
  source: autocompressor-2305.14788.txt p.5 Table 1  
  quote: `Extended FA 6.33 1.0% 6.15 2.1% 5.94 5.4% - - 8.57 0.5% 8.28 2.9% 7.93 7.0% - -`
- **AC-028** (context_loss) Baseline for Table 1 gains: fine-tuned OPT with no extra context has perplexity 6.28 in-domain and 8.53 out-of-domain; gains in AC-026 are measured against these.  
  value: `6.28; 8.53` metric: perplexity task: Pile 8K docs conditions: OPT-2.7B fine-tuned, no context  
  source: autocompressor-2305.14788.txt p.5 Table 1 caption  
  quote: `We also report the perplexity gains compared to the fine-tuned OPT baseline without extra context, which achieves 6.28 in-domain and 8.53 out-of-domain`
- **AC-029** (context_loss) Table 2 (30K): AutoCompressor-1.3B perplexity at 0 / 14,336 / 28,672 context tokens (segments 0 / 7 / 14) and training CUDA memory.  
  value: `13.21 12.49 12.47; 38GB` metric: perplexity; CUDA memory task: Books3 (in-domain) conditions: OPT-1.3B, trained on 30,720-token sequences  
  source: autocompressor-2305.14788.txt p.5 Table 2  
  quote: `AutoCompressor-1.3B 13.21 12.49 12.47 38GB`
- **AC-030** (context_loss) Table 2: RMT-1.3B baseline needs 54GB and its perplexity is identical in the last two columns (no gain from more context).  
  value: `13.18 12.50 12.50; 54GB` metric: perplexity; CUDA memory task: Books3 conditions: OPT-1.3B RMT  
  source: autocompressor-2305.14788.txt p.5 Table 2  
  quote: `RMT-1.3B 13.18 12.50 12.50 54GB`
- **AC-031** (context_loss) Table 2: AutoCompressor-2.7B perplexity and training CUDA memory.  
  value: `11.86 11.21 11.18; 75GB` metric: perplexity; CUDA memory task: Books3 conditions: OPT-2.7B, 30,720-token sequences  
  source: autocompressor-2305.14788.txt p.5 Table 2  
  quote: `AutoCompressor-2.7B 11.86 11.21 11.18 75GB`
- **AC-032** (context_loss) Table 2: RMT-2.7B runs out of memory on a single A100 80GB.  
  value: `OOM` metric:  task: Books3 conditions: OPT-2.7B RMT  
  source: autocompressor-2305.14788.txt p.5 Table 2  
  quote: `RMT-2.7B - - - OOM`
- **AC-033** (context_loss) Table 3 (Llama-2-7B): pre-trained Llama-2 perplexity with 0/128/512/2048 plain context tokens (columns Context tokens 0 128 512 2048 4096 6144).  
  value: `5.52 5.30 5.15 4.98` metric: perplexity task: RedPajama 8K docs, last 2,048 tokens conditions: Llama-2-7B pre-trained (4,096 window)  
  source: autocompressor-2305.14788.txt p.5 Table 3  
  quote: `Llama-2 5.52 5.30 5.15 4.98 - -`
- **AC-034** (context_loss) Table 3: Llama-2 Extended Full Attention (plain text) reaches perplexity 4.76 at 6,144 context tokens.  
  value: `5.40 5.19 5.06 4.88 4.80 4.76` metric: perplexity task: RedPajama 8K docs conditions: Llama-2-7B Extended FA  
  source: autocompressor-2305.14788.txt p.5 Table 3  
  quote: `Extended FA 5.40 5.19 5.06 4.88 4.80 4.76`
- **AC-035** (context_loss) Table 3: Llama-2 AutoCompressor perplexity with context compressed into summary vectors; worse than Extended Full Attention (AC-034) in the last columns.  
  value: `5.40 5.23 5.16 5.11 5.08 5.07` metric: perplexity task: RedPajama 8K docs conditions: Llama-2-7B AutoCompressor, 50 vectors/segment  
  source: autocompressor-2305.14788.txt p.5 Table 3  
  quote: `AutoCompressor 5.40 5.23 5.16 5.11 5.08 5.07`
- **AC-036** (limitation) Authors: with longer contexts the full-attention baselines beat the AutoCompressor; summary vectors do not preserve all context information.  
  value: `` metric:  task:  conditions: Llama-2-7B  
  source: autocompressor-2305.14788.txt p.6 Sec. 4.3  
  quote: `baseline outperform the AutoCompressor when longer contexts are provided. Further re- search is needed to construct summary vectors that preserve all of the context information`
- **AC-037** (limitation) Summary vectors generalise slightly worse out of domain than pre-trained attention heads.  
  value: `` metric:  task:  conditions: OPT-2.7B  
  source: autocompressor-2305.14788.txt p.4 Sec. 4.1  
  quote: `the gap between the AutoCompressor and the full-attention baseline increases in the out-of-domain setting, suggesting that the summary vectors generalize slightly less than pre-trained attention heads`
- **AC-038** (context_loss) ICL zero-shot accuracy of the Llama-2-7B AutoCompressor (no demonstrations). Columns per header: AG News, SST-2, BoolQ, WiC, WSC, RTE, CB, COPA, MultiRC, MR, Subj; values are accuracy, parenthesised value is std dev over 7 seeds.  
  value: `63.3 67.7 67.4 50.8 43.3 58.8 42.9 52.5 52.5 57.4 49.3` metric: accuracy task: 11 classification/MCQ datasets conditions: Llama-2-7B AutoCompressor, zero-shot  
  source: autocompressor-2305.14788.txt p.7 Table 4  
  quote: `Zero-shot 63.3(0.0) 67.7(0.0) 67.4(0.0) 50.8(0.0) 43.3(0.0) 58.8(0.0) 42.9(0.0) 52.5(0.0) 52.5(0.0) 57.4(0.0) 49.3(0.0)`
- **AC-039** (context_loss) ICL with demonstrations compressed into 50 summary vectors (one 750-token segment). Columns per header: AG News, SST-2, BoolQ, WiC, WSC, RTE, CB, COPA, MultiRC, MR, Subj; values are accuracy, parenthesised value is std dev over 7 seeds.  
  value: `79.6 94.2 70.1 51.6 47.7 66.3 46.4 84.5 52.6 91.5 53.5` metric: accuracy task: 11 classification/MCQ datasets conditions: Llama-2-7B AutoCompressor, 50 summary vectors  
  source: autocompressor-2305.14788.txt p.7 Table 4  
  quote: `50 summary vecs. 79.6(4.9) 94.2 (1.6) 70.1 (3.3) 51.6(2.1) 47.7(8.7) 66.3(7.0) 46.4(18.7) 84.5(1.0) 52.6(2.8) 91.5(1.0) 53.5(3.6)`
- **AC-040** (context_loss) ICL with 100 summary vectors (two segments). Columns per header: AG News, SST-2, BoolQ, WiC, WSC, RTE, CB, COPA, MultiRC, MR, Subj; values are accuracy, parenthesised value is std dev over 7 seeds.  
  value: `87.6 92.6 66.3 52.5 42.9 63.5 64.5 85.9 56.1 90.7 57.0` metric: accuracy task: 11 classification/MCQ datasets conditions: Llama-2-7B AutoCompressor, 100 summary vectors  
  source: autocompressor-2305.14788.txt p.7 Table 4  
  quote: `100 summary vecs. 87.6 (1.2) 92.6(3.3) 66.3(2.8) 52.5(2.2) 42.9(2.5) 63.5(6.6) 64.5 (5.9) 85.9(0.4) 56.1 (1.2) 90.7(2.6) 57.0(5.6)`
- **AC-041** (context_loss) ICL with 150 summary vectors (three segments). Columns per header: AG News, SST-2, BoolQ, WiC, WSC, RTE, CB, COPA, MultiRC, MR, Subj; values are accuracy, parenthesised value is std dev over 7 seeds.  
  value: `85.4 92.3 68.0 52.8 49.9 65.3 54.8 86.1 54.8 91.1 56.6` metric: accuracy task: 11 classification/MCQ datasets conditions: Llama-2-7B AutoCompressor, 150 summary vectors  
  source: autocompressor-2305.14788.txt p.7 Table 4  
  quote: `150 summary vecs. 85.4(3.4) 92.3(2.9) 68.0(1.8) 52.8 (1.5) 49.9(7.6) 65.3(6.6) 54.8(5.8) 86.1 (0.6) 54.8(2.2) 91.1(2.2) 56.6(7.9)`
- **AC-042** (context_loss) Baseline: plain-text ICL with 150 tokens' worth of demonstrations through the same AutoCompressor model. Columns per header: AG News, SST-2, BoolQ, WiC, WSC, RTE, CB, COPA, MultiRC, MR, Subj; values are accuracy, parenthesised value is std dev over 7 seeds.  
  value: `74.5 92.4 67.4 52.4 51.8 69.1 46.4 80.0 52.5 79.7 57.9` metric: accuracy task: 11 classification/MCQ datasets conditions: Llama-2-7B AutoCompressor, plain-text ICL 150 tokens  
  source: autocompressor-2305.14788.txt p.7 Table 4  
  quote: `ICL (150 tokens) 74.5(2.2) 92.4(3.1) 67.4(0.0) 52.4(2.7) 51.8 (6.9) 69.1(2.1) 46.4(23.0) 80.0(1.9) 52.5(0.0) 79.7(15.7) 57.9(10.7)`
- **AC-043** (context_loss) Baseline: plain-text ICL with 750 tokens' worth of demonstrations through the same AutoCompressor model (RTE 73.1 and Subj 60.7 beat the summary-vector results). Columns per header: AG News, SST-2, BoolQ, WiC, WSC, RTE, CB, COPA, MultiRC, MR, Subj; values are accuracy, parenthesised value is std dev over 7 seeds.  
  value: `81.2 93.8 67.7 52.4 40.0 73.1 50.3 82.6 47.0 91.6 60.7` metric: accuracy task: 11 classification/MCQ datasets conditions: Llama-2-7B AutoCompressor, plain-text ICL 750 tokens  
  source: autocompressor-2305.14788.txt p.7 Table 4  
  quote: `ICL (750 tokens) 81.2(4.1) 93.8(1.2) 67.7(2.7) 52.4(2.0) 40.0(5.7) 73.1 (3.5) 50.3(2.8) 82.6(1.6) 47.0(3.2) 91.6 (0.8) 60.7 (14.8)`
- **AC-044** (tasks_tested) ICL dataset columns (from the header row of Table 4).  
  value: `` metric:  task: AG News, SST-2, BoolQ, WiC, WSC, RTE, CB, COPA, MultiRC, MR, Subj conditions:   
  source: autocompressor-2305.14788.txt p.7 Table 4 header  
  quote: `AG News SST-2 BoolQ WIC WSC RTE CB COPA MultiRC MR Subj`
- **AC-045** (context_loss) ICL results are mean accuracy and standard deviation over 7 random seeds (parenthesised values in Tables 4 and 12 are therefore std dev).  
  value: `7 seeds` metric: accuracy task:  conditions:   
  source: autocompressor-2305.14788.txt p.6 Sec. 5  
  quote: `For each dataset, we report the mean accuracy and standard deviation over 7 random seeds`
- **AC-046** (context_loss) Table 12: pre-trained Llama-2-7B (not the AutoCompressor fine-tune) zero-shot accuracy is higher than the AutoCompressor's zero-shot on several tasks (e.g. SST-2 87.2 vs 67.7). Columns per header: AG News, SST-2, BoolQ, WiC, WSC, RTE, CB, COPA, MultiRC, MR, Subj; values are accuracy, parenthesised value is std dev over 7 seeds.  
  value: `68.8 87.2 70.0 51.4 65.4 62.8 32.1 75.5 54.5 84.1 48.9` metric: accuracy task: 11 classification/MCQ datasets conditions: Llama-2-7B pre-trained, zero-shot  
  source: autocompressor-2305.14788.txt p.18 Table 12  
  quote: `Zero-shot 68.8(0.0) 87.2(0.0) 70.0(0.0) 51.4(0.0) 65.4(0.0) 62.8(0.0) 32.1(0.0) 75.5(0.0) 54.5(0.0) 84.1(0.0) 48.9(0.0)`
- **AC-047** (context_loss) Table 12: pre-trained Llama-2-7B plain-text ICL, 150 tokens. Columns per header: AG News, SST-2, BoolQ, WiC, WSC, RTE, CB, COPA, MultiRC, MR, Subj; values are accuracy, parenthesised value is std dev over 7 seeds.  
  value: `71.9 91.6 70.0 51.0 55.4 70.9 39.3 84.2 54.5 90.6 63.6` metric: accuracy task: 11 classification/MCQ datasets conditions: Llama-2-7B pre-trained, ICL 150 tokens  
  source: autocompressor-2305.14788.txt p.18 Table 12  
  quote: `ICL (150 tokens) 71.9(3.8) 91.6(2.9) 70.0(0.0) 51.0(1.9) 55.4(3.2) 70.9(1.7) 39.3(21.2) 84.2(1.3) 54.5(0.0) 90.6(3.3) 63.6(10.8)`
- **AC-048** (context_loss) Table 12: pre-trained Llama-2-7B plain-text ICL, 750 tokens (the uncompressed 750-token baseline without AutoCompressor fine-tuning). Columns per header: AG News, SST-2, BoolQ, WiC, WSC, RTE, CB, COPA, MultiRC, MR, Subj; values are accuracy, parenthesised value is std dev over 7 seeds.  
  value: `78.2 94.5 70.3 54.9 42.2 71.3 51.3 85.3 47.0 92.9 65.4` metric: accuracy task: 11 classification/MCQ datasets conditions: Llama-2-7B pre-trained, ICL 750 tokens  
  source: autocompressor-2305.14788.txt p.18 Table 12  
  quote: `ICL (750 tokens) 78.2(3.8) 94.5(0.8) 70.3(6.1) 54.9(1.9) 42.2(5.0) 71.3(4.4) 51.3(3.5) 85.3(0.7) 47.0(1.5) 92.9(0.5) 65.4(14.5)`
- **AC-049** (context_loss) Authors: summary vectors beat 150 plain-text demonstration tokens on 8 of 11 tasks.  
  value: `8/11` metric: accuracy task: 11 classification/MCQ datasets conditions: Llama-2-7B AutoCompressor  
  source: autocompressor-2305.14788.txt p.7 Sec. 5  
  quote: `compared to 150 tokens worth of plain demonstra- tions on 8/11 tasks`
- **AC-050** (context_loss) Authors: on 8 tasks summary vectors also beat ICL with 750 tokens of plain-text demonstrations.  
  value: `8 tasks` metric: accuracy task: AG News, SST-2, BoolQ, WiC, WSC, CB, COPA, MultiRC conditions: Llama-2-7B AutoCompressor  
  source: autocompressor-2305.14788.txt p.7 Sec. 5  
  quote: `On 8 tasks (AG News, SST-2, BoolQ, WiC, WSC, CB, COPA and MultiRC), sum- mary vectors also out-perform ICL with 750 tokens' worth of plain text demonstrations`
- **AC-051** (limitation) Authors: the fine-tuned Llama-2 AutoCompressor has substantially worse zero-shot accuracy on some tasks and slightly worse ICL than the Llama-2 initialisation.  
  value: `` metric: accuracy task: 11 classification/MCQ datasets conditions: Llama-2-7B AutoCompressor vs Llama-2-7B  
  source: autocompressor-2305.14788.txt p.7 Sec. 5  
  quote: `We also ob- serve that our fine-tuned Llama-2 AutoCompressor has substantially worse zero-shot accuracy on some tasks compared to the Llama-2 initialization, and slightly worse ICL performance`
- **AC-052** (limitation) Authors attribute the degradation to domain mismatch between their fine-tuning data and the Llama-2 pre-training corpus.  
  value: `` metric:  task:  conditions:   
  source: autocompressor-2305.14788.txt p.7 Sec. 5  
  quote: `We suspect that this is due to domain mismatch in our fine-tuning data and the Llama-2 pre-training corpus`
- **AC-053** (context_loss) Table 5 REPLUG with 50-token passages: perplexity gain (%) at top-1/2/5/10 then throughput (examples/s) at top-1/2/5/10; baseline = no retrieval.  
  value: `-0.64 0.58 1.68 2.35 | 51 38 16 9` metric: perplexity gain %; throughput task: retrieval-augmented LM on Pile conditions: OPT-2.7B AutoCompressor, 1 A100, no batching  
  source: autocompressor-2305.14788.txt p.8 Table 5  
  quote: `50 tokens REPLUG -0.64 0.58 1.68 2.35 51 38 16 9`
- **AC-054** (context_loss) Table 5 Fused Passages (plain text, 50-token passages).  
  value: `0.71 1.01 1.70 2.60 | 28 27 23 17` metric: perplexity gain %; throughput task: retrieval-augmented LM on Pile conditions: OPT-2.7B  
  source: autocompressor-2305.14788.txt p.8 Table 5  
  quote: `50 tokens Fused Passages 0.71 1.01 1.70 2.60 28 27 23 17`
- **AC-055** (context_loss) Table 5 Fused Summaries (512-token passages compressed to 50 summary vectors each): gains are small, 1.04%-3.74%.  
  value: `1.04 1.67 2.63 3.74 | 28 27 23 17` metric: perplexity gain %; throughput task: retrieval-augmented LM on Pile conditions: OPT-2.7B AutoCompressor  
  source: autocompressor-2305.14788.txt p.8 Table 5  
  quote: `Fused Summaries 1.04 1.67 2.63 3.74 28 27 23 17`
- **AC-056** (context_loss) Table 5 REPLUG with full 512-token plain-text passages: larger perplexity gain (8.30% at top-10) but much lower throughput (3 examples/s).  
  value: `-1.47 2.24 5.25 8.30 | 18 10 6 3` metric: perplexity gain %; throughput task: retrieval-augmented LM on Pile conditions: OPT-2.7B  
  source: autocompressor-2305.14788.txt p.8 Table 5  
  quote: `512 tokens REPLUG -1.47 2.24 5.25 8.30 18 10 6 3`
- **AC-057** (latency_compute) Fused Summaries top-10 beats REPLUG top-2 with 512-token passages and has 1.7x throughput.  
  value: `1.7x` metric: throughput task: retrieval-augmented LM on Pile conditions: OPT-2.7B, 1 A100  
  source: autocompressor-2305.14788.txt p.8 Sec. 6.1  
  quote: `Fused Summaries outperforms RE- PLUG top-2 with 512-token passages and sees a 1.7x throughput increase`
- **AC-058** (limitation) REPLUG top-10 with plain-text passages still beats Fused Summaries (compressed passages lose information).  
  value: `` metric:  task: retrieval-augmented LM conditions: OPT-2.7B  
  source: autocompressor-2305.14788.txt p.8 Sec. 6.1  
  quote: `REPLUG top-10 outper- forms Fused Summaries`
- **AC-059** (hardware) Throughput measured on a single NVIDIA A100 GPU without batching.  
  value: `1x A100` metric:  task:  conditions:   
  source: autocompressor-2305.14788.txt p.8 Table 5 caption  
  quote: `we report throughput on a single NVIDIA A100 GPU for each method without batching examples`
- **AC-060** (latency_compute) Storage cost: summary vectors for a 10B-token corpus take 5TB per domain in half precision.  
  value: `5TB per 10B-token domain` metric: disk task: Pile domains conditions: OPT-2.7B AutoCompressor, 50 vectors/512-token passage  
  source: autocompressor-2305.14788.txt p.8 Sec. 6.1  
  quote: `compress- ing the 10B token datasets results in disk space of 5TB per domain when stored in half-precision for- mat`
- **AC-061** (latency_compute) For comparison the paper states storing every token's transformer output would take 51 TB and all attention states 3,276 TB for the same corpus.  
  value: `51 TB; 3,276 TB` metric: disk task: Pile domains conditions: 10B-token corpus  
  source: autocompressor-2305.14788.txt p.8 footnote 5  
  quote: `storing the transformer output at every single token (e.g., in an encoder-decoder setting) would take up 51 TB, and storing all attention states would be 3,276 TB`
- **AC-062** (latency_compute) Pre-computed summary vectors for the Wikipedia passage corpus need 2.1TB (20 vectors) and 5.4TB (50 vectors).  
  value: `2.1TB; 5.4TB` metric: disk task: NQ re-ranking corpus (21M passages per Sec. 6.2 text) conditions: half precision  
  source: autocompressor-2305.14788.txt p.9 Sec. 6.2  
  quote: `which requires 2.1TB and 5.4TB disk space in half precision for 20 and 50 summary vectors re- spectively`
- **AC-063** (latency_compute) Re-ranking throughput assumes the latency of loading pre-computed summary vectors is negligible; compressor encoding time itself is not reported in seconds.  
  value: `` metric: queries/s task: NQ re-ranking conditions: 1 A100 80GB, un-batched  
  source: autocompressor-2305.14788.txt p.9 Sec. 6.2  
  quote: `assume that the latency of loading summary vectors is negligible`
- **AC-064** (limitation) Re-ranking quality (Recall@20) and throughput are only shown in Figure 4; no numbers appear in the text.  
  value: `not reported` metric: Recall@20 task: NQ test set conditions:   
  source: autocompressor-2305.14788.txt p.9 Figure 4 caption  
  quote: `the vertical axis shows the Recall@20 performance of the re-ranking system on the NQ test set`
- **AC-065** (cost) Authors' summary: simple and inexpensive way to extend context window while speeding up inference over long contexts.  
  value: `` metric:  task:  conditions:   
  source: autocompressor-2305.14788.txt p.1 Abstract  
  quote: `AutoCompressors emerge as a simple and inexpensive solution to extend the context window of LMs while speeding up inference over long contexts`
- **AC-066** (limitation) Authors' limitation 1: only tested on OPT up to 2.7B and Llama 7B.  
  value: `` metric:  task:  conditions:   
  source: autocompressor-2305.14788.txt p.9 Limitations  
  quote: `We only apply AutoCompressors to OPT mod- els of up to 2.7B parameters and a Llama model of 7B parameters`
- **AC-067** (limitation) Authors' limitation 2: summary vectors ignore useful information available via full attention.  
  value: `` metric:  task:  conditions:   
  source: autocompressor-2305.14788.txt p.9 Limitations  
  quote: `Our results suggest that summary vectors ig- nore some useful information that is accessible via full attention`
- **AC-068** (limitation) Authors' limitation 3: summary accumulation is still quadratic in the number of segments.  
  value: `` metric:  task:  conditions:   
  source: autocompressor-2305.14788.txt p.9 Limitations  
  quote: `Summary accumulation still leads to quadratic complexity with increasing number of segments, albeit at a much lower rate than full attention`
- **AC-069** (limitation) More summary vectors do not always help.  
  value: `` metric:  task:  conditions:   
  source: autocompressor-2305.14788.txt p.9 Limitations  
  quote: `Additionally, models do not always benefit from increasing the number of summary vectors`
- **AC-070** (reproducibility) Code and models stated to be publicly available.  
  value: `` metric:  task:  conditions:   
  source: autocompressor-2305.14788.txt p.1 footnote 1  
  quote: `Our code and models are publicly available at https://github.com/princeton-nlp/AutoCompressors`
- **AC-071** (reproducibility) Official GitHub page (as summarised by WebFetch) shows no LICENSE file, badge or README licence section; absence only, verify manually. Base-model licences (Llama-2, OPT) are not mentioned.  
  value: `no licence declared` metric:  task:  conditions:   
  source: https://github.com/princeton-nlp/AutoCompressors GitHub page (WebFetch)  
  quote: `The page doesn't declare one.`
- **AC-072** (reproducibility) Released Hugging Face checkpoints (princeton-nlp namespace) include AutoCompressor-Llama-2-7b-6k (6,144 tokens), AutoCompressor-2.7b-6k and AutoCompressor-2.7b-30k / 1.3b-30k (30,720 tokens), plus RMT and FullAttention baselines. Quote as returned by WebFetch.  
  value: `` metric:  task:  conditions:   
  source: https://github.com/princeton-nlp/AutoCompressors GitHub README (WebFetch)  
  quote: `AutoCompressor-Llama-2-7b-6k (6,144 tokens, 4 compression steps)`
- **AC-073** (tasks_tested) Training domains for OPT 8K experiments: Books3, FreeLaw, GitHub and Wikipedia subdomains of the Pile (500M tokens each).  
  value: `` metric: perplexity task: language modelling conditions: OPT-2.7B  
  source: autocompressor-2305.14788.txt p.13 Appendix A.1  
  quote: `We sample 500M tokens from the following Pile subdomains: Books3, FreeLaw, GitHub and Wikipedia`
- **AC-074** (tasks_tested) Evaluation domains (OPT 8K): in-domain Books3, FreeLaw, GitHub, Wikipedia; out-of-domain ArXiv, Gutenberg, HackerNews, YoutubeSubtitles (610 docs each).  
  value: `610 docs per domain` metric: perplexity task: language modelling conditions: OPT-2.7B  
  source: autocompressor-2305.14788.txt p.13 Appendix A.1  
  quote: `We sample 610 documents from each of the following domains: Books3, FreeLaw, GitHub, Wikipedia (in-domain), and ArXiv, Gutenberg, HackerNews, YoutubeSubtitles (out-of-domain)`
- **AC-075** (tasks_tested) Llama-2 evaluation domains: ArXiv, Books, C4, GitHub, StackExchange (500 sequences of 8,192 tokens each) and CommonCrawl (5,000).  
  value: `500; 5,000` metric: perplexity task: language modelling conditions: Llama-2-7B  
  source: autocompressor-2305.14788.txt p.13 Appendix A.3  
  quote: `We evaluate our models on 500 sequences of 8,192 tokens from each of ArXiv, Books, C4, GitHub, StackExchange, and 5,000 sequences from CommonCrawl`
- **AC-076** (tasks_tested) In-context learning on 11 classification tasks including 7 SuperGLUE tasks.  
  value: `11 tasks` metric: accuracy task: ICL conditions: Llama-2-7B, OPT-2.7B  
  source: autocompressor-2305.14788.txt p.2 Sec. 1  
  quote: `We consider 11 classification tasks, including 7 SuperGLUE tasks`
- **AC-077** (tasks_tested) Retrieval-augmented language modelling (REPLUG-style, perplexity) retrieving from Pile subsets incl. GitHub and FreeLaw; no QA accuracy is reported.  
  value: `` metric: perplexity gain task: retrieval-augmented LM conditions: OPT-2.7B  
  source: autocompressor-2305.14788.txt p.8 Sec. 6.1  
  quote: `We use Books3, FreeLaw, GitHub, Wikipedia, Gutenberg, ArXiv, HackerNews, and YoutubeSubtitles`
- **AC-078** (tasks_tested) Zero-shot passage re-ranking of BM25 candidates on the NQ test set.  
  value: `` metric: Recall@20 task: NQ passage re-ranking conditions: OPT AutoCompressors vs pre-trained OPT 125M-2.7B  
  source: autocompressor-2305.14788.txt p.8 Sec. 6.2  
  quote: `We consider the task of re-ranking BM25 passages on the NQ test set`
- **AC-079** (tasks_tested) Evaluated tasks are language modelling (Pile / RedPajama domains), 11 classification ICL datasets, retrieval-augmented LM perplexity and NQ re-ranking. Not tested: coding tasks (only GitHub-domain perplexity), long-document QA/RAG answer accuracy, multi-turn chat, summarization, structured data (JSON/tables/logs), math/reasoning, PII/sensitive content.  
  value: `not tested in paper` metric:  task: coding; long-document QA/RAG; multi-turn chat; summarization; structured data; reasoning/math; sensitive/PII conditions: dataset lists quoted in AC-073..AC-078  
  source: autocompressor-2305.14788.txt p.2 Sec. 1  
  quote: `We consider 11 classification tasks, including 7 SuperGLUE tasks`
- **AC-080** (reproducibility) Identity: the AutoCompressor paper is 'Adapting Language Models to Compress Contexts' (Chevalier, Wettig, Ajith, Chen; Princeton).  
  value: `` metric:  task:  conditions:   
  source: autocompressor-2305.14788.txt p.1 title page  
  quote: `Adapting Language Models to Compress Contexts Alexis Chevalier Alexander Wettig Anirudh Ajith Danqi Chen`
- **AC-081** (reproducibility) arXiv identifier and version of the paper used.  
  value: `2305.14788` metric:  task:  conditions:   
  source: autocompressor-2305.14788.txt p.1 title page stamp  
  quote: `arXiv:2305.14788v2 [cs.CL] 4 Nov 2023`
- **AC-082** (context_loss) Table 1 gives only in-domain and out-of-domain aggregates; per-domain perplexity (e.g. GitHub, FreeLaw) is not reported in the text.  
  value: `not reported` metric: perplexity task: Pile domains conditions: OPT-2.7B  
  source: autocompressor-2305.14788.txt p.5 Table 1 caption  
  quote: `Held-out perplexity on 2,048 tokens, while varying the length of the preceding context`
- **AC-083** (context_loss) Qualitative: summary vectors carry salient information such as names or dates; there is no exact-string reconstruction metric (the training objective is next-token prediction, not reconstruction).  
  value: `` metric:  task: Pile conditions: OPT-2.7B  
  source: autocompressor-2305.14788.txt p.6 Sec. 4.4  
  quote: `We find that summary vectors contain salient information, such as names or dates, and that the model can reason over summary vectors`
- **AC-084** (limitation) Third-party characterisation (500xCompressor authors): AutoCompressor is limited to fine-tuned LLMs and has a complex training process. Cross-check only.  
  value: `` metric:  task:  conditions: claim by Li et al.  
  source: 500x-compressor.txt p.7 Sec. 6 Related Work  
  quote: `AutoCompressor, which recursively compresses the prompt but, like GIST tokens, is limited to fine-tuned LLMs and a complex training process`
- **AC-086** (compression_ratio) Table 5 row label: 512-token retrieved passages are compressed into 50 summary vectors each (the arrow glyph before '50' is lost in the raw text).  
  value: `512 tokens -> 50 vectors` metric:  task: retrieval-augmented LM on Pile conditions: OPT-2.7B AutoCompressor  
  source: autocompressor-2305.14788.txt p.8 Table 5  
  quote: `50 sum. vecs. Fused Summaries`
- **AC-087** (reproducibility) Venue of the AutoCompressor paper per the 500xCompressor reference list: EMNLP 2023.  
  value: `EMNLP 2023` metric:  task:  conditions: claim by Li et al.  
  source: 500x-compressor.txt p.8 References  
  quote: `Adapting Language Models to Compress Contexts. In The 2023 Conference on Empirical Methods in Natural Lan- guage Processing`

## CPC

- **CPC-01** (mechanism) CPC is a sentence-level compressor whose learned encoder scores each context sentence against the given question.  
  value: `` metric:  task:  conditions: query-aware (needs the question at compression time)  
  source: cpc-2409.01227.txt p.1 Abstract  
  quote: `key innovation is a novel context-aware sentence encoder that provides a relevance score for each sentence for a given question`
- **CPC-02** (mechanism) Compression selects whole sentences ranked by encoder relevance to the question and restores their original order; no text is rewritten.  
  value: `` metric:  task:  conditions: query-aware; extractive at sentence level  
  source: cpc-2409.01227.txt p.5 Sec. 3.4 Inference  
  quote: `We then restore the order of selected sentences in the original context to form the compressed context`
- **CPC-03** (mechanism) The encoder is a trained model: a pre-trained LLM fine-tuned (bidirectional attention plus contrastive loss) on the authors' CQR dataset; it is not an off-the-shelf scorer.  
  value: `` metric:  task:  conditions: trained encoder  
  source: cpc-2409.01227.txt p.5 Sec. 3.3  
  quote: `we adopt a pre-trained LLM and use the concept introduced in BehnamGhader et al. (2024) through finetuning to learn bidirectional attention over the whole context`
- **CPC-04** (mechanism) The encoder used in the paper is Mistral-7B-Instruct-v0.2 with LoRA rank 16, i.e. a 7B-parameter-class compressor model.  
  value: `7B; LoRA rank 16` metric:  task:  conditions: encoder f for all main results  
  source: cpc-2409.01227.txt p.5 Sec. 4.2  
  quote: `For f, we adopt the Mistral-7B-Instruct-v0.2 (Jiang et al. 2023a) given that it is open-source and allows for long context lengths, and fine-tune this model with LoRA (Hu et al. 2022) of rank 16`
- **CPC-05** (mechanism) Related-work position: the authors say sequence-to-sequence (generative) compressors have high latency because of autoregressive generation.  
  value: `` metric:  task:  conditions: statement about generative compressors such as RECOMP, not measured  
  source: cpc-2409.01227.txt p.2 Sec. 2.1  
  quote: `these methods have high latency due to the autoregressive nature of generation`
- **CPC-06** (io) CPC output is plain original-text sentences; the authors state it preserves human readability, unlike the LLMLingua family (design statement; no readability metric or user study is reported).  
  value: `` metric:  task:  conditions:   
  source: cpc-2409.01227.txt p.2 Sec. 1  
  quote: `it performs context compression while preserving human readability, unlike token-based compressors such as the LLMLingua family`
- **CPC-07** (io) Evidence that CPC output can feed a closed API model: the paper runs CPC with GPT-4o as the downstream backbone (Table 4). The paper does not discuss closed/API models explicitly; text-in/text-out use is inferred from the mechanism.  
  value: `` metric:  task: LongBench conditions: target LLM GPT-4o (Table 4 only); target LLM of Tables 2-3 is not stated  
  source: cpc-2409.01227.txt p.7 Sec. 4.4 Larger backbone  
  quote: `we compare the performance of CPC against prior works with a larger LLM, GPT-4o, as the backbone`
- **CPC-08** (compression_ratio) Main results use token budgets of 3,000 and 2,000 tokens, which the authors describe as about 3x and 5x compression of the average original length.  
  value: `3x; 5x` metric:  task: LongBench, ZeroSCROLLS conditions: token constraints 3,000 / 2,000  
  source: cpc-2409.01227.txt p.6 Sec. 4.4  
  quote: `the results are reported on 3,000 and 2,000 tokens, which is about 3� and 5� compression of the total token length`
- **CPC-09** (context_loss) Uncompressed LongBench/ZeroSCROLLS baseline row in Table 2 (columns: SingleDoc, MultiDoc, Summ., FewShot, Synth., Code, AVG, Tokens; then ZeroSCROLLS AVG, Tokens). Average original length 10,295 tokens (LongBench) and 9,788 (ZeroSCROLLS).  
  value: `44.0; 32.5` metric: LongBench AVG; ZeroSCROLLS AVG task: LongBench, ZeroSCROLLS conditions: Original Prompt, no compression; target LLM not stated in paper  
  source: cpc-2409.01227.txt p.6 Table 2  
  quote: `Original Prompt 39.7 38.7 26.5 67.0 37.8 54.2 44.0 10,295 - 32.5 9,788 -`
- **CPC-10** (context_loss) Table 2 column header giving the subtask order for the rows quoted from Table 2.  
  value: `` metric:  task: LongBench conditions:   
  source: cpc-2409.01227.txt p.6 Table 2 header  
  quote: `SingleDoc MultiDoc Summ. FewShot Synth. Code AVG Tokens`
- **CPC-11** (context_loss) CPC at the 3,000-token budget (about 3x): LongBench AVG 50.0, Summ. column 23.8, Code column 63.5; ZeroSCROLLS AVG 34.9.  
  value: `50.0; 34.9` metric: LongBench AVG; ZeroSCROLLS AVG task: LongBench, ZeroSCROLLS conditions: 3,000 tokens constraint; query-aware; target LLM not stated  
  source: cpc-2409.01227.txt p.6 Table 2  
  quote: `CPC (Ours) 42.7 47.9 23.8 69.3 52.8 63.5 50.0 3,327 3� 34.9 3,470 3�`
- **CPC-12** (context_loss) LongLLMLingua (compression-based group) at the 3,000-token budget in the same table: LongBench AVG 48.8, Summ. 27.2.  
  value: `48.8; 32.8` metric: LongBench AVG; ZeroSCROLLS AVG task: LongBench, ZeroSCROLLS conditions: 3,000 tokens constraint; query-aware  
  source: cpc-2409.01227.txt p.6 Table 2  
  quote: `LongLLMLingua 40.7 46.2 27.2 70.6 53.0 55.2 48.8 3,283 3� 32.8 3,412 3�`
- **CPC-13** (context_loss) LLMLingua-2 (query-agnostic) at the 3,000-token budget: LongBench AVG 42.2, Summ. 26.3, Synth. 21.4.  
  value: `42.2; 33.5` metric: LongBench AVG; ZeroSCROLLS AVG task: LongBench, ZeroSCROLLS conditions: 3,000 tokens constraint; query-agnostic  
  source: cpc-2409.01227.txt p.6 Table 2  
  quote: `LLMLingua-2 35.5 38.7 26.3 69.6 21.4 62.8 42.2 3,392 3� 33.5 3,206 3�`
- **CPC-14** (context_loss) LLMLingua at the 3,000-token budget: LongBench AVG 37.4 (Table 1 prints a different number for the same method, see CPC-22).  
  value: `37.4; 30.7` metric: LongBench AVG; ZeroSCROLLS AVG task: LongBench, ZeroSCROLLS conditions: 3,000 tokens constraint  
  source: cpc-2409.01227.txt p.6 Table 2  
  quote: `LLMLingua 31.8 37.5 26.2 67.2 8.3 53.2 37.4 3,421 3� 30.7 3,366 3�`
- **CPC-15** (context_loss) Selective-Context at the 3,000-token budget: LongBench AVG 32.0.  
  value: `32.0; 20.7` metric: LongBench AVG; ZeroSCROLLS AVG task: LongBench, ZeroSCROLLS conditions: 3,000 tokens constraint  
  source: cpc-2409.01227.txt p.6 Table 2  
  quote: `Selective-Context 23.3 39.2 25.0 23.8 27.5 53.1 32.0 3,328 3� 20.7 3,460 3�`
- **CPC-16** (context_loss) A second LongLLMLingua row sits in the retrieval-based group of Table 2 (LongBench AVG 46.5 at 3,000 tokens); the table therefore contains two different LongLLMLingua rows per budget.  
  value: `46.5; 29.3` metric: LongBench AVG; ZeroSCROLLS AVG task: LongBench, ZeroSCROLLS conditions: 3,000 tokens constraint; retrieval-based variant  
  source: cpc-2409.01227.txt p.6 Table 2  
  quote: `LongLLMLingua 37.6 42.9 26.9 68.2 49.9 53.4 46.5 3,424 3� 29.3 3,350 3�`
- **CPC-17** (context_loss) CPC at the 2,000-token budget (about 5x): LongBench AVG 49.5, Summ. 23.7, Code 60.00 (as printed), 1,844 tokens left; ZeroSCROLLS AVG 33.8.  
  value: `49.5; 33.8` metric: LongBench AVG; ZeroSCROLLS AVG task: LongBench, ZeroSCROLLS conditions: 2,000 tokens constraint; query-aware; target LLM not stated  
  source: cpc-2409.01227.txt p.6 Table 2  
  quote: `CPC (Ours) 42.6 48.6 23.7 69.4 52.8 60.00 49.5 1,844 5� 33.8 1,821 5�`
- **CPC-18** (context_loss) LongLLMLingua (compression-based) at the 2,000-token budget keeps 1,809 tokens (6x) and scores LongBench AVG 48.0 with Summ. 27.4; it keeps fewer tokens than CPC does in CPC-17.  
  value: `48.0; 32.5` metric: LongBench AVG; ZeroSCROLLS AVG task: LongBench, ZeroSCROLLS conditions: 2,000 tokens constraint; query-aware  
  source: cpc-2409.01227.txt p.6 Table 2  
  quote: `LongLLMLingua 39.0 42.2 27.4 69.3 53.8 56.6 48.0 1,809 6� 32.5 1,753 6�`
- **CPC-19** (context_loss) LLMLingua-2 at the 2,000-token budget: LongBench AVG 39.1; Summ. 25.3.  
  value: `39.1; 33.4` metric: LongBench AVG; ZeroSCROLLS AVG task: LongBench, ZeroSCROLLS conditions: 2,000 tokens constraint; query-agnostic  
  source: cpc-2409.01227.txt p.6 Table 2  
  quote: `LLMLingua-2 29.8 33.1 25.3 66.4 21.3 58.9 39.1 1,954 5� 33.4 1,898 5�`
- **CPC-20** (context_loss) LLMLingua at the 2,000-token budget: LongBench AVG 34.6.  
  value: `34.6; 27.2` metric: LongBench AVG; ZeroSCROLLS AVG task: LongBench, ZeroSCROLLS conditions: 2,000 tokens constraint  
  source: cpc-2409.01227.txt p.6 Table 2  
  quote: `LLMLingua 22.4 32.1 24.5 61.2 10.4 56.8 34.6 1,950 5� 27.2 1,862 5�`
- **CPC-21** (context_loss) Selective-Context at the 2,000-token budget: LongBench AVG 24.8.  
  value: `24.8; 19.4` metric: LongBench AVG; ZeroSCROLLS AVG task: LongBench, ZeroSCROLLS conditions: 2,000 tokens constraint  
  source: cpc-2409.01227.txt p.6 Table 2  
  quote: `Selective-Context 16.2 34.8 24.4 15.7 8.4 49.2 24.8 1,925 5� 19.4 1,865 5�`
- **CPC-22** (context_loss) Table 1 repeats the headline comparison on LongBench but prints a different LLMLingua number than Table 2 (3,000 tokens) does for the same method (see CPC-14).  
  value: `37.2; 9.8x` metric: LongBench AVG; relative latency task: LongBench conditions: Table 1; setting not stated (numbers match the 3,000-token rows of Table 2 except LLMLingua)  
  source: cpc-2409.01227.txt p.1 Table 1  
  quote: `LLMLingua 37.2 9.8�`
- **CPC-23** (context_loss) Table 1 caption: CPC is said to beat LongLLMLingua on both performance and latency (latency column is median relative time, see CPC-34).  
  value: `` metric: LongBench AVG task: LongBench conditions: Table 1  
  source: cpc-2409.01227.txt p.1 Table 1 caption  
  quote: `CPC outperforms LongLLMLingua (SOTA) on both performance and latency`
- **CPC-24** (context_loss) Domain-specific results (Table 3), 2,000-token constraint: CPC 43.5 on Krapivin-2009 keyword extraction vs LLMLingua-2 36.7 and LongLLMLingua 17.1. Columns are Krapivin-2009, PubMed, MeetingBank, SummScreen (header is garbled in the raw text). No uncompressed baseline and no target LLM are given for this table.  
  value: `43.5; 27.59; 17.66; 21.83` metric: keyword recall; Rouge (variant not stated) task: Krapivin-2009, PubMed, MeetingBank, SummScreen conditions: 2,000-token constraint; target LLM not stated; no Original row  
  source: cpc-2409.01227.txt p.6 Table 3  
  quote: `CPC 43.5 27.59 17.66 21.83`
- **CPC-25** (context_loss) Table 3 row for LLMLingua-2 on the same four domain-specific tasks.  
  value: `36.7; 26.24; 16.73; 21.57` metric: keyword recall; Rouge (variant not stated) task: Krapivin-2009, PubMed, MeetingBank, SummScreen conditions: 2,000-token constraint  
  source: cpc-2409.01227.txt p.6 Table 3  
  quote: `LLMLingua-2 36.7 26.24 16.73 21.57`
- **CPC-26** (context_loss) Table 3 row for LongLLMLingua on the same four domain-specific tasks.  
  value: `17.1; 24.31; 14.39; 17.48` metric: keyword recall; Rouge (variant not stated) task: Krapivin-2009, PubMed, MeetingBank, SummScreen conditions: 2,000-token constraint  
  source: cpc-2409.01227.txt p.6 Table 3  
  quote: `LongLLMLingua 17.1 24.31 14.39 17.48`
- **CPC-27** (context_loss) With GPT-4o as backbone (Table 4) CPC averages 52.91 on LongBench; LLMLingua-2 and LongLLMLingua rows are CPC-28 and CPC-29. The caption says 'larger encoder' while the text says GPT-4o is the backbone; token budget is not stated and there is no Original row, so the column meaning is ambiguous.  
  value: `52.91` metric: LongBench AVG task: LongBench conditions: Table 4; GPT-4o backbone per text; budget not stated  
  source: cpc-2409.01227.txt p.7 Table 4  
  quote: `CPC (Ours) 42.43 62.86 25.74 69.25 53.75 63.44 52.91`
- **CPC-28** (context_loss) Table 4 row for LLMLingua-2 with GPT-4o (see CPC-27 for caveats).  
  value: `40.69` metric: LongBench AVG task: LongBench conditions: Table 4; GPT-4o backbone per text  
  source: cpc-2409.01227.txt p.7 Table 4  
  quote: `LLMLingua-2 33.39 52.07 24.88 46.94 27.0 59.84 40.69`
- **CPC-29** (context_loss) Table 4 row for LongLLMLingua with GPT-4o (see CPC-27 for caveats).  
  value: `31.42` metric: LongBench AVG task: LongBench conditions: Table 4; GPT-4o backbone per text  
  source: cpc-2409.01227.txt p.7 Table 4  
  quote: `LongLLMLingua 26.70 39.25 22.66 58.45 13.75 27.73 31.42`
- **CPC-30** (context_loss) Replacing the trained encoder with off-the-shelf MpNet-v2 sentence embeddings gives LongBench AVG 47.2 at the 2,000-token budget; compare CPC-17 (trained encoder) and CPC-18 (LongLLMLingua) at the same budget.  
  value: `47.2` metric: LongBench AVG task: LongBench conditions: 2,000-token budget per Sec. 4.4 ablation text; same selector with off-the-shelf encoder  
  source: cpc-2409.01227.txt p.8 Table 7  
  quote: `MpNet-v2 38.4 47.5 23.5 65.1 40.5 55.5 47.2`
- **CPC-31** (context_loss) Authors' summary of the encoder ablation: off-the-shelf MpNet-v2 and LLM2Vec are 2.3% and 6.6% below the trained encoder on average.  
  value: `2.3%; 6.6%` metric: LongBench AVG task: LongBench conditions: 2,000-token budget  
  source: cpc-2409.01227.txt p.8 Sec. 4.4 Ablation  
  quote: `The average scores for MpNet-v2 and LLM2Vec are 2.3% and 6.6% lower than our proposed context-aware sentence encoder`
- **CPC-32** (context_loss) Authors' note on domain results: CPC beats LLMLingua-2 by 6.8, 1.35, 0.93 and 0.26 points on Krapivin-2009, PubMed, MeetingBank and SummScreen at 2,000 tokens.  
  value: `6.8; 1.35; 0.93; 0.26` metric: points task: Krapivin-2009, PubMed, MeetingBank, SummScreen conditions: 2,000-token constraint  
  source: cpc-2409.01227.txt p.7 Sec. 4.4 Domain generalization  
  quote: `CPC outperforms LLMLingua- 2 by 6.8, 1.35, 0.93, and 0.26 points on Krapivin-2009, PubMed, MeetingBank, and SummScreen, respectively`
- **CPC-33** (latency_compute) Table 5 header: Avg., Med. (absolute time) and Avg. Rel., Med. Rel. (relative to CPC). The caption does not give the absolute unit; Figure 3 labels its time axis in seconds.  
  value: `` metric:  task: LongBench conditions:   
  source: cpc-2409.01227.txt p.7 Table 5 caption  
  quote: `Table 5: Inference latency for different methods. Here, Avg., Med., and Rel., stand for average, median and relative time.`
- **CPC-34** (latency_compute) Table 5, LongLLMLingua: average 7.70, median 1.64, relative 27.5x average and 10.93x median versus CPC. The 10.93x quoted in the abstract is this MEDIAN relative compressor time against LongLLMLingua only.  
  value: `7.70; 1.64; 27.5x; 10.93x` metric: compression-time (unit not stated in caption) task: LongBench sample conditions: compressor stage only; A100; vs LongLLMLingua  
  source: cpc-2409.01227.txt p.7 Table 5  
  quote: `LongLLMLingua 7.70 1.64 27.5� 10.93�`
- **CPC-35** (latency_compute) Table 5, CPC: average 0.28, median 0.15 (relative 1x by definition).  
  value: `0.28; 0.15` metric: compression-time (unit not stated in caption) task: LongBench sample conditions: A100  
  source: cpc-2409.01227.txt p.7 Table 5  
  quote: `CPC 0.28 0.15 1� 1�`
- **CPC-36** (latency_compute) Table 5, LLMLingua-2: average 0.23, median 0.1; relative 0.82x average and 0.67x median, i.e. LLMLingua-2 is FASTER than CPC.  
  value: `0.23; 0.1; 0.82x; 0.67x` metric: compression-time (unit not stated in caption) task: LongBench sample conditions: A100  
  source: cpc-2409.01227.txt p.7 Table 5  
  quote: `LLMLingua-2 0.23 0.1 0.82� 0.67�`
- **CPC-37** (latency_compute) Table 5, LLMLingua: average 4.73, median 1.47; relative 16.89x average and 9.8x median versus CPC.  
  value: `4.73; 1.47; 16.89x; 9.8x` metric: compression-time (unit not stated in caption) task: LongBench sample conditions: A100  
  source: cpc-2409.01227.txt p.7 Table 5  
  quote: `LLMLingua 4.73 1.47 16.89� 9.8�`
- **CPC-38** (hardware) Latency was measured on the same single A100 used for training, as the average processing time over a sample of LongBench.  
  value: `` metric:  task: LongBench conditions: A100 (80G per Sec. 4.2)  
  source: cpc-2409.01227.txt p.7 Sec. 4.4 Latency evaluation  
  quote: `All the evaluations are conducted on the same A100 GPU used for training`
- **CPC-39** (latency_compute) The authors state CPC is faster than LLMLingua and LongLLMLingua by up to 27.5x (average) and 10.93x (median).  
  value: `27.5x; 10.93x` metric: relative compressor time task: LongBench sample conditions: vs LLMLingua and LongLLMLingua; LLMLingua-2 faster  
  source: cpc-2409.01227.txt p.7 Sec. 4.4 Latency evaluation  
  quote: `our method is significantly faster than LLMLingua and LongLLMLingua, showing up to 27.5� and 10.93� average and median speedup`
- **CPC-40** (latency_compute) Authors say CPC latency scales linearly with input length and is agnostic to text structure, whereas LongLLMLingua latency depends on text structure.  
  value: `` metric:  task: LongBench sample conditions: Figure 3  
  source: cpc-2409.01227.txt p.7 Sec. 4.4 Latency evaluation  
  quote: `the time complexity of our approach scales linearly with the growing length of the input context`
- **CPC-41** (latency_compute) Figure 3 plots processing time against original token length with the axis labelled in thousands of tokens (ticks 0 to 16), so latency was characterised up to roughly 16k-token inputs.  
  value: `0 to 16 (x1,000 tokens)` metric:  task: LongBench sample conditions: Figure 3 axis labels  
  source: cpc-2409.01227.txt p.6 Figure 3  
  quote: `0 2 4 6 8 10 12 14 16 Original token length (x 1,000)`
- **CPC-42** (latency_compute) Training cost: 2048 samples, batch size 32, one A100 80G GPU. Training wall-clock time is not reported.  
  value: `2048 samples; batch 32` metric:  task:  conditions: LoRA rank 16 on Mistral-7B-Instruct-v0.2  
  source: cpc-2409.01227.txt p.5 Sec. 4.2  
  quote: `We train the model with 2048 samples with a batch size 32`
- **CPC-43** (hardware) Training hardware: a single A100 80G GPU.  
  value: `` metric:  task:  conditions:   
  source: cpc-2409.01227.txt p.5 Sec. 4.2  
  quote: `The training is conducted on a single A100 80G GPU`
- **CPC-44** (cost) Building the training set required an OpenAI gpt-3.5-turbo-instruct call stream (question/answer generation) plus Phi-3-small-128k-instruct for probability filtering; dollar and token cost of data generation are not reported.  
  value: `` metric:  task:  conditions: one-off training-data cost, not per request  
  source: cpc-2409.01227.txt p.5 Sec. 4.2  
  quote: `gpt-3.5-turbo-instruct and microsoft/Phi-3-small-128k- instruct respectively`
- **CPC-45** (cost) Tokens saved per request: the uncompressed LongBench prompts average 10,295 tokens (this row); compressed sizes are in CPC-11 and CPC-17. CPC needs a local 7B encoder forward pass over the whole context as extra compute (no extra LLM API call, inferred from mechanism); end-to-end target-LLM latency/cost saving is not reported.  
  value: `10,295` metric: tokens task: LongBench conditions: avg tokens from Table 2  
  source: cpc-2409.01227.txt p.6 Table 2  
  quote: `Original Prompt 39.7 38.7 26.5 67.0 37.8 54.2 44.0 10,295 - 32.5 9,788 -`
- **CPC-46** (limitation) The paper has no limitations or failure-analysis section; the conclusion lists only strengths. Reported as 'not reported'.  
  value: `not reported` metric:  task:  conditions:   
  source: cpc-2409.01227.txt p.8 Sec. 5 Conclusion  
  quote: `Additionally, our method shows strong domain generalization and robust performance with larger encoders.`
- **CPC-47** (limitation) The target LLM used for Table 2 and Table 3 is not named anywhere in the paper text (only GPT-4o for Table 4 is named). Reported as 'not reported'.  
  value: `not reported` metric:  task:  conditions:   
  source: cpc-2409.01227.txt p.5 Sec. 4.3  
  quote: `We perform various experiments on several downstream tasks based on commonly used protocols.`
- **CPC-48** (limitation) The paper does not say what 'question' CPC uses for tasks with no natural question (code completion, summarization, synthetic tasks) although it reports them; reported as 'not reported'.  
  value: `not reported` metric: Levenshtein similarity task: LongBench Code conditions:   
  source: cpc-2409.01227.txt p.5 Sec. 4.3  
  quote: `For code completion tasks, we use the textual similarity metric based on the Levenshtein edit distance`
- **CPC-49** (limitation) Training data are synthetic questions generated from WikiText (Wikipedia) pages, so encoder training is Wikipedia/English-factual in domain; languages and max input length are not discussed.  
  value: `` metric:  task: CQR training set conditions:   
  source: cpc-2409.01227.txt p.3 Sec. 3.2  
  quote: `This dataset consists of long Wikipedia pages, each containing factual information about historical/scientific concepts.`
- **CPC-50** (limitation) Maximum input length of the compressor is not stated as a limit; the only statement is that the chosen base model allows long context lengths. Reported as 'not reported'.  
  value: `not reported` metric:  task:  conditions:   
  source: cpc-2409.01227.txt p.5 Sec. 4.2  
  quote: `given that it is open-source and allows for long context lengths`
- **CPC-51** (limitation) Failure pattern visible in Table 2: CPC's LongBench Summ. column (23.8 at 3,000 tokens) is below the Summ. entries of LLMLingua-2 (CPC-13) and LongLLMLingua (CPC-12) and the Original row (CPC-9); the authors do not comment on it. Extractive question-conditioned selection is a likely cause (inference, not an author statement).  
  value: `23.8` metric: Summ. column task: LongBench summarization conditions: 3,000 tokens constraint  
  source: cpc-2409.01227.txt p.6 Table 2  
  quote: `CPC (Ours) 42.7 47.9 23.8 69.3 52.8 63.5 50.0 3,327 3� 34.9 3,470 3�`
- **CPC-52** (reproducibility) Code and the CQR dataset are announced as released at the Workday GitHub repository.  
  value: `` metric:  task:  conditions:   
  source: cpc-2409.01227.txt p.1 Abstract  
  quote: `we release the code and the dataset for quick reproducibility and further development: https://github.com/Workday/cpc`
- **CPC-53** (reproducibility) The official repository declares the Apache License 2.0 (LICENSE file title as returned by WebFetch of the raw file, 2026-11-05).  
  value: `Apache-2.0` metric:  task:  conditions:   
  source: https://raw.githubusercontent.com/Workday/cpc/main/LICENSE LICENSE  
  quote: `Apache License`
- **CPC-54** (reproducibility) Official README says the original CQR dataset is on Hugging Face (WebFetch of raw README, 2026-11-05; checkpoint details are in the notes file).  
  value: `` metric:  task:  conditions:   
  source: https://raw.githubusercontent.com/Workday/cpc/main/README.md README  
  quote: `Original CQR dataset can be found on`
- **CPC-55** (tasks_tested) Long-document QA tested: LongBench SingleDoc/MultiDoc QA; the SingleDoc subset consists of NarrativeQA, Qasper and MultiFieldQA-en.  
  value: `tested` metric: F1 task: LongBench SingleDoc (NarrativeQA, Qasper, MultiFieldQA-en), MultiDoc conditions:   
  source: cpc-2409.01227.txt p.8 Sec. 4.4 Ablation  
  quote: `Doc consisting of NarrativeQA, Qasper and MultiFieldQa- en datasets`
- **CPC-56** (tasks_tested) Summarization tested: LongBench/ZeroSCROLLS summarization plus PubMed (medical papers), MeetingBank (meeting transcripts) and SummScreen (TV shows); keyword extraction (Krapivin) also tested.  
  value: `tested` metric: Rouge; keyword recall task: LongBench Summ., ZeroSCROLLS, PubMed, MeetingBank, SummScreen, Krapivin conditions:   
  source: cpc-2409.01227.txt p.5 Sec. 4.1  
  quote: `We also evaluate on domain-specific benchmarks such as medical paper summa- rization (PubMed (Cohan et al. 2018)), keyword extraction`
- **CPC-57** (tasks_tested) Coding tested only through the LongBench 'Code' column, scored with Levenshtein-edit-distance similarity; the paper does not name the code datasets.  
  value: `tested (LongBench Code)` metric: Levenshtein similarity task: LongBench Code conditions:   
  source: cpc-2409.01227.txt p.5 Sec. 4.3  
  quote: `For code completion tasks, we use the textual similarity metric based on the Levenshtein edit distance`
- **CPC-58** (tasks_tested) Multi-turn chat is not tested: the paper's dataset list (LongBench, ZeroSCROLLS, PubMed, Krapivin, MeetingBank, SummScreen) contains no multi-turn chat benchmark. MeetingBank is meeting-transcript summarization.  
  value: `not tested in paper` metric:  task:  conditions:   
  source: cpc-2409.01227.txt p.5 Sec. 4.1  
  quote: `keyword extraction (Krapivin (Krapivin et al. 2009)), meeting transcript sum- marization (MeetingBank (Hu et al. 2023)) and TV show summarization (SummScreen (Chen et al. 2021)) datasets.`
- **CPC-59** (tasks_tested) Structured data (JSON/tables/logs) is not tested: no such dataset appears in the paper's dataset list; LongBench 'Synth.' tasks are not described.  
  value: `not tested in paper` metric:  task:  conditions:   
  source: cpc-2409.01227.txt p.5 Sec. 4.1  
  quote: `is another dataset with different sub-tasks, including sum- marization, QA, and few-shot learning.`
- **CPC-60** (tasks_tested) Reasoning/math (e.g. GSM8K) and sensitive/PII content are not tested: neither appears in the paper's dataset list. Medical content appears only as PubMed paper summarization.  
  value: `not tested in paper` metric:  task:  conditions:   
  source: cpc-2409.01227.txt p.5 Sec. 4.1  
  quote: `keyword extraction (Krapivin (Krapivin et al. 2009)), meeting transcript sum- marization (MeetingBank (Hu et al. 2023)) and TV show summarization (SummScreen (Chen et al. 2021)) datasets.`
- **CPC-62** (latency_compute) Figure 3 labels its time axis 'Processing time (sec)', so the Table 5 absolute numbers are presumably seconds (Table 5's caption does not say).  
  value: `` metric: sec task: LongBench sample conditions: Figure 3 axis label  
  source: cpc-2409.01227.txt p.6 Figure 3  
  quote: `Processing time (sec)`

## EHPC

- **EH-001** (mechanism) EHPC is described by its authors as a training-free prompt compression method that keeps key information in the compressed prompt.  
  value: `` metric:  task:  conditions:   
  source: ehpc-2501.12959.txt p.1 Abstract  
  quote: `an efficient, training-free prompt compression method that retains key information within compressed prompts`
- **EH-002** (mechanism) EHPC runs only the first layers of a transformer that contain evaluator heads during pre-filling to score tokens, then passes only the important tokens to the model for inference.  
  value: `` metric:  task:  conditions:   
  source: ehpc-2501.12959.txt p.1 Abstract  
  quote: `subsequently passing only the important tokens to the model for inference`
- **EH-003** (mechanism) EHPC is a token-deletion method: it shortens the prompt by dropping tokens, so its output is a shorter text prompt.  
  value: `` metric:  task:  conditions:   
  source: ehpc-2501.12959.txt p.4 Sec. 3.1  
  quote: `compresses the prompt by dropping non-essential tokens directly`
- **EH-004** (mechanism) The compressed prompt stays in natural-language form but can miss context; the authors say so explicitly.  
  value: `` metric:  task:  conditions:   
  source: ehpc-2501.12959.txt p.6 Sec. 3.4  
  quote: `Although the compressed prompt retains its natural language form, it may lack certain contextual elements.`
- **EH-005** (mechanism) EHPC borrows SnapKV's pooling idea to keep neighbouring tokens together, so retained tokens form contiguous spans rather than isolated tokens.  
  value: `` metric:  task:  conditions:   
  source: ehpc-2501.12959.txt p.6 Sec. 3.4  
  quote: `we adopt a pooling operation, as described in (Li et al., 2024), to group neighboring tokens with similar scores`
- **EH-006** (mechanism) Qualitative example of EHPC output (Appendix G): the compressed prompt is a set of text fragments, not fluent prose.  
  value: `` metric:  task:  conditions: Appendix G example from a narrative text  
  source: ehpc-2501.12959.txt p.19 Appendix G  
  quote: `carried Kay and Gerda, first to Finn woman.`
- **EH-007** (mechanism) Evaluator heads are found with a one-time pilot experiment on synthetic Needle-in-a-Haystack data (no gradient training, but a per-model calibration step).  
  value: `` metric:  task: Needle-in-a-Haystack (synthetic) conditions:   
  source: ehpc-2501.12959.txt p.2 Sec. 1  
  quote: `To identify these evaluator heads, we design a pilot experiment using synthetic data (see Figure 1).`
- **EH-008** (mechanism) Evaluator heads are sparse and sit mostly in the middle layers (not only in the first layers).  
  value: `` metric:  task:  conditions:   
  source: ehpc-2501.12959.txt p.7 Sec. 4 Existence  
  quote: `predominantly concentrated in the middle layers`
- **EH-009** (mechanism) For Llama-3.1-8B-Instruct the selected evaluator layer is 13 of 32; heads are model-specific (indices differ per model).  
  value: `13` metric:  task:  conditions: Llama-3.1-8B-Instruct, 32 layers x 32 heads  
  source: ehpc-2501.12959.txt p.15 Appendix B  
  quote: `which has 32 layers and 32 heads, the selected layer is 13, and the chosen heads are [18, 13, 21, 8, 11, 1, 4, 3]`
- **EH-010** (mechanism) For Phi-3.5-mini-3.8B-Instruct the selected evaluator layer is 17 and the heads differ from Llama's, so heads must be re-identified per model.  
  value: `17` metric:  task:  conditions: Phi-3.5-mini-3.8B-Instruct  
  source: ehpc-2501.12959.txt p.15 Appendix B  
  quote: `the selected layer is 17, and the chosen heads are [7, 17, 30, 2, 6, 16, 25, 18]`
- **EH-011** (mechanism) Hyper-parameters for Llama-3.1-8B-Instruct: observation window 16 tokens, pooling kernel 32 (average pooling).  
  value: `16; 32` metric:  task:  conditions: Llama-3.1-8B-Instruct  
  source: ehpc-2501.12959.txt p.15 Appendix B  
  quote: `we set the size of the observed windows and the kernel size for pooling to 16 and 32, respectively`
- **EH-012** (mechanism) Token scores come from the attention rows of the final positions of the prompt (observation window). Inferred from mechanism: the question/instruction must be inside the text given to the evaluator; the paper does not discuss query-agnostic use.  
  value: `` metric:  task:  conditions: inferred from mechanism  
  source: ehpc-2501.12959.txt p.5 Sec. 3.3  
  quote: `We then extract the last row of the attention matrix`
- **EH-020** (io) EHPC needs a locally run LLM (with access to attention scores) to compress the prompt.  
  value: `` metric:  task:  conditions:   
  source: ehpc-2501.12959.txt p.2 Sec. 1  
  quote: `The proposed EHPC requires the local development of LLMs for prompt compression`
- **EH-021** (io) The paper states that EHPC's compressed prompts are text and can be sent to API-based black-box models (compression itself still runs locally).  
  value: `` metric:  task:  conditions:   
  source: ehpc-2501.12959.txt p.6 Sec. 3.4  
  quote: `and can be applied to API-based black-box large models`
- **EH-022** (io) In Extended Model Inference (EMI) the model that reads the compressed prompt is different from the evaluator model; in NMI it is the same model.  
  value: `` metric:  task:  conditions:   
  source: ehpc-2501.12959.txt p.6 Sec. 3.4  
  quote: `involves using a different language model to infer the compressed prompt`
- **EH-023** (io) Authors recommend a compression model with strong long-context ability, small for efficient deployment, e.g. Llama-3.1-8B with 128k context.  
  value: `8B; 128k` metric:  task:  conditions:   
  source: ehpc-2501.12959.txt p.6 Sec. 3.4  
  quote: `smaller models are preferred for efficient deployment, such as Llama-3.1-8B, with a context length of 128k`
- **EH-024** (io) In the prompt-compression benchmark EHPC used Llama-3.1-8B as the local compressor/evaluator.  
  value: `8B` metric:  task: LongBench, ZeroSCROLLS conditions: compressor model for Table 4  
  source: ehpc-2501.12959.txt p.8 Sec. 5.1  
  quote: `For prompt compression, we utilize the Llama-3.1-8B model`
- **EH-025** (io) Footnote 1 links the compressor model to meta-llama/Meta-Llama-3-8B although the text says Llama-3.1-8B; the exact checkpoint is ambiguous.  
  value: `` metric:  task:  conditions:   
  source: ehpc-2501.12959.txt p.8 Sec. 5.1 footnote 1  
  quote: `available at: https://huggingface.co/meta-llama/Meta-Llama-3-8B`
- **EH-026** (limitation) The paper does not name the target (inference) LLM used for the Table 4 EMI results; it says only 'another model'. No result is attributed to a named closed API model.  
  value: `not reported` metric:  task: LongBench, ZeroSCROLLS conditions: Table 4 target LLM  
  source: ehpc-2501.12959.txt p.8 Sec. 5.1  
  quote: `We compare our EMI setting, which employs a local LLM for prompt compression and another model for inferring the compressed prompts`
- **EH-027** (io) The only closed model named in the results is ChatGPT-3.5-Turbo, as a full-prompt latency baseline whose inference time is carried over from Liskavets et al.; no accuracy for a closed target is attributed to it.  
  value: `` metric:  task:  conditions: Table 5 caption  
  source: ehpc-2501.12959.txt p.9 Table 5 caption  
  quote: `serves as the baseline using the original prompts, where the inference time is carried over from (Liskavets et al., 2024)`
- **EH-028** (io) Related work frames the field as implicit methods (reduce the KV cache) versus explicit methods (decrease tokens); the authors place EHPC with the explicit methods, which can serve black-box LLMs.  
  value: `` metric:  task:  conditions:   
  source: ehpc-2501.12959.txt p.3 Sec. 2  
  quote: `explicit methods, which can be applied to black-box LLMs such as GPT-3.5-Turbo`
- **EH-029** (io) The authors define the two families: KV-cache methods are 'implicit', token-reduction methods are 'explicit'.  
  value: `` metric:  task:  conditions:   
  source: ehpc-2501.12959.txt p.3 Sec. 2  
  quote: `implicit methods that reduce the KV cache, and explicit methods that decrease the number of tokens`
- **EH-030** (io) The authors distinguish evaluator heads (which act explicitly on tokens) from retrieval heads used by KV-cache methods (which act implicitly on the KV cache).  
  value: `` metric:  task:  conditions:   
  source: ehpc-2501.12959.txt p.4 Sec. 3.2  
  quote: `evaluator heads operate explicitly on the tokens, in contrast to the retrieval heads`
- **EH-031** (io) EHPC differs from most KV-cache methods in using only the scores of selected evaluator heads, not all heads.  
  value: `` metric:  task:  conditions:   
  source: ehpc-2501.12959.txt p.2 Sec. 1  
  quote: `most KV cache compression methods preserve the cache according to all heads`
- **EH-039** (context_loss) Table 4 column header for LongBench categories and Avg; columns are SingleDoc, MultiDoc, Summ., FewShot, Synth., Code, Avg., # Tokens, compression ratio, then ZeroSCROLLS Avg., # Tokens, ratio.  
  value: `` metric:  task: LongBench conditions: column map  
  source: ehpc-2501.12959.txt p.8 Table 4 header  
  quote: `SingleDoc MultiDoc Summ. FewShot Synth. Code Avg. # Tokens`
- **EH-040** (context_loss) Uncompressed prompt reference: LongBench average 44.0 over ~10,295 tokens; ZeroSCROLLS average 32.5 over 9,788 tokens.  
  value: `LongBench Avg 44.0; Code 54.2; ZeroSCROLLS 32.5` metric: LongBench task metrics (F1, Rouge-L, accuracy, EM, edit sim.); ZeroSCROLLS task: LongBench, ZeroSCROLLS conditions: Original Prompt; target LLM not stated  
  source: ehpc-2501.12959.txt p.8 Table 4  
  quote: `Original Prompt 39.7 38.7 26.5 67.0 37.8 54.2 44.0 10,295 - 32.5 9,788 -`
- **EH-041** (compression_ratio) EHPC (EMI) at the 3,000-token constraint: 2,892 tokens (3x); LongBench average 49.7 vs 44.0 for the full prompt; code column 63.0 vs 54.2; ZeroSCROLLS 36.7 vs 32.5.  
  value: `LongBench Avg 49.7; 3x; Code 63.0; Summ 25.1; ZeroSCROLLS 36.7` metric: LongBench avg; ZeroSCROLLS avg task: LongBench, ZeroSCROLLS conditions: 3,000-token constraint; compressor Llama-3.1-8B; target LLM not stated; query-aware  
  source: ehpc-2501.12959.txt p.8 Table 4  
  quote: `EHPC (EMI) 44.2 49.1 25.1 68.8 54.0 63.0 49.7 2,892 3� 36.7 3,005 3�`
- **EH-042** (compression_ratio) EHPC (EMI) at the 2,000-token constraint: 2,004 tokens (5x); LongBench average 49.6 vs 44.0 full prompt; summarization column 24.8 vs 26.5 full prompt; code 61.9 vs 54.2; ZeroSCROLLS 34.6.  
  value: `LongBench Avg 49.6; 5x; Summ 24.8; Code 61.9; ZeroSCROLLS 34.6` metric: LongBench avg; ZeroSCROLLS avg task: LongBench, ZeroSCROLLS conditions: 2,000-token constraint; compressor Llama-3.1-8B; target LLM not stated; query-aware  
  source: ehpc-2501.12959.txt p.8 Table 4  
  quote: `EHPC (EMI) 44.5 50.7 24.8 68.9 51.5 61.9 49.6 2,004 5� 34.6 2,041 5�`
- **EH-043** (context_loss) LongLLMLingua at 3,000 tokens in the same table: LongBench average 48.8, code column 55.2.  
  value: `LongBench Avg 48.8; Code 55.2` metric: LongBench avg task: LongBench, ZeroSCROLLS conditions: 3,000-token constraint; target LLM not stated  
  source: ehpc-2501.12959.txt p.8 Table 4  
  quote: `LongLLMLingua 40.7 46.2 27.2 70.6 53.0 55.2 48.8 3,283 3� 32.8 3,412 3�`
- **EH-044** (context_loss) LongLLMLingua at 2,000 tokens in the same table: LongBench average 48.0, code column 56.6.  
  value: `LongBench Avg 48.0; Code 56.6` metric: LongBench avg task: LongBench, ZeroSCROLLS conditions: 2,000-token constraint; target LLM not stated  
  source: ehpc-2501.12959.txt p.8 Table 4  
  quote: `LongLLMLingua 39.0 42.2 27.4 69.3 53.8 56.6 48.0 1,809 6� 32.5 1,753 6�`
- **EH-045** (context_loss) LLMLingua-2 at 3,000 tokens in the same table: LongBench average 42.2, code column 62.8.  
  value: `LongBench Avg 42.2; Code 62.8` metric: LongBench avg task: LongBench, ZeroSCROLLS conditions: 3,000-token constraint; target LLM not stated  
  source: ehpc-2501.12959.txt p.8 Table 4  
  quote: `LLMLingua-2 35.5 38.7 26.3 69.6 21.4 62.8 42.2 3,392 3� 33.5 3,206 3�`
- **EH-046** (context_loss) LLMLingua-2 at 2,000 tokens in the same table: LongBench average 39.1, code column 58.9.  
  value: `LongBench Avg 39.1; Code 58.9` metric: LongBench avg task: LongBench, ZeroSCROLLS conditions: 2,000-token constraint; target LLM not stated  
  source: ehpc-2501.12959.txt p.8 Table 4  
  quote: `LLMLingua-2 29.8 33.1 25.3 66.4 21.3 58.9 39.1 1,954 5� 33.4 1,898 5�`
- **EH-047** (context_loss) RAG-style baseline in the same table: OpenAI-embedding retrieval at 3,000 tokens gets LongBench average 41.7 and code column 37.6.  
  value: `LongBench Avg 41.7; Code 37.6` metric: LongBench avg task: LongBench conditions: 3,000-token constraint (retrieval, not compression); target LLM not stated  
  source: ehpc-2501.12959.txt p.8 Table 4  
  quote: `OpenAI 34.5 38.6 26.8 63.4 49.6 37.6 41.7 3,421 3� 22.4 3,362 3�`
- **EH-048** (context_loss) RAG-style baseline at 2,000 tokens: OpenAI-embedding retrieval LongBench average 29.8, few-shot column 32.4.  
  value: `LongBench Avg 29.8; FewShot 32.4` metric: LongBench avg task: LongBench conditions: 2,000-token constraint; target LLM not stated  
  source: ehpc-2501.12959.txt p.8 Table 4  
  quote: `OpenAI 34.3 36.3 24.7 32.4 26.3 24.8 29.8 1,991 5� 20.6 1,784 5�`
- **EH-049** (compression_ratio) Compression ratio in the latency experiment: average prompt length reduced from 14,354 to 2,048 tokens.  
  value: `14,354 -> 2,048 tokens` metric:  task: RepoBench-P subset (10 examples) conditions: all methods in Table 5  
  source: ehpc-2501.12959.txt p.9 Sec. 5.1 Compression Latency  
  quote: `Each prompt compression method reduces the average prompt length from 14,354 tokens to 2,048 tokens`
- **EH-050** (context_loss) Authors report EHPC beats the original prompts on QA tasks (they attribute it to removing noisy context).  
  value: `` metric:  task: LongBench QA conditions: Table 4  
  source: ehpc-2501.12959.txt p.9 Sec. 5.1 Results  
  quote: `The results show that EHPC surpasses the original prompts and significantly enhances the accuracies of the QA tasks`
- **EH-051** (context_loss) Authors say EHPC performs well on LongBench code tasks (LCC, RepoBench-P) in the prompt-compression setting.  
  value: `` metric: EM task: LongBench code (LCC, RepoBench-P) conditions: Table 4  
  source: ehpc-2501.12959.txt p.9 Sec. 5.1 Results  
  quote: `our model performs well on code tasks in the LongBench`
- **EH-052** (context_loss) Authors describe EHPC on summarization and few-shot tasks as only 'competitive' (Table 4 summarization is below the full prompt: 24.8-25.1 vs 26.5).  
  value: `` metric: Rouge-L (summarization), mixed (few-shot) task: LongBench Summ., FewShot conditions: Table 4  
  source: ehpc-2501.12959.txt p.9 Sec. 5.1 Results  
  quote: `the performance of EHPC on summarization and few-shot learning tasks is competitive`
- **EH-053** (context_loss) Table 6 Llama 3.1 8B Instruct full-KV baseline (columns NrtvQA..LCC then Average): average 38.32; RepoBench-P 49.25, LCC 52.7.  
  value: `Avg 38.32; RepoBench-P 49.25; LCC 52.7` metric: LongBench task metrics task: LongBench conditions: All KV; Llama-3.1-8B-Instruct  
  source: ehpc-2501.12959.txt p.10 Table 6  
  quote: `All KV 32.02 13.04 27.34 16.23 16.05 11.22 34.52 23.41 26.89 73.0 91.64 43.8 7.16 97.73 49.25 52.7 38.32`
- **EH-054** (context_loss) EHPC with a 1024-token budget on Llama 3.1 8B: printed average 35.23 (vs 38.32 full KV); RepoBench-P 42.8 and LCC 48.9 (vs 49.25 and 52.7); PassageRetrieval 97.21.  
  value: `Avg 35.23; RepoBench-P 42.8; LCC 48.9` metric: LongBench task: LongBench conditions: EHPC-1024; Llama-3.1-8B-Instruct; NMI  
  source: ehpc-2501.12959.txt p.10 Table 6  
  quote: `EHPC (ours)-1024 22.98 13.02 27.41 20.64 16.97 13.99 29.49 24.15 25.24 68.0 86.52 41.86 5.79 97.21 42.8 48.9 35.23`
- **EH-055** (context_loss) EHPC with a 2048-token budget on Llama 3.1 8B: printed average 37.86 (vs 38.32 full KV); RepoBench-P 44.9, LCC 52.2.  
  value: `Avg 37.86; RepoBench-P 44.9; LCC 52.2` metric: LongBench task: LongBench conditions: EHPC-2048; Llama-3.1-8B-Instruct; NMI  
  source: ehpc-2501.12959.txt p.10 Table 6  
  quote: `EHPC (ours)-2048 20.98 14.38 30.50 19.35 16.23 13.02 32.9 24.54 26.72 71.0 90.47 42.24 9.35 97.94 44.9 52.2 37.86`
- **EH-060** (context_loss) Table 6 Phi 3.5 Mini 3.8B Instruct full-KV baseline: printed average 34.62; SAMSum 13.08; HotpotQA 21.70; Qasper 17.23.  
  value: `Avg 34.62` metric: LongBench task: LongBench conditions: All KV; Phi-3.5-mini-3.8B-Instruct  
  source: ehpc-2501.12959.txt p.10 Table 6  
  quote: `All KV 27.51 17.23 35.63 21.70 25.70 11.68 34.14 23.17 24.95 71.5 87.37 13.08 7.17 83.85 46.0 46.2 34.62`
- **EH-061** (context_loss) EHPC with a 1024-token budget on Phi 3.5 Mini: printed average 39.22 (above the 34.62 full-KV baseline), driven by Qasper 32.22 and HotpotQA 44.97; RepoBench-P 38.7 and LCC 41.6 are below full KV (46.0, 46.2).  
  value: `Avg 39.22; RepoBench-P 38.7; LCC 41.6` metric: LongBench task: LongBench conditions: EHPC-1024; Phi-3.5-mini-3.8B-Instruct; NMI  
  source: ehpc-2501.12959.txt p.10 Table 6  
  quote: `EHPC (ours)-1024 23.91 32.22 45.36 44.97 32.79 20.27 31.90 22.19 23.77 68.5 85.72 36.69 1.80 79.08 38.7 41.6 39.22`
- **EH-062** (context_loss) EHPC with a 2048-token budget on Phi 3.5 Mini: printed average 36.46; PassageRetrieval 63.00 (vs 83.85 full KV); RepoBench-P 47.31, LCC 45.44.  
  value: `Avg 36.46; PRe 63.00` metric: LongBench task: LongBench conditions: EHPC-2048; Phi-3.5-mini-3.8B-Instruct; NMI  
  source: ehpc-2501.12959.txt p.10 Table 6  
  quote: `EHPC (ours)-2048 24.80 39.27 39.78 27.06 25.22 14.05 33.26 23.52 24.48 68.0 87.66 37.77 2.54 63.00 47.31 45.44 36.46`
- **EH-065** (context_loss) Authors' text claims EHPC has the best average across compression rates in Table 6 (note: for Llama at 1024 the printed SnapKV average 35.25 is 0.02 above EHPC's 35.23).  
  value: `` metric:  task: LongBench conditions: Table 6; authors' claim  
  source: ehpc-2501.12959.txt p.10 Sec. 5.2 Results  
  quote: `EHPC achieves the best average performance compared to the baselines across different compression rates`
- **EH-066** (context_loss) Authors say prompt compression declines on code-related and few-shot tasks in the NMI/KV-cache comparison.  
  value: `` metric:  task: LongBench code, few-shot conditions: Table 6, NMI  
  source: ehpc-2501.12959.txt p.10 Sec. 5.2 Results  
  quote: `prompt compression exhibits a decline in performance on code-related tasks and few-shot learning tasks`
- **EH-067** (limitation) Authors state KV-cache compression stays more advantageous than prompt compression on code and few-shot tasks as memory shrinks.  
  value: `` metric:  task: LongBench code, few-shot conditions: Table 6  
  source: ehpc-2501.12959.txt p.10 Sec. 5.2 Results  
  quote: `it remains more advantageous than prompt compression for these tasks`
- **EH-068** (context_loss) Authors report that on Phi-3.8B EHPC improves direct-inference performance on QA tasks by up to 40% on average.  
  value: `up to 40%` metric: avg of QA task scores task: LongBench Single-/Multi-Doc QA conditions: Phi-3.5-mini-3.8B-Instruct, NMI, Table 6  
  source: ehpc-2501.12959.txt p.10 Sec. 5.2 Results  
  quote: `enhancing its performance on direct inference by an average of up to 40% averaged on QA tasks`
- **EH-069** (compression_ratio) Table 6 budgets: target lengths 1024 and 2048 tokens (wording ambiguous about which applies to prompt vs KV compression).  
  value: `1024; 2048` metric:  task: LongBench conditions: NMI; Llama-3.1-8B, Phi-3.8B  
  source: ehpc-2501.12959.txt p.10 Sec. 5.2 Implementation Detail  
  quote: `we set the target lengths to 1024 and 2048 tokens for prompt compression and KV cache compression respectively`
- **EH-070** (io) NMI target models are Llama-3.1-8B and Phi-3.8B, both with a 128k context window.  
  value: `8B; 3.8B; 128k` metric:  task:  conditions:   
  source: ehpc-2501.12959.txt p.10 Sec. 5.2 Implementation Detail  
  quote: `We utilize two popular long-context models: Llama-3.1-8B and Phi-3.8B`
- **EH-071** (context_loss) Head-set ablation on LongBench: evaluator heads beat comparison heads from the same layer (MF-en 27.7 vs 24.3; Musique 13.7 vs 12.1; TREC 62.5 vs 60.5).  
  value: `27.7; 13.7; 62.5` metric: task metrics task: MF-en, Musique, TREC conditions: 4 evaluator vs 4 comparison heads  
  source: ehpc-2501.12959.txt p.7 Table 2  
  quote: `Evaluator heads 27.7 13.7 62.5`
- **EH-072** (context_loss) Heads found from synthetic code/multi-hop probe data did not significantly beat heads found from simple QA data (multi-hop 16.40 vs 16.87; code 47.86 vs 47.72), so one QA-derived head set is used for all tasks.  
  value: `16.40 vs 16.87; 47.86 vs 47.72` metric: task metrics task: LongBench multi-hop, code conditions: Table 3  
  source: ehpc-2501.12959.txt p.7 Table 3  
  quote: `Evaluator heads (QA) 16.40 47.86`
- **EH-080** (latency_compute) Table 1: EHPC compression latency 0.88 s vs LongLLMLingua 67.44 s, LLMLingua 7.51 s, LLMLingua-2 1.27 s (2048-token target).  
  value: `0.88` metric: seconds task: LongBench conditions: 2048-token compressed prompt; see Table 5 for setup  
  source: ehpc-2501.12959.txt p.1 Table 1  
  quote: `EHPC (ours) 49.6 0.88`
- **EH-081** (latency_compute) Table 1: LongLLMLingua average LongBench performance 48.0 and latency 67.44.  
  value: `67.44` metric: seconds task: LongBench conditions: 2048 tokens  
  source: ehpc-2501.12959.txt p.1 Table 1  
  quote: `LongLLMLingua 48.0 67.44`
- **EH-082** (latency_compute) Table 1: LLMLingua average LongBench performance 34.6 and latency 7.51 (Table 5 labels this row LLMLingua-2 by mistake).  
  value: `7.51` metric: seconds task: LongBench conditions: 2048 tokens  
  source: ehpc-2501.12959.txt p.1 Table 1  
  quote: `LLMLingua 34.6 7.51`
- **EH-083** (latency_compute) Table 5: EHPC compression 0.88 s + inference 1.11 s = 1.99 s total, vs 2.16 s for ChatGPT-3.5-Turbo on the full 14k-token prompt (inference time borrowed from another paper).  
  value: `0.88; 1.11; 1.99; 2.16` metric: seconds task: RepoBench-P subset conditions: compression to 2,048 tokens; columns: compression time, inference time (2048 tokens), total; 5 repeats  
  source: ehpc-2501.12959.txt p.9 Table 5  
  quote: `EHPC (ours) 0.88 1.11 1.99`
- **EH-084** (latency_compute) Table 5: LongLLMLingua compression 67.44 s, total 68.74 s.  
  value: `67.44; 68.74` metric: seconds task: RepoBench-P subset conditions: same setup  
  source: ehpc-2501.12959.txt p.9 Table 5  
  quote: `LongLLMLingua 67.44 1.31 68.74`
- **EH-085** (latency_compute) Table 5: LLMLingua-2 compression 1.27 s, total 2.37 s.  
  value: `1.27; 2.37` metric: seconds task: RepoBench-P subset conditions: same setup  
  source: ehpc-2501.12959.txt p.9 Table 5  
  quote: `LLMLingua-2 1.27 1.15 2.37`
- **EH-086** (latency_compute) Table 5: full-prompt baseline (ChatGPT-3.5-Turbo, all tokens) 2.16 s.  
  value: `2.16` metric: seconds task: RepoBench-P subset conditions: inference time carried over from Liskavets et al.  
  source: ehpc-2501.12959.txt p.9 Table 5  
  quote: `ChatGPT-3.5-Turbo (all tokens) 2.16`
- **EH-087** (hardware) Latency experiments ran on one GPU with 40GB VRAM; the GPU model is not named.  
  value: `40GB VRAM` metric:  task:  conditions: GPU type not stated  
  source: ehpc-2501.12959.txt p.9 Sec. 5.1 Compression Latency  
  quote: `The experiments were conducted on a GPU with 40GB of VRAM`
- **EH-088** (latency_compute) Latency benchmark data: 10 RepoBench-P examples averaging 14,354 tokens, each repeated 5 times.  
  value: `14,354 tokens; 10 examples; 5 repeats` metric:  task: RepoBench-P conditions:   
  source: ehpc-2501.12959.txt p.9 Table 5 caption  
  quote: `The subset contains 10 examples from RepoBench-P, with an average of 14,354 tokens. Each example was repeated 5 times`
- **EH-089** (latency_compute) All methods except LLMLingua-2 used the same Llama-3.1-8B model in the latency comparison.  
  value: `8B` metric:  task: RepoBench-P subset conditions:   
  source: ehpc-2501.12959.txt p.9 Sec. 5.1 Compression Latency  
  quote: `we utilized the same language model, Llama-3.1-8B, for all methods except`
- **EH-090** (latency_compute) EHPC's compression pass needs an LLM forward over the prompt but uses only the cheap pre-filling stage, giving short compression time.  
  value: `` metric:  task:  conditions:   
  source: ehpc-2501.12959.txt p.6 Sec. 3.4  
  quote: `leverages the computationally efficient pre-filling stage, resulting in a relatively short compression time`
- **EH-091** (latency_compute) In native-model inference EHPC performs two pre-filling stages and one decoding stage (compress, then answer).  
  value: `` metric:  task:  conditions: NMI  
  source: ehpc-2501.12959.txt p.6 Sec. 3.5  
  quote: `our method involves two pre-filling stages and one decoding stage`
- **EH-092** (latency_compute) With a k-times compressed prompt the pre-fill KV cache is k times smaller, which also speeds decoding (stated by authors; no measured GPU memory or throughput for EHPC is reported).  
  value: `` metric:  task:  conditions: NMI  
  source: ehpc-2501.12959.txt p.9 Sec. 5.2  
  quote: `the KV cache during pre-filling is reduced k times, also accelerating the decoding stage`
- **EH-093** (limitation) Section 5.2 claims memory and compute savings but reports only task scores at equal budgets (Table 6); measured memory, throughput or end-to-end latency for NMI is not reported.  
  value: `not reported` metric:  task:  conditions:   
  source: ehpc-2501.12959.txt p.9 Sec. 5.2  
  quote: `effectively reduces memory overhead and computation costs during`
- **EH-094** (latency_compute) Authors state the shorter prompt reduces pre-filling latency of the answering model (Figure 3); the measured inference-time number is in Table 5.  
  value: `` metric:  task:  conditions: EMI/NMI  
  source: ehpc-2501.12959.txt p.6 Sec. 3.4  
  quote: `the proposed method reduces the number of tokens, thereby also reducing the pre-filling latency during inference`
- **EH-100** (cost) Cost argument for API use: API cost is linear in input prompt length, so shorter prompts cut cost and latency (no dollar figures given).  
  value: `` metric:  task:  conditions: inferred saving; no measured spend  
  source: ehpc-2501.12959.txt p.6 Sec. 3.4  
  quote: `this approach can reduce API latency and costs, as the API cost is linearly related to the input prompt length`
- **EH-101** (cost) Abstract claims reduced complexity and cost for commercial API calls; no dollar or token-price figures are reported.  
  value: `not reported` metric:  task:  conditions:   
  source: ehpc-2501.12959.txt p.1 Abstract  
  quote: `it effectively reduces the complexity and costs associated with commercial API calls`
- **EH-110** (limitation) Experiments cover English datasets only (LongBench English subsets).  
  value: `` metric:  task: LongBench conditions:   
  source: ehpc-2501.12959.txt p.16 Appendix D.2  
  quote: `we focus on English datasets and encompass six tasks across 16 datasets.`
- **EH-111** (limitation) Needle-in-a-Haystack is used only to locate evaluator heads (pilot experiments); no NIAH retrieval accuracy for compressed prompts is reported.  
  value: `not reported` metric:  task: Needle-in-a-Haystack conditions:   
  source: ehpc-2501.12959.txt p.15 Appendix B  
  quote: `We conducted pilot experiments using the "Needle-in-a-Haystack" benchmark across three popular LLMs`
- **EH-112** (limitation) The compressed prompt can exceed the nominal budget: at the 2,000-token constraint EHPC outputs 2,004 tokens on average (Table 4).  
  value: `2,004` metric:  task: LongBench conditions: Table 4 row quoted in EH-042  
  source: ehpc-2501.12959.txt p.8 Table 4  
  quote: `EHPC (EMI) 44.5 50.7 24.8 68.9 51.5 61.9 49.6 2,004 5� 34.6 2,041 5�`
- **EH-120** (reproducibility) Paper gives head indices and hyper-parameters 'for reproduce' but contains no code, checkpoint or license statement in its text.  
  value: `not reported` metric:  task:  conditions:   
  source: ehpc-2501.12959.txt p.14 Appendix B  
  quote: `In this section, we introduce the hyper-parameter for reproduce.`
- **EH-121** (reproducibility) Checked 2026-11-05: the NeurIPS 2025 poster page for this paper (spotlight) lists slides, poster and OpenReview but no code repository (per WebFetch summary of the page).  
  value: `no code link found` metric:  task:  conditions:   
  source: https://neurips.cc/virtual/2025/poster/115147 NeurIPS 2025 poster page  
  quote: `No code link exists on this page.`
- **EH-122** (reproducibility) Checked 2026-11-05: the arXiv abstract page shows no paper-specific code link; the page license is CC BY-NC-SA 4.0 (applies to the paper text, not to any code).  
  value: `CC BY-NC-SA 4.0 (paper text)` metric:  task:  conditions:   
  source: https://arxiv.org/abs/2501.12959 arXiv abs page  
  quote: `CC BY-NC-SA 4.0`
- **EH-130** (tasks_tested) Coding: LongBench LCC (Long Code Completion) is used, Exact Match metric.  
  value: `tested` metric: EM task: LCC conditions: LongBench code completion  
  source: ehpc-2501.12959.txt p.17 Appendix D.2  
  quote: `LCC (Guo et al., 2023): Sampled from the Long Code Completion dataset`
- **EH-131** (tasks_tested) Coding: LongBench RepoBench-P (repository-level, cross-file) is used, Exact Match metric, 200 entries.  
  value: `tested` metric: EM task: RepoBench-P conditions:   
  source: ehpc-2501.12959.txt p.17 Appendix D.2  
  quote: `RepoBench-P (Liu et al., 2024a): Collected from GitHub repositories`
- **EH-132** (tasks_tested) Long-document QA: LongBench multi-doc QA datasets (HotpotQA, 2WikiMultihopQA, MuSiQue) F1; single-doc QA (NarrativeQA, Qasper, MultiFieldQA-en) also used.  
  value: `tested` metric: F1 task: HotpotQA, 2WikiMQA, MuSiQue, NarrativeQA, Qasper, MultiFieldQA-en conditions:   
  source: ehpc-2501.12959.txt p.16 Appendix D.2  
  quote: `HotpotQA (Yang et al., 2018) features many 2-hop questions crafted by native speakers`
- **EH-133** (tasks_tested) Retrieval/RAG: BM25, SBERT and OpenAI-embedding retrieval are compared as RAG baselines.  
  value: `tested (as baselines)` metric:  task: LongBench, ZeroSCROLLS conditions:   
  source: ehpc-2501.12959.txt p.8 Sec. 5.1  
  quote: `We compare our method with Retrieval Augmented Generation (RAG) and other SoTA prompt compression methods.`
- **EH-134** (tasks_tested) Summarization: GovReport, QMSum, MultiNews (Rouge-L) in LongBench; ZeroSCROLLS adds SummScreenFD and SQuALITY.  
  value: `tested` metric: Rouge-L task: GovReport, QMSum, MultiNews conditions:   
  source: ehpc-2501.12959.txt p.16 Appendix D.2  
  quote: `GovReport (Huang et al., 2021) collects comprehensive reports containing human-written`
- **EH-135** (tasks_tested) Few-shot learning: TREC, TriviaQA, SAMSum from LongBench.  
  value: `tested` metric: accuracy / F1 / Rouge-L task: TREC, TriviaQA, SAMSum conditions:   
  source: ehpc-2501.12959.txt p.16 Appendix D.2  
  quote: `TREC (Li and Roth, 2002) is a classification dataset featuring fine-grained class labels.`
- **EH-136** (tasks_tested) Benchmarks used: LongBench (English, 16 datasets), ZeroSCROLLS, plus synthetic Needle-in-a-Haystack/RULER for head discovery. Multi-turn chat, structured data (JSON/tables/logs), math and PII/sensitive content are not among the listed datasets.  
  value: `not tested in paper (multi-turn chat; structured data; math; PII)` metric:  task:  conditions: dataset list in Appendix D  
  source: ehpc-2501.12959.txt p.16 Appendix D.2  
  quote: `LongBench (Bai et al., 2024) is a widely used long-context benchmark that includes 21 datasets across six`
- **EH-137** (tasks_tested) Reasoning: only multi-hop QA datasets in LongBench plus a synthetic RULER multi-hop tracing probe used for head discovery; no math/chain-of-thought dataset.  
  value: `partly (multi-hop QA only)` metric:  task: RULER multi-hop tracing (probe) conditions:   
  source: ehpc-2501.12959.txt p.18 Appendix F  
  quote: `For multi-hop reasoning, we utilize the multi-hop tracing task from the Ruler`
- **EH-138** (limitation) Context lengths in experiments: LongBench originals average 10,295 tokens (EH-040) and the latency subset 14,354 tokens; the NIAH pilot lengths are not stated. Models used advertise 128k context.  
  value: `128k` metric:  task:  conditions:   
  source: ehpc-2501.12959.txt p.10 Sec. 5.2  
  quote: `both support a context window length of 128k`

## GistTokens

- **AC-085** (mechanism) AutoCompressor authors describe Gist as concurrent work that compresses instructions into short key-value attention prefixes (so KV-form compression predates 500xCompressor).  
  value: `` metric:  task:  conditions: claim by Chevalier et al.  
  source: autocompressor-2305.14788.txt p.2 Sec. 2  
  quote: `In concurrent work, Mu et al. (2023) teach models to compress instructions into short key-value attention prefixes`
- **GT-001** (mechanism) Gisting trains an LM to compress a prompt into a few gist tokens whose activations are cached and reused.  
  value: `` metric:  task:  conditions: LLaMA-7B and FLAN-T5-XXL  
  source: gist-tokens-2304.08467.txt p.1 Abstract  
  quote: `gisting, which trains an LM to compress prompts into smaller sets of "gist" tokens which can be cached and reused for compute efficiency`
- **GT-002** (mechanism) Gist models are learned by modifying Transformer attention masks during ordinary instruction finetuning; no extra training cost.  
  value: `` metric:  task:  conditions:   
  source: gist-tokens-2304.08467.txt p.1 Abstract  
  quote: `Gist models can be trained with no additional cost over standard instruction finetuning by simply modifying Transformer attention masks to encourage prompt compression`
- **GT-003** (mechanism) Tokens after the gist tokens are masked from seeing the prompt, forcing prompt information into the gist prefix.  
  value: `` metric:  task:  conditions: decoder-only masking (Fig. 2a)  
  source: gist-tokens-2304.08467.txt p.3 Sec. 3  
  quote: `The model is then restricted such that input tokens after the gist tokens cannot attend to any of the prompt tokens before the gist tokens`
- **GT-004** (mechanism) What is trained: one new gist token (vocabulary and embedding row) is added and the LM is instruction-finetuned with the gist mask; the paper does not say whether this is full finetuning or parameter-efficient.  
  value: `` metric:  task:  conditions:   
  source: gist-tokens-2304.08467.txt p.3 Sec. 3  
  quote: `we add a single gist token g to the model vocabulary and embedding matrix`
- **GT-005** (mechanism) The gist prefix is predicted by the (finetuned) LM itself, so a gist prefix is only meaningful to that same gist model (inferred from mechanism).  
  value: `` metric:  task:  conditions: inferred from mechanism  
  source: gist-tokens-2304.08467.txt p.3 Sec. 3  
  quote: `using the LM itself as the gist predictor G`
- **GT-006** (mechanism) Base models: LLaMA-7B (decoder-only, ~7B) and FLAN-T5-XXL (encoder-decoder, 11B).  
  value: `~7B; 11B` metric:  task:  conditions:   
  source: gist-tokens-2304.08467.txt p.4 Sec. 4.2  
  quote: `we experiment with LLaMA- 7B [33], a decoder-only GPT-style model with ~7B parameters, and FLAN-T5-XXL [8], an encoder- decoder T5 model [28] with 11B parameters`
- **GT-007** (io) Output form: the key/value activations of the LM on top of the gist tokens (a Transformer prefix), cached and reused.  
  value: `` metric:  task:  conditions:   
  source: gist-tokens-2304.08467.txt p.2 Sec. 2  
  quote: `G(t) will be the key/value activations on top a set of gist tokens, smaller than the number of tokens in t, yet still inducing similar behavior from the LM`
- **GT-008** (io) The paper does not discuss closed/API LLMs. Its method requires finetuning the LM itself and consuming its KV activations (inferred from mechanism: not usable with an API-only model); retrofitting a frozen LM is listed only as future work.  
  value: `` metric:  task:  conditions: inferred from mechanism  
  source: gist-tokens-2304.08467.txt p.9 Sec. 8  
  quote: `another exciting approach is to retrofit an existing, frozen LM by training a smaller model to compress prompts, if finetuning the larger LM is inconvenient`
- **GT-009** (compression_ratio) Headline: up to 26x prompt compression, up to 40% FLOPs reduction, 4.2% wall-time speedup, with minimal loss in output quality (authors' abstract).  
  value: `26x; 40%; 4.2%` metric:  task: Alpaca+ conditions: LLaMA-7B and FLAN-T5-XXL  
  source: gist-tokens-2304.08467.txt p.1 Abstract  
  quote: `gisting enables up to 26x compression of prompts, resulting in up to 40% FLOPs reductions, 4.2% wall time speedups, and storage savings, all with minimal loss in output quality`
- **GT-010** (compression_ratio) The compression factor is the average prompt length of the validation split divided by the number of gist tokens, so it depends on how short the prompts are.  
  value: `` metric: compression factor task: Alpaca+ conditions: Figure 3 caption  
  source: gist-tokens-2304.08467.txt p.6 Figure 3 caption  
  quote: `Compression factors are calculated by computing the average token length of the validation split and dividing by the number of gist tokens`
- **GT-011** (compression_ratio) Compressed prompts are short instructions: the average training prompt is ~20 tokens and ~26 tokens in the Human split, so the 26x figure applies to very short instructions, not documents.  
  value: `~20; ~26` metric: tokens task: Alpaca+ Human split conditions:   
  source: gist-tokens-2304.08467.txt p.4 Sec. 4.1  
  quote: `the average training prompt has ~20 tokens, compared to ~26 in the human split`
- **GT-012** (compression_ratio) Authors state the 26x figure is for unseen out-of-distribution prompts while maintaining output quality.  
  value: `26x` metric:  task: Alpaca+ Human split conditions: 1 gist token  
  source: gist-tokens-2304.08467.txt p.9 Sec. 8  
  quote: `Gist models can compress unseen OOD prompts up to 26x while maintaining output quality`
- **GT-013** (compression_ratio) Number of gist tokens k was varied (Figure 3 axes show 1, 2, 5, 10); models were insensitive to k and a single gist token did not substantially underperform larger prefixes; the single-token model is used for all later experiments.  
  value: `` metric:  task: Alpaca+ conditions:   
  source: gist-tokens-2304.08467.txt p.5 Sec. 5  
  quote: `Models were generally insensitive to the number of gist tokens k: compressing prompts into a single token prefix did not substantially underperform larger prefixes`
- **GT-014** (compression_ratio) Too many gist tokens can hurt (LLaMA-7B with 10 gist tokens).  
  value: `` metric:  task: Alpaca+ conditions: LLaMA-7B, k=10  
  source: gist-tokens-2304.08467.txt p.5 Sec. 5  
  quote: `having too many gist tokens hurts performance in some cases (e.g. LLaMA-7B, 10 gist tokens)`
- **GT-015** (context_loss) Positive control (uncompressed baseline = instruction-finetuned LLaMA-7B, no mask change): defines 100 on the normalised scale. Table 1 columns per header: Seen ROUGE-L, Seen ChatGPT %, Unseen ROUGE-L, Unseen ChatGPT %, Human ROUGE-L, Human ChatGPT %; parentheses = score normalised between positive (100) and negative (0) controls.  
  value: `58.0 (100) 50.0 (100) 48.1 (100) 50.0 (100) 27.0 (100) 50.0 (100)` metric: ROUGE-L; ChatGPT win % vs Pos task: Alpaca+ Seen/Unseen/Human conditions: LLaMA-7B, Pos control  
  source: gist-tokens-2304.08467.txt p.6 Table 1  
  quote: `LLaMA- Pos 58.0 (100) 50.0 (100) 48.1 (100) 50.0 (100) 27.0 (100) 50.0 (100)`
- **GT-016** (context_loss) Gist model (1 gist token) vs the positive control on LLaMA-7B (GT-015); the drop is largest on the OOD Human split. Table 1 columns per header: Seen ROUGE-L, Seen ChatGPT %, Unseen ROUGE-L, Unseen ChatGPT %, Human ROUGE-L, Human ChatGPT %; parentheses = score normalised between positive (100) and negative (0) controls.  
  value: `57.8 (99.2) 48.6 (92.4) 46.6 (91.0) 49.7 (98.8) 23.9 (75.4) 45.8 (84.9)` metric: ROUGE-L; ChatGPT win % vs Pos task: Alpaca+ Seen/Unseen/Human conditions: LLaMA-7B, 1 gist token (prompt compressed ~20-26x on Human)  
  source: gist-tokens-2304.08467.txt p.6 Table 1  
  quote: `7B Gist 57.8 (99.2) 48.6 (92.4) 46.6 (91.0) 49.7 (98.8) 23.9 (75.4) 45.8 (84.9)`
- **GT-017** (context_loss) Negative control (no access to the task prompt) on LLaMA-7B: lower bound. Table 1 columns per header: Seen ROUGE-L, Seen ChatGPT %, Unseen ROUGE-L, Unseen ChatGPT %, Human ROUGE-L, Human ChatGPT %; parentheses = score normalised between positive (100) and negative (0) controls.  
  value: `31.5 (0) 31.5 (0) 31.4 (0) 25.4 (0) 14.4 (0) 22.2 (0)` metric: ROUGE-L; ChatGPT win % vs Pos task: Alpaca+ Seen/Unseen/Human conditions: LLaMA-7B, Neg control  
  source: gist-tokens-2304.08467.txt p.6 Table 1  
  quote: `Neg 31.5 (0) 31.5 (0) 31.4 (0) 25.4 (0) 14.4 (0) 22.2 (0)`
- **GT-018** (context_loss) TF-IDF single-keyword discrete compression on LLaMA-7B, at the same compression as one gist token, barely beats the negative control. Table 1 columns per header: Seen ROUGE-L, Seen ChatGPT %, Unseen ROUGE-L, Unseen ChatGPT %, Human ROUGE-L, Human ChatGPT %; parentheses = score normalised between positive (100) and negative (0) controls.  
  value: `38.1 (24.5) 34.5 (16.2) 34.0 (15.6) 29.3 (15.9) 16.5 (16.7) 24.6 (8.6)` metric: ROUGE-L; ChatGPT win % vs Pos task: Alpaca+ Seen/Unseen/Human conditions: LLaMA-7B, TF-IDF baseline  
  source: gist-tokens-2304.08467.txt p.6 Table 1  
  quote: `TF-IDF 38.1 (24.5) 34.5 (16.2) 34.0 (15.6) 29.3 (15.9) 16.5 (16.7) 24.6 (8.6)`
- **GT-019** (context_loss) Positive control for FLAN-T5-XXL. Table 1 columns per header: Seen ROUGE-L, Seen ChatGPT %, Unseen ROUGE-L, Unseen ChatGPT %, Human ROUGE-L, Human ChatGPT %; parentheses = score normalised between positive (100) and negative (0) controls.  
  value: `50.6 (100) 50.0 (100) 45.7 (100) 50.0 (100) 23.9 (100) 50.0 (100)` metric: ROUGE-L; ChatGPT win % vs Pos task: Alpaca+ Seen/Unseen/Human conditions: FLAN-T5-XXL, Pos control  
  source: gist-tokens-2304.08467.txt p.6 Table 1  
  quote: `FLAN- Pos 50.6 (100) 50.0 (100) 45.7 (100) 50.0 (100) 23.9 (100) 50.0 (100)`
- **GT-020** (context_loss) Gist model (1 gist token) vs the positive control on FLAN-T5-XXL; Human split win rate 42.5% (normalised 63.2). Table 1 columns per header: Seen ROUGE-L, Seen ChatGPT %, Unseen ROUGE-L, Unseen ChatGPT %, Human ROUGE-L, Human ChatGPT %; parentheses = score normalised between positive (100) and negative (0) controls.  
  value: `48.9 (93.2) 50.8 (103.9) 43.8 (88.6) 46.2 (84.4) 21.7 (80.9) 42.5 (63.2)` metric: ROUGE-L; ChatGPT win % vs Pos task: Alpaca+ Seen/Unseen/Human conditions: FLAN-T5-XXL, 1 gist token  
  source: gist-tokens-2304.08467.txt p.6 Table 1  
  quote: `T5-XXL Gist 48.9 (93.2) 50.8 (103.9) 43.8 (88.6) 46.2 (84.4) 21.7 (80.9) 42.5 (63.2)`
- **GT-021** (context_loss) Negative control for FLAN-T5-XXL. Table 1 columns per header: Seen ROUGE-L, Seen ChatGPT %, Unseen ROUGE-L, Unseen ChatGPT %, Human ROUGE-L, Human ChatGPT %; parentheses = score normalised between positive (100) and negative (0) controls.  
  value: `25.5 (0) 29.7 (0) 29.1 (0) 25.6 (0) 12.4 (0) 29.6 (0)` metric: ROUGE-L; ChatGPT win % vs Pos task: Alpaca+ Seen/Unseen/Human conditions: FLAN-T5-XXL, Neg control  
  source: gist-tokens-2304.08467.txt p.6 Table 1  
  quote: `Neg 25.5 (0) 29.7 (0) 29.1 (0) 25.6 (0) 12.4 (0) 29.6 (0)`
- **GT-022** (context_loss) Authors' own reading of Table 1: parity on Seen instructions.  
  value: `48.6%; 50.8%` metric: ChatGPT win rate vs Pos task: Alpaca+ Seen conditions: LLaMA-7B; FLAN-T5-XXL  
  source: gist-tokens-2304.08467.txt p.5 Sec. 5  
  quote: `On Seen instructions, gist models attain near-identical ROUGE and ChatGPT performance as their positive control models`
- **GT-023** (context_loss) Authors describe the Human (OOD) split as showing 'slight drops' in win rate.  
  value: `45.8%; 42.5%` metric: ChatGPT win rate vs Pos task: Alpaca+ Human conditions: LLaMA-7B; FLAN-T5-XXL  
  source: gist-tokens-2304.08467.txt p.5 Sec. 5  
  quote: `slight drops in win rate to 45.8% (LLaMA) and 42.5% (FLAN-T5)`
- **GT-024** (context_loss) Win rate against the positive control is the quality metric; 50% means parity with no compression.  
  value: `50%` metric: win rate task:  conditions: judge = ChatGPT-3.5 (chatgpt-3.5-turbo per App. C)  
  source: gist-tokens-2304.08467.txt p.5 Sec. 4.3  
  quote: `a win rate of 50% indicates that the model is of comparable quality to a model that does no prompt compression`
- **GT-025** (context_loss) The uncompressed baseline is the 'positive control', i.e. a single-gist-token model trained with standard instruction finetuning without the gist mask, not the original LLaMA.  
  value: `` metric:  task:  conditions:   
  source: gist-tokens-2304.08467.txt p.4 Sec. 4.2  
  quote: `As an upper bound on performance, we train a model with a single gist token, but without any modifications to the attention mask`
- **GT-026** (context_loss) Human evaluation design: 100 of the 252 Human-split prompts, 3 annotators each, win rate of single-token gist model over positive control.  
  value: `100 of 252; 3 annotators` metric: win rate task: Alpaca+ Human split conditions:   
  source: gist-tokens-2304.08467.txt p.5 Sec. 4.3  
  quote: `do a Human evaluation on a random subset of 100 of the 252 examples in the Human validation split`
- **GT-027** (context_loss) Human-evaluation win rates over the positive control, LLaMA-7B (H1, H2, H3, Human avg with 95% CI, ChatGPT with CI, kappa human, kappa ChatGPT). Column order per Table 2 header.  
  value: `52.3 (46.1, 58.4); ChatGPT 48.0 (38.0, 58.2)` metric: win % over Pos task: Alpaca+ Human split, 100 prompts conditions: LLaMA-7B, 1 gist token  
  source: gist-tokens-2304.08467.txt p.7 Table 2  
  quote: `LLaMA-7B 51.1 44.5 59.8 52.3 (46.1, 58.4) 48.0 (38.0, 58.2) .24 .29`
- **GT-028** (context_loss) Human-evaluation win rate for FLAN-T5-XXL gist is 40.6% with 95% CI (34.6, 46.8), i.e. significantly below 50% parity.  
  value: `40.6 (34.6, 46.8); ChatGPT 42.0 (32.2, 52.3)` metric: win % over Pos task: Alpaca+ Human split, 100 prompts conditions: FLAN-T5-XXL, 1 gist token  
  source: gist-tokens-2304.08467.txt p.7 Table 2  
  quote: `FLAN-T5-XXL 43.0 41.9 37.2 40.6 (34.6, 46.8) 42.0 (32.2, 52.3) .33 .29`
- **GT-029** (context_loss) Exact-string identity of gist outputs with the positive control's outputs (not a text-reconstruction test): nearly 50% on Seen, 20-25% on Unseen, ~10% on OOD Human.  
  value: `~50%; ~20-25%; ~10%` metric: exact string match vs Pos output task: Alpaca+ Seen/Unseen/Human conditions: per Figure A.3  
  source: gist-tokens-2304.08467.txt p.7 Sec. 5  
  quote: `the gist model outputs exactly match the positive control nearly 50% of the time. This drops to ~20-25% for Unseen tasks and ~10% for the OOD Human tasks`
- **GT-030** (limitation) Failure mode: instructions with details that must be copied verbatim into the output are not perfectly preserved.  
  value: `` metric:  task: Alpaca+ Human split conditions:   
  source: gist-tokens-2304.08467.txt p.7 Sec. 5.1  
  quote: `when the instruction contains specific details, e.g. phrases that must be copied verbatim into the output`
- **GT-031** (limitation) Qualitative failure example: FLAN-T5-XXL gist answered 'Culture' where the positive control answered the required category 'Arts & Culture'.  
  value: `` metric:  task: news-title categorisation (Human split) conditions: FLAN-T5-XXL gist vs pos control  
  source: gist-tokens-2304.08467.txt p.7 Sec. 5.1  
  quote: `Assistant A (FLAN-T5-XXL gist): Culture Assistant B (pos control): Arts & Culture`
- **GT-032** (limitation) Gist models showed runaway generations that the positive control did not (LaTeX example repeated for hundreds of tokens).  
  value: `` metric:  task: Alpaca+ Human split conditions: LLaMA-7B gist  
  source: gist-tokens-2304.08467.txt p.7 Sec. 5.1  
  quote: `We also see more cases of runaway generations that do not occur with the positive control model`
- **GT-033** (limitation) Authors' limitation: compression loses nuance of the original instruction; practitioners must evaluate safety/robustness before deployment.  
  value: `` metric:  task:  conditions:   
  source: gist-tokens-2304.08467.txt p.9 Sec. 8  
  quote: `achieving such com- pression necessarily results in some loss of nuance of the original instruction`
- **GT-034** (limitation) Authors advise carefully evaluating the compute/accuracy tradeoff per use case.  
  value: `` metric:  task:  conditions:   
  source: gist-tokens-2304.08467.txt p.9 Sec. 8  
  quote: `it is especially important for practitioners to carefully evaluate whether the compute/accuracy tradeoff of gisting is sufficiently safe and robust for their use case, before deployment`
- **GT-035** (limitation) Encoder-decoder (FLAN-T5) generalises slightly worse out of distribution than decoder-only LLaMA.  
  value: `` metric:  task: Alpaca+ Human split conditions:   
  source: gist-tokens-2304.08467.txt p.7 Sec. 5  
  quote: `Encoder-decoder LMs like FLAN-T5 show slightly worse OOD performance`
- **GT-036** (limitation) Very long prompts (e.g. many-shot prompts exceeding a context window) were not tested; named as future work.  
  value: `` metric:  task:  conditions:   
  source: gist-tokens-2304.08467.txt p.9 Sec. 8  
  quote: `Second, the largest efficiency gains from gisting will result from compressing very long prompts, for example k-shot prompts for large k that may even exceed a single context window`
- **GT-037** (limitation) Max sequence length for LLaMA-7B training/eval is 512 tokens (768 for the Human split); the compressor never sees long inputs.  
  value: `512; 768` metric: tokens task:  conditions: LLaMA-7B  
  source: gist-tokens-2304.08467.txt p.13 Appendix B  
  quote: `For LLaMA-7B, we used a maximum sequence length of 512 tokens during training and evaluation, except with the Human validation split, where the maximum length was increased to 768`
- **GT-038** (limitation) Max input length for FLAN-T5-XXL is 128 tokens (task plus input), 384 on the Human split.  
  value: `128; 384` metric: tokens task:  conditions: FLAN-T5-XXL  
  source: gist-tokens-2304.08467.txt p.13 Appendix B  
  quote: `For FLAN-T5-XXL, we set a maximum input length (task t + input x) of 128 and a maximum output length of 256`
- **GT-039** (latency_compute) Training hardware: one cluster machine with 4 A100-SXM4-80GB, 480GB RAM, 16 CPUs.  
  value: `4xA100-SXM4-80GB` metric:  task:  conditions:   
  source: gist-tokens-2304.08467.txt p.13 Appendix B  
  quote: `Experiments were run on a cluster machine with 4xA100-SXM4-80GB NVIDIA GPUs, 480GB RAM, and 16 CPUs`
- **GT-040** (latency_compute) Training time: ~7 hours for LLaMA-7B and ~25 hours for FLAN-T5-XXL (the quote ends before the model name FLAN-T5-XXL on the next line).  
  value: `~7 h; ~25 h` metric: hours task:  conditions: 4xA100 80GB  
  source: gist-tokens-2304.08467.txt p.13 Appendix B  
  quote: `Training runs take about ~7 hours to complete for LLaMA-7B and ~25 hours for`
- **GT-041** (latency_compute) Training length: 3000 steps for LLaMA-7B and 16000 steps for FLAN-T5-XXL.  
  value: `3000; 16000` metric: steps task: Alpaca+ conditions:   
  source: gist-tokens-2304.08467.txt p.13 Appendix B  
  quote: `LLaMA-7B was trained for 3000 steps, while FLAN-T5-XXL was trained for 16000 steps`
- **GT-042** (hardware) Benchmarking was done on one A100 GPU of the same machine.  
  value: `1 A100` metric:  task:  conditions:   
  source: gist-tokens-2304.08467.txt p.13 Appendix B  
  quote: `Benchmarking results were obtained on the same machine, but using just 1 of the A100 GPUs`
- **GT-043** (latency_compute) Efficiency was measured as a single forward pass (one decoding step with one input token), averaged over the 252 Human instructions - not end-to-end generation latency.  
  value: `` metric:  task: Alpaca+ Human instructions conditions: PyTorch 2.0, 1 A100  
  source: gist-tokens-2304.08467.txt p.8 Sec. 6  
  quote: `profiling a single forward pass through the model (i.e. one step of decoding with a single input token)`
- **GT-044** (latency_compute) Table 3 absolute CUDA wall time per forward step in ms (None / Instruction-caching / Gist-caching) and absolute/relative gain columns, LLaMA-7B. Columns per Table 3 header (None, Instruction, Gist, vs None, vs Instruction); the +/- glyph is unreadable in the raw text.  
  value: `23.4 / 22.1 / 21.8 ms; improvement 1.60 vs None, .221 vs Instruction` metric: CUDA time (ms) task: 252 Human instructions conditions: LLaMA-7B; avg KV cache length 26 (instruction) vs 1 (gist)  
  source: gist-tokens-2304.08467.txt p.8 Table 3  
  quote: `LLaMA- CUDA 23.4 � 6.88 22.1 � 6.58 21.8 � 6.55 1.60 (1.29, 1.90) .221 (.140, .302)`
- **GT-045** (latency_compute) LLaMA-7B relative wall-time saving of gist caching: 6.8% vs no caching, 1.0% vs caching the full instruction KV.  
  value: `6.8% (5.5, 8.1); 1.0% (.63, 1.4)` metric: relative CUDA time improvement task: 252 Human instructions conditions: LLaMA-7B  
  source: gist-tokens-2304.08467.txt p.8 Table 3  
  quote: `6.8% (5.5, 8.1) 1.0% (.63, 1.4)`
- **GT-046** (latency_compute) LLaMA-7B relative FLOPs saving of gist caching: 40% vs no caching, .11% vs caching the full instruction KV.  
  value: `40% (37, 42); .11% (.08, .14)` metric: relative GFLOPs reduction task: 252 Human instructions conditions: LLaMA-7B  
  source: gist-tokens-2304.08467.txt p.8 Table 3  
  quote: `40% (37, 42) .11% (.08, .14)`
- **GT-047** (latency_compute) FLAN-T5-XXL relative wall-time saving of gist caching vs no caching (instruction caching N/A for encoder-decoder).  
  value: `4.2% (3.6, 4.9)` metric: relative CUDA time improvement task: 252 Human instructions conditions: FLAN-T5-XXL  
  source: gist-tokens-2304.08467.txt p.8 Table 3  
  quote: `4.2% (3.6, 4.9)`
- **GT-048** (latency_compute) FLAN-T5-XXL relative FLOPs saving of gist caching vs no caching.  
  value: `40% (37, 43)` metric: relative GFLOPs reduction task: 252 Human instructions conditions: FLAN-T5-XXL  
  source: gist-tokens-2304.08467.txt p.8 Table 3  
  quote: `40% (37, 43)`
- **GT-049** (latency_compute) Authors' summary: 40% FLOPs savings but only 4-7% wall-time reduction vs unoptimised models.  
  value: `40%; 4-7%` metric:  task:  conditions:   
  source: gist-tokens-2304.08467.txt p.8 Sec. 6  
  quote: `Gist caching improves significantly over unoptimized models, with 40% FLOPs savings and 4-7% lower wall time for both models`
- **GT-050** (latency_compute) Against instruction (KV) caching in LLaMA-7B the gain is negligible: 0.11% FLOPs and ~1% wall time.  
  value: `0.11%; 1%` metric:  task:  conditions: LLaMA-7B  
  source: gist-tokens-2304.08467.txt p.8 Sec. 6  
  quote: `a negligible decrease in FLOPs (0.11%) and a modest 1% speedup in wall time`
- **GT-051** (latency_compute) Authors explain why wall time gains are smaller than FLOPs gains at these small scales (memory time).  
  value: `` metric:  task:  conditions:   
  source: gist-tokens-2304.08467.txt p.8 Sec. 6  
  quote: `Note that at these (relatively) small scales, the wall time improvements are smaller than the FLOPs reductions because much of the inference latency is caused by moving tensors`
- **GT-052** (latency_compute) Why instruction caching is already cheap: a forward pass with a 2000-length KV cache is only ~10% more expensive than with none.  
  value: `~10%` metric:  task:  conditions: LLaMA-7B, 1 input token, 2000-length KV cache  
  source: gist-tokens-2304.08467.txt p.8 Sec. 6  
  quote: `a forward pass through LLaMA-7B with a single input token and a 2000-length KV cache is only ~10% more expensive than the same forward pass with no KV cache`
- **GT-053** (latency_compute) Storage benefit: caching up to 26x more prompts than full-instruction caching for the same storage (comparison is against uncompressed instruction KV caches).  
  value: `up to 26x` metric:  task:  conditions: LLaMA-7B; ~26-token instructions into 1 gist token  
  source: gist-tokens-2304.08467.txt p.8 Sec. 6  
  quote: `gisting allows caching of up to 26x more prompts than full instruction caching, using the same amount of storage`
- **GT-054** (latency_compute) KV cache storage per token for LLaMA-7B.  
  value: `1.05 MB` metric: MB per token task:  conditions: LLaMA-7B, fp32  
  source: gist-tokens-2304.08467.txt p.8 Sec. 6  
  quote: `each token in the KV cache requires 1.05 MB storage`
- **GT-055** (cost) Training cost: no additional training cost beyond standard instruction finetuning (but the whole LM must be finetuned per model).  
  value: `` metric:  task:  conditions:   
  source: gist-tokens-2304.08467.txt p.3 Sec. 3  
  quote: `gisting incurs no additional training cost on top of standard instruction finetuning`
- **GT-056** (cost) Training data is Alpaca+ (130,321 examples, 104,664 unique tasks), model-generated instruction data.  
  value: `130,321 examples; 104,664 tasks` metric:  task: Alpaca+ conditions:   
  source: gist-tokens-2304.08467.txt p.4 Sec. 4.1  
  quote: `In total, Alpaca+ has 130,321 examples, with 104,664 unique tasks t, 48,530 unique inputs x`
- **GT-057** (reproducibility) Code, data and model checkpoints are stated to be released.  
  value: `` metric:  task:  conditions:   
  source: gist-tokens-2304.08467.txt p.13 Appendix B  
  quote: `Code, data, and model checkpoints are available at https://github.com/jayelm/gisting`
- **GT-058** (reproducibility) Official repo README states the codebase licence (Apache 2.0); data is a mix of Apache 2.0 (Self-Instruct) and CC BY-NC 4.0 (Alpaca). Quote is WebFetch's rendering of the README, not script-verified.  
  value: `Apache 2.0` metric:  task:  conditions: code licence; data licence CC BY-NC 4.0 portion  
  source: https://github.com/jayelm/gisting GitHub README (WebFetch)  
  quote: `The codebase is licensed Apache 2.0 (see `LICENSE`).`
- **GT-059** (reproducibility) Official repo README: released LLaMA-7B checkpoints are weight diffs requiring the base LLaMA-7B weights; 1-token gist models (plus pos/neg controls) for LLaMA-7B and FLAN-T5-XXL are on Hugging Face. Quote as returned by WebFetch.  
  value: `` metric:  task:  conditions:   
  source: https://github.com/jayelm/gisting GitHub README (WebFetch)  
  quote: `The released LLaMA-7B checkpoints are **weight diffs**.`
- **GT-060** (reproducibility) Identity: the real Gist Tokens paper is arXiv:2304.08467 (NeurIPS 2023), not arXiv:2401.09390.  
  value: `2304.08467` metric:  task:  conditions:   
  source: gist-tokens-2304.08467.txt p.1 title page stamp  
  quote: `arXiv:2304.08467v3 [cs.CL] 12 Feb 2024`
- **GT-061** (reproducibility) Title and authors of the real paper (Mu, Li, Goodman, Stanford).  
  value: `` metric:  task:  conditions:   
  source: gist-tokens-2304.08467.txt p.1 title page  
  quote: `Learning to Compress Prompts with Gist Tokens Jesse Mu, Xiang Lisa Li, Noah Goodman`
- **GT-062** (mechanism) Implementation is ~10 lines of attention-mask code - no architecture change.  
  value: `~10 lines` metric:  task:  conditions:   
  source: gist-tokens-2304.08467.txt p.4 Sec. 3  
  quote: `these masking changes are extremely simple and can be implemented in roughly 10 source lines of code`
- **GT-063** (tasks_tested) Training/eval data is Alpaca+ (Self-Instruct + Stanford Alpaca instruction-tuning data).  
  value: `` metric:  task: Alpaca+ instruction following conditions:   
  source: gist-tokens-2304.08467.txt p.4 Sec. 4.1  
  quote: `we create a dataset called Alpaca+, which combines the Self-Instruct [36] and Stanford Alpaca [31] instruction tuning datasets`
- **GT-064** (tasks_tested) Only three Alpaca+ validation splits were evaluated (Seen, Unseen, Human); no coding benchmark, long-document QA/RAG, multi-turn chat, summarization benchmark, structured-data, math/reasoning or PII dataset was evaluated.  
  value: `not tested in paper` metric:  task: coding; long-document QA/RAG; multi-turn chat; summarization; structured data; reasoning/math; sensitive/PII conditions: dataset list quoted  
  source: gist-tokens-2304.08467.txt p.4 Sec. 4.1  
  quote: `From Alpaca+ we hold out 3 validation splits: 1000 Seen prompts (with unseen, non-empty inputs); 1000 Unseen prompts (with non-empty inputs); and the 252 hand-written Human prompts`
- **GT-065** (tasks_tested) Coding questions may occur in the Human split (annotators could answer 'I don't know' for them; ~10% of responses dropped) but there is no coding-specific evaluation.  
  value: `~10%` metric:  task: Alpaca+ Human split conditions:   
  source: gist-tokens-2304.08467.txt p.5 Sec. 4.3  
  quote: `e.g. if the question was a coding question; we drop these responses (~10%) during analysis`
- **GT-066** (limitation) Third-party characterisation (500xCompressor authors): Gist needs fine-tuning of the original LLM and handles only short prompts (< ~30 tokens). Cross-check, not evidence from the Gist paper itself.  
  value: `< thirty tokens` metric:  task:  conditions: claim by Li et al.  
  source: 500x-compressor.txt p.7 Sec. 6 Related Work  
  quote: `lim- itations included the need for fine-tuning the original LLM and the short length of prompts to be compressed, typically less than thirty tokens`
- **GT-067** (reproducibility) Venue of the real Gist paper: NeurIPS 2023.  
  value: `NeurIPS 2023` metric:  task:  conditions:   
  source: gist-tokens-2304.08467.txt p.1 title page footer  
  quote: `37th Conference on Neural Information Processing Systems (NeurIPS 2023)`

## H2O

- **EH-058** (context_loss) EHPC's re-run of H2O with a 1024 KV budget on Llama 3.1 8B: printed average 34.77; PassageRetrieval falls to 71.34 (vs 97.73 full KV) and NarrativeQA to 21.98 (vs 32.02).  
  value: `Avg 34.77; PRe 71.34; NrtvQA 21.98` metric: LongBench task: LongBench conditions: H2O-1024; Llama-3.1-8B-Instruct; run by EHPC authors  
  source: ehpc-2501.12959.txt p.10 Table 6  
  quote: `H2O-1024 21.98 10.96 23.17 16.06 15.16 10.15 30.76 23.75 26.32 68.0 90.68 42.54 7.40 71.34 51.6 46.4 34.77`
- **EH-059** (context_loss) EHPC's re-run of H2O with a 2048 KV budget on Llama 3.1 8B: printed average 35.45; PassageRetrieval 72.79 (vs 97.73 full KV).  
  value: `Avg 35.45; PRe 72.79` metric: LongBench task: LongBench conditions: H2O-2048; Llama-3.1-8B-Instruct; run by EHPC authors  
  source: ehpc-2501.12959.txt p.10 Table 6  
  quote: `H2O-2048 23.16 11.68 25.09 16.17 15.22 9.93 32.13 23.32 26.73 68.5 91.32 43.97 6.52 72.79 52.5 48.1 35.45`
- **EH-064** (context_loss) EHPC's re-run of H2O 1024 on Phi 3.5 Mini: printed average 31.38; PassageRetrieval 46.80 (vs 83.85 full KV).  
  value: `Avg 31.38; PRe 46.80` metric: LongBench task: LongBench conditions: H2O-1024; Phi-3.5-mini-3.8B-Instruct; run by EHPC authors  
  source: ehpc-2501.12959.txt p.10 Table 6  
  quote: `H2O-1024 18.25 12.97 29.69 20.75 20.90 9.90 32.02 21.69 24.70 67.5 85.45 20.16 1.37 46.80 46.6 43.3 31.38`
- **H2-001** (mechanism) H2O is a KV-cache eviction policy for the generating model: it keeps a balance of recent tokens and 'heavy hitter' tokens (largest accumulated attention) in the cache.  
  value: `` metric:  task:  conditions:   
  source: h2o-2306.14048.txt p.1 Abstract  
  quote: `policy that dynamically retains a balance of recent and H2 tokens`
- **H2-002** (mechanism) The paper scopes itself to the token-generation (decoding) phase: the aim is to make the KV cache in attention more efficient while generating.  
  value: `` metric:  task:  conditions:   
  source: h2o-2306.14048.txt p.3 Sec. 2  
  quote: `to enhance the efficiency of the KV cache in attention during the token generation phase`
- **H2-003** (mechanism) Budget is split evenly between heavy hitters and the most recent KV entries.  
  value: `` metric:  task:  conditions:   
  source: h2o-2306.14048.txt p.7 Sec. 5.1 Baselines  
  quote: `O evenly assigns the caching budget to H2 and the most recent KV`
- **H2-004** (mechanism) Eviction is decided independently per head and layer from accumulated attention scores, one KV entry evicted per step.  
  value: `` metric:  task:  conditions:   
  source: h2o-2306.14048.txt p.27 Appendix C.9  
  quote: `each token can be kept or evicted independently across heads and layers`
- **H2-005** (mechanism) Attention matrices are over 95% sparse at inference in almost all layers, which motivates dropping KV entries.  
  value: `over 95%` metric: sparsity (threshold = 1% of row max) task: WikiText-103 conditions: OPT, zero-shot  
  source: h2o-2306.14048.txt p.4 Sec. 3.1  
  quote: `highly sparse, with a sparsity over 95% in almost all layers`
- **H2-006** (mechanism) H2O does not evict from the prompt only: during prefill the full prompt is processed, then K heavy hitters plus K recent tokens are kept if prompt length >= 2K; decoding then evicts one heavy hitter per head per step.  
  value: `` metric:  task:  conditions: FlexGen-based implementation  
  source: h2o-2306.14048.txt p.20 Appendix A  
  quote: `During prefill iterations, the function compute_attention() will return K heavy hitters and K recent tokens if the prompt has a length greater than or equal to 2K`
- **H2-007** (mechanism) H2O alone is not enough: keeping only heavy hitters or only local tokens degrades quality by 2.85% to 22.75%; both are needed.  
  value: `2.85% to 22.75%` metric: accuracy degradation task: PiQA, OpenBookQA, MathQA, Winogrande conditions: OPT-13B, OPT-30B, 20% budget  
  source: h2o-2306.14048.txt p.10 Sec. 5.3 Q4  
  quote: `only retaining the embeddings of H2 or local tokens can't maintain a similar performance as the model using full embeddings, with a performance degradation from 2.85% to 22.75%`
- **H2-008** (limitation) Authors' own failure analysis: accumulated attention score favours older tokens (bias), and averaging instead of summing hurt performance.  
  value: `` metric:  task:  conditions:   
  source: h2o-2306.14048.txt p.21 Appendix B.2  
  quote: `can lead to a potential bias favoring the least recent tokens`
- **H2-009** (mechanism) H2O needs no training or fine-tuning in the experiments (pre-trained models evaluated directly); the paper contrasts itself with a learnable token-dropping method that needs extra fine-tuning but does not itself use the phrase 'training-free'.  
  value: `` metric:  task:  conditions: inferred from experiments  
  source: h2o-2306.14048.txt p.3 Sec. 2  
  quote: `requires an extra fine-tuning process, which makes it less practical`
- **H2-010** (io) H2O is implemented inside a white-box serving stack: FlexGen's OPT implementation had its KV-cache handling modified. This requires access to model internals and the inference engine.  
  value: `` metric:  task:  conditions:   
  source: h2o-2306.14048.txt p.20 Appendix A System Details  
  quote: `FlexGen is a white-box implementation of OPT models, and we have done some surgery on handling the KV cache.`
- **H2-011** (io) Implementation detail: to stay I/O efficient evicted KV slots are overwritten in place by newly added KV, i.e. cache memory management of the serving engine is changed.  
  value: `` metric:  task:  conditions:   
  source: h2o-2306.14048.txt p.6 Sec. 4.2  
  quote: `we do not swap memory when stored KV is evicted, but directly fill with newly-added KV`
- **H2-012** (limitation) The paper never discusses closed/API-only models; all experiments use open weights (OPT, LLaMA, GPT-NeoX) and the method edits the KV cache, so it cannot be applied to a remote API model. (Inferred from mechanism.)  
  value: `not reported` metric:  task:  conditions: inferred from mechanism  
  source: h2o-2306.14048.txt p.20 Appendix A  
  quote: `FlexGen is a white-box implementation of OPT models`
- **H2-013** (io) Output of H2O is a smaller KV cache (not text, not soft prompts).  
  value: `` metric:  task:  conditions: inferred from mechanism  
  source: h2o-2306.14048.txt p.1 Abstract  
  quote: `a KV cache eviction`
- **H2-020** (compression_ratio) Headline claim: H2O reduces KV cache memory 5-10x with comparable accuracy on most tasks.  
  value: `5-10x` metric:  task: lm-eval-harness and HELM tasks conditions: OPT/LLaMA/GPT-NeoX; 5-shot lm-eval tasks, 0-shot HELM tasks  
  source: h2o-2306.14048.txt p.7 Sec. 5.1  
  quote: `5-10� while achieving comparable accuracy on a majority of tasks`
- **H2-021** (compression_ratio) KV budgets tested are 4%, 10%, 20% and 60% of the prompt length (relative budgets, not absolute token counts).  
  value: `4%, 10%, 20%, 60%` metric:  task: XSUM, CNN/Daily Mail, lm-eval tasks conditions:   
  source: h2o-2306.14048.txt p.20 Appendix A Experiment Details  
  quote: `varying sizes of KV cache that encompass 4%, 10%, 20%, and 60% of the prompt's length`
- **H2-022** (compression_ratio) H2O with under 20% budget (more than 5x memory reduction) matches full-KV performance on the 5-shot tasks; the paper reports this as a 5x reduction.  
  value: `<20% budget` metric:  task: lm-eval tasks conditions: 5-shot  
  source: h2o-2306.14048.txt p.8 Sec. 5.1 Main Results  
  quote: `less than 20% KV cache budget(i.e., more than 5� memory reduction)`
- **H2-023** (limitation) Short prompts need larger budgets: on 0/1-shot tasks (100-300 token prompts) some tasks need a 30-40% KV budget.  
  value: `30-40%` metric:  task: lm-eval tasks, 0/1-shot conditions: LLaMA-7B  
  source: h2o-2306.14048.txt p.25 Appendix C.3  
  quote: `resulting in a higher KV cache budget (30-40%)`
- **H2-024** (compression_ratio) Streaming H2O handles inputs up to four million tokens on PG-19 (perplexity).  
  value: `up to four million tokens` metric: perplexity task: PG-19 conditions: streaming mode, first sample  
  source: h2o-2306.14048.txt p.9 Sec. 5.3 Q1  
  quote: `Effective generation with sequence length up to four million tokens`
- **H2-030** (tasks_tested) Datasets: COPA, MathQA, OpenBookQA, PiQA, RTE, Winogrande from lm-eval-harness, XSUM and CNN/Daily Mail from HELM. No coding, long-document QA benchmark, chat, or PII dataset is listed.  
  value: `COPA, MathQA, OpenBookQA, PiQA, RTE, Winogrande, XSUM, CNN/Daily Mail` metric:  task:  conditions: dataset list  
  source: h2o-2306.14048.txt p.7 Sec. 5.1 Setup  
  quote: `COPA [42], MathQA [43], OpenBookQA [44], PiQA [45], RTE [46], Winogrande [47], XSUM [48], CNN/Daily Mail [49]`
- **H2-031** (tasks_tested) Evaluation protocol: HELM tasks (XSUM, CNN/DM) are zero-shot, lm-eval-harness tasks are 5-shot by default; the metric for XSUM/CNN-DM is not named in the text.  
  value: `0-shot (HELM); 5-shot (lm-eval)` metric: not stated task: XSUM, CNN/Daily Mail, lm-eval tasks conditions:   
  source: h2o-2306.14048.txt p.20 Appendix A  
  quote: `performance for zero-shot inference, while for the tasks from lm-eval-harness, we default to conduct five-shot inference`
- **H2-031b** (tasks_tested) The HELM summarization tasks (XSUM, CNN/DM) are evaluated on 1000 test samples.  
  value: `1000 test samples` metric: not stated task: XSUM, CNN/Daily Mail conditions:   
  source: h2o-2306.14048.txt p.20 Appendix A  
  quote: `present the performance based on 1000 test samples`
- **H2-032** (context_loss) Table 1 (5-shot, 20% KV budget per text; model not named in the caption): H2O row, columns PiQA, COPA, OpenBookQA, Winogrande. Compare Full (H2-033) and Local (H2-034).  
  value: `H2O 79.22/85.00/43.80/71.67; Full 80.09/81.00/44.80/71.51` metric: accuracy task: PiQA, COPA, OpenBookQA, Winogrande conditions: 5-shot; 20% budget stated in text; model not stated in table  
  source: h2o-2306.14048.txt p.8 Table 1  
  quote: `H2 O 79.22 85.00 43.80 71.67`
- **H2-033** (context_loss) Table 1 full-KV reference row (column order PiQA, COPA, OpenBookQA, Winogrande).  
  value: `80.09; 81.00; 44.80; 71.51` metric: accuracy task: PiQA, COPA, OpenBookQA, Winogrande conditions: Full KV; model not stated in table  
  source: h2o-2306.14048.txt p.8 Table 1  
  quote: `Full 80.09 81.00 44.80 71.51`
- **H2-034** (context_loss) Table 1 'Local' baseline (most recent tokens only) collapses at the same budget.  
  value: `57.94; 56.00; 28.40; 51.30` metric: accuracy task: PiQA, COPA, OpenBookQA, Winogrande conditions: Local; model not stated in table  
  source: h2o-2306.14048.txt p.8 Table 1  
  quote: `Local 57.94 56.00 28.40 51.30`
- **H2-035** (context_loss) Table 9 ablation, OPT-30B PiQA: Full 78.51; Local only 55.82; heavy hitters only 67.25; Local + H2 (H2O) 78.45.  
  value: `78.51; 55.82; 67.25; 78.45` metric: accuracy task: PiQA conditions: OPT-30B, 20% budget; columns Full, w. Local, w. H2, w. Local + H2  
  source: h2o-2306.14048.txt p.27 Table 9  
  quote: `OPT-30B 78.51 55.82 67.25 78.45`
- **H2-036** (context_loss) Table 2, OPT-30B 20% budget: full model COPA 85.00, OpenBookQA 43.20, PiQA 78.51, Winogrande 70.24.  
  value: `85.00; 43.20; 78.51; 70.24` metric: accuracy task: COPA, OpenBookQA, PiQA, Winogrande conditions: OPT-30B, Full  
  source: h2o-2306.14048.txt p.8 Table 2  
  quote: `Full 85.00 43.20 78.51 70.24`
- **H2-037** (context_loss) Table 2: Local + H2 (this is H2O) with OPT-30B at 20% budget: COPA 84.00, OpenBookQA 43.00, PiQA 78.45, Winogrande 69.06.  
  value: `84.00; 43.00; 78.45; 69.06` metric: accuracy task: COPA, OpenBookQA, PiQA, Winogrande conditions: OPT-30B, 20% KV budget  
  source: h2o-2306.14048.txt p.8 Table 2  
  quote: `Local w. H2 84.00 43.00 78.45 69.06`
- **H2-038** (context_loss) Summarization (XSUM, CNN/Daily Mail): authors report H2O stays effective, but results are shown only as plots (Figure 4, LLaMA-7B/13B/30B, GPT-NeoX-20B); numeric scores are not in the text.  
  value: `not reported (plots only)` metric: not stated task: XSUM, CNN/Daily Mail conditions: LLaMA-7B/13B/30B, GPT-NeoX-20B; budgets 4%-100%  
  source: h2o-2306.14048.txt p.8 Sec. 5.1 Main Results  
  quote: `O shows consistent effectiveness in the more challenging long sequence generation tasks, XSUM, and CNN/Daily Mail`
- **H2-039** (context_loss) Figure 4 panel titles confirm summarization runs on LLaMA-7B, -13B, -30B and GPT-NeoX-20B.  
  value: `` metric:  task: XSUM conditions:   
  source: h2o-2306.14048.txt p.7 Figure 4  
  quote: `XSUM, LLaMA-7B XSUM, LLaMA-13B XSUM, LLaMA-30B XSUM, GPT-NeoX-20B`
- **H2-040** (context_loss) Qualitative failure of the Local baseline vs H2O: authors say dropping critical KV entries causes severe functional collapse.  
  value: `` metric:  task:  conditions:   
  source: h2o-2306.14048.txt p.8 Sec. 5.1 Analysis  
  quote: `dropping certain critical KV embeddings can cause a severe functional collapse`
- **H2-041** (context_loss) Table 10 OpenBookQA, H2O row at 20% budget: 5-shot OPT-30B 43.00, OPT-66B 44.20; 10-shot OPT-30B 42.80, OPT-66B 44.80 (column order per header).  
  value: `43.00; 44.20; 42.80; 44.80` metric: accuracy task: OpenBookQA conditions: 20% budget; columns 5-shots OPT-30B, OPT-66B, 10-shots OPT-30B, OPT-66B  
  source: h2o-2306.14048.txt p.27 Table 10  
  quote: `H2 O 43.00 44.20 42.80 44.80`
- **H2-041b** (context_loss) Table 10 OpenBookQA, Full-KV row for the same columns.  
  value: `43.20; 44.40; 43.00; 44.80` metric: accuracy task: OpenBookQA conditions: Full KV; columns 5-shots OPT-30B, OPT-66B, 10-shots OPT-30B, OPT-66B  
  source: h2o-2306.14048.txt p.27 Table 10  
  quote: `Full 43.20 44.40 43.00 44.80`
- **H2-042** (context_loss) H2O re-run by the SnapKV authors with a 4096-token prompt budget on the Mistral-7B-Instruct-v0.2 block of LongBench Table 1 (compare with full-KV and SnapKV rows in SK ids): HotpotQA 36.54, 2WikiMQA 20.6, GovReport 30.0.  
  value: `HotpotQA 36.54; 2WikiMQA 20.6; GovReport 30.0` metric: LongBench task metrics task: LongBench conditions: H2O-4096 on Mistral; run by SnapKV authors  
  source: snapkv-2404.14469.txt p.9 SnapKV Table 1 (see SK ids)  
  quote: `H2O: 4096 22.61 29.06 47.22 36.54 20.6 16.25 30.0 23.8 26.75 70.5 86.16 42.97 3.46 86.38 53.72 51.1`
- **H2-050** (io) Claimed model coverage: OPT, LLaMA, GPT-NeoX with sizes 'from 6.7B to 175B'; figure panels name OPT-30B, OPT-66B, LLaMA-7B/13B/30B and GPT-NeoX-20B (no OPT-175B panel appears in text, figures or tables).  
  value: `6.7B to 175B (claimed)` metric:  task:  conditions: claimed vs shown  
  source: h2o-2306.14048.txt p.7 Sec. 5  
  quote: `model architectures (OPT, LLaMA, GPT-NeoX), sizes (from 6.7B to 175B)`
- **H2-051** (io) Figure 4 panel titles name OPT-30B and OPT-66B among the evaluated models.  
  value: `` metric:  task: COPA, MathQA, RTE, OpenBookQA conditions:   
  source: h2o-2306.14048.txt p.7 Figure 4  
  quote: `COPA, OPT-30B MathQA, OPT-30B RTE, OPT-66B`
- **H2-060** (hardware) Quality experiments used a single NVIDIA A100 80GB GPU.  
  value: `A100 80GB` metric:  task:  conditions:   
  source: h2o-2306.14048.txt p.3 Sec. 1  
  quote: `on a single NVIDIA A100 (80GB) GPU`
- **H2-061** (hardware) Throughput experiments used an NVIDIA T4 (16GB) and an NVIDIA A100 (80GB).  
  value: `T4 16GB; A100 80GB` metric:  task:  conditions:   
  source: h2o-2306.14048.txt p.9 Sec. 5.2 Setup  
  quote: `an NVIDIA T4 (16GB) GPU and an NVIDIA A100 (80GB) GPU`
- **H2-062** (latency_compute) Throughput timing is end-to-end: includes both prefill and generation and the time to build the H2O cache; metric is generated tokens / (prompt time + decoding time).  
  value: `` metric: tokens/s task:  conditions: synthetic padded prompts and XSUM  
  source: h2o-2306.14048.txt p.9 Sec. 5.2 Setup  
  quote: `tested in an end-to-end setting, including both the pre-filling and generation phases`
- **H2-063** (latency_compute) Headline: with 20% heavy hitters, throughput up to 29x and 29x over DeepSpeed and Hugging Face Accelerate and 3x over FlexGen on OPT-6.7B/30B; see H2-063b for latency.  
  value: `29x; 29x; 3x` metric: throughput task:  conditions: 20% budget; T4/A100; OPT-6.7B, OPT-30B  
  source: h2o-2306.14048.txt p.1 Abstract  
  quote: `up to 29�, 29�, and 3� on OPT-6.7B and OPT-30B`
- **H2-063b** (latency_compute) Abstract: at the same batch size H2O can reduce latency by up to 1.9x.  
  value: `up to 1.9x` metric: latency task:  conditions: same batch size vs FlexGen  
  source: h2o-2306.14048.txt p.1 Abstract  
  quote: `can reduce the latency by up to 1.9�`
- **H2-064** (latency_compute) Table 3 header: prompt+generation lengths 512+32, 512+512, 512+1024 for OPT-6.7B and OPT-30B on a T4; entries are tokens/s with (effective batch size, lowest memory tier G=GPU / C=CPU).  
  value: `` metric: tokens/s task:  conditions: T4 16GB  
  source: h2o-2306.14048.txt p.8 Table 3 header  
  quote: `Seq. length 512+32 512+512 512+1024`
- **H2-065** (latency_compute) Table 3 FlexGen row (T4): 20.2, 8.1, 16.8, 8.5, 16.9, 7.1 tokens/s for 6.7B/30B at the three lengths.  
  value: `20.2; 8.1; 16.8; 8.5; 16.9; 7.1` metric: tokens/s task: synthetic conditions: T4 16GB; (batch, tier) in brackets  
  source: h2o-2306.14048.txt p.8 Table 3  
  quote: `FlexGen 20.2 (2, G) 8.1 (144, C) 16.8 (1, G) 8.5 (80, C) 16.9 (1, G) 7.1 (48, C)`
- **H2-066** (latency_compute) Table 3 H2O 20% row (T4): 35.1, 12.7, 51.7, 18.83, 52.1, 13.82 tokens/s, using larger effective batches (4, 728, 4, 416, 4, 264).  
  value: `35.1; 12.7; 51.7; 18.83; 52.1; 13.82` metric: tokens/s task: synthetic conditions: T4 16GB; H2O 20% budget; batch sizes in brackets are larger than FlexGen's  
  source: h2o-2306.14048.txt p.8 Table 3  
  quote: `H2 O (20%) 35.1 (4, G) 12.7 (728, C) 51.7 (4, G) 18.83 (416, C) 52.1 (4, G) 13.82 (264, C)`
- **H2-067** (latency_compute) Table 3 Accelerate row (T4); the 29x claim is against slow offloaded baselines at 0.6 token/s for 30B.  
  value: `20.4; 0.6; 15.5; 0.6; 5.6; 0.6` metric: tokens/s task: synthetic conditions: T4 16GB  
  source: h2o-2306.14048.txt p.8 Table 3  
  quote: `Accelerate 20.4 (2, G) 0.6 (8, C) 15.5 (1, G) 0.6 (8, C) 5.6 (16, C) 0.6 (8, C)`
- **H2-068** (latency_compute) Table 4 (XSUM on T4): FlexGen 10.80 (6.7B) and 3.29 (30B) tokens/s vs H2O 20% 30.40 and 6.70.  
  value: `FlexGen 10.80; 3.29` metric: tokens/s task: XSUM conditions: T4 16GB; columns 6.7B, 30B  
  source: h2o-2306.14048.txt p.9 Table 4  
  quote: `FlexGen 10.80 (1, G) 3.29 (44, C)`
- **H2-069** (latency_compute) Table 4 H2O 20% row (XSUM, T4).  
  value: `30.40; 6.70` metric: tokens/s task: XSUM conditions: T4 16GB; effective batch 1 (6.7B) and 180 (30B)  
  source: h2o-2306.14048.txt p.9 Table 4  
  quote: `H2 O (20%) 30.40 (1, G) 6.70 (180, C)`
- **H2-070** (latency_compute) Table 5 header (A100): columns are FlexGen and H2O 20%; rows give prompt+generation length, model, batch, metric.  
  value: `` metric: latency (s); tokens/s task:  conditions: A100 80GB  
  source: h2o-2306.14048.txt p.9 Table 5 header  
  quote: `Seq. length Model size Batch size Metric FlexGen H2 O (20%)`
- **H2-071** (latency_compute) Table 5: 7000+1024, OPT-30B, batch 1: latency 57.0 s (FlexGen) vs 50.4 s (H2O).  
  value: `57.0 vs 50.4` metric: seconds task: synthetic conditions: A100 80GB; 7,000-token prompt  
  source: h2o-2306.14048.txt p.9 Table 5  
  quote: `7000+1024 30B 1 latency (s) 57.0 50.4`
- **H2-072** (latency_compute) Table 5: 5000+5000, OPT-13B, batch 4: latency 214.2 s vs 155.4 s.  
  value: `214.2 vs 155.4` metric: seconds task: synthetic conditions: A100 80GB  
  source: h2o-2306.14048.txt p.9 Table 5  
  quote: `5000+5000 13B 4 latency (s) 214.2 155.4`
- **H2-073** (latency_compute) Table 5: 2048+2048, OPT-6.7B, batch 24: latency 99.5 s vs 53.5 s.  
  value: `99.5 vs 53.5` metric: seconds task: synthetic conditions: A100 80GB  
  source: h2o-2306.14048.txt p.9 Table 5  
  quote: `2048+2048 6.7B 24 latency (s) 99.5 53.5`
- **H2-074** (latency_compute) Table 5: 2048+2048, OPT-6.7B, batch 24: throughput 494.1 vs 918.9 tokens/s.  
  value: `494.1 vs 918.9` metric: tokens/s task: synthetic conditions: A100 80GB  
  source: h2o-2306.14048.txt p.9 Table 5  
  quote: `2048+2048 6.7B 24 throughput (token/s) 494.1 918.9`
- **H2-075** (latency_compute) Table 5: with batch 64, FlexGen runs out of memory while H2O reaches 1161.0 tokens/s.  
  value: `OOM vs 1161.0` metric: tokens/s task: synthetic conditions: A100 80GB; OPT-6.7B, 2048+2048  
  source: h2o-2306.14048.txt p.9 Table 5  
  quote: `2048+2048 6.7B 64 throughput (token/s) OOM 1161.0`
- **H2-076** (latency_compute) Authors attribute the throughput gain to the smaller KV cache allowing a much larger batch size and avoiding CPU offloading; at equal batch size latency falls only 1.1-1.9x vs FlexGen.  
  value: `1.1-1.9x` metric: latency task:  conditions: A100, same batch size  
  source: h2o-2306.14048.txt p.9 Sec. 5.2 Results  
  quote: `With the same batch size, H2 O can reduce the latency by 1.1 - 1.9� compared to FlexGen`
- **H2-077** (latency_compute) Mechanism of speedup: memory use drops, enabling (1) a larger batch and (2) settings that no longer need offloading.  
  value: `` metric:  task:  conditions:   
  source: h2o-2306.14048.txt p.9 Sec. 5.2 Results  
  quote: `we can use a much larger batch size`
- **H2-078** (latency_compute) Motivating figure for KV memory: a 30B-parameter model with batch 128 and sequence length 1024 needs 180GB of KV cache.  
  value: `180GB` metric:  task:  conditions:   
  source: h2o-2306.14048.txt p.1 Sec. 1  
  quote: `with an input batch size of 128 and a sequence length of 1024 results in 180GB of KV cache`
- **H2-079** (latency_compute) Speed and latency were benchmarked at sequence lengths up to 10K on the A100 although OPT was trained on only 2K context; quality at those lengths is not reported.  
  value: `up to 10K` metric:  task:  conditions: A100 80GB  
  source: h2o-2306.14048.txt p.9 Sec. 5.2 Setup  
  quote: `with sequence lengths up to 10K. Although OPT is only trained on 2K sequence length`
- **H2-080** (cost) No per-request token or dollar saving applies: H2O does not shorten the prompt; the prompt is still processed in full during prefill.  
  value: `not applicable` metric:  task:  conditions: inferred from mechanism  
  source: h2o-2306.14048.txt p.20 Appendix A  
  quote: `compute_attention() will return K heavy hitters and K recent tokens if the prompt has a length`
- **H2-090** (limitation) Authors' limitations paragraph: implementing LLM inference stays hard due to parameter count; they suggest exploiting heavy hitters in MLP blocks for offloading policies. No other limitation is stated.  
  value: `` metric:  task:  conditions:   
  source: h2o-2306.14048.txt p.22 Appendix B.2 Limitations  
  quote: `implementing LLMs for generative inference remains challenging due to the immense parameter count`
- **H2-091** (limitation) The paper says AlpacaEval and MT-bench were also evaluated with details in the Appendix, but no AlpacaEval/MT-bench results appear in the appendix text read.  
  value: `not reported` metric:  task: AlpacaEval, MT-bench conditions:   
  source: h2o-2306.14048.txt p.7 Sec. 5.1 Setup  
  quote: `we evaluate our approach on recent generation benchmarks, AlpaceEval`
- **H2-092** (limitation) Multi-document QA (ten documents, key document position varied) is only shown as plots in Figure 9, comparing H2O to StreamingLLM; no numbers in text.  
  value: `not reported (plots only)` metric:  task: multi-document QA conditions:   
  source: h2o-2306.14048.txt p.26 Appendix C.4  
  quote: `each test sample comprises ten documents, followed by a question`
- **H2-093** (limitation) SnapKV's authors say H2O overlooks compression of prompt KVs, whereas H2O's own appendix pseudocode compresses the prompt KV at prefill (to K heavy hitters + K recent); the two papers describe it differently.  
  value: `` metric:  task:  conditions: cross-paper  
  source: snapkv-2404.14469.txt p.3 SnapKV Sec. 2  
  quote: `it overlooks compression of prompt KVs`
- **H2-100** (reproducibility) Code released: the abstract points to the FMInference/H2O GitHub repository.  
  value: `code released` metric:  task:  conditions:   
  source: h2o-2306.14048.txt p.1 Abstract  
  quote: `The code is available at https: //github.com/FMInference/H2O`
- **H2-101** (reproducibility) Checked 2026-11-05: the official repo page shows a license badge reading MIT (no LICENSE file visible in the page listing, per WebFetch summary); code is based on FlexGen and Hugging Face.  
  value: `MIT (badge)` metric:  task:  conditions:   
  source: https://github.com/FMInference/H2O GitHub repo page  
  quote: `License: MIT`
- **H2-110** (tasks_tested) Coding, multi-turn chat, structured data (JSON/tables/logs), PII/sensitive content, Needle-in-a-Haystack and LongBench are not in the paper's listed datasets (the longest-context evaluation is perplexity on PG-19 streaming).  
  value: `not tested in paper` metric:  task:  conditions: dataset list in Sec. 5.1 and Appendix A  
  source: h2o-2306.14048.txt p.7 Sec. 5.1 Setup  
  quote: `COPA [42], MathQA [43], OpenBookQA [44], PiQA [45], RTE [46], Winogrande [47], XSUM [48], CNN/Daily Mail [49]`
- **H2-111** (tasks_tested) Reasoning/math: MathQA (multiple-choice math word problems) is tested on OPT; Table 9 OPT-30B MathQA: Full 26.23, Local 20.87, H2 only 21.98, H2O 26.87.  
  value: `tested (MathQA)` metric: accuracy task: MathQA conditions: OPT-30B, 20% budget; columns Full, w. Local, w. H2, w. Local + H2  
  source: h2o-2306.14048.txt p.27 Table 9  
  quote: `OPT-30B 26.23 20.87 21.98 26.87`

## LLMLingua

- **LLv1-ABL-1** (context_loss) Table 3 ablation (GSM8K, 1-shot constraint; target LLM not named in caption): full method reference.  
  value: `79.08 5x` metric: EM task: GSM8K conditions: 1-shot constraint; ablation  
  source: llmlingua.txt p.7 Table 3  
  quote: `Ours 79.08 439 5x`
- **LLv1-ABL-10** (context_loss) Authors conclude instructions and questions need a lower compression ratio than demonstrations.  
  value: `` metric:  task: GSM8K conditions: ablation  
  source: llmlingua.txt p.7 Sec. 5.4  
  quote: `Instructions and questions necessitate a lower compression ratio`
- **LLv1-ABL-2** (context_loss) Removing the budget controller (same ratio for every component) drops EM at the same 5x ratio.  
  value: `73.62` metric: EM task: GSM8K conditions: 1-shot constraint; ablation  
  source: llmlingua.txt p.7 Table 3  
  quote: `- w/o Budget Controller 73.62 486 5x`
- **LLv1-ABL-3** (context_loss) Definition of the 'w/o Budget Controller' variant.  
  value: `` metric:  task: GSM8K conditions: ablation  
  source: llmlingua.txt p.7 Sec. 5.4  
  quote: `Ours w/o Budget Controller, which directly employs ITPC with the same compression ratio for all components`
- **LLv1-ABL-4** (context_loss) Removing iterative token-level compression lowers EM.  
  value: `72.93` metric: EM task: GSM8K conditions: 1-shot constraint; ablation  
  source: llmlingua.txt p.7 Table 3  
  quote: `- w/o Iterative Token-level Prompt Compression 72.93 453 5x`
- **LLv1-ABL-5** (context_loss) Using one ratio for all components (no dynamic ratio) lowers EM.  
  value: `77.26` metric: EM task: GSM8K conditions: 1-shot constraint; ablation  
  source: llmlingua.txt p.7 Table 3  
  quote: `- w/o Dynamic Compression Ratio 77.26 457 5x`
- **LLv1-ABL-6** (context_loss) Random demonstration selection in the budget controller lowers EM, so perplexity-based selection matters.  
  value: `72.78` metric: EM task: GSM8K conditions: 1-shot constraint; ablation  
  source: llmlingua.txt p.7 Table 3  
  quote: `- w/ Random Selection in Budget Controller 72.78 477 5x`
- **LLv1-ABL-7** (context_loss) Removing distribution alignment costs little EM on GSM8K.  
  value: `78.62` metric: EM task: GSM8K conditions: 1-shot constraint; ablation  
  source: llmlingua.txt p.7 Table 3  
  quote: `- w/o Distribution Alignment 78.62 452 5x`
- **LLv1-ABL-8** (context_loss) Authors quantify the contribution of alignment as 0.56 EM on GSM8K.  
  value: `0.56` metric: EM points task: GSM8K conditions: ablation  
  source: llmlingua.txt p.7 Sec. 5.4  
  quote: `resulting in a further improvement of 0.56 on GSM8K`
- **LLv1-ABL-9** (context_loss) Stop-word removal baseline barely compresses (1.3x) and still loses EM.  
  value: `76.27 1.3x` metric: EM task: GSM8K conditions: 1-shot constraint; ablation  
  source: llmlingua.txt p.7 Table 3  
  quote: `- w/ Remove Stop Words 76.27 1,882 1.3x`
- **LLv1-CL-1** (context_loss) Table 2 (GSM8K | BBH, each EM / Tokens / 1/tau): uncompressed full-shot reference, 8-shot complex CoT prompt for GSM8K (2,366 tokens) and 3-shot CoT for BBH (774 tokens).  
  value: `78.85 / 70.07` metric: EM task: GSM8K / BBH conditions: GPT-3.5-Turbo (default target); full-shot baseline  
  source: llmlingua.txt p.6 Table 2  
  quote: `Full-shot 78.85 2,366 - 70.07 774 -`
- **LLv1-CL-10** (context_loss) Selective-Context baseline at quarter-shot constraint.  
  value: `44.20 15x / 47.37 7x` metric: EM task: GSM8K / BBH conditions: Alpaca-7B small LM; GPT-3.5-Turbo  
  source: llmlingua.txt p.6 Table 2  
  quote: `Selective-Context 44.20 157 15x 47.37 108 7x`
- **LLv1-CL-11** (context_loss) Sentence Selection baseline at quarter-shot constraint.  
  value: `66.67 12x / 46.00 7x` metric: EM task: GSM8K / BBH conditions: GPT-3.5-Turbo  
  source: llmlingua.txt p.6 Table 2  
  quote: `Sentence Selection 66.67 195 12x 46.00 109 7x`
- **LLv1-CL-12** (context_loss) GPT-4 generation (LLM-summarised prompt) baseline at quarter-shot constraint.  
  value: `56.33 20x / 26.81 8x` metric: EM task: GSM8K / BBH conditions: GPT-3.5-Turbo target; GPT-4 compressor  
  source: llmlingua.txt p.6 Table 2  
  quote: `GPT4 Generation 56.33 188 20x 26.81 101 8x`
- **LLv1-CL-13** (context_loss) Selective-Context at 1-shot constraint collapses on GSM8K and BBH relative to LLMLingua.  
  value: `53.98 5x / 54.27 3x` metric: EM task: GSM8K / BBH conditions: GPT-3.5-Turbo; 1-shot constraint  
  source: llmlingua.txt p.6 Table 2  
  quote: `Selective-Context 53.98 452 5x 54.27 276 3x`
- **LLv1-CL-14** (context_loss) Authors report GSM8K EM drops of 1.44 and 1.52 at 14x and 20x, and BBH EM drops of 8.5 and 13.2 points at 5x and 7x.  
  value: `1.44; 1.52; 8.5; 13.2` metric: EM points task: GSM8K, BBH conditions: GPT-3.5-Turbo; half-shot and quarter-shot  
  source: llmlingua.txt p.6 Sec. 5.2  
  quote: `will decrease by 1.44 and 1.52, respectively, despite compression ratios as high as 14x and 20x`
- **LLv1-CL-15** (context_loss) BBH drop quote: 8.5 and 13.2 points at 5x and 7x.  
  value: `8.5; 13.2` metric: EM points task: BBH conditions: GPT-3.5-Turbo  
  source: llmlingua.txt p.6 Sec. 5.2  
  quote: `tios of 5x and 7x with the EM score decreasing by 8.5 and 13.2 points, respectively`
- **LLv1-CL-16** (context_loss) Authors attribute the BBH decline mainly to hard reasoning subtasks such as tracking_shuffled_objects_seven_objects.  
  value: `` metric:  task: BBH conditions: case study  
  source: llmlingua.txt p.6 Sec. 5.2  
  quote: `mainly due to challenging reasoning tasks, such as tracking_shuffled_objects_seven_objects`
- **LLv1-CL-17** (context_loss) Table 1 (ShareGPT | Arxiv-March23; each BLEU, Rouge1, Rouge2, RougeL, BS F1, Tokens, 1/tau). Constraint I header: 2x on ShareGPT and 350 tokens on Arxiv.  
  value: `` metric:  task: ShareGPT / Arxiv-March23 conditions:   
  source: llmlingua.txt p.6 Table 1  
  quote: `Constraint I 2x constraint 350 tokens constraint`
- **LLv1-CL-18** (context_loss) Table 1 Constraint I: LLMLingua row (ShareGPT then Arxiv-March23); 1.9x and 4x compression.  
  value: `27.36 BLEU 1.9x / 23.15 BLEU 4x` metric: BLEU, ROUGE, BERTScore F1 vs GPT-3.5-Turbo output from full prompt task: ShareGPT / Arxiv-March23 conditions: GPT-3.5-Turbo; reference = output from original prompt  
  source: llmlingua.txt p.6 Table 1  
  quote: `Ours 27.36 48.87 30.32 38.55 89.52 304 1.9x 23.15 54.21 32.66 42.74 90.33 345 4x`
- **LLv1-CL-19** (context_loss) Table 1 Constraint II header: 3x on ShareGPT and 175 tokens on Arxiv.  
  value: `` metric:  task: ShareGPT / Arxiv-March23 conditions:   
  source: llmlingua.txt p.6 Table 1  
  quote: `Constraint II 3x constraint 175 tokens constraint`
- **LLv1-CL-2** (context_loss) Table 2 1-shot constraint: LLMLingua row (GSM8K EM, tokens, ratio, then BBH EM, tokens, ratio).  
  value: `79.08 5x / 70.11 3x` metric: EM task: GSM8K / BBH conditions: GPT-3.5-Turbo; 1-shot constraint  
  source: llmlingua.txt p.6 Table 2  
  quote: `Ours 79.08 446 5x 70.11 288 3x`
- **LLv1-CL-20** (context_loss) Table 1 Constraint II: LLMLingua row; ShareGPT 3.3x, Arxiv-March23 9x.  
  value: `19.55 BLEU 3.3x / 13.45 BLEU 9x` metric: BLEU, ROUGE, BERTScore F1 vs GPT-3.5-Turbo output from full prompt task: ShareGPT / Arxiv-March23 conditions: GPT-3.5-Turbo; reference = output from original prompt  
  source: llmlingua.txt p.6 Table 1  
  quote: `Ours 19.55 40.81 22.68 30.98 87.70 177 3.3x 13.45 44.36 24.86 34.94 89.03 176 9x`
- **LLv1-CL-21** (context_loss) Table 1 Constraint II: Selective-Context baseline row for comparison.  
  value: `15.79 BLEU 3.3x / 12.23 BLEU 8x` metric: BLEU, ROUGE, BERTScore F1 task: ShareGPT / Arxiv-March23 conditions: Alpaca-7B small LM; GPT-3.5-Turbo  
  source: llmlingua.txt p.6 Table 1  
  quote: `Selective-Context 15.79 38.42 20.55 28.89 87.12 180 3.3x 12.23 42.47 19.48 29.47 88.16 185 8x`
- **LLv1-CL-22** (context_loss) Text claims 9x and 3.3x acceleration ratios with high BERTScore F1; order of datasets in text (ShareGPT first) is reversed relative to Table 1 (ShareGPT 3.3x, Arxiv 9x).  
  value: `9x; 3.3x` metric: BERTScore F1 task: ShareGPT, Arxiv-March23 conditions:   
  source: llmlingua.txt p.6 Sec. 5.2  
  quote: `our approach achieves acceleration ratios of 9x and 3.3x with a high BERTScore F1`
- **LLv1-CL-23** (context_loss) ShareGPT references are GPT-3.5-Turbo outputs from the full-dialogue prompt (all rounds but the last form the prompt), so scores measure similarity to the uncompressed-prompt output, not to a human gold answer.  
  value: `` metric:  task: ShareGPT conditions:   
  source: llmlingua.txt p.12 Appendix A.1  
  quote: `We use all dialogues except the final round as the prompt and generate results with GPT-3.5-Turbo as the reference`
- **LLv1-CL-24** (context_loss) Arxiv-March23 reference summary is also generated by GPT-3.5-Turbo from the full prompt.  
  value: `` metric:  task: Arxiv-March23 conditions:   
  source: llmlingua.txt p.12 Appendix A.1  
  quote: `concatenate these sections to form the original prompt and use GPT-3.5-Turbo to generate the summary as the reference`
- **LLv1-CL-25** (context_loss) Metrics: BLEU, ROUGE, BERTScore for ShareGPT and Arxiv-March23.  
  value: `` metric: BLEU, ROUGE, BERTScore task: ShareGPT, Arxiv-March23 conditions:   
  source: llmlingua.txt p.5 Sec. 5.1  
  quote: `as the evaluation metrics for ShareGPT and Arxiv-March23`
- **LLv1-CL-26** (context_loss) Metric: Exact Match for GSM8K and BBH.  
  value: `` metric: Exact Match task: GSM8K, BBH conditions:   
  source: llmlingua.txt p.5 Sec. 5.1  
  quote: `we utilize the Exact Match as the evaluation metric for GSM8K and BBH`
- **LLv1-CL-27** (context_loss) Claude-v1.3 target, GSM8K 1-shot constraint: LLMLingua row.  
  value: `83.51 5x` metric: EM task: GSM8K conditions: Claude-v1.3; Alpaca-7B small LM; 1-shot constraint  
  source: llmlingua.txt p.7 Table 4  
  quote: `Ours in 1-shot constraint 83.51 439 5x`
- **LLv1-CL-28** (context_loss) Claude-v1.3 target, GSM8K half-shot constraint: LLMLingua row.  
  value: `82.61 14x` metric: EM task: GSM8K conditions: Claude-v1.3; Alpaca-7B small LM; half-shot constraint  
  source: llmlingua.txt p.7 Table 4  
  quote: `Ours in half-shot constraint 82.61 171 14x`
- **LLv1-CL-29** (context_loss) Claude-v1.3 'Simple Prompt' baseline for the same GSM8K setup.  
  value: `81.8 3x` metric: EM task: GSM8K conditions: Claude-v1.3  
  source: llmlingua.txt p.7 Table 4  
  quote: `Simple Prompt 81.8 691 3x`
- **LLv1-CL-3** (context_loss) Table 2 half-shot constraint: LLMLingua row.  
  value: `77.41 14x / 61.60 5x` metric: EM task: GSM8K / BBH conditions: GPT-3.5-Turbo; half-shot constraint  
  source: llmlingua.txt p.6 Table 2  
  quote: `Ours 77.41 171 14x 61.60 171 5x`
- **LLv1-CL-30** (context_loss) Claude was evaluated only at 1-shot and half-shot constraints on GSM8K because of API cost.  
  value: `` metric:  task: GSM8K conditions: Claude-v1.3  
  source: llmlingua.txt p.7 Sec. 5.5  
  quote: `we only consider the scenarios with one-shot constraint and half-shot constraint`
- **LLv1-CL-31** (context_loss) GPT2-Alpaca small LM, GSM8K 1-shot constraint.  
  value: `77.02 5x` metric: EM task: GSM8K conditions: GPT-3.5-Turbo; GPT2-Alpaca small LM  
  source: llmlingua.txt p.8 Table 5  
  quote: `Ours with GPT2 in 1-shot constraint 77.02 447 5x`
- **LLv1-CL-32** (context_loss) GPT2-Alpaca small LM, GSM8K quarter-shot constraint.  
  value: `76.27 18x` metric: EM task: GSM8K conditions: GPT-3.5-Turbo; GPT2-Alpaca small LM  
  source: llmlingua.txt p.8 Table 5  
  quote: `Ours with GPT2 in quarter-shot constraint 76.27 128 18x`
- **LLv1-CL-33** (context_loss) GPT2-Alpaca is weaker than Alpaca-7B by a stated EM margin at each ratio.  
  value: `2.06; 0.99; 1.06` metric: EM points task: GSM8K conditions: GPT-3.5-Turbo  
  source: llmlingua.txt p.8 Sec. 5.5  
  quote: `are weaker than those obtained by Alpaca-7B with a performance drop of 2.06, 0.99, and 1.06 EM points at different compression ratios`
- **LLv1-CL-34** (context_loss) Selective-Context is far below LLMLingua on GSM8K at 20x.  
  value: `33.10` metric: EM points task: GSM8K conditions: GPT-3.5-Turbo; 20x  
  source: llmlingua.txt p.7 Sec. 5.3  
  quote: `its performance is lower than ours by 33.10 points at a compression ratio of 20x`
- **LLv1-CL-4** (context_loss) Table 2 quarter-shot constraint: LLMLingua row; 20x on GSM8K, 7x on BBH.  
  value: `77.33 20x / 56.85 7x` metric: EM task: GSM8K / BBH conditions: GPT-3.5-Turbo; quarter-shot constraint  
  source: llmlingua.txt p.6 Table 2  
  quote: `Ours 77.33 117 20x 56.85 110 7x`
- **LLv1-CL-5** (context_loss) Table 2 zero-shot (instruction only) reference row.  
  value: `48.75 215x / 32.32 48x` metric: EM task: GSM8K / BBH conditions: GPT-3.5-Turbo; zero-shot  
  source: llmlingua.txt p.6 Table 2  
  quote: `zero-shot 48.75 11 215x 32.32 16 48x`
- **LLv1-CL-6** (context_loss) Table 2: simply keeping one demonstration ('1-shot') reaches near the compressed score at a similar ratio, i.e. a trivial baseline is strong at 1-shot budget.  
  value: `77.10 6x / 69.60 3x` metric: EM task: GSM8K / BBH conditions: GPT-3.5-Turbo; 1-shot constraint baseline  
  source: llmlingua.txt p.6 Table 2  
  quote: `1-shot 77.10 422 6x 69.60 284 3x`
- **LLv1-CL-7** (context_loss) Table 2: 'Simple Prompt' (standard shorter 8-shot 3-step CoT) scores below the compressed prompt on GSM8K; no BBH entry.  
  value: `74.9 3x` metric: EM task: GSM8K conditions: GPT-3.5-Turbo  
  source: llmlingua.txt p.6 Table 2  
  quote: `Simple Prompt 74.9 691 3x`
- **LLv1-CL-8** (context_loss) Text clarifies that the 'Simple Prompt' baseline is the 8-shot 3-step CoT, which the 20x compressed prompt beats.  
  value: `2.43` metric: EM points task: GSM8K conditions: GPT-3.5-Turbo; 20x  
  source: llmlingua.txt p.7 Sec. 5.3  
  quote: `ratios. Notably, on GSM8K, our 20x compressed prompt outperforms the 8-shot 3-step CoT by 2.43`
- **LLv1-CL-9** (context_loss) GSM8K original prompt used for the full-shot baseline is a complex multi-step CoT prompt, not the usual short CoT prompt.  
  value: `` metric:  task: GSM8K conditions:   
  source: llmlingua.txt p.12 Appendix A.1  
  quote: `we employ the complex multi-step CoT prompt (Fu et al., 2023b)10 as the original prompt`
- **LLv1-COST-1** (cost) Table 7 header: dataset columns GSM8K, BBH, ShareGPT, Arxiv.  
  value: `` metric: USD task:  conditions:   
  source: llmlingua.txt p.12 Table 7  
  quote: `GSM8K BBH ShareGPT Arxiv`
- **LLv1-COST-2** (cost) Table 7: estimated GPT-3.5-Turbo inference cost in dollars for the original prompts.  
  value: `5.2; 12.8; 0.7; 1.3` metric: USD task: GSM8K; BBH; ShareGPT; Arxiv conditions: GPT-3.5-Turbo pricing  
  source: llmlingua.txt p.12 Table 7  
  quote: `Original 5.2 12.8 0.7 1.3`
- **LLv1-COST-3** (cost) Table 7: estimated cost in dollars with LLMLingua-compressed prompts.  
  value: `0.5; 4.8; 0.3; 0.2` metric: USD task: GSM8K; BBH; ShareGPT; Arxiv conditions: GPT-3.5-Turbo pricing  
  source: llmlingua.txt p.12 Table 7  
  quote: `Ours 0.5 4.8 0.3 0.2`
- **LLv1-COST-4** (cost) Text states the dollar reductions per dataset; cost of running the small LM is not included.  
  value: `$4.7, $8.0, $0.4, $0.8` metric: USD task: GSM8K, BBH, ShareGPT, Arxiv conditions: GPT-3.5-Turbo pricing  
  source: llmlingua.txt p.12 Appendix B  
  quote: `cost reductions of $4.7, $8.0, $0.4, and $0.8 observed in the GSM8K, BBH, ShareGPT, and Arxiv datasets, respectively`
- **LLv1-COST-5** (cost) The system needs a local small-LM pass plus the target LLM call: total compute is the sum of compression and inference.  
  value: `` metric:  task:  conditions:   
  source: llmlingua.txt p.8 Sec. 5.5  
  quote: `The overall computation of our system is the sum of the prompt compression and the following inference`
- **LLv1-CR-1** (compression_ratio) Abstract headline: up to 20x compression with little performance loss over four datasets.  
  value: `20x` metric:  task: GSM8K, BBH, ShareGPT, Arxiv-March23 conditions: headline  
  source: llmlingua.txt p.1 Abstract  
  quote: `performance and allows for up to 20x compression with little performance loss`
- **LLv1-CR-2** (compression_ratio) Conclusion restates up to 20x with only a 1.5 point drop (this is the GSM8K quarter-shot result; BBH drops more).  
  value: `20x; 1.5 point` metric: EM points task: GSM8K conditions: headline  
  source: llmlingua.txt p.9 Conclusion  
  quote: `with up to 20x compression with only a 1.5 point performance drop`
- **LLv1-HW-1** (hardware) All experiments ran on a single Tesla V100 (32GB).  
  value: `Tesla V100 (32GB)` metric:  task:  conditions:   
  source: llmlingua.txt p.12 Appendix A.2  
  quote: `All experiments were conducted using a Tesla V100 (32GB)`
- **LLv1-IO-1** (io) Authors compress without any gradient flow through the target LLM, to support a larger range of LLMs (text-in, text-out, no model internals of the target needed).  
  value: `` metric:  task:  conditions:   
  source: llmlingua.txt p.1 Sec. 1  
  quote: `we follow this line of studies to compress a long prompt into a shorter one without any gradient flow through the LLMs to support applications based on a larger range of LLMs`
- **LLv1-IO-2** (io) Conclusion says the method is based on the small LM's perplexity for black-box LLMs.  
  value: `` metric:  task:  conditions:   
  source: llmlingua.txt p.9 Conclusion  
  quote: `which is based on the small LM's PPL for black-box LLMs`
- **LLv1-IO-3** (io) Target LLMs are the GPT-3.5-Turbo-0301 and Claude-v1.3 API models, accessed via OpenAI and Claude API.  
  value: `` metric:  task:  conditions: target LLMs  
  source: llmlingua.txt p.5 Sec. 5.1 Implementation Details  
  quote: `we employ the GPT-3.5-Turbo-0301 and the Claude-v1.3 as the target LLMs, which can be accessed via`
- **LLv1-IO-4** (io) Motivation: parameter-modifying approaches (quantization etc.) are unsuitable when LLMs are API-only; prompt-level compression is the paper's answer.  
  value: `` metric:  task:  conditions:   
  source: llmlingua.txt p.1 Sec. 1  
  quote: `these approaches may be not suitable when the LLMs can be accessed via APIs only`
- **LLv1-IO-5** (io) Figure 1 shows the output as plain (heavily garbled) compressed text: the example prompt goes from 2366 tokens to 117 tokens.  
  value: `2366 tokens; 117 tokens` metric:  task: GSM8K example conditions: Figure 1 illustration  
  source: llmlingua.txt p.3 Figure 1  
  quote: `Black-box LLMs 2366 tokens : Sam bought a dozen boxes each 30 highl pens inside, $10 each.`
- **LLv1-IO-6** (io) Same Figure 1 example, compressed length.  
  value: `117 tokens` metric:  task: GSM8K example conditions: Figure 1 illustration  
  source: llmlingua.txt p.3 Figure 1  
  quote: `The answer is 115 117 tokens`
- **LLv1-IO-7** (io) For the Claude experiments the authors reuse Alpaca-7B as the small LM, citing the difficulty of collecting alignment data; no Claude-specific alignment is described.  
  value: `` metric:  task: GSM8K conditions: Claude-v1.3  
  source: llmlingua.txt p.7 Sec. 5.5 Different Target LLMs  
  quote: `we employe Alpaca-7B as the small language model for the challenges in collecting alignment data`
- **LLv1-LAT-1** (latency_compute) Latency measured on a V100-32G GPU, compression rate 1x to 10x, GSM8K.  
  value: `` metric:  task: GSM8K conditions: V100-32G  
  source: llmlingua.txt p.8 Table 6 text  
  quote: `Table 6 shows the end-to-end latency of different systems on a V100-32G GPU with a compression rate from 1x to 10x`
- **LLv1-LAT-10** (latency_compute) Generation length also falls as compression ratio rises, adding savings on the output side.  
  value: `` metric:  task: GSM8K, BBH, ShareGPT, Arxiv conditions: Figure 2  
  source: llmlingua.txt p.8 Sec. 5.5  
  quote: `as the compression ratio increases, the text length produced by target LLMs tends to decrease`
- **LLv1-LAT-11** (latency_compute) Training cost reported only for GPT2-Alpaca: eight epochs, about 150 minutes (V100); Alpaca-7B alignment cost not reported.  
  value: `approximately 150 minutes` metric:  task:  conditions: GPT2-Alpaca; V100-32G  
  source: llmlingua.txt p.12 Appendix A.2  
  quote: `The training process took approximately 150 minutes to complete`
- **LLv1-LAT-12** (latency_compute) Segment size for iterative compression is 100 tokens; this sets granularity of repeated small-LM passes.  
  value: `100` metric: tokens task:  conditions:   
  source: llmlingua.txt p.5 Sec. 5.1  
  quote: `segment size used in the iterative token-level compression is set to 100`
- **LLv1-LAT-2** (latency_compute) Table 6 header: columns are compression ratios 1x, 2x, 5x, 10x.  
  value: `` metric:  task: GSM8K conditions:   
  source: llmlingua.txt p.8 Table 6  
  quote: `1x 2x 5x 10x`
- **LLv1-LAT-3** (latency_compute) Table 6: end-to-end latency in seconds without compression (1x).  
  value: `8.6` metric: s task: GSM8K conditions: V100-32G; caption says Latency (s)  
  source: llmlingua.txt p.8 Table 6  
  quote: `End-to-End w/o LLMLingua 8.6 - - -`
- **LLv1-LAT-4** (latency_compute) Table 6: end-to-end latency with LLMLingua at 2x, 5x, 10x with speedups in parentheses.  
  value: `4.9 (1.7x); 2.3 (3.3x); 1.3 (5.7x)` metric: s task: GSM8K conditions: V100-32G  
  source: llmlingua.txt p.8 Table 6  
  quote: `End-to-End w/ LLMLingua - 4.9(1.7x) 2.3(3.3x) 1.3(5.7x)`
- **LLv1-LAT-5** (latency_compute) Table 6: compressor-only overhead in seconds at 2x, 5x, 10x.  
  value: `0.8; 0.3; 0.2` metric: s task: GSM8K conditions: V100-32G  
  source: llmlingua.txt p.8 Table 6  
  quote: `LLMLingua - 0.8 0.3 0.2`
- **LLv1-LAT-6** (latency_compute) Authors summarise the speedup range as 1.7x to 5.7x (not 1.6x).  
  value: `1.7x to 5.7x` metric: speedup task: GSM8K conditions: V100-32G  
  source: llmlingua.txt p.8 Sec. 5.5  
  quote: `has a relatively small computation overhead and can achieve a speedup ranging from 1.7x to 5.7x`
- **LLv1-LAT-7** (latency_compute) Table 6 caption fixes the unit (seconds) and the dataset (GSM8K).  
  value: `` metric: s task: GSM8K conditions:   
  source: llmlingua.txt p.8 Table 6  
  quote: `Table 6: Latency (s) comparison on GSM8K`
- **LLv1-LAT-8** (latency_compute) Compute saving is a model-based estimate assuming the small LM gets the same system optimizations as the LLM, not a measurement.  
  value: `` metric:  task:  conditions: modelled  
  source: llmlingua.txt p.8 Sec. 5.5  
  quote: `Assuming that the small LM has the same system optimizations as the LLMs`
- **LLv1-LAT-9** (latency_compute) Estimated about 4x compute saving at 5x compression with a small LM, per the paper's formula.  
  value: `4x` metric: compute task:  conditions: modelled, 5x  
  source: llmlingua.txt p.8 Sec. 5.5  
  quote: `we can achieve nearly 4x savings in computational resources when using the smaller LM with a prompt compression rate of 5x`
- **LLv1-LIM-1** (limitation) Official limitations section: notable drop at excessively high ratios (25x-30x on GSM8K).  
  value: `25x-30x` metric:  task: GSM8K conditions:   
  source: llmlingua.txt p.9 Limitations  
  quote: `we might observe a notable performance drop when trying to achieve excessively high compression ratios such as 25x-30x on GSM8K`
- **LLv1-LIM-2** (limitation) Upper limit of compression ratio varies with prompt length, task type, sentence count.  
  value: `` metric:  task:  conditions:   
  source: llmlingua.txt p.10 Limitations  
  quote: `The upper limit of the compression ratio for different prompts varies, depending on factors such as prompt length, task type, and the number of sentences involved`
- **LLv1-LIM-3** (limitation) Tokenizer mismatch between small LM and black-box LLM may underestimate the token length.  
  value: `` metric:  task:  conditions:   
  source: llmlingua.txt p.10 Limitations  
  quote: `there may be subtle differences between the tokenizers used by the small language model and the black-box LLM, which may result in an underestimation of the prompt's token length`
- **LLv1-LIM-4** (limitation) Compressed prompts are hard for humans to read; GPT-4 can recover meaning but GPT-3.5-Turbo struggles (compressed prompt is lossy, garbled text).  
  value: `` metric:  task:  conditions:   
  source: llmlingua.txt p.9 Sec. 5.5 Recovering  
  quote: `It is evident that LLMs can effectively comprehend the semantic information in the compressed prompts, even if it might be challenging for humans`
- **LLv1-LIM-5** (limitation) Footnote: GPT-3.5-Turbo struggles to reconstruct compressed prompts, GPT-4 can.  
  value: `` metric:  task:  conditions:   
  source: llmlingua.txt p.9 Footnote 9  
  quote: `GPT-3.5-Turbo struggles to reconstruct compressed prompts, while GPT-4 has demonstrated an ability to do so`
- **LLv1-LIM-6** (limitation) The Arxiv-March23 prompts are truncated to the first five sections of ten thousand characters each; no longer inputs were tested.  
  value: `10,000 characters` metric:  task: Arxiv-March23 conditions:   
  source: llmlingua.txt p.12 Appendix A.1  
  quote: `we take the first five sections of each article and truncate each section to 10,000 characters`
- **LLv1-LIM-7** (limitation) ShareGPT contains multilingual and coding conversations, but results are aggregate; no per-language or per-scenario breakdown is given.  
  value: `` metric:  task: ShareGPT conditions:   
  source: llmlingua.txt p.12 Appendix A.1  
  quote: `includes users sharing conversations with ChatGPT in different languages and in various scenarios (e.g., coding, chitchat, writing assistant, etc.)`
- **LLv1-LIM-8** (limitation) Statement that the method might merely offer a potential solution for longer contexts (speculative, untested).  
  value: `` metric:  task:  conditions:   
  source: llmlingua.txt p.9 Conclusion  
  quote: `offers a potential solution for accommodating longer contexts in LLMs`
- **LLv1-MECH-1** (mechanism) Abstract defines LLMLingua as a coarse-to-fine prompt compression method built around a budget controller.  
  value: `` metric:  task:  conditions:   
  source: llmlingua.txt p.1 Abstract  
  quote: `a coarse-to-fine prompt compression method that involves a budget controller to maintain semantic integrity`
- **LLv1-MECH-10** (mechanism) The paper fine-tunes GPT2-small on the Alpaca dataset to build the small-LM variant.  
  value: `` metric:  task:  conditions:   
  source: llmlingua.txt p.8 Sec. 5.5 Different Small LMs  
  quote: `we fine-tune the GPT2-small on the Alpaca dataset and use it as the small LM for our system`
- **LLv1-MECH-2** (mechanism) The three components are a budget controller, a token-level iterative compression algorithm, and an instruction-tuning based distribution alignment between language models.  
  value: `` metric:  task:  conditions:   
  source: llmlingua.txt p.1 Abstract  
  quote: `a token-level iterative compression algorithm to better model the interdependence between compressed contents, and an instruction tuning based method for distribution alignment between language models`
- **LLv1-MECH-3** (mechanism) Demonstration-level coarse compression uses a small LM (GPT-2 or LLaMA) to compute the perplexity of each demonstration; no trained keep/drop classifier, scorer is perplexity.  
  value: `` metric:  task:  conditions: small LM perplexity scorer  
  source: llmlingua.txt p.4 Sec. 4.1  
  quote: `we first employ a small language model M, such as GPT-2 or LLaMA, to compute the perplexity of each demonstration`
- **LLv1-MECH-4** (mechanism) Demonstrations are selected in descending order of perplexity until the token budget for demonstrations is exhausted.  
  value: `` metric:  task:  conditions:   
  source: llmlingua.txt p.4 Sec. 4.1  
  quote: `Then, we select demonstrations in descending order of their perplexity values`
- **LLv1-MECH-5** (mechanism) Fine-grained step keeps tokens whose perplexity exceeds a dynamically computed threshold, applied segment by segment (token pruning).  
  value: `` metric:  task:  conditions:   
  source: llmlingua.txt p.5 Sec. 4.2 Eq. 7  
  quote: `tokens in each s with the PPL greater than are retained in the compressed prompt`
- **LLv1-MECH-6** (mechanism) Distribution alignment instruction-tunes the small LM on data generated by the target LLM; this is the only training step.  
  value: `` metric:  task:  conditions:   
  source: llmlingua.txt p.5 Sec. 4.3  
  quote: `and use the data generated by the LLM to perform instruction tuning`
- **LLv1-MECH-7** (mechanism) Experiments use Alpaca-7B or GPT2-Alpaca (GPT2 fine-tuned on Alpaca) as the small compressor LM.  
  value: `` metric:  task:  conditions: compressor model  
  source: llmlingua.txt p.5 Sec. 5.1 Implementation Details  
  quote: `we utilize either Alpaca-7B4 or GPT2-Alpaca as the small pre-trained language model`
- **LLv1-MECH-8** (mechanism) The ablation without distribution alignment uses pre-trained LLaMA-7B directly as the small LM, so LLaMA-7B appears only in that ablation.  
  value: `` metric:  task: GSM8K conditions: ablation  
  source: llmlingua.txt p.7 Sec. 5.4  
  quote: `directly use the pre-trained LLaMA-7B as the small`
- **LLv1-MECH-9** (mechanism) The small-LM size is given only through a parameter-count ratio; 7 (billion, Alpaca-7B) over 175 (target LLM) is used for the FLOPs estimate. GPT2-small parameter count is not stated.  
  value: `7/175` metric:  task:  conditions: modelled estimate, not measured  
  source: llmlingua.txt p.8 Sec. 5.5 Overhead  
  quote: `7/175LLMs = 1/25LLMs`
- **LLv1-Q-1** (mechanism) Instruction and question are NOT kept verbatim: they are compressed with fixed light rates (instruction 0.85, question 0.9) while demonstrations absorb most of the budget.  
  value: `0.85; 0.9` metric: compression rate tau task:  conditions: all experiments  
  source: llmlingua.txt p.5 Sec. 5.1 Implementation Details  
  quote: `use the pre-defined compression rates ins = 0.85 and que = 0.9 for instructions and questions`
- **LLv1-Q-2** (mechanism) Rationale: instruction and question directly influence the generated result.  
  value: `` metric:  task:  conditions:   
  source: llmlingua.txt p.3 Sec. 4.1  
  quote: `the instruction and the question in a prompt have a direct influence on the generated results`
- **LLv1-Q-3** (mechanism) Budget controller gives smaller compression ratios to instructions and questions and less budget to demonstrations.  
  value: `` metric:  task:  conditions:   
  source: llmlingua.txt p.4 Sec. 4.1  
  quote: `smaller compression ratios) for instructions and questions, and less budget for demonstrations`
- **LLv1-REP-1** (reproducibility) Code release stated in paper.  
  value: `` metric:  task:  conditions:   
  source: llmlingua.txt p.1 Footnote 1  
  quote: `Our code is available at https://aka.ms/LLMLingua`
- **LLv1-REP-2** (reproducibility) Official repo LICENSE file is MIT (Microsoft).  
  value: `MIT` metric:  task:  conditions:   
  source: https://raw.githubusercontent.com/microsoft/LLMLingua/main/LICENSE LICENSE  
  quote: `MIT License Copyright (c) Microsoft Corporation.`
- **LLv1-REP-3** (reproducibility) Official repo README ships an installable package (pip install llmlingua); README names no Hugging Face checkpoint for LLMLingua v1 or LongLLMLingua (only for LLMLingua-2).  
  value: `` metric:  task:  conditions:   
  source: https://raw.githubusercontent.com/microsoft/LLMLingua/main/README.md README  
  quote: `To get started with LLMLingua, simply install it using pip:`
- **LLv1-REP-4** (reproducibility) Alpaca data is used for alignment; paper text does not say the aligned GPT2-Alpaca checkpoint is released (value: not reported).  
  value: `not reported` metric:  task:  conditions:   
  source: llmlingua.txt p.5 Sec. 5.1  
  quote: `The Alpaca dataset (Taori et al., 2023) is exclusively employed for aligning small language models with black-box LLMs, and is not utilized in the evaluation process`
- **LLv1-TASK-1** (tasks_tested) Dataset list: GSM8K and BBH are reasoning/ICL, ShareGPT conversation, Arxiv-March23 summarization.  
  value: `` metric:  task: reasoning/math; multi-turn chat; summarization conditions:   
  source: llmlingua.txt p.2 Sec. 1  
  quote: `GSM8K and BBH for reasoning and ICL, ShareGPT for conversation, and Arxiv-March23 for summarization`
- **LLv1-TASK-2** (tasks_tested) Multi-turn chat tested on ShareGPT: 575 samples.  
  value: `575` metric: samples task: ShareGPT conditions:   
  source: llmlingua.txt p.12 Appendix A.1  
  quote: `We use a dataset of 575 samples provided by Li (2023) as our test set`
- **LLv1-TASK-3** (tasks_tested) Summarization tested on Arxiv-March23: 500 items.  
  value: `500` metric: items task: Arxiv-March23 conditions:   
  source: llmlingua.txt p.12 Appendix A.1  
  quote: `We use 500 data items collected by Li (2023) as the test set`
- **LLv1-TASK-4** (tasks_tested) Coding: no code benchmark in the paper's dataset list.  
  value: `not tested in paper` metric:  task: coding conditions:   
  source: llmlingua.txt p.1 Abstract  
  quote: `four datasets from different scenarios, i.e., GSM8K, BBH, ShareGPT, and Arxiv-March23`
- **LLv1-TASK-5** (tasks_tested) Long-document QA / RAG: no QA or retrieval benchmark in the dataset list.  
  value: `not tested in paper` metric:  task: long-document QA/RAG conditions:   
  source: llmlingua.txt p.1 Abstract  
  quote: `four datasets from different scenarios, i.e., GSM8K, BBH, ShareGPT, and Arxiv-March23`
- **LLv1-TASK-6** (tasks_tested) Structured data (JSON/tables/logs): not in the dataset list.  
  value: `not tested in paper` metric:  task: structured data conditions:   
  source: llmlingua.txt p.1 Abstract  
  quote: `four datasets from different scenarios, i.e., GSM8K, BBH, ShareGPT, and Arxiv-March23`
- **LLv1-TASK-7** (tasks_tested) Sensitive/PII content: not in the dataset list.  
  value: `not tested in paper` metric:  task: sensitive/PII conditions:   
  source: llmlingua.txt p.1 Abstract  
  quote: `four datasets from different scenarios, i.e., GSM8K, BBH, ShareGPT, and Arxiv-March23`
- **LLv1-TASK-8** (tasks_tested) Reasoning/math: GSM8K and BBH tested (also the paper says it is the first to evaluate reasoning and ICL in efficient-LLM work).  
  value: `` metric:  task: GSM8K, BBH conditions:   
  source: llmlingua.txt p.1 Abstract  
  quote: `four datasets from different scenarios, i.e., GSM8K, BBH, ShareGPT, and Arxiv-March23`

## LLMLingua-2

- **L2-001** (mechanism) Compression is cast as binary token classification (preserve or discard) with a Transformer encoder, not as perplexity/self-information scoring.  
  value: `` metric:  task:  conditions: method design  
  source: llmlingua-2-2403.12968.txt p.5 Sec. 4  
  quote: `We formulate prompt compression as a binary token classification problem (i.e., preserve or discard)`
- **L2-002** (mechanism) At inference the compressor keeps the highest-probability words up to a target budget and preserves their original order (hard-text output made of original words).  
  value: `` metric:  task:  conditions: method design  
  source: llmlingua-2-2403.12968.txt p.6 Sec. 4.2  
  quote: `with the highest pi and maintain their original order`
- **L2-003** (mechanism) Two encoders are used: xlm-roberta-large (called LLMLingua-2) and multilingual-BERT (called LLMLingua-2-small).  
  value: `` metric:  task:  conditions: feature encoder f  
  source: llmlingua-2-2403.12968.txt p.6 Sec. 5 Implementation Details  
  quote: `We use xlm-roberta-large (Conneau et al., 2020) and multilingual-BERT (Devlin et al., 2019) for the feature encoder f`
- **L2-004** (mechanism) Size of the xlm-roberta-large compressor encoder.  
  value: `355M parameters` metric:  task:  conditions: LLMLingua-2 (xlm-roberta-large)  
  source: llmlingua-2-2403.12968.txt p.14 Appendix H  
  quote: `We use xlm-roberta-large which has 355M parameters as the feature encoder f in LLMLingua-2`
- **L2-005** (latency_compute) Size and training time of the multilingual-BERT (small) compressor.  
  value: `110M parameters; roughly 16 hours` metric:  task:  conditions: LLMLingua-2-small (multilingual-BERT); training hardware not stated  
  source: llmlingua-2-2403.12968.txt p.14 Appendix H  
  quote: `which has 110M parameters. It takes roughly 16 hours to train the multilingual-BERT model.`
- **L2-006** (latency_compute) Training time of the xlm-roberta-large compressor on the MeetingBank compression dataset.  
  value: `approximately 23 hours` metric:  task:  conditions: LLMLingua-2 (xlm-roberta-large); training GPU type not stated  
  source: llmlingua-2-2403.12968.txt p.14 Appendix H  
  quote: `The training process takes approximately 23 hours on our MeetingBank compression dataset.`
- **L2-007** (mechanism) Fine-tuning recipe for both compressors.  
  value: `10 epochs; lr 1e-5; batch size 10` metric:  task:  conditions: Adam optimizer  
  source: llmlingua-2-2403.12968.txt p.6 Sec. 5 Implementation Details  
  quote: `using the Adam optimizer (Kingma and Ba, 2015) with a learning rate of 1e-5 and a batch size of 10`
- **L2-008** (mechanism) Training labels come from distilling GPT-4 compressions of MeetingBank transcripts (teacher = GPT-4).  
  value: `` metric:  task: MeetingBank conditions: data distillation  
  source: llmlingua-2-2403.12968.txt p.2 Sec. 1 Contributions  
  quote: `We propose a data distillation procedure to derive knowledge from an LLM (GPT-4) to compress the prompts without losing crucial information.`
- **L2-009** (mechanism) The method is explicitly task-agnostic (question-agnostic).  
  value: `` metric:  task:  conditions: design goal  
  source: llmlingua-2-2403.12968.txt p.1 Abstract  
  quote: `This paper focuses on task-agnostic prompt compression for better generalizability and efficiency.`
- **L2-010** (mechanism) Compression ratio is defined over words: tau is compressed words divided by original words and the ratio reported is 1/tau; table 'Tokens' columns count target-LLM tokens.  
  value: `` metric:  task:  conditions: definition  
  source: llmlingua-2-2403.12968.txt p.6 Sec. 4.2  
  quote: `as the quotient of the number of words in the compressed prompt and the number of words in the original prompt`
- **L2-011** (mechanism) Multi-token words are kept intact and a word's score is the average over its subword tokens, to make the compressor usable across different LLM and SLM tokenizers.  
  value: `` metric:  task:  conditions: footnote 2  
  source: llmlingua-2-2403.12968.txt p.6 Sec. 4.2 footnote 2  
  quote: `we preserve the integrity of multi-token words and represent the probability of a word by averaging over the predicted probabilities of all subword tokens`
- **L2-012** (mechanism) The GPT-4 distillation instruction allows only word deletion (no rewording, reordering or additions).  
  value: `` metric:  task:  conditions: distillation prompt  
  source: llmlingua-2-2403.12968.txt p.4 Fig. 2  
  quote: `1. You can ONLY remove unimportant words.`
- **L2-013** (limitation) In data distillation, contexts are split into chunks of at most 512 tokens ending with a period before GPT-4 compresses each chunk; the paper states this as the chunk limit for building the training data, not as an inference-time limit of the compressor.  
  value: `512 tokens` metric:  task: MeetingBank distillation conditions: GPT-4-32k distillation  
  source: llmlingua-2-2403.12968.txt p.4 Sec. 3.1 Chunk-Wise Compression  
  quote: `no more than 512 tokens and ending with a period`
- **L2-014** (mechanism) Training-set statistics of the MeetingBank compression dataset (compressed row; header columns: Data Size, Chunk, Sentence Avg, Token Avg, 1/tau).  
  value: `Data Size 5,169; 41,746 chunks; 132 sentences avg; 1,415 tokens avg; 2.57x` metric:  task: MeetingBank compression dataset conditions: GPT-4-32k compressed  
  source: llmlingua-2-2403.12968.txt p.11 Table 8  
  quote: `Compressed 5,169 41,746 132 1,415 2.57x`
- **L2-014b** (mechanism) Training-set statistics, original (uncompressed) row of Table 8: average tokens per transcript before compression.  
  value: `Data Size 5,169; 41,746 chunks; 232 sentences avg; 3,635 tokens avg` metric:  task: MeetingBank compression dataset conditions: original transcripts  
  source: llmlingua-2-2403.12968.txt p.11 Table 8  
  quote: `Original 5,169 41,746 232 3,635 -`
- **L2-015** (mechanism) GPT-4 compresses very long contexts too aggressively, which motivated chunk-wise distillation (Table 7 ablation rows below).  
  value: `` metric:  task:  conditions: Fig. 4 discussion  
  source: llmlingua-2-2403.12968.txt p.4 Sec. 3.1  
  quote: `GPT-4 tends to apply a high compression ratio when processing very long context`
- **L2-016** (mechanism) Ablation row: GPT-4 compression with the paper's instruction but WITHOUT chunking (columns: 1/tau, variation rate, QA F1; arrow glyphs lost in extraction). Rows describe distillation settings; the table does not state whether numbers come from GPT-4-compressed text or the trained compressor.  
  value: `21x; VR 6.0; QA F1 27.9` metric: QA F1 task: LongBench Single Document QA conditions: ablation, chunk-wise compression  
  source: llmlingua-2-2403.12968.txt p.9 Table 7  
  quote: `LLMLingua-2 w/o Chunk 21x 6.0 27.9`
- **L2-017** (mechanism) Ablation row: the paper's instruction WITH chunk-wise compression (same columns; same caveat on what the row measures).  
  value: `2.6x; VR 2.2; QA F1 36.7` metric: QA F1 task: LongBench Single Document QA conditions: ablation, chunk-wise compression  
  source: llmlingua-2-2403.12968.txt p.9 Table 7  
  quote: `LLMLingua-2 2.6x 2.2 36.7`
- **L2-018** (mechanism) Ablation row for an alternative instruction from LLMLingua (Instruction1): shows the 123x figure in Table 7 belongs to a rejected distillation instruction, not to LLMLingua-2.  
  value: `123x; VR 13.7; QA F1 19.1` metric: QA F1 task: LongBench Single Document QA conditions: ablation, instruction design  
  source: llmlingua-2-2403.12968.txt p.9 Table 7  
  quote: `Instruction1 123x 13.7 19.1`
- **L2-020** (io) Paper positions KV-cache compression as not easily applicable to black-box LLMs, implying its own hard-text output is meant to work with them (the paper's statement concerns KV-cache methods; the black-box fit of LLMLingua-2 is inferred from mechanism).  
  value: `` metric:  task:  conditions: text-in / text-out  
  source: llmlingua-2-2403.12968.txt p.3 Sec. 2  
  quote: `cannot be easily applied to black-box LLMs.`
- **L2-021** (io) Compressed prompts were tested on an API model (GPT-3.5-Turbo) and an open model (Mistral-7B), without any change to the target LLM.  
  value: `` metric:  task:  conditions: target LLMs  
  source: llmlingua-2-2403.12968.txt p.2 Sec. 1 Contributions  
  quote: `robust generalization ability from GPT-3.5-Turbo to Mistral-7B`
- **L2-022** (io) Default target LLM for downstream tasks is GPT-3.5-Turbo (snapshot named in footnote 3), greedy decoding.  
  value: `` metric:  task:  conditions: evaluation setup  
  source: llmlingua-2-2403.12968.txt p.6 Sec. 5 Implementation Details  
  quote: `as the target LLM for downstream tasks, with greedy decoding at a temperature of 0`
- **L2-023** (io) Second target LLM is Mistral-7B (open model), reported in Table 4 and Table 13.  
  value: `` metric:  task: MeetingBank, LongBench single doc QA conditions: Mistral-7B target  
  source: llmlingua-2-2403.12968.txt p.8 Table 4 caption  
  quote: `Table 4: Evaluation with Mistral-7B as the Target LLM on MeetingBank and LongBench single doc QA task.`
- **L2-024** (io) RAG motivation: question-aware compression forces re-compressing the same documents per query; a task-agnostic compressor avoids that.  
  value: `` metric:  task:  conditions: motivation  
  source: llmlingua-2-2403.12968.txt p.1 Sec. 1  
  quote: `it may become necessary to compress the same documents multiple times depending on the associated queries with task-aware prompt compression`
- **L2-030** (compression_ratio) Abstract states end-to-end latency speedup range for compression ratios of 2x to 5x.  
  value: `1.6x-2.9x speedup at 2x-5x` metric:  task: MeetingBank latency (Table 5) conditions: V100-32G; target LLM for latency not stated  
  source: llmlingua-2-2403.12968.txt p.1 Abstract  
  quote: `accelerating the end-to-end latency by 1.6x-2.9x with compression ratios of 2x-5x`
- **L2-031** (compression_ratio) Paper says the method can be integrated into LLMLingua's coarse-to-fine framework for a higher ratio of 15x on multi-demonstration/multi-document tasks; this is a stated possibility with no dedicated results table (Appendix K reports 3.9x on NaturalQuestions).  
  value: `15x` metric:  task: multi-demonstration or multi-document tasks conditions: integration with LLMLingua budget controller  
  source: llmlingua-2-2403.12968.txt p.6 Sec. 4.2  
  quote: `for a higher compression ratio of 15x for tasks`
- **L2-032** (compression_ratio) LLMLingua-2 row of Table 3 for GSM8K. Columns (verified from header rows): GSM8K 1-shot constraint [EM, Tokens, 1/tau], GSM8K half-shot constraint [EM, Tokens, 1/tau], BBH 1-shot [EM, Tokens, 1/tau], BBH half-shot [EM, Tokens, 1/tau]. GSM8K: EM 79.08 at 5x and 77.79 at 14x.  
  value: `79.08 (457 tok, 5x); 77.79 (178 tok, 14x)` metric: EM task: GSM8K conditions: LLMLingua-2 (xlm-roberta-large); target LLM GPT-3.5-Turbo (default per p.6), greedy decoding, temperature 0; task-agnostic (question-agnostic) compression  
  source: llmlingua-2-2403.12968.txt p.7 Table 3  
  quote: `LLMLingua-2 79.08 457 5x 77.79 178 14x 70.02 269 3x 61.94 176 5x`
- **L2-033** (compression_ratio) Same Table 3 row read for BBH: EM 70.02 at 3x (1-shot constraint) and 61.94 at 5x (half-shot constraint).  
  value: `70.02 (269 tok, 3x); 61.94 (176 tok, 5x)` metric: EM task: BBH conditions: LLMLingua-2 (xlm-roberta-large); target LLM GPT-3.5-Turbo (default per p.6), greedy decoding, temperature 0; task-agnostic (question-agnostic) compression  
  source: llmlingua-2-2403.12968.txt p.7 Table 3  
  quote: `LLMLingua-2 79.08 457 5x 77.79 178 14x 70.02 269 3x 61.94 176 5x`
- **L2-034** (compression_ratio) Table 2, 2,000-token constraint, LLMLingua-2 row. Columns from header: LongBench [SingleDoc, MultiDoc, Summ., FewShot, Synth., Code, AVG, Tokens, 1/tau], then ZeroSCROLLS [AVG, Tokens, 1/tau]. Metric per task is 'as in LongLLMLingua' (not named in this paper).  
  value: `SingleDoc 29.8; MultiDoc 33.1; Summ. 25.3; FewShot 66.4; Synth. 21.3; Code 58.9; LB AVG 39.1; 1,954 tok 5x; ZeroSCROLLS AVG 33.4; 1,898 tok 5x` metric: task metrics as in LongLLMLingua task: LongBench; ZeroSCROLLS conditions: LLMLingua-2 (xlm-roberta-large); 2,000-token constraint; target LLM GPT-3.5-Turbo (default per p.6), greedy decoding, temperature 0; task-agnostic (question-agnostic) compression  
  source: llmlingua-2-2403.12968.txt p.7 Table 2  
  quote: `LLMLingua-2 29.8 33.1 25.3 66.4 21.3 58.9 39.1 1,954 5x 33.4 1,898 5x`
- **L2-035** (compression_ratio) Table 2, 3,000-token constraint, LLMLingua-2 row (same columns as L2-034).  
  value: `SingleDoc 35.5; MultiDoc 38.7; Summ. 26.3; FewShot 69.6; Synth. 21.4; Code 62.8; LB AVG 42.4; 3,392 tok 3x; ZeroSCROLLS AVG 33.5; 3,206 tok 3x` metric: task metrics as in LongLLMLingua task: LongBench; ZeroSCROLLS conditions: LLMLingua-2 (xlm-roberta-large); 3,000-token constraint; target LLM GPT-3.5-Turbo (default per p.6), greedy decoding, temperature 0; task-agnostic (question-agnostic) compression  
  source: llmlingua-2-2403.12968.txt p.7 Table 2  
  quote: `LLMLingua-2 35.5 38.7 26.3 69.6 21.4 62.8 42.4 3,392 3x 33.5 3,206 3x`
- **L2-036** (compression_ratio) Authors say robustness to increasing compression ratio was checked on a 100-sample MeetingBank subset; the plot (Fig. 15, ratios 1x-10x) gives no extractable numbers.  
  value: `` metric:  task: MeetingBank 100-sample subset conditions: ratios 1.0-10.0 on the figure axis; figure only  
  source: llmlingua-2-2403.12968.txt p.15 Appendix M  
  quote: `LLMLingua-2 exhibits superior robustness compared to other baselines as the compression ratio increases`
- **L2-037** (compression_ratio) Table 12 fixed-ratio (FR) row: a fixed per-sample ratio of 7x (left block) and 5x (right block) on LongBench single-doc QA. Columns: QA Score, Tokens, 1/tau per block.  
  value: `25.1 (2,131 tok, 6.8x); 27.4 (3,185 tok, 4.5x)` metric: QA Score task: LongBench SingleDoc conditions: LLMLingua-2 FR; ratio constraint 7x / 5x  
  source: llmlingua-2-2403.12968.txt p.18 Table 12  
  quote: `LLMLingua-2 FR 25.1 2,131 6.8x 27.4 3,185 4.5x`
- **L2-038** (compression_ratio) Table 12 dynamic-compression-ratio (DCR) row: per-sample ratio chosen by a probability threshold under the same overall constraint.  
  value: `29.5 (2,125 tok, 6.8x); 32.2 (3,164 tok, 4.5x)` metric: QA Score task: LongBench SingleDoc conditions: LLMLingua-2 DCR; ratio constraint 7x / 5x  
  source: llmlingua-2-2403.12968.txt p.18 Table 12  
  quote: `LLMLingua-2 DCR 29.5 2,125 6.8x 32.2 3,164 4.5x`
- **L2-039** (compression_ratio) Table 12 target-token-constraint row for comparison (2,000 and 3,000 tokens).  
  value: `29.8 (1,954 tok, 7.4x); 35.5 (3,392 tok, 4.3x)` metric: QA Score task: LongBench SingleDoc conditions: LLMLingua-2; target token constraint  
  source: llmlingua-2-2403.12968.txt p.18 Table 12  
  quote: `LLMLingua-2 29.8 1,954 7.4x 35.5 3,392 4.3x`
- **L2-040** (context_loss) Table 1 LLMLingua-2 (xlm-roberta-large) row. Columns from the two header rows: QA = EM; Summary = BLEU, Rouge1, Rouge2, RougeL, BERTScore; Length = Tokens, 1/tau.  
  value: `EM 86.92; BLEU 17.37; Rouge1 48.64; Rouge2 22.96; RougeL 34.24; BERTScore 88.27; 970 tok; 3.1x` metric: EM; BLEU/ROUGE/BERTScore task: MeetingBank (in-domain) QA and summary conditions: LLMLingua-2; target LLM GPT-3.5-Turbo (default per p.6), greedy decoding, temperature 0; task-agnostic (question-agnostic) compression  
  source: llmlingua-2-2403.12968.txt p.6 Table 1  
  quote: `LLMLingua-2 86.92 17.37 48.64 22.96 34.24 88.27 970 3.1x`
- **L2-041** (context_loss) Table 1 LLMLingua-2-small (mBERT) row, same columns as L2-040.  
  value: `EM 85.82; BLEU 17.41; Rouge1 48.33; Rouge2 23.07; RougeL 34.36; BERTScore 88.77; 984 tok; 3.0x` metric: EM; BLEU/ROUGE/BERTScore task: MeetingBank (in-domain) conditions: LLMLingua-2-small; target LLM GPT-3.5-Turbo (default per p.6), greedy decoding, temperature 0; task-agnostic (question-agnostic) compression  
  source: llmlingua-2-2403.12968.txt p.6 Table 1  
  quote: `LLMLingua-2-small 85.82 17.41 48.33 23.07 34.36 88.77 984 3.0x`
- **L2-042** (context_loss) Table 1 Original (uncompressed) row, same columns as L2-040: the baseline for L2-040/041.  
  value: `EM 87.75; BLEU 22.34; Rouge1 47.28; Rouge2 26.66; RougeL 35.15; BERTScore 88.96; 3,003 tok; 1.0x` metric: EM; BLEU/ROUGE/BERTScore task: MeetingBank (in-domain) conditions: uncompressed prompt; target LLM GPT-3.5-Turbo (default per p.6), greedy decoding, temperature 0; task-agnostic (question-agnostic) compression  
  source: llmlingua-2-2403.12968.txt p.6 Table 1  
  quote: `Original 87.75 22.34 47.28 26.66 35.15 88.96 3,003 1.0x`
- **L2-043** (context_loss) Table 2 Original Prompt row (uncompressed baseline), same columns as L2-034.  
  value: `SingleDoc 39.7; MultiDoc 38.7; Summ. 26.5; FewShot 67.0; Synth. 37.8; Code 54.2; LB AVG 44.0; 10,295 tok; ZeroSCROLLS AVG 34.7; 9,788 tok` metric: task metrics as in LongLLMLingua task: LongBench; ZeroSCROLLS conditions: uncompressed; target LLM GPT-3.5-Turbo (default per p.6), greedy decoding, temperature 0; task-agnostic (question-agnostic) compression  
  source: llmlingua-2-2403.12968.txt p.7 Table 2  
  quote: `Original Prompt 39.7 38.7 26.5 67.0 37.8 54.2 44.0 10,295 - 34.7 9,788 -`
- **L2-044** (context_loss) Table 2 Zero-Shot row (no context at all), same columns as L2-034; useful floor for judging compressed results.  
  value: `SingleDoc 15.6; MultiDoc 31.3; Summ. 15.6; FewShot 40.7; Synth. 1.6; Code 36.2; LB AVG 23.5; 214 tok; ZeroSCROLLS AVG 10.8; 32 tok` metric: task metrics as in LongLLMLingua task: LongBench; ZeroSCROLLS conditions: zero-shot (no context); target LLM GPT-3.5-Turbo (default per p.6), greedy decoding, temperature 0; task-agnostic (question-agnostic) compression  
  source: llmlingua-2-2403.12968.txt p.7 Table 2  
  quote: `Zero-Shot 15.6 31.3 15.6 40.7 1.6 36.2 23.5 214 48x 10.8 32 306x`
- **L2-045** (context_loss) Table 2 LLMLingua-2-small row, 2,000-token constraint (same columns as L2-034).  
  value: `SingleDoc 29.5; MultiDoc 32.0; Summ. 24.5; FewShot 64.8; Synth. 22.3; Code 56.2; LB AVG 38.2; 1,891 tok 5x; ZeroSCROLLS AVG 33.3` metric: task metrics as in LongLLMLingua task: LongBench; ZeroSCROLLS conditions: LLMLingua-2-small; 2,000-token constraint; target LLM GPT-3.5-Turbo (default per p.6), greedy decoding, temperature 0; task-agnostic (question-agnostic) compression  
  source: llmlingua-2-2403.12968.txt p.7 Table 2  
  quote: `LLMLingua-2-small 29.5 32.0 24.5 64.8 22.3 56.2 38.2 1,891 5x 33.3 1,862 5x`
- **L2-046** (context_loss) Table 2 LLMLingua-2-small row, 3,000-token constraint (same columns as L2-034).  
  value: `SingleDoc 35.5; MultiDoc 38.1; Summ. 26.2; FewShot 67.5; Synth. 23.9; Code 60.0; LB AVG 41.9; 3,278 tok 3x; ZeroSCROLLS AVG 33.4` metric: task metrics as in LongLLMLingua task: LongBench; ZeroSCROLLS conditions: LLMLingua-2-small; 3,000-token constraint; target LLM GPT-3.5-Turbo (default per p.6), greedy decoding, temperature 0; task-agnostic (question-agnostic) compression  
  source: llmlingua-2-2403.12968.txt p.7 Table 2  
  quote: `LLMLingua-2-small 35.5 38.1 26.2 67.5 23.9 60.0 41.9 3,278 3x 33.4 3,089 3x`
- **L2-047** (context_loss) Authors' reading of LongBench/GSM8K/BBH results: even the small model is comparable to, and sometimes slightly above, the original prompt (see rows for per-task detail).  
  value: `` metric:  task: LongBench; ZeroSCROLLS; GSM8K; BBH conditions: authors' summary  
  source: llmlingua-2-2403.12968.txt p.8 Sec. 5 Results on Out-of-Domain Benchmarks  
  quote: `able to achieve comparable, and in some cases, even slightly higher performance than the original prompt`
- **L2-048** (context_loss) Authors concede the task-agnostic compressor falls short of question-aware LongLLMLingua on LongBench, attributing the gap to question information.  
  value: `` metric:  task: LongBench conditions: task-agnostic vs task-aware  
  source: llmlingua-2-2403.12968.txt p.8 Sec. 5 Results on Out-of-Domain Benchmarks  
  quote: `(Jiang et al., 2023a) on Longbench. We attribute this performance gap to the additional information that they leverage from the question.`
- **L2-049** (context_loss) Table 3 Full-Shot row: uncompressed baseline for GSM8K and BBH (same column layout as L2-032).  
  value: `GSM8K EM 78.85 (2,366 tok); BBH EM 70.07 (774 tok)` metric: EM task: GSM8K; BBH conditions: full-shot prompt; target LLM GPT-3.5-Turbo (default per p.6), greedy decoding, temperature 0; task-agnostic (question-agnostic) compression  
  source: llmlingua-2-2403.12968.txt p.7 Table 3  
  quote: `Full-Shot 78.85 2,366 - 78.85 2,366 - 70.07 774 - 70.07 774 -`
- **L2-050** (context_loss) Table 3 Zero-Shot row: floor with no demonstrations (same column layout as L2-032).  
  value: `GSM8K EM 48.75 (11 tok); BBH EM 32.32 (16 tok)` metric: EM task: GSM8K; BBH conditions: zero-shot; target LLM GPT-3.5-Turbo (default per p.6), greedy decoding, temperature 0; task-agnostic (question-agnostic) compression  
  source: llmlingua-2-2403.12968.txt p.7 Table 3  
  quote: `Zero-Shot 48.75 11 215x 48.75 11 215x 32.32 16 48x 32.32 16 48x`
- **L2-051** (context_loss) Table 4 (Mistral-7B target) LLMLingua-2 row. Columns from header: MeetingBank [QA, Summ., Tokens, 1/tau], LongBench-SingleDoc 2,000-token constraint [score, Tokens, 1/tau], 3,000-token constraint [score, Tokens, 1/tau]. Summary = Rouge1 per caption; QA metric not named in caption.  
  value: `MB QA 76.22; MB Summ. 30.18 (970 tok, 3.0x); LB SingleDoc 26.8 (1,967 tok, 7.4x); 27.3 (2,853 tok, 5.1x)` metric: QA (metric not named); Rouge1; LongBench score task: MeetingBank; LongBench SingleDoc conditions: LLMLingua-2; target LLM Mistral-7B  
  source: llmlingua-2-2403.12968.txt p.8 Table 4  
  quote: `LLMLingua-2 76.22 30.18 970 3.0x 26.8 1,967 7.4x 27.3 2,853 5.1x`
- **L2-052** (context_loss) Table 4 Original Prompt row for Mistral-7B (baseline for L2-051; LongBench originals average 14,511 tokens).  
  value: `MB QA 66.95; MB Summ. 26.26 (3,003 tok); LB SingleDoc 24.5 (14,511 tok)` metric: QA (metric not named); Rouge1; LongBench score task: MeetingBank; LongBench SingleDoc conditions: uncompressed; target LLM Mistral-7B  
  source: llmlingua-2-2403.12968.txt p.8 Table 4  
  quote: `Original Prompt 66.95 26.26 3,003 - 24.5 14,511 - 24.5 14,511 -`
- **L2-053** (context_loss) Authors speculate Mistral-7B copes worse with long contexts than GPT-3.5-Turbo, which is why compressed prompts can beat the original.  
  value: `` metric:  task: LongBench; MeetingBank conditions: Mistral-7B target  
  source: llmlingua-2-2403.12968.txt p.8 Sec. 5 Mistral-7B as the Target LLM  
  quote: `speculate that Mistral-7B might be less adept at managing long contexts than GPT-3.5-Turbo.`
- **L2-054** (context_loss) Table 13 (Mistral-7B, only samples with original prompt under 8K tokens): LLMLingua-2 row; same columns as L2-051; ratios here are only about 1.6x-2.6x.  
  value: `MB QA 81.75; MB Summ. 30.83 (651 tok, 2.6x); LB SingleDoc 35.0 (1,889 tok, 2.4x); 36.3 (2,841 tok, 1.6x)` metric: QA (metric not named); Rouge1; LongBench score task: MeetingBank; LongBench SingleDoc (<8K subset) conditions: LLMLingua-2; target LLM Mistral-7B  
  source: llmlingua-2-2403.12968.txt p.19 Table 13  
  quote: `LLMLingua-2 81.75 30.83 651 2.6x 35.0 1,889 2.4x 36.3 2,841 1.6x`
- **L2-055** (context_loss) Table 13 Original Prompt row (baseline for L2-054).  
  value: `MB QA 71.27; MB Summ. 27.56 (1,700 tok); LB SingleDoc 31.4 (4,595 tok)` metric: QA (metric not named); Rouge1; LongBench score task: MeetingBank; LongBench SingleDoc (<8K subset) conditions: uncompressed; target LLM Mistral-7B  
  source: llmlingua-2-2403.12968.txt p.19 Table 13  
  quote: `Original Prompt 71.27 27.56 1,700 - 31.4 4,595 - 31.4 4,595 -`
- **L2-056** (context_loss) Table 9: GPT-4 itself used as the compressor (same instruction and 512 chunking) scores lower QA EM than the trained LLMLingua-2 at a similar ratio. Columns: QA EM, Tokens, 1/tau.  
  value: `EM 84.86 (1,221 tok, 2.5x)` metric: EM task: MeetingBank QA conditions: GPT-4 compression; target LLM GPT-3.5-Turbo (default per p.6), greedy decoding, temperature 0; task-agnostic (question-agnostic) compression  
  source: llmlingua-2-2403.12968.txt p.16 Table 9  
  quote: `GPT-4 Compression 84.86 1,221 2.5x`
- **L2-057** (context_loss) Table 10 LLMLingua-2 row on LongBench-Zh. Columns from header: SingleDoc, MultiDoc, Summ., FewShot, Synth., AVG, Tokens, 1/tau (no Code column). Target LLM not restated (default GPT-3.5-Turbo assumed per p.6 'unless specified otherwise').  
  value: `SingleDoc 46.7; MultiDoc 23.0; Summ. 15.3; FewShot 32.8; Synth. 72.6; AVG 38.1; 3,023 tok; 5x` metric: task metrics as in LongLLMLingua (not named) task: LongBench-Zh (Chinese) conditions: LLMLingua-2; task-agnostic; 5x  
  source: llmlingua-2-2403.12968.txt p.17 Table 10  
  quote: `LLMLingua-2 46.7 23.0 15.3 32.8 72.6 38.1 3,023 5x`
- **L2-058** (context_loss) Table 10 Original Prompt row on LongBench-Zh (baseline for L2-057).  
  value: `SingleDoc 61.2; MultiDoc 28.7; Summ. 16.0; FewShot 29.2; Synth. 77.5; AVG 42.5; 14,940 tok` metric: task metrics as in LongLLMLingua (not named) task: LongBench-Zh (Chinese) conditions: uncompressed  
  source: llmlingua-2-2403.12968.txt p.17 Table 10  
  quote: `Original Prompt 61.2 28.7 16.0 29.2 77.5 42.5 14,940 -`
- **L2-059** (context_loss) Table 11 (NaturalQuestions, 20 documents, 4x constraint) question-AGNOSTIC LLMLingua-2 row. Columns: 1st, 5th, 10th, 15th, 20th, Reorder, Tokens, 1/tau; 1st-20th are presumably the position of the answer-bearing document (inferred from the Liu et al. 2024 benchmark; caption does not define them). The metric is not named in the table or caption.  
  value: `1st 48.6; 5th 44.5; 10th 43.6; 15th 40.9; 20th 39.9; Reorder 46.2; 748 tok; 3.9x` metric: not named (accuracy-type score) task: NaturalQuestions 20-document (Liu et al. 2024) conditions: LLMLingua-2 question-agnostic; 4x constraint; target LLM not restated  
  source: llmlingua-2-2403.12968.txt p.18 Table 11  
  quote: `LLMLingua-2 48.6 44.5 43.6 40.9 39.9 46.2 748 3.9x`
- **L2-060** (context_loss) Table 11 Original Prompt row (uncompressed; same columns as L2-059).  
  value: `1st 75.7; 5th 57.3; 10th 54.1; 15th 55.4; 20th 63.1; 2,946 tok` metric: not named task: NaturalQuestions 20-document conditions: uncompressed  
  source: llmlingua-2-2403.12968.txt p.18 Table 11  
  quote: `Original Prompt 75.7 57.3 54.1 55.4 63.1 - 2,946 -`
- **L2-061** (context_loss) Table 11 Zero-shot row: a single score (no documents) printed once, so it presumably applies to every position column; ambiguous. It is higher than every question-agnostic LLMLingua-2 cell in the same table.  
  value: `56.1 (15 tok, 196x)` metric: not named task: NaturalQuestions 20-document conditions: zero-shot (no documents)  
  source: llmlingua-2-2403.12968.txt p.18 Table 11  
  quote: `Zero-shot 56.1 15 196x`
- **L2-062** (context_loss) Table 11 LLMLingua-2+ row: LLMLingua-2 combined with LongLLMLingua question-aware coarse-level compression (same columns as L2-059).  
  value: `1st 74.0; 5th 70.4; 10th 67.0; 15th 66.9; 20th 65.3; Reorder 71.9; 739 tok; 3.9x` metric: not named task: NaturalQuestions 20-document conditions: question-AWARE hybrid; 4x constraint  
  source: llmlingua-2-2403.12968.txt p.18 Table 11  
  quote: `LLMLingua-2+ 74.0 70.4 67.0 66.9 65.3 71.9 739 3.9x`
- **L2-063** (context_loss) Appendix K: authors report the hybrid beats plain LLMLingua-2 on NaturalQuestions on average.  
  value: `25.3% average gain` metric:  task: NaturalQuestions 20-document conditions: LLMLingua-2+ vs LLMLingua-2  
  source: llmlingua-2-2403.12968.txt p.15 Appendix K  
  quote: `achieves an average performance gain of 25.3% on NaturalQuestions`
- **L2-064** (context_loss) Table 6 second LLMLingua-2 row (compressor trained on MeetingBank data expanded with 50k TriviaQA-wiki examples per caption; the marker distinguishing the row is lost in extraction, so the mapping to the expanded model is inferred from the caption). Columns as L2-034.  
  value: `SingleDoc 30.7; MultiDoc 33.9; Summ. 25.4; FewShot 66.6; Synth. 22.6; Code 58.1; LB AVG 39.5; 1,853 tok 5x; ZeroSCROLLS AVG 33.4` metric: task metrics as in LongLLMLingua task: LongBench; ZeroSCROLLS conditions: 2,000-token constraint; target LLM GPT-3.5-Turbo (default per p.6), greedy decoding, temperature 0; task-agnostic (question-agnostic) compression  
  source: llmlingua-2-2403.12968.txt p.9 Table 6  
  quote: `LLMLingua-2 30.7 33.9 25.4 66.6 22.6 58.1 39.5 1,853 5x 33.4 1,897 5x`
- **L2-065** (context_loss) Authors claim GPT-4 can reconstruct the original prompt from the compressed one, taken as evidence of no essential information loss (MeetingBank examples only).  
  value: `` metric:  task: MeetingBank examples (Fig. 7, 8) conditions: qualitative reconstruction test  
  source: llmlingua-2-2403.12968.txt p.8 Sec. 5 Prompt Reconstruction  
  quote: `suggesting that there is no essential information loss during the compression process of LLMLingua-2`
- **L2-070** (latency_compute) Table 5 row: end-to-end latency without compression (seconds, MeetingBank). Header: 1/tau 1x 2x 3x 5x. Target LLM used for end-to-end latency is not stated.  
  value: `14.9 s` metric: latency (s) task: MeetingBank conditions: V100-32G; target LLM not stated  
  source: llmlingua-2-2403.12968.txt p.8 Table 5  
  quote: `End2End w/o Compression 14.9`
- **L2-071** (latency_compute) Table 5 row: end-to-end latency with LLMLingua-2 at 2x, 3x, 5x compression (speedup in parentheses).  
  value: `9.4 s (1.6x) at 2x; 7.5 s (2.1x) at 3x; 5.2 s (2.9x) at 5x` metric: latency (s) task: MeetingBank conditions: V100-32G; target LLM not stated  
  source: llmlingua-2-2403.12968.txt p.8 Table 5  
  quote: `End2End w/ LLMLingua-2 - 9.4 (1.6x) 7.5 (2.1x) 5.2 (2.9x)`
- **L2-072** (latency_compute) Table 5 row: LLMLingua-2 latency at 2x, 3x, 5x. The caption does not say whether these rows are compressor-only time; the row ordering and magnitudes suggest compressor overhead (inferred).  
  value: `0.5 s; 0.4 s; 0.4 s` metric: latency (s) task: MeetingBank conditions: V100-32G  
  source: llmlingua-2-2403.12968.txt p.8 Table 5  
  quote: `LLMLingua-2 - 0.5 0.4 0.4`
- **L2-073** (hardware) Latency measured on a V100-32G GPU.  
  value: `V100-32G` metric:  task: MeetingBank conditions: latency evaluation  
  source: llmlingua-2-2403.12968.txt p.8 Sec. 5 Latency Evaluation  
  quote: `different systems on a V100-32G GPU with different compression ratios`
- **L2-074** (latency_compute) Peak GPU memory of LLMLingua-2 on MeetingBank.  
  value: `2.1GB` metric: GPU memory task: MeetingBank conditions: LLMLingua-2 compressor  
  source: llmlingua-2-2403.12968.txt p.14 Appendix I  
  quote: `memory usage of LLMLingua-2 on MeetingBank is only 2.1GB`
- **L2-075** (latency_compute) Peak GPU memory of the LLaMA-2-7B based baselines LLMLingua and Selective-Context (in that order) on the same data.  
  value: `16.6GB; 26.5GB` metric: GPU memory task: MeetingBank conditions: LLMLingua; Selective-Context  
  source: llmlingua-2-2403.12968.txt p.14 Appendix I  
  quote: `consume 16.6GB and 26.5GB of GPU memory, respectively`
- **L2-076** (latency_compute) Authors' summary of memory saving versus the LLaMA-2-7B baselines.  
  value: `8x` metric: GPU memory task: MeetingBank conditions:   
  source: llmlingua-2-2403.12968.txt p.8 Sec. 5 Latency Evaluation  
  quote: `our method can reduce GPU memory costs by 8x`
- **L2-077** (latency_compute) Abstract speed claim: 3x-6x faster than existing prompt compression methods (compressor-only; Table 5 gives the underlying seconds).  
  value: `3x-6x` metric:  task: MeetingBank (Table 5) conditions: V100-32G; compared against existing compressors, not only LLMLingua  
  source: llmlingua-2-2403.12968.txt p.1 Abstract  
  quote: `our model is 3x-6x faster than existing prompt compression methods`
- **L2-078** (latency_compute) Table 5 row for the LLMLingua baseline (seconds at 2x, 3x, 5x), kept here to check the paper's 3x-6x speed claim against LLMLingua-2 (L2-072).  
  value: `2.9 s; 2.1 s; 1.5 s` metric: latency (s) task: MeetingBank conditions: V100-32G; LLaMA-2-7B based baseline  
  source: llmlingua-2-2403.12968.txt p.8 Table 5  
  quote: `LLMLingua - 2.9 2.1 1.5`
- **L2-080** (cost) Token savings per request on MeetingBank (Table 1 LLMLingua-2 row; compare the original token count in L2-042).  
  value: `970 tokens at 3.1x` metric: tokens task: MeetingBank conditions: ratio about 3x  
  source: llmlingua-2-2403.12968.txt p.6 Table 1  
  quote: `LLMLingua-2 86.92 17.37 48.64 22.96 34.24 88.27 970 3.1x`
- **L2-081** (cost) Token savings per request on LongBench at 5x (Table 2 LLMLingua-2 row; compare the original token count in L2-043).  
  value: `1,954 tokens at 5x` metric: tokens task: LongBench conditions: 2,000-token constraint  
  source: llmlingua-2-2403.12968.txt p.7 Table 2  
  quote: `LLMLingua-2 29.8 33.1 25.3 66.4 21.3 58.9 39.1 1,954 5x 33.4 1,898 5x`
- **L2-082** (cost) The compressor is a small bidirectional encoder, so no extra LLM call is needed at inference (inferred from mechanism); the GPT-4 teacher is used only offline to build training data.  
  value: `` metric:  task:  conditions: inferred from mechanism  
  source: llmlingua-2-2403.12968.txt p.5 Sec. 4.1  
  quote: `we employ a Transformer encoder as the feature extractor to leverage information from the bidirectional contexts of each token`
- **L2-083** (cost) Training-data creation used GPT-4-32k as the compressor; the paper reports no GPT-4 token count or dollar cost for distillation (not reported).  
  value: `not reported` metric:  task: MeetingBank distillation conditions: GPT-4-32k  
  source: llmlingua-2-2403.12968.txt p.11 Appendix A  
  quote: `we use GPT-4-32k to compress the original meeting transcript`
- **L2-090** (limitation) Authors' own limitation: compressor training data is only MeetingBank (English meeting transcripts), raising generalization concerns.  
  value: `` metric:  task:  conditions: Limitations section  
  source: llmlingua-2-2403.12968.txt p.9 Limitations  
  quote: `This raises concerns about the generalization ability of our compressor.`
- **L2-091** (limitation) Authors say adding 50k TriviaQA-wiki examples to training helps only slightly.  
  value: `` metric:  task: LongBench; ZeroSCROLLS conditions: Limitations section  
  source: llmlingua-2-2403.12968.txt p.9 Limitations / Table 6  
  quote: `However, the improvement seems not that significant.`
- **L2-092** (limitation) Compressor training data is English only; Chinese results come from multilingual encoder pre-training transfer.  
  value: `` metric:  task: LongBench-Zh conditions: Appendix J  
  source: llmlingua-2-2403.12968.txt p.14 Appendix J  
  quote: `which consists of English corpus only`
- **L2-093** (limitation) The only non-English evaluation is five LongBench Chinese tasks (1000 samples); no other language is tested.  
  value: `5 tasks; 1000 samples` metric:  task: LongBench-Zh conditions: Appendix J  
  source: llmlingua-2-2403.12968.txt p.14 Appendix J  
  quote: `LongBench, comprising 5 tasks with a total of 1000 samples`
- **L2-094** (limitation) Failure analysis in the paper concerns OTHER extractive datasets (SentComp, DebateSum): their compressions are too concise and miss question-relevant details. The paper shows no failure example of LLMLingua-2 itself dropping question-relevant content.  
  value: `` metric:  task: SentComp; DebateSum (Fig. 13, 14) conditions: motivation for new dataset  
  source: llmlingua-2-2403.12968.txt p.13 Appendix G  
  quote: `The compressed texts provided in their dataset are usually too concise, only maintaining the main idea of the original text and lacking detailed information.`
- **L2-095** (limitation) Fig. 7 reconstruction (shown as a success by the authors) turns the compressed fragment into a sentence about 20 of 28 counties; compare the original wording in L2-096. Extractor observation, not the authors' claim.  
  value: `` metric:  task: MeetingBank example conditions: GPT-4 reconstruction of 2x compressed prompt  
  source: llmlingua-2-2403.12968.txt p.13 Fig. 7  
  quote: `As of now, 20 out of 28 counties have completed 29,000 energy efficient projects.`
- **L2-096** (limitation) Original transcript wording for the Fig. 7 example (see L2-095).  
  value: `` metric:  task: MeetingBank example conditions: uncompressed text  
  source: llmlingua-2-2403.12968.txt p.13 Fig. 7  
  quote: `We're in. Over 20. We're in 28 counties, and we've completed over`
- **L2-097** (limitation) Fig. 7 reconstruction also adds a sentence about a representative from CNN, while the original transcript only contains the token CNN (L2-098). Extractor observation, not the authors' claim.  
  value: `` metric:  task: MeetingBank example conditions: GPT-4 reconstruction of 2x compressed prompt  
  source: llmlingua-2-2403.12968.txt p.13 Fig. 7  
  quote: `We have a representative from CNN here.`
- **L2-098** (limitation) Original transcript wording around CNN for the Fig. 7 example.  
  value: `` metric:  task: MeetingBank example conditions: uncompressed text  
  source: llmlingua-2-2403.12968.txt p.13 Fig. 7  
  quote: `CNN. Please cast your vote.`
- **L2-100** (reproducibility) Paper gives a code link.  
  value: `` metric:  task:  conditions: footnote 1  
  source: llmlingua-2-2403.12968.txt p.1 Abstract footnote  
  quote: `Code: https://aka.ms/LLMLingua-2`
- **L2-101** (reproducibility) Authors state the MeetingBank-based extractive compression dataset is publicly released.  
  value: `` metric:  task:  conditions: dataset release  
  source: llmlingua-2-2403.12968.txt p.9 Sec. 6  
  quote: `We publicly release the dataset of text compression with no essential information loss in this paper.`
- **L2-102** (reproducibility) Official GitHub repository (microsoft/LLMLingua) is shown with an MIT license (WebFetch summary of the page; page states only the license name).  
  value: `MIT` metric:  task:  conditions: https://github.com/microsoft/LLMLingua  
  source: https://github.com/microsoft/LLMLingua GitHub About/Resources  
  quote: `MIT license`
- **L2-103** (reproducibility) Hugging Face card microsoft/llmlingua-2-xlm-roberta-large-meetingbank lists license mit (WebFetch noted the card's page heading names the BERT-base multilingual variant, an inconsistency on the card).  
  value: `mit` metric:  task:  conditions: https://huggingface.co/microsoft/llmlingua-2-xlm-roberta-large-meetingbank  
  source: https://huggingface.co/microsoft/llmlingua-2-xlm-roberta-large-meetingbank model card  
  quote: `License: mit`
- **L2-104** (reproducibility) GitHub README announces LLMLingua-2 with a 3x-6x speed improvement 'over LLMLingua' (README wording as returned by WebFetch).  
  value: `3x-6x over LLMLingua` metric:  task:  conditions: https://github.com/microsoft/LLMLingua  
  source: https://github.com/microsoft/LLMLingua README  
  quote: `boasting a 3x-6x speed improvement over LLMLingua!`
- **L2-110** (tasks_tested) In-domain plus out-of-domain dataset list: MeetingBank (in-domain), LongBench, ZeroSCROLLS, GSM8K, Big Bench Hard; later NaturalQuestions 20-doc (Table 11) and LongBench-Zh (Table 10).  
  value: `` metric:  task: MeetingBank; LongBench; ZeroSCROLLS; GSM8K; BBH conditions: dataset list  
  source: llmlingua-2-2403.12968.txt p.2 Sec. 1 Contributions  
  quote: `ZeroScrolls, GSM8K, and Big Bench Hard)`
- **L2-111** (tasks_tested) Authors summarise tasks covered: document QA, math problems, in-context learning; nothing on chat, code-specific, structured-data or sensitive-content tasks is listed.  
  value: `` metric:  task: LongBench; ZeroSCROLLS; GSM8K; BBH conditions: Limitations section dataset summary  
  source: llmlingua-2-2403.12968.txt p.9 Limitations  
  quote: `which cover multiple tasks from document QA to math problems and in-context learning`
- **L2-112** (tasks_tested) Coding: the only code-related item is a 'Code' column in the LongBench/ZeroSCROLLS table header; the paper never describes what it contains, its metric, or discusses code compression.  
  value: `partially: LongBench Code column only` metric:  task: LongBench Code column conditions: see L2-034/035/043/044  
  source: llmlingua-2-2403.12968.txt p.7 Table 2 header  
  quote: `SingleDoc MultiDoc Summ. FewShot Synth. Code AVG Tokens 1/ AVG Tokens 1/`
- **L2-113** (tasks_tested) Long-document QA/RAG: LongBench SingleDoc/MultiDoc QA, ZeroSCROLLS and NaturalQuestions 20-doc were tested.  
  value: `tested` metric:  task: LongBench; ZeroSCROLLS; NaturalQuestions 20-doc conditions:   
  source: llmlingua-2-2403.12968.txt p.7 Sec. 5 Datasets & Evaluation Metrics  
  quote: `we use LongBench (Bai et al., 2023) and`
- **L2-114** (tasks_tested) Multi-turn chat/conversation: not tested in paper (dataset list quoted: document QA, math, in-context learning).  
  value: `not tested in paper` metric:  task:  conditions:   
  source: llmlingua-2-2403.12968.txt p.9 Limitations  
  quote: `which cover multiple tasks from document QA to math problems and in-context learning`
- **L2-115** (tasks_tested) Structured data (JSON/tables/logs): not tested in paper (the LongBench Synth. column is not described).  
  value: `not tested in paper` metric:  task:  conditions:   
  source: llmlingua-2-2403.12968.txt p.9 Limitations  
  quote: `which cover multiple tasks from document QA to math problems and in-context learning`
- **L2-116** (tasks_tested) Reasoning/math: GSM8K and BBH were tested with compressed few-shot demonstrations.  
  value: `tested` metric: EM task: GSM8K; BBH conditions:   
  source: llmlingua-2-2403.12968.txt p.7 Sec. 5 Datasets & Evaluation Metrics  
  quote: `For reasoning and in-context learning, we use GSM8K (Cobbe et al., 2021) and Big Bench Hard (BBH)`
- **L2-117** (tasks_tested) Sensitive/PII content: not tested in paper (dataset list quoted: document QA, math, in-context learning).  
  value: `not tested in paper` metric:  task:  conditions:   
  source: llmlingua-2-2403.12968.txt p.9 Limitations  
  quote: `which cover multiple tasks from document QA to math problems and in-context learning`
- **L2-118** (tasks_tested) Summarization: MeetingBank summary (Rouge etc.) and LongBench/ZeroSCROLLS Summ. columns; MeetingBank QA metric is Exact Match.  
  value: `tested` metric: EM; Rouge1/2/L; BLEU; BERTScore task: MeetingBank; LongBench Summ. conditions:   
  source: llmlingua-2-2403.12968.txt p.7 Sec. 5 Datasets & Evaluation Metrics  
  quote: `For QA task, we utilize the Exact Match as the evaluation metric.`
- **L2-119** (tasks_tested) MeetingBank summaries used as ground truth are themselves generated by GPT-4-32K (the same teacher family used to build training labels).  
  value: `` metric:  task: MeetingBank summary conditions: evaluation references  
  source: llmlingua-2-2403.12968.txt p.13 Appendix F  
  quote: `The summaries generated by GPT-4 are used as ground truth to evaluate the summary performance.`
- **L2-120** (tasks_tested) MeetingBank QA pairs are also generated by GPT-4-32K (then filtered).  
  value: `10 generated per transcript` metric:  task: MeetingBank QA conditions: evaluation references  
  source: llmlingua-2-2403.12968.txt p.12 Appendix F  
  quote: `we generate 10 question-answer pairs for each meeting transcript using GPT-4-32K`
- **L2-121** (context_loss) Metric statement for LongBench/ZeroSCROLLS: same metrics as LongLLMLingua; this paper does not name them (per-task metrics unverified here).  
  value: `` metric: same as LongLLMLingua (not named) task: LongBench; ZeroSCROLLS conditions:   
  source: llmlingua-2-2403.12968.txt p.7 Sec. 5 Datasets & Evaluation Metrics  
  quote: `we employ the same evaluation metric as in LongLLMLingua (Jiang et al., 2023b)`
- **L2-130** (reproducibility) The real paper's arXiv identifier, title and date line (Pan et al., Tsinghua/Microsoft).  
  value: `arXiv:2403.12968v2, 12 Aug 2024` metric:  task:  conditions: paper identity  
  source: llmlingua-2-2403.12968.txt p.1 Title page  
  quote: `arXiv:2403.12968v2 [cs.CL] 12 Aug 2024`
- **L2-131** (reproducibility) Real title is 'LLMLingua-2: Data Distillation for Efficient and Faithful Task-Agnostic Prompt Compression'.  
  value: `` metric:  task:  conditions: paper identity  
  source: llmlingua-2-2403.12968.txt p.1 Title page  
  quote: `LLMLingua-2: Data Distillation for Efficient and Faithful Task-Agnostic Prompt Compression`
- **L2-132** (reproducibility) First author listed on the real paper.  
  value: `` metric:  task:  conditions: paper identity  
  source: llmlingua-2-2403.12968.txt p.1 Title page  
  quote: `Zhuoshi Pan1`

## LongLLMLingua

- **LongLL-ABL-1** (context_loss) Table 3 caption: ablation on NaturalQuestions, 2x, GPT-3.5-Turbo.  
  value: `` metric: accuracy task: NaturalQuestions conditions: GPT-3.5-Turbo; 2x  
  source: longllmlingua-2310.06839.txt p.8 Table 3 caption  
  quote: `Ablation study on NaturalQuestions with 2x constraint using GPT-3.5-Turbo`
- **LongLL-ABL-10** (context_loss) Table 4 full LongLLMLingua at 2,000 tokens (LongBench, GPT-3.5-Turbo).  
  value: `AVG 48.3` metric: LongBench score task: LongBench conditions: GPT-3.5-Turbo; 2,000 tokens  
  source: longllmlingua-2310.06839.txt p.14 Table 4  
  quote: `LongLLMLingua 39.9 43.2 27.4 69.8 53.0 56.7 48.3 1,822 6x`
- **LongLL-ABL-11** (context_loss) Table 4: without question-awareness, LongBench average falls, with Synthetic dropping most.  
  value: `AVG 37.4; Synth. 18.0` metric: LongBench score task: LongBench conditions: GPT-3.5-Turbo; 2,000 tokens  
  source: longllmlingua-2310.06839.txt p.14 Table 4  
  quote: `- w/o Question-awareness 27.1 38.7 25.4 62.0 18.0 53.3 37.4 1,945 5x`
- **LongLL-ABL-12** (context_loss) Table 4: without question-aware fine-grained compression.  
  value: `AVG 44.2` metric: LongBench score task: LongBench conditions: GPT-3.5-Turbo; 2,000 tokens  
  source: longllmlingua-2310.06839.txt p.14 Table 4  
  quote: `- w/o Question-aware Fine-grained 35.7 41.1 26.4 62.9 44.5 54.8 44.2 1,807 6x`
- **LongLL-ABL-13** (context_loss) Table 4: GPT2-small compressor LM.  
  value: `AVG 43.0` metric: LongBench score task: LongBench conditions: GPT-3.5-Turbo; 2,000 tokens  
  source: longllmlingua-2310.06839.txt p.14 Table 4  
  quote: `- w/ GPT2-small 35.9 39.4 25.0 60.6 42.0 55.4 43.0 1,892 5x`
- **LongLL-ABL-14** (context_loss) Table 4: removing document reordering costs little on LongBench.  
  value: `AVG 48.0` metric: LongBench score task: LongBench conditions: GPT-3.5-Turbo; 2,000 tokens  
  source: longllmlingua-2310.06839.txt p.14 Table 4  
  quote: `- w/o Document Reordering 39.0 42.2 27.4 69.3 53.8 56.6 48.0 1,809 6x`
- **LongLL-ABL-15** (context_loss) Authors say question-aware coarse-grained step matters most for document QA and synthetic tasks, less for summarization and code.  
  value: `35.8 points` metric: points task: LongBench conditions: GPT-3.5-Turbo; 2,000 tokens  
  source: longllmlingua-2310.06839.txt p.13 Appendix C.2  
  quote: `question-aware coarse-grained is particularly important for document-based QA and synthetic tasks, with the maximum drop being 35.8 points; its impact on summarization and code tasks is relatively smaller`
- **LongLL-ABL-16** (context_loss) Authors: GPT2-small compressor loses effective tokens but still reaches near or slightly above the original prompt on LongBench.  
  value: `` metric:  task: LongBench conditions:   
  source: longllmlingua-2310.06839.txt p.14 Appendix C.2  
  quote: `reduces the capture of effective tokens, but it can still achieve results close to or even slightly better than the original prompt`
- **LongLL-ABL-2** (context_loss) Table 3 full LongLLMLingua (answer at 1st/5th/10th/15th/20th).  
  value: `77.2 / 72.9 / 70.8 / 70.5 / 70.6` metric: accuracy task: NaturalQuestions conditions: GPT-3.5-Turbo; 2x  
  source: longllmlingua-2310.06839.txt p.8 Table 3  
  quote: `LongLLMLingua 77.2 72.9 70.8 70.5 70.6`
- **LongLL-ABL-3** (context_loss) Table 3: removing question-awareness in the coarse step nearly halves accuracy.  
  value: `42.1 / 40.3 / 39.7 / 40.1 / 40.3` metric: accuracy task: NaturalQuestions conditions: GPT-3.5-Turbo; 2x  
  source: longllmlingua-2310.06839.txt p.8 Table 3  
  quote: `- w/o Question-awareness 42.1 40.3 39.7 40.1 40.3`
- **LongLL-ABL-4** (context_loss) Table 3: replacing the question-aware ranker with SBERT.  
  value: `73.2 / 68.5 / 65.7 / 66.1 / 66.7` metric: accuracy task: NaturalQuestions conditions: GPT-3.5-Turbo; 2x  
  source: longllmlingua-2310.06839.txt p.8 Table 3  
  quote: `- w/ SBERT 73.2 68.5 65.7 66.1 66.7`
- **LongLL-ABL-5** (context_loss) Table 3: without question-aware fine-grained (contrastive perplexity) compression.  
  value: `75.8 / 71.0 / 68.9 / 68.4 / 69.3` metric: accuracy task: NaturalQuestions conditions: GPT-3.5-Turbo; 2x  
  source: longllmlingua-2310.06839.txt p.8 Table 3  
  quote: `- w/o Question-aware Fine-grained 75.8 71.0 68.9 68.4 69.3`
- **LongLL-ABL-6** (context_loss) Table 3: without dynamic compression ratio.  
  value: `74.4 / 70.7 / 68.7 / 67.9 / 68.1` metric: accuracy task: NaturalQuestions conditions: GPT-3.5-Turbo; 2x  
  source: longllmlingua-2310.06839.txt p.8 Table 3  
  quote: `- w/o Dynamic Compression Ratio 74.4 70.7 68.7 67.9 68.1`
- **LongLL-ABL-7** (context_loss) Table 3: without subsequence recovery.  
  value: `76.7 / 71.7 / 69.4 / 69.3 / 69.7` metric: accuracy task: NaturalQuestions conditions: GPT-3.5-Turbo; 2x  
  source: longllmlingua-2310.06839.txt p.8 Table 3  
  quote: `- w/o Subsequence Recovery 76.7 71.7 69.4 69.3 69.7`
- **LongLL-ABL-8** (context_loss) Table 3: GPT2-small (GPT2-dolly) as the compressor LM.  
  value: `74.6 / 71.7 / 70.1 / 69.8 / 68.5` metric: accuracy task: NaturalQuestions conditions: GPT-3.5-Turbo; 2x  
  source: longllmlingua-2310.06839.txt p.8 Table 3  
  quote: `- w/ GPT2-small 74.6 71.7 70.1 69.8 68.5`
- **LongLL-ABL-9** (context_loss) Authors conclude removing any component causes a drop at every answer position.  
  value: `` metric:  task: NaturalQuestions conditions:   
  source: longllmlingua-2310.06839.txt p.7 Sec. 5 Ablation  
  quote: `removing any component proposed for LongLLMLingua will lead to a performance drop regardless of the position of the ground-truth answer`
- **LongLL-CL-1** (context_loss) Table 1 column layout: GPT3.5-Turbo accuracy by answer position (1st,5th,10th,15th,20th) and Reorder, then LongChat-13b the same, then Tokens, 1/tau, Latency, Speedup.  
  value: `` metric: accuracy task: NaturalQuestions (20 docs) conditions:   
  source: longllmlingua-2310.06839.txt p.7 Table 1 header  
  quote: `1st 5th 10th 15th 20th Reorder 1st 5th 10th 15th 20th Reorder Tokens`
- **LongLL-CL-10** (context_loss) Authors state LLMLingua and Selective Context can even fall below the zero-shot setting on NaturalQuestions.  
  value: `` metric:  task: NaturalQuestions conditions:   
  source: longllmlingua-2310.06839.txt p.6 Sec. 5 Main results  
  quote: `performance worse than the zero-shot setting, e.g., on NaturalQuestions`
- **LongLL-CL-11** (context_loss) Authors note a small gain from 2x to 4x compression for LongLLMLingua.  
  value: `` metric:  task: NaturalQuestions conditions:   
  source: longllmlingua-2310.06839.txt p.6 Sec. 5 Main results  
  quote: `LongLLMLingua even achieves a little performance gain`
- **LongLL-CL-12** (context_loss) Table 1 reporting convention: columns 1st-20th are without reordering for all methods.  
  value: `` metric:  task: NaturalQuestions conditions:   
  source: longllmlingua-2310.06839.txt p.7 Table 1 caption  
  quote: `For results reported under 1st to 20th, we do not use the reordering strategy for all methods`
- **LongLL-CL-13** (context_loss) NaturalQuestions metric is accuracy (percent), per the Figure 1b axis.  
  value: `` metric: accuracy task: NaturalQuestions conditions:   
  source: longllmlingua-2310.06839.txt p.2 Figure 1b  
  quote: `Accuracy(%)`
- **LongLL-CL-14** (context_loss) Table 2 header columns (LongBench categories + average + length + latency).  
  value: `` metric:  task: LongBench conditions:   
  source: longllmlingua-2310.06839.txt p.8 Table 2 header  
  quote: `Methods SingleDoc MultiDoc Summ. FewShot Synth. Code AVG Tokens`
- **LongLL-CL-15** (context_loss) Table 2 caption: LongBench with GPT-3.5-Turbo under 3,000 and 2,000 token constraints.  
  value: `` metric:  task: LongBench conditions: GPT-3.5-Turbo  
  source: longllmlingua-2310.06839.txt p.8 Table 2 caption  
  quote: `Performance of different methods under different compression ratios on LongBench (Bai et al., 2023) using GPT-3.5-Turbo in 2,000 tokens constraint`
- **LongLL-CL-16** (context_loss) Table 2 original prompt: scores per LongBench category, average length 10,295 tokens, latency 15.6 s.  
  value: `44.0 AVG; Code 54.2; 10,295 tokens; 15.6 s` metric: LongBench score task: LongBench conditions: GPT-3.5-Turbo; no compression  
  source: longllmlingua-2310.06839.txt p.8 Table 2  
  quote: `Original Prompt 39.7 38.7 26.5 67.0 37.8 54.2 44.0 10,295 - 15.6 -`
- **LongLL-CL-17** (context_loss) Table 2, 3,000 token constraint (3x): LongLLMLingua row.  
  value: `AVG 48.8; Code 55.2; 3x; 1.6x speedup` metric: LongBench score task: LongBench conditions: GPT-3.5-Turbo; 3,000 tokens  
  source: longllmlingua-2310.06839.txt p.8 Table 2  
  quote: `LongLLMLingua 40.7 46.2 27.2 70.6 53.0 55.2 48.8 3,283 3x 10.0 1.6x`
- **LongLL-CL-18** (context_loss) Table 2, 2,000 token constraint (about 6x on 10k prompts): LongLLMLingua row.  
  value: `AVG 48.3; Code 56.7; 6x; 2.6x speedup` metric: LongBench score task: LongBench conditions: GPT-3.5-Turbo; 2,000 tokens  
  source: longllmlingua-2310.06839.txt p.8 Table 2  
  quote: `LongLLMLingua 39.9 43.2 27.4 69.8 53.0 56.7 48.3 1,822 6x 6.1 2.6x`
- **LongLL-CL-19** (context_loss) Table 2, 3,000 tokens: LLMLingua (v1) row for comparison.  
  value: `AVG 37.4; Code 53.2` metric: LongBench score task: LongBench conditions: GPT-3.5-Turbo; 3,000 tokens  
  source: longllmlingua-2310.06839.txt p.8 Table 2  
  quote: `LLMLingua 31.8 37.5 26.2 67.2 8.3 53.2 37.4 3,421 3x 9.2 1.7x`
- **LongLL-CL-2** (context_loss) Table 1 original (uncompressed) prompt, accuracy by answer position; U-shaped, best at 1st position (GPT-3.5-Turbo columns first).  
  value: `75.7 / 57.3 / 54.1 / 55.4 / 63.1` metric: accuracy task: NaturalQuestions (20 docs) conditions: GPT-3.5-Turbo (first five numbers), LongChat-13b (next five); 2,946 tokens; latency 4.1 s  
  source: longllmlingua-2310.06839.txt p.7 Table 1  
  quote: `Original Prompt 75.7 57.3 54.1 55.4 63.1 - 68.6 57.4 55.3 52.5 55.0 - 2,946 - 4.1 -`
- **LongLL-CL-20** (context_loss) Table 2, 2,000 tokens: LLMLingua (v1) row; its Code score is slightly above the original while other categories fall.  
  value: `AVG 34.6; Code 56.8` metric: LongBench score task: LongBench conditions: GPT-3.5-Turbo; 2,000 tokens  
  source: longllmlingua-2310.06839.txt p.8 Table 2  
  quote: `LLMLingua 22.4 32.1 24.5 61.2 10.4 56.8 34.6 1,950 5x 5.9 2.6x`
- **LongLL-CL-21** (context_loss) Table 2, 3,000 tokens: Selective-Context row (latency 50.6 s, 0.3x).  
  value: `AVG 32.0` metric: LongBench score task: LongBench conditions: GPT-3.5-Turbo; 3,000 tokens  
  source: longllmlingua-2310.06839.txt p.8 Table 2  
  quote: `Selective-Context 23.3 39.2 25.0 23.8 27.5 53.1 32.0 3,328 3x 50.6 0.3x`
- **LongLL-CL-22** (context_loss) Table 2 zero-shot row (214 tokens) for LongBench.  
  value: `AVG 23.5; Code 36.2` metric: LongBench score task: LongBench conditions: GPT-3.5-Turbo zero-shot  
  source: longllmlingua-2310.06839.txt p.8 Table 2  
  quote: `Zero-shot 15.6 31.3 15.6 40.7 1.6 36.2 23.5 214 48x 1.6 9.8x`
- **LongLL-CL-23** (context_loss) LongBench categories listed by the authors include code completion.  
  value: `` metric:  task: LongBench conditions:   
  source: longllmlingua-2310.06839.txt p.12 Appendix B.1  
  quote: `such as single-document QA, multi-document QA, summarization, few-shot learning, synthetic tasks, and code completion`
- **LongLL-CL-24** (context_loss) Table 5 (LongChat-13b target): original prompt scores.  
  value: `AVG 30.5; Code 42.5` metric: LongBench score task: LongBench conditions: LongChat-13b-16k; no compression  
  source: longllmlingua-2310.06839.txt p.15 Table 5  
  quote: `Original Prompt 27.4 30.3 20.3 49.9 12.5 42.5 30.5 10,295 -`
- **LongLL-CL-25** (context_loss) Table 5 (LongChat-13b target), 2,000 tokens: LongLLMLingua row.  
  value: `AVG 35.5; Code 48.8; 6x` metric: LongBench score task: LongBench conditions: LongChat-13b-16k; 2,000 tokens  
  source: longllmlingua-2310.06839.txt p.15 Table 5  
  quote: `LongLLMLingua 31.3 34.6 24.6 46.1 27.8 48.8 35.5 1,822 6x`
- **LongLL-CL-26** (context_loss) Table 6 header: ZeroSCROLLS task columns; GvRp/SSFD/QMsm/SQAL are summarization, QALT/Nrtv/Qspr/MuSQ QA, SpDg/BkSS ordering (mapping from authors' text in C.4).  
  value: `` metric:  task: ZeroSCROLLS conditions:   
  source: longllmlingua-2310.06839.txt p.15 Table 6 header  
  quote: `Methods GvRp SSFD QMsm SQAL QALT Nrtv Qspr MuSQ SpDg BkSS AVG Tokens`
- **LongLL-CL-27** (context_loss) Table 6 original prompt (9,788 tokens, 12.2 s).  
  value: `AVG 32.5` metric: ZeroSCROLLS score task: ZeroSCROLLS conditions: GPT-3.5-Turbo; no compression  
  source: longllmlingua-2310.06839.txt p.15 Table 6  
  quote: `Original Prompt 21.8 12.1 17.9 17.4 66.7 25.3 29.8 20.0 69.7 44.1 32.5 9,788 - 12.2 -`
- **LongLL-CL-28** (context_loss) Table 6, 3,000 tokens (3x): LongLLMLingua row.  
  value: `AVG 33.0; 1.5x speedup` metric: ZeroSCROLLS score task: ZeroSCROLLS conditions: GPT-3.5-Turbo; 3,000 tokens  
  source: longllmlingua-2310.06839.txt p.15 Table 6  
  quote: `LongLLMLingua 22.1 12.8 15.9 17.1 67.0 27.8 31.3 23.9 65.8 46.5 33.0 3,431 3x 8.2 1.5x`
- **LongLL-CL-29** (context_loss) Table 6, 2,000 tokens (6x): LongLLMLingua row; several summarization columns are below the original (GvRp, QMsm).  
  value: `AVG 32.7; 2.3x speedup` metric: ZeroSCROLLS score task: ZeroSCROLLS conditions: GPT-3.5-Turbo; 2,000 tokens  
  source: longllmlingua-2310.06839.txt p.15 Table 6  
  quote: `LongLLMLingua 20.1 12.4 14.9 16.5 65.1 27.7 30.7 23.6 68.5 47.2 32.7 1,826 6x 5.2 2.3x`
- **LongLL-CL-3** (context_loss) Table 1, 2x constraint: LongLLMLingua row (question-aware).  
  value: `77.2 / 72.9 / 70.8 / 70.5 / 70.6; Reorder 76.2; 2.1x; 1.4x speedup` metric: accuracy task: NaturalQuestions (20 docs) conditions: GPT-3.5-Turbo (first six), LongChat-13b (next six); 2x constraint  
  source: longllmlingua-2310.06839.txt p.7 Table 1  
  quote: `LongLLMLingua 77.2 72.9 70.8 70.5 70.6 76.2 68.7 59.4 57.3 55.9 58.4 66.1 1,429 2.1x 2.9 1.4x`
- **LongLL-CL-30** (context_loss) Table 6 anomaly: LLMLingua (2,000 tokens) latency 4.8 s versus original 12.2 s but printed speedup 0.3x, internally inconsistent; do not use the speedup value.  
  value: `4.8 s; 0.3x` metric: latency task: ZeroSCROLLS conditions: GPT-3.5-Turbo; likely typo  
  source: longllmlingua-2310.06839.txt p.15 Table 6  
  quote: `LLMLingua 19.4 11.9 13.1 16.0 62.1 23.7 24.0 22.4 33.9 44.9 27.2 1,862 5x 4.8 0.3x`
- **LongLL-CL-31** (context_loss) Authors say LongLLMLingua closely matches or slightly surpasses original results on the four summarization tasks.  
  value: `` metric:  task: ZeroSCROLLS conditions:   
  source: longllmlingua-2310.06839.txt p.14 Appendix C.4  
  quote: `LongLLMLingua closely matches or slightly surpasses the original results under two compression constraints`
- **LongLL-CL-32** (context_loss) Table 7 caption: MuSiQue with 2x constraint using GPT-3.5-Turbo; metric F1.  
  value: `` metric: F1 task: MuSiQue conditions: GPT-3.5-Turbo; 2x  
  source: longllmlingua-2310.06839.txt p.16 Table 7 caption  
  quote: `Performance of different methods and ablation study on MuSicQue (Trivedi et al., 2022) with 2x constraint using GPT-3.5-Turbo`
- **LongLL-CL-33** (context_loss) Table 7 original prompt (2,427 tokens).  
  value: `45.8` metric: F1 task: MuSiQue conditions: GPT-3.5-Turbo; no compression  
  source: longllmlingua-2310.06839.txt p.16 Table 7  
  quote: `Original Prompt 45.8 2,427 -`
- **LongLL-CL-34** (context_loss) Table 7 LongLLMLingua at 2.3x.  
  value: `51.2 at 2.3x` metric: F1 task: MuSiQue conditions: GPT-3.5-Turbo; 2x constraint  
  source: longllmlingua-2310.06839.txt p.16 Table 7  
  quote: `LongLLMLingua 51.2 1,077 2.3x`
- **LongLL-CL-35** (context_loss) Table 7 LLMLingua (v1) at 2.2x.  
  value: `40.1 at 2.2x` metric: F1 task: MuSiQue conditions: GPT-3.5-Turbo; 2x constraint  
  source: longllmlingua-2310.06839.txt p.16 Table 7  
  quote: `LLMLingua 40.1 1,110 2.2x`
- **LongLL-CL-36** (context_loss) Table 8 original prompt on LooGLE long-dependency QA (average 30,546 tokens).  
  value: `AVG 22.6` metric: LooGLE score task: LooGLE long-dependency QA conditions: GPT-3.5-Turbo; no compression  
  source: longllmlingua-2310.06839.txt p.17 Table 8  
  quote: `Original Prompt 24.1 20.9 13.5 32.1 22.6 30,546 -`
- **LongLL-CL-37** (context_loss) Table 8 LongLLMLingua at 10x on LooGLE (columns Retrieval, Timeline Reorder, Computation, Reasoning, AVG).  
  value: `AVG 32.1 at 10x` metric: LooGLE score task: LooGLE long-dependency QA conditions: GPT-3.5-Turbo  
  source: longllmlingua-2310.06839.txt p.17 Table 8  
  quote: `LongLLMLingua 40.0 35.0 19.7 33.6 32.1 3,121 10x`
- **LongLL-CL-38** (context_loss) Table 8 LLMLingua (v1) at 9x on LooGLE.  
  value: `AVG 17.3 at 9x` metric: LooGLE score task: LooGLE long-dependency QA conditions: GPT-3.5-Turbo  
  source: longllmlingua-2310.06839.txt p.17 Table 8  
  quote: `LLMLingua 10.0 25.0 13.3 21.1 17.3 3,404 9x`
- **LongLL-CL-39** (context_loss) LooGLE: compression baselines lose most on retrieval tasks because they cannot see the question.  
  value: `` metric:  task: LooGLE conditions:   
  source: longllmlingua-2310.06839.txt p.16 Appendix C.6  
  quote: `due to the difficulty in perceiving question information, there tends to be a larger performance loss in retrieval tasks within long contexts`
- **LongLL-CL-4** (context_loss) Table 1, 4x constraint: LongLLMLingua row. Compared with the original row, 1st-position accuracy is slightly below uncompressed, while middle positions are far above.  
  value: `75.0 / 71.8 / 71.2 / 71.2 / 74.7; Reorder 75.5; 3.9x; 2.0x speedup` metric: accuracy task: NaturalQuestions (20 docs) conditions: GPT-3.5-Turbo (first six), LongChat-13b (next six); 4x constraint  
  source: longllmlingua-2310.06839.txt p.7 Table 1  
  quote: `LongLLMLingua 75.0 71.8 71.2 71.2 74.7 75.5 68.7 60.5 59.3 58.3 61.3 66.7 748 3.9x 2.1 2.0x`
- **LongLL-CL-5** (context_loss) Table 1, 4x constraint: LLMLingua (v1, query-agnostic) is far below the original on NaturalQuestions.  
  value: `25.5 / 27.5 / 23.5 / 26.5 / 30.0` metric: accuracy task: NaturalQuestions (20 docs) conditions: GPT-3.5-Turbo (first six), LongChat-13b (next six); 4x constraint  
  source: longllmlingua-2310.06839.txt p.7 Table 1  
  quote: `LLMLingua 25.5 27.5 23.5 26.5 30.0 27.0 32.1 30.8 29.9 28.9 32.4 30.5 775 3.8x 1.8 2.2x`
- **LongLL-CL-6** (context_loss) Table 1, 2x constraint: LLMLingua (v1) baseline.  
  value: `39.7 / 39.5 / 40.4 / 37.1 / 42.3` metric: accuracy task: NaturalQuestions (20 docs) conditions: GPT-3.5-Turbo (first six), LongChat-13b (next six); 2x constraint  
  source: longllmlingua-2310.06839.txt p.7 Table 1  
  quote: `LLMLingua 39.7 39.5 40.4 37.1 42.3 41.5 38.7 37.3 35.7 34.1 37.5 37.1 1,410 2.1x 2.8 1.5x`
- **LongLL-CL-7** (context_loss) Table 1, 4x constraint: Selective-Context baseline (also much slower: 6.8 s).  
  value: `31.4 / 19.5 / 24.7 / 24.1 / 43.8` metric: accuracy task: NaturalQuestions (20 docs) conditions: GPT-3.5-Turbo (first five), LongChat-13b; 4x constraint  
  source: longllmlingua-2310.06839.txt p.7 Table 1  
  quote: `Selective-Context 31.4 19.5 24.7 24.1 43.8 - 38.2 17.2 15.9 16.0 27.3 - 791 3.7x 6.8 0.6x`
- **LongLL-CL-8** (context_loss) Table 1, 4x constraint: coarse-grained ranker r_k alone (retrieval-style, no token pruning) is already close to full LongLLMLingua.  
  value: `71.1 / 70.7 / 69.3 / 68.7 / 68.5` metric: accuracy task: NaturalQuestions (20 docs) conditions: GPT-3.5-Turbo (first six), LongChat-13b; 4x constraint  
  source: longllmlingua-2310.06839.txt p.7 Table 1  
  quote: `LongLLMLingua rk 71.1 70.7 69.3 68.7 68.5 71.5 67.8 59.4 57.7 57.7 58.6 64.0 807 3.7x 1.7 2.4x`
- **LongLL-CL-9** (context_loss) Table 1 zero-shot row (no documents); garbled extraction: first numbers 56.1 and 35.0 are presumably GPT-3.5-Turbo and LongChat accuracies, then tokens/ratio/latency/speedup. Column mapping not certain.  
  value: `56.1; 35.0` metric: accuracy task: NaturalQuestions conditions: zero-shot; mapping uncertain  
  source: longllmlingua-2310.06839.txt p.7 Table 1  
  quote: `Zero-shot 56.1 35.0 15 196x 1.1 3.7x`
- **LongLL-COST-1** (cost) Table 9 header: dataset columns, cost per 1,000 samples with GPT-3.5-Turbo.  
  value: `` metric: USD per 1,000 samples task:  conditions:   
  source: longllmlingua-2310.06839.txt p.17 Table 9  
  quote: `Multi-document QA LongBench ZeroScolls MuSicQue LooGLE`
- **LongLL-COST-2** (cost) Table 9 original cost per 1,000 samples.  
  value: `4.6; 31.5; 30.6; 3.8; 93.6` metric: USD per 1,000 samples task: NQ multi-doc QA; LongBench; ZeroSCROLLS; MuSiQue; LooGLE conditions: GPT-3.5-Turbo pricing  
  source: longllmlingua-2310.06839.txt p.17 Table 9  
  quote: `Original 4.6 31.5 30.6 3.8 93.6`
- **LongLL-COST-3** (cost) Table 9 cost with LongLLMLingua and percent reduction.  
  value: `1.3 (71.7%); 3.0 (90.5%); 3.2 (89.5%); 1.8 (52.6%); 5.6 (94.0%)` metric: USD per 1,000 samples task: NQ multi-doc QA; LongBench; ZeroSCROLLS; MuSiQue; LooGLE conditions: GPT-3.5-Turbo pricing  
  source: longllmlingua-2310.06839.txt p.17 Table 9  
  quote: `Ours 1.3 (71.7%) 3.0 (90.5%) 3.2 (89.5%) 1.8 (52.6%) 5.6 (94.0%)`
- **LongLL-COST-4** (cost) Costs cover prompt and output tokens at GPT-3.5-Turbo prices; no cost for running the small LM is mentioned.  
  value: `` metric:  task:  conditions:   
  source: longllmlingua-2310.06839.txt p.16 Appendix D  
  quote: `Table 9 presents the estimated per 1,000 samples inference costs for various datasets, encompassing input prompts and generated output text, based on GPT-3.5-Turbo pricing19`
- **LongLL-COST-5** (cost) Authors list dollar and percent savings per 1,000 samples for each benchmark.  
  value: `$3.3 (71.7%), $28.5 (90.5%), $27.4 (89.5%), $2.0 (52.6%), $88.0 (94.0%)` metric: USD per 1,000 samples task: NQ multi-doc QA; LongBench; ZeroSCROLLS; MuSiQue; LooGLE conditions: GPT-3.5-Turbo pricing  
  source: longllmlingua-2310.06839.txt p.16 Appendix D  
  quote: `Cost reductions of $3.3 (71.7%), $28.5 (90.5%), $27.4 (89.5%), $2.0 (52.6%), and $88.0 (94.0%) per 1,000 samples are observed for Multi-document QA, LongBench, ZeroScrolls, MuSiQue, and LooGLE, respectively`
- **LongLL-CR-1** (compression_ratio) Abstract headline: up to 21.4% boost on NaturalQuestions with around 4x fewer tokens (GPT-3.5-Turbo); the body ties this to answer at the 10th position.  
  value: `21.4%; 4x` metric: accuracy task: NaturalQuestions conditions: GPT-3.5-Turbo  
  source: longllmlingua-2310.06839.txt p.1 Abstract  
  quote: `LongLLMLingua boosts performance by up to 21.4% with around 4x fewer tokens in GPT-3.5-Turbo`
- **LongLL-CR-2** (cost) Abstract: 94.0% cost reduction on LooGLE.  
  value: `94.0%` metric: cost task: LooGLE conditions: GPT-3.5-Turbo pricing  
  source: longllmlingua-2310.06839.txt p.1 Abstract  
  quote: `It achieves a 94.0% cost reduction in the LooGLE benchmark`
- **LongLL-CR-3** (latency_compute) Abstract: 1.4x-2.6x end-to-end latency acceleration for ~10k-token prompts at 2x-6x.  
  value: `1.4x-2.6x` metric: speedup task: multi-document QA, LongBench, ZeroSCROLLS conditions: V100-32G  
  source: longllmlingua-2310.06839.txt p.1 Abstract  
  quote: `tios of 2x-6x, LongLLMLingua can accelerate end-to-end latency by 1.4x-2.6x`
- **LongLL-CR-4** (compression_ratio) Body text ties the 21.4% gain to the ground-truth document at the 10th position and 4x fewer tokens.  
  value: `21.4%; 4x` metric: accuracy task: NaturalQuestions conditions: GPT-3.5-Turbo; answer at 10th position  
  source: longllmlingua-2310.06839.txt p.6 Sec. 5 Main results  
  quote: `LongLLMLingua gains a performance boost of 21.4% on NaturalQuestions with the ground-truth document at the 10th position, while the number of tokens input to GPT3.5-Turbo is 4x less`
- **LongLL-CR-5** (compression_ratio) Case study of a 30x setting (compression at 30x) from NaturalQuestions, illustrating extreme compression with subsequence recovery.  
  value: `30x` metric:  task: NaturalQuestions conditions: GPT-3.5-Turbo; case study  
  source: longllmlingua-2310.06839.txt p.17 Figure 6  
  quote: `= 30x, high compression ratio setting) from NaturalQuestions`
- **LongLL-HW-1** (hardware) All experiments on a single Tesla V100 (32GB).  
  value: `Tesla V100 (32GB)` metric:  task:  conditions:   
  source: longllmlingua-2310.06839.txt p.13 Appendix B.2  
  quote: `All experiments were conducted using a Tesla V100 (32GB)`
- **LongLL-IO-1** (io) Target LLMs are GPT-3.5-Turbo-0613 (API) and LongChat-13B-16k (open weights, HuggingFace).  
  value: `` metric:  task:  conditions: target LLMs  
  source: longllmlingua-2310.06839.txt p.5 Sec. 5 Implementation details  
  quote: `and LongChat-13B-16k as the target LLMs, both accessible via OpenAI7 and HuggingFace8`
- **LongLL-IO-2** (io) Framework figure labels the target as black-box LLMs, with a small model doing the compression (text-to-text, inferred no target internals needed).  
  value: `` metric:  task:  conditions: inferred from mechanism  
  source: longllmlingua-2310.06839.txt p.3 Figure 2  
  quote: `Black-box LLMs`
- **LongLL-IO-3** (io) The compression depends on the question, so it must be redone per question and the context cannot be cached.  
  value: `` metric:  task:  conditions:   
  source: longllmlingua-2310.06839.txt p.9 Limitation  
  quote: `LongLLMLingua is a question-aware approach, meaning it requires re-compression for different questions, even with the same context, preventing caching of the context`
- **LongLL-IO-4** (io) GPT-3.5-Turbo-16k-0613 is used when the original prompt exceeds 4k tokens (other prompts use GPT-3.5-Turbo-0613).  
  value: `` metric:  task:  conditions: target LLM versions  
  source: longllmlingua-2310.06839.txt p.5 Footnote 6  
  quote: `we utilize GPT-3.5-Turbo-16k-0613`
- **LongLL-LAT-1** (latency_compute) Latency measured end to end on a V100-32G against API calls, using multi-document QA, LongBench and ZeroSCROLLS prompts.  
  value: `` metric:  task: NaturalQuestions, LongBench, ZeroSCROLLS conditions: V100-32G  
  source: longllmlingua-2310.06839.txt p.8 Latency evaluation  
  quote: `latency testing on a V100-32G, using the prompts from Multi-document QA, LongBench, and ZeroSCROLLS in the API call`
- **LongLL-LAT-2** (latency_compute) Latency includes compression time plus the LLM request time, averaged over multiple measurements; compressor-only overhead is not broken out.  
  value: `` metric: s task:  conditions:   
  source: longllmlingua-2310.06839.txt p.8 Latency evaluation  
  quote: `The latency includes the time cost for prompt compression and the request time for LLMs, with multiple measurements taken and averaged over`
- **LongLL-LAT-3** (latency_compute) Acceleration grows with compression ratio up to 2.6x; embedding-based and Selective-Context baselines are slower.  
  value: `2.6x` metric: speedup task:  conditions: V100-32G  
  source: longllmlingua-2310.06839.txt p.8 Latency evaluation  
  quote: `Moreover, with the compression ratio increasing, the acceleration effect becomes more pronounced up to 2.6x`
- **LongLL-LAT-4** (latency_compute) Authors state LongLLMLingua doubles compute relative to LLMLingua.  
  value: `twice` metric:  task:  conditions:   
  source: longllmlingua-2310.06839.txt p.9 Limitation  
  quote: `in terms of computational cost, LongLLMLingua increases the computation by twice as much as LLMLingua`
- **LongLL-LIM-1** (limitation) Official limitation 1: question-aware, so re-compression per question, no context caching; compute is twice LLMLingua.  
  value: `` metric:  task:  conditions:   
  source: longllmlingua-2310.06839.txt p.9 Limitation  
  quote: `LongLLMLingua is a question-aware approach, meaning it requires re-compression for different questions, even with the same context, preventing caching of the context`
- **LongLL-LIM-2** (limitation) Official limitation 2: effectiveness may drop when the relationship between context and prompt is complex and subtle, given the coarse question-aware step.  
  value: `` metric:  task:  conditions:   
  source: longllmlingua-2310.06839.txt p.9 Limitation  
  quote: `its effectiveness might be impacted when the relationship between context and prompt is more complex and subtle due to the coarse-level question-aware approach`
- **LongLL-LIM-3** (limitation) Token-level pruning corrupts entities (names, dates) in the compressed prompt; the LLM copies them wrongly, hence subsequence recovery.  
  value: `` metric:  task:  conditions:   
  source: longllmlingua-2310.06839.txt p.5 Sec. 4.4  
  quote: `Compressing these entities at the token level doesn't affect the LLMs' understanding of semantic content but can lead to errors in the generated content`
- **LongLL-LIM-4** (limitation) Qualitative failure/repair example: at 4x the compressed prompt makes the LLM answer a corrupted year; subsequence recovery fixes it.  
  value: `209 -> 2019` metric:  task: NaturalQuestions conditions: GPT-3.5-Turbo; 4x; Figure 7  
  source: longllmlingua-2310.06839.txt p.18 Figure 7  
  quote: `LLMs' Response: 209 LLMs' Response after Subsquence Recovery: 2019`
- **LongLL-LIM-5** (limitation) Code case study (LongBench lcc, 2,000 tokens): LLM response to the compressed code prompt.  
  value: `` metric:  task: LongBench lcc code completion conditions: GPT-3.5-Turbo; 2,000 tokens  
  source: longllmlingua-2310.06839.txt p.19 Figure 8  
  quote: `LLMs' Response: contact.setLastMessageTransmitted(query.getEnd());`
- **LongLL-LIM-6** (limitation) Same Figure 8 case: ground truth is wrapped in an if, which the response lacks.  
  value: `` metric:  task: LongBench lcc code completion conditions: GPT-3.5-Turbo; 2,000 tokens  
  source: longllmlingua-2310.06839.txt p.19 Figure 8  
  quote: `Ground Truth: if (contact.setLastMessageTransmitted(query.getEnd())) {`
- **LongLL-LIM-7** (limitation) Maximum compressor input length and how 24k-30k token LooGLE prompts are fed to the small LM are not stated; LooGLE prompts average over 24k tokens.  
  value: `24,005` metric: tokens task: LooGLE conditions:   
  source: longllmlingua-2310.06839.txt p.13 Appendix B.1  
  quote: `The average prompt token length in this benchmark stands at 24,005`
- **LongLL-MECH-1** (mechanism) LongLLMLingua uses LLMLingua as the backbone for compression (small-LM perplexity token pruning).  
  value: `` metric:  task:  conditions:   
  source: longllmlingua-2310.06839.txt p.1 Sec. 1  
  quote: `we use LLMLingua (Jiang et al., 2023a) as the backbone for prompt compression`
- **LongLL-MECH-10** (mechanism) GPT2-dolly stands in for GPT2-small in the small-LM ablation.  
  value: `` metric:  task:  conditions: ablation  
  source: longllmlingua-2310.06839.txt p.13 Appendix B.2  
  quote: `We use the GPT2-dolly18 as the small language model in w/ GPT2-small ablation experiments`
- **LongLL-MECH-11** (mechanism) Reordering is applied only in the NaturalQuestions experiments and flagged in Table 1.  
  value: `` metric:  task: NaturalQuestions conditions:   
  source: longllmlingua-2310.06839.txt p.13 Appendix B.2  
  quote: `we only used reordering in the NaturalQuestions Multi-document QA and noted this in Table 1`
- **LongLL-MECH-12** (mechanism) Same pre-defined light compression rates for instruction (0.85) and question (0.9) as LLMLingua: they are lightly compressed, not preserved verbatim.  
  value: `0.85; 0.9` metric: compression rate tau task:  conditions:   
  source: longllmlingua-2310.06839.txt p.13 Appendix B.2  
  quote: `pre-defined compression rates ins = 0.85 and que = 0.9 for instructions and questions`
- **LongLL-MECH-13** (mechanism) Segment size for iterative token-level compression is 200.  
  value: `200` metric: tokens task:  conditions:   
  source: longllmlingua-2310.06839.txt p.13 Appendix B.2  
  quote: `segment size used in the iterative token-level compression is set to 200`
- **LongLL-MECH-14** (mechanism) Background statement that LLMLingua fine-tunes its small LM on target-LLM data; the paper does not say whether this alignment was applied in the LongLLMLingua experiments.  
  value: `` metric:  task:  conditions: ambiguous  
  source: longllmlingua-2310.06839.txt p.2 Sec. 3  
  quote: `To aware different target LLMs, LLMLingua fine-tunes MS using data from the target LLM`
- **LongLL-MECH-15** (mechanism) In LongLLMLingua's comparison, the LLMLingua and Selective-Context baselines also use LLaMA-2-7B-Chat as the small LM (not the Alpaca-7B/GPT2-Alpaca of the original LLMLingua paper).  
  value: `` metric:  task:  conditions: baseline compressor model  
  source: longllmlingua-2310.06839.txt p.6 Sec. 5 Baselines  
  quote: `Both methods employ LLaMA-2-7B-Chat as the small language model for compression`
- **LongLL-MECH-2** (mechanism) Contribution 1: question-aware coarse-to-fine compression.  
  value: `` metric:  task:  conditions:   
  source: longllmlingua-2310.06839.txt p.1 Sec. 1  
  quote: `propose a question-aware coarse-to-fine compression method to improve the key information density in the prompt`
- **LongLL-MECH-3** (mechanism) Contribution 2: document reordering to reduce position bias.  
  value: `` metric:  task:  conditions:   
  source: longllmlingua-2310.06839.txt p.1 Sec. 1  
  quote: `a document reordering strategy to minimize position bias in LLMs`
- **LongLL-MECH-4** (mechanism) Contribution 3: dynamic compression ratios between coarse and fine levels.  
  value: `` metric:  task:  conditions:   
  source: longllmlingua-2310.06839.txt p.1 Sec. 1  
  quote: `dynamic compression ratios for precise control between coarse and fine compression levels`
- **LongLL-MECH-5** (mechanism) Coarse step scores documents by the perplexity of the question given each document, with an appended restrictive statement.  
  value: `` metric:  task:  conditions:   
  source: longllmlingua-2310.06839.txt p.3 Sec. 4.1  
  quote: `We also append a restrictive statement`
- **LongLL-MECH-6** (mechanism) Fine step uses contrastive perplexity (distribution shift caused by conditioning on the question) as token importance.  
  value: `` metric:  task:  conditions:   
  source: longllmlingua-2310.06839.txt p.4 Sec. 4.1  
  quote: `we propose contrastive perplexity, i.e., the distribution shift caused by the condition of the question, to represent the association between the token and the question`
- **LongLL-MECH-7** (mechanism) Retained documents are reordered by importance score.  
  value: `` metric:  task:  conditions:   
  source: longllmlingua-2310.06839.txt p.4 Sec. 4.2  
  quote: `we reorder documents using their importance scores to better leverage LLMs' information perception difference in positions`
- **LongLL-MECH-8** (mechanism) Subsequence recovery maps entities in the LLM response back to the original prompt text.  
  value: `` metric:  task:  conditions:   
  source: longllmlingua-2310.06839.txt p.5 Sec. 4.4  
  quote: `we propose a subsequence recovery method to restore the original content in LLMs' responses`
- **LongLL-MECH-9** (mechanism) Compressor LM is LLaMA-2-7B-Chat (aligned by SFT and RLHF); no separate training of the compressor is described for the main results.  
  value: `` metric:  task:  conditions: compressor model  
  source: longllmlingua-2310.06839.txt p.6 Sec. 5 Implementation details  
  quote: `we apply LLaMA-2-7B-Chat9, which has been aligned by supervised fine-tuning and RLHF`
- **LongLL-POS-1** (context_loss) Original-prompt accuracy is highest when the answer is at the beginning and degrades in the middle (lost in the middle).  
  value: `` metric:  task: NaturalQuestions conditions: GPT-3.5-Turbo original prompt  
  source: longllmlingua-2310.06839.txt p.4 Sec. 4.2  
  quote: `LLM achieves the highest performance when relevant information occurs at the beginning and significantly degrades if relevant information is located in the middle of long contexts`
- **LongLL-POS-2** (context_loss) Figure 1b caption: relevant-information position matters; reordering is introduced to reduce loss in the middle.  
  value: `` metric:  task: NaturalQuestions conditions:   
  source: longllmlingua-2310.06839.txt p.2 Figure 1 caption  
  quote: `LLMs' ability to capture the relevant information depends on their positions in the prompt`
- **LongLL-POS-3** (context_loss) Table 3: with document reordering (2x), accuracy is the same at every answer position.  
  value: `76.2 at all five positions` metric: accuracy task: NaturalQuestions conditions: GPT-3.5-Turbo; 2x  
  source: longllmlingua-2310.06839.txt p.8 Table 3  
  quote: `- w/ Document Reordering 76.2 76.2 76.2 76.2 76.2`
- **LongLL-REP-1** (reproducibility) Code release stated in paper.  
  value: `` metric:  task:  conditions:   
  source: longllmlingua-2310.06839.txt p.1 Footnote 1  
  quote: `Access our code at https://aka.ms/LongLLMLingua`
- **LongLL-REP-2** (reproducibility) Official repo (shared with LLMLingua) is MIT-licensed.  
  value: `MIT` metric:  task:  conditions:   
  source: https://raw.githubusercontent.com/microsoft/LLMLingua/main/LICENSE LICENSE  
  quote: `MIT License Copyright (c) Microsoft Corporation.`
- **LongLL-REP-3** (reproducibility) Official repo README shows a LongLLMLingua quick-start snippet in the same llmlingua package.  
  value: `` metric:  task:  conditions:   
  source: https://github.com/microsoft/LLMLingua README  
  quote: `To try LongLLMLingua in your scenarios, you can use.`
- **LongLL-REP-4** (reproducibility) Compressor is an existing public chat model (LLaMA-2-7B-Chat, linked to ai.meta.com/llama); its license is not discussed in the paper.  
  value: `` metric:  task:  conditions:   
  source: longllmlingua-2310.06839.txt p.6 Sec. 5 footnote 9  
  quote: `https://ai.meta.com/llama/`
- **LongLL-TASK-1** (tasks_tested) Dataset list: NaturalQuestions, LongBench, ZeroSCROLLS, MuSiQue, LooGLE.  
  value: `` metric:  task: long-document QA/RAG conditions:   
  source: longllmlingua-2310.06839.txt p.2 Sec. 1 contributions  
  quote: `We evaluate LongLLMLingua across five benchmarks, i.e., NaturalQuestions (Liu et al., 2024), LongBench (Bai et al., 2023), ZeroSCROLLS`
- **LongLL-TASK-2** (tasks_tested) NaturalQuestions 20-doc setup is described as a realistic retrieval-augmented generation setup (2,655 problems).  
  value: `2,655` metric: problems task: NaturalQuestions multi-doc QA conditions:   
  source: longllmlingua-2310.06839.txt p.12 Appendix B.1  
  quote: `This dataset provides a realistic retrieval-augmented generation setup`
- **LongLL-TASK-3** (tasks_tested) Coding and summarization are covered inside LongBench/ZeroSCROLLS (code completion, document summarization named among long-context scenarios).  
  value: `` metric:  task: coding (LongBench Code, lcc); summarization (LongBench Summ., ZeroSCROLLS) conditions:   
  source: longllmlingua-2310.06839.txt p.1 Sec. 1  
  quote: `Scenarios such as multi-document question answering, code completion, and document summarization also necessitate the processing of long contexts`
- **LongLL-TASK-4** (tasks_tested) Multi-turn chat: not in the dataset list.  
  value: `not tested in paper` metric:  task: multi-turn chat conditions:   
  source: longllmlingua-2310.06839.txt p.2 Sec. 1 contributions  
  quote: `We evaluate LongLLMLingua across five benchmarks, i.e., NaturalQuestions (Liu et al., 2024), LongBench (Bai et al., 2023), ZeroSCROLLS`
- **LongLL-TASK-5** (tasks_tested) Structured data (JSON/tables/logs): not in the dataset list.  
  value: `not tested in paper` metric:  task: structured data conditions:   
  source: longllmlingua-2310.06839.txt p.2 Sec. 1 contributions  
  quote: `We evaluate LongLLMLingua across five benchmarks, i.e., NaturalQuestions (Liu et al., 2024), LongBench (Bai et al., 2023), ZeroSCROLLS`
- **LongLL-TASK-6** (tasks_tested) Math reasoning: no math benchmark in the list (multi-hop QA via MuSiQue is the closest).  
  value: `not tested in paper` metric:  task: reasoning/math conditions:   
  source: longllmlingua-2310.06839.txt p.2 Sec. 1 contributions  
  quote: `We evaluate LongLLMLingua across five benchmarks, i.e., NaturalQuestions (Liu et al., 2024), LongBench (Bai et al., 2023), ZeroSCROLLS`
- **LongLL-TASK-7** (tasks_tested) Sensitive/PII content: not in the dataset list.  
  value: `not tested in paper` metric:  task: sensitive/PII conditions:   
  source: longllmlingua-2310.06839.txt p.2 Sec. 1 contributions  
  quote: `We evaluate LongLLMLingua across five benchmarks, i.e., NaturalQuestions (Liu et al., 2024), LongBench (Bai et al., 2023), ZeroSCROLLS`

## RateDistortion

- **RD-01** (mechanism) The paper's framework covers only token-level methods that output hard prompts for black-box models; it is a theory/benchmark framework, not a compressor.  
  value: `` metric:  task:  conditions:   
  source: rate-distortion-framework.txt p.1 Abstract  
  quote: `present a framework to unify token-level prompt compression methods which create hard prompts for black-box models`
- **RD-02** (mechanism) Soft-prompt (embedding-vector) methods are explicitly excluded because they are not transferable to black-box models.  
  value: `` metric:  task:  conditions:   
  source: rate-distortion-framework.txt p.3 Sec. 1  
  quote: `exclude methods which output embedding vectors`
- **RD-03** (mechanism) The paper asserts that all prompt compression methods in the literature work by pruning tokens (non-generative, order-preserving). Inference: abstractive compressors such as SCOPE, which rewrite text, fall outside this assumption.  
  value: `` metric:  task:  conditions:   
  source: rate-distortion-framework.txt p.17 Sec. 4.2.2  
  quote: `all prompt compression methods in the literature work by pruning tokens`
- **RD-04** (mechanism) The paper treats compressed prompts as needing to be interpretable only by the LLM, not human-readable, contrasting with text summarization.  
  value: `` metric:  task:  conditions:   
  source: rate-distortion-framework.txt p.4 Sec. 2  
  quote: `prompt compression has the advantage that the compressed prompt is not required to be human-readable`
- **RD-05** (io) Black-box framing: prompt compression is the only technique available for lowering cost of black-box API calls to closed-source models.  
  value: `` metric:  task:  conditions:   
  source: rate-distortion-framework.txt p.3 Sec. 1  
  quote: `it is the only technique available when seeking to lower costs for black-box API calls to closed-source models`
- **RD-06** (io) In the experiments the target LLM is Mistral 7B Instruct v0.2, kept fixed and inaccessible to the compressors (a simulated black box, not an API model).  
  value: `Mistral 7B Instruct v0.2` metric:  task:  conditions: only one target LLM  
  source: rate-distortion-framework.txt p.15 Sec. 4.1 Models  
  quote: `Critically, this model is fixed after fine-tuning and no prompt compression methods have access to any part of it.`
- **RD-07** (mechanism) Query-aware compression means the compressor also receives the query; query-agnostic means it receives only the prompt.  
  value: `` metric:  task:  conditions:   
  source: rate-distortion-framework.txt p.7 Sec. 3.1  
  quote: `with the difference being that the compressor also has access to the query`
- **RD-08** (mechanism) The framework assumes a query is always supplied alongside the compressed prompt, matching the LLMLingua/LongLLMLingua setting.  
  value: `` metric:  task:  conditions:   
  source: rate-distortion-framework.txt p.5 Sec. 2  
  quote: `We offer a framework for hard-prompt compression methods where we assume that a query is provided in addition to the compressed prompt`
- **RD-09** (tasks_tested) Compressors actually evaluated: Selective Context, LLMLingua, 'LLMLingua Query' (the query-aware extension, cited as [JWL+23] = LongLLMLingua) and LLMLingua-2, plus the authors' QuerySelect and Adaptive QuerySelect. CPC and SCOPE are not evaluated.  
  value: `` metric:  task:  conditions:   
  source: rate-distortion-framework.txt p.14 Sec. 4.1 Baseline methods  
  quote: `Selective Context [LDLG23], LLMLingua [JWLYQ23], LLMLingua Query [JWL+23], LLMLingua-2 [PWJ+24]`
- **RD-10** (tasks_tested) 'LLMLingua Query' is the query-aware extension of LLMLingua used as the query-aware baseline.  
  value: `` metric:  task:  conditions:   
  source: rate-distortion-framework.txt p.14 Sec. 4.1 Baseline methods  
  quote: `They later extended their method to perform query- aware compression, which is what we use for LLMLingua Query`
- **RD-11** (tasks_tested) Soft-prompt methods (Gist Tokens, ICAE, AutoCompressor) are not evaluated.  
  value: `not tested in paper` metric:  task:  conditions:   
  source: rate-distortion-framework.txt p.14 Sec. 4.1  
  quote: `we do not consider methods like Gist Tokens`
- **RD-12** (tasks_tested) Datasets and metrics: log loss and 0/1 loss for the synthetic set; RougeL and BertScore for natural-language sets.  
  value: `` metric: log loss; 0/1 loss; RougeL; BertScore task: synthetic binary; small NL; NarrativeQA conditions:   
  source: rate-distortion-framework.txt p.13 Sec. 4  
  quote: `We report our results with the log loss and 0/1 loss metrics (defined in (1)) for the synthetic dataset`
- **RD-13** (tasks_tested) Synthetic dataset: binary prompts whose length ranges between the printed minimum and maximum (four and ten tokens).  
  value: `four and ten` metric:  task: synthetic binary strings conditions:   
  source: rate-distortion-framework.txt p.14 Sec. 4.1 Dataset  
  quote: `the minimum and maximum possible lengths for each prompt are four and ten, respectively`
- **RD-14** (tasks_tested) Validation set size for the synthetic experiment.  
  value: `1400 examples` metric:  task: synthetic binary strings conditions: 7 queries, 200 examples per query  
  source: rate-distortion-framework.txt p.14 Sec. 4.1 Dataset  
  quote: `All methods are evaluated on a validation set of 1400 examples in total (7 queries, 200 examples per query)`
- **RD-15** (tasks_tested) Small natural-language dataset: only ten GPT-4-written prompts with four queries each (prompt length in RD-55).  
  value: `ten prompts; four queries each` metric:  task: small NL dataset conditions:   
  source: rate-distortion-framework.txt p.18 Sec. 4.2.2  
  quote: `consisting of ten prompts and four queries for each prompt`
- **RD-16** (tasks_tested) NarrativeQA experiment uses dataset summaries (hundreds of tokens, about 3,500 samples) as prompts; this is the only larger natural-language test, and the optimum is only approximated by beam search.  
  value: `about 3,500 samples` metric: RougeL; BertScore task: NarrativeQA summaries conditions:   
  source: rate-distortion-framework.txt p.41 App. D.2  
  quote: `Since the sizes of the prompts are hundreds of tokens and approximately 3,500 samples`
- **RD-17** (tasks_tested) The synthetic queries (count, parity, palindrome) are bit-string computations, not math/reasoning benchmarks; coding, chat, structured data, summarization benchmarks and PII content are not tested.  
  value: `not tested in paper` metric:  task:  conditions:   
  source: rate-distortion-framework.txt p.14 Sec. 4.1 Dataset  
  quote: `such as "Count the number of 1s," "Compute the parity," and "Is the binary string a palindrome?"`
- **RD-18** (context_loss) Headline result (Fig. 1, synthetic binary prompts, sizes in RD-13): most existing methods are far from the theoretical limit; the figure curves have no numeric values printed in the text.  
  value: `` metric: log loss; 0/1 loss task: synthetic binary prompts conditions: target Mistral 7B Instruct v0.2 fine-tuned; all compressors fine-tuned on the synthetic training split; rate = len(M)/len(X) from 0 to 1  
  source: rate-distortion-framework.txt p.4 Figure 1 caption  
  quote: `We observe that (1) most existing methods are far from the theoretical limit, suggesting that there is still room for improvement in this field`
- **RD-19** (context_loss) In Fig. 1 only the authors' Adaptive QuerySelect (not an existing method) beats the optimal query-agnostic curve; by implication LLMLingua, LLMLingua-2 and Selective Context do not on the synthetic set.  
  value: `` metric: log loss; 0/1 loss task: synthetic binary prompts conditions: Adaptive QuerySelect = query-aware, variable-rate LLMLingua-2 adaptation  
  source: rate-distortion-framework.txt p.4 Figure 1 caption  
  quote: `achieves the best performance among all methods considered, and is the only method to outperform the optimal query-agnostic strategy`
- **RD-20** (context_loss) Query conditioning matters: query-aware QuerySelect beats query-agnostic LLMLingua-2 in Fig. 1.  
  value: `` metric: log loss; 0/1 loss task: synthetic binary prompts conditions:   
  source: rate-distortion-framework.txt p.4 Figure 1 caption  
  quote: `conditioning on the query allows for a significant improvement`
- **RD-21** (context_loss) Important caveat: every compressor was fine-tuned on the synthetic training split before evaluation (not off-the-shelf).  
  value: `` metric:  task: synthetic binary prompts conditions:   
  source: rate-distortion-framework.txt p.15 Sec. 4.1 Models  
  quote: `For each method, we finetune on the training set partition to enable the best performance possible for that method.`
- **RD-22** (context_loss) The query-aware LongLLMLingua-style variant ('LLMLingua Query') showed mixed performance versus vanilla LLMLingua on the synthetic data.  
  value: `` metric:  task: synthetic binary prompts conditions:   
  source: rate-distortion-framework.txt p.16 Sec. 4.2.1  
  quote: `An exception here is the performance of LLMLingua Query, which we find has mixed performance compared to vanilla LLMLingua`
- **RD-23** (context_loss) Optimal curves eventually fall below the no-compression baseline, i.e. compression can in principle improve task performance.  
  value: `` metric:  task: synthetic binary prompts conditions:   
  source: rate-distortion-framework.txt p.15 Sec. 4.2.1  
  quote: `the optimal distortion-rate curves eventually fall below the baseline performance of using the full prompt (no compression)`
- **RD-24** (context_loss) Small NL dataset (Fig. 6): large gap between all algorithms and the optimal strategies.  
  value: `` metric: 1 - RougeL; 1 - BertScore task: small NL dataset (10 prompts, 40 queries) conditions: Mistral 7B Instruct v0.2; 10 prompts x 4 queries; existing methods use published HF compressor checkpoints per App. C.3.2  
  source: rate-distortion-framework.txt p.18 Sec. 4.2.2  
  quote: `However, the gap between all algorithms and the optimal strategies is significant.`
- **RD-25** (context_loss) The optimal strategies can reach much lower distortion with roughly 70% (query-aware) and 40% (query-agnostic) fewer tokens, on the 10-prompt dataset (prompt length in RD-55).  
  value: `70%; 40%` metric: fewer tokens at lower distortion task: small NL dataset conditions: optimal query-aware / query-agnostic bound  
  source: rate-distortion-framework.txt p.18 Sec. 4.2.2  
  quote: `much lower distortion can be achieved in roughly 70% and 40% fewer tokens for the query-aware and query-agnostic cases, respectively`
- **RD-26** (context_loss) On the small NL set, only LLMLingua-2-based methods (which include the authors' QuerySelect variants) beat no-compression, and only at higher rates; Selective Context and LLMLingua do not.  
  value: `` metric: 1 - RougeL; 1 - BertScore task: small NL dataset conditions:   
  source: rate-distortion-framework.txt p.18 Sec. 4.2.2  
  quote: `LLMLingua-2 methods are the only methods that achieve lower distortion than the no compression result, albeit for higher rates.`
- **RD-27** (context_loss) On NarrativeQA, LLMLingua-2-based methods can outperform the query-agnostic beam-search upper bound at most rates, so the 'optimum' there is only a loose upper bound.  
  value: `` metric: 1 - RougeL task: NarrativeQA conditions: beam search C = 4000, B = 5  
  source: rate-distortion-framework.txt p.20 Sec. 4.2.3  
  quote: `Although LLMLingua-2-based methods can outperform the upper bound in the query-agnostic case for most rates`
- **RD-28** (context_loss) On NarrativeQA the gap between existing methods and the query-aware bound is large, even for methods that use the query.  
  value: `` metric: 1 - RougeL task: NarrativeQA conditions: beam search C = 4000, B = 5  
  source: rate-distortion-framework.txt p.20 Sec. 4.2.3  
  quote: `Impressively, the gap between existing methods and the query-aware case is quite large, even for the methods that use the query to compress the prompt.`
- **RD-29** (context_loss) Beam-search budget used for the NarrativeQA bound.  
  value: `C = 4000; B = 5` metric:  task: NarrativeQA conditions:   
  source: rate-distortion-framework.txt p.20 Sec. 4.2.3  
  quote: `Fig. 7 compares existing methods to our beam search upper bounds for C = 4000 and B = 5.`
- **RD-30** (context_loss) On NarrativeQA the authors' query-aware methods are better below rate 0.5 and only 'competitive' above it.  
  value: `0.5` metric: RougeL; BertScore task: NarrativeQA conditions: rate = len(M)/len(X)  
  source: rate-distortion-framework.txt p.41 App. D.2  
  quote: `our proposed methods are better for rates less than 0.5 and remain competitive for rates about 0.5.`
- **RD-31** (compression_ratio) Rate grid swept for each method: r from 0.04 to 1.0; the realised average rate can differ from r.  
  value: `0.04 ... 1.0` metric: rate task: synthetic conditions:   
  source: rate-distortion-framework.txt p.30 App. C.1  
  quote: `{0.04, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 0.96, 0.99, 1.0} in our experiments`
- **RD-32** (latency_compute) Table 6 header: average time to compress a single prompt, in seconds, for NarrativeQA and the small NLP dataset; the hardware for this table is not specified.  
  value: `` metric: seconds per prompt task: NarrativeQA; small NLP dataset conditions: hardware not specified for this table  
  source: rate-distortion-framework.txt p.42 Table 6  
  quote: `Table 6: Average time required to compress a single prompt (seconds).`
- **RD-33** (latency_compute) Selective Context: 1.043 s per NarrativeQA prompt, 0.049 s on the small set.  
  value: `1.043; 0.049` metric: seconds per prompt task: NarrativeQA; small NLP dataset conditions:   
  source: rate-distortion-framework.txt p.42 Table 6  
  quote: `Selective 1.043 0.049`
- **RD-34** (latency_compute) LLMLingua: 0.510 s (NarrativeQA), 0.273 s (small set).  
  value: `0.510; 0.273` metric: seconds per prompt task: NarrativeQA; small NLP dataset conditions:   
  source: rate-distortion-framework.txt p.42 Table 6  
  quote: `LLMLingua 0.510 0.273`
- **RD-35** (latency_compute) LLMLingua Query (query-aware extension): 1.060 s (NarrativeQA), 0.530 s (small set).  
  value: `1.060; 0.530` metric: seconds per prompt task: NarrativeQA; small NLP dataset conditions:   
  source: rate-distortion-framework.txt p.42 Table 6  
  quote: `LLMLingua Query 1.060 0.530`
- **RD-36** (latency_compute) LLMLingua-2: 0.113 s (NarrativeQA), 0.044 s (small set); the authors' QuerySelect variants share the same timings.  
  value: `0.113; 0.044` metric: seconds per prompt task: NarrativeQA; small NLP dataset conditions:   
  source: rate-distortion-framework.txt p.42 Table 6  
  quote: `LLMLingua-2 0.113 0.044`
- **RD-37** (hardware) One of the machines used: a DGX with 4x 80GB A100 GPUs and a 64-core EPYC CPU; other machines are workstations with RTX 4090 GPUs (App. C.1).  
  value: `` metric:  task:  conditions:   
  source: rate-distortion-framework.txt p.30 App. C.1  
  quote: `AMD EPYC 7742 64-Core Processor, 512 GB of system RAM, and 4x 80GB SMX4 A100 GPUs`
- **RD-38** (latency_compute) Training cost of the authors' query-aware compressor: 1 to 2 hours and 30 GB VRAM on a single A100 (XLM RoBERTa Large, full fine-tune).  
  value: `1 to 2 hours; 30 GB` metric:  task:  conditions:   
  source: rate-distortion-framework.txt p.31 App. C.2  
  quote: `training took one to two hours and 30 GB of VRAM on a single A100`
- **RD-39** (mechanism) The distortion-rate function is a linear program solved efficiently via its dual; the paper calls the LP simple from an optimization perspective.  
  value: `` metric:  task:  conditions:   
  source: rate-distortion-framework.txt p.8 Sec. 3.2  
  quote: `the optimization problem is simply a linear program, which is simple from an optimization perspective`
- **RD-40** (cost) Where the exponential cost comes from: to compute D_x the algorithm needs one target-LLM inference call per possible compressed prompt of a given prompt and query.  
  value: `` metric:  task:  conditions: cost of computing the theoretical benchmark, not of running a compressor  
  source: rate-distortion-framework.txt p.17 Sec. 4.2.2  
  quote: `We require one inference call for each possible compressed prompt`
- **RD-41** (cost) Unrestricted candidate set is enormous (vocabulary 32,000), so only tiny prompts are tractable.  
  value: `|V| = 32,000` metric:  task:  conditions:   
  source: rate-distortion-framework.txt p.17 Sec. 4.2.2  
  quote: `Clearly, it is then virtually impossible to consider prompts with more than 2 tokens`
- **RD-42** (cost) Restricting to pruned prompts gives |M_x| = 2^len(x) candidates (printed '2len(x)'), independent of vocabulary size.  
  value: `2^len(x)` metric:  task:  conditions: pruning-only candidate set  
  source: rate-distortion-framework.txt p.17 Sec. 4.2.2  
  quote: `Then, we have |Mx| = 2len(x), irrespective of the vocabulary size |V|.`
- **RD-43** (cost) For prompts of a few hundred or thousand tokens even 2^len(x) calls are impractical, so exact optimal curves are intractable at that scale.  
  value: `` metric:  task:  conditions:   
  source: rate-distortion-framework.txt p.19 Sec. 4.2.3  
  quote: `However, when len(x) is a few hundred or thousand, as is the case for large-scale datasets, 2len(x) is far too many inference calls to make Dx to be practical.`
- **RD-44** (cost) The paper uses beam search, giving an upper bound on the optimum rather than the optimum; cost O(B N^2) nodes, still large.  
  value: `O(BN^2)` metric:  task:  conditions:   
  source: rate-distortion-framework.txt p.19 Sec. 4.2.3  
  quote: `When N is large, checking O(BN2) nodes is a drastic reduction over checking 2N nodes, but the growth rate is still too large.`
- **RD-45** (cost) Example in the paper: beam search on one 100-token prompt needs on the order of 10^6 target-LLM calls, about 11.5 days at one second per call.  
  value: `10^6 calls; 11.5 days` metric:  task:  conditions: one inference call = 1 second assumed  
  source: rate-distortion-framework.txt p.19 Sec. 4.2.3  
  quote: `single prompt of just 100 tokens will require on the order of 106 LLM inference calls, or roughly 11.5`
- **RD-46** (limitation) NP-hardness is not discussed anywhere in the paper; the formal results are an LP formulation and an efficient dual algorithm. Reported as 'not reported'.  
  value: `not reported` metric:  task:  conditions:   
  source: rate-distortion-framework.txt p.8 Sec. 3.2  
  quote: `Hence, the optimization problem is simply a linear program`
- **RD-47** (limitation) The authors list only one future-work item: studying their method exhaustively on natural-language datasets.  
  value: `` metric:  task:  conditions:   
  source: rate-distortion-framework.txt p.20 Sec. 5  
  quote: `As future work, it is important to exhaustively study our proposed method on natural language datasets.`
- **RD-48** (limitation) Natural-language prompts of the same 4-10 token length as the synthetic set are hard to find, which is why binary prompts were used for exact results.  
  value: `` metric:  task:  conditions:   
  source: rate-distortion-framework.txt p.18 Sec. 4.2.2  
  quote: `it is difficult to identify sufficiently rich natural language prompts of such short lengths for which compression is a reasonable problem`
- **RD-49** (limitation) Distortion metric choice is called an open problem: no metric that matches human notion of 'same meaning' is known; the paper uses RougeL and BertScore.  
  value: `` metric:  task:  conditions:   
  source: rate-distortion-framework.txt p.31 App. C.2.2  
  quote: `This is a crucial open problem not just for our work but also for the fair benchmarking of LLMs in general.`
- **RD-50** (limitation) Gap analysis for natural language: authors attribute the larger gap partly to noisy GPT-4-generated labels for LLMLingua-2-based methods.  
  value: `` metric:  task: small NL dataset conditions:   
  source: rate-distortion-framework.txt p.18 Sec. 4.2.2  
  quote: `We posit the quality of the training data for LLMLingua-2-based methods accounts for the discrepancy`
- **RD-51** (reproducibility) Authors' code release URL.  
  value: `` metric:  task:  conditions:   
  source: rate-distortion-framework.txt p.14 Footnote 1  
  quote: `Our code is available at https://github.com/acnagle/fundamental-limits`
- **RD-52** (reproducibility) Existing-method code used by the authors (LLMLingua, Selective Context repos) is MIT-licensed per the paper; the license of the authors' own repo is covered in the notes file.  
  value: `MIT (third-party code)` metric:  task:  conditions:   
  source: rate-distortion-framework.txt p.30 App. C.1  
  quote: `We use code from the LLMLingua and Selective Context GitHub repos, which are released under the MIT license.`
- **RD-53** (reproducibility) Authors' repo README says QuerySelect weights are on Hugging Face (WebFetch of raw README).  
  value: `` metric:  task:  conditions:   
  source: https://raw.githubusercontent.com/acnagle/fundamental-limits/main/README.md README  
  quote: `the model weights are available on`
- **RD-54** (limitation) CPC and SCOPE (sentence-/chunk-level and generative compressors) are outside the framework: the paper's own scope statement limits it to token-level hard-prompt methods.  
  value: `not tested in paper` metric:  task:  conditions:   
  source: rate-distortion-framework.txt p.1 Abstract  
  quote: `present a framework to unify token-level prompt compression methods which create hard prompts for black-box models`
- **RD-55** (tasks_tested) The largest prompt in the small natural-language dataset is 15 tokens.  
  value: `15 tokens` metric:  task: small NL dataset conditions:   
  source: rate-distortion-framework.txt p.19 Sec. 4.2.3  
  quote: `whose largest prompt consists of 15 tokens`
- **RD-56** (context_loss) On the small NL set the authors' own query-aware methods (QuerySelect, Adaptive QuerySelect) give the lowest distortion among the compared algorithms at low rates (i.e. high compression); existing methods are not best there.  
  value: `` metric: 1 - RougeL; 1 - BertScore task: small NL dataset conditions: low rates = high compression  
  source: rate-distortion-framework.txt p.18 Sec. 4.2.2  
  quote: `achieve the lowest distortion among all other prompt compression algorithms for low rates`
- **RD-57** (context_loss) Even query-aware methods are far from the query-agnostic optimal strategy on the small NL set.  
  value: `` metric: 1 - RougeL; 1 - BertScore task: small NL dataset conditions:   
  source: rate-distortion-framework.txt p.18 Sec. 4.2.2  
  quote: `Surprisingly, even the gap between the query-aware prompt compression methods and the query-agnostic optimal strategy is quite large.`
- **RD-58** (compression_ratio) The paper's 'rate' is the expected ratio of compressed to original length (so rate 0.5 means half the tokens kept, and lower rate means more compression); it is a fraction, not an 'Nx' ratio.  
  value: `` metric: rate task:  conditions:   
  source: rate-distortion-framework.txt p.7 Sec. 3.1  
  quote: `(1) the rate E len(M) len(X) , to measure how much the prompt is compressed`

## SCOPE

- **SCP-01** (mechanism) SCOPE is a training-free generative compressor that splits the prompt into chunks and rewrites each chunk with a summarization model.  
  value: `` metric:  task:  conditions: query-agnostic (see SCP-05)  
  source: scope-2508.15813.txt p.1 Abstract  
  quote: `we propose SCOPE, a training-free generative prompt compression framework based on chunk-level rewriting`
- **SCP-02** (mechanism) A small pre-trained summarization model (BART given as example) is used instead of an LLM.  
  value: `` metric:  task:  conditions:   
  source: scope-2508.15813.txt p.1 Sec. 1  
  quote: `a smaller summarization model (e.g., BART (Lewis et al. (2019))) is chosen`
- **SCP-03** (mechanism) No additional training: compression uses lightweight pre-trained embedding and summarization models without invoking large LLMs.  
  value: `` metric:  task:  conditions:   
  source: scope-2508.15813.txt p.2 Sec. 1  
  quote: `requires no additional training and performs compression using lightweight pretrained embedding and summarization models, without invoking large LLMs during compression`
- **SCP-04** (mechanism) The default summarization model is bart-large-cnn, and the paper says the summarizer can be varied; no parameter count is given.  
  value: `bart-large-cnn` metric:  task:  conditions: model sizes not reported  
  source: scope-2508.15813.txt p.6 Sec. 4  
  quote: `The summarization model can be vary (e.g., bart-large-cnn)`
- **SCP-05** (mechanism) Algorithm 1 takes only the text and a compression ratio as input (no question), so compression is query-agnostic.  
  value: `` metric:  task:  conditions: query-agnostic (inferred from Algorithm 1 inputs)  
  source: scope-2508.15813.txt p.4 Algorithm 1  
  quote: `Input: text string essay, compression ratio`
- **SCP-06** (mechanism) Chunk relevance is the cosine similarity of each chunk to an embedding of the full context, not to a question.  
  value: `` metric:  task:  conditions: query-agnostic  
  source: scope-2508.15813.txt p.5 Sec. 3.3.1  
  quote: `Chunk relevance is then calculated using cosine similarity with this representation`
- **SCP-07** (mechanism) In QA evaluation the context is compressed before the question is used, confirming the compressor does not see the question.  
  value: `` metric:  task: Trivia-QA, MultiFieldQA-en conditions:   
  source: scope-2508.15813.txt p.7 Sec. 4.1  
  quote: `In this task, context is first compressed by a compression method, then fed to downstream LLM to generate answers`
- **SCP-08** (mechanism) The paper says per-chunk ratios are chosen so the overall ratio is only guaranteed to be 'close to the target' (not exact).  
  value: `` metric:  task:  conditions:   
  source: scope-2508.15813.txt p.5 Sec. 3.3.1  
  quote: `squeezing enough to guarantee the overall ratio close to the target`
- **SCP-09** (mechanism) Keywords are extracted by NER and numeric/date expressions by rule-based matching and are forced into the summaries.  
  value: `` metric:  task:  conditions:   
  source: scope-2508.15813.txt p.6 Sec. 4  
  quote: `numerical and date expressions additionally preserved through rule-based matching`
- **SCP-10** (mechanism) Two variants: SCOPE_D preserves head and tail tokens (128 and 256) and SCOPE_N compresses everything.  
  value: `128; 256` metric: tokens task:  conditions:   
  source: scope-2508.15813.txt p.4 Sec. 3  
  quote: `we preserve head and tail tokens (128 and 256 respectively)`
- **SCP-11** (mechanism) Each chunk is rewritten by a generative summarization model told to produce a summary of a given length, so the output is generated text, not a subset of original tokens.  
  value: `` metric:  task:  conditions:   
  source: scope-2508.15813.txt p.6 Sec. 3.3.2  
  quote: `SCOPE instructs the model (like BART) to generate a summary of the given chunk`
- **SCP-12** (io) All main results use GPT-4o-mini (an API model) as downstream LLM, and Qwen-2.5 for secondary tests; the compressor needs no access to the target model (inferred from mechanism).  
  value: `` metric:  task:  conditions: target LLM GPT-4o-mini (default); Qwen-2.5  
  source: scope-2508.15813.txt p.7 Sec. 4.1  
  quote: `Without explicit notation, all baselines and our method are using GPT-4o-mini as the downstream LLM`
- **SCP-13** (compression_ratio) Compression ratio is defined as uncompressed length over compressed length; the ratios evaluated are 5x, 3x and 2x only.  
  value: `5x; 3x; 2x` metric:  task: summarization, QA conditions:   
  source: scope-2508.15813.txt p.8 Sec. 4.2  
  quote: `under various compression ratios (5x, 3x, and 2x)`
- **SCP-14** (compression_ratio) Definition of the reported compression ratio (target ratio, not measured post-hoc ratio; actual compressed lengths are not tabulated).  
  value: `` metric:  task:  conditions:   
  source: scope-2508.15813.txt p.6 Sec. 4  
  quote: `to denote the compression ratio, which is calculated as uncompressed prompt length over length after compression`
- **SCP-15** (context_loss) Column mapping of Tables 1/2: each metric is printed twice, GPT (GPT-4o-mini) then QWEN (Qwen-2.5).  
  value: `` metric:  task: Arxiv-Summarization conditions:   
  source: scope-2508.15813.txt p.6 Table 1 header  
  quote: `GPT QWEN GPT QWEN GPT QWEN GPT QWEN GPT QWEN GPT QWEN`
- **SCP-16** (context_loss) Uncompressed baseline on Arxiv-Summarization: ROUGE-1 40.49 (GPT-4o-mini) / 41.23 (Qwen-2.5).  
  value: `40.49 / 41.23` metric: ROUGE-1 task: Arxiv-Summarization conditions: Arxiv-Summarization, 2,000 sampled test docs; columns per metric are GPT (GPT-4o-mini) then QWEN (Qwen-2.5); ROUGE-1 value shown as GPT / QWEN; Original (1x)  
  source: scope-2508.15813.txt p.6 Table 1  
  quote: `Original 38.69 37.98 40.49 41.23 12.63 13.59 21.85 22.43 31.12 31.51 81.50 81.49 1�`
- **SCP-17** (context_loss) LLMLingua-2 at 5x on Arxiv-Summarization: ROUGE-1 35.53 / 34.11.  
  value: `35.53 / 34.11` metric: ROUGE-1 task: Arxiv-Summarization conditions: Arxiv-Summarization, 2,000 sampled test docs; columns per metric are GPT (GPT-4o-mini) then QWEN (Qwen-2.5); ROUGE-1 value shown as GPT / QWEN; 5x  
  source: scope-2508.15813.txt p.6 Table 1  
  quote: `LLMLingua-2 36.57 35.62 35.53 34.11 8.04 7.08 19.14 18.00 27.81 26.12 80.55 80.12 5�`
- **SCP-18** (context_loss) LongLLMLingua at 5x on Arxiv-Summarization: ROUGE-1 32.58 / 31.07.  
  value: `32.58 / 31.07` metric: ROUGE-1 task: Arxiv-Summarization conditions: Arxiv-Summarization, 2,000 sampled test docs; columns per metric are GPT (GPT-4o-mini) then QWEN (Qwen-2.5); ROUGE-1 value shown as GPT / QWEN; 5x  
  source: scope-2508.15813.txt p.6 Table 1  
  quote: `LongLLMLingua 36.23 34.55 32.58 31.07 5.76 4.81 18.17 16.89 26.12 24.40 79.71 79.07 5�`
- **SCP-19** (context_loss) SCOPE_N at 5x on Arxiv-Summarization: ROUGE-1 37.75 / 36.26.  
  value: `37.75 / 36.26` metric: ROUGE-1 task: Arxiv-Summarization conditions: Arxiv-Summarization, 2,000 sampled test docs; columns per metric are GPT (GPT-4o-mini) then QWEN (Qwen-2.5); ROUGE-1 value shown as GPT / QWEN; 5x  
  source: scope-2508.15813.txt p.6 Table 1  
  quote: `SCOPEN 38.09 37.02 37.75 36.26 10.31 9.15 20.16 19.12 29.12 27.59 80.93 80.52 5�`
- **SCP-20** (context_loss) SCOPE_D at 5x on Arxiv-Summarization: ROUGE-1 37.80 / 38.33.  
  value: `37.80 / 38.33` metric: ROUGE-1 task: Arxiv-Summarization conditions: Arxiv-Summarization, 2,000 sampled test docs; columns per metric are GPT (GPT-4o-mini) then QWEN (Qwen-2.5); ROUGE-1 value shown as GPT / QWEN; 5x  
  source: scope-2508.15813.txt p.6 Table 1  
  quote: `SCOPED 37.65 36.72 37.80 38.33 10.36 11.08 20.15 20.34 29.09 29.24 80.80 80.78 5�`
- **SCP-21** (context_loss) LLMLingua-2 at 2x on Arxiv-Summarization: ROUGE-1 38.14 / 36.37.  
  value: `38.14 / 36.37` metric: ROUGE-1 task: Arxiv-Summarization conditions: Arxiv-Summarization, 2,000 sampled test docs; columns per metric are GPT (GPT-4o-mini) then QWEN (Qwen-2.5); ROUGE-1 value shown as GPT / QWEN; 2x  
  source: scope-2508.15813.txt p.6 Table 1  
  quote: `LLMLingua-2 36.96 36.43 38.14 36.37 10.29 9.02 20.22 19.12 29.37 27.68 80.86 80.54 2�`
- **SCP-22** (context_loss) LongLLMLingua at 2x on Arxiv-Summarization: ROUGE-1 35.75 / 34.07.  
  value: `35.75 / 34.07` metric: ROUGE-1 task: Arxiv-Summarization conditions: Arxiv-Summarization, 2,000 sampled test docs; columns per metric are GPT (GPT-4o-mini) then QWEN (Qwen-2.5); ROUGE-1 value shown as GPT / QWEN; 2x  
  source: scope-2508.15813.txt p.6 Table 1  
  quote: `LongLLMLingua 37.44 36.25 35.75 34.07 8.20 6.99 19.41 18.13 28.06 26.25 80.63 80.12 2�`
- **SCP-23** (context_loss) SCOPE_N at 2x on Arxiv-Summarization: ROUGE-1 38.66 / 37.07 (compare the uncompressed row SCP-16).  
  value: `38.66 / 37.07` metric: ROUGE-1 task: Arxiv-Summarization conditions: Arxiv-Summarization, 2,000 sampled test docs; columns per metric are GPT (GPT-4o-mini) then QWEN (Qwen-2.5); ROUGE-1 value shown as GPT / QWEN; 2x  
  source: scope-2508.15813.txt p.6 Table 1  
  quote: `SCOPEN 38.14 37.35 38.66 37.07 11.04 9.68 20.67 19.62 29.78 28.20 81.09 80.71 2�`
- **SCP-24** (context_loss) SCOPE_D at 2x on Arxiv-Summarization: ROUGE-1 38.74 / 39.47.  
  value: `38.74 / 39.47` metric: ROUGE-1 task: Arxiv-Summarization conditions: Arxiv-Summarization, 2,000 sampled test docs; columns per metric are GPT (GPT-4o-mini) then QWEN (Qwen-2.5); ROUGE-1 value shown as GPT / QWEN; 2x  
  source: scope-2508.15813.txt p.6 Table 1  
  quote: `SCOPED 37.78 37.32 38.74 39.47 11.09 12.12 20.63 21.08 29.77 30.12 81.02 81.10 2�`
- **SCP-25** (context_loss) PartPrompt (a baseline) at 2x on Arxiv-Summarization: ROUGE-1 38.43 / 38.94, which on Qwen-2.5 exceeds SCOPE_N's 37.07, so SCOPE does not win every cell.  
  value: `38.43 / 38.94` metric: ROUGE-1 task: Arxiv-Summarization conditions: Arxiv-Summarization, 2,000 sampled test docs; columns per metric are GPT (GPT-4o-mini) then QWEN (Qwen-2.5); ROUGE-1 value shown as GPT / QWEN; 2x  
  source: scope-2508.15813.txt p.6 Table 1  
  quote: `PartPrompt 38.02 36.07 38.43 38.94 10.53 11.43 20.65 20.81 29.78 29.84 81.09 80.91 2�`
- **SCP-26** (context_loss) Uncompressed baseline on GovReport: ROUGE-1 43.78 (GPT-4o-mini) / 27.97 (Qwen-2.5).  
  value: `43.78 / 27.97` metric: ROUGE-1 task: GovReport-Summarization conditions: GovReport-Summarization, 2,000 sampled test docs; columns GPT (GPT-4o-mini) then QWEN (Qwen-2.5); ROUGE-1 shown as GPT / QWEN; Original (1x)  
  source: scope-2508.15813.txt p.7 Table 2  
  quote: `Original 62.46 64.56 43.78 27.97 14.98 11.57 20.25 15.66 25.29 18.23 82.46 82.74 1�`
- **SCP-27** (context_loss) LLMLingua-2 at 5x on GovReport: ROUGE-1 40.46 / 25.10.  
  value: `40.46 / 25.10` metric: ROUGE-1 task: GovReport-Summarization conditions: GovReport-Summarization, 2,000 sampled test docs; columns GPT (GPT-4o-mini) then QWEN (Qwen-2.5); ROUGE-1 shown as GPT / QWEN; 5x  
  source: scope-2508.15813.txt p.7 Table 2  
  quote: `LLMLingua-2 58.29 60.34 40.46 25.10 11.16 7.56 18.15 13.36 23.10 15.14 81.28 80.96 5�`
- **SCP-28** (context_loss) LongLLMLingua at 5x on GovReport: ROUGE-1 36.68 / 25.97.  
  value: `36.68 / 25.97` metric: ROUGE-1 task: GovReport-Summarization conditions: GovReport-Summarization, 2,000 sampled test docs; columns GPT (GPT-4o-mini) then QWEN (Qwen-2.5); ROUGE-1 shown as GPT / QWEN; 5x  
  source: scope-2508.15813.txt p.7 Table 2  
  quote: `LongLLMLingua 55.14 56.62 36.68 25.97 8.05 6.03 16.61 13.22 20.95 15.54 80.69 80.45 5�`
- **SCP-29** (context_loss) SCOPE_N at 5x on GovReport: ROUGE-1 43.59 / 26.52 (compare the uncompressed row SCP-26).  
  value: `43.59 / 26.52` metric: ROUGE-1 task: GovReport-Summarization conditions: GovReport-Summarization, 2,000 sampled test docs; columns GPT (GPT-4o-mini) then QWEN (Qwen-2.5); ROUGE-1 shown as GPT / QWEN; 5x  
  source: scope-2508.15813.txt p.7 Table 2  
  quote: `SCOPEN 60.52 62.72 43.59 26.52 14.00 9.18 19.20 14.29 24.76 16.21 81.86 81.76 5�`
- **SCP-30** (context_loss) SCOPE_D at 5x on GovReport: ROUGE-1 43.73 / 27.14.  
  value: `43.73 / 27.14` metric: ROUGE-1 task: GovReport-Summarization conditions: GovReport-Summarization, 2,000 sampled test docs; columns GPT (GPT-4o-mini) then QWEN (Qwen-2.5); ROUGE-1 shown as GPT / QWEN; 5x  
  source: scope-2508.15813.txt p.7 Table 2  
  quote: `SCOPED 60.84 63.24 43.73 27.14 14.17 10.52 19.56 14.97 24.89 17.61 82.01 82.31 5�`
- **SCP-31** (context_loss) LLMLingua-2 at 2x on GovReport: ROUGE-1 43.60 / 26.06.  
  value: `43.60 / 26.06` metric: ROUGE-1 task: GovReport-Summarization conditions: GovReport-Summarization, 2,000 sampled test docs; columns GPT (GPT-4o-mini) then QWEN (Qwen-2.5); ROUGE-1 shown as GPT / QWEN; 2x  
  source: scope-2508.15813.txt p.7 Table 2  
  quote: `LLMLingua-2 60.92 62.02 43.60 26.06 14.06 8.86 19.71 14.02 24.99 15.91 82.10 81.56 2�`
- **SCP-32** (context_loss) LongLLMLingua at 2x on GovReport: ROUGE-1 40.77 / 26.67.  
  value: `40.77 / 26.67` metric: ROUGE-1 task: GovReport-Summarization conditions: GovReport-Summarization, 2,000 sampled test docs; columns GPT (GPT-4o-mini) then QWEN (Qwen-2.5); ROUGE-1 shown as GPT / QWEN; 2x  
  source: scope-2508.15813.txt p.7 Table 2  
  quote: `LongLLMLingua 58.56 60.46 40.77 26.67 11.54 8.05 18.29 13.98 23.35 16.12 81.71 81.43 2�`
- **SCP-33** (context_loss) SCOPE_N at 2x on GovReport: ROUGE-1 43.79 / 26.60; compare LLMLingua-2 in SCP-31 and PartPrompt in SCP-35.  
  value: `43.79 / 26.60` metric: ROUGE-1 task: GovReport-Summarization conditions: GovReport-Summarization, 2,000 sampled test docs; columns GPT (GPT-4o-mini) then QWEN (Qwen-2.5); ROUGE-1 shown as GPT / QWEN; 2x  
  source: scope-2508.15813.txt p.7 Table 2  
  quote: `SCOPEN 61.35 62.94 43.79 26.60 14.44 9.30 19.58 14.29 24.95 16.18 82.17 81.87 2�`
- **SCP-34** (context_loss) SCOPE_D at 2x on GovReport: ROUGE-1 43.75 / 27.38.  
  value: `43.75 / 27.38` metric: ROUGE-1 task: GovReport-Summarization conditions: GovReport-Summarization, 2,000 sampled test docs; columns GPT (GPT-4o-mini) then QWEN (Qwen-2.5); ROUGE-1 shown as GPT / QWEN; 2x  
  source: scope-2508.15813.txt p.7 Table 2  
  quote: `SCOPED 61.65 63.73 43.75 27.38 14.41 10.86 19.78 15.22 24.94 17.96 82.26 82.47 2�`
- **SCP-35** (context_loss) PartPrompt (baseline) at 2x on GovReport: ROUGE-1 41.79 / 27.76; its Qwen-2.5 value is higher than both SCOPE variants' Qwen values in SCP-33 and SCP-34, so SCOPE does not win every cell.  
  value: `41.79 / 27.76` metric: ROUGE-1 task: GovReport-Summarization conditions: GovReport-Summarization, 2,000 sampled test docs; columns GPT (GPT-4o-mini) then QWEN (Qwen-2.5); ROUGE-1 shown as GPT / QWEN; 2x  
  source: scope-2508.15813.txt p.7 Table 2  
  quote: `PartPrompt 60.32 59.66 41.79 27.76 12.61 9.66 18.80 14.77 23.94 18.01 82.04 81.35 2�`
- **SCP-36** (context_loss) Table 3 header: three F1 columns (Trivia-QA GPT-4o-mini, Multifield-QA GPT-4o-mini, Trivia-QA with Qwen); the caption confirms the third column is Trivia-QA on Qwen-2.5.  
  value: `` metric: F1 task: Trivia-QA, MultiFieldQA-en conditions:   
  source: scope-2508.15813.txt p.8 Table 3 header  
  quote: `Methods Trivia-QA Multifield-QA Trivia-QA W/T Qwen`
- **SCP-37** (context_loss) Uncompressed baseline: Trivia-QA F1 86.08, MultiFieldQA-en F1 54.20 (GPT-4o-mini), Trivia-QA with Qwen 81.99.  
  value: `86.08; 54.20; 81.99` metric: F1 task: Trivia-QA; MultiFieldQA-en conditions: F1 (%); columns: Trivia-QA (GPT-4o-mini), Multifield-QA-en (GPT-4o-mini), Trivia-QA with Qwen-2.5 (no Qwen MultiField column); Original (1x)  
  source: scope-2508.15813.txt p.8 Table 3  
  quote: `Original 86.08 54.20 81.99 1�`
- **SCP-38** (context_loss) LLMLingua-2 at 5x: Trivia-QA 83.58, MultiFieldQA-en 36.23, Trivia-QA/Qwen 72.68.  
  value: `83.58; 36.23; 72.68` metric: F1 task: Trivia-QA; MultiFieldQA-en conditions: F1 (%); columns: Trivia-QA (GPT-4o-mini), Multifield-QA-en (GPT-4o-mini), Trivia-QA with Qwen-2.5 (no Qwen MultiField column); 5x; query-agnostic  
  source: scope-2508.15813.txt p.8 Table 3  
  quote: `LLMLingua-2 83.58 36.23 72.68 5�`
- **SCP-39** (context_loss) LongLLMLingua at 5x: Trivia-QA 80.79, MultiFieldQA-en 27.03, Trivia-QA/Qwen 60.04 (evaluated by SCOPE's authors without the question-aware configuration being described).  
  value: `80.79; 27.03; 60.04` metric: F1 task: Trivia-QA; MultiFieldQA-en conditions: F1 (%); columns: Trivia-QA (GPT-4o-mini), Multifield-QA-en (GPT-4o-mini), Trivia-QA with Qwen-2.5 (no Qwen MultiField column); 5x  
  source: scope-2508.15813.txt p.8 Table 3  
  quote: `LongLLMLingua 80.79 27.03 60.04 5�`
- **SCP-40** (context_loss) SCOPE_N at 5x: Trivia-QA 85.31, MultiFieldQA-en 41.39, Trivia-QA/Qwen 77.85 (MultiFieldQA-en uncompressed value is in SCP-37).  
  value: `85.31; 41.39; 77.85` metric: F1 task: Trivia-QA; MultiFieldQA-en conditions: F1 (%); columns: Trivia-QA (GPT-4o-mini), Multifield-QA-en (GPT-4o-mini), Trivia-QA with Qwen-2.5 (no Qwen MultiField column); 5x  
  source: scope-2508.15813.txt p.8 Table 3  
  quote: `SCOPEN 85.31 41.39 77.85 5�`
- **SCP-41** (context_loss) SCOPE_D at 5x: Trivia-QA 85.66, MultiFieldQA-en 43.54, Trivia-QA/Qwen 78.36.  
  value: `85.66; 43.54; 78.36` metric: F1 task: Trivia-QA; MultiFieldQA-en conditions: F1 (%); columns: Trivia-QA (GPT-4o-mini), Multifield-QA-en (GPT-4o-mini), Trivia-QA with Qwen-2.5 (no Qwen MultiField column); 5x  
  source: scope-2508.15813.txt p.8 Table 3  
  quote: `SCOPED 85.66 43.54 78.36 5�`
- **SCP-42** (context_loss) LLMLingua-2 at 2x: Trivia-QA 85.84, MultiFieldQA-en 46.96, Trivia-QA/Qwen 79.16.  
  value: `85.84; 46.96; 79.16` metric: F1 task: Trivia-QA; MultiFieldQA-en conditions: F1 (%); columns: Trivia-QA (GPT-4o-mini), Multifield-QA-en (GPT-4o-mini), Trivia-QA with Qwen-2.5 (no Qwen MultiField column); 2x  
  source: scope-2508.15813.txt p.8 Table 3  
  quote: `LLMLingua-2 85.84 46.96 79.16 2�`
- **SCP-43** (context_loss) LongLLMLingua at 2x: Trivia-QA 84.40, MultiFieldQA-en 35.10, Trivia-QA/Qwen 70.58.  
  value: `84.40; 35.10; 70.58` metric: F1 task: Trivia-QA; MultiFieldQA-en conditions: F1 (%); columns: Trivia-QA (GPT-4o-mini), Multifield-QA-en (GPT-4o-mini), Trivia-QA with Qwen-2.5 (no Qwen MultiField column); 2x  
  source: scope-2508.15813.txt p.8 Table 3  
  quote: `LongLLMLingua 84.40 35.10 70.58 2�`
- **SCP-44** (context_loss) SCOPE_N at 2x: Trivia-QA 86.07, MultiFieldQA-en 47.52, Trivia-QA/Qwen 79.56; MultiFieldQA-en remains below the uncompressed value in SCP-37.  
  value: `86.07; 47.52; 79.56` metric: F1 task: Trivia-QA; MultiFieldQA-en conditions: F1 (%); columns: Trivia-QA (GPT-4o-mini), Multifield-QA-en (GPT-4o-mini), Trivia-QA with Qwen-2.5 (no Qwen MultiField column); 2x  
  source: scope-2508.15813.txt p.8 Table 3  
  quote: `SCOPEN 86.07 47.52 79.56 2�`
- **SCP-45** (context_loss) SCOPE_D at 2x: Trivia-QA 86.25, MultiFieldQA-en 47.15, Trivia-QA/Qwen 80.57; the Trivia-QA value is above the uncompressed value in SCP-37.  
  value: `86.25; 47.15; 80.57` metric: F1 task: Trivia-QA; MultiFieldQA-en conditions: F1 (%); columns: Trivia-QA (GPT-4o-mini), Multifield-QA-en (GPT-4o-mini), Trivia-QA with Qwen-2.5 (no Qwen MultiField column); 2x  
  source: scope-2508.15813.txt p.8 Table 3  
  quote: `SCOPED 86.25 47.15 80.57 2�`
- **SCP-46** (context_loss) Authors' explanation for compressed Trivia-QA beating the original: rewriting may make task-relevant information more salient (speculation, not tested).  
  value: `86.25; 86.08` metric: F1 task: Trivia-QA conditions: SCOPE_D, 2x, GPT-4o-mini  
  source: scope-2508.15813.txt p.9 Sec. 4.3  
  quote: `SCOPE at 2x compression achieves an F1-score of 86.25, slightly higher than 86.08 with the original prompt`
- **SCP-47** (context_loss) PubMed uncompressed baseline: ROUGE-1 40.22.  
  value: `40.22` metric: ROUGE-1 task: PubMed-Summarization conditions: PubMed-Summarization (biomedical papers), GPT-4o-mini; ROUGE-1; Original  
  source: scope-2508.15813.txt p.14 Table 6  
  quote: `Original 47.29 40.22 12.62 21.46 31.93 83.13 1�`
- **SCP-48** (context_loss) PubMed, LLMLingua-2 at 5x: ROUGE-1 35.86.  
  value: `35.86` metric: ROUGE-1 task: PubMed-Summarization conditions: PubMed-Summarization (biomedical papers), GPT-4o-mini; ROUGE-1; 5x  
  source: scope-2508.15813.txt p.14 Table 6  
  quote: `LLMLingua-2 45.02 35.86 8.60 18.74 28.61 81.91 5�`
- **SCP-49** (context_loss) PubMed, SCOPE_N at 5x: ROUGE-1 38.03 (compare the uncompressed row SCP-47).  
  value: `38.03` metric: ROUGE-1 task: PubMed-Summarization conditions: PubMed-Summarization (biomedical papers), GPT-4o-mini; ROUGE-1; 5x  
  source: scope-2508.15813.txt p.14 Table 6  
  quote: `SCOPEN 45.93 38.03 10.68 19.92 30.25 82.26 5�`
- **SCP-50** (context_loss) PubMed, SCOPE_N at 2x: ROUGE-1 38.97.  
  value: `38.97` metric: ROUGE-1 task: PubMed-Summarization conditions: PubMed-Summarization (biomedical papers), GPT-4o-mini; ROUGE-1; 2x  
  source: scope-2508.15813.txt p.14 Table 6  
  quote: `SCOPEN 46.51 38.97 11.51 20.53 30.95 82.69 2�`
- **SCP-51** (context_loss) Multi-News (LongBench multi-document summarization), 5x, GPT-4o-mini: SCOPE ROUGE-1 36.84 (LLMLingua-2 in SCP-52); Table 8 has no uncompressed (Original) row.  
  value: `36.84` metric: ROUGE-1 task: Multi-News conditions: 5x; GPT-4o-mini; no Original row in Table 8  
  source: scope-2508.15813.txt p.15 Table 8  
  quote: `SCOPE 45.54 36.84 9.65 17.57 20.39 79.48 5�`
- **SCP-52** (context_loss) Multi-News LLMLingua-2 row at 5x (companion to SCP-51).  
  value: `34.80` metric: ROUGE-1 task: Multi-News conditions: 5x; GPT-4o-mini  
  source: scope-2508.15813.txt p.15 Table 8  
  quote: `LLMLingua-2 43.76 34.80 7.71 16.06 19.00 78.71 5�`
- **SCP-53** (context_loss) Authors claim SCOPE's score difference across 2x-5x is always within 1%; the printed tables do not strictly bear this out (e.g. SCOPE_D Qwen-2.5 ROUGE-1 on Arxiv moves by slightly more than 1 point between SCP-20 and SCP-24, and MultiFieldQA-en varies more, SCP-40 vs SCP-44).  
  value: `within 1%` metric:  task: summarization conditions:   
  source: scope-2508.15813.txt p.9 Sec. 4.2  
  quote: `its score difference is always within 1%`
- **SCP-54** (context_loss) Authors report SCOPE's advantage grows with compression ratio, with the largest gaps at 5x.  
  value: `` metric:  task: summarization, QA conditions:   
  source: scope-2508.15813.txt p.9 Sec. 4.2 / 4.3  
  quote: `The advantage of SCOPE enlarges when compression ratio increases`
- **SCP-55** (context_loss) Removing keyword extraction lowers Trivia-QA F1 at 2x from 86.07 to 85.36 (ablation).  
  value: `86.07; 85.36` metric: F1 task: Trivia-QA conditions: SCOPE_N, 2x, GPT-4o-mini  
  source: scope-2508.15813.txt p.8 Table 4  
  quote: `SCOPEN W/O Keyword Extraction 85.36 2�`
- **SCP-56** (context_loss) Swapping BART for Llama-3-8B-Instruct as the compressor gives similar GovReport quality at 5x (BART ROUGE-1 27.99, Llama-3-8B in SCP-57); this table is 'Longbench GovReport', a different set from Table 2.  
  value: `27.99` metric: ROUGE-1 task: LongBench GovReport conditions: 5x; compressor backbone swap  
  source: scope-2508.15813.txt p.16 Table 10  
  quote: `GovReport 5� BART 27.99 10.89 82.73`
- **SCP-57** (context_loss) Llama-3-8B-Instruct compressor row at 5x (companion to SCP-56).  
  value: `27.40` metric: ROUGE-1 task: LongBench GovReport conditions: 5x  
  source: scope-2508.15813.txt p.16 Table 10  
  quote: `5� Llama-3-8B 27.40 10.56 81.68`
- **SCP-58** (context_loss) On the full Arxiv test set (6,440) at 5x the ranking of methods is reported unchanged; this table has no Original row.  
  value: `6,440 examples` metric:  task: Arxiv-Summarization conditions: 5x  
  source: scope-2508.15813.txt p.15 Sec. A.3.4  
  quote: `The relative ranking of the evaluated methods remains unchanged, with SCOPE achieving the highest scores across all metrics.`
- **SCP-59** (latency_compute) Compression time per document averaged over 2x/3x/5x on GovReport: SCOPE 4.20 s, PartPrompt 4.49 s, LongLLMLingua 2.79 s. LLMLingua-2, LLMLingua and Selective-Context timings are not reported.  
  value: `4.20 s; 4.49 s; 2.79 s` metric: seconds per document task: GovReport conditions: averaged over three ratios  
  source: scope-2508.15813.txt p.10 Sec. 4.5  
  quote: `averagely SCOPE takes 4.20 seconds, PartPrompt takes 4.49 seconds, while LongLLMLingua takes 2.79 seconds`
- **SCP-60** (latency_compute) Arxiv runtimes: 3.39s, 3.96s and 2.15s, listed in the order of the previous sentence (SCOPE, PartPrompt, LongLLMLingua) - order inferred from the text, not labelled.  
  value: `3.39s; 3.96s; 2.15s` metric: seconds per document task: Arxiv-Summarization conditions: averaged over three ratios  
  source: scope-2508.15813.txt p.10 Sec. 4.5  
  quote: `on Arxiv dataset, the three runtime numbers are 3.39s, 3.96s, and 2.15s`
- **SCP-61** (latency_compute) Authors acknowledge SCOPE adds moderate latency relative to baselines and call it acceptable; the slowest step is summarization.  
  value: `` metric:  task:  conditions:   
  source: scope-2508.15813.txt p.10 Sec. 4.5  
  quote: `Comparing to the baselines, SCOPE introduces moderate latency.`
- **SCP-62** (latency_compute) The most time-consuming step in SCOPE is the summarization model.  
  value: `` metric:  task:  conditions:   
  source: scope-2508.15813.txt p.2 Sec. 1  
  quote: `the most time-consuming step in SCOPE is the summarization, which is not an issue`
- **SCP-63** (hardware) Experiment machine: one NVIDIA A100 80GB, 3 AMD Rome CPU cores, 64GB RAM; the paper does not say whether the timing in Sec. 4.5 was measured on GPU or CPU.  
  value: `A100 80GB; 3 cores; 64GB RAM` metric:  task:  conditions:   
  source: scope-2508.15813.txt p.6 Sec. 4  
  quote: `All experiments are evaluated on a machine with one NVIDIA A100 80GB Tensor Core GPU, 3 AMD Rome cores CPU and 64GB RAM.`
- **SCP-64** (latency_compute) Training cost is zero for SCOPE itself ('no additional training'); memory footprint of the three pipeline models is not reported.  
  value: `no additional training` metric:  task:  conditions:   
  source: scope-2508.15813.txt p.2 Sec. 1  
  quote: `SCOPE is a training-free generative prompt compression framework that operates at the chunk level without requiring additional model training`
- **SCP-65** (limitation) Chunk sizes are constrained to the printed range (see SCP-66 for an inconsistent upper bound elsewhere).  
  value: `400 to 700 tokens` metric:  task:  conditions: chunk size constraint  
  source: scope-2508.15813.txt p.6 Sec. 4  
  quote: `chunk sizes are constrained between 400 and 700 tokens`
- **SCP-66** (limitation) Chunk size limit is stated inconsistently: Sec. 3.1 says up to 800 tokens in the evaluation while Sec. 4 gives a different range (SCP-65).  
  value: `800 tokens` metric:  task:  conditions:   
  source: scope-2508.15813.txt p.4 Sec. 3.1  
  quote: `(e.g., up to 800 tokens in our evaluation)`
- **SCP-67** (limitation) Input length handling: when the context exceeds the embedding model's input limit it is embedded in segments and averaged. A maximum input length for SCOPE is not reported.  
  value: `not reported` metric:  task:  conditions:   
  source: scope-2508.15813.txt p.5 Sec. 3.3.1  
  quote: `When the context exceeds the embedding model's input limit, we encode it in smaller segments and average their embeddings`
- **SCP-68** (limitation) Evaluation sampled at most 2,000 records per dataset and used the Trivia-QA training split; MultiFieldQA-en is much smaller (SCP-69).  
  value: `2,000` metric:  task:  conditions:   
  source: scope-2508.15813.txt p.7 Sec. 4.1  
  quote: `Due to time and resource limit, we randomly sample 2,000 records`
- **SCP-69** (limitation) MultiFieldQA-en subset size.  
  value: `150` metric:  task: MultiFieldQA-en conditions:   
  source: scope-2508.15813.txt p.13 App. A.2  
  quote: `This subset contains 150 question- answering rows`
- **SCP-70** (limitation) All dataset descriptions state English-only data; no multilingual evaluation.  
  value: `English` metric:  task: Arxiv, PubMed, GovReport conditions:   
  source: scope-2508.15813.txt p.13 App. A.2  
  quote: `All data is in English and the dataset is split into 119,924 rows in the train set`
- **SCP-71** (limitation) There is no limitations section; the conclusion limits its claim to 'the evaluated settings'. Reported as 'not reported'.  
  value: `not reported` metric:  task:  conditions:   
  source: scope-2508.15813.txt p.10 Sec. 5  
  quote: `demonstrating the effectiveness of SCOPE across the evaluated settings`
- **SCP-72** (limitation) Documented safeguard/failure mode of the generative step: an over-truncated rewrite is replaced by the extracted keywords; the authors saw no such cases in 7,000+ chunks of 200 GovReport examples. No factual-consistency or hallucination evaluation of the rewritten text is reported.  
  value: `` metric:  task: GovReport conditions:   
  source: scope-2508.15813.txt p.6 Sec. 3.3.2  
  quote: `if the compression result is overly truncated (i.e., too short), the result will be substituted with these preserved keywords`
- **SCP-73** (reproducibility) The paper footnote says code is available at a GitHub URL.  
  value: `` metric:  task:  conditions:   
  source: scope-2508.15813.txt p.1 Footnote 1  
  quote: `Code is available at https://github.com/tzhan024/scope-prompt-compression.`
- **SCP-74** (reproducibility) Fetched on 2026-11-05, the official repository README contained only 'code coming soon.'; the repository page showed no LICENSE file, so no code and no license were available despite the paper's footnote (WebFetch).  
  value: `no code; no license` metric:  task:  conditions:   
  source: https://raw.githubusercontent.com/tzhan024/scope-prompt-compression/main/README.md README  
  quote: `code coming soon.`
- **SCP-75** (reproducibility) All models used (embedding, summarization) are public pre-trained models, which makes a re-implementation possible from the paper alone.  
  value: `` metric:  task:  conditions:   
  source: scope-2508.15813.txt p.2 Sec. 1  
  quote: `all models (mainly the embedding and summarization models) are public pre-trained small language models`
- **SCP-76** (reproducibility) Fetched version is arXiv v2 (COLM 2026, dated 20 Aug 2026); numbers may differ from v1.  
  value: `v2` metric:  task:  conditions:   
  source: scope-2508.15813.txt p.1 Title page  
  quote: `arXiv:2508.15813v2 [cs.CL] 20 Aug 2026`
- **SCP-77** (tasks_tested) Tested: long-document summarization (Arxiv, PubMed, GovReport; Multi-News in appendix) and QA (Trivia-QA, MultiFieldQA-en).  
  value: `tested` metric: ROUGE/BLEU/BERTScore; F1 task: Arxiv, PubMed, GovReport, Multi-News, Trivia-QA, MultiFieldQA-en conditions:   
  source: scope-2508.15813.txt p.7 Sec. 4.1  
  quote: `for reading-comprehension and MultiFieldQA-en (Bai et al. (2023)) from LongBench for long document QA`
- **SCP-78** (tasks_tested) Authors state they evaluate on long document summarization and QA only; coding, multi-turn chat, structured data and reasoning/math are not tested.  
  value: `not tested in paper` metric:  task:  conditions:   
  source: scope-2508.15813.txt p.2 Sec. 1  
  quote: `We evaluate our method on long document summarization and question- answering (QA) tasks, two common scenarios that require long input context.`
- **SCP-79** (tasks_tested) Legal content appears only as one document type inside the 150-row MultiFieldQA-en set; there is no legal-specific result. Biomedical content is PubMed paper summarization.  
  value: `` metric:  task: MultiFieldQA-en conditions:   
  source: scope-2508.15813.txt p.13 App. A.2  
  quote: `The documents span various fields, including academic papers, legal documents, government reports, and tech- nical manuals`
- **SCP-80** (tasks_tested) Sensitive/PII content is not tested: no PII or privacy dataset appears in the dataset list (Arxiv, PubMed, GovReport, Trivia-QA, MultiFieldQA-en, Multi-News).  
  value: `not tested in paper` metric:  task:  conditions:   
  source: scope-2508.15813.txt p.7 Sec. 4.1  
  quote: `For the summarization task, we utilize three datasets: Arxiv-Summarization (Cohan et al. (2018)) for arXiv paper summarization`
- **SCP-81** (mechanism) Keyword extraction uses a separate pre-trained NER model (HuggingFace pipeline with dbmdz/bert-large-cased-finetuned-conll03-english), so SCOPE runs a third model in addition to embedder and summarizer.  
  value: `` metric:  task:  conditions:   
  source: scope-2508.15813.txt p.6 Sec. 4  
  quote: `Keyword extraction is implemented using the HuggingFace Transformers NER pipeline with dbmdz/bert-large-cased-finetuned-conll03-english`
- **SCP-82** (mechanism) The embedding model used for chunking and relevance is All-MiniLM; a Jina embedding model was the only alternative tested.  
  value: `` metric:  task:  conditions:   
  source: scope-2508.15813.txt p.13 App. A.3.1  
  quote: `The embedding model in SCOPE for all other experiments is All-MiniLM`
- **SCP-83** (mechanism) Compressibility weight rises with chunk length and falls with relevance, so long low-similarity chunks are squeezed most.  
  value: `` metric:  task:  conditions:   
  source: scope-2508.15813.txt p.5 Sec. 3.3.1  
  quote: `(1) it decreases for higher relevance, and (2) it increases for longer chunk`
- **SCP-84** (cost) The compressor invokes only small local models (embedding, summarizer, NER) and no large LLM, so no extra LLM API call is needed (paper statement); end-to-end target-LLM cost saving is not reported.  
  value: `` metric:  task:  conditions:   
  source: scope-2508.15813.txt p.2 Sec. 1  
  quote: `without invoking large LLMs during compression`
- **SCP-85** (context_loss) Authors state SCOPE's QA F1 varies by less than 2% and 4% on the two QA datasets from 5x to 2x; the unit is not defined, and SCOPE_N's MultiFieldQA-en F1 moves by more than 4 points between SCP-40 and SCP-44 (SCOPE_D's moves less, SCP-41 vs SCP-45).  
  value: `less than 2% and 4%` metric: F1 task: Trivia-QA; MultiFieldQA-en conditions: 5x to 2x  
  source: scope-2508.15813.txt p.9 Sec. 4.3  
  quote: `SCOPE shows a variation less than 2% and 4% respectively on two datasets`
- **SCP-86** (context_loss) SCOPE_D at 3x scores Trivia-QA 85.81, MultiFieldQA-en 46.09, Trivia-QA/Qwen 78.82.  
  value: `85.81; 46.09; 78.82` metric: F1 task: Trivia-QA; MultiFieldQA-en conditions: F1 (%); columns: Trivia-QA (GPT-4o-mini), Multifield-QA-en (GPT-4o-mini), Trivia-QA with Qwen-2.5 (no Qwen MultiField column); 3x  
  source: scope-2508.15813.txt p.8 Table 3  
  quote: `SCOPED 85.81 46.09 78.82 3�`
- **SCP-87** (context_loss) LLMLingua-2 at 3x for the same QA table: Trivia-QA 85.09, MultiFieldQA-en 40.32, Trivia-QA/Qwen 76.89.  
  value: `85.09; 40.32; 76.89` metric: F1 task: Trivia-QA; MultiFieldQA-en conditions: F1 (%); columns: Trivia-QA (GPT-4o-mini), Multifield-QA-en (GPT-4o-mini), Trivia-QA with Qwen-2.5 (no Qwen MultiField column); 3x  
  source: scope-2508.15813.txt p.8 Table 3  
  quote: `LLMLingua-2 85.09 40.32 76.89 3�`

## SelectiveContext

- **SC-001** (mechanism) Informativeness of lexical units (tokens, phrases, sentences) is scored by self-information computed by a base causal language model.  
  value: `` metric:  task:  conditions: method design  
  source: selective-context-2310.06201.txt p.2 Sec. 1  
  quote: `Selective Context evaluates informativeness of lexical units (i.e., tokens, phrases, or sentences) with self-information (Shannon, 1948) computed by a base causal language model.`
- **SC-002** (mechanism) Pipeline: causal-LM self-information per token, optional merging into lexical units, then deletion of the least informative content.  
  value: `` metric:  task:  conditions: method design  
  source: selective-context-2310.06201.txt p.3 Sec. 3  
  quote: `Finally, 3) we eliminate content that is deemed least necessary to render the input more compact.`
- **SC-003** (mechanism) Base LM for LLaMA and Vicuna targets is LLaMA-7B.  
  value: `LLaMA-7B` metric:  task:  conditions: self-information computation  
  source: selective-context-2310.06201.txt p.5 Sec. 4.4  
  quote: `we employ LLaMA-7B to compute self-information.`
- **SC-004** (mechanism) Base LM for the OpenAI-family targets is the smaller GPT-3 variant curie, called through the OpenAI web API (size of curie is not stated in the paper).  
  value: `curie` metric:  task:  conditions: self-information computation  
  source: selective-context-2310.06201.txt p.5 Sec. 4.4  
  quote: `OpenAI family, we use a smaller GPT-3 variant`
- **SC-005** (mechanism) Self-information is computed sentence by sentence because LLMs give later lexical units lower self-information when the whole context is processed at once.  
  value: `` metric:  task:  conditions: implementation choice  
  source: selective-context-2310.06201.txt p.5 Sec. 4.4  
  quote: `Instead, we compute self-information sentence by sentence in our experiments.`
- **SC-006** (mechanism) Noun phrases only are merged via spaCy; verb phrases are not merged; sentence units use the NLTK sentence tokenizer.  
  value: `` metric:  task:  conditions: lexical units  
  source: selective-context-2310.06201.txt p.3 Sec. 3.2  
  quote: `We do not merge verb phrases as it might produce very long phrases.`
- **SC-007** (mechanism) Content is kept or dropped with a percentile threshold on self-information, so the amount removed is a user-set parameter chosen per task.  
  value: `` metric:  task:  conditions: percentile filtering  
  source: selective-context-2310.06201.txt p.3 Sec. 3.3  
  quote: `we design a percentile-based filtering approach to adaptively select the most informative content.`
- **SC-008** (mechanism) A filtered example shows the output is ungrammatical hard text with words and punctuation removed at phrase level (Fig. 2 'Filtered:' output).  
  value: `` metric:  task: arXiv intro example conditions: phrase level, p=50  
  source: selective-context-2310.06201.txt p.3 Fig. 2  
  quote: `Filtered: INTRODUCTION Continual Learning ( a promising learning paradigm to design models`
- **SC-009** (mechanism) Lexical units compared: token, phrase, sentence. Phrase level was best and is used for all results except Sec. 5.5.  
  value: `` metric:  task:  conditions: lexical-unit ablation  
  source: selective-context-2310.06201.txt p.5 Sec. 5  
  quote: `all results of selective context presented are at the phrase level (the optimal).`
- **SC-010** (io) Compressed text was fed to GPT-3.5 and GPT-4, which the paper says were accessed only via web API (closed models), so the method works with API targets; the compressor itself needs a base LM forward pass.  
  value: `` metric:  task:  conditions: target LLMs  
  source: selective-context-2310.06201.txt p.4 Sec. 4.2  
  quote: `are unfortunately not open-source, we can only access these models via web api`
- **SC-011** (io) Target LLMs tested: GPT-3.5, GPT-4, LLaMA-7B/13B/30B, Vicuna-7B/13B.  
  value: `` metric:  task:  conditions: target LLMs  
  source: selective-context-2310.06201.txt p.4 Sec. 4.2  
  quote: `To investigate the effect of scaling law to Selective Context, we experiment with LLaMA with 7B, 13B, and 30B parameters.`
- **SC-012** (io) Paper says the approach can potentially be combined with architecture-level efficiency methods.  
  value: `` metric:  task:  conditions: positioning  
  source: selective-context-2310.06201.txt p.1 Sec. 1  
  quote: `can be potentially combined with other architecture optimisation methods to further enhance inference efficiency.`
- **SC-020** (compression_ratio) Reduction ratios tested.  
  value: `0.2, 0.35, 0.5, 0.65, 0.8` metric:  task:  conditions: content reduction ratio  
  source: selective-context-2310.06201.txt p.5 Sec. 4.4  
  quote: `content reduction ratios in Selective Context: 0.2, 0.35, 0.5, 0.65, and 0.8`
- **SC-021** (compression_ratio) The ratio is the proportion of content filtered out (so 0.5 means half removed), measured over lexical units.  
  value: `` metric:  task:  conditions: definition  
  source: selective-context-2310.06201.txt p.5 Sec. 4.4  
  quote: `These ratios determine the proportion of content to be filtered out`
- **SC-022** (compression_ratio) Worked example: with percentile p=50 at phrase level (half of phrases removed) the remaining context keeps more than half of the tokens, i.e. a nominal 0.5 ratio is not exactly 50% token savings.  
  value: `57.2% of tokens retained; 42.7% context saved` metric:  task: arXiv intro example conditions: phrase level, p=50  
  source: selective-context-2310.06201.txt p.4 Sec. 3.3  
  quote: `context after processing by selective context only retains 57.2% of tokens, which saves 42.7% of context length.`
- **SC-023** (compression_ratio) Abstract headline: 50% reduction in context cost.  
  value: `50%` metric:  task:  conditions: abstract  
  source: selective-context-2310.06201.txt p.1 Abstract  
  quote: `we achieve a 50% reduction in context cost`
- **SC-024** (compression_ratio) Dataset size statistics: Arxiv (columns: #Doc, #Sent, #Phrase, #Token, averages per document).  
  value: `408 docs; 864.85 tokens avg` metric:  task: Arxiv conditions: test set  
  source: selective-context-2310.06201.txt p.10 Table 4  
  quote: `Arxiv 408 28.20 514.55 864.85`
- **SC-025** (compression_ratio) Dataset size statistics: ShareGPT.  
  value: `470 docs; 689.32 tokens avg` metric:  task: ShareGPT conditions: test set  
  source: selective-context-2310.06201.txt p.10 Table 4  
  quote: `ShareGPT 470 27.35 389.42 689.32`
- **SC-026** (compression_ratio) Dataset size statistics: BBC.  
  value: `294 docs; 732.54 tokens avg` metric:  task: BBC News conditions: test set  
  source: selective-context-2310.06201.txt p.10 Table 4  
  quote: `BBC 294 25.63 523.96 732.54`
- **SC-030** (context_loss) Columns from header: Ratio, BLEU, METEOR, rouge1, rouge2, rougeL, BERTScore Precision/Recall/F1; value in parentheses = drop from the Original row. Original (full-context) row: the baseline, which is below 1.0 because references come from sampled outputs at temperature 0.7.  
  value: `BLEU .347; METEOR .496; rouge1 .571; rouge2 .383; rougeL .471; BERTScore P .910 R .909 F1 .909` metric: BLEU/METEOR/ROUGE/BERTScore agreement with full-context answers task: summarisation, QA, reconstruction, conversation (aggregate) conditions: Selective Context, phrase level (p.5), temperature 0.7, metric averaged across all target models in Sec. 4.2 (whether also across tasks is not stated in the sentence; Fig. 3 splits by task); references = outputs of the same LLM given full context (4 references)  
  source: selective-context-2310.06201.txt p.6 Table 1  
  quote: `Original - .347 .496 .571 .383 .471 .910 .909 .909`
- **SC-031** (context_loss) Columns from header: Ratio, BLEU, METEOR, rouge1, rouge2, rougeL, BERTScore Precision/Recall/F1; value in parentheses = drop from the Original row. Ratio 0.2.  
  value: `BLEU .295 (.05); METEOR .460 (.04); rouge1 .540 (.03); rouge2 .346 (.04); rougeL .438 (.03); BERTScore P .905 R .900 F1 .902 (.007)` metric: agreement with full-context answers task: aggregate conditions: Selective Context, phrase level (p.5), temperature 0.7, metric averaged across all target models in Sec. 4.2 (whether also across tasks is not stated in the sentence; Fig. 3 splits by task); references = outputs of the same LLM given full context (4 references)  
  source: selective-context-2310.06201.txt p.6 Table 1  
  quote: `0.2 .295 (.05) .460 (.04) .540 (.03) .346 (.04) .438 (.03) .905 (.005) .900 (.009) .902 (.007)`
- **SC-032** (context_loss) Columns from header: Ratio, BLEU, METEOR, rouge1, rouge2, rougeL, BERTScore Precision/Recall/F1; value in parentheses = drop from the Original row. Ratio 0.35.  
  value: `BLEU .243 (.10); METEOR .421 (.08); rouge1 .504 (.07); rouge2 .294 (.09); rougeL .396 (.07); BERTScore P .900 R .894 F1 .897 (.013)` metric: agreement with full-context answers task: aggregate conditions: Selective Context, phrase level (p.5), temperature 0.7, metric averaged across all target models in Sec. 4.2 (whether also across tasks is not stated in the sentence; Fig. 3 splits by task); references = outputs of the same LLM given full context (4 references)  
  source: selective-context-2310.06201.txt p.6 Table 1  
  quote: `0.35 .243 (.10) .421 (.08) .504 (.07) .294 (.09) .396 (.07) .900 (.010) .894 (.015) .897 (.013)`
- **SC-033** (context_loss) Columns from header: Ratio, BLEU, METEOR, rouge1, rouge2, rougeL, BERTScore Precision/Recall/F1; value in parentheses = drop from the Original row. Ratio 0.5.  
  value: `BLEU .179 (.17); METEOR .362 (.13); rouge1 .449 (.12); rouge2 .237 (.15); rougeL .344 (.13); BERTScore P .893 R .882 F1 .887 (.023)` metric: agreement with full-context answers task: aggregate conditions: Selective Context, phrase level (p.5), temperature 0.7, metric averaged across all target models in Sec. 4.2 (whether also across tasks is not stated in the sentence; Fig. 3 splits by task); references = outputs of the same LLM given full context (4 references)  
  source: selective-context-2310.06201.txt p.6 Table 1  
  quote: `0.5 .179 (.17) .362 (.13) .449 (.12) .237 (.15) .344 (.13) .893 (.018) .882 (.027) .887 (.023)`
- **SC-034** (context_loss) Columns from header: Ratio, BLEU, METEOR, rouge1, rouge2, rougeL, BERTScore Precision/Recall/F1; value in parentheses = drop from the Original row. Ratio 0.65.  
  value: `BLEU .127 (.22); METEOR .299 (.20); rouge1 .391 (.18); rouge2 .178 (.21); rougeL .287 (.18); BERTScore P .885 R .870 F1 .877 (.032)` metric: agreement with full-context answers task: aggregate conditions: Selective Context, phrase level (p.5), temperature 0.7, metric averaged across all target models in Sec. 4.2 (whether also across tasks is not stated in the sentence; Fig. 3 splits by task); references = outputs of the same LLM given full context (4 references)  
  source: selective-context-2310.06201.txt p.6 Table 1  
  quote: `0.65 .127 (.22) .299 (.20) .391 (.18) .178 (.21) .287 (.18) .885 (.025) .870 (.039) .877 (.032)`
- **SC-035** (context_loss) Columns from header: Ratio, BLEU, METEOR, rouge1, rouge2, rougeL, BERTScore Precision/Recall/F1; value in parentheses = drop from the Original row. Ratio 0.8.  
  value: `BLEU .070 (.28); METEOR .224 (.27); rouge1 .311 (.26); rouge2 .122 (.26); rougeL .225 (.25); BERTScore P .874 R .852 F1 .863 (.047)` metric: agreement with full-context answers task: aggregate conditions: Selective Context, phrase level (p.5), temperature 0.7, metric averaged across all target models in Sec. 4.2 (whether also across tasks is not stated in the sentence; Fig. 3 splits by task); references = outputs of the same LLM given full context (4 references)  
  source: selective-context-2310.06201.txt p.6 Table 1  
  quote: `0.8 .070 (.28) .224 (.27) .311 (.26) .122 (.26) .225 (.25) .874 (.036) .852 (.057) .863 (.047)`
- **SC-036** (context_loss) Columns from header: Ratio, BLEU, METEOR, rouge1, rouge2, rougeL, BERTScore Precision/Recall/F1. Random-deletion baseline, ratio 0.2.  
  value: `BLEU .437; METEOR .578; rouge1 .666; rouge2 .503; rougeL .566; BERTScore F1 .899` metric: agreement with full-context answers task: aggregate conditions: Selective Context vs random deletion, phrase level, greedy decoding, reference = single full-context output; NOT comparable with Table 1 (different decoding and reference protocol)  
  source: selective-context-2310.06201.txt p.6 Table 2  
  quote: `Random 0.20 0.437 0.578 0.666 0.503 0.566 0.892 0.909 0.899`
- **SC-037** (context_loss) Columns from header: Ratio, BLEU, METEOR, rouge1, rouge2, rougeL, BERTScore Precision/Recall/F1. Selective Context, ratio 0.2 (compare Random in SC-036).  
  value: `BLEU .527; METEOR .643; rouge1 .714; rouge2 .585; rougeL .631; BERTScore F1 .931` metric: agreement with full-context answers task: aggregate conditions: Selective Context vs random deletion, phrase level, greedy decoding, reference = single full-context output; NOT comparable with Table 1 (different decoding and reference protocol)  
  source: selective-context-2310.06201.txt p.6 Table 2  
  quote: `Selective Context 0.20 0.527 0.643 0.714 0.585 0.631 0.930 0.932 0.931`
- **SC-038** (context_loss) Columns from header: Ratio, BLEU, METEOR, rouge1, rouge2, rougeL, BERTScore Precision/Recall/F1. Random-deletion baseline, ratio 0.5.  
  value: `BLEU .283; METEOR .443; rouge1 .576; rouge2 .346; rougeL .432; BERTScore F1 .873` metric: agreement with full-context answers task: aggregate conditions: Selective Context vs random deletion, phrase level, greedy decoding, reference = single full-context output; NOT comparable with Table 1 (different decoding and reference protocol)  
  source: selective-context-2310.06201.txt p.6 Table 2  
  quote: `0.50 0.283 0.443 0.576 0.346 0.432 0.867 0.881 0.873`
- **SC-039** (context_loss) Columns from header: Ratio, BLEU, METEOR, rouge1, rouge2, rougeL, BERTScore Precision/Recall/F1. Selective Context, ratio 0.5.  
  value: `BLEU .350; METEOR .528; rouge1 .642; rouge2 .425; rougeL .501; BERTScore F1 .900` metric: agreement with full-context answers task: aggregate conditions: Selective Context vs random deletion, phrase level, greedy decoding, reference = single full-context output; NOT comparable with Table 1 (different decoding and reference protocol)  
  source: selective-context-2310.06201.txt p.6 Table 2  
  quote: `0.50 0.350 0.528 0.642 0.425 0.501 0.900 0.902 0.900`
- **SC-040** (context_loss) Columns from header: Ratio, BLEU, METEOR, rouge1, rouge2, rougeL, BERTScore Precision/Recall/F1. Random-deletion baseline, ratio 0.8.  
  value: `BLEU .156; METEOR .314; rouge1 .450; rouge2 .219; rougeL .310; BERTScore F1 .847` metric: agreement with full-context answers task: aggregate conditions: Selective Context vs random deletion, phrase level, greedy decoding, reference = single full-context output; NOT comparable with Table 1 (different decoding and reference protocol)  
  source: selective-context-2310.06201.txt p.6 Table 2  
  quote: `0.80 0.156 0.314 0.450 0.219 0.310 0.843 0.853 0.847`
- **SC-041** (context_loss) Columns from header: Ratio, BLEU, METEOR, rouge1, rouge2, rougeL, BERTScore Precision/Recall/F1. Selective Context, ratio 0.8.  
  value: `BLEU .160; METEOR .328; rouge1 .464; rouge2 .223; rougeL .319; BERTScore F1 .866` metric: agreement with full-context answers task: aggregate conditions: Selective Context vs random deletion, phrase level, greedy decoding, reference = single full-context output; NOT comparable with Table 1 (different decoding and reference protocol)  
  source: selective-context-2310.06201.txt p.6 Table 2  
  quote: `0.80 0.160 0.328 0.464 0.223 0.319 0.875 0.858 0.866`
- **SC-042** (context_loss) All metrics compare the compressed-context answer to the full-context LLM answer, not to human or gold labels; the paper reports no accuracy/EM against ground truth.  
  value: `` metric:  task:  conditions: evaluation protocol  
  source: selective-context-2310.06201.txt p.4 Sec. 4  
  quote: `We take the generated answer given full context as the reference answer`
- **SC-043** (context_loss) QA reference answers are also generated from the original context by an LLM rather than human-annotated.  
  value: `` metric:  task: QA conditions: evaluation protocol  
  source: selective-context-2310.06201.txt p.5 Sec. 4.3  
  quote: `Here we first generate questions and answers based on the original context, where these answers are treated as reference answers`
- **SC-044** (context_loss) Authors' reading of Table 1: drops become noticeable at reduction 0.5.  
  value: `BLEU drop 0.17; ROUGE-1 drop 0.12` metric: BLEU; ROUGE-1 task: aggregate conditions: Table 1 discussion  
  source: selective-context-2310.06201.txt p.6 Sec. 5.1  
  quote: `The drops become noticeable as the reduction ratio rises to 0.5, where the average BLEU score drops 0.17 and the average ROUGE-1 drops 0.12.`
- **SC-044b** (context_loss) Authors judge reduction 0.65 and 0.8 less valuable; the text says 0.32 BERTScore-F1 drop, but Table 1 shows F1 drops of .032 and .047 (SC-034, SC-035), so '0.32' looks like a typo (extractor inference).  
  value: `0.18 ROUGE-1 drop; '0.32' BERTScore-F1 drop (as printed)` metric: ROUGE-1; BERTScore-F1 task: aggregate conditions: Table 1 discussion  
  source: selective-context-2310.06201.txt p.6 Sec. 5.1  
  quote: `as shown by the 0.18 drop on ROUGE-1 and 0.32 drop on BERTScore-F1.`
- **SC-045** (context_loss) Faithfulness test row, uncompressed baseline (columns: Ratio, #Sorry, Answer len., Unfaithfulness).  
  value: `0 sorry; answer length 160.3` metric: answer length task: QA, 200 pairs per ratio (1000 total) conditions: gpt-3.5-turbo; manual OpenIE-tuple entailment check  
  source: selective-context-2310.06201.txt p.6 Table 3  
  quote: `Full 0 160.3 -`
- **SC-046** (context_loss) Faithfulness test, ratio 0.2.  
  value: `#Sorry 0; answer len. 156.5; unfaithfulness .027` metric: unfaithful tuple rate task: QA, 200 pairs conditions: gpt-3.5-turbo  
  source: selective-context-2310.06201.txt p.6 Table 3  
  quote: `0.2 0 156.5 .027`
- **SC-047** (context_loss) Faithfulness test, ratio 0.35.  
  value: `#Sorry 6; answer len. 136.0; unfaithfulness .050` metric: unfaithful tuple rate task: QA, 200 pairs conditions: gpt-3.5-turbo  
  source: selective-context-2310.06201.txt p.6 Table 3  
  quote: `0.35 6 136.0 .050`
- **SC-048** (context_loss) Faithfulness test, ratio 0.5.  
  value: `#Sorry 4; answer len. 140.2; unfaithfulness .038` metric: unfaithful tuple rate task: QA, 200 pairs conditions: gpt-3.5-turbo  
  source: selective-context-2310.06201.txt p.6 Table 3  
  quote: `0.5 4 140.2 .038`
- **SC-049** (context_loss) Faithfulness test, ratio 0.65.  
  value: `#Sorry 19; answer len. 131.2; unfaithfulness .051` metric: unfaithful tuple rate task: QA, 200 pairs conditions: gpt-3.5-turbo  
  source: selective-context-2310.06201.txt p.6 Table 3  
  quote: `0.65 19 131.2 .051`
- **SC-050** (context_loss) Faithfulness test, ratio 0.8.  
  value: `#Sorry 27; answer len. 103.7; unfaithfulness .086` metric: unfaithful tuple rate task: QA, 200 pairs conditions: gpt-3.5-turbo  
  source: selective-context-2310.06201.txt p.6 Table 3  
  quote: `0.8 27 103.7 .086`
- **SC-051** (context_loss) Failure mode: at ratio 0.65 gpt-3.5 refused or shortened answers because evidence was removed.  
  value: `19 refusals (9% of 200); answers 35% shorter` metric:  task: QA conditions: gpt-3.5-turbo, ratio 0.65  
  source: selective-context-2310.06201.txt p.7 Sec. 5.2  
  quote: `refuses to answer 19 questions (9% of 200), and the answers are 35% shorter than the reference answer`
- **SC-052** (limitation) Failure mode: the target LLM tends to answer shorter or refuse when needed evidence is missing from the selective context.  
  value: `` metric:  task: QA conditions: gpt-3.5-turbo  
  source: selective-context-2310.06201.txt p.7 Sec. 5.2  
  quote: `tend to generate shorter answers or refuse to answer the questions if it fails to identify necessary evidence in the given selective context.`
- **SC-053** (context_loss) By task, the original-context reconstruction task drops steepest as compression rises (results only in Fig. 3, no extractable numbers).  
  value: `` metric:  task: reconstruction conditions: Fig. 3  
  source: selective-context-2310.06201.txt p.7 Sec. 5.3  
  quote: `show the steepest drop with increasing compression ratio`
- **SC-054** (context_loss) Authors conclude the method is especially suitable for summarisation and answer generation (QA), judged by BERTScore curves.  
  value: `` metric: BERTScore task: summarisation; QA conditions: Fig. 3  
  source: selective-context-2310.06201.txt p.7 Sec. 5.3  
  quote: `We could say Selective Context is especially suitable for tasks of summarisation and answer generation.`
- **SC-055** (context_loss) Human check found no trend with model scale; instruct-tuned Vicuna was more robust than LLaMA, whose outputs often derailed with selective context.  
  value: `` metric:  task: summaries conditions: human evaluation of 1150 summaries by three students  
  source: selective-context-2310.06201.txt p.8 Sec. 5.4  
  quote: `llama models often fail to follow instructions and go wild very easily.`
- **SC-056** (context_loss) Lexical-unit ablation: phrase level is best, token level second; numbers appear only in a figure (text calls it Table 5 but no table values exist in the extracted pages).  
  value: `` metric: BERTScore-F1 task:  conditions: Fig. 5 / 'Table 5'  
  source: selective-context-2310.06201.txt p.8 Sec. 5.5  
  quote: `is the optimal approach, consistently outperforming the other two variants, followed by token-level Selective Context.`
- **SC-057** (context_loss) Sentence-level filtering is unstable compared with token and phrase level.  
  value: `` metric: BERTScore-F1 task:  conditions: lexical-unit ablation  
  source: selective-context-2310.06201.txt p.8 Sec. 5.5  
  quote: `Removing redundancy at sentence-level is a rather unstable implementation compared to the token and phrase-level.`
- **SC-058** (context_loss) Qualitative failure example: the summary from selective context omitted research-background information because it had been pruned as redundancy.  
  value: `` metric:  task: arXiv paper summary (vicuna-13b) conditions: ratio 0.5  
  source: selective-context-2310.06201.txt p.8 Sec. 5.6  
  quote: `the summary given selective context missed relevant information about the research background`
- **SC-059** (context_loss) Abstract headline quality cost at the 50% point: BERTScore and faithfulness drops, on four downstream applications.  
  value: `.023 BERTScore; .038 faithfulness` metric: BERTScore; unfaithfulness task: four downstream applications conditions: ratio 0.5; reference = full-context output  
  source: selective-context-2310.06201.txt p.1 Abstract  
  quote: `while observing only a minor drop of .023 in BERTscore and .038 in faithfulness on four downstream applications`
- **SC-060** (latency_compute) Single case-study numbers, uncompressed: GPU memory and time per generated token (summary from vicuna-13b; GPU type not stated).  
  value: `77,695 MB; 110.8 ms/token` metric: CUDA memory; ms/token task: one arXiv paragraph summary conditions: vicuna_13b; full context; GPU type not stated  
  source: selective-context-2310.06201.txt p.8 Fig. 6  
  quote: `Original Context, CUDA Memory = 77,695 MB; Time = 110.8 ms/token`
- **SC-061** (latency_compute) Same case study with Selective Context at ratio 0.5.  
  value: `61,885 MB; 76.3 ms/token` metric: CUDA memory; ms/token task: one arXiv paragraph summary conditions: vicuna_13b; ratio 0.5; GPU type not stated  
  source: selective-context-2310.06201.txt p.8 Fig. 6  
  quote: `Selective Context, Ratio: 0.5, CUDA Memory = 61,885 MB, Time = 76.3 ms/token,`
- **SC-062** (latency_compute) One-time cost to build the selective context for the case-study paragraph (self-information plus lexical-unit tokenisation).  
  value: `46.1 ms` metric: ms task: one arXiv paragraph conditions: GPU/CPU not stated; base LM not named for this example  
  source: selective-context-2310.06201.txt p.8 Fig. 6  
  quote: `Time to construct selective context = 46.1 ms`
- **SC-063** (latency_compute) Abstract headline: inference memory and time reductions at the 50% reduction point.  
  value: `36% memory; 32% time` metric:  task:  conditions: abstract; ratio 0.5  
  source: selective-context-2310.06201.txt p.1 Abstract  
  quote: `a 36% reduction in inference memory usage and a 32% reduction in inference time`
- **SC-064** (latency_compute) Case-study text restates the memory and speed gain (per token) at ratio 0.5.  
  value: `about 36% memory; 1.32 times faster per token` metric:  task: one arXiv paragraph summary conditions: ratio 0.5  
  source: selective-context-2310.06201.txt p.8 Sec. 5.6  
  quote: `reduces about 36% of the memory cost in inference and makes generation 1.32 times faster (per token)`
- **SC-065** (hardware) No GPU model, CPU or batch-size information is given for memory/latency numbers (grep for GPU/A100/V100 found only the 'CUDA Memory' labels).  
  value: `not reported` metric:  task:  conditions:   
  source: selective-context-2310.06201.txt p.8 Sec. 5.6  
  quote: `it shows selective context significantly reduces the memory usage of the GPU and accelerates the generation process`
- **SC-070** (cost) Extra compute: a base-LM forward pass over the context (LLaMA-7B, or GPT-3 curie via API) is needed before the target LLM call; no dollar cost or token-count accounting is reported (not reported).  
  value: `not reported` metric:  task:  conditions: inferred from mechanism plus SC-003/SC-004  
  source: selective-context-2310.06201.txt p.5 Sec. 4.4  
  quote: `We use smaller base causal language model`
- **SC-080** (limitation) Authors' limitation 1: results depend on the noun-phrase boundary detection; verb phrases are not handled.  
  value: `` metric:  task:  conditions: Limitations section  
  source: selective-context-2310.06201.txt p.9 Sec. 7  
  quote: `our approach is somewhat influenced by the phrase boundary detection procedure.`
- **SC-081** (limitation) Authors say no mature verb-phrase tokenisation exists and speculate dependency-tree filtering could help (future work, not implemented).  
  value: `` metric:  task:  conditions: Limitations section  
  source: selective-context-2310.06201.txt p.9 Sec. 7  
  quote: `we do not consider verb phrases as there is no mature solution for verb phrase tokenisation.`
- **SC-082** (limitation) Authors' limitation 2: the best percentile varies by task and context, and no tool for choosing it exists.  
  value: `` metric:  task:  conditions: Limitations section  
  source: selective-context-2310.06201.txt p.9 Sec. 7  
  quote: `the optimal compression percentile varies based on specific tasks and context.`
- **SC-083** (limitation) Test items longer than 2048 tokens were excluded, and mean document length is under 900 tokens, so the evaluation does not cover genuinely long contexts despite the motivation.  
  value: `2048-token cap` metric:  task: all datasets conditions: dataset construction  
  source: selective-context-2310.06201.txt p.4 Sec. 4.1  
  quote: `has a max_length of 2048 tokens, we do not include articles or conversations exceeding this length`
- **SC-084** (limitation) Multilingual/code: ShareGPT includes several languages and scenarios such as coding, but no per-language or per-scenario results are reported.  
  value: `` metric:  task: ShareGPT conditions: dataset description  
  source: selective-context-2310.06201.txt p.4 Sec. 4.1  
  quote: `This datasets consists of conversations in different languages and in various scenarios (e.g., coding, chitchat, writing assistant, etc.).`
- **SC-085** (limitation) Test sets were created after March 2023 to avoid pre-training contamination of the target LLMs.  
  value: `` metric:  task:  conditions: dataset construction  
  source: selective-context-2310.06201.txt p.4 Sec. 4.1  
  quote: `Data samples in the BBC News, arXiv, and ShareGPT.com datasets were all created after March 2023`
- **SC-090** (reproducibility) Paper states code and data are available on GitHub.  
  value: `` metric:  task:  conditions: abstract  
  source: selective-context-2310.06201.txt p.1 Abstract  
  quote: `Code and data are available at https://github.com/`
- **SC-091** (reproducibility) Official GitHub repo README says the project is licensed under the MIT License (WebFetch summary of the page; the repo example uses gpt2 as base model via model_type='gpt2').  
  value: `MIT` metric:  task:  conditions: https://github.com/liyucheng09/Selective_Context  
  source: https://github.com/liyucheng09/Selective_Context README  
  quote: `licensed under the MIT License`
- **SC-092** (reproducibility) README describes lexical units as sentences, phrases or tokens and shows a reduce_ratio parameter example of 0.5 (WebFetch summary).  
  value: `reduce_ratio = 0.5` metric:  task:  conditions: https://github.com/liyucheng09/Selective_Context  
  source: https://github.com/liyucheng09/Selective_Context README  
  quote: `lexical units (sentences, phrases, or tokens)`
- **SC-100** (tasks_tested) Datasets and tasks: arXiv papers, BBC News and ShareGPT conversations; summarisation, question answering, original-context reconstruction, conversation.  
  value: `` metric:  task: arXiv; BBC News; ShareGPT conditions: dataset list  
  source: selective-context-2310.06201.txt p.2 Sec. 1  
  quote: `on arXiv papers, BBC News, and real conversation on ShareGPT.com with four NLP tasks: summarisation, question answering, original context reconstruction, and conversation`
- **SC-101** (tasks_tested) The authors built three custom test sets because standard benchmarks (MMLU, ARC) are single-round QA; no coding, structured-data, math or PII benchmark is included.  
  value: `` metric:  task: BBC; arXiv; ShareGPT conditions: dataset list  
  source: selective-context-2310.06201.txt p.4 Sec. 4.1  
  quote: `we collect three test sets consisting of long documents and conversations to evaluate Selective Context.`
- **SC-102** (tasks_tested) Coding: not tested as a task (only a mention that ShareGPT contains coding conversations; SC-084).  
  value: `not tested in paper` metric:  task:  conditions: dataset list SC-101  
  source: selective-context-2310.06201.txt p.4 Sec. 4.1  
  quote: `we collect three test sets consisting of long documents and conversations to evaluate Selective Context.`
- **SC-103** (tasks_tested) Structured data (JSON/tables/logs): not tested in paper.  
  value: `not tested in paper` metric:  task:  conditions: dataset list SC-101  
  source: selective-context-2310.06201.txt p.4 Sec. 4.1  
  quote: `we collect three test sets consisting of long documents and conversations to evaluate Selective Context.`
- **SC-104** (tasks_tested) Reasoning/math: not tested in paper.  
  value: `not tested in paper` metric:  task:  conditions: dataset list SC-101  
  source: selective-context-2310.06201.txt p.4 Sec. 4.1  
  quote: `we collect three test sets consisting of long documents and conversations to evaluate Selective Context.`
- **SC-105** (tasks_tested) Sensitive/PII content: not tested in paper.  
  value: `not tested in paper` metric:  task:  conditions: dataset list SC-101  
  source: selective-context-2310.06201.txt p.4 Sec. 4.1  
  quote: `we collect three test sets consisting of long documents and conversations to evaluate Selective Context.`
- **SC-106** (tasks_tested) Multi-turn chat: tested as the conversation task on ShareGPT (compress history, answer the last user query); per-task numbers only in Fig. 3.  
  value: `tested` metric: agreement with full-context answer task: ShareGPT conditions: conversation task  
  source: selective-context-2310.06201.txt p.5 Sec. 4.3  
  quote: `we ask LLMs to answer users' last query of ShareGPT conversation instances with selective context applied on the previous conversation history.`
- **SC-107** (tasks_tested) Long-document QA and summarisation: tested on arXiv (first two sections only) and BBC articles.  
  value: `tested` metric:  task: arXiv; BBC conditions: dataset construction  
  source: selective-context-2310.06201.txt p.4 Sec. 4.1  
  quote: `we only process the first two sections (usually introduction and background) for each paper in our experiments.`
- **SC-110** (reproducibility) The real paper's title.  
  value: `` metric:  task:  conditions: paper identity  
  source: selective-context-2310.06201.txt p.1 Title page  
  quote: `Compressing Context to Enhance Inference Efficiency of`
- **SC-111** (reproducibility) The real paper's arXiv identifier and date line.  
  value: `arXiv:2310.06201v1, 9 Oct 2023` metric:  task:  conditions: paper identity  
  source: selective-context-2310.06201.txt p.1 Title page  
  quote: `arXiv:2310.06201v1 [cs.CL] 9 Oct 2023`
- **SC-T01** (context_loss) Selective-Context baseline in LLMLingua-2 paper Table 1 (columns as L2-040).  
  value: `EM 66.28; BLEU 10.83; Rouge1 39.21; Rouge2 18.73; RougeL 27.67; BERTScore 84.48; 1,222 tok; 2.5x` metric: EM; BLEU/ROUGE/BERTScore task: MeetingBank conditions: baseline re-run by LLMLingua-2 authors (not the original SC authors); base LM LLaMA-2-7B per p.7; lexical-unit level not stated; target LLM GPT-3.5-Turbo (default per p.6), greedy decoding, temperature 0; task-agnostic (question-agnostic) compression  
  source: llmlingua-2-2403.12968.txt p.6 Table 1  
  quote: `Selective-Context 66.28 10.83 39.21 18.73 27.67 84.48 1,222 2.5x`
- **SC-T02** (context_loss) Selective-Context baseline in Table 2, 2,000-token constraint (columns as L2-034). Code column is 49.2 vs 54.2 original (L2-043); Synth. 8.4 vs 37.8.  
  value: `SingleDoc 16.2; MultiDoc 34.8; Summ. 24.4; FewShot 15.7; Synth. 8.4; Code 49.2; LB AVG 24.8; 1,925 tok 5x; ZeroSCROLLS AVG 19.4` metric: task metrics as in LongLLMLingua task: LongBench; ZeroSCROLLS conditions: baseline re-run by LLMLingua-2 authors (not the original SC authors); base LM LLaMA-2-7B per p.7; lexical-unit level not stated; target LLM GPT-3.5-Turbo (default per p.6), greedy decoding, temperature 0; task-agnostic (question-agnostic) compression  
  source: llmlingua-2-2403.12968.txt p.7 Table 2  
  quote: `Selective-Context 16.2 34.8 24.4 15.7 8.4 49.2 24.8 1,925 5x 19.4 1,865 5x`
- **SC-T03** (context_loss) Selective-Context baseline in Table 2, 3,000-token constraint (columns as L2-034).  
  value: `SingleDoc 23.3; MultiDoc 39.2; Summ. 25.0; FewShot 23.8; Synth. 27.5; Code 53.1; LB AVG 32.0; 3,328 tok 3x; ZeroSCROLLS AVG 20.7` metric: task metrics as in LongLLMLingua task: LongBench; ZeroSCROLLS conditions: baseline re-run by LLMLingua-2 authors (not the original SC authors); base LM LLaMA-2-7B per p.7; lexical-unit level not stated; target LLM GPT-3.5-Turbo (default per p.6), greedy decoding, temperature 0; task-agnostic (question-agnostic) compression  
  source: llmlingua-2-2403.12968.txt p.7 Table 2  
  quote: `Selective-Context 23.3 39.2 25.0 23.8 27.5 53.1 32.0 3,328 3x 20.7 3,460 3x`
- **SC-T04** (context_loss) Selective-Context baseline in Table 3 (columns as L2-032). GSM8K EM is only slightly above the zero-shot floor (L2-050) and far below full-shot (L2-049).  
  value: `GSM8K 53.98 (452 tok, 5x), 52.99 (218 tok, 11x); BBH 54.27 (276 tok, 3x), 54.02 (155 tok, 5x)` metric: EM task: GSM8K; BBH conditions: baseline re-run by LLMLingua-2 authors (not the original SC authors); base LM LLaMA-2-7B per p.7; lexical-unit level not stated; target LLM GPT-3.5-Turbo (default per p.6), greedy decoding, temperature 0; task-agnostic (question-agnostic) compression  
  source: llmlingua-2-2403.12968.txt p.7 Table 3  
  quote: `Selective-Context 53.98 452 5x 52.99 218 11x 54.27 276 3x 54.02 155 5x`
- **SC-T05** (context_loss) Selective-Context baseline in Table 11 (NaturalQuestions 20 docs; columns as L2-059; the Reorder cell is a dash).  
  value: `1st 31.4; 5th 19.5; 10th 24.7; 15th 24.1; 20th 43.8; Reorder -; 791 tok; 3.7x` metric: not named task: NaturalQuestions 20-document conditions: question-agnostic; 4x constraint; baseline re-run by LLMLingua-2 authors (not the original SC authors); base LM LLaMA-2-7B per p.7; lexical-unit level not stated; target LLM GPT-3.5-Turbo (default per p.6), greedy decoding, temperature 0; task-agnostic (question-agnostic) compression  
  source: llmlingua-2-2403.12968.txt p.18 Table 11  
  quote: `Selective-Context 31.4 19.5 24.7 24.1 43.8 - 791 3.7x`
- **SC-T06** (context_loss) Selective-Context baseline with Mistral-7B target (columns as L2-051).  
  value: `MB QA 58.13; MB Summ. 26.84 (1,222 tok, 2.5x); LB SingleDoc 22.0 (2,038 tok, 7.1x); 26.0 (3,075 tok, 4.7x)` metric: QA (metric not named); Rouge1; LongBench score task: MeetingBank; LongBench SingleDoc conditions: target LLM Mistral-7B; base LM LLaMA-2-7B  
  source: llmlingua-2-2403.12968.txt p.8 Table 4  
  quote: `Selective-Context 58.13 26.84 1,222 2.5x 22.0 2,038 7.1x 26.0 3,075 4.7x`
- **SC-T07** (latency_compute) Table 5 Selective-Context row (seconds at 2x, 3x, 5x), which is larger than the uncompressed end-to-end latency of 14.9 s (L2-070) whichever way the row is read (compressor-only or end-to-end; caption does not say).  
  value: `15.9 s; 15.6 s; 15.5 s` metric: latency (s) task: MeetingBank conditions: V100-32G; LLaMA-2-7B based baseline  
  source: llmlingua-2-2403.12968.txt p.8 Table 5  
  quote: `Selective-Context - 15.9 15.6 15.5`
- **SC-T08** (latency_compute) Peak GPU memory of Selective-Context with LLaMA-2-7B as the SLM (second value of the pair), per LLMLingua-2 paper.  
  value: `26.5GB` metric: GPU memory task: MeetingBank conditions: LLaMA-2-7B SLM  
  source: llmlingua-2-2403.12968.txt p.14 Appendix I  
  quote: `consume 16.6GB and 26.5GB of GPU memory, respectively`
- **SC-T09** (mechanism) LLMLingua-2 paper states its Selective-Context and LLMLingua baselines both use LLaMA-2-7B.  
  value: `` metric:  task:  conditions: baseline setup  
  source: llmlingua-2-2403.12968.txt p.7 Sec. 5 Baselines  
  quote: `LLMLingua (Jiang et al., 2023a), both are based on LLaMA-2-7B.`

## SnapKV

- **EH-056** (context_loss) EHPC's re-run of SnapKV with a 1024 KV budget on Llama 3.1 8B: printed average 35.25 (0.02 above EHPC-1024's 35.23); RepoBench-P 48.7, LCC 52.1, PassageRetrieval 98.16.  
  value: `Avg 35.25; RepoBench-P 48.7; LCC 52.1` metric: LongBench task: LongBench conditions: SnapKV-1024; Llama-3.1-8B-Instruct; run by EHPC authors  
  source: ehpc-2501.12959.txt p.10 Table 6  
  quote: `SnapKV-1024 31.98 11.17 25.33 14.81 15.73 10.69 26.95 22.89 25.86 67.5 91.89 42.85 7.67 98.16 48.7 52.1 35.25`
- **EH-057** (context_loss) EHPC's re-run of SnapKV with a 2048 KV budget on Llama 3.1 8B: printed average 35.80; RepoBench-P 49.5, LCC 52.6.  
  value: `Avg 35.80; RepoBench-P 49.5; LCC 52.6` metric: LongBench task: LongBench conditions: SnapKV-2048; Llama-3.1-8B-Instruct; run by EHPC authors  
  source: ehpc-2501.12959.txt p.10 Table 6  
  quote: `SnapKV-2048 31.45 11.94 26.24 15.73 16.03 11.66 29.64 23.24 26.44 69.5 91.48 42.68 7.21 98.03 49.5 52.6 35.80`
- **EH-063** (context_loss) EHPC's re-run of SnapKV 1024 on Phi 3.5 Mini: printed average 33.68; of H2O 1024: 31.38.  
  value: `SnapKV-1024 Avg 33.68` metric: LongBench task: LongBench conditions: SnapKV-1024; Phi-3.5-mini-3.8B-Instruct; run by EHPC authors  
  source: ehpc-2501.12959.txt p.10 Table 6  
  quote: `SnapKV-1024 24.31 16.03 34.93 20.72 26.02 13.74 28.27 22.03 24.02 67.5 87.71 14.57 6.08 85.60 44.0 47.1 33.68`
- **SK-001** (mechanism) SnapKV is a fine-tuning-free method that shrinks the KV cache of the prompt while the model generates.  
  value: `` metric:  task:  conditions:   
  source: snapkv-2404.14469.txt p.1 Abstract  
  quote: `an innovative and fine-tuning-free approach that efficiently minimizes KV cache size`
- **SK-002** (mechanism) SnapKV selects, per attention head, clustered important KV positions of the prompt, using an observation window at the end of the prompt.  
  value: `` metric:  task:  conditions:   
  source: snapkv-2404.14469.txt p.1 Abstract  
  quote: `SnapKV automatically compresses KV caches by selecting clustered important KV positions for each attention head`
- **SK-003** (mechanism) Compressed cache = voted prefix positions plus ALL features in the observation window (the last part of the prompt, which includes the question).  
  value: `` metric:  task:  conditions:   
  source: snapkv-2404.14469.txt p.5 Sec. 4.1  
  quote: `We concatenate the selected attention features with all features within the observation window`
- **SK-004** (mechanism) SnapKV keeps a constant number of prompt KV entries during generation.  
  value: `` metric:  task:  conditions:   
  source: snapkv-2404.14469.txt p.4 Sec. 4  
  quote: `SnapKV addresses this issue by maintaining a constant amount of prompt KVs during generation`
- **SK-005** (mechanism) The pseudo-code operates on query/key/value tensors of the prompt phase of a transformer layer (asserts it is the prompt phase), i.e. it is code inside the model's attention layer.  
  value: `` metric:  task:  conditions: Listing 1  
  source: snapkv-2404.14469.txt p.5 Listing 1  
  quote: `# Ensure it is the prompt phase.`
- **SK-006** (mechanism) Pooling over voted positions keeps neighbouring tokens; the authors say selecting only the highest-weight features is insufficient. A failure example is retrieving only the country code of a phone number and hallucinating the rest.  
  value: `` metric:  task:  conditions:   
  source: snapkv-2404.14469.txt p.6 Sec. 4.3  
  quote: `such compression might cause the LLMs to retrieve only the country code of a phone number and hallucinate the rest`
- **SK-007** (mechanism) Selection depends on the instruction: different instructions on the same document pick different prefix features (hit rates drop), so the compressed cache is instruction-specific. Reuse of one compressed cache for different later questions is not evaluated (inferred from mechanism).  
  value: `` metric:  task:  conditions: QMSum, Openreview, SPACE; Mistral-7B-Instruct-v0.2  
  source: snapkv-2404.14469.txt p.5 Sec. 4.2.1  
  quote: `different instructions prioritize different prefix attention`
- **SK-008** (mechanism) Compression happens once after the prompt has been processed; the cache is not updated during decoding (so it is not dynamic eviction like H2O).  
  value: `` metric:  task:  conditions: LWM-Text-Chat-1M, batch sizes 1-8  
  source: snapkv-2404.14469.txt p.7 Sec. 5.1.2  
  quote: `there is no extra update during the inference`
- **SK-009** (mechanism) Needle-in-a-Haystack uses max pooling kernel 5 and observation window 16 (KV size 1024).  
  value: `5/16` metric:  task:  conditions:   
  source: snapkv-2404.14469.txt p.7 Sec. 5.1.1  
  quote: `with a maximum pooling kernel size of 5 and an observation window size of 16`
- **SK-009b** (mechanism) LongBench runs use max pooling kernel 7 and observation window 32.  
  value: `7/32` metric:  task: LongBench conditions:   
  source: snapkv-2404.14469.txt p.9 Sec. 5.3  
  quote: `We use max pooling with kernel size 7 and observation window size 32.`
- **SK-009c** (mechanism) Command-R runs use pooling kernel 13 and window 64 with KV capped at 4096.  
  value: `13/64` metric:  task:  conditions: Command-R  
  source: snapkv-2404.14469.txt p.10 Sec. 5.4  
  quote: `while the pooling kernel size and window size are set to 13 and 64, respectively`
- **SK-010** (io) Integration needs source-level change of the model's attention code; the authors describe it as a few lines changed in the native HuggingFace implementation.  
  value: `` metric:  task:  conditions:   
  source: snapkv-2404.14469.txt p.7 Figure 6 caption  
  quote: `native HuggingFace implementation with only a few lines of code changed`
- **SK-011** (io) Authors claim SnapKV can be integrated into popular deep-learning frameworks with just a few code adjustments.  
  value: `` metric:  task:  conditions:   
  source: snapkv-2404.14469.txt p.2 Sec. 1  
  quote: `be easily integrated into popular deep-learning frameworks with just a few code adjustments`
- **SK-012** (io) All evaluated models are open-weight: LWM-Text-Chat-1M (7B), LongChat-7b-v1.5-32k, Mistral-7B-Instruct-v0.2, Mixtral-8x7B-Instruct-v0.1, and Cohere Command-R (35B, called open-source). No closed API model is evaluated and none is discussed as a target.  
  value: `` metric:  task:  conditions:   
  source: snapkv-2404.14469.txt p.9 Sec. 5.3  
  quote: `We choose LWM-Text-Chat-1M with 1 million context length, LongChat-7b-v1.5-32k, Mistral-7B-Instruct-v0.2, Mixtral-8x7B-Instruct-v0.1 with 32k context length as our baselines`
- **SK-013** (io) Command-R is described as an open-source 35B-parameter model with up to 128k context.  
  value: `35B; 128k` metric:  task:  conditions:   
  source: snapkv-2404.14469.txt p.9 Sec. 5.4  
  quote: `an open-source model with 35B parameters and capable of handling sequences of up to`
- **SK-014** (io) LWM-Text-Chat-1M is a 7B model with up to one million context.  
  value: `7B; 1M` metric:  task:  conditions:   
  source: snapkv-2404.14469.txt p.7 Sec. 5.1  
  quote: `is a 7B instruction-fine-tuned model with up to one million context length`
- **SK-015** (limitation) The paper does not discuss black-box/API deployment; the method edits attention/KV tensors inside the serving model. (Inferred from mechanism.)  
  value: `not reported` metric:  task:  conditions: inferred from mechanism  
  source: snapkv-2404.14469.txt p.12 Sec. 6  
  quote: `SnapKV's scope is primarily confined to the generative aspect of models, specifically targeting the KV cache during the generation.`
- **SK-020** (compression_ratio) KV budgets tested on LongBench: 1024, 2048, 4096 prompt tokens; average input about 13k tokens, giving 92% compression at 1024 and 68% at 4096.  
  value: `92% at 1024; 68% at 4096` metric:  task: LongBench (16 datasets) conditions: LWMChat, LongChat, Mistral-7B, Mixtral-8x7B; avg input ~13k tokens  
  source: snapkv-2404.14469.txt p.9 Sec. 5.3  
  quote: `using 1024, SnapKV achieves an average compression rate of 92%, and using 4096, it reaches 68%`
- **SK-021** (compression_ratio) Needle-in-a-Haystack on LWM-Text-Chat-1M is described as a 380x compression ratio (KV size 1024 in SK-021b; 380k length in SK-080).  
  value: `380x` metric:  task: Needle-in-a-Haystack conditions: LWM-Text-Chat-1M on one A100-80GB  
  source: snapkv-2404.14469.txt p.7 Sec. 5.1.1  
  quote: `with a 380x compression ratio`
- **SK-021b** (compression_ratio) Needle-in-a-Haystack KV budget was fixed at 1024 prompt tokens.  
  value: `1024` metric:  task: Needle-in-a-Haystack conditions: LWM-Text-Chat-1M  
  source: snapkv-2404.14469.txt p.7 Sec. 5.1.1  
  quote: `We configured the prompt KV cache size to 1024`
- **SK-022** (compression_ratio) Command-R: KV capped at 4096 with pooling 13/window 64 gives compression between 2x and 32x depending on sequence length.  
  value: `2x to 32x` metric:  task:  conditions: Command-R 35B  
  source: snapkv-2404.14469.txt p.10 Sec. 5.4  
  quote: `these hyper-parameters give a KV cache compression ratio between 2x to 32x depending on the sequence length`
- **SK-023** (compression_ratio) RAG citation benchmark: contexts of 20k-40k tokens with KV size 4096 gives 5-10x compression.  
  value: `5-10x` metric:  task: RAG citation (internal Cohere benchmark) conditions: Command-R  
  source: snapkv-2404.14469.txt p.10 Sec. 5.4.2  
  quote: `Given our KV cache size of 4096, we achieve a compression of 5-10x`
- **SK-024** (compression_ratio) End-to-end RAG: average length around 16,000 tokens gives about 4x compression.  
  value: `about 4x` metric:  task: HotpotQA-based RAG conditions: Command-R  
  source: snapkv-2404.14469.txt p.11 Sec. 5.4.2  
  quote: `average dataset length of around 16,000 tokens, the KV cache benefits from a compression ratio of approximately 4x`
- **SK-030** (context_loss) Table 1 columns are: NrtvQA, Qasper, MF-en, HotpotQA, 2WikiMQA, Musique, GovReport, QMSum, MultiNews, TREC, TriviaQA, SAMSum, PCount, PRe, Lcc, RB-P. Rows give the prompt KV capacity (1024/2048/4096) or H2O at 4096.  
  value: `` metric:  task: LongBench conditions: column map  
  source: snapkv-2404.14469.txt p.9 Table 1  
  quote: `NrtvQA Qasper MF-en HotpotQA 2WikiMQA Musique GovReport QMSum MultiNews TREC TriviaQA SAMSum PCount PRe Lcc RB-P`
- **SK-031** (context_loss) Mistral-7B-Instruct-v0.2 full KV baseline on LongBench (GovReport 32.85, Lcc 55.51, RB-P 52.88).  
  value: `GovReport 32.85; Lcc 55.51; RB-P 52.88` metric: task metrics task: LongBench conditions: All KV; Mistral block  
  source: snapkv-2404.14469.txt p.9 Table 1  
  quote: `All KV 26.82 33.06 49.28 42.77 27.33 19.27 32.85 24.25 27.06 71.0 86.23 42.98 2.75 86.98 55.51 52.88`
- **SK-032** (context_loss) SnapKV with 1024 prompt KV on Mistral: GovReport falls to 25.89 (from 32.85) but code is flat (Lcc 55.65, RB-P 51.87). Full-KV reference in SK-031.  
  value: `GovReport 25.89; Lcc 55.65; RB-P 51.87` metric: task metrics task: LongBench conditions: SnapKV 1024; Mistral-7B-Instruct-v0.2  
  source: snapkv-2404.14469.txt p.9 Table 1  
  quote: `SnapKV: 1024 25.54 29.51 49.25 40.94 25.7 19.42 25.89 23.82 26.11 69.5 86.48 42.06 2.98 88.56 55.65 51.87`
- **SK-033** (context_loss) SnapKV with 4096 prompt KV on Mistral: near-parity with full KV (GovReport 30.74, Lcc 55.62, RB-P 52.65).  
  value: `GovReport 30.74; Lcc 55.62; RB-P 52.65` metric: task metrics task: LongBench conditions: SnapKV 4096; Mistral  
  source: snapkv-2404.14469.txt p.9 Table 1  
  quote: `SnapKV: 4096 26.41 33.36 49.81 42.32 27.93 18.76 30.74 24.19 27.08 71.0 86.25 43.01 2.73 86.18 55.62 52.65`
- **SK-034** (context_loss) SnapKV with 2048 prompt KV on Mistral: GovReport 28.81, Lcc 55.93, RB-P 52.01.  
  value: `GovReport 28.81; Lcc 55.93; RB-P 52.01` metric: task metrics task: LongBench conditions: SnapKV 2048; Mistral  
  source: snapkv-2404.14469.txt p.9 Table 1  
  quote: `SnapKV: 2048 25.89 32.47 48.6 41.71 27.31 18.69 28.81 24.5 26.6 70.0 86.27 42.47 3.09 87.43 55.93 52.01`
- **SK-035** (context_loss) LWM-Text-Chat-1M full KV baseline on LongBench (GovReport 27.97, PCount 3.17).  
  value: `GovReport 27.97; PCount 3.17` metric: task metrics task: LongBench conditions: All KV; LWMChat block  
  source: snapkv-2404.14469.txt p.9 Table 1  
  quote: `All KV 18.18 25.56 40.94 24.57 19.39 10.49 27.97 24.9 24.81 71.0 60.9 39.73 3.17 3.5 44.4 43.82`
- **SK-036** (context_loss) LWM-Text-Chat-1M with SnapKV 1024: summarization GovReport drops to 19.79 (from 27.97); code Lcc 43.34, RB-P 44.0 (full-KV reference in SK-035).  
  value: `GovReport 19.79; Lcc 43.34; RB-P 44.0` metric: task metrics task: LongBench conditions: SnapKV 1024; LWMChat  
  source: snapkv-2404.14469.txt p.9 Table 1  
  quote: `SnapKV: 1024 18.02 23.73 40.25 24.61 19.84 10.77 19.79 24.44 23.53 70.0 61.42 39.64 1.67 3.0 43.34 44.0`
- **SK-037** (context_loss) LongChat-7b-v1.5-32k full KV baseline on LongBench (TREC 66.5, Lcc 54.89, RB-P 59.05).  
  value: `TREC 66.5; Lcc 54.89; RB-P 59.05` metric: task metrics task: LongBench conditions: All KV; LongChat block  
  source: snapkv-2404.14469.txt p.9 Table 1  
  quote: `All KV 20.88 29.36 43.2 33.05 24.58 14.66 30.89 22.76 26.61 66.5 83.99 40.83 0.0 30.5 54.89 59.05`
- **SK-038** (context_loss) LongChat with SnapKV 1024: MF-en 37.93, GovReport 23.45; code Lcc 53.63, RB-P 57.62 (full-KV reference in SK-037).  
  value: `MF-en 37.93; GovReport 23.45; Lcc 53.63; RB-P 57.62` metric: task metrics task: LongBench conditions: SnapKV 1024; LongChat  
  source: snapkv-2404.14469.txt p.9 Table 1  
  quote: `SnapKV: 1024 19.32 26.6 37.93 34.15 23.34 12.71 23.45 21.81 24.93 65.0 80.88 38.19 0.0 31.0 53.63 57.62`
- **SK-039** (context_loss) Mixtral-8x7B-Instruct full KV baseline on LongBench (GovReport 34.25, Lcc 69.07, RB-P 69.65).  
  value: `GovReport 34.25; Lcc 69.07; RB-P 69.65` metric: task metrics task: LongBench conditions: All KV; Mixtral block  
  source: snapkv-2404.14469.txt p.9 Table 1  
  quote: `All KV 26.81 37.06 51.55 47.77 32.46 26.59 34.25 26.05 27.91 76.0 90.57 46.98 5.5 100.0 69.07 69.65`
- **SK-040** (context_loss) Mixtral with SnapKV 1024: GovReport 27.77; code Lcc 69.02, RB-P 68.98 (full-KV reference in SK-039).  
  value: `GovReport 27.77; Lcc 69.02; RB-P 68.98` metric: task metrics task: LongBench conditions: SnapKV 1024; Mixtral  
  source: snapkv-2404.14469.txt p.9 Table 1  
  quote: `SnapKV: 1024 26.01 34.65 51.58 48.23 32.67 25.92 27.77 25.0 27.25 74.5 90.42 46.48 5.5 99.5 69.02 68.98`
- **SK-041** (context_loss) H2O re-run by SnapKV authors with a larger 4096 budget on LWMChat: much lower than SnapKV 1024 on several columns (MF-en 20.01, HotpotQA 16.86, Lcc 41.52, RB-P 40.97).  
  value: `MF-en 20.01; HotpotQA 16.86; Lcc 41.52; RB-P 40.97` metric: task metrics task: LongBench conditions: H2O 4096; LWMChat  
  source: snapkv-2404.14469.txt p.9 Table 1  
  quote: `H2O: 4096 13.17 24.82 20.01 16.86 9.74 7.2 25.77 23.26 23.83 71.0 61.06 40.33 0.0 0.0 41.52 40.97`
- **SK-042** (context_loss) H2O re-run with 4096 budget on Mixtral: HotpotQA 34.76, 2WikiMQA 25.69, Lcc 64.91, RB-P 63.52 (vs full KV 47.77, 32.46, 69.07, 69.65).  
  value: `HotpotQA 34.76; Lcc 64.91; RB-P 63.52` metric: task metrics task: LongBench conditions: H2O 4096; Mixtral  
  source: snapkv-2404.14469.txt p.9 Table 1  
  quote: `H2O: 4096 20.45 32.09 48.02 34.76 25.69 16.5 29.76 23.53 26.84 74.5 90.24 47.1 7.06 99.42 64.91 63.52`
- **SK-043** (context_loss) Authors' summary: 'negligible performance drop' on 16 datasets even at 1024 prompt-KV, some models outperform baseline. (GovReport/summarization drops of several points at 1024 in Table 1 contradict 'negligible' for that column.)  
  value: `` metric:  task: LongBench conditions:   
  source: snapkv-2404.14469.txt p.9 Sec. 5.3  
  quote: `Table 1 illustrates a negligible performance drop from models with SnapKV`
- **SK-044** (context_loss) SnapKV 1024 beats H2O at 4096 on 11 of 16 benchmarks for Mistral (SnapKV authors' own comparison; H2O gets 4x the cache).  
  value: `11 of 16` metric:  task: LongBench conditions: SnapKV 1024 vs H2O 4096, Mistral-7B-Instruct-v0.2  
  source: snapkv-2404.14469.txt p.9 Sec. 5.3  
  quote: `SnapKV on Mistral-7B-Instruct-v0.2 achieves better performance than H2O with 4096 caches on 11 out of 16 benchmarks`
- **SK-045** (context_loss) Needle-in-a-Haystack with Command-R at up to 128k tokens: aggregated score 9.866 (baseline) vs 9.819 (SnapKV), -0.5%.  
  value: `9.866 vs 9.819 (-0.5%)` metric: aggregated NIAH score task: Needle-in-a-Haystack (permuted contexts, 8 runs) conditions: Command-R 35B; KV cap 4096; up to 128k tokens  
  source: snapkv-2404.14469.txt p.10 Table 2  
  quote: `Score 9.866 9.819 -0.5%`
- **SK-046** (context_loss) Needle test at 128k tokens gives 32x KV compression with no degradation, per authors.  
  value: `32x` metric:  task: Needle-in-a-Haystack conditions: Command-R  
  source: snapkv-2404.14469.txt p.10 Sec. 5.4.1  
  quote: `even with a 128k sequence length resulting in 32x compression of KV cache`
- **SK-047** (context_loss) RAG citation (selecting relevant documents among 100) changes Command-R's F1 by -1.2% relative to full KV (Table 3).  
  value: `-1.2%` metric: F1 (relative difference) task: RAG Citation (internal benchmark) conditions: Command-R; 20k-40k tokens; KV 4096  
  source: snapkv-2404.14469.txt p.10 Table 3  
  quote: `RAG Citation F1 score -1.2%`
- **SK-048** (context_loss) End-to-end RAG (retrieve 200, re-rank to 100, answer with Command-R): F1 -2.1% relative to full KV.  
  value: `-2.1%` metric: F1 (relative difference) task: modified HotpotQA with Wikipedia conditions: Command-R; ~16k tokens  
  source: snapkv-2404.14469.txt p.10 Table 3  
  quote: `RAG End-to-end F1 score -2.1%`
- **SK-049** (context_loss) RAG generation on bioasq with 200 documents (about 24k tokens): average +5.4% relative to the baseline.  
  value: `+5.4%` metric: relative difference of answer accuracy task: bioasq RAG-style conditions: Command-R; ground truth at beginning/middle/end  
  source: snapkv-2404.14469.txt p.11 Table 4  
  quote: `Avg +5.4%`
- **SK-050** (context_loss) Authors suggest compression can help by removing noise from negative documents when the context holds close to 200 documents.  
  value: `` metric:  task: bioasq RAG conditions: Command-R  
  source: snapkv-2404.14469.txt p.11 Sec. 5.4.2  
  quote: `we can effectively reduce the noise from negative documents`
- **SK-051** (context_loss) Pooling ablation: pooling significantly improves retrieval on LongEval-Lines compared with no pooling.  
  value: `` metric:  task: LongEval-Lines conditions: Mistral-7B-Instruct-v0.2; 5K-30K tokens  
  source: snapkv-2404.14469.txt p.8 Sec. 5.2  
  quote: `we find that pooling significantly enhances retrieval accuracy`
- **SK-060** (hardware) Decoding-speed and memory benchmarks on a single A100 80GB GPU.  
  value: `A100 80GB` metric:  task:  conditions:   
  source: snapkv-2404.14469.txt p.8 Figure 7 caption  
  quote: `All experiments are conducted on an A100 80GB GPU.`
- **SK-061** (latency_compute) Decoding: at 16k input and batch 2 the baseline exceeds 100 ms/token while SnapKV stays under 40 ms, about 3.6x faster.  
  value: `3.6x; >100 ms vs <40 ms` metric: ms/token task:  conditions: LWM-Text-Chat-1M; KV 2048; 512 generated tokens; A100 80GB  
  source: snapkv-2404.14469.txt p.7 Sec. 5.1.2  
  quote: `the decoding time for the baseline model surpasses 100 ms, whereas for SnapKV-optimized model, the decoding time consistently remains below 40 ms, achieving approximately a 3.6x speedup`
- **SK-062** (latency_compute) Decoding latency with SnapKV stays constant as the input grows because the compressed prompt KV has fixed size.  
  value: `` metric: ms/token task:  conditions: LWM-Text-Chat-1M; KV 2048  
  source: snapkv-2404.14469.txt p.7 Sec. 5.1.2  
  quote: `the SnapKV-optimized model maintains a constant decoding speed`
- **SK-063** (latency_compute) Memory: at batch 2 the baseline runs out of memory beyond 16k input tokens, SnapKV extends this to 131k tokens, about 8.2x.  
  value: `8.2x; 16k to 131k` metric:  task:  conditions: LWM-Text-Chat-1M; A100 80GB; batch 2  
  source: snapkv-2404.14469.txt p.8 Sec. 5.1.2  
  quote: `at a batch size of 2, the baseline model encounters an OOM error beyond 16k input tokens, whereas the SnapKV-enhanced model extends this limit to 131k input tokens, indicating an approximately 8.2x improvement`
- **SK-064** (latency_compute) Abstract: 3.6x faster generation and 8.2x better memory efficiency vs baseline at 16K input tokens.  
  value: `3.6x; 8.2x` metric:  task:  conditions: A100-80GB  
  source: snapkv-2404.14469.txt p.1 Abstract  
  quote: `SnapKV achieves a consistent decoding speed with a 3.6x increase in generation speed and an 8.2x enhancement in memory efficiency compared to the baseline when processing inputs of 16K tokens`
- **SK-065** (latency_compute) The original (uncompressed) implementation runs out of memory at 33k input tokens in the Needle-in-a-Haystack run that SnapKV handles to 380k (see SK-080).  
  value: `33k` metric:  task: Needle-in-a-Haystack conditions: LWM-Text-Chat-1M; native HuggingFace; A100-80GB  
  source: snapkv-2404.14469.txt p.7 Figure 6 caption  
  quote: `Meanwhile, the original implementation encounters OOM error with 33k input tokens`
- **SK-066** (latency_compute) Prefill effect: SnapKV does not make processing of the prompt itself cheaper; the authors say its design does not cover prompt inference, limiting usefulness when the system cannot handle long prompts. Only decoding is sped up.  
  value: `` metric:  task:  conditions:   
  source: snapkv-2404.14469.txt p.12 Sec. 6  
  quote: `SnapKV's design does not cover the processing of the prompt inference`
- **SK-067** (latency_compute) Appendix A: generation time dominates total time for long inputs; prompting time (Mistral) is shown only as a plot (Figure 10), no prompting-latency numbers in text.  
  value: `not reported (plot only)` metric:  task:  conditions: Mistral-7B-Instruct-v0.2; 512 generated tokens  
  source: snapkv-2404.14469.txt p.16 Appendix A  
  quote: `generation time dominates the whole processing time for LLMs over input sequences`
- **SK-068** (latency_compute) Combined with Medusa speculative decoding at 10k prompt: 1.3x faster than Medusa alone and 2.2x faster than native decoding.  
  value: `1.3x; 2.2x` metric: ms/token task: QASPER subset (summarize paper) conditions: Mistral-7B-Instruct-v0.2; 128 generation steps  
  source: snapkv-2404.14469.txt p.12 Sec. 5.5  
  quote: `which achieved a 1.3x speedup for sequences with 10k length compared to Medusa and a 2.2x speedup compared to the native decoding`
- **SK-069** (limitation) SnapKV cannot extend a model's long-context ability and does not help if the system cannot process long prompts (authors' discussion).  
  value: `` metric:  task:  conditions:   
  source: snapkv-2404.14469.txt p.12 Sec. 6  
  quote: `SnapKV cannot extend a model's long context capability if the model inherently struggles with long contexts or exhibits poor performance.`
- **SK-070** (cost) No tokens are removed from the prompt sent to the model, so no per-request token-price saving applies; savings are GPU memory and decoding time inside the serving stack. (Inferred from mechanism.)  
  value: `not applicable` metric:  task:  conditions: inferred from mechanism  
  source: snapkv-2404.14469.txt p.12 Sec. 6  
  quote: `SnapKV's scope is primarily confined to the generative aspect of models, specifically targeting the KV cache during the generation.`
- **SK-080** (limitation) Max context tested: 380k tokens (LWM-Text-Chat-1M, Needle-in-a-Haystack), 128k (Command-R), LongBench inputs average about 13k.  
  value: `380k; 128k; ~13k` metric:  task:  conditions:   
  source: snapkv-2404.14469.txt p.7 Sec. 5.1.1  
  quote: `we extended the document length to 380k tokens which is the longest content that can be processed by a single A100-80GB GPU`
- **SK-081** (limitation) Command-R RAG results use internal Cohere benchmarks and an internal tool-use benchmark whose numbers are not given (only 'demonstrated its effectiveness').  
  value: `not reported` metric:  task: internal tool-use benchmark conditions: Command-R  
  source: snapkv-2404.14469.txt p.9 Sec. 5.4  
  quote: `an internal benchmark on tool use`
- **SK-082** (limitation) Qualitative examples (Figure 11) compare outputs of SnapKV 1024/2048/4096 with full KV on SAMSum, Qasper and HotpotQA for Mistral.  
  value: `` metric:  task: SAMSum, Qasper, HotpotQA conditions: Mistral-7B-Instruct-v0.2  
  source: snapkv-2404.14469.txt p.17 Appendix B Figure 11  
  quote: `Figure 11: Visualization of generation examples from Samsum, Qasper, HotpotQA datasets with`
- **SK-090** (reproducibility) Paper text contains no link to SnapKV's own code (only links to StreamingLLM and Medusa repositories).  
  value: `not reported` metric:  task:  conditions:   
  source: snapkv-2404.14469.txt p.11 Sec. 5.5 footnote  
  quote: `https://github.com/FasterDecoding/Medusa`
- **SK-091** (reproducibility) Checked 2026-11-05: official repo github.com/FasterDecoding/SnapKV is listed under Apache-2.0 license (per WebFetch summary); README says it supports Llama, Mistral and Mixtral via monkey patches.  
  value: `Apache-2.0` metric:  task:  conditions:   
  source: https://github.com/FasterDecoding/SnapKV GitHub repo page  
  quote: `Apache-2.0 license`
- **SK-100** (tasks_tested) LongBench categories evaluated: single/multi-doc QA, summarization, few-shot, synthetic, and code completion (Lcc, RB-P).  
  value: `tested` metric: task metrics task: LongBench 16 datasets conditions:   
  source: snapkv-2404.14469.txt p.9 Sec. 5.3  
  quote: `spanning single and multi-document QA, summarization, few-shot learning, synthetic tasks, and code`
- **SK-101** (tasks_tested) Long-document QA/RAG: Command-R tested on NarrativeQA, Needle-in-a-Haystack, bioasq RAG, HotpotQA-based RAG and an internal tool-use benchmark.  
  value: `tested` metric:  task: NarrativeQA, bioasq, HotpotQA conditions: Command-R  
  source: snapkv-2404.14469.txt p.9 Sec. 5.4  
  quote: `To evaluate SnapKV's impact on RAG, we ran tests on bioasq`
- **SK-102** (tasks_tested) Multi-turn chat: UltraChat (multi-turn, >3k-token prompts, >512-token responses) is used only for attention-pattern observations, not for quality evaluation.  
  value: `observation only` metric:  task: UltraChat conditions:   
  source: snapkv-2404.14469.txt p.3 Sec. 3  
  quote: `Ultrachat [11], a multi-turns, high-quality instruction dataset`
- **SK-103** (tasks_tested) Reasoning/math, structured data (JSON/tables/logs) and PII/sensitive content are not among the evaluated datasets (LongBench 16, NIAH, LongEval-Lines, NarrativeQA, bioasq, HotpotQA, QASPER, internal tool-use).  
  value: `not tested in paper` metric:  task:  conditions: dataset list in Sec. 5  
  source: snapkv-2404.14469.txt p.9 Sec. 5.3  
  quote: `spanning single and multi-document QA, summarization, few-shot learning, synthetic tasks, and code`
- **SK-104** (tasks_tested) Coding: LongBench Lcc and RB-P (RepoBench-P) columns are the only code evaluation; no HumanEval-style generation.  
  value: `tested (Lcc, RB-P)` metric: task metrics task: Lcc, RB-P conditions:   
  source: snapkv-2404.14469.txt p.9 Table 1  
  quote: `NrtvQA Qasper MF-en HotpotQA 2WikiMQA Musique GovReport QMSum MultiNews TREC TriviaQA SAMSum PCount PRe Lcc RB-P`
