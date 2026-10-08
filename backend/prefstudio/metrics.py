"""Inter-rater agreement statistics.

Pure functions with no database or web code, so they are easy to test against
published worked examples (see tests/test_metrics.py).
"""

from __future__ import annotations

from collections import Counter
from itertools import combinations
from typing import Hashable, Iterable, Sequence


def percent_agreement(units: Iterable[Sequence[Hashable]]) -> float | None:
    """Share of rater pairs that gave the same label, averaged over units.

    Units with fewer than two labels are skipped.
    """
    agree = total = 0
    for labels in units:
        if len(labels) < 2:
            continue
        for a, b in combinations(labels, 2):
            total += 1
            agree += a == b
    return agree / total if total else None


def cohen_kappa(a: Sequence[Hashable], b: Sequence[Hashable]) -> float | None:
    """Cohen's kappa for two raters who labeled the same units.

    Returns None when chance agreement is 1 (both raters always used one
    category), where kappa is undefined.
    """
    if len(a) != len(b):
        raise ValueError("both raters must label the same units")
    n = len(a)
    if n == 0:
        return None
    p_o = sum(x == y for x, y in zip(a, b)) / n
    ca, cb = Counter(a), Counter(b)
    p_e = sum(ca[c] * cb[c] for c in ca.keys() | cb.keys()) / (n * n)
    if p_e == 1:
        return None
    return (p_o - p_e) / (1 - p_e)


def fleiss_kappa(table: Sequence[Sequence[int]]) -> float | None:
    """Fleiss' kappa from a units x categories table of label counts.

    Every unit must have the same number of ratings.
    """
    if not table:
        return None
    n = sum(table[0])
    if n < 2 or any(sum(row) != n for row in table):
        raise ValueError("every unit needs the same number (>= 2) of ratings")
    big_n = len(table)
    k = len(table[0])
    p_bar = sum((sum(c * c for c in row) - n) / (n * (n - 1)) for row in table) / big_n
    p_j = [sum(row[j] for row in table) / (big_n * n) for j in range(k)]
    p_e = sum(p * p for p in p_j)
    if p_e == 1:
        return None
    return (p_bar - p_e) / (1 - p_e)


def krippendorff_alpha(
    units: Iterable[Sequence[float | Hashable]], level: str = "nominal"
) -> float | None:
    """Krippendorff's alpha. Handles any number of raters and missing labels.

    ``units`` holds the labels each unit received (missing labels are simply
    absent). ``level`` is "nominal", "ordinal" or "interval".
    Returns None when there is no variation at all (alpha is undefined).
    """
    pairable = [list(u) for u in units if len(u) >= 2]
    values = sorted({v for u in pairable for v in u})
    if not values:
        return None

    # Coincidence matrix: every ordered pair of labels within a unit,
    # weighted by 1 / (m_u - 1).
    o: dict[tuple, float] = Counter()
    for u in pairable:
        w = 1 / (len(u) - 1)
        for i, c in enumerate(u):
            for j, k in enumerate(u):
                if i != j:
                    o[(c, k)] += w
    n_c = {c: sum(o[(c, k)] for k in values) for c in values}
    n = sum(n_c.values())

    if level == "nominal":
        def delta(c, k):
            return 0.0 if c == k else 1.0
    elif level == "interval":
        def delta(c, k):
            return float(c - k) ** 2
    elif level == "ordinal":
        rank = {v: i for i, v in enumerate(values)}

        def delta(c, k):
            lo, hi = sorted((rank[c], rank[k]))
            s = sum(n_c[values[g]] for g in range(lo, hi + 1))
            return (s - (n_c[c] + n_c[k]) / 2) ** 2
    else:
        raise ValueError(f"unknown level {level!r}")

    d_o = sum(o[(c, k)] * delta(c, k) for c in values for k in values) / n
    d_e = sum(n_c[c] * n_c[k] * delta(c, k) for c in values for k in values) / (n * (n - 1))
    if d_e == 0:
        return None
    return 1 - d_o / d_e
