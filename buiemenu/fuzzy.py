"""Subsequence fuzzy match. Consecutive and word-start hits score higher."""
from collections.abc import Iterable
from heapq import nlargest

WORD_START = 8
CONSECUTIVE = 5
GAP = 1


def score(query: str, text: str) -> int | None:
    """Return the match score, or None if query is not a subsequence of text."""
    text_low, total, last = text.lower(), 0, -1
    for ch in query.lower():
        pos = text_low.find(ch, last + 1)
        if pos < 0:
            return None
        start = pos == 0 or not text_low[pos - 1].isalnum()
        total += (WORD_START if start else 0) + (CONSECUTIVE if pos == last + 1 else 0)
        total -= GAP * (pos - last - 1)
        last = pos
    return total


def search[T](query: str, items: Iterable[T], key, limit: int = 8) -> list[T]:
    """Return the best `limit` items for query, best first."""
    scored = ((s, i, item) for i, item in enumerate(items) if (s := score(query, key(item))) is not None)
    return [item for _, _, item in nlargest(limit, scored, key=lambda t: (t[0], -t[1]))]
