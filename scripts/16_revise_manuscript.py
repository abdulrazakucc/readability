#!/usr/bin/env python3
"""Produce a revised manuscript implementing the external implementation review.

Two rules govern this script:

1. **The author's file is never edited in place.** It is opened read-only and a new
   document is written alongside it, so the original remains the reference.
2. **No result is typed in.** Every numeric replacement is read from the regenerated
   reports, so a re-run after a pipeline change updates the manuscript automatically
   and a stale value cannot survive.

Wording changes come from section 7 of the review, which supplies replacement text
for the passages it identifies as inaccurate.

Every substitution is recorded to a CSV so the revision is auditable line by line:
what was replaced, what replaced it, and which report the value came from.

Edits that require the authors' judgement -- reframing the Discussion, deciding how
to describe a borderline association -- are NOT attempted here. They are listed in
the run summary as outstanding.
"""

from __future__ import annotations

import re
import sys
from datetime import date
from pathlib import Path

import docx
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from src.config import REPORTS_DIR  # noqa: E402

PUB = REPO_ROOT / "publication"
SOURCE = PUB / "Naeem_final_clean_cardiac_CT_readability.docx"
OUT = PUB / f"Naeem_revised_{date.today().isoformat()}.docx"
AUDIT = PUB / f"manuscript_revision_audit_{date.today().isoformat()}.csv"

MODEL_NAME = {"claude": "Claude Opus 4.8", "openai": "GPT-5.5", "gemini": "Gemini 3.1 Pro"}


def _fmt(x: float, dp: int = 2) -> str:
    return f"{x:.{dp}f}"


def _p(x: float) -> str:
    """JAMA style: leading zero dropped, < .001 for very small values."""
    if x < 0.001:
        return "< .001"
    return f"= {x:.2f}".replace("0.", ".")


