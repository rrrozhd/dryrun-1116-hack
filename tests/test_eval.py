import json
from pathlib import Path

from datarescue import baseline
from datarescue.eval import items, score

SCHEMA = {"fields": {"status": {"type": "enum", "description": "order status", "values": ["paid", "unpaid"]}}}
GOLD = {"headers": {"Status": "status", "Notes": None},
        "values": {"status": {"PAID": "paid", "settled": "paid", "on hold": None, "x": None}}}


def table(answers):
    return lambda desc, allowed, raw: {"value": answers[raw], "confidence": 1.0}


def test_metric_arithmetic_hand_checked():
    # Status->status right, Notes->status wrong, PAID right, settled missed, on hold abstain ok, x -> off-list
    m = score(table({"Status": "status", "Notes": "status", "PAID": "paid", "settled": None,
                     "on hold": None, "x": "bogus"}), SCHEMA, GOLD)
    assert (m["total"], m["correct_change"], m["wrong_change"], m["missed"], m["correct_abstain"]) == (6, 2, 1, 1, 2)
    assert m["accuracy"] == round(4 / 6, 3) and m["change_precision"] == round(2 / 3, 3)


def test_baseline_matches_close_spelling_and_abstains_on_unrelated():
    assert baseline.decide("order status", ["paid", "unpaid"], "PAID")["value"] == "paid"
    assert baseline.decide("order status", ["paid", "unpaid"], "money back")["value"] is None


def test_fixtures_are_consistent():
    for d in Path("fixtures").iterdir():
        schema = json.loads((d / "schema.json").read_text(encoding="utf-8"))
        gold = json.loads((d / "gold.json").read_text(encoding="utf-8"))
        header = (d / "input.csv").read_text(encoding="utf-8").splitlines()[0]
        assert list(gold["headers"]) == header.split(",")
        for kind, field, _, allowed, raw, expected in items(schema, gold):
            assert expected is None or expected in allowed, (d.name, raw)
