import random

from evalforge.models import FunctionModel

from prefstudio import service
from prefstudio.ai_rater import combine, parse_rating, rate_project


def test_parse_rating():
    assert parse_rating("Response 1 is correct.\nRATING: 1") == -2
    assert parse_rating("rating: **4**") == 1
    assert parse_rating("RATING: 3 ... actually RATING: 5") == 2
    assert parse_rating("I think the first one") is None


def test_combine():
    assert combine(-2, -2) == (-2, True)
    assert combine(-2, -1) == (-1, True)  # rounds toward a tie
    assert combine(-1, 0) == (0, True)
    assert combine(-2, 2) == (0, False)  # flipped with the order


def _project(session, n=4):
    p = service.create_project(session, "AI", overlap=1)
    service.add_items(session, p, [
        {"prompt": f"p{i}", "response_a": f"GOOD{i}", "response_b": f"bad{i}", "gold": "A" if i == 0 else None}
        for i in range(n)
    ])
    return p


def _first_section(prompt):
    return prompt.split("[Response 1]")[1].split("[Response 2]")[0]


def test_consistent_judge(session):
    p = _project(session)
    judge = FunctionModel(lambda pr: "RATING: 1" if "GOOD" in _first_section(pr) else "RATING: 5", label="fake:fair")
    rep = rate_project(session, p, judge, log=lambda *_: None)
    s = rep.summary()
    assert s["rated"] == 4 and s["order_consistency"] == 1.0 and s["first_position_rate"] == 0.5
    st = service.project_stats(session, p)
    assert st.raters[0].rater == "ai:fake:fair" and st.raters[0].gold_accuracy == 1.0
    assert all(i.majority == "A" for i in st.items)


def test_position_biased_judge_becomes_ties(session):
    p = _project(session)
    rep = rate_project(session, p, FunctionModel(lambda pr: "RATING: 1", label="fake:biased"), log=lambda *_: None)
    s = rep.summary()
    assert s["order_consistency"] == 0.0 and s["first_position_rate"] == 1.0
    assert all(i.majority == "tie" for i in service.project_stats(session, p).items)


def test_random_order_and_unparseable(session):
    p = _project(session)
    rep = rate_project(session, p, FunctionModel(lambda pr: "RATING: 2", label="fake:r"), order="random",
                       rng=random.Random(1), log=lambda *_: None)
    assert rep.rated == 4 and rep.summary()["order_consistency"] is None
    st = service.project_stats(session, p)
    assert st.raters[0].left_bias == 1.0  # always picked the left side

    p2 = _project(session, n=2)
    rep2 = rate_project(session, p2, FunctionModel(lambda pr: "no idea", label="fake:mute"), log=lambda *_: None)
    assert rep2.rated == 0 and rep2.unparseable == 2


def test_model_error_stops_cleanly(session):
    p = _project(session)

    def boom(_):
        raise RuntimeError("ollama is not running")

    rep = rate_project(session, p, FunctionModel(boom, label="fake:down"), log=lambda *_: None)
    assert rep.rated == 0 and "ollama is not running" in rep.errors[0]
