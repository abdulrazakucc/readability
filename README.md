# Cardiac CT Patient-Education Readability Study

**Reproduction package.** Reading-level analysis of online patient-education materials for three
pre-procedure cardiac CT use cases — TAVR planning, coronary CT angiography, and LAAO/Watchman
planning — with a rewrite arm comparing three frontier large language models on readability **and**
blinded clinical accuracy.

Everything needed to regenerate every published number and figure is in this branch. Nothing else is.

---

## At a glance

| | |
|---|---|
| **Sample** | 26 patient-education pages · 10 prespecified US/UK sites · 3 procedures |
| **Aim 1** | Baseline reading level, six formulas |
| **Aim 2** | Reading-level change after LLM rewriting (77 rewrites, 3 models) |
| **Aim 3** | Clinical accuracy — blinded subspecialist review (primary) + automated LLM-judge panel (secondary) |
| **Reproducibility** | Three consecutive full runs produce byte-identical output |
| **Figures** | 11, all 600 dpi |
| **Participants** | De-identified: `E01`–`E06` subspecialists, `L01`–`L05` lay readers |

---

## Quick start

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements-lock.txt   # exact pins — use this to reproduce
.venv/bin/pytest                                  # sanity check
```

Then regenerate every result. **No API keys and no network needed** — the LLM-judge panel replays
from its committed cache:

```bash
.venv/bin/python scripts/03_score_originals.py --included-only
.venv/bin/python scripts/05_score_rewrites.py
.venv/bin/python scripts/06_build_review_packet.py
.venv/bin/python scripts/07_run_statistics.py
.venv/bin/python scripts/08_generate_figures.py
.venv/bin/python scripts/09_llm_accuracy.py --aggregate
.venv/bin/python scripts/10_aim3_llm_stats.py
.venv/bin/python scripts/11_aim3_llm_figures.py
.venv/bin/python scripts/12_aim3_human_results.py
.venv/bin/python scripts/13_aim3_human_figures.py
.venv/bin/python scripts/19_model_comparison_figure.py
.venv/bin/python scripts/21_build_submission_displays.py   # journal-named copies + consistency check
```

### Display naming

Repository figures are named for the analysis that produced them
(`aim3_human_compiled.png`); the manuscript names them for where they appear
(`Figure 1`). `config/displays.yaml` is the single source of truth linking the two, plus the script
that generates each one. `scripts/21_build_submission_displays.py` reads it, writes journal-named
copies to `reports/submission/`, and fails if the manifest, the figures on disk and the manuscript
disagree — so a display cannot be renumbered in one place and left stale in another.

Main displays carry no prefix and count toward the journal limit; supplementary displays are
prefixed `e` (`eFigure 1`, `eTable 1`), which is JAMA house style. A different target journal would
use `Figure S1`, changed by editing the manifest rather than by renaming files.

Confirm nothing drifted:

```bash
git diff --stat -- '*.csv'      # must be empty
```

That empty diff is the reproducibility guarantee: the committed results are exactly what this code
produces from the committed data.

---

## ⚠️ Three steps that must not be re-run

These consume the study's irreplaceable inputs. They are excluded from the sequence above on purpose.

| Step | Why it must not be re-run |
|---|---|
| `01_capture_pages` | Re-fetches every URL. Five pages sit behind bot mitigation and return **HTTP 403**; re-running replaces good captures with error pages. |
| `02_clean_pages` | Regenerates cleaned text **from** raw HTML. For those same five pages the raw file is only a 403 error page — the real text was recovered by hand. Re-running destroys it and silently drops the study from n=26 to an effective n=21. |
| `04_generate_rewrites` | Calls three paid APIs. The current flagship models no longer accept a sampling temperature, so output is **not** reproducible; new rewrites would invalidate all 565 human ratings and 231 cached judge scores. |

---

## What lives where

| Path | Contents |
|---|---|
| `config/` | Locked YAML: site allowlist, model snapshots, search queries, seed |
| `prompts/` | The exact locked rewrite prompt |
| `src/` | Library code — scraping, cleaning, readability, rewriting, judging, scoring, statistics, agreement |
| `scripts/` | Numbered, idempotent pipeline steps |
| `data/raw/` | Captured HTML + provenance (immutable) |
| `data/cleaned/` | Extracted body text |
| `data/rewrites/` | 77 model rewrites + per-call provenance |
| `data/review/` | Blinded instrument, blinding key, de-identified reviewer score sheets |
| `data/scores/` | Readability scores, deltas, judge cache and consensus |
| `reports/` | Generated tables and 600 dpi figures |
| `docs/` | Protocols, statistical analysis plan, scoring rubric, deviation log |
| `tests/` | Unit tests, including pinned readability and agreement values |

---

## Study design in one pass

```
data/urls.csv
   │
   ▼  01 capture ─────────► data/raw/<page_id>.html
   │
   ▼  02 clean ───────────► data/cleaned/<page_id>.txt
   │
   ├──► 03 score originals ───────────────────► Aim 1
   │
   ▼  04 rewrite (3 models) ──► data/rewrites/<page_id>__<model>.txt
   │
   ▼  05 score rewrites ─────────────────────► Aim 2
   │
   ▼  06 build blinded packet ──► blinded_review_packet.csv + unblinding_key.csv
   │
   ├─── blinded human review ──► reviewer_responses/ ──► 12, 13 ──► Aim 3 primary
   │
   └─── automated judge panel ──► 09, 10, 11 ─────────────────────► Aim 3 secondary
                                                                     (screening only)
   07 statistics ──► reports/aim1_*, aim2_*
   08 figures    ──► reports/figures/