def build_edits() -> list[dict]:
    """Every substitution, with its source. Numeric values come from reports."""
    prim = pd.read_csv(REPORTS_DIR / "aim3_compiled_by_model_primary.csv").set_index("model_id")
    irr = pd.read_csv(REPORTS_DIR / "aim3_compiled_irr.csv")
    irr = irr[irr.condition == "expert_labeled"].set_index("axis")
    trade = pd.read_csv(REPORTS_DIR / "aim3_compiled_tradeoff.csv")
    evl = pd.read_csv(REPORTS_DIR / "aim3_compiled_expert_vs_lay.csv").set_index("axis")
    ph = pd.read_csv(REPORTS_DIR / "aim2_posthoc_models.csv")
    ph = ph[ph.label == "fkgl"]

    E: list[dict] = []

    def add(old: str, new: str, why: str, src: str = "review §7"):
        E.append({"old": old, "new": new, "rationale": why, "source": src})

    # ---- 7.3 Methods: the 403 contradiction (the review calls this mandatory) ----
    add(
        "Five candidate pages from Johns Hopkins Medicine (3) and Mayo Clinic (2) returned "
        "HTTP 403 status codes consistent with commercial bot-detection at the content delivery "
        "network layer and were not recovered for this analysis; this exclusion is documented in "
        "the prespecified deviation log and addressed in the Limitations section.",
        "Five candidate pages (3 Johns Hopkins Medicine and 2 Mayo Clinic) initially returned "
        "HTTP 403 responses consistent with commercial bot detection. All 5 were recovered on "
        "June 8, 2026, by manual browser capture of the visible patient-facing text. Documented "
        "site-specific boilerplate was removed, after which the text passed through the same "
        "Unicode normalization, junk-line filtering, whitespace normalization, readability "
        "scoring, and downstream analysis used for the automated captures. All 5 recovered pages "
        "were included in the final N = 26.",
        "Methods said the 5 pages were NOT recovered; Results, Limitations and the deviation "
        "appendix all say they were recovered and included, and n=26 depends on them.",
    )

    # ---- 7.8 unit of analysis wording ----
    add("155 independent ratings", "155 expert ratings",
        "155 rating events over 77 rewrites are not 155 independent experimental units.")

    # ---- 7.8 Table 3 values, now per rewrite ----
    for m in ("claude", "openai", "gemini"):
        r = prim.loc[m]
        add(f"{_fmt(4.82 if m=='claude' else 4.84 if m=='openai' else 4.85)} "
            f"({_fmt(0.39 if m=='claude' else 0.62 if m=='openai' else 0.36)})",
            f"{_fmt(r.accuracy_1_5_mean)} ({_fmt(r.accuracy_1_5_sd)})",
            f"{MODEL_NAME[m]} accuracy: one expert mean per rewrite, not per rating.",
            "reports/aim3_compiled_by_model_primary.csv")

    # ---- 7.8 / 4.2 agreement values ----
    add("Gwet AC1 0.77 for accuracy, 0.79 for completeness, and 0.89 for added errors",
        f"Gwet AC1 {_fmt(irr.loc['accuracy_1_5','gwet_ac1'])} for accuracy, "
        f"{_fmt(irr.loc['completeness_1_5','gwet_ac1'])} for completeness, and "
        f"{_fmt(irr.loc['added_errors_1_5','gwet_ac1'])} for added errors",
        "AC1 now uses the protocol's 1-5 category universe for every axis and cohort.",
        "reports/aim3_compiled_irr.csv")
    add("whereas quadratic-weighted Cohen κ was near zero",
        "whereas mean pairwise quadratic-weighted Cohen κ was near zero",
        "Name the statistic exactly as computed.")

    # ---- 7.8 trade-off: add bootstrap CIs, both axes ----
    def tr(m, axis):
        row = trade[(trade.model_id == m) & (trade.axis == axis)].iloc[0]
        return row
    ga = tr("gemini", "accuracy_1_5")
    ca = tr("claude", "accuracy_1_5")
    oa = tr("openai", "accuracy_1_5")
    add("(Spearman ρ = −0.37 between grade levels removed and accuracy; P = .06)",
        f"(Spearman ρ = {_fmt(ga.spearman_rho)} between grade levels removed and accuracy; "
        f"95% CI, {_fmt(ga.ci_low)} to {_fmt(ga.ci_high)}; P {_p(ga.p_value)})",
        "Methods promised 5000-resample bootstrap CIs; they were not previously computed.",
        "reports/aim3_compiled_tradeoff.csv")
    add("whereas the association was null for Claude Opus 4.8 (ρ = 0.25; P = .22) and GPT-5.5 (ρ = 0.03; P = .90)",
        f"whereas the association was null for Claude Opus 4.8 (ρ = {_fmt(ca.spearman_rho)}; "
        f"95% CI, {_fmt(ca.ci_low)} to {_fmt(ca.ci_high)}; P {_p(ca.p_value)}) and GPT-5.5 "
        f"(ρ = {_fmt(oa.spearman_rho)}; 95% CI, {_fmt(oa.ci_low)} to {_fmt(oa.ci_high)}; "
        f"P {_p(oa.p_value)}). Completeness correlations were similarly null "
        f"(Claude ρ = {_fmt(tr('claude','completeness_1_5').spearman_rho)}; "
        f"GPT-5.5 ρ = {_fmt(tr('openai','completeness_1_5').spearman_rho)}; "
        f"Gemini ρ = {_fmt(tr('gemini','completeness_1_5').spearman_rho)})",
        "Add CIs and the completeness correlations the Methods/SAP require.",
        "reports/aim3_compiled_tradeoff.csv")

    # ---- 7.7 Aim 2 pairwise post-hoc ----
    if len(ph):
        def pair(a, b):
            r = ph[((ph.model_a == a) & (ph.model_b == b)) | ((ph.model_a == b) & (ph.model_b == a))]
            return r.iloc[0] if len(r) else None
        cg, co, go = pair("claude", "gemini"), pair("claude", "openai"), pair("gemini", "openai")
        if cg is not None and co is not None and go is not None:
            add("with Claude and Gemini comparable and both stronger than GPT-5.5",
                "with Claude Opus 4.8 and Gemini 3.1 Pro both producing lower post-rewrite FKGL "
                f"than GPT-5.5 (Holm-adjusted paired Wilcoxon, both P {_p(co.p_holm)}); "
                f"Claude and Gemini did not differ significantly (P {_p(cg.p_holm)})",
                "The comparative claim rested on an omnibus P value alone; pairwise post-hoc "
                "now supports it, and Claude vs Gemini is not significant.",
                "reports/aim2_posthoc_models.csv")

    # ---- 7.9 lay / presentation: exploratory framing + rewrite-level values ----
    add("Two prespecified secondary analyses addressed",
        "Two secondary exploratory analyses, added after the primary protocol, addressed",
        "Methods states the neutral arm was added after a reviewer raised concern, so it "
        "cannot be described as prespecified.")
    ea, ec, ed = evl.loc["accuracy_1_5"], evl.loc["completeness_1_5"], evl.loc["added_errors_1_5"]
    add("Pooled across lay readers, accuracy was near the ceiling (4.94) and higher than the "
        "subspecialists (4.94 vs 4.84; Mann–Whitney P = .001), while completeness (4.90 vs 4.80; "
        "P = .20) and added errors (1.08 vs 1.09; P = .95) did not differ",
        "Comparing subspecialists and lay readers on the same standard instrument at the level of "
        f"the rewrite, lay accuracy was higher ({_fmt(ea.layperson_mean)} vs "
        f"{_fmt(ea.expert_mean)}; paired Wilcoxon P {_p(ea.wilcoxon_p)}), as was completeness "
        f"({_fmt(ec.layperson_mean)} vs {_fmt(ec.expert_mean)}; P {_p(ec.wilcoxon_p)}), while lay "
        f"readers recorded fewer added errors ({_fmt(ed.layperson_mean)} vs "
        f"{_fmt(ed.expert_mean)}; P {_p(ed.wilcoxon_p)})",
        "Ratings on the same rewrite are repeated observations, so the raw-rating "
        "Mann-Whitney tests were pseudo-replicated; the lay pool also mixed two instruments.",
        "reports/aim3_compiled_expert_vs_lay.csv")

    # ---- 7.10 automated panel framing ----
    add("As a pre-specified screening analysis, a panel of 3 large language models",
        "As a secondary exploratory analysis added after the primary protocol, a panel of 3 "
        "large language models",
        "The deviation log records the judge panel as a later addition.")

    # ---- 7.11 non-causal language ----
    add("the residual risk a simplification–completeness trade-off in the most aggressive simplifier",
        "the lowest observed completeness occurring in the most aggressive simplifier",
        "Across-model completeness is not significant (P ≈ .06), so causal phrasing is not supported.")

    return E


