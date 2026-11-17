# Scripted walkthrough

This demonstration uses the frozen v1 implementation at `82daad1`. It shows a
real local model decision, the audit trail, and the measured limitations. It is
the repository's scripted demo deliverable; no video is required to follow it.

## 1. Prepare the local environment

Clone the documentation candidate and follow [README setup](README.md#setup-and-first-run).
Run the following from the repository root, after the explicit weight download:

```sh
export HF_HUB_OFFLINE=1
RUN_DIR=$(mktemp -d)
```

Use the same shell for subsequent commands so `RUN_DIR` remains set. The new
temporary parent prevents existing output files from being overwritten. Internet
was needed for setup, but the model now loads from the local snapshot.

## 2. Clean the development export

```sh
uv run --no-sync python -m datarescue clean fixtures/dev/input.csv \
  --schema fixtures/dev/schema.json --out "$RUN_DIR/model" --decider model
```

Selected fields from the actual replay's stdout:

```json
{
  "decider": "model",
  "header_changes": 3,
  "cell_changes": 26,
  "abstained": 219,
  "input_sha256": "752ae6c134da874d24b0935e2473296b64753800fe16fead835c99f2096b56aa"
}
```

The command also prints your output path and elapsed time; those vary by run.
“26 cell changes” is a count of edits, not a count of correct edits. This mode is
the difflib-first cascade, with model inference only after the rule abstains.

## 3. Inspect and replay the audit

```sh
uv run --no-sync python - "$RUN_DIR/model" <<'PY'
import collections
import hashlib
import json
import sys
from pathlib import Path
from datarescue.tools import verify_audit

out = Path(sys.argv[1])
events = [json.loads(line) for line in (out / "audit.jsonl").read_text().splitlines()]
verify_audit("fixtures/dev/input.csv", out / "cleaned.csv", events)
print("audit replay: passed")
print("edit sources:", dict(collections.Counter(event["decided_by"] for event in events)))
print("model-selected edit:", json.dumps(next(event for event in events if event["decided_by"] == "model"), ensure_ascii=False))
print("input sha256:", hashlib.sha256(Path("fixtures/dev/input.csv").read_bytes()).hexdigest())
PY
```

The recorded replay prints `{'baseline': 26, 'model': 3}` for the 29 total edits
(3 headers plus 26 cells). Its first model-selected event is:

```json
{"kind": "cell", "row": 4, "column": 5, "before": "México", "after": "MX", "decided_by": "model", "score": 0.6158, "reason": "chose 'MX' with selection score 0.62"}
```

Column 5 is the original zero-based column; row 4 is the fourth data record.
Open `abstained.jsonl` to see why `E-mail Addr` was left unresolved: its model
selection score was below the threshold and “none/unsure” scored higher. A missing
header mapping can block useful value mappings. Audit replay verifies that the
edits explain the output; it does not establish that their meanings are correct.

## 4. Compare actual held-out outputs

```sh
uv run --no-sync python -m datarescue.e2e --decider baseline fixtures/heldout
uv run --no-sync python -m datarescue.e2e --decider model fixtures/heldout
```

These commands use the same header-first execution path as the CLI. Gold labels
are loaded only after prediction and application. Both commands reproduce:

| Outcome | Headers | Cells |
| --- | ---: | ---: |
| Correct changes | 2 | 12 |
| Wrong changes | 0 | 4 |
| Correct abstentions | 3 | 35 |
| Already correct and preserved | 0 | 140 |
| Missed changes | 5 | 79 |

The 270 cells are 27 records × 10 columns. Of 91 cells needing an edit, 12 were
correctly changed. Both deciders incorrectly map four occurrences of `XXL` to
`XL`; the schema describes adult sizes but does not make that substitution valid.
The cascade cannot repair a wrong baseline decision because it only receives
baseline abstentions.

The separate [component results](results/model-heldout.json) give value questions
their correct field association. They show one additional isolated match for the
cascade, but no gain survives to the cleaned CSV. The
[model-only diagnostic](results/model-only-heldout.json) makes 2 correct edits,
0 wrong edits and misses 28. Keep these diagnostics separate from integrated results.

## 5. Check the implementation and hand off the result

```sh
uv run --no-sync pytest -q
```

The documentation replay passed all 39 tests. They exercise core preservation,
collisions, missing/invalid decisions, model selection with injected probabilities,
metric arithmetic and integrated failure paths. They do not prove general model
accuracy; the real inference runs above supply separate evidence.

Use the unchanged source CSV as the rollback point. Keep a cleaned copy only after
reviewing its edits and unresolved fields. There is no automatic approval or undo
command. [Documentation verification](evidence/docs/README.md) records this run,
while [the original model evidence](evidence/model/README.md) retains the first
measured outputs. The independent hub replay is a separate review of the published head.
