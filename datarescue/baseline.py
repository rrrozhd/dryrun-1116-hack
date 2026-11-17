"""Fixed-rule baseline decider: closest allowed value by stdlib difflib, else abstain."""

import difflib

CUTOFF = 0.6  # difflib's own default; fixed before any model results, never tuned on held-out


def decide(field_desc: str, allowed: list[str], raw: str) -> dict:
    """Same Decider interface as the model: field description, allowed targets, raw value."""
    by_lower = {a.lower(): a for a in allowed}
    hit = difflib.get_close_matches(raw.strip().lower(), list(by_lower), n=1, cutoff=CUTOFF)
    if not hit:
        return {"value": None, "score": 0.0, "decided_by": "baseline", "reason": f"no match >= {CUTOFF}"}
    score = difflib.SequenceMatcher(None, raw.strip().lower(), hit[0]).ratio()
    return {"value": by_lower[hit[0]], "score": round(score, 3), "decided_by": "baseline",
            "reason": f"difflib ratio {score:.2f}"}
