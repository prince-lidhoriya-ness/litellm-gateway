# Classifier benchmark, split=dev

| model | format | sensitive recall | sensitive precision | macro-F1 | accuracy | hard-neg acc | p50 ms | p95 ms | params |
|---|---|---|---|---|---|---|---|---|---|
| typeform/distilbert-base-uncased-mnli | plain | 0.389 | 0.200 | 0.185 | 0.250 | 0.3333 | 89.2 | 221.5 | 67M |
| typeform/distilbert-base-uncased-mnli | descriptive | 0.889 | 0.314 | 0.288 | 0.375 | 0.1111 | 152.0 | 236.5 | 67M |
| MoritzLaurer/deberta-v3-base-zeroshot-v2.0 | plain | 0.556 | 0.714 | 0.452 | 0.514 | 0.5556 | 375.1 | 530.5 | 184M |
| MoritzLaurer/deberta-v3-base-zeroshot-v2.0 | descriptive | 0.389 | 1.000 | 0.403 | 0.444 | 0.6667 | 385.9 | 509.3 | 184M |
| MoritzLaurer/DeBERTa-v3-base-mnli-fever-anli | plain | 0.722 | 0.464 | 0.470 | 0.514 | 0.8889 | 382.0 | 584.9 | 184M |
| MoritzLaurer/DeBERTa-v3-base-mnli-fever-anli | descriptive | 0.000 | 0.000 | 0.290 | 0.431 | 0.0 | 442.1 | 616.8 | 184M |
| MoritzLaurer/deberta-v3-xsmall-zeroshot-v1.1-all-33 | plain | 0.778 | 0.412 | 0.330 | 0.361 | 0.3333 | 109.0 | 150.4 | 71M |
| MoritzLaurer/deberta-v3-xsmall-zeroshot-v1.1-all-33 | descriptive | 0.000 | 0.000 | 0.274 | 0.361 | 0.4444 | 116.9 | 194.4 | 71M |
| MoritzLaurer/deberta-v3-base-zeroshot-v2.0@int8 | plain | 0.444 | 0.421 | 0.258 | 0.292 | 0.4444 | 254.2 | 393.7 | 99M |
| MoritzLaurer/deberta-v3-base-zeroshot-v2.0@int8 | descriptive | 0.000 | 0.000 | 0.120 | 0.153 | 0.2222 | 390.6 | 537.6 | 99M |
| MoritzLaurer/DeBERTa-v3-base-mnli-fever-anli@int8 | plain | 0.167 | 0.188 | 0.136 | 0.153 | 0.1111 | 280.9 | 456.0 | 99M |
| MoritzLaurer/DeBERTa-v3-base-mnli-fever-anli@int8 | descriptive | 0.167 | 0.600 | 0.200 | 0.250 | 0.3333 | 377.5 | 561.2 | 99M |
