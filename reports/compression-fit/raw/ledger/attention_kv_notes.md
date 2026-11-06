# attention_kv notes: EHPC, H2O, SnapKV

Ledger: `raw/ledger/attention_kv.jsonl` (all quotes verified by `scripts/verify_ledger.py`). Every factual sentence ends with ledger ids. Numbers come only from quoted lines. "My arithmetic" is marked wherever a figure is computed from ledger numbers rather than printed.
Sources: ehpc-2501.12959 (19 pp.), h2o-2306.14048 (49 pp.), snapkv-2404.14469 (17 pp.), plus official repo/landing pages for license/code (WebFetch, checked 2026-11-05).

## Key question: text pruning (gateway-compatible) vs KV cache inside the serving model

- EHPC is the only one of the three that produces TEXT: it deletes tokens and hands a shorter prompt to a different model; the authors place it with "explicit" methods that "can be applied to black-box LLMs" and stress it acts on tokens, unlike KV methods that act on the cache [EH-003, EH-028, EH-029, EH-030, EH-031, EH-021].
- But EHPC still needs a LOCAL LLM with access to attention scores to score tokens, so a gateway would have to host an open-weight evaluator (paper uses Llama-3.1-8B) [EH-020, EH-024, EH-023]. The scoring pass is a full forward over the prompt through the first layers up to the evaluator layer (layer 13 of 32 for Llama-3.1-8B) [EH-002, EH-009].
- H2O operates on the KV cache of the generating model during decoding; implemented by modifying a white-box OPT engine (FlexGen). It cannot be applied to a remote API model; the paper never discusses API/closed models [H2-001, H2-002, H2-010, H2-012].
- SnapKV operates on the KV cache of the generating model: after the prompt is processed it keeps voted prefix positions per head plus the whole observation window. Integration is a source-level change to attention code. It was tested only on open-weight models and never discusses API targets [SK-002, SK-003, SK-005, SK-010, SK-012, SK-015].
- Evidence sentences: EHPC "The compressed prompts obtained are transferable and can be applied to API-based black-box large models" (EH-021) and "EHPC requires the local development of LLMs for prompt compression" (EH-020). H2O "FlexGen is a white-box implementation of OPT models, and we have done some surgery on handling the KV cache" (H2-010). SnapKV "native HuggingFace implementation with only a few lines of code changed" (SK-010) and "SnapKV's scope is primarily confined to the generative aspect of models, specifically targeting the KV cache during the generation" (SK-015).
- Prefill vs decode: H2O and SnapKV leave the prompt's prefill compute untouched and shrink only what decoding reads/stores [H2-006, H2-002, SK-066]. EHPC cuts the answering model's prefill and decode input (k-times shorter prompt) but adds its own scoring pass [EH-094, EH-091, EH-092, EH-090].

## EHPC (Fei et al., arXiv 2501.12959; NeurIPS 2025 spotlight per poster page)

Mechanism and I/O
- Training-free token deletion driven by attention of a few "evaluator heads" found once per model with a synthetic Needle-in-a-Haystack pilot [EH-001, EH-003, EH-007].
- Heads sit in middle layers; Llama-3.1-8B uses layer 13 of 32, Phi-3.5-mini layer 17; head indices differ per model [EH-008, EH-009, EH-010]. Observation window 16 and pooling kernel 32 for Llama [EH-011]. Evaluator heads beat other heads from the same layer, and one QA-derived head set is used for all tasks [EH-071, EH-072].
- Scores come from the last rows of attention, so the question must sit at the end of the prompt text given to the evaluator (inferred from mechanism; query-agnostic use not discussed) [EH-012].
- Output is shortened natural-language text with fragments; the authors admit it "may lack certain contextual elements", example in Appendix G is fragmentary [EH-004, EH-006]. Pooling (borrowed from SnapKV) keeps neighbouring tokens [EH-005].
- Evaluator can differ from the answering model (EMI) or be the same (NMI) [EH-022]. Compressor in Table 4 is Llama-3.1-8B; footnote 1 links Meta-Llama-3-8B (ambiguous) [EH-024, EH-025]. NMI targets are Llama-3.1-8B and Phi-3.8B (128k context) [EH-070].
- The target LLM behind Table 4 is not named; ChatGPT-3.5-Turbo appears only as a full-prompt latency baseline with timing copied from another paper [EH-026, EH-027].

