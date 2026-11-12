# prompt_compression

A prompt-compression pipeline for every `chat/completions` request that passes through the LiteLLM proxy. It follows
one architecture, stage by stage:

```
Client request  (messages + metadata)
      |
      v
 Redact (optional) ----- REDACT_SENSITIVE: every message and role, before everything else; an error rejects (503)
      |
      v
 Gate ------------------ opt-out, size, admission, deadline -- on a timeout or an error: Fail open (send the original)
      |
      v
 Segment and classify -- content type (code, structured data, identifier-dense text, prose) and sensitivity
      |
      v
 Router ---------------- the task type picks the action
      |
      +--> Keep verbatim   code, data, PII, the instruction and the question
      +--> Select or drop  whole old turns; passages and log lines of the latest user message, lookups only
      +--> Compress text   running prose through LLMLingua-2, 3x cap
      |
      v
 Reassemble in order --- ratio and tokens logged
      |
      v
 Model  (closed API or local)            (shadow mode: the model gets the original)
```

The design and the evidence behind every choice are in
[`../reports/compression-fit/REPORT.md`](../reports/compression-fit/REPORT.md), sections 4 and 7. The short version:
token-level compression damaged exactly the text that is read for exact strings (log field names, identifiers, dates,
names), so only running prose is compressed, at a modest ratio, and whole units are dropped instead of pruned.

There is no importance label any more. An earlier version asked a zero-shot classifier whether a *message* was
`critical`, `non_sensitive` or `less_important` and compressed only the last two; with the shipped model most prompts
scored below its confidence floor and fell back to `critical`, so almost nothing was compressed. What matters now is
what kind of text a block is, and whether it is sensitive.

## Layout

| Stage | File | Purpose |
|---|---|---|
| Redact | `redaction.py` | Redaction guardrail over every message and role (`REDACT_SENSITIVE=true`) |
| Gate | `gate.py` | Disabled, not a chat call, per-request opt-out; too few / too many tokens (`size_check`, in the worker) |
| Gate, Fail open | `prompt_compression_callback.py` | LiteLLM `CustomLogger.async_pre_call_hook`: redaction, admission, bounded worker pool, deadline and timeout, fail open / closed, shadow mode, metadata, logging |
| | `deadline.py` | The request deadline every model call checks; lock waits bounded by it |
| Router | `intent.py` | Lookup or transform (summarise, translate, review ...): selection only runs for lookups |
| Segment and classify | `segmenter.py` | Splits a message into blocks and says what each is; never changes a character |
| | `rules.py` | Regex + checksum rules (e-mail, phone, IDs, Luhn cards, IBAN, keys, tokens, private keys, passwords); `redact()` |
| | `sensitivity.py` | Sensitive or not: rules, then topics, then the model's probability against a threshold |
| | `topics.py` | Sensitive-topic lexicon (health, personal money, legal, identity, abuse, employment, non-public news) |
| | `embedding_classifier.py` | Default model: all-MiniLM-L6-v2 embedding + trained logistic-regression head (`models/sensitivity_head.json`) |
| | `labels.py` | Candidate labels of the legacy zero-shot backend (`SENSITIVITY_BACKEND=nli`) |
| Router | `router.py` | Decides keep / select / compress for every unit, and which old turns to drop |
| Actions | `actions.py` | Carries the plan out: redaction, record and passage selection, LLMLingua-2 with a ratio cap |
| | `selectors.py` | BM25 passage ranking, record (line) selection, chat-history trimming |
| | `compressor_adapter.py` | Thin wrapper over `llmlingua.PromptCompressor` (LLMLingua-2, CPU): pinned revision, deadline-bounded lock, output cache |
| Reassemble | `pipeline.py` | Runs the stages over `messages`, joins the blocks back in order, builds the report |
| shared | `units.py`, `texts.py`, `settings.py` | The unit passed between stages, message/token helpers, all environment variables |
| | `eval/` | Datasets, benchmarks, saved results |
| | `tests/` | pytest suite |
| | `dev/` | Mock OpenAI-compatible provider and an end-to-end verification client |

## Setup

Python 3.12, CPU only. From the gateway folder (`litellm-gateway/`):

