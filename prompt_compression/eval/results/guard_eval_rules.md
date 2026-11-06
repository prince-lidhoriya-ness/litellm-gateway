# Pipeline evaluation (local), sensitivity check: rules

Real pipeline, real LLMLingua-2 on CPU, target llama3.2:3b through Ollama, the report's prompts and baseline (reports/compression-fit/raw/llm_runs.jsonl). Accuracy = the reference string appears in the answer; Wilson 95% interval; exact McNemar against the baseline on the same items. A prompt the router leaves byte for byte unchanged reuses the baseline answer (column 'prompt changed').

| family | condition | items | accuracy [95% Wilson] | diff vs baseline | McNemar p | prompt changed | token ratio | router ms, mean |
|---|---|---|---|---|---|---|---|---|
| qa | baseline (uncompressed) | 40 | 1.000 [0.912, 1.000] | - | - | - | 1.00x | - |
| qa | default | 40 | 1.000 [0.912, 1.000] | +0.000 | 1.000 | 32/40 | 1.12x | 1529 |
| qa | aggressive | 40 | 1.000 [0.912, 1.000] | +0.000 | 1.000 | 25/40 | 1.10x | 3148 |
| qa | passages | 40 | 1.000 [0.912, 1.000] | +0.000 | 1.000 | 40/40 | 1.64x | 529 |
| logs | baseline (uncompressed) | 40 | 1.000 [0.912, 1.000] | - | - | - | 1.00x | - |
| logs | default | 40 | 1.000 [0.912, 1.000] | +0.000 | 1.000 | 0/40 | 1.00x | 27 |
| logs | aggressive | 40 | 1.000 [0.912, 1.000] | +0.000 | 1.000 | 0/40 | 1.00x | 24 |
| logs | records | 40 | 1.000 [0.912, 1.000] | +0.000 | 1.000 | 40/40 | 2.95x | 22 |
| code | baseline (uncompressed) | 40 | 0.875 [0.739, 0.945] | - | - | - | 1.00x | - |
| code | default | 40 | 0.875 [0.739, 0.945] | +0.000 | 1.000 | 0/40 | 1.00x | 17 |
| code | aggressive | 40 | 0.875 [0.739, 0.945] | +0.000 | 1.000 | 0/40 | 1.00x | 16 |

Sensitive records: the deterministic rules alone flag 50 of 50 synthetic case notes, which the pipeline then never compresses (the NLI classifier adds to this).
