# Sensitivity head: evaluation

Encoder `sentence-transformers/all-MiniLM-L6-v2` + logistic regression (C=4.0, balanced), trained on 345 prompts (150 sensitive). Threshold 0.37 = largest with 5-fold out-of-fold recall >= 0.95 (CV recall 0.953, CV FPR 0.149).

Decision columns: `rules` = rules.py, `topics` = topics.py, `head` = this classifier at the threshold.

| set | decision | recall | FPR | flagged sensitive | flagged other |
|---|---|---|---|---|---|
| test | rules | 0.459 | 0.0 | 17/37 | 0/111 |
| test | rules or topics | 0.946 | 0.009 | 35/37 | 1/111 |
| test | rules or head | 0.973 | 0.072 | 36/37 | 8/111 |
| test | rules or topics or head | 0.973 | 0.072 | 36/37 | 8/111 |
| holdout | rules | 0.0 | 0.0 | 0/40 | 0/60 |
| holdout | rules or topics | 0.3 | 0.017 | 12/40 | 1/60 |
| holdout | rules or head | 1.0 | 0.067 | 40/40 | 4/60 |
| holdout | rules or topics or head | 1.0 | 0.083 | 40/40 | 5/60 |
| qa_prose | rules | - | 0.0 | 0/0 | 0/112 |
| qa_prose | rules or topics | - | 0.0 | 0/0 | 0/112 |
| qa_prose | rules or head | - | 0.0 | 0/0 | 0/112 |
| qa_prose | rules or topics or head | - | 0.0 | 0/0 | 0/112 |
| pii_notes | rules | 1.0 | - | 50/50 | 0/0 |
| pii_notes | rules or topics | 1.0 | - | 50/50 | 0/0 |
| pii_notes | rules or head | 1.0 | - | 50/50 | 0/0 |
| pii_notes | rules or topics or head | 1.0 | - | 50/50 | 0/0 |
| playground | rules | - | 0.0 | 0/0 | 0/1 |
| playground | rules or topics | - | 0.0 | 0/0 | 0/1 |
| playground | rules or head | - | 0.0 | 0/0 | 0/1 |
| playground | rules or topics or head | - | 0.0 | 0/0 | 0/1 |

Mean scoring time 16.4 ms per text (encoder + head, this CPU, includes chunking).

**test: missed by rules or topics or head (1)**
- Slack webhook: https://hooks.slack.com/services/[SLACK_WEBHOOK_TOKEN]

**test: false alarms (8)**
- Rename the column `cust_nm` to `customer_name` in all migrations, but not in the legacy view.
- SELECT customer_id, SUM(amount) FROM payments WHERE created_at >= '2024-01-01' GROUP BY customer_id HAVING SUM(amount) > 1000;
- Set max_tokens to 512, temperature to 0, and stop on the sequence '###'.
- The contract term is 36 months starting 2025-02-01 with a 90-day notice period. When is the last day to cancel?
- Dosage rule: children under 12 get 5 mg/kg, max 250 mg per dose, every 8 hours. A 30 kg child needs how much?
- Cybersecurity awareness month encourages people to learn about phishing and safe browsing.
- I hope this message finds you well.
- Yeah, I guess, maybe, we'll see.

**holdout: missed by rules or topics or head (0)**
- none

**holdout: false alarms (5)**
- Our company reported revenue of $12.4 million in 2023, up 8 percent on the year before.
- Mortgage rates in the country averaged 6.8 percent last month according to the national survey.
- Antibiotics do not work against viral infections such as the common cold.
- The board approved a dividend of 40 cents per share at the annual general meeting.
- The tax filing deadline for individuals is the end of January.

Playground prompt score: 0.0156 (threshold 0.37).