Ratios and quality (LongBench/ZeroSCROLLS, EMI, Table 4)
- Full prompt: LongBench avg 44.0 at 10,295 tokens; ZeroSCROLLS 32.5 [EH-040]. EHPC 3,000-token constraint: 2,892 tokens (3x), avg 49.7, code 63.0, ZeroSCROLLS 36.7 [EH-041]. 2,000-token constraint: 2,004 tokens (5x), avg 49.6, code 61.9, ZeroSCROLLS 34.6 [EH-042, EH-112].
- Comparators: LongLLMLingua 48.8 / 48.0, LLMLingua-2 42.2 / 39.1, OpenAI-embedding RAG 41.7 / 29.8 at 3,000 / 2,000 tokens [EH-043, EH-044, EH-045, EH-046, EH-047, EH-048].
- Summarization is below the full prompt (24.8-25.1 vs 26.5); few-shot is called "competitive"; QA and code are above the full prompt in this setting [EH-041, EH-042, EH-040, EH-050, EH-051, EH-052].
- NMI vs KV methods (Table 6, budgets 1024/2048): Llama-3.1-8B full KV avg 38.32; EHPC 35.23 (1024) and 37.86 (2048); code columns fall (RepoBench-P 49.25 -> 42.8/44.9) [EH-053, EH-054, EH-055]. Phi-3.5-mini full KV 34.62; EHPC 39.22 (1024), 36.46 (2048), with PassageRetrieval down to 63.00 at 2048 (full 83.85) [EH-060, EH-061, EH-062]. Authors: prompt compression declines on code and few-shot, KV methods remain better there [EH-066, EH-067]; gains up to 40% on QA for Phi [EH-068].
- Third-party numbers for H2O/SnapKV on Llama-3.1-8B (run by EHPC authors): SnapKV avg 35.25 (1024), 35.80 (2048); H2O 34.77 / 35.45, with H2O PassageRetrieval collapsing to 71.34 / 72.79 (full 97.73) [EH-056, EH-057, EH-058, EH-059].

Latency, compute, cost
- Table 5 (14,354-token RepoBench-P subset to 2,048 tokens [EH-049], 5 repeats, one 40GB-VRAM GPU, type not named): EHPC compression 0.88 s, total 1.99 s vs 2.16 s for sending the full prompt to ChatGPT-3.5-Turbo (inference time borrowed); LongLLMLingua 67.44 s, LLMLingua-2 1.27 s [EH-083, EH-084, EH-085, EH-086, EH-087, EH-088, EH-089, EH-080, EH-081].
- Memory/throughput benefit of NMI is argued, not measured [EH-092, EH-093]. API-cost saving is argued (cost linear in prompt length), no dollar figures [EH-100, EH-101].
- No training cost (training-free); cost of the pilot calibration is not reported [EH-001, EH-007].

Limitations, reproducibility, tasks
- English LongBench only; no limitations section; compressed length can exceed the budget (2,004 for 2,000) [EH-110, EH-112].
- NIAH used only for head discovery, no NIAH accuracy for compressed prompts [EH-111].
- Code: paper has no code/checkpoint/license statement; NeurIPS poster page and arXiv abstract page show no code link; arXiv page license CC BY-NC-SA 4.0 is for the paper text [EH-120, EH-121, EH-122].
- Tested: coding (LCC, RepoBench-P), long-doc QA (LongBench, ZeroSCROLLS), RAG baselines, summarization, few-shot. Not tested: multi-turn chat, structured data, math, PII [EH-130, EH-131, EH-132, EH-133, EH-134, EH-135, EH-136, EH-137]. Models advertise 128k context; the largest reported average prompt is 14,354 tokens (latency subset) [EH-138, EH-088].

## H2O (Zhang et al., arXiv 2306.14048, NeurIPS 2023)

