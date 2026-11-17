"""Agent layer: asks a decider about each header and each distinct enum value, then hands
the materialized decision maps to core `apply`, which writes outputs and the audit."""

from __future__ import annotations

from pathlib import Path
from typing import Callable

from datarescue import tools
from datarescue.schema import load_schema

Decide = Callable[[str, list[str], str], dict]


def header_description(fields: dict) -> str:
    """Field description shown for header decisions; same wording as datarescue.eval uses on dev."""
    return "CSV column header; schema fields: " + "; ".join(
        f"{name}: {f.get('description', name)}" for name, f in fields.items())


def exact(value: str) -> dict:
    return {"value": value, "score": 1.0, "decided_by": "exact", "reason": "already matches the schema"}


def plan(profile: dict, fields: dict, decide: Decide) -> tuple[dict, dict]:
    """Build header_map {col: Decision} and value_maps {col: {raw: Decision}} keyed by original column index.

    Exact matches skip the decider; empty cells are never mapped.
    """
    names = list(fields)
    desc = header_description(fields)
    header_map, value_maps = {}, {}
    for col in profile["columns"]:
        index, header = col["column"], col["header"]
        d = exact(header) if header in fields else decide(desc, names, header)
        header_map[index] = d
        field = fields.get(d["value"]) if d["value"] is not None else None
        if not field or field.get("type") != "enum":
            continue
        allowed = list(field["values"])
        value_maps[index] = {
            raw: exact(raw) if raw in allowed else decide(field.get("description", d["value"]), allowed, raw)
            for raw in col["values"] if raw.strip()
        }
    return header_map, value_maps


def run(csv_path: str | Path, schema_path: str | Path, out_dir: str | Path, decide: Decide) -> dict:
    """Decide with no gold in sight, let core apply and serialize, then replay-check the audit."""
    schema = load_schema(schema_path)
    header_map, value_maps = plan(tools.profile(csv_path, schema), schema["fields"], decide)
    result = tools.apply(csv_path, schema, header_map, value_maps, out_dir)
    tools.verify_audit(csv_path, Path(out_dir) / "cleaned.csv", result["header_events"] + result["cell_events"])
    return result
