# Pipeline evaluation (local), sensitivity check: real

Real pipeline, real LLMLingua-2 on CPU, target llama3.2:3b through Ollama, the report's prompts and baseline (reports/compression-fit/raw/llm_runs.jsonl). Accuracy = the reference string appears in the answer; Wilson 95% interval; exact McNemar against the baseline on the same items. A prompt the router leaves byte for byte unchanged reuses the baseline answer (column 'prompt changed').

| family | condition | items | accuracy [95% Wilson] | diff vs baseline | McNemar p | prompt changed | token ratio | router ms, mean |
|---|---|---|---|---|---|---|---|---|
| qa | baseline (uncompressed) | 40 | 1.000 [0.912, 1.000] | - | - | - | 1.00x | - |
| qa | default | 40 | 1.000 [0.912, 1.000] | +0.000 | 1.000 | 18/40 | 1.06x | 1478 |
| qa | aggressive | 40 | 1.000 [0.912, 1.000] | +0.000 | 1.000 | 14/40 | 1.05x | 1402 |
| qa | passages | 40 | 1.000 [0.912, 1.000] | +0.000 | 1.000 | 29/40 | 1.39x | 1840 |
| logs | baseline (uncompressed) | 40 | 1.000 [0.912, 1.000] | - | - | - | 1.00x | - |
| logs | default | 40 | 1.000 [0.912, 1.000] | +0.000 | 1.000 | 0/40 | 1.00x | 248 |
| logs | aggressive | 40 | 1.000 [0.912, 1.000] | +0.000 | 1.000 | 0/40 | 1.00x | 10 |
| logs | records | 40 | 1.000 [0.912, 1.000] | +0.000 | 1.000 | 40/40 | 2.95x | 8 |
| code | baseline (uncompressed) | 40 | 0.875 [0.739, 0.945] | - | - | - | 1.00x | - |
| code | default | 40 | 0.875 [0.739, 0.945] | +0.000 | 1.000 | 0/40 | 1.00x | 208 |
| code | aggressive | 40 | 0.875 [0.739, 0.945] | +0.000 | 1.000 | 0/40 | 1.00x | 11 |

Sensitive records: the deterministic rules alone flag 50 of 50 synthetic case notes, which the pipeline then never compresses (the NLI classifier adds to this).
