# Documentation delivery verification

These are **author-local** checks of the README, walkthrough and pitch. They do
not stand in for the separate hub review or clean-machine replay card.

- Implementation: `82daad176f42d6989386b022f433ff9cc454fe4e`, merged without rebasing
  into the documentation branch. Python source files and frozen results were not changed.
- Host: macOS ARM64, 16 GiB RAM; uv 0.11.3 and Python 3.12.12.
- Setup reused the existing project environment and cached 0.5B snapshot.
  `uv sync --locked` exited 0, resolving 48 packages and installing the four missing
  pytest dependencies. The explicit download command then verified the cached snapshot.
  This does not claim a cold package/weight download or another platform.
- The model slot was coordinated through the hub. CLI and evaluation model jobs
  ran sequentially, offline, without changing model, prompt, threshold or fixtures.

## Evidence

[commands.json](commands.json) records command arguments, exit codes, stdout and
stderr. It includes version checks, explicit download, all 39 tests, CLI help,
the dev model CLI, both held-out component/e2e deciders and the walkthrough's exact
audit-inspection Python snippet. The preceding `uv sync --locked` result is recorded
above from its interactive tool receipt. Temporary output paths and timings are
machine-local observations, not required values for another run.

[checks.json](checks.json) records:

- Exact JSON equality with all four committed baseline/cascade held-out reports.
- Byte equality of the dev cleaned CSV, edit audit and abstention log with
  `evidence/model/dev-run/`.
- The unchanged input SHA-256 and frozen held-out file hashes.
- SHA-256 values of the Python modules used by these checks.
- Successful audit inspection and the pitch's word count (under 500 words).

The dev CLI printed 3 header changes, 26 cell changes and 219 abstention records;
its 29 edit events comprise 26 baseline and 3 model decisions. The first model edit
was `México` → `MX` at original column 5, data record 4. These are actual outputs,
not generated example transcripts. The original author's result files remain the
numerical references for the pitch; this replay confirms their reproduction.

The runtime emitted its existing sliding-window/SDPA warning, retained in the
command records. No tuning was performed in response. Long-context behavior and
general model accuracy remain unverified. Model-only diagnostics were read from
the pinned original result; they were not rerun for this documentation delivery.

## Acceptance boundary

The README is the project overview and links to `docs/core.md` for detailed
interfaces and invariants, avoiding a duplicate project-model document. A separate
reviewer must follow it from the published documentation head. Upstream peer
approval and these local checks do not record the goal owner's acceptance.
