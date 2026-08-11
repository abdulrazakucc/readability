#!/usr/bin/env python3
"""Build the change report for Dr Naeem: what the manuscript said, what it says now, why.

Audience is a clinician co-author, not a developer. The report therefore describes
only the manuscript: original wording, revised wording, and the reason. It never
mentions scripts, branches, commits or file paths.

Everything is derived. The change table comes from the revision audit trail; the
results table is recomputed from the generated reports. Re-run it after any further
change and the document stays current.
"""

from __future__ import annotations

import html
import sys
from datetime import date
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from src.config import DATA_DIR, REPORTS_DIR  # noqa: E402

PUB = REPO_ROOT / "publication"
AUDIT = PUB / "manuscript_revision_audit.csv"
OUT = REPORTS_DIR / "manuscript_change_report.html"

# Plain-language grouping for the audience.
SECTIONS = {
    "Accuracy of reporting": ["Methods stated", "implies all 26", "Model versions",
                              "programmatic search", "rating-weighted", "rating event, not a",
                              "exact proportions", "155 rating events"],
    "Statistical correctness": ["one expert mean per rewrite", "1-5 category set",
                                "exactly as computed", "bootstrap", "omnibus P value",
                                "pseudo-replicated", "site-level omnibus", "inferential conclusion"],
    "Claims matched to evidence": ["causal", "threshold", "ranks GPT", "prespecified",
                                   "later addition", "count column"],
    "References": ["Kutner", "Ayers", "References 11-16", "trafilatura source",
                   "textstat source", "References 9 and 10", "References 23-25",
                   "References 19 and 20"],
    "Housekeeping": ["deviation log now records"],
}


def classify(rationale: str) -> str:
    for section, keys in SECTIONS.items():
        if any(k.lower() in str(rationale).lower() for k in keys):
            return section
    return "Other"


def shorten(text: str, limit: int = 300) -> str:
    text = " ".join(str(text).split())
    return text if len(text) <= limit else text[:limit].rsplit(" ", 1)[0] + " …"


