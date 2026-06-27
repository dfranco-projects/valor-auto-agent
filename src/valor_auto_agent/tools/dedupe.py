from __future__ import annotations

import re

from valor_auto_agent.tools.crawler.schemas import Listing

# cross-source duplicate detection: the same car is often posted on both olx and
# standvirtual. listings carry no brand/model fields, so we fingerprint on year (exact),
# km + price proximity, and title token overlap.

_WORD = re.compile(r"[a-z0-9]+")
_STOP = {"de", "da", "do", "com", "the", "and"}


def _tokens(title: str | None) -> set[str]:
    return {t for t in _WORD.findall((title or "").lower()) if len(t) > 1 and t not in _STOP}


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def _close(x: int | None, y: int | None, tol_abs: int, tol_frac: float) -> bool:
    if x is None or y is None:
        return False
    return abs(x - y) <= max(tol_abs, tol_frac * max(x, y))


def _similar(a: Listing, b: Listing) -> bool:
    if a.year and b.year and a.year != b.year:
        return False
    if not _close(a.km, b.km, 3000, 0.07):
        return False
    if not _close(a.price_eur, b.price_eur, 600, 0.12):
        return False
    return _jaccard(_tokens(a.title), _tokens(b.title)) >= 0.45


def group_duplicates(listings: list[Listing]) -> list[list[int]]:
    """union cross-source look-alikes; returns groups of indices (singletons omitted)."""
    n = len(listings)
    parent = list(range(n))

    def find(i: int) -> int:
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    for i in range(n):
        for j in range(i + 1, n):
            if listings[i].source != listings[j].source and _similar(listings[i], listings[j]):
                parent[find(i)] = find(j)

    groups: dict[int, list[int]] = {}
    for i in range(n):
        groups.setdefault(find(i), []).append(i)
    return [g for g in groups.values() if len(g) > 1]


def also_on(listings: list[Listing]) -> dict[int, list[dict[str, str]]]:
    """map each duplicate listing's index -> the other listings it also appears as."""
    out: dict[int, list[dict[str, str]]] = {}
    for group in group_duplicates(listings):
        for i in group:
            out[i] = [
                {"source": listings[j].source, "url": listings[j].url}
                for j in group
                if j != i
            ]
    return out
