"""Just-in-time retrieval of older turns: which older turns does the current question need verbatim?

Scores whole turns (a user message with the assistant and tool messages that answer it) against the current query:
  bm25    prompt_compression.selectors.rank_units, the ranking the passages route already uses (no new dependency)
  hybrid  BM25 blended with the cosine similarity of all-MiniLM-L6-v2 embeddings, using the encoder the sensitivity
          check has already loaded in this worker; falls back to BM25 when the encoder is not available
A turn is retrieved only when it scores above JIT_RETRIEVAL_MIN_SCORE; at most JIT_RETRIEVAL_MAX_TURNS are kept.
No lexical signal (all scores zero) retrieves nothing, the same rule the passage selector follows.
"""

import logging
import math

from prompt_compression.selectors import rank_units

logger = logging.getLogger("context_engineering.retrieval")


def _encoder():
    try:
        from prompt_compression.sensitivity import get_detector

        classifier = getattr(get_detector(), "_classifier", None)
        encoder = getattr(classifier, "encoder", None)
        if encoder is not None and getattr(encoder, "_model", None) is not None:
            return encoder
    except Exception:
        return None
    return None


def _cosine(a: list, b: list) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm = math.sqrt(sum(x * x for x in a)) * math.sqrt(sum(y * y for y in b))
    return dot / norm if norm else 0.0


def score_turns(query: str, texts: list, backend: str = "bm25", encoder=None) -> tuple[list, str]:
    """(scores, backend actually used). Scores are in [0, 1] for hybrid and raw BM25 otherwise."""
    bm25 = rank_units(query, texts)
    if backend != "hybrid":
        return bm25, "bm25"
    encoder = encoder or _encoder()
    if encoder is None:
        return bm25, "bm25"
    try:
        vectors = encoder.encode([query] + [text[:2000] for text in texts])
    except Exception as exc:
        logger.warning("jit retrieval: embedding failed, using bm25: error=%s", type(exc).__name__)
        return bm25, "bm25"
    top = max(bm25) or 1.0
    query_vector = vectors[0]
    blended = [0.5 * (b / top) + 0.5 * max(0.0, _cosine(query_vector, v)) for b, v in zip(bm25, vectors[1:])]
    # Without any lexical overlap the semantic score alone must be clearly high to count.
    return [s if b > 0 or s >= 0.35 else 0.0 for s, b in zip(blended, bm25)], "hybrid"


def select(scores: list, max_turns: int, min_score: float) -> list[int]:
    ranked = sorted((i for i, s in enumerate(scores) if s > min_score), key=lambda i: (-scores[i], i))
    return sorted(ranked[:max(0, max_turns)])
