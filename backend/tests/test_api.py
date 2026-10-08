import json

from prefstudio.cli import SAMPLE

PAIRS = "\n".join(
    json.dumps({"prompt": f"p{i}", "response_a": f"a{i}", "response_b": f"b{i}", **({"gold": "A"} if i == 3 else {})})
    for i in range(1, 4)
)


def sign_in(client, name):
    r = client.post("/api/raters", json={"name": name})
    assert r.status_code == 200
    return {"X-Rater-Id": str(r.json()["id"])}


def make_project(client, overlap=2):
    r = client.post("/api/projects", json={"name": "Test", "overlap": overlap})
    assert r.status_code == 201
    pid = r.json()["id"]
    assert client.post(f"/api/projects/{pid}/import", json={"jsonl": PAIRS}).json() == {"imported": 3}
    return pid


def label_all(client, pid, headers, prefer="A"):
    """Label every assigned pair, always preferring the given canonical side."""
    n = 0
    while (a := client.get(f"/api/projects/{pid}/next", headers=headers).json()) is not None:
        left_is_a = not a["swapped"]
        assert a["left"].startswith("a" if left_is_a else "b")
        score = -2 if (prefer == "A") == left_is_a else 2
        r = client.post(
            f"/api/projects/{pid}/labels", headers=headers,
            json={"item_id": a["item_id"], "swapped": a["swapped"], "score": score,
                  "criteria": {"helpful": "left" if score < 0 else "right"}, "seconds": 5},
        )
        assert r.status_code == 201, r.text
        assert r.json()["score"] == (-2 if prefer == "A" else 2)
        assert r.json()["criteria"] == {"helpful": prefer}
        n += 1
    return n


def test_health_and_default_rubric(client):
    assert client.get("/api/health").json()["ok"] is True
    pid = make_project(client)
    p = client.get(f"/api/projects/{pid}").json()
    assert [c["key"] for c in p["rubric"]] == ["helpful", "honest", "harmless", "clear"]
    assert p["n_items"] == 3 and p["n_labels"] == 0


def test_requires_sign_in(client):
    pid = make_project(client)
    assert client.get(f"/api/projects/{pid}/next").status_code == 401
    assert client.get(f"/api/projects/{pid}/next", headers={"X-Rater-Id": "999"}).status_code == 401


def test_full_labeling_flow(client):
    pid = make_project(client, overlap=2)
    ann, ben, cat = (sign_in(client, n) for n in ("ann", "ben", "cat"))
    assert label_all(client, pid, ann, "A") == 3
    assert label_all(client, pid, ben, "A") == 3
    # Overlap is 2, so cat only gets the gold item (gold is shown to everyone).
    assert label_all(client, pid, cat, "B") == 1

    st = client.get(f"/api/projects/{pid}/stats").json()
    assert st["n_labels"] == 7 and st["n_raters"] == 3 and st["items_fully_labeled"] == 3
    raters = {r["rater"]: r for r in st["raters"]}
    assert raters["ann"]["gold_accuracy"] == 1.0
    assert raters["cat"]["gold_accuracy"] == 0.0
    assert st["percent_agreement"] == 1.0

    r = client.get(f"/api/projects/{pid}/export/dpo")
    assert r.headers["content-type"].startswith("application/x-ndjson")
    rows = [json.loads(l) for l in r.text.splitlines()]
    assert [(x["prompt"], x["chosen"], x["rejected"]) for x in rows] == [("p1", "a1", "b1"), ("p2", "a2", "b2")]

    labels = [json.loads(l) for l in client.get(f"/api/projects/{pid}/export/labels").text.splitlines()]
    assert len(labels) == 7 and {"rater", "score", "criteria", "shown_swapped"} <= labels[0].keys()


def test_duplicate_and_invalid_labels(client):
    pid = make_project(client)
    ann = sign_in(client, "ann")
    a = client.get(f"/api/projects/{pid}/next", headers=ann).json()
    body = {"item_id": a["item_id"], "swapped": a["swapped"], "score": 1}
    url = f"/api/projects/{pid}/labels"
    assert client.post(url, headers=ann, json=body).status_code == 201
    assert client.post(url, headers=ann, json=body).status_code == 409
    assert client.post(url, headers=ann, json={**body, "score": 5}).status_code == 422
    assert client.post(url, headers=ann, json={**body, "item_id": 9999}).status_code == 404
    other = client.get(f"/api/projects/{pid}/next", headers=ann).json()
    bad = {"item_id": other["item_id"], "swapped": False, "score": 0, "criteria": {"nope": "left"}}
    assert client.post(url, headers=ann, json=bad).status_code == 422


def test_import_errors_and_missing_project(client):
    pid = make_project(client)
    r = client.post(f"/api/projects/{pid}/import", json={"jsonl": "oops"})
    assert r.status_code == 422 and "line 1" in r.json()["detail"]
    assert client.get("/api/projects/999").status_code == 404
    assert client.get("/api/projects/999/stats").status_code == 404


def test_import_sample_dataset(client):
    pid = client.post("/api/projects", json={"name": "Sample"}).json()["id"]
    r = client.post(f"/api/projects/{pid}/import", json={"jsonl": SAMPLE.read_text(encoding="utf-8")})
    assert r.json() == {"imported": 40}
    assert client.post("/api/projects/sample").json()["n_items"] == 40
    assert [p["n_items"] for p in client.get("/api/projects").json()] == [40, 40]


def test_custom_rubric(client):
    rubric = [{"key": "correct", "label": "Correctness"}]
    pid = client.post("/api/projects", json={"name": "R", "rubric": rubric}).json()["id"]
    assert client.get(f"/api/projects/{pid}").json()["rubric"][0]["key"] == "correct"
    assert client.post("/api/projects", json={"name": "R", "rubric": [{"key": "Bad Key", "label": "x"}]}).status_code == 422
