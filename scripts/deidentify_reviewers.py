#!/usr/bin/env python3
"""One-time de-identification of the Aim 3 reviewer score sheets.

Reviewers are human participants. Their names must never enter version control,
so every score sheet is keyed by an opaque participant ID instead:

  * `E01`-`E06`  blinded subspecialist reviewers
  * `L01`-`L05`  blinded lay reviewers

What this changes, per sheet:
  - filename    `..._<given>_<family>_expert.csv` -> `..._e06_expert.csv`
  - reviewer_name  free-text name -> the participant ID
  - reviewer_role  free-text job title -> `expert` / `layperson`

Job titles are removed as well as names: a specific job title identifies a person
about as effectively as their name in a study this small.

Ratings, blind IDs, dates and clinical notes are untouched. The notes were
checked and contain no participant names -- they are comments about the rewrites.

The name-to-ID crosswalk is written to `private/reviewer_crosswalk.csv`, which is
gitignored. That file is the ONLY place the mapping exists; keep it with your IRB
records and never commit it.

Idempotent: sheets already carrying an ID are left alone, so re-running is safe.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from src.config import REVIEW_DIR  # noqa: E402

SCORES_ROOT = REVIEW_DIR / "questionnaire_scores"
CROSSWALK = REPO_ROOT / "private" / "reviewer_crosswalk.csv"

# `<slug>` is whatever sits between the set id and the role suffix.
SHEET_RE = re.compile(
    r"^(aim3_scores_(?:neutral_)?set_[a-c])_(.+?)_(expert|layman|layperson)$", re.I
)
ID_RE = re.compile(r"^[el]\d{2}$", re.I)


def assign_ids(sheets: list[tuple[Path, str, str]]) -> dict[str, str]:
    """Map each reviewer slug to a stable participant ID.

    A reviewer keeps one ID across every sheet and cohort they contributed to, so
    the same person is never counted twice. IDs are assigned in alphabetical order
    of slug within each role, which makes the assignment deterministic and
    reproducible from the crosswalk.
    """
    by_role: dict[str, set[str]] = {"expert": set(), "layperson": set()}
    for _, slug, role in sheets:
        by_role["expert" if role.lower() == "expert" else "layperson"].add(slug)

    overlap = by_role["expert"] & by_role["layperson"]
    if overlap:
        raise SystemExit(
            f"reviewer(s) appear as both expert and layperson: {sorted(overlap)}. "
            "Resolve the role before de-identifying; an ID must mean one thing."
        )

    mapping: dict[str, str] = {}
    for role, prefix in (("expert", "E"), ("layperson", "L")):
        for i, slug in enumerate(sorted(by_role[role]), start=1):
            mapping[slug] = f"{prefix}{i:02d}"
    return mapping


def main() -> int:
    sheets: list[tuple[Path, str, str]] = []
    already = 0
    for f in sorted(SCORES_ROOT.rglob("aim3_scores_*.csv")):
        m = SHEET_RE.match(f.stem)
        if not m:
            print(f"  ! skipping unparseable filename: {f.name}")
            continue
        _, slug, role = m.groups()
        if ID_RE.match(slug):
            already += 1
            continue
        sheets.append((f, slug.lower(), role.lower()))

    if not sheets:
        print(f"nothing to do — {already} sheet(s) already de-identified.")
        return 0

    mapping = assign_ids(sheets)

    rows = []
    for path, slug, role in sheets:
        pid = mapping[slug]
        prefix = SHEET_RE.match(path.stem).group(1)
        new_path = path.with_name(f"{prefix}_{pid.lower()}_{role}.csv")

        d = pd.read_csv(path)
        original_names = sorted({str(x) for x in d.get("reviewer_name", pd.Series(dtype=str)).dropna()})
        original_roles = sorted({str(x).strip() for x in d.get("reviewer_role", pd.Series(dtype=str)).dropna()})
        if "reviewer_name" in d.columns:
            d["reviewer_name"] = pid
        if "reviewer_role" in d.columns:
            d["reviewer_role"] = "expert" if role == "expert" else "layperson"
        d.to_csv(new_path, index=False)
        path.unlink()

        rows.append({
            "participant_id": pid,
            "reviewer_slug": slug,
            "reviewer_names_in_sheets": " | ".join(original_names),
            "reviewer_roles_in_sheets": " | ".join(original_roles),
            "role": "expert" if role == "expert" else "layperson",
            "sheet": new_path.name,
        })
        print(f"  {path.name}  ->  {new_path.name}")

    CROSSWALK.parent.mkdir(parents=True, exist_ok=True)
    cw = pd.DataFrame(rows).sort_values(["participant_id", "sheet"])
    cw.to_csv(CROSSWALK, index=False)

    n_people = cw.participant_id.nunique()
    print(f"\nde-identified {len(rows)} sheet(s) covering {n_people} participants")
    print(f"crosswalk written to {CROSSWALK.relative_to(REPO_ROOT)} (gitignored — keep it private)")
    print("\nRe-run scripts/12 and 13 so the compiled reports pick up the new IDs.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
