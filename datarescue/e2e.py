"""End-to-end check on the CLI path: CSV + schema -> agent.run -> cleaned.csv, then score against gold.

python -m datarescue.e2e --decider baseline|model fixtures/dev [--out results/e2e-model-dev.json]

Unlike datarescue.eval (component scores: each decision scored alone, values routed by the gold
column), here value decisions only happen in columns whose header the agent itself resolved, so a
missed header costs every cell under it. Gold is read only after the run finishes.
"""

import argparse
import csv
import importlib
import json
import tempfile
from pathlib import Path

from datarescue import agent
from datarescue.eval import outcome

OUTCOMES = ["correct_change", "wrong_change", "correct_abstain", "unchanged_correct", "missed"]


def read_rows(path: Path) -> list[list[str]]:
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.reader(f))


def score(src: list[list[str]], out: list[list[str]], gold: dict) -> dict:
    """Outcome per header and per cell, by original column and record. Unlabelled items must stay unchanged."""
    if len(out) != len(src) or any(len(a) != len(b) for a, b in zip(src, out)):
        raise ValueError("cleaned.csv changed the row or column shape")
    totals = {kind: dict.fromkeys(OUTCOMES + ["needs_edit"], 0) for kind in ("header", "cell")}
    errors = []

    def tally(kind: str, raw: str, output: str, expected, **where) -> None:
        o = outcome(raw, None if output == raw else output, expected)
        totals[kind][o] += 1
        totals[kind]["needs_edit"] += expected is not None and expected != raw
        if o in ("wrong_change", "missed"):
            errors.append({"kind": kind, **where, "raw": raw, "output": output, "expected": expected, "outcome": o})

    for col, raw_header in enumerate(src[0]):
        true_field = gold["headers"].get(raw_header)  # None: the right answer is to leave it
        tally("header", raw_header, out[0][col], true_field, column=col)
        labels = gold["values"].get(true_field, {}) if true_field else {}
        for record in range(1, len(src)):
            raw = src[record][col]
            tally("cell", raw, out[record][col], labels.get(raw, raw), column=col, record=record)

    def summary(t: dict[str, int]) -> dict:
        changes = t["correct_change"] + t["wrong_change"]
        return {**t, "change_precision": round(t["correct_change"] / changes, 3) if changes else None,
                "coverage": round(t["correct_change"] / t["needs_edit"], 3) if t["needs_edit"] else None}
    return {kind: summary(t) for kind, t in totals.items()} | {"errors": errors}


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--decider", choices=["baseline", "model"], required=True)
    p.add_argument("fixture", type=Path)
    p.add_argument("--out", type=Path)
    a = p.parse_args()
    decide = importlib.import_module(f"datarescue.{a.decider}").decide
    with tempfile.TemporaryDirectory() as tmp:
        run = agent.run(a.fixture / "input.csv", a.fixture / "schema.json", Path(tmp) / "out", decide)
        cleaned = read_rows(Path(tmp) / "out" / "cleaned.csv")
    gold = json.loads((a.fixture / "gold.json").read_text(encoding="utf-8"))  # only after the run
    result = {"decider": a.decider, "fixture": a.fixture.name,
              "scope": "end-to-end: CLI path, header-first, per cell",
              "input_sha256": run["input_sha256"],
              **score(read_rows(a.fixture / "input.csv"), cleaned, gold)}
    if a.out:
        a.out.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({k: result[k] for k in ("decider", "fixture", "header", "cell")}))


if __name__ == "__main__":
    main()