```bash
python -m venv .venv-compression
.venv-compression/Scripts/python -m pip install torch==2.15.0 --index-url https://download.pytorch.org/whl/cpu
.venv-compression/Scripts/python -m pip install -r prompt_compression/requirements.txt
```

Start the proxy (models download from the Hugging Face Hub on first start, then load once):

```bash
.venv-compression/Scripts/litellm --config config.yaml --port 4000
```

`config.yaml` registers the hook:

```yaml
litellm_settings:
  callbacks: ["prompt_compression.prompt_compression_callback.prompt_compression_instance"]
```

LiteLLM 1.106.0 resolves that dotted path relative to the config file and loads
`prompt_compression/prompt_compression_callback.py`; the module adds the gateway folder to `sys.path` so the package
imports work. LiteLLM only calls a callback whose own class defines `async_pre_call_hook`, so a subclass of the hook
has to define it too, even if it only delegates (`observability/observed_callback.py` does).

## Environment variables

All optional; `../prompt_compression.env.example` lists every variable with its default and a comment.

| Stage | Variable | Default | Meaning |
|---|---|---|---|
| Gate | `PROMPT_COMPRESSION_ENABLED` | `true` | Global switch |
| | `PROMPT_COMPRESSION_MIN_TOKENS` | `50` | Requests with fewer text tokens skip the pipeline |
| | `PROMPT_COMPRESSION_MAX_INPUT_TOKENS` | `32000` | Requests with more text tokens skip the pipeline (`too_large`); 0 = no limit |
| | `PROMPT_COMPRESSION_MAX_CONCURRENCY` | `4` | Pipelines at once per worker; above it a request is sent unchanged (`busy`) |
| | `PROMPT_COMPRESSION_TIMEOUT_S` | `10` | Budget for the whole pipeline per request; model work stops at 90% of it |
| | `PROMPT_COMPRESSION_FAIL_MODE` | `open` | `open`: send the original prompt + warning; `closed`: reject with HTTP 503 |
| | `PROMPT_COMPRESSION_MODE` | `enforce` | `shadow`: run and report everything but send the original prompt |
| Classify | `SENSITIVITY_BACKEND` | `embedding` | `embedding` (trained head) or `nli` (legacy zero-shot model) |
| | `SENSITIVITY_THRESHOLD` | head: `0.36` | Probability at or above this keeps a text verbatim (empty = backend default; nli: 0.35) |
| | `CLASSIFIER_MODEL` / `_LABEL_FORMAT` / `_QUANTIZE` | distilbert-mnli / `descriptive` / `none` | `nli` backend only |
| | `CLASSIFIER_CACHE_SIZE` / `_MAX_CHUNK_TOKENS` | `2048` / `400` | LRU entries; tokens per chunk for long texts |
| | `PROMPT_COMPRESSION_EXACT_DENSITY` | `0.15` | Share of identifier-like words that makes a paragraph "exact text" |
| Router | `PROMPT_COMPRESSION_ROUTES` | `narrative,passages,records` | Active actions: `narrative`, `passages`, `records`, `history` |
| | `PROMPT_COMPRESSION_SELECTION_SCOPE` | `latest_user` | Messages passages/records may thin out: `latest_user` or `all` |
| | `PROMPT_COMPRESSION_INTENT_GATE` | `true` | No selection for requests that need the whole text (`intent.py`) |
| Redact | `REDACT_SENSITIVE` | `false` | Guardrail: replace rule matches with `[EMAIL]`, `[API_KEY]`, ... in every message, role and mode |
| | `PROMPT_COMPRESSION_PRESERVE_LAST_USER` | `false` | Never touch the latest user message |
| | `PROMPT_COMPRESSION_PROTECT_EDGES` | `true` | Never compress the first and last paragraph of the latest user message |
| Compress | `PROMPT_COMPRESSION_RATE` | `0.4` | LLMLingua-2 rate, the fraction of tokens kept (about 2x on prose); digits are always kept |
| | `PROMPT_COMPRESSION_MAX_RATIO` | `3.0` | Largest ratio accepted per block; above it: one lighter retry, then the block is left as it was |
| | `PROMPT_COMPRESSION_MIN_CHARS` / `_MAX_CALLS` | `200` / `6` | Shortest prose run worth compressing; LLMLingua-2 calls per message |
| | `PROMPT_COMPRESSION_MAX_CALLS_PER_REQUEST` | `12` | LLMLingua-2 calls per request, longest runs first (cache hits are free) |
| | `PROMPT_COMPRESSION_CACHE_SIZE` | `512` | Compressed outputs remembered per worker; replays earlier turns byte for byte |
| | `PROMPT_COMPRESSION_MODEL` / `_MODEL_REVISION` / `_EAGER_LOAD` | LLMLingua-2 mBERT / pinned commit / `true` | Checkpoint and revision; load models at proxy start |
| Select | `PROMPT_COMPRESSION_MIN_PASSAGES` / `_MIN_PASSAGE_TOKENS` / `_PASSAGE_KEEP_RATIO` | `6` / `100` / `0.5` | `passages` route guards and target |
| | `PROMPT_COMPRESSION_RECORD_MIN_LINES` / `_RECORD_CONTEXT_LINES` | `10` / `1` | `records` route guard and neighbour lines |
| | `PROMPT_COMPRESSION_HISTORY_MAX_TOKENS` / `_HISTORY_KEEP_MESSAGES` | `0` / `6` | `history` route budget (0 = off) and the tail that is always kept |

