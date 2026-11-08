"""Fuzzy search with RapidFuzz."""
from collections.abc import Callable, Sequence

from rapidfuzz import fuzz, process, utils

CUTOFF = 50  # lowest WRatio score (0-100) that shows


def search[T](query: str, items: Sequence[T], key: Callable[[T], str], limit: int = 8) -> list[T]:
    """Return the best `limit` items for query, best first."""
    found = process.extract(query, [key(i) for i in items], scorer=fuzz.WRatio,
                            processor=utils.default_process, limit=limit, score_cutoff=CUTOFF)
    return [items[index] for _, _, index in found]
