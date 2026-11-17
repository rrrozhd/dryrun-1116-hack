"""Local-model decider: picks one schema value for a raw value, or abstains.

The model never writes values or code. It sees a numbered list (0 = none/unsure,
1..9 = candidates) and we read its next-token probabilities over the digit tokens
in a single forward pass. `score` is that selection probability, not a probability
that the mapping is correct.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Callable, Sequence

from datarescue import baseline

# Never send an ambient Hugging Face login token; generation is offline.
os.environ["HF_HUB_DISABLE_IMPLICIT_TOKEN"] = "1"

MODEL_ID = "Qwen/Qwen2.5-0.5B-Instruct"
REVISION = "7ae557604adf67be50417f59c2c2f167def9a775"
THRESHOLD = 0.35  # pinned on fixtures/dev only: middle of the 0.30-0.40 plateau (0.25 adds 2 wrong changes)
ORDERS = 2  # score forward and reversed option order, average, to cancel position bias
CACHE = Path(__file__).resolve().parent.parent / ".models"
MAX_OPTIONS = 9  # digits 1..9 are single tokens; 0 is "none/unsure"; larger enums go in rounds

SYSTEM = (
    "You map a messy value from a CSV file to one allowed value of a schema field. "
    "Answer with the option number only. Answer 0 if no option has the same meaning "
    "or if you are unsure."
)

# probs_fn(field_desc, raw, options) -> probabilities for digits 0..len(options)
ProbsFn = Callable[[str, str, Sequence[str]], list[float]]


def _pick(probs_fn: ProbsFn, field_desc: str, raw: str, options: Sequence[str],
          orders: int) -> tuple[str, float, float]:
    """Best option, its score and the none/unsure score, averaged over `orders` orderings."""
    totals = {o: 0.0 for o in options}
    none = 0.0
    for order in (list(options), list(options)[::-1])[:orders]:
        probs = probs_fn(field_desc, raw, order)
        none += probs[0]
        for option, p in zip(order, probs[1:]):
            totals[option] += p
    best = max(options, key=totals.__getitem__)
    return best, totals[best] / orders, none / orders


def decide_with(probs_fn: ProbsFn, field_desc: str, allowed: Sequence[str], raw: str,
                threshold: float = THRESHOLD, orders: int = ORDERS) -> dict:
    """Average option probabilities over `orders` orderings, then pick or abstain."""
    options = list(allowed)
    if not options:
        return {"value": None, "score": 0.0, "decided_by": "model", "reason": "no allowed values"}
    # More than 9 options: pick a winner per group of 9, then a final round among winners.
    while len(options) > MAX_OPTIONS:
        groups = [options[i:i + MAX_OPTIONS] for i in range(0, len(options), MAX_OPTIONS)]
        options = [g[0] if len(g) == 1 else _pick(probs_fn, field_desc, raw, g, orders)[0] for g in groups]
    best, score, none = _pick(probs_fn, field_desc, raw, options, orders)
    if score < threshold or none >= score:
        return {"value": None, "score": round(score, 4), "decided_by": "model",
                "reason": f"abstain: best {best!r} {score:.2f}, none/unsure {none:.2f}"}
    return {"value": best, "score": round(score, 4), "decided_by": "model",
            "reason": f"chose {best!r} with selection score {score:.2f}"}


class ModelDecider:
    """Loads the pinned local model once; `decide` matches the baseline's interface."""

    def __init__(self, model_id: str = MODEL_ID, revision: str = REVISION,
                 threshold: float = THRESHOLD, orders: int = ORDERS) -> None:
        from huggingface_hub import snapshot_download
        import torch
        from transformers.models.auto.modeling_auto import AutoModelForCausalLM
        from transformers.models.auto.tokenization_auto import AutoTokenizer

        # local_files_only: a missing snapshot raises instead of downloading or faking output
        snapshot = snapshot_download(repo_id=model_id, revision=revision, cache_dir=CACHE,
                                     token=False, local_files_only=True)
        self.model_id, self.revision = model_id, revision
        self.threshold, self.orders = threshold, orders
        self._torch = torch
        self.tokenizer = AutoTokenizer.from_pretrained(
            snapshot, local_files_only=True, token=False, trust_remote_code=False)
        self.model = AutoModelForCausalLM.from_pretrained(
            snapshot, local_files_only=True, token=False, trust_remote_code=False,
            use_safetensors=True, torch_dtype=torch.float32).to("cpu").eval()
        self.digit_ids = [self.tokenizer.encode(str(i))[0] for i in range(MAX_OPTIONS + 1)]

    def option_probs(self, field_desc: str, raw: str, options: Sequence[str]) -> list[float]:
        lines = ["0. none of these / unsure"] + [f"{i}. {o}" for i, o in enumerate(options, 1)]
        user = f"Field: {field_desc}\nRaw value: {raw!r}\nOptions:\n" + "\n".join(lines)
        messages = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": user}]
        text = self.tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        inputs = self.tokenizer(text, return_tensors="pt")
        with self._torch.inference_mode():
            logits = self.model(**inputs).logits[0, -1]
        ids = self.digit_ids[: len(options) + 1]
        return self._torch.softmax(logits[ids], dim=0).tolist()

    def decide(self, field_desc: str, allowed: Sequence[str], raw: str) -> dict:
        return decide_with(self.option_probs, field_desc, allowed, raw, self.threshold, self.orders)


_decider: ModelDecider | None = None


def decide(field_desc: str, allowed: Sequence[str], raw: str) -> dict:
    """Agent decider (`--decider model`): the difflib baseline answers first; the local model is
    asked only where the baseline abstains. `decided_by` records which one made each choice."""
    global _decider
    d = baseline.decide(field_desc, list(allowed), raw)
    if d["value"] is not None:
        return d
    if _decider is None:
        _decider = ModelDecider()
    return _decider.decide(field_desc, allowed, raw)
