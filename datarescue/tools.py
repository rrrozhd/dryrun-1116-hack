"""Apply materialized decisions with source coordinates and replayable audits."""
from collections import Counter
import csv
import hashlib
import json
import math
from pathlib import Path
from .schema import validate_schema


def read_csv(path: str | Path) -> tuple[list[str], list[list[str]]]:
    with Path(path).open(encoding="utf-8", newline="") as stream:
        table = list(csv.reader(stream, strict=True))
    if not table or not table[0] or len(set(table[0])) != len(table[0]):
        raise ValueError("CSV needs a nonempty, unique header")
    header, rows = table[0], table[1:]
    if any(len(row) != len(header) for row in rows):
        raise ValueError("CSV records must match header width")
    return header, rows


def profile(csv_path: str | Path, schema: dict) -> dict:
    validate_schema(schema)
    header, rows = read_csv(csv_path)
    return {"header": header, "row_count": len(rows), "columns": [
        {"column": col, "header": name, "values": dict(Counter(row[col] for row in rows))}
        for col, name in enumerate(header)]}


def _decision(value: str | None, reason: str) -> dict:
    return {"value": value, "score": 0.0, "decided_by": "rule", "reason": reason}


def _validate_decision(d: dict) -> None:
    if not isinstance(d, dict) or not {"value", "score", "decided_by", "reason"} <= d.keys():
        raise ValueError("Decision requires value, score, decided_by and reason")
    if d["value"] is not None and not isinstance(d["value"], str):
        raise ValueError("Decision value must be string or None")
    if type(d["score"]) not in (int, float) or not math.isfinite(d["score"]) or not 0 <= d["score"] <= 1:
        raise ValueError("Score must be finite and between zero and one")
    if not isinstance(d["reason"], str) or not isinstance(d["decided_by"], str):
        raise ValueError("Decision provenance must be text")


def _event(kind: str, row: int | None, column: int, before: str, after: str, d: dict) -> dict:
    return {"kind": kind, "row": row, "column": column, "before": before, "after": after,
            "decided_by": d["decided_by"], "score": d["score"], "reason": d["reason"]}


def _replay(header: list[str], rows: list[list[str]], events: list[dict]) -> tuple[list[str], list[list[str]]]:
    rebuilt_header, rebuilt_rows = header.copy(), [row.copy() for row in rows]
    seen = set()
    for event in events:
        required = {"kind", "row", "column", "before", "after", "decided_by", "score", "reason"}
        if not isinstance(event, dict) or not required <= event.keys():
            raise ValueError("Audit event requires coordinates, values and provenance")
        _validate_decision({"value": event["after"], "score": event["score"],
                            "decided_by": event["decided_by"], "reason": event["reason"]})
        kind, row, col = event.get("kind"), event.get("row"), event.get("column")
        if type(col) is not int or not 0 <= col < len(header):
            raise ValueError("Invalid audit column")
        if kind == "header" and row is None:
            target = rebuilt_header
        elif kind == "cell" and type(row) is int and 1 <= row <= len(rows):
            target = rebuilt_rows[row - 1]
        else:
            raise ValueError("Invalid audit kind or row")
        key = (kind, row, col)
        if key in seen or target[col] != event.get("before"):
            raise ValueError("Duplicate or incorrect audit before-value")
        if not isinstance(event.get("after"), str) or event["after"] == event["before"]:
            raise ValueError("Audit must record an actual string change")
        seen.add(key)
        target[col] = event["after"]
    if len(set(rebuilt_header)) != len(rebuilt_header):
        raise ValueError("Audit creates duplicate headers")
    return rebuilt_header, rebuilt_rows


def verify_audit(csv_path: str | Path, cleaned_path: str | Path, events: list[dict]) -> None:
    header, rows = read_csv(csv_path)
    if _replay(header, rows, events) != read_csv(cleaned_path):
        raise ValueError("Audit does not reproduce the complete cleaned CSV")


