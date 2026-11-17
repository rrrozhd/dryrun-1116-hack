"""Clean a CSV against a declared schema.

uv run python -m datarescue clean INPUT.csv --schema SCHEMA.json --out DIR [--decider model|baseline]

Writes DIR/cleaned.csv, DIR/audit.jsonl and DIR/abstained.jsonl; the input is never written.
"""

import argparse
import importlib
import json
import sys
import time

from datarescue import agent


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="datarescue", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="command", required=True)
    c = sub.add_parser("clean", help="map headers and enum values to the schema, with an audit trail")
    c.add_argument("input")
    c.add_argument("--schema", required=True)
    c.add_argument("--out", required=True, help="new output directory")
    c.add_argument("--decider", choices=["model", "baseline"], default="model")
    a = p.parse_args(argv)

    started = time.monotonic()
    decide = importlib.import_module(f"datarescue.{a.decider}").decide
    result = agent.run(a.input, a.schema, a.out, decide)
    print(json.dumps({
        "decider": a.decider,
        "header_changes": len(result["header_events"]),
        "cell_changes": len(result["cell_events"]),
        "abstained": len(result["abstained"]),
        "input_sha256": result["input_sha256"],
        "out": a.out,
        "seconds": round(time.monotonic() - started, 1),
    }, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
