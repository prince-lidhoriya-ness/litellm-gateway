# Sensitivity decision, split=dev

72 prompts, 18 gold-sensitive; model typeform/distilbert-base-uncased-mnli; the rules alone flag 8 of the 18 sensitive prompts (0.444). Latency per prompt p50 227 ms, p95 458 ms.

| threshold | sensitive recall | false-positive rate | hard negatives flagged | tp | fn | fp | tn |
|---|---|---|---|---|---|---|---|
| 0.99 | 0.444 | 0.000 | 0/7 | 8 | 10 | 0 | 54 |
| 0.6 | 0.556 | 0.000 | 0/7 | 10 | 8 | 0 | 54 |
| 0.5 | 0.722 | 0.148 | 0/7 | 13 | 5 | 8 | 46 |
| 0.4 | 0.889 | 0.500 | 4/7 | 16 | 2 | 27 | 27 |
| 0.35 (configured) | 1.000 | 0.759 | 6/7 | 18 | 0 | 41 | 13 |
| 0.3 | 1.000 | 0.907 | 7/7 | 18 | 0 | 49 | 5 |
| 0.25 | 1.000 | 0.963 | 7/7 | 18 | 0 | 52 | 2 |
| 0.2 | 1.000 | 0.981 | 7/7 | 18 | 0 | 53 | 1 |
