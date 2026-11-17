"""Score a decider against a fixture's frozen gold labels.

python -m datarescue.eval --decider baseline|model fixtures/heldout [--out metrics.json]
"""

import argparse
import importlib
import json
from pathlib import Path


def items(schema: dict, gold: dict):
    """Yield (kind, field, field_desc, allowed, raw, expected) for every labelled header and value."""
    fields = schema["fields"]
    header_desc = "CSV column header; schema fields: " + "; ".join(
        f"{name}: {f['description']}" for name, f in fields.items())
    for raw, expected in gold["headers"].items():
        yield "header", None, header_desc, list(fields), raw, expected
    for field, labels in gold["values"].items():
        for raw, expected in labels.items():
            yield "value", field, fields[field]["description"], fields[field]["values"], raw, expected


def outcome(predicted, expected) -> str:
    if predicted is None:
        return "correct_abstain" if expected is None else "missed"
    return "correct_change" if predicted == expected else "wrong_change"


def score(decide, schema: dict, gold: dict) -> dict:
    counts = dict.fromkeys(["correct_change", "wrong_change", "correct_abstain", "missed"], 0)
    rows = []
    for kind, field, desc, allowed, raw, expected in items(schema, gold):
        d = decide(desc, allowed, raw)
        value = d["value"]
        if value is not None and value not in allowed:  # out-of-allowlist output never counts as a change
            value = None
        o = outcome(value, expected)
        counts[o] += 1
        rows.append({"kind": kind, "field": field, "raw": raw, "expected": expected, "predicted": value,
                     "confidence": d.get("confidence"), "outcome": o})
    total = len(rows)
    changes = counts["correct_change"] + counts["wrong_change"]
    return {"total": total, **counts,
            "accuracy": round((counts["correct_change"] + counts["correct_abstain"]) / total, 3),
            "change_precision": round(counts["correct_change"] / changes, 3) if changes else None,
            "items": rows}


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--decider", choices=["baseline", "model"], required=True)
    p.add_argument("fixture", type=Path)
    p.add_argument("--out", type=Path)
    a = p.parse_args()
    decide = importlib.import_module(f"datarescue.{a.decider}").decide
    schema = json.loads((a.fixture / "schema.json").read_text(encoding="utf-8"))
    gold = json.loads((a.fixture / "gold.json").read_text(encoding="utf-8"))
    result = {"decider": a.decider, "fixture": a.fixture.name, **score(decide, schema, gold)}
    text = json.dumps(result, indent=2, ensure_ascii=False) + "\n"
    if a.out:
        a.out.write_text(text, encoding="utf-8")
    print(json.dumps({k: v for k, v in result.items() if k != "items"}))


if __name__ == "__main__":
    main()