```

The automated judge panel is a **clearly-labelled screening signal**. It never substitutes for the
blinded subspecialist review, which is the pre-registered primary endpoint for Aim 3.

---

## Reviewer cohorts

Reviewer type and instrument presentation vary independently, so there are **four** cohorts. They are
never pooled, because the labelled-vs-neutral contrast is one of the things the study measures.

| Cohort | Reviewers | Ratings | Instrument |
|---|---:|---:|---|
| `expert_labeled` — **primary endpoint** | 6 | 155 | standard (labelled) |
| `expert_neutral` | 1 | 25 | neutral wording |
| `layperson_labeled` | 2 | 154 | standard (labelled) |
| `layperson_neutral` | 3 | 231 | neutral wording |

`scripts/12` additionally reports `layperson_all` (5 readers, 385 ratings) for the lay-vs-subspecialist
contrast — an extra row, never a replacement.

---

## Participant privacy

Reviewers are human participants. **No name appears anywhere in this repository.** Sheets are keyed by
opaque IDs (`E01`–`E06`, `L01`–`L05`) applied by `scripts/deidentify_reviewers.py`, which also strips
free-text job titles. The name-to-ID crosswalk is written to `private/`, is gitignored, and is kept with the
study's ethics documentation outside this repository.

Clinical free-text notes are retained — they are commentary on the rewrites and were checked to
contain no participant names.

---

## Reproducibility guarantees

- **Deterministic downstream reproduction.** All shuffling seeds from `random_seed` in
  `config/default.yaml`. Three consecutive runs of the analysis steps reproduce byte-identical CSVs
  **from the frozen committed inputs**. This is not re-creation from live sources: page capture,
  cleaning of the bot-blocked pages, and rewrite generation are deliberately not re-runnable (see the
  table above), so the guarantee covers everything downstream of `data/raw` and `data/rewrites`.
- **No hard-coded results.** Every reported quantity is computed from the data; counts such as the
  rewrite total are derived, not written in.
- **Pinned environment.** `requirements-lock.txt` holds exact versions for the environment that
  produced the committed results. `requirements.txt` uses floor pins and is *not* sufficient to
  guarantee reproduction — `textstat` in particular drives every readability score.
- **Locked artifacts.** `config/`, `prompts/rewrite_v1.txt`, `src/stats.py`,
  `docs/statistical_analysis_plan.md` and `scripts/07_run_statistics.py` are frozen. Any change is
  recorded in `docs/stats_deviations.md` with a date and reason.
- **Provenance.** Every generated artifact carries a JSON sidecar with content hash, git SHA, UTC
  timestamp and config hash.

### Known state

The blinded human review is **complete**. `scripts/12` writes the canonical
`data/scores/accuracy.csv` — one expert mean per (page × model), 77 rows — and `scripts/07` consumes
it, so Aim 3 runs end to end through a single path. The aggregation rule (average multiply-scored
rewrites so each contributes once) is recorded in `docs/stats_deviations.md`. Rating-level tables in
`reports/aim3_compiled_*.csv` remain as supporting descriptives.

---

## Inter-rater agreement — read this before quoting a number

Aim 3 ratings sit against a hard ceiling: ~86% of subspecialist accuracy ratings are the maximum. Under
that condition Cohen's κ collapses toward zero even when raters agree on nearly every item — the
well-known high-agreement/low-κ paradox. Three quantities are therefore reported together:

| Column | What it is |
|---|---|
| `pct_exact`, `pct_within_1` | Raw agreement — transparent, not chance-corrected |
| `gwet_ac1` | Gwet's AC1, computed over the protocol's full 1–5 category set |
| `quad_weighted_kappa` | Quadratic-weighted Cohen's κ — expected near zero here |

**One AC1, one convention.** Chance agreement depends on q, the number of rating categories. The
pipeline fixes q at the **full 1–5 scale defined by the scoring rubric**, for every axis and cohort, so
q cannot shrink merely because a ceiling sample never used the low categories. Taking q from the
observed categories instead is a different estimator and reads materially lower under a ceiling (0.771
vs 0.805 for subspecialist accuracy); it is reachable by passing an explicit category set and is pinned
in the tests as the contrast, but it is not what the pipeline reports.

---

## Testing

```bash
.venv/bin/pytest          # unit tests
.venv/bin/ruff check .    # lint
```

`tests/test_readability.py` asserts exact scores for fixed inputs, so a `textstat` algorithm change
fails loudly rather than silently shifting every result. `tests/test_agreement.py` pins the agreement
coefficients against hand-computed cases. If either breaks after a dependency bump, that is the safety
net working — update the pin and the expected values deliberately, and log it.

---

## Scope of this branch

`main` is the reproduction package. Manuscript drafts, the manuscript cross-check tooling, background
literature, planning notes and exploratory notebooks are deliberately **not** here —
they live on the `draft` branch.

## License

MIT — see [LICENSE](LICENSE).
