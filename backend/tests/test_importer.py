import pytest

from prefstudio.cli import SAMPLE
from prefstudio.importer import PairFormatError, parse_pairs


def test_parse_valid_with_blank_lines():
    rows = parse_pairs('{"prompt":"p","response_a":"a","response_b":"b","gold":"B","meta":{"x":1}}\n\n')
    assert rows == [{"prompt": "p", "response_a": "a", "response_b": "b", "model_a": "", "model_b": "",
                     "gold": "B", "meta": {"x": 1}}]


@pytest.mark.parametrize(
    "text,msg",
    [
        ("not json", "line 1: invalid JSON"),
        ('{"prompt":"p","response_a":"a","response_b":"b"}\n[1]', "line 2: expected an object"),
        ('{"prompt":"p","response_a":"","response_b":"b"}', "missing or empty 'response_a'"),
        ('{"prompt":"p","response_a":"a","response_b":"b","gold":"C"}', "gold must be"),
        ("\n\n", "no pairs found"),
    ],
)
def test_parse_errors(text, msg):
    with pytest.raises(PairFormatError, match=msg):
        parse_pairs(text)


def test_sample_dataset_is_valid():
    rows = parse_pairs(SAMPLE.read_text(encoding="utf-8"))
    assert len(rows) == 40
    assert sum(1 for r in rows if r["gold"]) == 10
    assert len({r["prompt"] for r in rows}) == 40
