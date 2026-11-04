# Classifier benchmark, split=test

| model | format | sensitive recall | sensitive precision | macro-F1 | accuracy | hard-neg acc | p50 ms | p95 ms | params |
|---|---|---|---|---|---|---|---|---|---|
| typeform/distilbert-base-uncased-mnli | descriptive | 0.919 | 0.374 | 0.307 | 0.399 | 0.3333 | 139.6 | 194.4 | 67M |
| MoritzLaurer/deberta-v3-base-zeroshot-v2.0 | descriptive | 0.460 | 1.000 | 0.445 | 0.480 | 0.5556 | 450.1 | 691.5 | 184M |
| MoritzLaurer/DeBERTa-v3-base-mnli-fever-anli | descriptive | 0.054 | 0.500 | 0.322 | 0.446 | 0.2778 | 468.3 | 763.6 | 184M |
| MoritzLaurer/deberta-v3-xsmall-zeroshot-v1.1-all-33 | descriptive | 0.000 | 0.000 | 0.284 | 0.351 | 0.3889 | 139.8 | 213.6 | 71M |
| MoritzLaurer/deberta-v3-base-zeroshot-v2.0 | plain | 0.405 | 0.714 | 0.392 | 0.453 | 0.5 | 343.2 | 495.6 | 184M |
| MoritzLaurer/DeBERTa-v3-base-mnli-fever-anli | plain | 0.730 | 0.509 | 0.519 | 0.534 | 0.5 | 381.3 | 892.3 | 184M |
| MoritzLaurer/deberta-v3-xsmall-zeroshot-v1.1-all-33 | plain | 0.811 | 0.370 | 0.291 | 0.331 | 0.2778 | 129.7 | 213.3 | 71M |
| typeform/distilbert-base-uncased-mnli | full-pipeline | 0.540 | 0.870 | 0.333 | 0.392 | 0.1667 | 114.7 | 162.9 | - |