Per-request opt-out: send `"metadata": {"prompt_compression": false}` (or `{"disable_prompt_compression": true}`) in
the request body. With the OpenAI SDK: `extra_body={"metadata": {"prompt_compression": False}}`.

## The stages

### Gate

With `REDACT_SENSITIVE=true` the redaction guardrail (`redaction.py`) runs first, on every message and role, whatever
the opt-out, the size or the mode; if it fails the request is rejected with HTTP 503 even in fail-open mode.

Then cheap checks on the event loop (`gate.py`): compression switched off, not a chat call, a per-request opt-out. At
most `MAX_CONCURRENCY` pipelines run per worker; a request that finds them all busy is sent unchanged (`busy`). The
token checks run in the worker thread (a full tiktoken pass costs about 200 ms on 2 MB, too long for the event loop):
fewer than `MIN_TOKENS` (classifying a tiny prompt costs more than compression can save) or more than
`MAX_INPUT_TOKENS` tokens skip the pipeline.

The pipeline runs under a deadline of 90% of `TIMEOUT_S` (`deadline.py`): every model call checks it, and model locks
are waited for only until it passes. Compression that runs out of time stops and sends what it has; classification
that runs out of time is a timeout. A timeout or any error sends the original prompt (**Fail open**) or rejects the
request with HTTP 503 (`FAIL_MODE=closed`). A worker thread cannot be killed, but with the deadline a timed-out request
stops at its next model call instead of running on and holding the locks for the requests behind it.

### Segment and classify

Every message the pipeline may touch is split into blocks (`segmenter.py`), each with a kind, and each block gets a
sensitivity verdict. Never touched at all: `system` and `developer` messages, `tool` and `function` results, assistant
messages carrying `tool_calls` / `function_call`, non-text content parts, tool definitions (`tools`, which live outside
`messages`), message roles and order. Also left verbatim, and never dropped by the `history` route: messages the
context-engineering stage (`../context_engineering/`, which runs before this hook) lists in
`metadata.context_engineering.hints.protected_indexes`, i.e. its compaction summary (report action
`preserved_context_engineering`).

| Kind | Examples | Why it matters (research report) |
|---|---|---|
| `code` | fenced or unfenced code, shell, SQL | identifiers were split (`MAX_WINDOW_PB` became `MAX WINDOW _ PB`), keywords dropped |
| `structured` | JSON, JSON lines, log lines, tables, CSV, `key=value`, stack traces | LLMLingua-2 kept none of the six log field names, so the model saw bare numbers |
| `exact` | prose dense in numbers, ids, paths, addresses, camelCase or mid-sentence names | dates lost their separators, numbers were dropped; an early benchmark run lost an answer name ("Tanaka") from a paragraph with two digit-words, so names count |
| `prose` | everything else | the only kind a compressor may touch |

A short label line directly above data ("Here is the log:" with no blank line between) does not hide the data. The
guard is a set of cheap regexes, not a model, and errs towards "exact".

