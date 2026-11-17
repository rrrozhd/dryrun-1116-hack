import csv
import json

import pytest

from datarescue.tools import apply, profile, verify_audit
from datarescue.schema import load_schema


SCHEMA = {"fields": {"state": {"type": "enum", "values": ["NY", "CA"], "description": "State"}}}


def decision(value):
    return {"value": value, "score": 0.9, "decided_by": "test", "reason": "explicit test decision"}


def source(tmp_path, text="State,notes\nNew York,a\n?,b\nNew York,c\n"):
    path = tmp_path / "input.csv"
    path.write_text(text)
    return path


def test_apply_preserves_input_audits_each_occurrence_and_abstains(tmp_path):
    path = source(tmp_path)
    before = path.read_bytes()
    result = apply(path, SCHEMA, {0: decision("state")}, {0: {"New York": decision("NY"), "?": decision(None)}}, tmp_path / "out")
    assert result is not None
    assert path.read_bytes() == before
    assert len(result["header_events"]) == 1
    assert [e["row"] for e in result["cell_events"]] == [1, 3]
    assert any(e["row"] == 2 and e["column"] == 0 for e in result["abstained"])
    with (tmp_path / "out/cleaned.csv").open(newline="") as f:
        assert list(csv.reader(f)) == [["state", "notes"], ["NY", "a"], ["?", "b"], ["NY", "c"]]
    events = [json.loads(line) for line in (tmp_path / "out/audit.jsonl").read_text().splitlines()]
    verify_audit(path, tmp_path / "out/cleaned.csv", events)
    for altered in (events[:-1], events + [events[-1]], [{**events[0], "before": "wrong"}, *events[1:]]):
        with pytest.raises(ValueError):
            verify_audit(path, tmp_path / "out/cleaned.csv", altered)


def test_profile_preserves_raw_values(tmp_path):
    p = profile(source(tmp_path), SCHEMA)
    assert p["row_count"] == 3
    assert p["columns"][0]["values"] == {"New York": 2, "?": 1}


@pytest.mark.parametrize("text", ["x,x\na,b\n", "x,y\na\n", ""])
def test_rejects_bad_csv(tmp_path, text):
    with pytest.raises(ValueError):
        profile(source(tmp_path, text), SCHEMA)


def test_collision_abstains_without_rebinding_values(tmp_path):
    path = source(tmp_path, "State,state\nNew York,CA\n")
    r = apply(path, SCHEMA, {0: decision("state")}, {0: {"New York": decision("NY")}}, tmp_path / "out")
    assert not r["header_events"] and not r["cell_events"]
    assert "New York" in (tmp_path / "out/cleaned.csv").read_text()


def test_invalid_enum_rejected_before_writing(tmp_path):
    path = source(tmp_path)
    with pytest.raises(ValueError):
        apply(path, SCHEMA, {0: decision("state")}, {0: {"New York": decision("XX")}}, tmp_path / "out")
    assert not (tmp_path / "out").exists()


def test_refuses_input_output_alias(tmp_path):
    path = tmp_path / "cleaned.csv"
    path.write_text("state\nNY\n")
    with pytest.raises(ValueError):
        apply(path, SCHEMA, {}, {}, tmp_path)
    assert path.read_text() == "state\nNY\n"


def test_multiline_records_and_non_cascading_value_maps(tmp_path):
    path = source(tmp_path, 'state,notes\nNY,"two\nlines"\nCA,one\n')
    result = apply(path, SCHEMA, {}, {0: {"NY": decision("CA"), "CA": decision("NY")}}, tmp_path / "out")
    assert [(e["row"], e["before"], e["after"]) for e in result["cell_events"]] == [(1, "NY", "CA"), (2, "CA", "NY")]
    verify_audit(path, tmp_path / "out/cleaned.csv", result["cell_events"])
    assert result["abstained"][-1]["row"] == 2


def test_header_collision_rollback_reaches_fixed_point(tmp_path):
    path = source(tmp_path, "A,B,C\na,b,c\n")
    schema = {"fields": {name: {"type": "string"} for name in ("A", "B", "C")}}
    result = apply(path, schema, {0: decision("B"), 1: decision("C")}, {}, tmp_path / "out")
    assert result["header_events"] == []
    assert {(e["row"], e["column"]) for e in result["abstained"]} == {(None, 0), (None, 1), (1, 0), (1, 1)}


def test_header_swap_keeps_original_column_identity(tmp_path):
    path = source(tmp_path, "A,B\nx,y\n")
    schema = {"fields": {"A": {"type": "enum", "values": ["a"]}, "B": {"type": "enum", "values": ["b"]}}}
    result = apply(path, schema, {0: decision("B"), 1: decision("A")}, {0: {"x": decision("b")}, 1: {"y": decision("a")}}, tmp_path / "out")
    with (tmp_path / "out/cleaned.csv").open(newline="") as f:
        assert list(csv.reader(f)) == [["B", "A"], ["b", "a"]]
    verify_audit(path, tmp_path / "out/cleaned.csv", result["header_events"] + result["cell_events"])


@pytest.mark.parametrize("link", ["symlink", "hardlink"])
def test_input_alias_in_output_directory_is_rejected(tmp_path, link):
    path = source(tmp_path)
    original = path.read_bytes()
    out = tmp_path / "out"
    out.mkdir()
    target = out / "audit.jsonl"
    if link == "symlink":
        target.symlink_to(path)
    else:
        target.hardlink_to(path)
    with pytest.raises(ValueError, match="overwrite input"):
        apply(path, SCHEMA, {}, {}, out)
    assert path.read_bytes() == original
    assert not (out / "cleaned.csv").exists()


@pytest.mark.parametrize("change", ["missing_reason", "bad_score"])
def test_replay_rejects_malformed_provenance(tmp_path, change):
    path = source(tmp_path)
    result = apply(path, SCHEMA, {0: decision("state")}, {}, tmp_path / "out")
    events = result["header_events"]
    if change == "missing_reason":
        del events[0]["reason"]
    else:
        events[0]["score"] = float("nan")
    with pytest.raises(ValueError):
        verify_audit(path, tmp_path / "out/cleaned.csv", events)


@pytest.mark.parametrize("text", [
    '{"fields":{"x":{"type":"enum","values":["a","a"]}}}',
    '{"fields":{"x":{"type":"number"}}}',
    '{"fields":{"x":{"type":"string"},"x":{"type":"date"}}}',
])
def test_invalid_or_duplicate_schema_rejected(tmp_path, text):
    path = tmp_path / "schema.json"
    path.write_text(text)
    with pytest.raises(ValueError):
        load_schema(path)


@pytest.mark.parametrize("kind", ["string", "date"])
def test_non_enum_value_maps_rejected(tmp_path, kind):
    path = source(tmp_path, "field\nraw\n")
    schema = {"fields": {"field": {"type": kind}}}
    with pytest.raises(ValueError, match="enum"):
        apply(path, schema, {}, {0: {"raw": decision(None)}}, tmp_path / "out")
    assert not (tmp_path / "out").exists()
