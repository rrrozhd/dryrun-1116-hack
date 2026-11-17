# Core delivery evidence

Implementation reviewed: `bac7eed` on `data-rescue-core`, based on main
`7e2b9553c2ac5651305a7f0400c42803789bab99`. Later commits in this candidate add
evidence only. Governing hub plan: `09c1d1eb`, revision 3; core card `cac618d9`.

## Checks and scope

- Fresh local clone with a new virtual environment: `uv run --frozen pytest -q`
  passed all 20 tests. See `pytest.txt` and `environment.txt`.
- Pyright 1.1.414 analyzed all three package files: zero errors and warnings.
  See `pyright.txt` for the exact command and raw result.
- The implementation's first test run failed before the code was implemented.
  Two later malformed-provenance regressions and two non-enum-map regressions
  failed before their fixes, then passed. The red runs are session evidence;
  only the final fresh-clone run is retained here.
- No held-out fixtures, gold labels, hackathon entries, winners, or gallery
  informed the core implementation. No model or network runtime dependency.

The highest-risk interactions are header collision rollback, original column
identity after swaps, repeated values, and audit completeness. Tests exercise
collision chains, swaps with different destination enums, non-cascading value
swaps, multiline records, abstentions, and omitted/duplicate/incorrect events.
They also check source bytes, invalid schema/targets, and symlink/hardlink
aliases before output creation. These examples establish tested behavior, not
exhaustive proof over all input files or filesystems.

## Independent source review

A separate local reviewing agent inspected the source read-only and ran targeted
temporary-directory probes. It identified two P2 defects in the first version:

1. Replay ignored missing or malformed provenance. The common replay boundary
   now requires all event fields and validates provenance types and score range.
2. Nonempty string/date value maps were silently ignored. The core now rejects
   these maps explicitly under v1's enum-only operation scope.

The reviewer replayed both failure classes after the fixes and reported zero
remaining findings. Its probes rejected missing fields, nontext provenance,
string/NaN/infinite/boolean/out-of-range scores, bad before-values, omitted and
duplicate changes; valid replay passed. It independently checked all three
output filenames through symlinks and hardlinks, plus header swaps, collision
chains, and per-cell abstentions on unresolved/colliding columns.

Reviewed source SHA-256 values:

```text
schema.py    3ec2c3313077bef0536a6aab5f271ca73ce3e4bfa711786043d80361048482ae
tools.py     aca1b21bb0168a50bc2cd0dfd10789d8de40bd1e434f3a36e7929ed4d10a0e24
test_core.py 8b744f5e0faf64c2fb2e5f84b9f7c1594c75cf805dd25b09e186dc238e86bbbb
```

## Limits and handoff

Keep the core and focused tests. No unsuccessful helper, model dependency, or
special-case fixture rule was retained. Whole-agent generation, CLI behavior,
evaluation arithmetic, model quality, and README replay belong to the other
agreed cards and remain unverified by this card.

Replay checks logical CSV consistency and well-formed provenance; it does not
authenticate a plausible provenance string, verify semantics, or validate the
abstention log. Output files are serialized separately, so I/O failure can leave
partial results. Concurrent writers, huge files, and other platforms have not
been qualified. These limits are also documented in `docs/core.md`.

This is an ordinary hub delivery. The local tests and agent review are reported
evidence, not convergence-gate managed execution or owner acceptance. The hub's
agreed reviewer must still replay the published candidate independently; owner
judgement is a later step.
