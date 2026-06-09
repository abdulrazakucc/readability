"""Automated LLM-as-judge accuracy assessment for Aim 3 (SECONDARY / SCREENING).

IMPORTANT: This is NOT the pre-registered blinded human subspecialist review and
must never be presented as such. It is an automated, reproducible screening
signal produced by a panel of large language models. The primary Aim 3 endpoint
remains the blinded subspecialist (Dr. Naeem) scoring of `data/review/review_packet.csv`.

Design:
  - A panel of three LLM judges (the same three models used for rewriting) scores
    every rewrite against its original on the three locked rubric dimensions in
    `docs/accuracy_scoring_rubric.md`.
  - Each judge is blinded to which model produced the rewrite (it sees only the
    original text and the rewrite text).
  - Using all three models as judges lets us report inter-judge agreement and
    detect self-preference (a judge favouring its own rewrites).
  - Every call is cached to disk so the panel is resumable and deterministic to re-aggregate.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from .ai_rewrite import build_rewriter
from .provenance import utc_now_iso

JUDGE_PROMPT_VERSION = "judge_v1"

# Grounded in docs/accuracy_scoring_rubric.md. Anchors reproduced verbatim in spirit.
JUDGE_PROMPT = """You are a careful, board-certified physician reviewing patient-education material. \
You are shown an ORIGINAL patient-education text and a REWRITE that was intended to be easier to read. \
Judge ONLY medical content (not tone, style, or reading level). Score the REWRITE against the ORIGINAL \
on three dimensions using these exact anchors. Use integer scores 1-5.

ACCURACY (are all medical statements in the rewrite correct?):
  5 = every medical statement accurate, no misstatements
  4 = one minor inaccuracy that would not change patient understanding or behavior
  3 = one moderate inaccuracy that could confuse a patient but not cause harm
  2 = multiple inaccuracies, or one that could lead to a wrong patient decision
  1 = major inaccuracies likely to cause patient harm or refusal of needed care

COMPLETENESS (did the rewrite preserve the key preparation, risk, and safety points of the original?):
  5 = all key prep/risk/safety points present
  4 = all major points present, one minor point dropped
  3 = one major point (a prep step or a risk) dropped
  2 = multiple major points dropped; materially less informative
  1 = omits most prep/risk/safety information

ADDED_ERRORS (did the rewrite invent medical claims not in the original?) -- HIGHER IS WORSE:
  1 = nothing invented; only content present in the original
  2 = one trivial added claim (e.g., a generic wellness platitude)
  3 = one non-trivial added medical claim (e.g., a statistic not in the original)
  4 = multiple added claims, or one clearly wrong invented claim
  5 = substantial fabricated medical content (hallucination)

Return ONLY a single JSON object, no prose before or after:
{"accuracy_1_5": <int>, "completeness_1_5": <int>, "added_errors_1_5": <int>, \
"note": "<=25 words naming the single most important issue, or 'none'", \
"flagged_claims": ["specific invented or incorrect statements, if any; else empty list"]}

ORIGINAL:
<<<
{ORIGINAL}
>>>

REWRITE:
<<<
{REWRITE}
>>>
"""

_DIMS = ("accuracy_1_5", "completeness_1_5", "added_errors_1_5")


def build_judge_prompt(original: str, rewrite: str) -> str:
    return JUDGE_PROMPT.replace("{ORIGINAL}", original).replace("{REWRITE}", rewrite)


def parse_judgment(text: str) -> dict[str, Any] | None:
    """Tolerantly extract the JSON object from a judge response."""
    if not text:
        return None
    # Strip code fences if present.
    text = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.M).strip()
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        return None
    try:
        obj = json.loads(m.group(0))
    except json.JSONDecodeError:
        return None
    out: dict[str, Any] = {}
    for d in _DIMS:
        v = obj.get(d)
        try:
            iv = int(round(float(v)))
        except (TypeError, ValueError):
            return None
        if not 1 <= iv <= 5:
            return None
        out[d] = iv
    out["note"] = str(obj.get("note", ""))[:300]
    fc = obj.get("flagged_claims", [])
    out["flagged_claims"] = fc if isinstance(fc, list) else [str(fc)]
    return out


def score_one(
    judge,
    judge_id: str,
    page_id: str,
    model_id: str,
    original: str,
    rewrite: str,
    cache_dir: Path,
    force: bool = False,
    max_retries: int = 3,
) -> dict[str, Any]:
    """Score one rewrite with one judge. Cached to cache_dir/<page>__<model>__<judge>.json."""
    cache_path = cache_dir / f"{page_id}__{model_id}__{judge_id}.json"
    if cache_path.exists() and not force:
        return json.loads(cache_path.read_text())

    prompt = build_judge_prompt(original, rewrite)
    parsed = None
    raw_text = ""
    for _ in range(max_retries):
        out = judge.rewrite(prompt)  # reuses provider client; "rewrite" == send prompt, get text
        raw_text = out.get("text", "") or ""
        parsed = parse_judgment(raw_text)
        if parsed is not None:
            break
    if parsed is None:
        raise ValueError(f"judge {judge_id} returned unparseable output for {page_id}__{model_id}: {raw_text[:200]!r}")

    record = {
        "page_id": page_id,
        "model_id": model_id,
        "judge_id": judge_id,
        "judge_prompt_version": JUDGE_PROMPT_VERSION,
        "scored_at_utc": utc_now_iso(),
        **{d: parsed[d] for d in _DIMS},
        "note": parsed["note"],
        "flagged_claims": parsed["flagged_claims"],
    }
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(json.dumps(record, indent=2))
    return record


def build_judges(model_specs: list[dict]) -> dict[str, Any]:
    """One judge client per model spec (reuses the rewrite-arm provider wrappers)."""
    return {spec["id"]: build_rewriter(spec) for spec in model_specs}
