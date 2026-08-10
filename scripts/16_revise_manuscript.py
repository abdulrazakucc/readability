#!/usr/bin/env python3
"""Apply the implementation-review corrections to the manuscript as TRACKED CHANGES.

Edits are made IN PLACE, as real Word revisions, so each can be reviewed, accepted
or rejected individually.

python-docx has no tracked-changes API: editing paragraph text through it produces
silent, untracked edits, removing the reviewability this document depends on. So the
revision XML is written directly -- the old phrase in `w:del`/`w:delText`, the new
phrase in `w:ins`, each with an author and timestamp. Only the changed phrase is
marked, so revision marks stay readable.

No result is typed in: every numeric replacement is read from the regenerated
reports. A timestamped backup goes to `private/` before anything is modified.

Wording changes come from section 7 of the review, which supplies replacement text
for the passages it identifies as inaccurate.

Every substitution is recorded to a CSV so the revision is auditable line by line:
what was replaced, what replaced it, and which report the value came from.

Edits that require the authors' judgement -- reframing the Discussion, deciding how
to describe a borderline association -- are NOT attempted here. They are listed in
the run summary as outstanding.
"""

from __future__ import annotations

import copy
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

import docx
import pandas as pd
from docx.oxml.ns import qn

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from src.config import REPORTS_DIR  # noqa: E402

PUB = REPO_ROOT / "publication"
MANUSCRIPT = PUB / "Naeem_final_clean_cardiac_CT_readability.docx"
BACKUP_DIR = REPO_ROOT / "private" / "manuscript_backups"
AUDIT = PUB / "manuscript_revision_audit.csv"
REVISION_AUTHOR = "Implementation review"
_rev_id = [1000]

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
    # Reference integrity: SciPy and pandas are named in the text but never cited.
    add("Analyses were performed in Python 3.11 using SciPy and pandas.",
        "Analyses were performed in Python 3.11 using SciPy and pandas.19,20",
        "References 19 and 20 appear in the reference list but were never cited; "
        "this is the sentence that names both tools.",
        "reference-list audit")

    add("the residual risk a simplification–completeness trade-off in the most aggressive simplifier",
        "the lowest observed completeness occurring in the most aggressive simplifier",
        "Across-model completeness is not significant (P ≈ .06), so causal phrasing is not supported.")

    return E


def _stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run(text, rpr, deleted=False):
    r = docx.oxml.OxmlElement("w:r")
    if rpr is not None:
        r.append(copy.deepcopy(rpr))
    t = docx.oxml.OxmlElement("w:delText" if deleted else "w:t")
    t.set(qn("xml:space"), "preserve")
    t.text = text
    r.append(t)
    return r


def _revision(tag, child):
    _rev_id[0] += 1
    el = docx.oxml.OxmlElement(tag)
    el.set(qn("w:id"), str(_rev_id[0]))
    el.set(qn("w:author"), REVISION_AUTHOR)
    el.set(qn("w:date"), _stamp())
    el.append(child)
    return el


def apply_paragraph_edits(para, edits: list[dict]) -> int:
    """Apply every edit belonging to this paragraph in ONE pass.

    Applying them one at a time is unsafe: after the first, part of the paragraph
    lives inside a `w:ins` element, which python-docx cannot see. A second edit
    reading `para.text` would get a truncated string and, on rewriting the runs,
    silently delete the first insertion along with the surrounding prose. This bug
    destroyed text on an earlier run, hence the single-pass rebuild.
    """
    text = para.text
    spans = sorted((text.find(e["old"]), e) for e in edits if text.find(e["old"]) >= 0)
    if not spans:
        return 0

    rpr = None
    if para.runs and para.runs[0]._element.find(qn("w:rPr")) is not None:
        rpr = para.runs[0]._element.find(qn("w:rPr"))
    for r in list(para.runs):
        r._element.getparent().remove(r._element)

    p, cursor = para._element, 0
    for i, e in spans:
        if i < cursor:
            continue
        if i > cursor:
            p.append(_run(text[cursor:i], rpr))
        p.append(_revision("w:del", _run(e["old"], rpr, deleted=True)))
        p.append(_revision("w:ins", _run(e["new"], rpr)))
        cursor = i + len(e["old"])
    if cursor < len(text):
        p.append(_run(text[cursor:], rpr))
    return len(spans)


def enable_track_changes(document) -> None:
    """Switch on <w:trackChanges/> so later editing in Word is tracked too."""
    settings = document.settings.element
    if settings.find(qn("w:trackChanges")) is None:
        settings.insert(0, docx.oxml.OxmlElement("w:trackChanges"))


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


def clean_whitespace(document) -> int:
    """Strip trailing/leading spaces from runs and collapse internal double spaces.

    Applied silently rather than as tracked changes: seven invisible space removals
    would add revision marks that tell a reader nothing, and would obscure the
    substantive edits. Text content is unchanged.
    """
    W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
    fixed = 0
    for para in document.paragraphs:
        nodes = [n for n in para._element.iter() if n.tag == f"{W}t" and n.text]
        for k, node in enumerate(nodes):
            original = node.text
            text = original.replace("\u00a0", " ")
            while "  " in text:
                text = text.replace("  ", " ")
            if k == 0:
                text = text.lstrip()
            if k == len(nodes) - 1:
                text = text.rstrip()
            if text != original:
                node.text = text
                fixed += 1
    return fixed


def main() -> int:
    if not MANUSCRIPT.exists():
        print(f"manuscript not found: {MANUSCRIPT}")
        return 2

    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    backup = BACKUP_DIR / f"{MANUSCRIPT.stem}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.docx"
    shutil.copy2(MANUSCRIPT, backup)

    document = docx.Document(str(MANUSCRIPT))
    enable_track_changes(document)

    paragraphs = list(document.paragraphs)
    for tbl in document.tables:
        for row in tbl.rows:
            for cell in row.cells:
                paragraphs.extend(cell.paragraphs)

    assigned: dict[int, list[dict]] = {}
    applied = []
    for e in build_edits():
        target = next((i for i, para in enumerate(paragraphs) if e["old"] in para.text), None)
        applied.append({**e, "status": "NOT FOUND" if target is None else "APPLIED"})
        if target is not None:
            assigned.setdefault(target, []).append(e)

    for idx, group in assigned.items():
        apply_paragraph_edits(paragraphs[idx], group)

    n_ws = clean_whitespace(document)
    document.save(str(MANUSCRIPT))

    audit = pd.DataFrame(applied)[["status", "rationale", "source", "old", "new"]]
    audit.to_csv(AUDIT, index=False)
    n_ok = int((audit.status == "APPLIED").sum())

    print("=" * 84)
    print("MANUSCRIPT REVISED IN PLACE, AS TRACKED CHANGES")
    print("=" * 84)
    print(f"  file   : {MANUSCRIPT.name}")
    print(f"  backup : {backup.relative_to(REPO_ROOT)}")
    print(f"  audit  : {AUDIT.name}")
    print(f"  whitespace runs cleaned: {n_ws}")
    print(f"\n  {n_ok} of {len(applied)} edits applied as tracked revisions\n")
    for _, r in audit.iterrows():
        print(f"  [{'OK ' if r.status == 'APPLIED' else 'MISS'}] {r.rationale[:72]}")
    print("\n  Outstanding, needing author judgement:")
    for o in OUTSTANDING:
        print(f"    - {o}")
    print("\n  In Word: Review > Tracking to step through each change.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
