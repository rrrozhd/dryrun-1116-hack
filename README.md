# Data Rescue

A local Python agent that maps CSV headers and categorical values to a declared
schema, writes a separate cleaned copy, and records every edit for review.
This is the `dryrun-1116` entry for the Best Agent in Python category.

**Observed result:** on the frozen held-out CSV, the baseline and model-assisted
cascade each made 12 correct cell edits and 4 wrong edits, missing 79 needed edits.
Adding the model did not improve the final cleaned CSV. Review outputs before use:
an audit proves how data changed, not that a mapping is right.

Start with the [scripted walkthrough](WALKTHROUGH.md) or [one-page pitch](PITCH.md).
Results describe implementation commit
[`82daad1`](https://github.com/rrrozhd/dryrun-1116-hack/commit/82daad176f42d6989386b022f433ff9cc454fe4e).
This documentation candidate includes that tree; upstream owner acceptance is separate.

## Setup and first run

You need Git and [uv](https://docs.astral.sh/uv/getting-started/installation/), plus
internet for initial packages and weights. No account, API key, paid service or GPU
is required. Commands use a POSIX shell. The verified host is macOS ARM64 with
16 GiB RAM; other platforms remain unverified.

The project pins Python 3.12.12, PyTorch 2.7.1 and Transformers 4.51.3. `uv sync`
uses `uv.lock` and may download Python. The snapshot occupies about 1.00 GB
(953 MiB), excluding the environment and shared caches. CPU float32 inference
needs additional memory; avoid concurrent model jobs on a small machine.

During review, clone the published documentation candidate:

```sh
git clone --branch hub/ff1ea14b-c112-4f67-96e3-8a14c1137df6 https://github.com/rrrozhd/dryrun-1116-hack.git
cd dryrun-1116-hack
uv sync --locked
uv run --no-sync python model_smoke.py --download
export HF_HUB_OFFLINE=1
RUN_DIR=$(mktemp -d)
uv run --no-sync python -m datarescue clean fixtures/dev/input.csv \
  --schema fixtures/dev/schema.json --out "$RUN_DIR/model" --decider model
```

The explicit download retrieves public Qwen2.5-0.5B-Instruct weights at revision
`7ae557604adf67be50417f59c2c2f167def9a775` into `.models/`, including its Apache-2.0
license. Inference loads only local safetensors with repository code disabled.
`HF_HUB_OFFLINE=1` and local-only loading prevent model downloads during inference;
this is not an operating-system network sandbox.

The command prints counts, input SHA-256, output path and elapsed time. It writes
`cleaned.csv`, `audit.jsonl` and `abstained.jsonl`. Use a fresh destination each
time: existing output files are refused; an existing empty directory is allowed.
Input bytes are never written.

`--decider model` is the default **difflib-first cascade**: exact matches are kept,
difflib handles close spellings, and the model handles remaining decisions.
For the fixed-rule baseline, use `--decider baseline` and a different output path.
A cascade run need not load the model if rules answer every question; `decided_by`
in the audit identifies the source of each actual edit.

## What the agent does

Schema validation → CSV profile → header and value decisions → bounded Python
application → replay check. Header choices determine which columns can receive
enum mappings. Unresolved or colliding headers preserve their cells. Each distinct
nonblank value is considered once per resolved enum column.

The model scores numbered schema choices plus “none/unsure” using local forward
passes. It averages forward and reversed option orders, then abstains below the
dev-selected 0.35 threshold or when none/unsure wins. It cannot emit new values or
execute code. A selection score is not a correctness probability.

Only header renames and enum mappings are implemented. Row/column order and counts
are preserved; dates, numbers, units, null conversion and deduplication are outside
v1. Cell values remain strings. CSV quoting and line endings may be reserialized.
The [core contract](docs/core.md) defines schema shape, collisions, source
coordinates, output validation and audit guarantees. Start a custom schema from
[the development example](fixtures/dev/schema.json).

## Results and reproducibility

The threshold, prompt, model revision and option ordering were pinned on dev at
`057f738` before the first recorded model/cascade held-out evaluation (`644bc5a`).
Baseline held-out results were recorded earlier, at `faed211`. Replays keep the
frozen configuration. Fixtures are synthetic; this small evaluation is not a
production accuracy guarantee.

| Held-out evaluation | Baseline | Cascade (`model`) | Model only |
| --- | ---: | ---: | ---: |
| Component: correct edits / wrong edits | 8 / 1 | 9 / 1 | 2 / 0 |
| Component: missed edits | 22 | 21 | 28 |
| Integrated: correct cell edits / wrong edits | 12 / 4 | 12 / 4 | Not measured |
| Integrated: missed cell edits | 79 | 79 | Not measured |

Component scoring asks 45 isolated questions and supplies the correct field
association for value questions. It is a diagnostic, not final cleanup performance.
Integrated scoring uses predicted headers and the shared CLI execution path, then
compares output against gold by original column and record. Both modes rename 2 of
the 7 headers needing a rename and miss 5. Both make four wrong `XXL` → `XL` cell
edits. Cell edit precision is 12/16 = 75%; coverage is 12/91 = 13.2% for both modes.

Sources: [component baseline](results/baseline-heldout.json),
[cascade](results/model-heldout.json), [model-only diagnostic](results/model-only-heldout.json),
[integrated baseline](results/e2e-baseline-heldout.json),
[integrated cascade](results/e2e-model-heldout.json).
The cascade's extra isolated `Instagram` → `social_media` match never reaches the
output because its header is unresolved. Model-only precision covers just two
edits; it missed 28 component edits.

Run these from the repository root after setup:

```sh
uv run --no-sync pytest -q
HF_HUB_OFFLINE=1 uv run --no-sync python -m datarescue.eval --decider baseline fixtures/heldout
HF_HUB_OFFLINE=1 uv run --no-sync python -m datarescue.eval --decider model fixtures/heldout
HF_HUB_OFFLINE=1 uv run --no-sync python -m datarescue.e2e --decider baseline fixtures/heldout
HF_HUB_OFFLINE=1 uv run --no-sync python -m datarescue.e2e --decider model fixtures/heldout
```

The [model evidence](evidence/model/README.md) records original runs;
[documentation verification](evidence/docs/README.md) records this delivery's checks.
The earlier [generation smoke](evidence/README.md) is prerequisite evidence, not
an evaluation of the finished agent. The separate hub replay card verifies the
published documentation head independently; author logs do not establish that result.

## Debugging, limits and ownership

Inspect `abstained.jsonl` for preservation reasons and `audit.jsonl` for edits.
Coordinates use original zero-based columns and one-based data records. Replay
detects missing or inconsistent edit events; it neither certifies their meaning
nor separately validates the abstention log.

A missing snapshot raises `LocalEntryNotFoundError`: complete the explicit download
before offline use. Invalid schemas, ragged CSVs, duplicate headers and reused
output files cause nonzero exits. I/O failures can leave partial outputs; use a
fresh destination after correcting the cause. CSVs are held in memory. There is
no remote fallback, streaming mode or concurrent-writer guarantee.

`schema.py`/`tools.py` validate and apply; `agent.py` builds decisions;
`baseline.py`/`model.py` choose; `cli.py` exposes the command; `eval.py` measures
components and `e2e.py` measures outputs. Tests are under `tests/`. The standard
library handles CSV/JSON; PyTorch/Transformers supply local inference without an
agent server or orchestration framework. This overview and the core contract
describe the project's scope, critical flow and invariants.

There is no deployment or background service. To roll back a run, retain the input
and discard generated output. Removing `.venv/` and `.models/` removes this
checkout's environment and weights; uv's shared Python and package caches remain.
Better header resolution, larger datasets and cross-platform validation remain
future work. No model upgrade is included in this delivery.
