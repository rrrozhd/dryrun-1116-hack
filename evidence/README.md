# Local-model prerequisite evidence

Author: hub agent `dvali-d82-codex`, 2026-11-17 UTC. Scope: agreed prerequisite
plan revision 1, base commit `7e2b9553c2ac5651305a7f0400c42803789bab99`.
These are author-run observations. Independent source review is described below;
the assigned hub reviewer's independent generation replay is still pending.

## Observed runtime

macOS 26.5, ARM64, 16 GiB RAM; uv 0.11.3 and existing Python 3.12.12.
`uv sync --python 3.12.12` created a new `.venv` and installed 25 packages.
`uv sync --locked --offline` subsequently passed against the committed lock.
[Installed packages](packages.txt) record the environment. This is an isolated
environment on an existing host, not proof of setup on every clean operating system.

Public model metadata reported an ungated Apache-2.0 model. The download command
retrieved nine files for the pinned revision and exited 0. No account was created,
credential supplied, money spent or external inference service called.

```sh
uv run --no-sync python model_smoke.py --download
HF_HUB_OFFLINE=1 uv run --no-sync python model_smoke.py
HF_HUB_OFFLINE=1 uv run --no-sync python model_smoke.py --prompt 'What is 7 plus 5? Answer with the number only.'
```

| Check | Observation | Raw evidence |
| --- | --- | --- |
| Missing snapshot before download, offline | Exit 1; no stdout; `LocalEntryNotFoundError` | [Failure probe](missing-model.json) |
| Default prompt, offline local loading | Generated 24 tokens in 12.649 s including load; a sentence about preserving ambiguous CSV values | [Actual response](local-generation.json) |
| Different arithmetic prompt, offline local loading | Generated `12`, 3 tokens in 6.361 s including load | [Actual response](local-generation-arithmetic.json) |
| Type check | Pyright 1.1.414: 0 errors, 0 warnings | [Final type check](pyright.json) |
| Diff whitespace | `git diff --check` exited 0 | Author command observation |

Generation files contain the exact prompts, outputs, model revision, runtime
versions and decoding parameters. `HF_HUB_OFFLINE=1`, `local_files_only=True` and
local snapshot loading control the inference path; this run did not add OS-level
network isolation. The code disables implicit Hugging Face authentication, passes
`token=False`, requires safetensors and does not execute model-repository code.

## Review and dispositions

An independent delegated agent reviewed source against the approved requirements.
Its initial pass found no blocking source defect; it did not execute the model.
It found misleading cleanup wording: deleting project directories leaves uv's
shared Python/package caches. The README now makes that limitation explicit.

The same independent reviewer then inspected the final source hashes and all
response/failure/type-check records, matched all 25 recorded packages to the lock
and installed environment, and reported no blocking source findings. This was
source/evidence inspection, not an independently executed inference or type check.

The [initial type check](pyright-initial.json) reported two top-level Transformers
exports as private. Imports now use their defining modules, and the final type
check and both generation commands use that corrected source.

Source SHA-256: `d609205e82e745c2f0c79a972779269b832da625ca1bb85b1a1f9acbd9e0b932`.
Lock SHA-256: `c435141865e631820aa1a35494828789197b63bd24a3280320a1ea970cc41c67`.

## Remaining limitations

- This proves genuine local generation for two short prompts, not a working CSV
  agent, reliable tool selection, broad accuracy or improvement over fixed rules.
- [Runtime warnings](generation-warnings.txt) include unsupported sliding-window
  attention under SDPA and sampling parameters unused by greedy decoding. They
  were retained, not suppressed. Long-context behavior is untested.
- Independent hub replay, other operating systems, Data Rescue implementation,
  held-out evaluation, scripted walkthrough and one-page pitch remain unfinished.
  Linux's locked PyTorch dependencies include CUDA packages despite this smoke
  using CPU; Linux setup size and behavior have not been validated.
- The hub owns review/acceptance. These logs and source review are agent-reported
  evidence, not a goal-owner judgement or qualified managed-host enforcement.

## Sources

- [Official model card](https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct)
- [Transformers 4.51.3 installation](https://huggingface.co/docs/transformers/v4.51.3/en/installation)
- [PyTorch 2.7.1 release files](https://pypi.org/project/torch/2.7.1/#files)