Mechanism and I/O
- KV-cache eviction policy that keeps a balance of recent and heavy-hitter (accumulated attention) tokens, one eviction per step, per head/layer [H2-001, H2-004]. Budget split evenly between the two; each alone loses 2.85% to 22.75% [H2-003, H2-007].
- Focus is the token-generation phase [H2-002]. In the implementation prefill runs in full, then K heavy hitters + K recent tokens are kept [H2-006].
- Attention is over 95% sparse at inference in almost all layers [H2-005].
- Models: OPT (30B and 66B named in figures; 6.7B/13B/30B in throughput runs), LLaMA 7B/13B/30B, GPT-NeoX-20B; text claims sizes up to 175B but no 175B result is shown [H2-050, H2-051, H2-039, H2-063].
- White-box OPT engine modified; evicted slots overwritten in place [H2-010, H2-011]. Output is a smaller KV cache, not text [H2-013]. No API/closed model discussion [H2-012]. No fine-tuning, though the phrase "training-free" is not used [H2-009].

Compression and quality
- Headline: 5-10x smaller KV cache with comparable accuracy; budgets 4/10/20/60% of prompt length [H2-020, H2-021, H2-022].
- Table 1 (5-shot, model not named in caption): H2O 79.22/85.00/43.80/71.67 vs Full 80.09/81.00/44.80/71.51; Local 57.94/56.00/28.40/51.30 [H2-032, H2-033, H2-034].
- OPT-30B 20%: COPA 84.00 vs Full 85.00, PiQA 78.45 vs 78.51; Local-only 55.82, H2-only 67.25 on PiQA [H2-036, H2-037, H2-035]. Longer shots hold (OpenBookQA 10-shot) [H2-041, H2-041b]. MathQA tested [H2-111].
- Summarization (XSUM, CNN/DM; 1000 test samples, zero-shot) reported only as plots, LLaMA-7B/13B/30B and GPT-NeoX-20B; no numbers or metric in text [H2-038, H2-039, H2-031, H2-031b]. Authors' qualitative claim: dropping critical KV entries causes severe collapse [H2-040].
- Short prompts need 30-40% budget (0/1-shot, 100-300 tokens) [H2-023].
- Streaming mode up to four million tokens (PG-19 perplexity) [H2-024]. Throughput/latency benchmarks at up to 10K tokens [H2-079].
- Cross-paper: SnapKV's authors say H2O overlooks prompt-KV compression, while H2O's appendix pseudocode compresses the prompt KV at prefill [H2-093, H2-006]; SnapKV authors' re-run with a 4096 budget on Mistral/Mixtral/LWM shows large QA/code losses vs full KV (Mixtral HotpotQA 34.76 vs 47.77, Lcc 64.91 vs 69.07) and vs SnapKV 1024 [H2-042, SK-041, SK-042, SK-039, SK-044]; EHPC authors' re-run shows PassageRetrieval collapse [EH-058, EH-059, EH-064].

Latency, throughput, hardware
- Quality on one A100 80GB; throughput on T4 16GB and A100 80GB [H2-060, H2-061]. Timing is end-to-end including prefill and H2O cache construction [H2-062].
- Headline: up to 29x/29x/3x throughput vs DeepSpeed/Accelerate/FlexGen, up to 1.9x lower latency at equal batch [H2-063, H2-063b]. The big factors come from larger batches and avoiding CPU offload [H2-077, H2-076].
- T4 (Table 3, 512+32...512+1024): FlexGen 20.2/8.1/16.8/8.5/16.9/7.1 tok/s vs H2O 35.1/12.7/51.7/18.83/52.1/13.82; Accelerate 30B 0.6 tok/s [H2-064, H2-065, H2-066, H2-067]. XSUM on T4: FlexGen 10.80/3.29 vs H2O 30.40/6.70 [H2-068, H2-069].
- A100 (Table 5): 7000+1024 30B batch 1 57.0 s vs 50.4 s; 5000+5000 13B 214.2 vs 155.4 s; 2048+2048 6.7B batch 24 99.5 vs 53.5 s and 494.1 vs 918.9 tok/s; batch 64 FlexGen OOM vs 1161.0 [H2-070, H2-071, H2-072, H2-073, H2-074, H2-075].
- 180GB KV example (30B, batch 128, length 1024) [H2-078]. Per-request token savings: none (prompt untouched) [H2-080].

