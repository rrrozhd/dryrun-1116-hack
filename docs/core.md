# CSV core API and invariants

This package applies decisions already made by a caller. It uses only the Python
standard library and never loads a model or uses the network. The agent and
evaluation layers own decision generation; both call the same core.

## Data and interfaces

`datarescue.schema.load_schema(path)` reads and validates a JSON object:

```json
{"fields":{"state":{"type":"enum","values":["NY","CA"],"description":"State"}}}
```

Field types are `enum`, `string`, and `date`. V1 changes values only in enum
fields. String and date fields may receive a header rename, but their values
are preserved. Duplicate schema keys, duplicate enum options, unsupported types,
duplicate CSV headers, and ragged CSV records are rejected.

`datarescue.tools.profile(csv_path, schema)` returns:

```python
{"header": ["State"], "row_count": 2,
 "columns": [{"column": 0, "header": "State", "values": {"New York": 2}}]}
```

All values remain strings. No stripping, null conversion, date parsing, number
conversion, row filtering, or deduplication occurs. Column indices refer to the
original zero-based position; row indices refer to the one-based data record,
not the physical line number. Quoted embedded newlines stay inside one record.

`apply(csv_path, schema, header_map, value_maps, out_dir)` takes maps keyed by
original column index, even after a header rename:

```python
from datarescue.tools import apply

def decision(value):
    return {"value": value, "score": 0.9,
            "decided_by": "example", "reason": "Caller supplied this choice"}

result = apply("input.csv", schema,
               {0: decision("state")},
               {0: {"New York": decision("NY"), "?": decision(None)}},
               "out")
```

Each decision requires `value` (string or `None`), finite `score` in [0, 1],
`decided_by`, and `reason`. The score is a selection score, not a calibrated
probability of correctness. `None` means abstain and preserve the source value.

Headers resolve first. An omitted exact schema header stays resolved; an
unmatched or explicitly abstained header stays unchanged. All renames involved
in a collision roll back, repeating if that exposes another collision. Their
columns become unresolved; precomputed value decisions for them are ignored
and every cell is recorded as an abstention. A collision-free header swap is
valid and retains original column identity.

For a resolved enum column, map each distinct raw value once; the same decision
applies to every occurrence without cascading rewrites. Targets must be schema
options. Without a supplied decision, already allowed values stay unchanged and
other values abstain. Nonempty value maps for resolved string/date fields are
rejected. Unknown column indices and unobserved raw-value keys are rejected.

## Outputs and verification

The return value contains `header_events`, `cell_events`, `abstained`, and
`input_sha256`. The output directory contains:

- `cleaned.csv`: ordered headers and string-cell matrix, with row/column counts
  and order preserved. CSV quoting and line endings may be reserialized.
- `audit.jsonl`: actual header changes followed by actual cell changes. No-ops
  are absent; every changed coordinate has exactly one event.
- `abstained.jsonl`: unresolved headers and each abstained cell, with equal
  before/after values.

Each JSONL record has `kind` (`header` or `cell`), `row` (`null` for headers),
`column`, `before`, `after`, `decided_by`, `score`, and `reason`.

`verify_audit(csv_path, cleaned_path, events)` rebuilds the entire logical CSV
from the input and change events. It rejects omitted, duplicate, extra,
out-of-bounds, malformed, and inconsistent events. It also validates provenance
fields and score range. It does **not** prove semantic correctness, authenticate
a plausible reason, or validate the separate abstention log. Keep the original
input and audit together for review; the output alone is not evidence of safety.

Input bytes are never written. Output files must be new; path aliases, including
existing symlinks and hardlinks to the input, are rejected before writing.
Validation failures raise `ValueError`; filesystem and parsing errors propagate.
An I/O failure while serializing can leave a partial output directory. Use a new
directory when retrying. Concurrent writers and atomic multi-file publication
are outside this local batch API's guarantees. Files are read into memory.

## Ownership and development

The flow is schema validation → CSV profile → caller decisions → header
resolution → enum edits/abstentions → replay check → serialization. Debug
unexpected preservation by inspecting the abstention reason and original column
index; debug an edit by replaying its audit with the unchanged source file.

Run `uv run --frozen pytest -q` for core checks. The test suite covers repeated
values, abstentions, invalid targets, collision chains, swaps, multiline
records, audit omissions/duplicates/provenance, and output aliases. Check results
and remaining limits are in `evidence/core/review.md`. There is no deployment or
migration in this card. Removing its commit removes the API; generated output
directories can be discarded without modifying source CSVs.