def apply(csv_path: str | Path, schema: dict, header_map: dict[int, dict],
          value_maps: dict[int, dict[str, dict]], out_dir: str | Path) -> dict:
    validate_schema(schema)
    source, output = Path(csv_path), Path(out_dir)
    original_bytes = source.read_bytes()
    header, rows = read_csv(source)
    fields = schema["fields"]
    for col in (*header_map, *value_maps):
        if type(col) is not int or not 0 <= col < len(header):
            raise ValueError("Maps require original integer column indices")
    decisions = [header_map.get(i, _decision(name if name in fields else None, "Original schema field" if name in fields else "Unresolved header"))
                 for i, name in enumerate(header)]
    for d in decisions:
        _validate_decision(d)
        if d["value"] is not None and d["value"] not in fields:
            raise ValueError("Header target absent from schema")
    cleaned_header = [d["value"] if d["value"] is not None else name for name, d in zip(header, decisions)]
    while len(set(cleaned_header)) != len(cleaned_header):
        counts = Counter(cleaned_header)
        for i, target in enumerate(cleaned_header):
            if counts[target] > 1 and target != header[i]:
                decisions[i] = _decision(None, "Header rename collision")
                cleaned_header[i] = header[i]
    header_events, cell_events, abstained = [], [], []
    for col, (before, after, d) in enumerate(zip(header, cleaned_header, decisions)):
        event = _event("header", None, col, before, after, d)
        if d["value"] is None:
            abstained.append(event)
        elif before != after:
            header_events.append(event)
    cleaned_rows = [row.copy() for row in rows]
    for col, d in enumerate(decisions):
        field = fields.get(cleaned_header[col]) if d["value"] is not None else None
        mapping = value_maps.get(col, {})
        if not isinstance(mapping, dict) or not set(mapping) <= {row[col] for row in rows}:
            raise ValueError("Value keys must be observed raw strings")
        if field and field["type"] != "enum" and mapping:
            raise ValueError("Value maps are only supported for enum fields")
        if field and field["type"] == "enum":
            for vd in mapping.values():
                _validate_decision(vd)
                if vd["value"] is not None and vd["value"] not in field["values"]:
                    raise ValueError("Target outside schema enum")
        for row_id, row in enumerate(rows, 1):
            raw = row[col]
            if field is None:
                vd = _decision(None, "Unresolved header; value preserved")
            elif field["type"] != "enum":
                continue
            else:
                vd = mapping.get(raw, _decision(raw if raw in field["values"] else None, "Already allowed" if raw in field["values"] else "No decision"))
            after = raw if vd["value"] is None else vd["value"]
            event = _event("cell", row_id, col, raw, after, vd)
            if vd["value"] is None:
                abstained.append(event)
            elif after != raw:
                cleaned_rows[row_id - 1][col] = after
                cell_events.append(event)
    events = header_events + cell_events
    if _replay(header, rows, events) != (cleaned_header, cleaned_rows):
        raise ValueError("Internal audit mismatch")
    paths = [output / name for name in ("cleaned.csv", "audit.jsonl", "abstained.jsonl")]
    for path in paths:
        if path.resolve() == source.resolve() or (path.exists() and path.samefile(source)):
            raise ValueError("Output would overwrite input")
        if path.exists():
            raise ValueError("Output files must not already exist")
    if source.read_bytes() != original_bytes:
        raise ValueError("Input changed during application")
    output.mkdir(parents=True, exist_ok=True)
    with paths[0].open("x", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(cleaned_header)
        writer.writerows(cleaned_rows)
    for path, records in zip(paths[1:], (events, abstained)):
        with path.open("x", encoding="utf-8") as stream:
            for record in records:
                stream.write(json.dumps(record, ensure_ascii=False, allow_nan=False) + "\n")
    return {"header_events": header_events, "cell_events": cell_events, "abstained": abstained,
            "input_sha256": hashlib.sha256(original_bytes).hexdigest()}
