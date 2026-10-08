"""Turns raw labels into project statistics and training data.

Works on plain records rather than ORM objects so it can be tested without a
database.
"""

from __future__ import annotations

import statistics
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from itertools import combinations

from .metrics import cohen_kappa, fleiss_kappa, krippendorff_alpha, percent_agreement

CATEGORIES = ("A", "tie", "B")


def category(score: int) -> str:
    return "A" if score < 0 else "B" if score > 0 else "tie"


def canonicalize(displayed_score: int, criteria: dict[str, str], swapped: bool) -> tuple[int, dict[str, str]]:
    """Convert a rating made on the left/right display into A/B terms.

    ``displayed_score`` is negative when the left response is better.
    ``criteria`` maps rubric keys to "left", "right" or "tie".
    """
    if not -2 <= displayed_score <= 2:
        raise ValueError("score must be between -2 and 2")
    left, right = ("B", "A") if swapped else ("A", "B")
    mapping = {"left": left, "right": right, "tie": "tie"}
    try:
        crit = {k: mapping[v] for k, v in criteria.items()}
    except KeyError as e:
        raise ValueError(f"criteria values must be left, right or tie, got {e.args[0]!r}") from None
    return (-displayed_score if swapped else displayed_score), crit


@dataclass
class LabelRec:
    item_id: int
    rater: str
    score: int
    shown_swapped: bool | None = False
    seconds: float | None = None


@dataclass
class ItemRec:
    id: int
    gold: str | None = None


@dataclass
class ItemStats:
    item_id: int
    n_labels: int
    counts: dict[str, int]
    majority: str | None
    agreement: float | None  # share of labels matching the majority
    mean_score: float | None
    gold: str | None = None


@dataclass
class RaterStats:
    rater: str
    n_labels: int
    agreement_with_others: float | None  # vs. leave-one-out majority
    gold_accuracy: float | None
    n_gold: int
    left_bias: float | None  # share of non-tie picks that went to the left side
    tie_rate: float | None
    median_seconds: float | None


@dataclass
class ProjectStats:
    n_items: int
    n_labels: int
    n_raters: int
    items_fully_labeled: int
    percent_agreement: float | None
    krippendorff_nominal: float | None
    krippendorff_interval: float | None
    fleiss_kappa: float | None
    items: list[ItemStats] = field(default_factory=list)
    raters: list[RaterStats] = field(default_factory=list)
    pairwise_kappa: list[dict] = field(default_factory=list)


def _majority(counter: Counter) -> str | None:
    top = counter.most_common(2)
    if not top or (len(top) == 2 and top[0][1] == top[1][1]):
        return None
    return top[0][0]


def item_stats(item: ItemRec, labels: list[LabelRec]) -> ItemStats:
    cats = Counter(category(l.score) for l in labels)
    maj = _majority(cats)
    return ItemStats(
        item_id=item.id,
        n_labels=len(labels),
        counts={c: cats.get(c, 0) for c in CATEGORIES},
        majority=maj,
        agreement=(cats[maj] / len(labels)) if maj and labels else None,
        mean_score=statistics.fmean(l.score for l in labels) if labels else None,
        gold=item.gold,
    )