**Sensitivity** is decided per block. The deterministic rules (`rules.py`) and the topic lexicon (`topics.py`, reported
as rule hits `topic_<name>`) run on every block. The model (default: sentence embedding + trained head) runs on
consecutive prose blocks merged into one run (and on exact-text runs too when a route could drop them whole, `history`
or `passages`); a run is sensitive when the model's probability reaches `SENSITIVITY_THRESHOLD`. A rules or topic
hit protects only its own block; a sensitive run is protected whole. A failed inference counts as sensitive; if the
model cannot be loaded, the hook's fail mode applies.

### Router

Two limits apply to "select or drop" (passages and records):

- **Scope** (`SELECTION_SCOPE=latest_user`): only the latest user message is selected from. Earlier turns are history:
  they can be compressed (deterministically, and replayed from the compression cache), and dropped whole only by the
  `history` route. Selecting them against each new question silently lost context in multi-turn chats and changed the
  conversation prefix on every request, which defeats provider prompt caching.
- **Intent** (`INTENT_GATE=true`, `intent.py`): a request whose instruction or question asks for a task over the whole
  text (summarise, translate, rewrite, review, key points, every/each/whole ...) selects nothing. A "summarize the whole
  report" request used to lose about half of its sections.

The task type picks the action for every block (`router.py`); it only decides:

| Block | Action |
|---|---|
| sensitive text, code, structured data, exact text, the latest user message's first and last paragraph | **Keep verbatim** (`REDACT_SENSITIVE=true` replaces PII spans) |
| passages the question does not need (route `passages`) | **Select or drop**: whole passages, ranked by BM25 against the question; no lexical signal means nothing is dropped |
| log / JSON-lines / CSV lines the question does not name (route `records`) | **Select or drop**: matches and their neighbours stay |
| the oldest whole chat turns (route `history`, needs `HISTORY_MAX_TOKENS`) | **Select or drop**: never a turn with tool calls or results, never one containing sensitive text, never the last `HISTORY_KEEP_MESSAGES` messages |
| running prose (route `narrative`) | **Compress text** |

`narrative`, `passages` and `records` are on by default (until 2026-11-06 only `narrative` was, with guards of 300
tokens / 20 lines that kept the selection routes from firing on typical prompts; the benchmark prompts then saved 11% on
QA and 0% on logs, against 39% and 66% now, see `reports/playground-ab/REPORT.md`). A latest user message that is a single paragraph is both instruction and content,
so it is not compressed; to compress a long pasted document, put the instruction and the question in their own
paragraphs.

### Actions

Select runs before compress, so a dropped passage never reaches the compressor. Consecutive prose blocks are merged into
one LLMLingua-2 call (at most `MAX_CALLS` per message, longest first), at `RATE`, with digits reserved. A block whose
ratio exceeds `MAX_RATIO` is retried once at a lighter rate and left as it was if it still exceeds the cap. A block
whose result is empty or not shorter is left as it was.

### Reassemble

Each message's blocks are joined back in their original order with their original blank-line separators, so roles and
layout are unchanged; only the text of dropped or compressed blocks differs. The summary goes to
`metadata.prompt_compression` and `metadata.spend_logs_metadata.prompt_compression`. Per message: `category`
(`sensitive` / `general`), `score` (the model's probability, 1.0 for a rules hit), `source` (`rules`, `model`, `error`,
`none`), `rule_hits`, `classify_ms`, `compress_ms`, `tokens_before` / `tokens_after`, `segments` (block counts by kind and
action counters) and `action`: `compressed`, `selected_passages`, `selected_records`, `redacted`, `sensitive`, `guarded`
(protected blocks and nothing else changed), `unchanged`, `below_min_chars`, `preserved_role`, `preserved_last_user`,
`no_text`, `dropped_history`. The request summary adds `kept` (why blocks were kept verbatim: `sensitive`, `code`, `edge`,
...). `index` always refers to the original request; with the `history` route `new_index` is the position in the result.

## Sensitivity

A false alarm costs only compression (the text is kept); a miss means a sensitive text may be compressed. So recall
comes first, but a check that flags most ordinary text makes the whole pipeline pointless.

