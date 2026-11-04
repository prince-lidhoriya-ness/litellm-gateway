"""Maps a classifier label to a compression decision (runs before the compressor).

Routing table (see README.md for the reasoning):
  sensitive       no compression; optional PII redaction when REDACT_SENSITIVE=true
  critical        no compression (LLMLingua-2 has no lossless mode, so "most
                  conservative" here means skipping it entirely)
  non_sensitive   standard LLMLingua-2 rate (PROMPT_COMPRESSION_RATE_NON_SENSITIVE)
  less_important  aggressive LLMLingua-2 rate (PROMPT_COMPRESSION_RATE_LESS_IMPORTANT)
"""

from dataclasses import dataclass

from prompt_compression.labels import CRITICAL, LABELS, LESS_IMPORTANT, NON_SENSITIVE, SENSITIVE
from prompt_compression.settings import PipelineSettings


@dataclass(frozen=True)
class Route:
    label: str
    compress: bool
    rate: float = 1.0
    redact: bool = False
    # Passed to LLMLingua-2 compress_prompt().
    force_reserve_digit: bool = False
    force_tokens: tuple = ()


def build_routes(settings: PipelineSettings) -> dict[str, Route]:
    routes = {
        SENSITIVE: Route(SENSITIVE, compress=False, redact=settings.redact_sensitive),
        CRITICAL: Route(CRITICAL, compress=False),
        # Digits are kept even in ordinary text: a dropped number is a silent factual change.
        NON_SENSITIVE: Route(NON_SENSITIVE, compress=True, rate=settings.rate_non_sensitive, force_reserve_digit=True),
        LESS_IMPORTANT: Route(LESS_IMPORTANT, compress=True, rate=settings.rate_less_important),
    }
    missing = set(LABELS) - set(routes)
    if missing:
        raise ValueError(f"no route for labels: {sorted(missing)}")
    return routes
