# Production-shaped examples through the LiteLLM proxy

Run on 2026-11-12 with `scripts/production_examples.py` against the benchmark proxy (`bench_config.yaml`,
profile `full`: compaction and JIT on, 6,000-token effective window). Raw data: `raw/production_examples.json`.

**Two conversations.**
- **Coding agent:** an incident fix with 7 tool definitions. The agent searches the error logs, greps, reads the view,
  the service (twice), the tests and the model, runs pytest (2 failures with tracebacks), reads `git log` and
  `git show`, applies a patch and re-runs the tests. The user then asks for the root cause, the commit and the result.
- **Support chat:** a policy system prompt with today's date, and a customer who says "email only, never by phone".
  The chat has two knowledge-base searches (RAG), order JSON, an explicit decision and 9 follow-up questions; the user
  then asks what was agreed.

**A "longer" variant of each continues the same session:**
- the agent reads 4 more files before patching;
- the support answers are as long as typical support-agent replies.

**How each request was run.** Every request went through the four configurations on the echo provider, which shows
exactly what reaches the model. Baseline and combined then went to the real model (local llama3.2:3b, CPU) for the
variants that fit its 8,192-token context. The final-answer requests were sent without tool definitions: with them,
llama3.2 answered the summary question with another tool call (first attempt, 35 tokens, empty text).

## What reached the model

| Example | Original | Compression only | CE only | Combined | What CE did |
|---|---|---|---|---|---|
| coding_agent (39 msgs) | 5,773 | 5,773 (0%) | 5,363 (−7.1%) | 5,363 (−7.1%) | folded the second, byte-identical read of `payments/refunds.py` |
| coding_agent_longer (51 msgs) | 8,532 | 8,532 (0%) | 6,388 (−25.1%) | 6,388 (−25.1%) | + masked the 4 oldest large tool outputs into verbatim key-line stubs |
| support_chat (32 msgs) | 2,499 | 2,167 (−13.3%) | 2,499 (0%) | 2,167 (−13.3%) | nothing: compaction skipped by its safety ratio (a 244-token summary for 315 tokens) |
| support_chat_longer (32 msgs) | 4,099 | 2,843 (−30.6%) | 3,626 (−11.5%) | 2,581 (−37.0%) | compacted 2 older turns into one summary; JIT kept the decision turn in full |

The table shows tokens per configuration (cl100k_base, including tool-call arguments).

**Exact strings, kept in every configuration** (6/6 and 4/4):
- **Coding agent:** `KeyError: 'currency'`, `payments/refunds.py:41`, `a41c9e2`, `currency=payment.currency`,
  `14 passed`, `PAY-2304`.
- **Support chat:** `ORD-48213`, `ESP-2200-STL`, `never by phone`, `JD014600003829471`.
- **Everywhere:** tool-call ids and the latest question were unchanged.

**Why the shorter variants change little.** Masking keeps the newest 3 large outputs and advances in batches of 4, so
it starts at the 7th large output; this keeps the cached prompt prefix stable between turns. Compaction is not used when
its summary would save less than 30% of the span. Both are designed limits.

**The tool-heavy agent session gains only from CE.** Compression never touches tool outputs, so it saved nothing on
the coding agent. On the long support chat, compression and compaction add up: −37.0% together, against −30.6% and
−11.5% alone.

Example of a stub (coding_agent_longer):

```
[gateway: observation obs_6e176b2cc3cb masked by gateway | tool=search_logs | 1157 tokens, 24 lines | original stored]
Key lines (verbatim):
2026-11-12T08:00:11Z ERROR payments.api POST /v1/payments/pay_7000/refunds 500 KeyError('currency') request_id=req-0a0000 amount=5.00
...
[Full output omitted to save context. To restore it, mention obs_6e176b2cc3cb in a message, or call the tool again.]
```

## Real-model answers (llama3.2:3b, baseline vs combined)

| Example | Config | Provider prompt tokens | Latency | Required facts in the answer |
|---|---|---|---|---|
| coding_agent | baseline | 5,599 | 440 s | KeyError, a41c9e2, 14 (3/3) |
| coding_agent | combined | 5,189 | 213 s | KeyError, a41c9e2, 14 (3/3) |
| support_chat | baseline | 2,520 | 227 s | replacement, email (2/2) |
| support_chat | combined | 2,188 | 154 s | replacement, email (2/2) |
| support_chat_longer | baseline | 4,120 | 324 s | replacement, email (2/2) |
| support_chat_longer | combined | 2,594 | 260 s | replacement, email (2/2) |

Provider prompt tokens are Ollama's own count.

**Answer quality was the same.**
- Every answer named the root cause, the commit and the test count, or the replacement and the email-only contact.
- The combined answer to the short support chat even repeated "only by email, and not by phone" verbatim.
- coding_agent_longer (8,532 tokens) was not sent to the model, because it exceeds the local model's context in the
  baseline.

## Caveats

- **Latencies are single runs on a shared CPU.** The background quality benchmark used Ollama on the same 8 cores
  during this run, so the absolute times are inflated and noisy. The direction (combined faster) matches the
  benchmark, but these six requests are not a latency measurement.
- **Fail-open under load.** In one earlier pass of this script (echo only), the compression stage hit its 10 s timeout
  twice under that load and **failed open**: it forwarded the original prompt, logged `prompt_pipeline.fail_open`, and
  the request still succeeded. Context engineering's own savings were unaffected. In the run above, compression
  finished in time.
