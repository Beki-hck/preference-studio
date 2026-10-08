import pytest

from prefstudio.analysis import (
    ExportOptions, ItemRec, LabelRec, canonicalize, category, compute_stats, dpo_pairs,
)


def test_category():
    assert [category(s) for s in (-2, -1, 0, 1, 2)] == ["A", "A", "tie", "B", "B"]


def test_canonicalize_unswapped_keeps_sides():
    assert canonicalize(-2, {"helpful": "left", "clear": "tie"}, swapped=False) == (
        -2, {"helpful": "A", "clear": "tie"},
    )


def test_canonicalize_swapped_flips_sides():
    # Left was response B, so preferring the left side means preferring B.
    assert canonicalize(-1, {"helpful": "left", "honest": "right"}, swapped=True) == (
        1, {"helpful": "B", "honest": "A"},
    )


def test_canonicalize_rejects_bad_input():
    with pytest.raises(ValueError):
        canonicalize(3, {}, False)
    with pytest.raises(ValueError):
        canonicalize(0, {"helpful": "A"}, False)


ITEMS = [ItemRec(1), ItemRec(2), ItemRec(3), ItemRec(4, gold="A")]
LABELS = [
    # item 1: everyone prefers A
    LabelRec(1, "ann", -2, False, 10), LabelRec(1, "ben", -1, True, 20), LabelRec(1, "cat", -1, False, 30),
    # item 2: split, cat disagrees
    LabelRec(2, "ann", 1, False, 10), LabelRec(2, "ben", 2, False, 20), LabelRec(2, "cat", -1, True, 30),
    # item 3: ann and ben tie, cat picks B
    LabelRec(3, "ann", 0, False), LabelRec(3, "ben", 0, False), LabelRec(3, "cat", 1, True),
    # gold item 4 (answer A): cat fails it
    LabelRec(4, "ann", -2, False), LabelRec(4, "ben", -1, False), LabelRec(4, "cat", 2, False),
]


def test_compute_stats_project_level():
    st = compute_stats(ITEMS, LABELS, overlap=3, min_shared=2)
    assert (st.n_items, st.n_labels, st.n_raters, st.items_fully_labeled) == (4, 12, 3, 4)
    # Non-gold units: [A,A,A], [B,B,A], [tie,tie,B] -> agreeing pairs 3 + 1 + 1 of 9
    assert st.percent_agreement == pytest.approx(5 / 9)
    assert st.fleiss_kappa is not None
    assert st.krippendorff_nominal is not None


def test_compute_stats_raters():
    st = compute_stats(ITEMS, LABELS, overlap=3, min_shared=2)
    r = {x.rater: x for x in st.raters}
    assert r["ann"].agreement_with_others == pytest.approx(1.0)
    assert r["cat"].agreement_with_others == pytest.approx(1 / 3)
    assert r["ann"].gold_accuracy == 1.0 and r["cat"].gold_accuracy == 0.0
    assert r["ann"].tie_rate == pytest.approx(1 / 4)
    # cat's decided picks: item1 A unswapped (left), item2 A swapped (right),
    # item3 B swapped (left), item4 B unswapped (right) -> 2 of 4 left
    assert r["cat"].left_bias == pytest.approx(0.5)
    assert r["ann"].median_seconds == 10


def test_compute_stats_items_and_pairs():
    st = compute_stats(ITEMS, LABELS, overlap=3, min_shared=2)
    it = {x.item_id: x for x in st.items}
    assert it[1].majority == "A" and it[1].agreement == 1.0
    assert it[2].majority == "B" and it[2].agreement == pytest.approx(2 / 3)
    assert it[3].majority == "tie"
    pairs = {(p["rater_a"], p["rater_b"]): p for p in st.pairwise_kappa}
    assert pairs[("ann", "ben")]["kappa"] == pytest.approx(1.0)
    assert pairs[("ann", "ben")]["n_shared"] == 3  # gold item excluded


def test_compute_stats_empty_project():
    st = compute_stats([], [])
    assert st.n_items == 0 and st.percent_agreement is None and st.krippendorff_nominal is None


def _items():
    return [
        {"id": i, "prompt": f"p{i}", "response_a": f"a{i}", "response_b": f"b{i}", "gold": None}
        for i in (1, 2, 3)
    ] + [{"id": 4, "prompt": "p4", "response_a": "a4", "response_b": "b4", "gold": "A"}]


def test_dpo_pairs_default_drops_ties_and_gold():
    out = dpo_pairs(_items(), LABELS)
    assert [r["meta"]["item_id"] for r in out] == [1, 2]
    assert out[0]["chosen"] == "a1" and out[0]["rejected"] == "b1"
    assert out[1]["chosen"] == "b2" and out[1]["rejected"] == "a2"


def test_dpo_pairs_filters():
    assert [r["meta"]["item_id"] for r in dpo_pairs(_items(), LABELS, ExportOptions(min_agreement=0.9))] == [1]
    assert [r["meta"]["item_id"] for r in dpo_pairs(_items(), LABELS, ExportOptions(min_labels=4))] == []
    gold = dpo_pairs(_items(), LABELS, ExportOptions(include_gold=True, min_margin=0.3))
    assert 4 in [r["meta"]["item_id"] for r in gold]
    # Dropping cat makes item 2 unanimous for B and item 3 a pure tie.
    no_cat = dpo_pairs(_items(), LABELS, ExportOptions(min_agreement=1.0, exclude_raters=("cat",)))
    assert [r["meta"]["item_id"] for r in no_cat] == [1, 2]