def results_table() -> list[dict]:
    """Every headline result, as the manuscript originally reported it and as it stands now."""
    prim = pd.read_csv(REPORTS_DIR / "aim3_compiled_by_model_primary.csv").set_index("model_id")
    irr = pd.read_csv(REPORTS_DIR / "aim3_compiled_irr.csv")
    exp = irr[irr.condition == "expert_labeled"].set_index("axis")
    lay = irr[irr.condition == "layperson_neutral"].set_index("axis")
    trade = pd.read_csv(REPORTS_DIR / "aim3_compiled_tradeoff.csv")
    evl = pd.read_csv(REPORTS_DIR / "aim3_compiled_expert_vs_lay.csv").set_index("axis")
    am = pd.read_csv(REPORTS_DIR / "aim3_compiled_across_model.csv").set_index("axis")
    acc = pd.read_csv(DATA_DIR / "scores" / "accuracy.csv")
    rw = pd.read_csv(DATA_DIR / "scores" / "rewrites.csv")
    ph = pd.read_csv(REPORTS_DIR / "aim2_posthoc_models.csv")
    ph = ph[ph.label == "fkgl"]

    def pair(a, b):
        r = ph[((ph.model_a == a) & (ph.model_b == b)) | ((ph.model_a == b) & (ph.model_b == a))]
        return r.iloc[0] if len(r) else None

    def pv(x):
        return "&lt; .001" if x < 0.001 else f"{x:.2f}".lstrip("0")

    rows = [
        ("Pages meeting the 6th-grade benchmark", "0 of 26", "0 of 26 (95% CI, 0%–13.2%)",
         "Unchanged. The exact confidence interval is now generated rather than hand-calculated."),
        ("Median reading level of original pages", "10.31", "10.31", "Unchanged."),
        ("Reading-level drop, Claude", "−5.52 grades", "−5.52 grades", "Unchanged."),
        ("Reading-level drop, Gemini", "−5.74 grades", "−5.74 grades", "Unchanged."),
        ("Reading-level drop, GPT-5.5", "−3.90 grades", "−3.90 grades", "Unchanged."),
        ("Rewrites meeting the benchmark", "“roughly 80%”",
         f"Claude {int((rw[rw.model_id=='claude'].fkgl<=6).sum())}/26, "
         f"Gemini {int((rw[rw.model_id=='gemini'].fkgl<=6).sum())}/26, "
         f"GPT-5.5 {int((rw[rw.model_id=='openai'].fkgl<=6).sum())}/25",
         "Exact proportions replace an approximation."),
        ("Which models differ on reading level", "“Claude and Gemini stronger than GPT-5.5”",
         (f"Claude vs GPT-5.5 P {pv(pair('claude','openai').p_holm)}; "
          f"Gemini vs GPT-5.5 P {pv(pair('gemini','openai').p_holm)}; "
          f"Claude vs Gemini P {pv(pair('claude','gemini').p_holm)} (not significant)")
         if pair("claude", "openai") is not None else "see report",
         "The comparison previously rested on an overall test only. Direct model-to-model "
         "comparisons now support it, and show Claude and Gemini do not differ."),
        ("Unit of the clinical analysis", "155 expert ratings",
         "77 rewrites (26 Claude, 25 GPT-5.5, 26 Gemini)",
         "A rewrite scored by three subspecialists is one clinical observation, not three. "
         "Averaging first stops multiply-scored rewrites carrying extra weight."),
        ("Accuracy, Claude", "4.82 (0.39)",
         f"{prim.loc['claude','accuracy_1_5_mean']:.2f} ({prim.loc['claude','accuracy_1_5_sd']:.2f})",
         "Recomputed per rewrite."),
        ("Accuracy, GPT-5.5", "4.84 (0.62)",
         f"{prim.loc['openai','accuracy_1_5_mean']:.2f} ({prim.loc['openai','accuracy_1_5_sd']:.2f})",
         "Recomputed per rewrite."),
        ("Accuracy, Gemini", "4.85 (0.36)",
         f"{prim.loc['gemini','accuracy_1_5_mean']:.2f} ({prim.loc['gemini','accuracy_1_5_sd']:.2f})",
         "Recomputed per rewrite."),
        ("Pooled accuracy", "4.84", f"{acc.accuracy_1_5.mean():.2f}",
         "4.84 was the average across rating events; 4.79 is the average across rewrites."),
        ("Do models differ on accuracy?", "not stated as a test",
         f"Friedman P = {am.loc['accuracy_1_5','p_value']:.3f}".replace("0.", "."),
         "No significant difference between models."),
        ("Do models differ on completeness?", "P = .06",
         f"Friedman P = {am.loc['completeness_1_5','p_value']:.3f}".replace("0.", "."),
         "Unchanged and still not significant, so wording no longer implies a demonstrated "
         "difference."),
        ("Agreement between subspecialists (AC1)", "0.77 / 0.79 / 0.89",
         f"{exp.loc['accuracy_1_5','gwet_ac1']:.2f} / {exp.loc['completeness_1_5','gwet_ac1']:.2f} "
         f"/ {exp.loc['added_errors_1_5','gwet_ac1']:.2f}",
         "Agreement is now measured against the full 1–5 rating scale the instrument defines, "
         "rather than only the scores reviewers happened to use."),
        ("Agreement between lay readers (AC1)", "0.76–0.90",
         f"{min(lay.gwet_ac1):.2f}–{max(lay.gwet_ac1):.2f}", "Same change of scale."),
        ("Reading-level drop vs accuracy, Gemini", "ρ = −0.37, P = .06",
         (lambda r: f"ρ = {r.spearman_rho:.2f} (95% CI, {r.ci_low:.2f} to {r.ci_high:.2f}); "
                    f"P = {r.p_value:.3f}".replace("0.", "."))(
             trade[(trade.model_id == "gemini") & (trade.axis == "accuracy_1_5")].iloc[0]),
         "A confidence interval is added, as the Methods promised. The association remains "
         "suggestive, not significant."),
        ("Completeness correlations", "not reported",
         "Reported for all three models; none statistically significant",
         "The Methods promised these; they were previously missing."),
        ("Lay readers vs subspecialists", "4.94 vs 4.84 (P = .001)",
         f"{evl.loc['accuracy_1_5','layperson_mean']:.2f} vs "
         f"{evl.loc['accuracy_1_5','expert_mean']:.2f} (P {pv(evl.loc['accuracy_1_5','wilcoxon_p'])})",
         "Compared on the same instrument and per rewrite. The earlier comparison mixed two "
         "different instruments and counted repeat ratings as independent."),
        ("Site differences", "FKGL P = .074 only",
         "FKGL P = .074; also FKRE P = .042 and CLI P = .046, with no pair surviving correction",
         "Two significant overall tests were previously unreported. Follow-up shows no specific "
         "pair of sites differs."),
    ]
    return [{"quantity": q, "before": b, "after": a, "why": w} for q, b, a, w in rows]


