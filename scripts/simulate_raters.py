"""Sanity-check the agreement metrics with simulated raters.

Each non-gold pair gets a hidden "true" score. A simulated rater reports the
true score with probability ``skill`` and a uniformly random score otherwise,
so lower skill should mean lower agreement. One rater can also be given a
position bias: when guessing, they pick whichever response was shown on the
left. Run with --demo to fill a project with labels for screenshots.

    python scripts/simulate_raters.py              # print the validation table
    python scripts/simulate_raters.py --demo       # create a demo project
"""

from __future__ import annotations

import argparse
import random

from prefstudio import service
from prefstudio.analysis import ItemRec, LabelRec, compute_stats
from prefstudio.api import SAMPLE
from prefstudio.db import Database
from prefstudio.importer import parse_pairs

SCORES = (-2, -1, 0, 1, 2)


def simulate_label(truth: int, skill: float, rng: random.Random, left_bias: bool, swapped: bool) -> int:
    if rng.random() < skill:
        return truth
    if left_bias:
        # Guessing rater: picks the left side, which is B when swapped.
        return 2 if swapped else -2
    return rng.choice(SCORES)


def run(n_items: int, raters: list[tuple[str, float, bool]], seed: int):
    rng = random.Random(seed)
    truth = {i: rng.choice(SCORES) for i in range(n_items)}
    labels = []
    for name, skill, bias in raters:
        for i in range(n_items):
            swapped = rng.random() < 0.5
            labels.append(LabelRec(i, name, simulate_label(truth[i], skill, rng, bias, swapped), swapped))
    return compute_stats([ItemRec(i) for i in range(n_items)], labels, overlap=len(raters))


def _f(x: float) -> str:
    return f"{x:.2f}".replace("-0.00", "0.00")


def validation_table(seed: int = 7) -> None:
    print("| Rater skill | Percent agreement | Krippendorff α (A/tie/B) | α (5-point) | Fleiss κ |")
    print("|---|---|---|---|---|")
    for skill in (1.0, 0.9, 0.75, 0.5, 0.25, 0.0):
        st = run(400, [(f"r{k}", skill, False) for k in range(3)], seed)
        print(
            f"| {skill:.2f} | {st.percent_agreement:.0%} | {_f(st.krippendorff_nominal)} "
            f"| {_f(st.krippendorff_interval)} | {_f(st.fleiss_kappa)} |"
        )
    st = run(400, [("careful", 0.9, False), ("careful-2", 0.9, False), ("left-guesser", 0.5, True)], seed)
    r = {x.rater: x for x in st.raters}
    print(
        f"\nPosition-bias check: 'left-guesser' picks the left side {r['left-guesser'].left_bias:.0%} of the time "
        f"(careful raters: {r['careful'].left_bias:.0%})."
    )


def demo(db_url: str | None, seed: int = 3) -> None:
    rng = random.Random(seed)
    db = Database(db_url)
    db.create_all()
    rows = parse_pairs(SAMPLE.read_text(encoding="utf-8"))
    with db.sessionmaker() as s:
        p = service.create_project(s, "Demo: simulated raters", "Sample pairs labeled by four simulated raters.", overlap=3)
        service.add_items(s, p, rows)
        items = list(p.items)
        truth = {it.id: (-2 if it.gold == "A" else 2 if it.gold == "B" else rng.choice(SCORES)) for it in items}
        for name, skill, bias in [("sim-alice", 0.9, False), ("sim-bruk", 0.8, False), ("sim-chen", 0.7, False), ("sim-dawit", 0.4, True)]:
            rater = service.get_or_create_rater(s, name)
            while (picked := service.next_item(s, p, rater, rng)) is not None:
                it, swapped = picked
                score = simulate_label(truth[it.id], skill, rng, bias, swapped)
                service.add_label(s, it, rater, score, {}, "", swapped, rng.uniform(15, 90))
        print(f"Created demo project {p.id}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--demo", action="store_true")
    ap.add_argument("--db")
    args = ap.parse_args()
    demo(args.db) if args.demo else validation_table()
