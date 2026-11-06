# Gateway router evaluation (local)

Real pipeline, real LLMLingua-2 on CPU, target llama3.2:3b through Ollama, the report's prompts and baseline (reports/compression-fit/raw/llm_runs.jsonl). Classifier stubbed to let every message through. Accuracy = the reference string appears in the answer; Wilson 95% interval; exact McNemar against the baseline on the same items. A prompt the router leaves byte for byte unchanged reuses the baseline answer (column 'prompt changed').

| family | condition | items | accuracy [95% Wilson] | diff vs baseline | McNemar p | prompt changed | token ratio | router ms, mean |
|---|---|---|---|---|---|---|---|---|
| qa | baseline (uncompressed) | 40 | 1.000 [0.912, 1.000] | - | - | - | 1.00x | - |
| qa | default | 40 | 0.950 [0.835, 0.986] | -0.050 | 0.500 | 40/40 | 1.21x | 1374 |
| qa | aggressive | 40 | 0.900 [0.769, 0.960] | -0.100 | 0.125 | 39/40 | 1.35x | 2723 |
| qa | passages | 40 | 0.975 [0.871, 0.996] | -0.025 | 1.000 | 40/40 | 1.77x | 804 |
| logs | baseline (uncompressed) | 40 | 1.000 [0.912, 1.000] | - | - | - | 1.00x | - |
| logs | default | 40 | 1.000 [0.912, 1.000] | +0.000 | 1.000 | 0/40 | 1.00x | 5 |
| logs | aggressive | 40 | 1.000 [0.912, 1.000] | +0.000 | 1.000 | 0/40 | 1.00x | 4 |
| logs | records | 40 | 1.000 [0.912, 1.000] | +0.000 | 1.000 | 20/40 | 1.65x | 4 |
| code | baseline (uncompressed) | 40 | 0.875 [0.739, 0.945] | - | - | - | 1.00x | - |
| code | default | 40 | 0.875 [0.739, 0.945] | +0.000 | 1.000 | 0/40 | 1.00x | 4 |
| code | aggressive | 40 | 0.875 [0.739, 0.945] | +0.000 | 1.000 | 0/40 | 1.00x | 4 |

Sensitive records: the deterministic rules alone flag 50 of 50 synthetic case notes, which the pipeline then never compresses (the NLI classifier adds to this).
