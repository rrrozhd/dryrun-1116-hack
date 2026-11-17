"""Local-model decider: picks one schema value for a raw value, or abstains.

The model never writes values or code. It sees a numbered list (0 = none/unsure,
1..9 = candidates) and we read its next-token probabilities over the digit tokens
in a single forward pass. `score` is that selection probability, not a probability
that the mapping is correct.
"""

from __future__ import annotations

import difflib
import os
from pathlib import Path
from typing import Callable, Sequence

# Never send an ambient Hugging Face login token; generation is offline.
os.environ["HF_HUB_DISABLE_IMPLICIT_TOKEN"] = "1"

MODEL_ID = "Qwen/Qwen2.5-0.5B-Instruct"
REVISION = "7ae557604adf67be50417f59c2c2f167def9a775"
THRESHOLD = 0.5  # provisional; pinned from fixtures/dev only before the held-out run
ORDERS = 2  # score forward and reversed option order, average, to cancel position bias
CACHE = Path(__file__).resolve().parent.parent / ".models"
MAX_OPTIONS = 9  # digits 1..9 are single tokens; 0 is "none/unsure"

SYSTEM = (
    "You map a messy value from a CSV file to one allowed value of a schema field. "
    "Answer with the option number only. Answer 0 if no option has the same meaning "
    "or if you are unsure."
)

# probs_fn(field_desc, raw, options) -> probabilities for digits 0..len(options)
ProbsFn = Callable[[str, str, Sequence[str]], list[float]]


def shortlist(raw: str, allowed: Sequence[str], k: int = MAX_OPTIONS) -> list[str]:
    """Allowed values to show the model, in schema order.

    shortcut: enums above 9 values are cut to the 9 closest by difflib ratio, so a
    correct value that looks nothing like the raw one can be missed; upgrade to
    multi-token option scoring if fixtures need large enums.
    """
    if len(allowed) <= k:
        return list(allowed)
    ratio = lambda a: difflib.SequenceMatcher(None, raw.lower(), a.lower()).ratio()
    keep = set(sorted(allowed, key=ratio, reverse=True)[:k])
    return [a for a in allowed if a in keep]


def decide_with(probs_fn: ProbsFn, field_desc: str, allowed: Sequence[str], raw: str,
                threshold: float = THRESHOLD, orders: int = ORDERS) -> dict:
    """Average option probabilities over `orders` orderings, then pick or abstain."""
    options = shortlist(raw, allowed)
    if not options:
        return {"value": None, "score": 0.0, "decided_by": "model", "reason": "no allowed values"}
    totals = {o: 0.0 for o in options}
    none = 0.0
    for order in (options, options[::-1])[:orders]:
        probs = probs_fn(field_desc, raw, order)
        none += probs[0]
        for option, p in zip(order, probs[1:]):
            totals[option] += p
    best = max(options, key=totals.__getitem__)
    score = totals[best] / orders
    none /= orders
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
