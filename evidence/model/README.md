# Model card evidence (author-local, macOS 26.5 arm64, 16 GB, shared host)

All numbers below come from committed files in `results/`. These are the author's local
runs. The reviewer's fresh-clone replay is separate evidence.

## Frozen configuration (pinned at `057f738` before any held-out run)

- `--decider model` is a **cascade**: the difflib baseline answers first, and the local model
  is asked only where difflib abstains. The audit's `decided_by` says which one made each change.
  `score` is a difflib ratio when `decided_by` is `baseline` and a softmax value when it is `model`.
- Model: `Qwen/Qwen2.5-0.5B-Instruct` revision `7ae557604adf67be50417f59c2c2f167def9a775`
  (card 1's pin), CPU, float32, offline.
- Scoring: one forward pass per question, softmax over digit tokens `0..k` (0 = none/unsure),
  averaged over forward and reversed option order. More than 9 options go in rounds of 9.
- Abstain if the best score is below **0.35** or none/unsure >= best. The 0.35 threshold
  was chosen on `fixtures/dev` only: it is the middle of the 0.30-0.40 plateau, where every
  setting made 1 wrong change, and 0.25 adds 2 more wrong changes.
- 1.5B was **not measured**. Swap on this host was full (27.1 of 27.6 GB), so the run made no progress.

## Results

Component eval (`datarescue.eval`) scores each decision on its own and gives value
questions the true column. End-to-end (`datarescue.e2e`) runs the CLI path and scores every
output cell, so a missed header costs every cell under it.

| set | scorer | decider | correct | wrong | correct abstain | missed |
|---|---|---|---|---|---|---|
| dev | component | baseline | 11 | 1 | 10 | 21 |
| dev | component | cascade | 13 | 1 | 10 | 19 |
| dev | e2e cells | baseline | 19 | 4 | 24 | 73 |
| dev | e2e cells | cascade | 22 | 4 | 24 | 70 |
| held-out | component | baseline | 8 | 1 | 13 | 22 |
| held-out | component | cascade | 9 | 1 | 13 | 21 |
| held-out | component | model only (diagnostic) | 2 | 0 | 14 | 28 |
| held-out | e2e cells | baseline | 12 | 4 | 35 | 79 |
| held-out | e2e cells | cascade | 12 | 4 | 35 | 79 |
| held-out | e2e headers | both | 2 | 0 | 3 | 5 |

**Reading:** on held-out the cascade adds one correct component decision
(`Instagram` -> `social_media`) and nothing end to end. That cell's column header was not
resolved, so its values were never asked about. The 0.5B model alone abstains on almost
everything. The bottleneck is **header resolution**: 5 of the 7 held-out headers that needed
a rename were missed.

## Runs

- Real CLI run on dev with the model: `cli-dev-run.txt` (31.3 s including the model load).
  Outputs are in `dev-run/`.
- A missing model snapshot exits 1 with `LocalEntryNotFoundError`: `missing-model.txt`. There
  is no download, no remote call and no canned output.
- An existing output directory exits 1, and the input is untouched: `existing-out.txt`.
- `uv run --frozen pytest -q`: 39 passed. Pyright reports 0 errors on `datarescue` and `tests`.

Replay commands:

```sh
uv sync --locked
uv run --no-sync python model_smoke.py --download
export HF_HUB_OFFLINE=1
uv run --frozen python -m datarescue.eval --decider model fixtures/heldout
uv run --frozen python -m datarescue.e2e --decider model fixtures/heldout
uv run --frozen python -m datarescue clean fixtures/dev/input.csv --schema fixtures/dev/schema.json --out /tmp/dr-out
```