Limitations, reproducibility, tasks
- Authors' limitations: only a note on parameter count/MLP heavy hitters; bias of accumulated score toward older tokens; averaging hurt [H2-090, H2-008].
- Tested: HELM XSUM/CNN-DM, lm-eval COPA/MathQA/OpenBookQA/PiQA/RTE/Winogrande, multi-doc QA (plot only). Not tested: coding, multi-turn chat, structured data, PII, Needle-in-a-Haystack/LongBench [H2-030, H2-092, H2-110].
- Code at github.com/FMInference/H2O, license badge MIT [H2-100, H2-101].

## SnapKV (Li et al., arXiv 2404.14469)

Mechanism and I/O
- Fine-tuning-free; per head it keeps top-voted prefix positions (pooled/clustered) plus every KV in the last-window observation window; constant prompt-KV size during generation [SK-001, SK-002, SK-003, SK-004].
- Compression is applied once after prompt processing; no updates while decoding [SK-005, SK-008]. Selection depends on the instruction, so a cache compressed for one question is not shown to serve other questions (inferred from mechanism) [SK-007].
- Qualitative outputs for SAMSum/Qasper/HotpotQA at 1024/2048/4096 are in Appendix B [SK-082].
- Failure example: country code retrieved, rest of phone number hallucinated without pooling [SK-006]; pooling ablation on LongEval-Lines [SK-051].
- Needs source-level change to attention code (few lines in HuggingFace) [SK-010, SK-011]; open-weight models only (LWM-Text-Chat-1M 7B, LongChat, Mistral-7B, Mixtral-8x7B, Command-R 35B); no API discussion [SK-012, SK-013, SK-014, SK-015].
- Hyper-parameters: pooling 5/window 16 (NIAH), 7/32 (LongBench), 13/64 (Command-R) [SK-009, SK-009b, SK-009c].

Compression and quality
- LongBench budgets 1024/2048/4096 on ~13k-token inputs: 92% / 68% compression [SK-020]. NIAH: KV 1024, up to 380k tokens, "380x" [SK-021, SK-021b, SK-080]. Command-R 2x-32x, RAG 5-10x and ~4x [SK-022, SK-023, SK-024].
- Mistral full KV vs SnapKV 1024/2048/4096: GovReport 32.85 vs 25.89/28.81/30.74; code Lcc 55.51 vs 55.65/55.93/55.62; RB-P 52.88 vs 51.87/52.01/52.65 [SK-031, SK-032, SK-034, SK-033]. Code is essentially unchanged; summarization (GovReport) is the clearest loss, also LWM (27.97 vs 19.79) and Mixtral (34.25 vs 27.77) at 1024 [SK-035, SK-036, SK-039, SK-040, SK-037, SK-038]. Authors still call the drop "negligible" [SK-043].
- vs H2O (budget 4096, run by SnapKV authors): SnapKV 1024 wins 11 of 16 on Mistral [SK-044, SK-041, SK-042].
- Needle-in-a-Haystack (Command-R, up to 128k): 9.866 vs 9.819 (-0.5%) [SK-045, SK-046]. RAG: citation F1 -1.2%, end-to-end F1 -2.1%, bioasq 200 docs +5.4% (authors suggest noise removal) [SK-047, SK-048, SK-049, SK-050].

Latency, memory, hardware
- A100 80GB. At 16k input, batch 2, baseline >100 ms/token vs <40 ms, 3.6x; OOM beyond 16k vs 131k tokens, 8.2x [SK-060, SK-061, SK-063, SK-064, SK-062]. Original implementation OOM at 33k vs 380k handled [SK-065, SK-080].
- Prefill is not accelerated: "SnapKV's design does not cover the processing of the prompt inference" [SK-066]; generation dominates total time (plot only) [SK-067]. With Medusa: 1.3x vs Medusa, 2.2x vs native at 10k [SK-068].
- Cost: no prompt-token reduction, so no API-token saving [SK-070].

Limitations, reproducibility, tasks
- Cannot extend a model's long-context ability; scope limited to the generative KV cache [SK-069, SK-015].
- Tested: LongBench (all categories incl. code), NIAH, LongEval-Lines, RAG on Command-R, QASPER with Medusa. Multi-turn chat only for attention observation. Not tested: math/reasoning, structured data, PII [SK-100, SK-101, SK-102, SK-103, SK-104].
- Paper has no link to its own code; repo is Apache-2.0 and supports Llama, Mistral, Mixtral [SK-090, SK-091].