**Why the zero-shot model was replaced (2026-11-06).** The earlier model (`typeform/distilbert-base-uncased-mnli`, a
softmax over four candidate labels) does not separate the classes: its P("sensitive") was 0.38-0.67 on sensitive prompts
and up to 0.57 on chit-chat, code questions and company prose. At 0.35 it reached 0.97 test recall only by flagging
67.6% of ordinary prompts and 79.5% of the company-prose paragraphs of the research benchmark, so almost nothing was
compressed (a Playground prompt about suppliers and manufacturers scored 0.44 and was kept whole). No threshold or
hypothesis wording fixed it (`reports/playground-ab/raw/sensitivity_variants.json`).

**Current decision** (`eval/train_sensitivity_head.py`, `eval/results/sensitivity_head.md`): rules, then topics, then
`all-MiniLM-L6-v2` + a logistic-regression head (`sensitivity-head-v2`) trained on `eval/sensitivity_train.jsonl` and
the dev split (385 prompts, 164 sensitive). Threshold 0.36 = largest value with 5-fold out-of-fold recall of at least
0.95. Nothing below was used for training:

| set | decision | sensitive recall | false-positive rate |
|---|---|---|---|
| test (148 prompts) | zero-shot at 0.35 (old) | 0.973 | 0.676 |
| | rules + topics + head v1 / v2 | 0.973 / 0.973 (36 of 37) | 0.072 / 0.099 |
| fresh holdout (100 prompts) | zero-shot at 0.35 (old) | 1.000 | 0.917 |
| | rules + topics + head v1 / v2 | 1.000 / 1.000 (40 of 40) | 0.083 / 0.117 |
| QA company prose (112 runs) | old / v1 / v2 | - | 0.795 / 0.000 / 0.000 |
| QA passages one at a time (360) | v1 / v2 | - | see below / 0.006 |

v2 (2026-11-08) adds 26 public leadership-history sentences as hard negatives, plus 14 confidential or personal
employment and commercial items as positives. The gateway now scores each passage on its own (`pipeline._passage_groups`).
v1 flagged sentences such as "leadership passed to X in 2009, who remains chief executive" (scores 0.38-0.69), so 28 of
40 benchmark qa requests were labelled sensitive (evals/REPORT.md §0). v2 keeps the same recall, at a few more false
alarms on general prose. v1 is in git history if a rollback is needed.
| PII case notes (50) | old / new | 1.000 / 1.000 | - |

The one test miss is a placeholder Slack webhook URL (a rules-test artefact, see "Tests"). The fresh holdout and the
training file were written by the same author as the topic lexicon, so they share its blind spots; check the decision
on your own traffic in shadow mode, and retrain with your own labelled examples by adding them to
`eval/sensitivity_train.jsonl` and rerunning the training script. Scoring costs about 14 ms per text on this CPU (the
zero-shot model: about 250 ms). `SENSITIVITY_BACKEND=nli` restores the old model.

**What the model is asked about** (changed after `evals/REPORT.md`, 2026-11-08):
- **Instruction and question are not sent to the model.** In a message of three or more paragraphs, the first and last
  paragraph of the latest user message are kept verbatim by the router whatever they contain, so the model only
  judges the content between them. Rules and topics still check them. Before this change, short lookup questions such
  as "What was the user id of request req-1?" were labelled sensitive in 17 of 40 log prompts. That only mislabelled
  the request, since the question is never changed. One- and two-paragraph prompts are still judged whole.
- **Each passage is judged on its own** when the `passages` or `history` route is on. A passage shorter than 40
  characters is judged with the next one. All passages of a request go through one batched encoder call.
- **Why per passage:** scoring the whole document in 200-token windows let one company-finance paragraph, falling into
  a short window, keep the entire document verbatim. Moving the window edges, even by changing an 8-character request
  tag, flipped the decision. Now a high score protects only its own passage.
- **With only the `narrative` route,** the prose run is compressed as a whole and is still judged as a whole.

## What it does on the research benchmark

`eval/guard_eval.py` runs this pipeline (real LLMLingua-2, `--detector real` = the production sensitivity check) on the
benchmark items of `reports/compression-fit` and sends every changed prompt to the same local model the report used
(40 items per family; `eval/results/guard_eval_real.md`, raw rows in `reports/compression-fit/raw/gateway_eval/`):