def compute_stats(
    items: list[ItemRec], labels: list[LabelRec], overlap: int = 3, min_shared: int = 3
) -> ProjectStats:
    by_item: dict[int, list[LabelRec]] = defaultdict(list)
    by_rater: dict[str, list[LabelRec]] = defaultdict(list)
    for l in labels:
        by_item[l.item_id].append(l)
        by_rater[l.rater].append(l)
    gold = {i.id: i.gold for i in items if i.gold}

    # Agreement is measured on non-gold items only: gold items are designed to be easy.
    units = [[category(l.score) for l in by_item[i.id]] for i in items if not i.gold]
    scores = [[l.score for l in by_item[i.id]] for i in items if not i.gold]

    fk = None
    sized = [u for u in units if len(u) >= 2]
    if sized and len({len(u) for u in sized}) == 1:
        fk = fleiss_kappa([[Counter(u)[c] for c in CATEGORIES] for u in sized])

    rater_rows = []
    for rater, rl in sorted(by_rater.items()):
        agree = comparable = 0
        for l in rl:
            others = Counter(category(o.score) for o in by_item[l.item_id] if o.rater != rater)
            maj = _majority(others)
            if l.item_id not in gold and maj:
                comparable += 1
                agree += category(l.score) == maj
        gl = [l for l in rl if l.item_id in gold]
        decided = [l for l in rl if l.score != 0]
        placed = [l for l in decided if l.shown_swapped is not None]
        secs = [l.seconds for l in rl if l.seconds is not None]
        rater_rows.append(
            RaterStats(
                rater=rater,
                n_labels=len(rl),
                agreement_with_others=agree / comparable if comparable else None,
                gold_accuracy=(sum(category(l.score) == gold[l.item_id] for l in gl) / len(gl)) if gl else None,
                n_gold=len(gl),
                # Left side is A unless the pair was shown swapped.
                left_bias=(sum((l.score < 0) != l.shown_swapped for l in placed) / len(placed)) if placed else None,
                tie_rate=(len(rl) - len(decided)) / len(rl),
                median_seconds=statistics.median(secs) if secs else None,
            )
        )

    pairs = []
    for r1, r2 in combinations(sorted(by_rater), 2):
        s1 = {l.item_id: category(l.score) for l in by_rater[r1] if l.item_id not in gold}
        s2 = {l.item_id: category(l.score) for l in by_rater[r2] if l.item_id not in gold}
        shared = sorted(s1.keys() & s2.keys())
        if len(shared) >= min_shared:
            pairs.append(
                {
                    "rater_a": r1,
                    "rater_b": r2,
                    "n_shared": len(shared),
                    "kappa": cohen_kappa([s1[i] for i in shared], [s2[i] for i in shared]),
                }
            )

    return ProjectStats(
        n_items=len(items),
        n_labels=len(labels),
        n_raters=len(by_rater),
        items_fully_labeled=sum(len(by_item[i.id]) >= overlap for i in items),
        percent_agreement=percent_agreement(units),
        krippendorff_nominal=krippendorff_alpha(units, "nominal"),
        krippendorff_interval=krippendorff_alpha(scores, "interval"),
        fleiss_kappa=fk,
        items=[item_stats(i, by_item[i.id]) for i in items],
        raters=rater_rows,
        pairwise_kappa=pairs,
    )


@dataclass
class ExportOptions:
    min_labels: int = 1
    min_agreement: float = 0.0
    min_margin: float = 0.5  # minimum |mean score|; drops near-ties
    include_gold: bool = False
    exclude_raters: tuple[str, ...] = ()


def dpo_pairs(items: list[dict], labels: list[LabelRec], opts: ExportOptions = ExportOptions()) -> list[dict]:
    """Build {"prompt", "chosen", "rejected"} records from labeled items.

    ``items`` are dicts with id, prompt, response_a, response_b and gold.
    The preferred response is decided by the mean canonical score.
    """
    by_item: dict[int, list[LabelRec]] = defaultdict(list)
    for l in labels:
        if l.rater not in opts.exclude_raters:
            by_item[l.item_id].append(l)

    out = []
    for it in items:
        if it.get("gold") and not opts.include_gold:
            continue
        st = item_stats(ItemRec(it["id"], it.get("gold")), by_item[it["id"]])
        if st.n_labels < opts.min_labels or st.mean_score is None:
            continue
        if abs(st.mean_score) < opts.min_margin or st.mean_score == 0:
            continue
        if (st.agreement or 0.0) < opts.min_agreement:
            continue
        a_wins = st.mean_score < 0
        out.append(
            {
                "prompt": it["prompt"],
                "chosen": it["response_a"] if a_wins else it["response_b"],
                "rejected": it["response_b"] if a_wins else it["response_a"],
                "meta": {
                    "item_id": it["id"],
                    "n_labels": st.n_labels,
                    "agreement": st.agreement,
                    "mean_score": round(st.mean_score, 3),
                    "chosen_model": it.get("model_a" if a_wins else "model_b", ""),
                    "rejected_model": it.get("model_b" if a_wins else "model_a", ""),
                },
            }
        )
    return out
