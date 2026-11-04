# prompt_compression

Classify -> route -> compress pipeline for every `chat/completions` request
that passes through the LiteLLM proxy. The classifier labels each message,
the router decides how hard (or whether) to compress it, and
[LLMLingua-2](https://github.com/microsoft/LLMLingua) (the compressor from
`ai-features/promptCompression/PromptCompressionWithLLMLingua-2`, used
unmodified through `compressor_adapter.py`) does the compression.

```
request -> async_pre_call_hook -> per message: rules -> NLI classifier -> route -> LLMLingua-2 -> provider
```

## Layout

| File | Purpose |
|---|---|
| `labels.py` | Label names, priority, label wording for the NLI model |
| `rules.py` | Regex + checksum rules (email, phone, IDs, Luhn cards, IBAN, keys, tokens, private keys, passwords); a hit forces `sensitive`; `redact()` |
| `classifier.py` | Zero-shot classifier: rules first, confidence fallback, chunking, LRU cache, loaded once |
| `router.py` | Label -> compression decision (the routing table below) |
| `compressor_adapter.py` | Thin wrapper over `llmlingua.PromptCompressor` (LLMLingua-2, CPU) |
| `pipeline.py` | Walks `messages`, preserves what must not change, records token counts |
| `prompt_compression_callback.py` | LiteLLM `CustomLogger.async_pre_call_hook` (fail mode, timeout, opt-out, metadata, logging) |
| `settings.py` | All environment variables |
| `eval/` | Dataset, dev/test split, benchmark script, saved results |
| `tests/` | pytest suite |
| `dev/` | Mock OpenAI-compatible provider and an end-to-end verification client |

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
`prompt_compression/prompt_compression_callback.py`; the module adds the
gateway folder to `sys.path` so the package imports work.

## Environment variables

All optional; see `../prompt_compression.env.example` for the full list with defaults.

| Variable | Default | Meaning |
|---|---|---|
| `CLASSIFIER_MODEL` | see "Model comparison" | HF id of the zero-shot NLI model |
| `CLASSIFIER_LABEL_FORMAT` | `descriptive` | `descriptive` (full label descriptions) or `plain` (label words) |
| `CLASSIFIER_QUANTIZE` | `none` | `int8`: torch dynamic quantization (hurt DeBERTa accuracy badly in the benchmark) |
| `CLASSIFIER_MIN_CONFIDENCE` | `0.6` | Below this top score -> `critical` |
| `CLASSIFIER_LATENCY_BUDGET_MS` | `300` | Selection budget for the benchmark (not enforced at runtime) |
| `CLASSIFIER_CACHE_SIZE` | `2048` | LRU entries, keyed by sha256 of the text |
| `CLASSIFIER_MAX_CHUNK_TOKENS` | `400` | Premise tokens per chunk for long prompts |
| `PROMPT_COMPRESSION_ENABLED` | `true` | Global switch |
| `PROMPT_COMPRESSION_FAIL_MODE` | `open` | `open`: send original prompt + warning; `closed`: reject with HTTP 503 |
| `PROMPT_COMPRESSION_TIMEOUT_S` | `10` | Budget for classify + compress per request |
| `REDACT_SENSITIVE` | `false` | Replace PII spans in sensitive messages with `[EMAIL]`, `[PHONE]`, ... |
| `PROMPT_COMPRESSION_PRESERVE_LAST_USER` | `false` | Never compress the latest user message |
| `PROMPT_COMPRESSION_MIN_CHARS` | `200` | Shorter messages are never compressed |
| `PROMPT_COMPRESSION_MODEL` | `microsoft/llmlingua-2-bert-base-multilingual-cased-meetingbank` | LLMLingua-2 checkpoint |
| `PROMPT_COMPRESSION_RATE_NON_SENSITIVE` | `0.6` | LLMLingua-2 rate (fraction of tokens kept) |
| `PROMPT_COMPRESSION_RATE_LESS_IMPORTANT` | `0.3` | LLMLingua-2 rate for filler |
| `PROMPT_COMPRESSION_EAGER_LOAD` | `true` | Load models at proxy start |
| `PROMPT_COMPRESSION_LOG_LEVEL` | `INFO` | Log level of the `prompt_compression` logger |

Per-request opt-out: send `"metadata": {"prompt_compression": false}` (or
`{"disable_prompt_compression": true}`) in the request body. With the OpenAI SDK:
`extra_body={"metadata": {"prompt_compression": False}}`.

## Routing table

| Label | Action | LLMLingua-2 setting |
|---|---|---|
| `sensitive` | Not compressed. With `REDACT_SENSITIVE=true`, rule-detected PII is replaced by placeholders. | none |
| `critical` | Not compressed. LLMLingua-2 has no lossless setting, so "most conservative" is "skip it". | none |
| `non_sensitive` | Standard compression | `rate=0.6`, `force_reserve_digit=True` |
| `less_important` | Aggressive compression | `rate=0.3` |

Always preserved, whatever the label: `system` and `developer` messages, `tool`
and `function` results, assistant messages carrying `tool_calls` /
`function_call`, non-text content parts, tool definitions (`tools`, which live
outside `messages`), message roles and order. Messages shorter than
`PROMPT_COMPRESSION_MIN_CHARS` are left alone. The latest user message follows
the routing table unless `PROMPT_COMPRESSION_PRESERVE_LAST_USER=true`.

The request-level category written to the metadata is the most restrictive
message label (`sensitive > critical > non_sensitive > less_important`).

Note: the Streamlit demo (`app.py`) uses a different, lighter policy (sensitive
rate 0.9, critical 0.85, code 0.95, less important 0.3). The gateway follows the
stricter policy above so sensitive and critical prompts reach the model byte for
byte; set the rates via env vars if you want to move closer to the demo.

