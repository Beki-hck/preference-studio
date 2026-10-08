"""Parses comparison pairs from JSONL."""

from __future__ import annotations

import json


class PairFormatError(ValueError):
    pass


def parse_pairs(text: str) -> list[dict]:
    """Each line: {"prompt", "response_a", "response_b", optional "model_a",
    "model_b", "gold" ("A" or "B") and "meta"}. Errors name the line number."""
    rows = []
    for n, line in enumerate(text.splitlines(), 1):
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError as e:
            raise PairFormatError(f"line {n}: invalid JSON ({e.msg})") from None
        if not isinstance(obj, dict):
            raise PairFormatError(f"line {n}: expected an object")
        for key in ("prompt", "response_a", "response_b"):
            if not isinstance(obj.get(key), str) or not obj[key].strip():
                raise PairFormatError(f"line {n}: missing or empty {key!r}")
        gold = obj.get("gold")
        if gold not in (None, "A", "B"):
            raise PairFormatError(f"line {n}: gold must be 'A', 'B' or absent")
        rows.append(
            {
                "prompt": obj["prompt"],
                "response_a": obj["response_a"],
                "response_b": obj["response_b"],
                "model_a": str(obj.get("model_a", "")),
                "model_b": str(obj.get("model_b", "")),
                "gold": gold,
                "meta": obj.get("meta") if isinstance(obj.get("meta"), dict) else {},
            }
        )
    if not rows:
        raise PairFormatError("no pairs found")
    return rows
