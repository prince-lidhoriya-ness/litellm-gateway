"""Context compaction: older turns become one anchored, structured summary message.

extractive (default) - no LLM call. Every line of the summary is copied verbatim from the compacted turns:
                       instructions and constraints, decisions, open tasks and questions, tool calls with their
                       arguments, identifiers, small code/data blocks, tool errors, and an index of the turns with
                       their refs. Constraints and open tasks are never trimmed to fit the size cap.
llm                  - the extractive summary is used at once, and a model-written summary of the same span is
                       requested in the background (CONTEXT_COMPACTION_MODEL, through the proxy's own router with
                       compression and context engineering switched off). It replaces the extractive one on a later
                       request only if it passes validation: every identifier it contains occurs in the originals, it
                       contains no instruction-shaped text the originals do not, and it is smaller than the span.
                       The verbatim constraints and the turn index are always appended to it.

Summaries are cached by the hash of the exact span they replace, so the same span is never summarized twice, and they
are only applied to a request that contains that exact span.
"""

import asyncio
import hashlib
import json
import logging
import re
import sys
from typing import Optional

from context_engineering import extract
from context_engineering import tokens as tk
from context_engineering.settings import ContextSettings
from context_engineering.structures import SUMMARY_MARKER

logger = logging.getLogger("context_engineering.compaction")

_INJECTION = re.compile(
    r"(ignore (all|any|the)? ?(previous|prior|above)|disregard (the )?(previous|above)|you (must|should) now|"
    r"new instructions|system prompt|developer message|you are now)",
    re.I,
)

SUMMARY_INSTRUCTIONS = (
    "Summarize the conversation excerpt below for an assistant that will continue the conversation without seeing "
    "it. Use these sections: Session intent; Instructions and constraints; Decisions and rationale; Files, artifacts "
    "and identifiers; Current state; Open tasks and next steps. Copy every file path, identifier, number, error "
    "message and code symbol exactly as written. Do not add facts, opinions or instructions. Be concise."
)


