# Sensitivity head: evaluation

Encoder `sentence-transformers/all-MiniLM-L6-v2` + logistic regression (C=4.0, balanced), trained on 385 prompts (164 sensitive). Threshold 0.36 = largest with 5-fold out-of-fold recall >= 0.95 (CV recall 0.951, CV FPR 0.154).

Decision columns: `rules` = rules.py, `topics` = topics.py, `head` = this classifier at the threshold.

| set | decision | recall | FPR | flagged sensitive | flagged other |
|---|---|---|---|---|---|
| test | rules | 0.459 | 0.0 | 17/37 | 0/111 |
| test | rules or topics | 0.946 | 0.009 | 35/37 | 1/111 |
| test | rules or head | 0.973 | 0.09 | 36/37 | 10/111 |
| test | rules or topics or head | 0.973 | 0.099 | 36/37 | 11/111 |
| holdout | rules | 0.0 | 0.0 | 0/40 | 0/60 |
| holdout | rules or topics | 0.3 | 0.017 | 12/40 | 1/60 |
| holdout | rules or head | 1.0 | 0.1 | 40/40 | 6/60 |
| holdout | rules or topics or head | 1.0 | 0.117 | 40/40 | 7/60 |
| qa_prose | rules | - | 0.0 | 0/0 | 0/112 |
| qa_prose | rules or topics | - | 0.0 | 0/0 | 0/112 |
| qa_prose | rules or head | - | 0.0 | 0/0 | 0/112 |
| qa_prose | rules or topics or head | - | 0.0 | 0/0 | 0/112 |
| qa_passages | rules | - | 0.0 | 0/0 | 0/360 |
| qa_passages | rules or topics | - | 0.0 | 0/0 | 0/360 |
| qa_passages | rules or head | - | 0.006 | 0/0 | 2/360 |
| qa_passages | rules or topics or head | - | 0.006 | 0/0 | 2/360 |
| pii_notes | rules | 1.0 | - | 50/50 | 0/0 |
| pii_notes | rules or topics | 1.0 | - | 50/50 | 0/0 |
| pii_notes | rules or head | 1.0 | - | 50/50 | 0/0 |
| pii_notes | rules or topics or head | 1.0 | - | 50/50 | 0/0 |
| playground | rules | - | 0.0 | 0/0 | 0/1 |
| playground | rules or topics | - | 0.0 | 0/0 | 0/1 |
| playground | rules or head | - | 0.0 | 0/0 | 0/1 |
| playground | rules or topics or head | - | 0.0 | 0/0 | 0/1 |

Mean scoring time 30.0 ms per text (encoder + head, this CPU, includes chunking).

**test: missed by rules or topics or head (1)**
- Slack webhook: https://hooks.slack.com/services/[SLACK_WEBHOOK_TOKEN]

**test: false alarms (11)**
- Rename the column `cust_nm` to `customer_name` in all migrations, but not in the legacy view.
- SELECT customer_id, SUM(amount) FROM payments WHERE created_at >= '2024-01-01' GROUP BY customer_id HAVING SUM(amount) > 1000;
- Set max_tokens to 512, temperature to 0, and stop on the sequence '###'.
- The contract term is 36 months starting 2025-02-01 with a 90-day notice period. When is the last day to cancel?
- Dosage rule: children under 12 get 5 mg/kg, max 250 mg per dose, every 8 hours. A 30 kg child needs how much?
- Cybersecurity awareness month encourages people to learn about phishing and safe browsing.
- I hope this message finds you well.
- Hope your team is doing well too! Say hi to everyone for me.
- Yeah, I guess, maybe, we'll see.
- Ok that's it from me, see ya!
- It's been a crazy week, 5 meetings a day, you know how it is.

**holdout: missed by rules or topics or head (0)**
- none

**holdout: false alarms (7)**
- Our company reported revenue of $12.4 million in 2023, up 8 percent on the year before.
- The Supreme Court hears oral arguments from October through April.
- Mortgage rates in the country averaged 6.8 percent last month according to the national survey.
- Antibiotics do not work against viral infections such as the common cold.
- The board approved a dividend of 40 cents per share at the annual general meeting.
- The tax filing deadline for individuals is the end of January.
- The company's annual report lists its main risks as currency moves and energy prices.

Playground prompt score: 0.0188 (threshold 0.36).