## Classifier behaviour

1. Rules (`rules.py`) run first. Any hit -> `sensitive`, score 1.0, model not called.
2. Long text is split into token chunks that fit the model window; each chunk is
   classified and the most restrictive chunk label wins.
3. A top score below `CLASSIFIER_MIN_CONFIDENCE` -> `critical`.
4. An inference error -> `critical` (not cached, so a transient error is retried).
5. If the model cannot be loaded, `ClassifierUnavailable` is raised and the
   hook's fail mode applies (open: original prompt; closed: HTTP 503). The load
   error is remembered; restart the proxy to retry.

Models are loaded once (at proxy start by default) in float32. transformers 5
otherwise keeps the checkpoint dtype, and fp16 DeBERTa-v3 checkpoints were about
10x slower on this CPU. All label hypotheses of a chunk are scored in one batched
forward pass. The hook runs the CPU-bound pipeline in a worker thread
(`asyncio.to_thread`) under `asyncio.wait_for(PROMPT_COMPRESSION_TIMEOUT_S)`.

## Logging and metadata

Log lines never contain prompt text, only category, scores, source (rules/model/
fallback), rule names, model names, token counts, ratio and timings:

```
prompt compression: category=less_important tokens_before=78 tokens_after=31 ratio=2.516 ...
```

The same summary goes to `metadata.prompt_compression` and
`metadata.spend_logs_metadata.prompt_compression`. `spend_logs_metadata` is part
of LiteLLM's `StandardLoggingMetadata`, so the summary appears in spend logs and
in every logging callback (Langfuse, OTel, ...). Token counts use tiktoken
`cl100k_base`, the same encoding LLMLingua-2 reports with.

## Model comparison

Full record, candidate sources and licenses: [`eval/results/SELECTION.md`](eval/results/SELECTION.md).
Raw per-run output (metrics, confusion matrix, every prediction): `eval/results/*.json`.

Held-out test set (148 prompts, 37 per class), descriptive labels, CPU (i7-10610U, 4 cores):

| model | sensitive recall | macro-F1 | p95 ms | params |
|---|---|---|---|---|
| **typeform/distilbert-base-uncased-mnli (baseline, kept)** | **0.919** | 0.307 | 194 | 67M |
| MoritzLaurer/deberta-v3-base-zeroshot-v2.0 | 0.460 | 0.445 | 692 | 184M |
| MoritzLaurer/DeBERTa-v3-base-mnli-fever-anli | 0.054 | 0.322 | 764 | 184M |
| MoritzLaurer/deberta-v3-xsmall-zeroshot-v1.1-all-33 | 0.000 | 0.284 | 214 | 71M |

Switch rule: sensitive recall not lower, macro-F1 at least +0.02, p95 within
`CLASSIFIER_LATENCY_BUDGET_MS` (300). No candidate passed, so the baseline stays.
The DeBERTa-v3-base models are clearly better on macro-F1 but lose sensitive
recall and run at 2-4x the latency budget on this CPU. The baseline's model card
states no license; confirm it is acceptable before production use.

Production classifier on test (rules + 0.6 confidence fallback): every sensitive
prompt stays uncompressed (37/37, 19 of them caught by rules), but only 6 of 74
compressible prompts get compressed, because the baseline's top score is usually
below 0.6. `SELECTION.md` has the threshold trade-off measured on dev.

To try another model: `CLASSIFIER_MODEL=<hf id>` (and optionally
`CLASSIFIER_LABEL_FORMAT=plain`), then rerun the benchmark on dev first.

## Adding or changing labels

1. `labels.py`: add the constant, include it in `LABELS`, give it a `PRIORITY`
   (lower = more restrictive), a `PLAIN_LABELS` word and a `DESCRIPTIONS` sentence.
2. `router.py`: add a `Route` for it in `build_routes()` (startup fails if a label has no route).
3. `eval/build_dataset.py`: add at least 40 examples, including hard negatives;
   rerun it, then rerun the benchmark on dev, and only at the end on test.
4. To reword a label, change only `DESCRIPTIONS`/`PLAIN_LABELS` and rerun the
   dev benchmark; the wording changes zero-shot accuracy noticeably.

## Tests and benchmark

```bash
cd prompt_compression
../.venv-compression/Scripts/python -m pytest            # includes loading the configured model
SKIP_MODEL_TESTS=1 ../.venv-compression/Scripts/python -m pytest   # no model download
cd ..
.venv-compression/Scripts/python -m prompt_compression.eval.build_dataset
.venv-compression/Scripts/python -m prompt_compression.eval.benchmark --split dev --formats plain descriptive --models <id> ...
.venv-compression/Scripts/python -m prompt_compression.eval.benchmark --split test --formats <format> --models <id> ...
.venv-compression/Scripts/python -m prompt_compression.eval.benchmark --split test --full   # production classifier
```

Results land in `eval/results/` (one JSON per run with per-class metrics,
confusion matrix, latency and every prediction, plus `summary_<split>.md`).

## Verification (local, no API key)

```bash
.venv-compression/Scripts/python prompt_compression/dev/mock_openai_server.py --port 4010
# second shell, with MOCK_LLM_API_BASE=http://127.0.0.1:4010/v1, MOCK_LLM_API_KEY, LITELLM_MASTER_KEY set
.venv-compression/Scripts/litellm --config config.yaml --port 4000
# third shell
.venv-compression/Scripts/python prompt_compression/dev/verify_gateway.py
```

The mock provider echoes the messages it received, so the client can show
whether each prompt reached the model unchanged.
