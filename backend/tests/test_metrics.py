"""Metric tests against published worked examples."""

import pytest

from prefstudio.metrics import cohen_kappa, fleiss_kappa, krippendorff_alpha, percent_agreement


def test_cohen_kappa_wikipedia_example():
    # 50 units: yes/yes 20, yes/no 5, no/yes 10, no/no 15 -> kappa = 0.4
    a = ["y"] * 25 + ["n"] * 25
    b = ["y"] * 20 + ["n"] * 5 + ["y"] * 10 + ["n"] * 15
    assert cohen_kappa(a, b) == pytest.approx(0.4)


def test_cohen_kappa_perfect_and_undefined():
    assert cohen_kappa(["A", "B", "A"], ["A", "B", "A"]) == pytest.approx(1.0)
    assert cohen_kappa(["A", "A"], ["A", "A"]) is None
    with pytest.raises(ValueError):
        cohen_kappa(["A"], ["A", "B"])


def test_fleiss_kappa_wikipedia_example():
    # 10 units, 14 raters, 5 categories -> kappa = 0.210
    table = [
        [0, 0, 0, 0, 14],
        [0, 2, 6, 4, 2],
        [0, 0, 3, 5, 6],
        [0, 3, 9, 2, 0],
        [2, 2, 8, 1, 1],
        [7, 7, 0, 0, 0],
        [3, 2, 6, 3, 0],
        [2, 5, 3, 2, 2],
        [6, 5, 2, 1, 0],
        [0, 2, 2, 3, 7],
    ]
    assert fleiss_kappa(table) == pytest.approx(0.20993, abs=1e-4)


def test_fleiss_kappa_needs_equal_ratings():
    with pytest.raises(ValueError):
        fleiss_kappa([[1, 1], [2, 1]])


# Krippendorff (2011), "Computing Krippendorff's Alpha-Reliability":
# 4 observers, 12 units, values 1-5, with missing data.
OBSERVERS = [
    [1, 2, 3, 3, 2, 1, 4, 1, 2, None, None, None],
    [1, 2, 3, 3, 2, 2, 4, 1, 2, 5, None, 3],
    [None, 3, 3, 3, 2, 3, 4, 2, 2, 5, 1, None],
    [1, 2, 3, 3, 2, 4, 4, 1, 2, 5, 1, None],
]
UNITS = [[obs[u] for obs in OBSERVERS if obs[u] is not None] for u in range(12)]


@pytest.mark.parametrize(
    "level,expected", [("nominal", 0.743), ("ordinal", 0.815), ("interval", 0.849)]
)
def test_krippendorff_alpha_paper_example(level, expected):
    assert krippendorff_alpha(UNITS, level) == pytest.approx(expected, abs=1e-3)


def test_krippendorff_alpha_edge_cases():
    assert krippendorff_alpha([[1], [2]]) is None  # nothing pairable
    assert krippendorff_alpha([["A", "A"], ["A", "A"]]) is None  # no variation
    assert krippendorff_alpha([["A", "A"], ["B", "B"]]) == pytest.approx(1.0)
    with pytest.raises(ValueError):
        krippendorff_alpha([[1, 2]], "ratio")


def test_percent_agreement():
    assert percent_agreement([["A", "A", "B"], ["B", "B"], ["A"]]) == pytest.approx(2 / 4)
    assert percent_agreement([["A"]]) is None
