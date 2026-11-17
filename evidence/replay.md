# Independent replay of the integrated head (card E)

**Result: every README step passed, and all four held-out results files reproduce byte for byte.**

- **Integrated commit:** `ae05ce0dd44fb9a7bad490f2832f98dcdfa652ae`, the current head of
  `hub/ff1ea14b-c112-4f67-96e3-8a14c1137df6` (docs card). It merges the model card
  (`82daad1`), which carries card 1, core and fixtures/eval.
- **Runtime receipts below were produced at `15f93fb2e25142a0aa9b84e584edeeb8c850d17e`**,
  the docs head before it. `git diff 15f93fb ae05ce0` touches only `README.md` and
  `evidence/model/README.md` (freeze-chronology prose; no command lines changed), so no
  code, configuration, fixture, results or command differs and the steps were not re-run.
- **Pre-acceptance:** at replay time (2026-11-17 ~07:00 UTC) the owner had accepted no
  upstream card. If an upstream card changes, this replay must be rerun on the new head.
- **Replayer:** dvali-d82-claude-2. It wrote no code, setup or docs for the entry; it reviewed the core card.
- **Raw log:** [`replay.log`](replay.log), with every command, its exit code, seconds and output.

## Host

macOS 26.5, arm64, 16 GiB RAM, uv 0.11.3, CPython 3.12.12 (installed by uv).
This is the same host the authors used, and it is **not a clean machine**: uv's shared
package cache and Python install were already warm, so `uv sync --locked` took under a
second. The model snapshot was downloaded fresh into the new clone's `.models/` (15 s).
Other platforms remain unverified.

## Steps (README "Setup and first run", then "Results and reproducibility")

| # | Command (verbatim from README) | Exit | Result |
|---|---|---|---|
| 1 | `git clone --branch hub/ff1ea14b-… https://github.com/rrrozhd/dryrun-1116-hack.git` | 0 | HEAD = `15f93fb` (then the docs head) |
| 2 | `uv sync --locked` | 0 | env created |
| 3 | `uv run --no-sync python model_smoke.py --download` | 0 | pinned revision `7ae5576` downloaded |
| 4 | `export HF_HUB_OFFLINE=1`; `RUN_DIR=$(mktemp -d)` | – | – |
| 5 | `… datarescue clean fixtures/dev/input.csv --schema fixtures/dev/schema.json --out "$RUN_DIR/model" --decider model` | 0 | 3 header / 26 cell changes, 219 abstained, 28.9 s |
| 6 | same with `--decider baseline` and `$RUN_DIR/baseline` | 0 | 3 header / 23 cell changes, 222 abstained |
| 7 | `uv run --no-sync pytest -q` | 0 | 39 passed |
| 8 | `… datarescue.eval --decider baseline fixtures/heldout` | 0 | 8 correct / 1 wrong / 22 missed |
| 9 | `… datarescue.e2e --decider baseline fixtures/heldout` | 0 | cells 12 / 4 / 79; headers 2 renamed, 5 missed |
| 10 | `… datarescue.eval --decider model fixtures/heldout` | 0 | 9 correct / 1 wrong / 21 missed (23 s) |
| 11 | `… datarescue.e2e --decider model fixtures/heldout` | 0 | cells 12 / 4 / 79; headers 2 renamed, 5 missed (14 s) |
| 12 | `git status --porcelain` | 0 | clean: no tracked file changed |

**One addition:** steps 8–11 also passed `--out "$RUN_DIR/<name>.json"`, so the full
results could be compared. It only adds a file write; the printed summary is unchanged.

## Comparison with committed files

| Replay output | Committed file | sha256 | Match |
|---|---|---|---|
| eval baseline | `results/baseline-heldout.json` | `79f32f79…3b913599` | identical |
| eval model | `results/model-heldout.json` | `5a18b1b7…cee18b3e` | identical |
| e2e baseline | `results/e2e-baseline-heldout.json` | `4180c32f…c36f708d` | identical |
| e2e model | `results/e2e-model-heldout.json` | `309326cd…4f81bde08a` | identical |
| dev CLI `cleaned.csv`, `audit.jsonl`, `abstained.jsonl` | `evidence/model/dev-run/` | – | identical |

The held-out freeze hashes posted in the room (msg 356) match `fixtures/heldout/gold.json`,
`input.csv` and `schema.json` at `15f93fb` and `ae05ce0` (unchanged between them). Every held-out figure in the README table
matches the committed results files.

## Findings

- **No mismatches**, so no bugs were filed.
- **Not replayed:** `results/model-only-heldout.json` (2 correct / 0 wrong / 28 missed),
  cited in the README and walkthrough. The README gives no command that produces it.
  The file's numbers match the docs, but this replay does not reproduce it.
- **Not verified:** a truly clean machine, or any platform other than macOS arm64.
- The pinned runtime prints a `Sliding Window Attention … sdpa` warning on each model run.
  It is already recorded in the card-1 evidence.
