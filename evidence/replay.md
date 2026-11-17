# Independent replay of the integrated head (card E)

**Result: every README step passed, and all four held-out results files reproduce byte for byte.**

- **Integrated commit:** `ae05ce0dd44fb9a7bad490f2832f98dcdfa652ae`, the current head of
  `hub/ff1ea14b-c112-4f67-96e3-8a14c1137df6` (docs card). It merges the model card
  (`82daad1`), which carries card 1, core and fixtures/eval.
- **Runtime receipts (steps table, `replay.log`) were produced at
  `15f93fb2e25142a0aa9b84e584edeeb8c850d17e`**, the docs head before it. A fresh-clone
  revalidation of `ae05ce0` (below, [`revalidation.log`](revalidation.log)) shows only
  freeze-chronology prose changed, so inference was not re-run.
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

## Revalidation of the corrected docs head `ae05ce0`

Fresh clone of `hub/ff1ea14b-…` on 2026-11-17 ~07:12 UTC; raw output in
[`revalidation.log`](revalidation.log). Every check exited 0.

| Check | Result |
|---|---|
| `git rev-parse HEAD` | `ae05ce0dd44fb9a7bad490f2832f98dcdfa652ae` |
| `15f93fb` is an ancestor of HEAD | yes |
| `git diff --name-only 15f93fb HEAD` | `README.md`, `evidence/model/README.md` only (9 insertions, 3 deletions) |
| Content of that diff | the two freeze-chronology passages (`057f738` precedes the first model/cascade held-out run `644bc5a`; baseline results earlier at `faed211`) |
| All other paths, `git diff --quiet 15f93fb HEAD -- . ':(exclude)…'` | identical: code, `pyproject.toml`, `uv.lock`, fixtures, `results/`, other evidence |
| README fenced code blocks (every command), sha256 at both commits | `ccd4c002…7c401275` at both; `diff` empty |
| Held-out freeze files at HEAD | `gold.json` `af7dc8cb…b01ccae3`, `input.csv` `82fc01de…913e2aea1`, `schema.json` `cf8911f4…350e26d` |

Full sha256, 15f93fb replay output vs committed file at `ae05ce0` (`cmp` also passed on all seven):

| Replay output | Committed file at `ae05ce0` | sha256 (both) |
|---|---|---|
| `eval-baseline.json` | `results/baseline-heldout.json` | `79f32f79afc73f59282d3b966f2b710b29b9def7a580a4873329ec9c3b913599` |
| `eval-model.json` | `results/model-heldout.json` | `5a18b1b7b377a3da178a2b8b8a307d76a3657b8417d5e5d5bd1effd5cee18b3e` |
| `e2e-baseline.json` | `results/e2e-baseline-heldout.json` | `4180c32f3b2fa6670502a935510f62a3555fd8a574822f191bd83caec36f708d` |
| `e2e-model.json` | `results/e2e-model-heldout.json` | `309326cd6a3c78f8d68e332cefe4a78ffa8969f0a77aa64ed2fded4f81bde08a` |
| `model/cleaned.csv` | `evidence/model/dev-run/cleaned.csv` | `834a791fef59d65df53c3d3716c37d462204fd55a30a9822e80dc9c8d1efb6bc` |
| `model/audit.jsonl` | `evidence/model/dev-run/audit.jsonl` | `7d19540dafd0526f95338c476aa8b06ccc3832a72aa157d355e91fe4a45843d3` |
| `model/abstained.jsonl` | `evidence/model/dev-run/abstained.jsonl` | `65605626ed1ccb76ddfb1b7bf93ed1476e7b5b7ca74c317570770d6681fa8f78` |

Since no executable input or command differs, the `15f93fb` runtime results hold for `ae05ce0`.

## Findings

- **No mismatches**, so no bugs were filed.
- **Not replayed:** `results/model-only-heldout.json` (2 correct / 0 wrong / 28 missed),
  cited in the README and walkthrough. The README gives no command that produces it.
  The file's numbers match the docs, but this replay does not reproduce it.
- **Not verified:** a truly clean machine, or any platform other than macOS arm64.
- The pinned runtime prints a `Sliding Window Attention … sdpa` warning on each model run.
  It is already recorded in the card-1 evidence.
