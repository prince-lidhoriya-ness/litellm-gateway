"""Helpers for the text of OpenAI-style messages and for token counts (cl100k_base)."""

from typing import Optional

import tiktoken

# Same encoding LLMLingua-2 reports origin/compressed tokens with (gpt-3.5-turbo).
_ENCODING = tiktoken.get_encoding("cl100k_base")


def count_tokens(text: str) -> int:
    return len(_ENCODING.encode(text)) if text else 0


def text_parts(message: dict) -> list[tuple[Optional[int], str]]:
    """(part index or None for a plain string, text) for every text segment of a message."""
    content = message.get("content")
    if isinstance(content, str):
        return [(None, content)]
    if isinstance(content, list):
        return [
            (i, part.get("text", ""))
            for i, part in enumerate(content)
            if isinstance(part, dict) and part.get("type") == "text" and isinstance(part.get("text"), str)
        ]
    return []


def set_text(message: dict, part_index: Optional[int], text: str) -> None:
    if part_index is None:
        message["content"] = text
    else:
        message["content"][part_index]["text"] = text


def message_tokens(message: dict) -> int:
    return sum(count_tokens(text) for _, text in text_parts(message))


def all_text_tokens(messages: list) -> int:
    return sum(message_tokens(message) for message in messages)