| Family | Condition | Accuracy (baseline) | Prompts changed | Token ratio |
|---|---|---|---|---|
| QA over distractor paragraphs | prose route | 1.000 (1.000) | 18 of 40 | 1.06x |
| | prose route at rate 0.28 | 1.000 | 14 of 40 | 1.05x |
| | + passages route | 1.000 | 29 of 40 | 1.39x |
| Lookups in logs and JSON | prose route | 1.000 (1.000) | 0 of 40 | 1.00x |
| | + records route | 1.000 | 40 of 40 | 2.95x |
| Lookups of constants in code | prose route | 0.875 (0.875) | 0 of 40 | 1.00x |

Quality equals the uncompressed baseline everywhere (whole-message LLMLingua-2 at the gateway's old mild setting lost
0.575 on logs and 0.125 on code). The yield of the prose route is small on this data, for two reasons that the same
benchmark run with `--detector rules` (no NLI model, `guard_eval_rules.md`) separates: the exact-text guard alone, which
keeps fact paragraphs (numbers, names) verbatim, caps QA at 1.12x (32 of 40 prompts changed; passages route 1.64x), and
the sensitivity check at its default threshold takes it down to 1.06x by keeping 22 of the 40 QA prompts whole. Logs and
code are identical in both runs (no prose to compress; records route 2.95x). The `passages` and `records` routes save
more because they drop units instead of pruning tokens, but those numbers are a best case: the synthetic questions
share rare words with their evidence. The history route and the sensitivity decision were measured separately (above,
and in `tests/`). The table above was measured with the earlier zero-shot sensitivity model; the QA prose rows are
therefore lower than with the current embedding head (which flags none of the 112 QA prose paragraphs).

**Through the gateway, current defaults.** `reports/playground-ab/REPORT.md` (run B2) sends 170 benchmark prompts to the
proxy twice, once with `metadata.prompt_compression=false`. The current defaults gave:
- prompt tokens −27.5% overall: QA −35%, logs −63%, code and PII 0%;
- 0 answers lost and 0 gained on the 69 changed prompts;
- mean end-to-end latency −3.5 s with the local CPU model.

**CPU cost.**
- **Sensitivity head:** about 14–16 ms per text. The old NLI check took about 0.25 s per prose run.
- **Selection routes:** a few milliseconds.
- **LLMLingua-2:** each call takes 0.2–1 s on this CPU.
- **Through the proxy:** the pipeline adds 22 ms at p50 and 0.43 s at p95 (run B2).
- **Capacity:** each proxy worker loads its own models (about 1 GB RAM), and inside a worker the model calls run one
  at a time.
  - `LITELLM_NUM_WORKERS` (default 2) and `PROMPT_COMPRESSION_TORCH_THREADS` (default 4) in
    `docker-compose.quickstart.yml` set the split. Keep workers × threads = CPUs.
  - On 8 vCPUs with an instant mock model and 120 mixed requests at concurrency 8, compressed throughput was
    8.1–8.7 req/s with 1 × 8, 12.7–13.1 with 2 × 4, and 8.7 with 4 × 2 (LLMLingua-2 starved of threads).
  - Uncompressed traffic gets 42–48 req/s at 2 × 4. Size proxy CPU, or add replicas, for the compressed rate.
- **Timeouts:** if the pipeline exceeds `PROMPT_COMPRESSION_TIMEOUT_S`, it fails open and sends the original prompt.
  - Repeated turns hit the sensitivity cache.
  - Raise the timeout if long conversations are common.
  - Do not run evaluations on the same CPU as the proxy.

## Rolling it out

Set `PROMPT_COMPRESSION_MODE=shadow` first. The whole pipeline runs and the summary (`status: shadow`, the tokens it would
have saved, the per-message actions) is logged and exported, but the provider receives the original prompt;
`observability` counts the hypothetical saving separately (`prompt_pipeline_shadow_tokens_saved_total`). Then switch one
route at a time to `enforce`. Check quality on your own prompts first: 30 to 50 items per route with reference answers,
the same inputs with and without compression. The report (section 7.5) explains why 40 items cannot show a loss below
about 15 points. Keep the per-request opt-out.

