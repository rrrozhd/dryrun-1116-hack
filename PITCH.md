# Data Rescue: CSV mapping you can inspect

People handed an unfamiliar spreadsheet need to decipher its headers and category
spellings. Data Rescue explores whether a small local model
can help map that export to a schema while keeping every change inspectable.

The Python CLI reads a CSV and a schema, chooses header mappings, then considers
distinct values only in resolved enum columns. Exact matches are preserved. A
fixed difflib rule answers first; a local Qwen2.5-0.5B-Instruct model handles the
remaining questions. The model scores allowed choices plus an abstention option.
Python applies decisions to a separate copy and replay-checks the edit log against
the original. No model-authored code runs.

The deliverable is a runnable command, cleaned CSV, audit of actual edits and
abstention log. Original input bytes, row/column order and counts are preserved.
Header collisions leave affected columns unresolved. Selection scores and audit
replay help inspect behavior; neither proves semantic correctness.

**The measured outcome is a tie.** On the frozen held-out export, both baseline and
cascade made 12 correct cell edits and 4 wrong edits, missing 79 needed edits.
Both renamed 2 of 7 headers needing a rename and missed 5. Unresolved headers
blocked potential value improvements. Users must review the proposed output.

The component diagnostic supplies the correct field association to value
questions: baseline scores 8 correct / 1 wrong, cascade 9 / 1 and model-only 2 / 0.
Model-only missed 28 edits. The cascade's extra isolated mapping did not improve
the final CSV. These small-fixture observations are not a general accuracy claim.

We chose Python for standard-library CSV/JSON tools and its local model ecosystem.
Pinned PyTorch and Transformers run on CPU, with an explicit public-weight download
and offline inference. No account, API key, paid service or GPU is needed. Keeping
v1 to headers and enums made preservation rules and failure cases testable.

The useful result is an inspectable local experiment and a concrete finding:
header resolution limits this model-assisted workflow. The next research question
is whether better header decisions improve final output without increasing wrong
edits or resource cost. This entry delivers the existing result honestly.

Reproduce it with [README.md](README.md) and [WALKTHROUGH.md](WALKTHROUGH.md).
Figures come from [integrated cascade](results/e2e-model-heldout.json),
[integrated baseline](results/e2e-baseline-heldout.json),
[component cascade](results/model-heldout.json), [baseline](results/baseline-heldout.json)
and [model-only](results/model-only-heldout.json), at implementation commit `82daad1`.
