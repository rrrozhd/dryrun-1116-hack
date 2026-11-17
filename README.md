# dryrun-1116-hack
AMH hackathon dry run 2026-11-16: an agent swarm's 24 h entry (test, delete after)

The selected direction is **Data Rescue**, a Python agent for auditable CSV cleanup.
This revision supplies only the local-model prerequisite. The agent, CSV tools,
evaluation, walkthrough and pitch are still unfinished.

## Run the local-model smoke

Prerequisites: [uv](https://docs.astral.sh/uv/getting-started/installation/),
internet for the initial package/weight downloads, and enough memory/disk for a
0.5B model. No account, API key, paid service or GPU is required. The initial
validation target is macOS ARM64 with 16 GiB RAM; other platforms are unverified.
The project pins Python 3.12.12, Transformers 4.51.3 and PyTorch 2.7.1; `uv.lock`
pins their transitive dependencies. `uv sync` may download Python if absent.

```sh
git clone https://github.com/rrrozhd/dryrun-1116-hack.git
cd dryrun-1116-hack
uv sync --locked
uv run --no-sync python model_smoke.py --download
HF_HUB_OFFLINE=1 uv run --no-sync python model_smoke.py
```

To supply a different prompt after download:

```sh
HF_HUB_OFFLINE=1 uv run --no-sync python model_smoke.py --prompt "What is 7 plus 5? Answer with the number only."
```

The download command fetches public
[Qwen2.5-0.5B-Instruct](https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct)
weights at revision `7ae557604adf67be50417f59c2c2f167def9a775` into `.models/`.
The model is Apache-2.0 licensed; its license is downloaded with the weights.
Generation loads only this local snapshot, uses CPU float32 and greedy decoding,
and prints JSON containing the prompt, actual response, versions and timing.
Prompts are not sent to an inference service. Model-authored Python is never run.
Safetensors are required and model repository code is disabled.

## What this proves and how to debug it

A successful response proves local generation works for that prompt. It does not
establish accurate cleanup, reliable tool selection or superiority to fixed rules.
The 64-token limit can truncate an answer. An unavailable snapshot or runtime fails
with a nonzero exit and traceback; there is no canned response or remote fallback.
Check the final exception and the setup command that failed. Do not treat a partial
download or a fixture transcript as a successful generation.

See [recorded checks and limitations](evidence/README.md). The pinned runtime emits
attention/sampling warnings, retained with the evidence. The short smoke prompts
do not validate long-context behavior or the model's reasoning quality.

The flow is: explicit weight download → offline snapshot load → chat template →
local model generation → JSON evidence. A single Python script avoids a server,
agent framework and system-wide runtime installation. Dependencies and weights are
isolated in `.venv/` and `.models/`, both ignored by Git. Remove those two directories
to remove this project's environment and weights; uv's shared Python installation
and package cache remain. No deployment or background service is involved.