def span_sha(turns: list) -> str:
    payload = json.dumps([messages for _, _, messages in turns], sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(payload.encode("utf-8", "surrogatepass")).hexdigest()


def turn_ref(messages: list) -> str:
    payload = json.dumps(messages, sort_keys=True, ensure_ascii=False, default=str)
    return "turn_" + hashlib.sha256(payload.encode("utf-8", "surrogatepass")).hexdigest()[:12]


def _dedupe(values: list) -> list:
    seen, out = set(), []
    for value in values:
        if value not in seen:
            seen.add(value)
            out.append(value)
    return out


def _first_words(text: str, count: int = 15) -> str:
    words = text.split()
    snippet = " ".join(words[:count])
    return snippet + (" ..." if len(words) > count else "")


def _blocks(text: str):
    from prompt_compression.segmenter import CODE, STRUCTURED, split_segments

    return [seg.text for seg in split_segments(text) if seg.kind in (CODE, STRUCTURED) and seg.text.strip()]


def extract_sections(turns: list, settings: ContextSettings) -> dict:
    """turns: [(ref, original_indexes, messages)]. Returns section name -> list of verbatim lines."""
    constraints, decisions, open_tasks, calls, idents, blocks, tool_lines, index = [], [], [], [], [], [], [], []
    for ref, indexes, messages in turns:
        user_text = answer = ""
        for message in messages:
            role = message.get("role")
            text = tk.message_text(message)
            if role == "assistant" and text and not answer:
                first = extract.sentences(text)
                answer = first[0] if first else ""
            if role == "user":
                user_text = user_text or text
                constraints += extract.matching_sentences(text, extract.CONSTRAINT)
                open_tasks += extract.matching_sentences(text, extract.OPEN_TASK)
                decisions += extract.matching_sentences(text, extract.DECISION)
            elif role == "assistant":
                decisions += extract.matching_sentences(text, extract.DECISION)
                open_tasks += [s for s in extract.matching_sentences(text, extract.OPEN_TASK) if not s.endswith("?")]
                for call in message.get("tool_calls") or []:
                    function = (call or {}).get("function") or {}
                    arguments = str(function.get("arguments", ""))
                    if tk.text_tokens(arguments) > settings.compaction_verbatim_block_tokens:
                        arguments = f"<{tk.text_tokens(arguments)} tokens, stored under {ref}>"
                    calls.append(f"{function.get('name', '?')}({arguments})")
                    idents += extract.identifiers(str(function.get("arguments", "")))
            elif role in ("tool", "function"):
                errors = [line for line in extract.key_lines(text, "", 60, 0)][:2]
                name = message.get("name") or ""
                tool_lines.append(f"{name or 'tool'} result ({tk.text_tokens(text)} tokens)" +
                                  (": " + " | ".join(errors) if errors else ""))
            if role in ("user", "assistant") and text:
                idents += extract.identifiers(text)
                for block in _blocks(text):
                    size = tk.text_tokens(block)
                    if size <= settings.compaction_verbatim_block_tokens:
                        blocks.append(block)
                    else:
                        first = block.strip().splitlines()[0][:160]
                        blocks.append(f"{first}  <{size}-token block, stored under {ref}>")
        span = f"#{indexes[0]}" if len(indexes) == 1 else f"#{indexes[0]}-#{indexes[-1]}"
        entry = f"{ref} (messages {span}): user: \"{_first_words(user_text)}\""
        if answer:
            entry += f" / assistant: \"{_first_words(answer, 30)}\""
        index.append(entry)
    return {
        "Instructions and constraints (verbatim)": _dedupe(constraints),
        "Open tasks and questions (verbatim, as of those turns)": _dedupe(open_tasks),
        "Decisions (verbatim)": _dedupe(decisions),
        "Tool calls (verbatim arguments)": _dedupe(calls),
        "Identifiers, files and values (verbatim)": _dedupe(idents)[:120],
        "Code and data blocks": _dedupe(blocks),
        "Tool results": tool_lines,
        "Turn index": index,
    }


# Trimmed last-first when the summary is over its cap; the first two are never trimmed.
_NEVER_TRIM = ("Instructions and constraints (verbatim)", "Open tasks and questions (verbatim, as of those turns)")
_TRIM_ORDER = ("Tool results", "Identifiers, files and values (verbatim)", "Tool calls (verbatim arguments)",
               "Turn index", "Code and data blocks", "Decisions (verbatim)")
_INDEX_LEVEL = ("Instructions and constraints (verbatim)", "Open tasks and questions (verbatim, as of those turns)",
                "Decisions (verbatim)", "Turn index")


def header(turns: list, tokens_before: int, retrieved: int) -> str:
    first = turns[0][1][0]
    last = turns[-1][1][-1]
    note = f"; {retrieved} older turn(s) relevant to the current question are kept in full below" if retrieved else ""
    return (f"{SUMMARY_MARKER} by gateway: {len(turns)} turn(s), messages #{first}-#{last} of the original request, "
            f"{tokens_before} tokens{note}. Lines below are copied verbatim from those turns. To restore a turn in "
            f"full, mention its turn_ ref.]")


def render(head: str, sections: dict, order: tuple) -> str:
    parts = [head]
    for name in order:
        lines = sections.get(name) or []
        if lines:
            parts.append(f"{name}:")
            parts.extend(f"- {line}" if "\n" not in line else line for line in lines)
    return "\n".join(parts)


def build_summary(turns: list, settings: ContextSettings, level: str = "full", retrieved: int = 0,
                  sections: Optional[dict] = None) -> str:
    """The extractive summary, at most CONTEXT_COMPACTION_MAX_SUMMARY_TOKENS unless the never-trimmed sections
    (constraints, open tasks) alone are bigger: those are kept whole and the caller's ratio check decides."""
    tokens_before = sum(tk.messages_tokens(messages) for _, _, messages in turns)
    sections = {name: list(lines) for name, lines in (sections or extract_sections(turns, settings)).items()}
    order = tuple(sections) if level == "full" else _INDEX_LEVEL
    head = header(turns, tokens_before, retrieved)
    budget = settings.compaction_max_summary_tokens
    # Additive estimate (line tokens + 1 per newline) so trimming does not re-tokenize the whole summary per line.
    cost = {name: [tk.text_tokens(line) + 2 for line in sections[name]] for name in order}
    total = tk.text_tokens(head) + sum(sum(c) + tk.text_tokens(name) + 1 for name, c in cost.items() if c)
    for name in _TRIM_ORDER:
        if name not in order or total <= budget:
            continue
        if name == "Turn index":
            # Shorten the entries to their ref and span before dropping any: the refs are how a turn is restored.
            compact = [line.split(": user:", 1)[0] for line in sections[name]]
            total -= sum(cost[name])
            cost[name] = [tk.text_tokens(line) + 2 for line in compact]
            total += sum(cost[name])
            sections[name] = compact
            if total <= budget:
                continue
        trimmed = False
        while sections[name] and total > budget:
            sections[name].pop()
            total -= cost[name].pop()
            trimmed = True
        if trimmed:
            sections[name].append("(more omitted to fit the summary size; restore a turn by its ref)")
            total += 14
    return render(head, sections, order)


def validate_model_summary(summary: str, source: str) -> list[str]:
    problems = []
    if not summary or not summary.strip():
        return ["empty"]
    unknown = [token for token in extract.identifiers(summary) if token not in source]
    if unknown:
        problems.append(f"identifiers not in the originals: {len(unknown)}")
    if _INJECTION.search(summary) and not _INJECTION.search(source):
        problems.append("instruction-shaped text not present in the originals")
    if tk.text_tokens(summary) >= tk.text_tokens(source):
        problems.append("not shorter than the originals")
    return problems


class ModelSummarizer:
    """Background, model-written summaries (CONTEXT_COMPACTION_MODE=llm). Off the request path: a request never waits
    for it; the first request of a span gets the extractive summary."""

    def __init__(self, model: str, store, max_tokens: int, completion=None):
        self.model = model
        self.store = store
        self.max_tokens = max_tokens
        self._completion = completion
        self._pending: set = set()

    def key(self, sha: str) -> str:
        return "sum_" + sha[:24]

    def lookup(self, sha: str) -> Optional[str]:
        entry = self.store.get(self.key(sha))
        return entry.get("text") if isinstance(entry, dict) and entry.get("valid") else None

    def wants(self, sha: str) -> bool:
        return bool(self.model) and sha not in self._pending and self.store.get(self.key(sha)) is None

    async def _complete(self, messages: list) -> str:
        if self._completion is not None:
            return await self._completion(model=self.model, messages=messages, max_tokens=self.max_tokens)
        proxy = sys.modules.get("litellm.proxy.proxy_server")
        router = getattr(proxy, "llm_router", None) if proxy is not None else None
        kwargs = dict(model=self.model, messages=messages, max_tokens=self.max_tokens, temperature=0,
                      metadata={"prompt_compression": False, "context_engineering": False,
                                "tags": ["context_engineering:compaction"]})
        if router is not None:
            response = await router.acompletion(**kwargs)
        else:
            import litellm

            response = await litellm.acompletion(**kwargs)
        return response.choices[0].message.content or ""

    async def summarize(self, sha: str, source: str) -> None:
        if sha in self._pending:
            return
        self._pending.add(sha)
        try:
            text = await self._complete([
                {"role": "system", "content": SUMMARY_INSTRUCTIONS},
                {"role": "user", "content": source},
            ])
            problems = validate_model_summary(text, source)
            self.store.put(self.key(sha), {"kind": "summary", "valid": not problems, "text": text if not problems else "",
                                           "problems": problems, "model": self.model})
            if problems:
                logger.warning("compaction: model summary rejected: %s", "; ".join(problems))
        except Exception as exc:
            logger.warning("compaction: model summary failed: error=%s", type(exc).__name__)
        finally:
            self._pending.discard(sha)

    def schedule(self, sha: str, source: str) -> bool:
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            return False
        loop.create_task(self.summarize(sha, source))
        return True


def source_text(turns: list) -> str:
    """The span as plain text for a summarizer: role-prefixed messages, tool calls included."""
    lines = []
    for _, _, messages in turns:
        for message in messages:
            text = tk.message_text(message)
            calls = tk.tool_calls_text(message)
            lines.append(f"{message.get('role')}: {text}" + (f"\n[tool calls] {calls}" if calls else ""))
    return "\n\n".join(lines)


def model_summary_message(head: str, model_text: str, sections: dict) -> str:
    keep = {name: sections[name] for name in (*_NEVER_TRIM, "Turn index")}
    return render(head + "\nSummary (model-written, checked against the originals):\n" + model_text.strip(),
                  keep, tuple(keep))
