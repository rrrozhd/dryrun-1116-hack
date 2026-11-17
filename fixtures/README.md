# Fixtures and evaluation

- `dev/`: order export, 43 labelled headers and values (23% must abstain). The only set used to tune prompts and thresholds.
- `heldout/`: volunteer sign-up export, 45 labelled items (31% must abstain). It was frozen in commit `9798cd4` before any model run, and none of its values appear in the scratch spike cases.
- Each set has `input.csv` (messy export), `schema.json` (target fields, enums and descriptions) and `gold.json` (expected target per header and per enum value; `null` means the right answer is to abstain).
- Gold is never shown to either decider.

Run the checks (stdlib, plus pytest for the tests):

```sh
uv run --no-project --python 3.12 --with pytest python -m pytest -q tests
uv run --no-project --python 3.12 python -m datarescue.eval --decider baseline fixtures/heldout --out results/baseline-heldout.json
```

`--decider model` imports `datarescue.model.decide`, which the model card provides.
**Scope: these are component scores.** Header decisions and value decisions are scored separately, and values are routed to their gold column, so a failed header decision does not hide value errors here. End-to-end cleanup metrics come from the integrated header-first `apply` path (core + model cards).

Metrics are classified by effective output; predicting the raw value counts as a no-op. They are `correct_change`, `wrong_change` (including any edit to an already-correct value), `correct_abstain`, `unchanged_correct`, `missed`, `change_precision` (no-ops excluded) and `coverage` (correct changes ÷ items whose gold differs from the raw value).
