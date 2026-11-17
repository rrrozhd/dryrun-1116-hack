import json
from pathlib import Path

from datarescue import baseline
from datarescue.eval import items, score

SCHEMA = {"fields": {"status": {"type": "enum", "description": "order status", "values": ["paid", "unpaid"]}}}
GOLD = {"headers": {"Status": "status", "Notes": None},
        "values": {"status": {"PAID": "paid", "settled": "paid", "on hold": None, "x": None}}}


def table(answers):
    return lambda desc, allowed, raw: {"value": answers[raw], "score": 1.0}


def test_metric_arithmetic_hand_checked():
    # Status->status right, Notes->status wrong, PAID right, settled missed, on hold abstain ok, x -> off-list
    m = score(table({"Status": "status", "Notes": "status", "PAID": "paid", "settled": None,
                     "on hold": None, "x": "bogus"}), SCHEMA, GOLD)
    assert (m["total"], m["correct_change"], m["wrong_change"], m["missed"], m["correct_abstain"]) == (6, 2, 1, 1, 2)
    assert m["accuracy"] == round(4 / 6, 3) and m["change_precision"] == round(2 / 3, 3)
    assert m["coverage"] == round(2 / 3, 3)  # gold targets: Status, PAID, settled


def test_baseline_matches_close_spelling_and_abstains_on_unrelated():
    assert baseline.decide("order status", ["paid", "unpaid"], "PAID")["value"] == "paid"
    assert baseline.decide("order status", ["paid", "unpaid"], "money back")["value"] is None


def test_fixtures_are_consistent():
    for d in (p for p in Path("fixtures").iterdir() if p.is_dir()):
        schema = json.loads((d / "schema.json").read_text(encoding="utf-8"))
        gold = json.loads((d / "gold.json").read_text(encoding="utf-8"))
        header = (d / "input.csv").read_text(encoding="utf-8").splitlines()[0]
        assert list(gold["headers"]) == header.split(",")
        for kind, field, _, allowed, raw, expected in items(schema, gold):
            assert expected is None or expected in allowed, (d.name, raw)


SIZE = {"fields": {"size": {"type": "enum", "description": "shirt size", "values": ["M", "XL"]}}}


def test_unchanged_only_counts_no_edits():
    gold = {"headers": {}, "values": {"size": {"XL": "XL"}}}
    for answer in ("XL", None):  # predicting the raw value is a no-op, same as abstaining
        m = score(table({"XL": answer}), SIZE, gold)
        assert (m["unchanged_correct"], m["correct_change"], m["missed"]) == (1, 0, 0)
        assert m["change_precision"] is None and m["coverage"] is None
    m = score(table({"XL": "M"}), SIZE, gold)  # editing an already-correct value is wrong
    assert m["wrong_change"] == 1


def test_mixed_edit_and_noop():
    gold = {"headers": {}, "values": {"size": {"XL": "XL", "medium": "M", "huge": None}}}
    m = score(table({"XL": "XL", "medium": "M", "huge": None}), SIZE, gold)
    assert (m["unchanged_correct"], m["correct_change"], m["correct_abstain"]) == (1, 1, 1)
    assert m["change_precision"] == 1.0 and m["coverage"] == 1.0  # denominator excludes the no-op
    m = score(table({"XL": "XL", "medium": "medium", "huge": None}), SIZE, gold)
    assert m["missed"] == 1 and m["coverage"] == 0.0


def test_component_scope_routes_values_by_gold_column():
    # Probe: the header decision fails (abstain), yet the value is still scored in its gold column.
    # Documented component behaviour; end-to-end scoring needs the header-first apply path.
    gold = {"headers": {"zzzzz": "status"}, "values": {"status": {"PAID": "paid"}}}
    m = score(table({"zzzzz": None, "PAID": "paid"}), SCHEMA, gold)
    by_kind = {r["kind"]: r["outcome"] for r in m["items"]}
    assert by_kind == {"header": "missed", "value": "correct_change"}