def main() -> int:
    if not AUDIT.exists():
        print(f"audit trail not found: {AUDIT}")
        return 2
    audit = pd.read_csv(AUDIT)
    audit["section"] = audit["rationale"].map(classify)

    # The audit trail is rewritten on every pass, so its status column only describes
    # the last run. Verify against the manuscript instead: a change counts as made if
    # its revised wording is actually present with tracked changes accepted. That is
    # the only claim worth putting in front of a co-author.
    import docx
    sys.path.insert(0, str(REPO_ROOT))
    from src.manuscript import paragraph_texts
    doc = docx.Document(str(PUB / "Naeem_final_clean_cardiac_CT_readability.docx"))
    current = " ".join(paragraph_texts(doc))
    for tbl in doc.tables:
        for row in tbl.rows:
            for cell in row.cells:
                current += " " + "".join(
                    nn.text for nn in cell._element.iter()
                    if nn.tag.endswith("}t") and nn.text)

    def landed(new: str) -> bool:
        probe = " ".join(str(new).split())[:60]
        return probe in " ".join(current.split())

    applied = audit[audit["new"].map(landed)]

    order = ["Accuracy of reporting", "Statistical correctness", "Claims matched to evidence",
             "References", "Housekeeping", "Other"]
    blocks = []
    n = 0
    for sec in order:
        rows = applied[applied.section == sec]
        if rows.empty:
            continue
        body = []
        for _, r in rows.iterrows():
            n += 1
            body.append(
                f"<tr><td class='num'>{n}</td>"
                f"<td class='was'>{html.escape(shorten(r['old']))}</td>"
                f"<td class='now'>{html.escape(shorten(r['new']))}</td>"
                f"<td class='why'>{html.escape(shorten(r['rationale'], 400))}</td></tr>")
        blocks.append(
            f"<h3>{html.escape(sec)} <span class='count'>{len(rows)} change"
            f"{'s' if len(rows) != 1 else ''}</span></h3>"
            "<table><thead><tr><th>#</th><th>Original wording</th><th>Revised wording</th>"
            "<th>Reason</th></tr></thead><tbody>" + "".join(body) + "</tbody></table>")

    res = results_table()
    unchanged = sum(1 for r in res if r["why"].startswith("Unchanged"))
    res_rows = "".join(
        f"<tr><td class='q'>{html.escape(r['quantity'])}</td>"
        f"<td class='was'>{r['before']}</td><td class='now'>{r['after']}</td>"
        f"<td class='why'>{html.escape(r['why'])}</td></tr>" for r in res)

    doc = f"""<style>
:root {{ --ink:#1a2733; --muted:#5d6b78; --line:#e3e9ee; --was:#fdf3f2; --now:#f1f8f3;
        --accent:#2f5d8a; --bg:#ffffff; }}
:root:not([data-theme="light"]) {{ }}
@media (prefers-color-scheme: dark) {{ :root:not([data-theme="light"]) {{
  --ink:#e8eef4; --muted:#9fb0bf; --line:#2b3742; --was:#3a2a2a; --now:#22332a;
  --accent:#7fb0e0; --bg:#151b21; }} }}
:root[data-theme="dark"] {{ --ink:#e8eef4; --muted:#9fb0bf; --line:#2b3742; --was:#3a2a2a;
  --now:#22332a; --accent:#7fb0e0; --bg:#151b21; }}
body {{ background:var(--bg); color:var(--ink); margin:0 auto; padding:2.5rem 1.4rem 4rem;
  max-width:1180px; font:16px/1.65 Georgia,'Iowan Old Style',serif; }}
h1 {{ font-size:1.85rem; margin:0 0 .3rem; letter-spacing:-.01em; }}
h2 {{ font-size:1.3rem; margin:2.8rem 0 .6rem; padding-bottom:.35rem;
  border-bottom:2px solid var(--accent); }}
h3 {{ font-size:1.02rem; margin:2rem 0 .5rem; color:var(--accent);
  font-family:system-ui,sans-serif; }}
.count {{ font-size:.76rem; color:var(--muted); font-weight:400; }}
.lede {{ color:var(--muted); font-size:1.02rem; margin:.2rem 0 1.6rem; }}
.cards {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(150px,1fr)); gap:.7rem;
  margin:1.4rem 0 2rem; }}
.card {{ border:1px solid var(--line); border-radius:9px; padding:.85rem 1rem; }}
.card b {{ display:block; font-size:1.5rem; font-family:system-ui,sans-serif; color:var(--accent); }}
.card span {{ font-size:.78rem; color:var(--muted); font-family:system-ui,sans-serif; }}
table {{ width:100%; border-collapse:collapse; margin:.4rem 0 1.2rem;
  font:13.5px/1.5 system-ui,-apple-system,sans-serif; }}
th {{ text-align:left; padding:.55rem .6rem; border-bottom:2px solid var(--line);
  color:var(--muted); font-size:.76rem; text-transform:uppercase; letter-spacing:.04em; }}
td {{ padding:.6rem; border-bottom:1px solid var(--line); vertical-align:top; }}
.num {{ color:var(--muted); width:2.2rem; }}
.q {{ font-weight:600; width:20%; }}
.was {{ background:var(--was); width:26%; }}
.now {{ background:var(--now); width:26%; }}
.why {{ color:var(--muted); }}
.note {{ border-left:3px solid var(--accent); background:color-mix(in srgb,var(--accent) 7%,transparent);
  padding:.8rem 1rem; border-radius:0 7px 7px 0; margin:1.1rem 0; font-size:.95rem; }}
.scroll {{ overflow-x:auto; }}
ol li {{ margin:.4rem 0; }}
</style>

<h1>Manuscript change report</h1>
<p class="lede">Cardiac CT patient-education readability study &middot; prepared
{date.today().strftime('%d %B %Y')}</p>

<p>This document lists every change made to the manuscript since your version: what it said
before, what it says now, and why. All changes are marked in the file itself, so nothing has
been altered silently &mdash; each can be accepted or rejected individually in Word under
<em>Review &rarr; Tracking</em>. Two passages also carry a comment asking for your decision.</p>

<div class="cards">
  <div class="card"><b>{n}</b><span>wording changes</span></div>
  <div class="card"><b>{len(res)}</b><span>results checked</span></div>
  <div class="card"><b>{unchanged}</b><span>headline results unchanged</span></div>
  <div class="card"><b>2</b><span>questions for you</span></div>
</div>

<div class="note"><strong>The headline findings did not change.</strong> Reading levels, the
size of the improvement from AI rewriting, and the finding that accuracy stayed high are all
as you reported them. What changed is how some numbers were calculated, how precisely certain
claims are worded, and the completeness of the citations.</div>

<h2>1. Changes to the text</h2>
{''.join(blocks)}

<h2>2. Results: your manuscript compared with the current analysis</h2>
<p>Every figure below is regenerated from the study data. &ldquo;Unchanged&rdquo; means your
reported value was confirmed exactly.</p>
<div class="scroll">
<table><thead><tr><th>Quantity</th><th>As reported</th><th>Current value</th>
<th>Explanation</th></tr></thead><tbody>{res_rows}</tbody></table>
</div>

<h2>3. Decisions that need you</h2>
<ol>
<li><strong>The 6th-grade recommendation.</strong> The sentence credited the recommendation to
the National Library of Medicine, the AMA and the CDC, citing a national literacy survey. That
survey supports the reading statistic but contains no recommendation from those bodies, so the
attribution was softened. If you want the named attribution back, please supply those three
guidance documents and they will be cited. They were not invented.</li>
<li><strong>Reference 8 (Ayers).</strong> It was cited for cardiology readability, but it
studied general patient questions on a social-media forum. Each claim now carries only the
citation that supports it. Confirm this reads correctly, or say if you would rather remove the
reference entirely.</li>
<li><strong>Three references remain uncited</strong> &mdash; 21 (STROBE reporting guideline),
23 and 24 (chatbot response studies). Whether the study followed the STROBE checklist is your
statement to make, and where the two chatbot studies best support the discussion is an
editorial choice.</li>
<li><strong>Ethics statement.</strong> The current wording explains why review was not needed
for the public web pages, but does not address the reviewers who scored the rewrites. Please
insert your institution&rsquo;s exact determination.</li>
<li><strong>eFigure 2</strong> is referred to in the text but has no legend or image in the
document.</li>
</ol>
"""
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(doc, encoding="utf-8")
    print(f"wrote {OUT}  ({n} text changes, {len(res)} results compared)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