## Not reported
- EHPC: target LLM for Table 4 [EH-026]; GPU model [EH-087]; measured NMI memory/throughput [EH-093]; dollar cost [EH-101]; NIAH accuracy [EH-111]; code/checkpoints/license [EH-120, EH-121]; limitations section (absent); multi-turn chat, structured data, math, PII (not tested) [EH-136].
- H2O: any closed/API discussion [H2-012]; numeric XSUM/CNN-DM and multi-doc QA scores and the metric [H2-038, H2-092]; AlpacaEval/MT-bench results despite being mentioned [H2-091]; OPT-175B results despite "6.7B to 175B" claim [H2-050]; separate prefill-latency numbers [H2-062]; model for Table 1 [H2-032]; coding/chat/PII/structured tests [H2-110].
- SnapKV: closed/API discussion [SK-015]; prompting-latency numbers (plot) [SK-067]; internal tool-use benchmark numbers [SK-081]; own code link in the paper [SK-090]; math/structured/PII tests [SK-103].

## Article vs paper disagreements (ids)
- Papers now located [AR-001]. EHPC grouped with KV-cache methods [AR-002, AR-003]. "Processing Stage: During inference" [AR-004]. "API-Based Deployments" and "API Compatibility" [AR-005, AR-006]. "Work with any Transformer-based model" [AR-007]. "Training-Free" [AR-008]. "Dynamic compression during inference" [AR-009]. EHPC "early layers" [AR-010]. EHPC "only tokens with high attention scores" [AR-011]. H2O/SnapKV "retaining only high-attention tokens", article and README [AR-012, AR-013]. "Without modification" and "where model modification is not possible" [AR-014, AR-015].

## Unverified or ambiguous table columns
- EHPC Table 4: column "Avg." for EHPC rows is lower than the mean of its six category columns (my arithmetic: 50.70 vs printed 49.7 at 3,000; 50.38 vs 49.6 at 2,000); for the other methods the mean matches the printed Avg within rounding (LLMLingua-2: 42.38 vs 42.2). Cause not explained [EH-041, EH-042, EH-045].
- EHPC Table 4: "1/tau" ratio header is garbled in the extracted text (read as the x-fold ratio from the "3x/5x" cells); the 2,000 constraint row for EHPC is 2,004 tokens [EH-039, EH-112].
- EHPC Table 5: first row is labelled LLMLingua-2 but its 7.51 s matches LLMLingua in Table 1; Table 5 header columns read "compression time / inference time (2048 tokens) / total" [EH-082, EH-083].
- EHPC Table 6: printed Average equals the plain mean of the 16 columns only for H2O rows (my arithmetic); e.g. Llama All KV mean 38.50 vs printed 38.32, SnapKV-1024 37.14 vs 35.25, EHPC-1024 36.56 vs 35.23, EHPC-2048 37.92 vs 37.86. Using recomputed means SnapKV-1024 (37.14) is above EHPC-1024 (36.56) on Llama, even more than with printed averages (35.25 vs 35.23), so "best average at every budget" depends on the printed averages [EH-053, EH-054, EH-055, EH-056, EH-065].
- EHPC Table 6: Llama-3.1 full-KV QA columns (e.g. Qasper 13.04) are far below the Table 4 original-prompt QA category averages, so the "up to 40% QA gain" on Phi is over a baseline that the paper does not discuss (Phi full KV SAMSum 13.08); the sentence about target lengths "for prompt compression and KV cache compression respectively" is ambiguous [EH-053, EH-060, EH-068, EH-069].
- EHPC footnote 1 links Meta-Llama-3-8B while the text says Llama-3.1-8B [EH-025].
- H2O Table 1: caption does not name the model; Table 3/5 brackets give (effective batch, memory tier), so throughput gain mixes batch-size and offload effects [H2-032, H2-066, H2-076].
- H2O Table 5 columns (FlexGen, H2O 20%) taken from the header; 29x is versus the slowest offloaded baselines [H2-070, H2-067].
- SnapKV Table 1: four model blocks (LWMChat, LongChat, Mistral, Mixtral) repeat the "All KV" label; blocks identified by row order under each model name; column order from the header [SK-030, SK-031, SK-035, SK-037, SK-039].
- SnapKV Tables 3-4 report relative % differences only (no absolute F1/accuracy) [SK-047, SK-048, SK-049].
