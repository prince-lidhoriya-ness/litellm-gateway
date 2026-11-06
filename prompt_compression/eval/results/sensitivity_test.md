# Sensitivity decision, split=test

148 prompts, 37 gold-sensitive; model typeform/distilbert-base-uncased-mnli; the rules alone flag 17 of the 37 sensitive prompts (0.459). Latency per prompt p50 249 ms, p95 741 ms.

| threshold | sensitive recall | false-positive rate | hard negatives flagged | tp | fn | fp | tn |
|---|---|---|---|---|---|---|---|
| 0.99 | 0.459 | 0.000 | 0/14 | 17 | 20 | 0 | 111 |
| 0.6 | 0.486 | 0.027 | 0/14 | 18 | 19 | 3 | 108 |
| 0.5 | 0.595 | 0.090 | 0/14 | 22 | 15 | 10 | 101 |
| 0.4 | 0.865 | 0.459 | 4/14 | 32 | 5 | 51 | 60 |
| 0.35 (configured) | 0.973 | 0.676 | 9/14 | 36 | 1 | 75 | 36 |
| 0.3 | 1.000 | 0.838 | 10/14 | 37 | 0 | 93 | 18 |
| 0.25 | 1.000 | 0.937 | 13/14 | 37 | 0 | 104 | 7 |
| 0.2 | 1.000 | 0.964 | 13/14 | 37 | 0 | 107 | 4 |