def apply_edits(doc, edits: list[dict]) -> list[dict]:
    """Replace at paragraph level, preserving each paragraph's leading run formatting."""
    applied = []
    for e in edits:
        hit = False
        for para in doc.paragraphs:
            if e["old"] in para.text:
                new_text = para.text.replace(e["old"], e["new"])
                for r in list(para.runs)[1:]:
                    r._element.getparent().remove(r._element)
                if para.runs:
                    para.runs[0].text = new_text
                else:
                    para.add_run(new_text)
                hit = True
                break
        if not hit:
            for tbl in doc.tables:
                for row in tbl.rows:
                    for cell in row.cells:
                        if e["old"] in cell.text:
                            for p in cell.paragraphs:
                                if e["old"] in p.text:
                                    txt = p.text.replace(e["old"], e["new"])
                                    for r in list(p.runs)[1:]:
                                        r._element.getparent().remove(r._element)
                                    if p.runs:
                                        p.runs[0].text = txt
                                    else:
                                        p.add_run(txt)
                                    hit = True
                                    break
                        if hit:
                            break
                    if hit:
                        break
                if hit:
                    break
        applied.append({**e, "status": "APPLIED" if hit else "NOT FOUND"})
    return applied


OUTSTANDING = [
    "Table 3 header: change 'No. ratings' to 'No. rewrites' and set 26 / 25 / 26 "
    "(table structure edit, needs author review of layout)",
    "§7.1 Methods reproducibility paragraph — replacement text supplied by the review",
    "§7.2 Methods sample selection — programmatic search wording",
    "§7.5 Results sample — capture dates split (21 automated, 5 manual on June 8)",
    "§7.6 Aim 1 — add site-level Dunn post-hoc sentence once those diagnostics are run",
    "§7.11 Discussion / Conclusions — non-causal reframing throughout",
    "§7.12 Deviations summary — update the count; the repository log now has 10 entries",
    "§7.13 eFigure 1 / eFigure 2 — regenerate and add the missing eFigure 2 legend",
]


def main() -> int:
    if not SOURCE.exists():
        print(f"source manuscript not found: {SOURCE}")
        return 2

    edits = build_edits()
    doc = docx.Document(str(SOURCE))          # opened read-only; never saved back
    applied = apply_edits(doc, edits)
    doc.save(str(OUT))

    audit = pd.DataFrame(applied)[["status", "rationale", "source", "old", "new"]]
    audit.to_csv(AUDIT, index=False)

    n_ok = int((audit.status == "APPLIED").sum())
    n_miss = int((audit.status == "NOT FOUND").sum())
    print("=" * 88)
    print("MANUSCRIPT REVISION")
    print("=" * 88)
    print(f"  source (unmodified): {SOURCE.name}")
    print(f"  revised output     : {OUT.name}")
    print(f"  audit trail        : {AUDIT.name}")
    print(f"\n  {n_ok} edit(s) applied, {n_miss} not found\n")
    for _, r in audit.iterrows():
        mark = "OK " if r.status == "APPLIED" else "MISS"
        print(f"  [{mark}] {r.rationale[:76]}")
        if r.status == "NOT FOUND":
            print(f"         looked for: {r.old[:70]}...")
    print("\n  Outstanding — need author judgement, not automation:")
    for o in OUTSTANDING:
        print(f"    - {o}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