**Not implemented, on purpose.** Few-shot demonstration trimming (research: GSM8K held to 14x, BBH only to 3x) needs a
task-type signal the gateway does not have. A question-aware model such as CPC or LongLLMLingua needs a GPU-hosted 7B
model; `selectors.rank_units` is the seam where one would replace the BM25 ranking.

## Logging

Log lines never contain prompt text, only category, scores, source, rule names, model names, token counts, ratio and
timings:

```
prompt compression: category=general tokens_before=193 tokens_after=130 ratio=1.485 elapsed_ms=1655.7 ...
```

Token counts use tiktoken `cl100k_base`, the same encoding LLMLingua-2 reports with. Models are loaded once (at proxy
start by default) in float32; transformers 5 otherwise keeps the checkpoint dtype, and fp16 DeBERTa-v3 checkpoints were
about 10x slower on this CPU. The hook runs the CPU-bound pipeline in a worker thread (`asyncio.to_thread`) under
`asyncio.wait_for(PROMPT_COMPRESSION_TIMEOUT_S)`.

## Model comparison (historical)

`eval/benchmark.py` compares NLI checkpoints as four-way classifiers; the pipeline now uses only the "sensitive"
probability. Full record, candidate sources and licenses: [`eval/results/SELECTION.md`](eval/results/SELECTION.md), written
when the model also served as an importance classifier (its "production classifier" and `critical`-fallback figures
describe the removed design). Held-out test set (148 prompts, 37 per class), descriptive labels, CPU (i7-10610U):

| model | sensitive recall | macro-F1 | p95 ms | params |
|---|---|---|---|---|
| **typeform/distilbert-base-uncased-mnli (kept)** | **0.919** | 0.307 | 194 | 67M |
| MoritzLaurer/deberta-v3-base-zeroshot-v2.0 | 0.460 | 0.445 | 692 | 184M |
| MoritzLaurer/DeBERTa-v3-base-mnli-fever-anli | 0.054 | 0.322 | 764 | 184M |
| MoritzLaurer/deberta-v3-xsmall-zeroshot-v1.1-all-33 | 0.000 | 0.284 | 214 | 71M |

Those "sensitive recall" figures are for the argmax label; the pipeline's threshold decision is measured in the
"Sensitivity" section above. The baseline's model card states no license; confirm it is acceptable before production use.
To try another model: `CLASSIFIER_MODEL=<hf id>` (and optionally `CLASSIFIER_LABEL_FORMAT=plain`), rerun the benchmark on
dev, then `sensitivity_eval` and pick the threshold on dev.

## Tests and evaluation

```bash
cd prompt_compression
../.venv-compression/Scripts/python -m pytest
cd ..
# the sensitivity decision (rules + model + threshold) on the labelled dev and test splits
.venv-compression/Scripts/python -m prompt_compression.eval.sensitivity_eval
# does the pipeline keep the quality the research report says whole-message compression loses?
# (needs Ollama with llama3.2:3b and reports/compression-fit; writes eval/results/guard_eval_<detector>.md)
.venv-compression/Scripts/python -m prompt_compression.eval.guard_eval --detector real
.venv-compression/Scripts/python -m prompt_compression.eval.guard_eval --detector rules   # router only, no NLI model
# model comparison
.venv-compression/Scripts/python -m prompt_compression.eval.build_dataset
.venv-compression/Scripts/python -m prompt_compression.eval.benchmark --split dev --formats plain descriptive --models <id> ...
```

Two tests in `tests/test_rules.py` fail because their API-key examples were replaced by placeholders that the rules do not
match; they are unrelated to the pipeline.

## Verification (local, no API key)

```bash
.venv-compression/Scripts/python prompt_compression/dev/mock_openai_server.py --port 4010
# second shell, with MOCK_LLM_API_BASE=http://127.0.0.1:4010/v1, MOCK_LLM_API_KEY, LITELLM_MASTER_KEY set
.venv-compression/Scripts/litellm --config config.yaml --port 4000
# third shell
.venv-compression/Scripts/python prompt_compression/dev/verify_gateway.py
```

The mock provider echoes the messages it received, so the client can show whether each prompt reached the model unchanged.
