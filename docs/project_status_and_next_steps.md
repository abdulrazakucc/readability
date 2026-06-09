# Project Status and Next Steps

A living document that captures **where the pipeline is right now** and **exactly what to do next** to take the project from current state to a finished manuscript. Update this file at the end of every work session.

Master task plan: [data_scientist_tasks.md](data_scientist_tasks.md). This file is the *state snapshot* on top of that plan.

## Last updated

2026-06-08, recovered and re-cleaned the 5 previously-blocked Hopkins/Mayo pages (manual browser capture); included corpus is now 26 pages. Aim 1 scoring/statistics still reflect the earlier n=21 and must be re-run (see Step 2). Phases 3–6 still blocked on API keys.

2026-06-03, end of Phase 2 (Aim 1 complete on n=21 originals; Phases 3–6 blocked on API keys).

## At-a-glance status

| Phase | Description | State |
|-------|-------------|-------|
| 0 | Bootstrap (venv, deps, model lock, scorer sanity) | partial, `requirements.txt` works, `pytest` not yet run on fresh clone; `config/models.yaml` already locked; `docs/background_summary.md` is still a stub |
| 1 | Sample selection, capture, clean, manifest | **done**, 26 captured, 26 included (5 Hopkins/Mayo recovered by manual capture 2026-06-08), all 3 procedures clear the 5-page floor |
| 2 | Aim 1 readability of originals | **stale, needs re-run**, `reports/aim1_*.csv` + 2 figures were generated on n=21; 0/21 met FKGL ≤ 6. Re-score with the 5 recovered pages before citing n=26 |
| 3 | AI rewrite arm (Aim 2) | **blocked**, needs API keys for Anthropic, OpenAI, Google |
| 4 | Clinical accuracy scoring (Aim 3) | not started, depends on Phase 3 + reviewer Naeem's availability |
| 5 | Statistics (Aims 2 & 3 portion) | partial, Aim 1 portion done; Aim 2/3 portion blocked on Phases 3–4 |
| 6 | Manuscript support | not started |

See [stats_deviations.md](stats_deviations.md) for protocol deviations logged in this session.

## What is in the repo right now

- `data/urls.csv`, 26 URLs across 3 procedures from the locked allowlist in `config/sites.yaml`
- `data/raw/`, 26 captured HTML files + 26 `.provenance.json` (5 of the HTMLs are 403 error pages; the real body text for those 5 lives in `data/cleaned/`, captured manually in a browser)
- `data/cleaned/`, 26 cleaned `.txt` + 26 `.provenance.json` (the 5 recovered pages carry `capture_method = "manual_browser"`)
- `data/manifest.csv`, 26 rows; all 26 marked `include=Y` (5 flipped from `N` on 2026-06-08 after manual recovery)
- `data/scores/originals.csv`, 21 scored pages (six formulas) — **does not yet include the 5 recovered pages; re-run scoring**
- `reports/aim1_*.csv`, descriptives, inference, benchmark-meeting
- `reports/figures/aim1_fkgl_by_*.png`, 2 figures

Headline finding (Aim 1, on the n=21 corpus): **0/21 included pages meet FKGL ≤ 6** (NIH/AMA 6th-grade benchmark). Median FKGL = 10.4 (IQR 9.5–12.3). These numbers predate the 5 recovered pages and will shift slightly once scoring is re-run on n=26.

## Open blockers

### B1: API keys for the three rewrite models (high priority)

Required to start Phase 3. Add to a local `.env` (gitignored) from `.env.example`:

```
ANTHROPIC_API_KEY=...
OPENAI_API_KEY=...
GOOGLE_API_KEY=...
```

Cost estimate before running the full arm: roughly **USD $4–6** for the locked 3-model panel on the current 21-page corpus, well under the `cost_warn_usd: 20` guardrail in `config/default.yaml`. Full breakdown (with sensitivity to model choice, corpus growth, and output length) is in [cost_estimates.md](cost_estimates.md). `scripts/04_generate_rewrites.py` will print the actual estimate and require `--confirm-cost` to proceed.

### B2: Five sites blocked by bot detection (RESOLVED 2026-06-08)

Johns Hopkins (×3 pages: CCTA, TAVR, LAAO) and Mayo Clinic (×2 pages: CCTA, TAVR) returned HTTP 403 to both the locked research User-Agent and to a clean Chrome User-Agent via headless fetcher. Recovered on 2026-06-08 by manual browser capture and re-cleaned to pipeline standard (`scripts/_reclean_manual.py`); manifest, cleaned text, and provenance are updated. Logged in [stats_deviations.md](stats_deviations.md). The only remaining action is to re-score (Step 2) so Aim 1 outputs reflect n=26.

### B3: Clinical reviewer (Naeem) availability for Aim 3

Required after Phase 3 produces rewrites and Phase 4 builds the blinded review packet. Estimated reviewer effort: 26 pages × 3 rewrites = 78 rewrites to score on accuracy, completeness, and added errors (1–5 each). At 3–5 minutes per rewrite, ~4–6 hours total.

## Next steps (ordered)

Each step lists: inputs → outputs → command → done-when. Steps are mostly idempotent, re-running is safe.

### Step 1: Fill in the background summary (independent of blockers)
- **Why:** Phase 0 deliverable; becomes the manuscript intro.
- **Input:** 4 sources in `literature/`.
- **Output:** `docs/background_summary.md` rewritten as a 250–500-word narrative (currently a stub with bullets).
- **Done when:** A co-author can read it and understand the gap this study fills without opening the PDFs.

### Step 2: Re-score Aim 1 on the recovered n=26 corpus
- **Why:** The 5 Hopkins/Mayo pages were recovered and cleaned on 2026-06-08 (manual capture; option (b) below was taken). Manifest, cleaned text, and provenance are done. Scoring and all Aim 1 outputs still reflect n=21 and must be regenerated.
- **What was already done (2026-06-08):**
  - The 5 pages were captured in a browser and saved straight to `data/cleaned/<page_id>.txt` (the cleaner only handles HTML; option (b)). They were then re-cleaned to pipeline standard with `scripts/_reclean_manual.py`, which strips the boilerplate trafilatura would have removed and applies the project's unicode/whitespace normalizers.
  - `data/manifest.csv`: 5 rows flipped to `include=Y`, `word_count_cleaned` set (825 / 1199 / 1357 / 1227 / 484), manual-capture note added.
  - Provenance JSON regenerated for all 5 with `capture_method = "manual_browser"`.
  - The five recovered `page_id`s:
  - `jhmi__cta__f15ba785`, https://www.hopkinsmedicine.org/health/treatment-tests-and-therapies/coronary-computed-tomography-angiography-ccta
  - `jhmi__tavr__7bdb4834`, https://www.hopkinsmedicine.org/health/treatment-tests-and-therapies/transcatheter-aortic-valve-replacement-tavr
  - `jhmi__laao__b5350128`, https://www.hopkinsmedicine.org/health/treatment-tests-and-therapies/left-atrial-appendage-closure-procedures
  - `mayo__cta__7756ee3c`, https://www.mayoclinic.org/tests-procedures/ct-coronary-angiogram/about/pac-20385117
  - `mayo__tavr__739229dd`, https://www.mayoclinic.org/tests-procedures/transcatheter-aortic-valve-replacement/about/pac-20384698
- **Command (still to run):**
  ```bash
  .venv/bin/python scripts/03_score_originals.py --included-only
  .venv/bin/python scripts/07_run_statistics.py
  .venv/bin/python scripts/08_generate_figures.py
  ```
- **Then refresh manuscript numbers:** every "n = 21", "0 of 21", median FKGL, IQR, and ANOVA / Kruskal-Wallis value in `publication/draft_manuscript.md`, `publication/build_docx.py`, and `docs/data_scientist_tasks.md` must be updated from the regenerated `reports/aim1_*.csv`.
- **Done when:** `data/scores/originals.csv` has 26 rows and every Aim 1 number in the manuscript traces to a regenerated `reports/` CSV.

### Step 3: Unblock B1 (API keys), then run the rewrite arm
- **Input:** populated `.env`.
- **Commands:**
  ```bash
  .venv/bin/python scripts/04_generate_rewrites.py --dry-run # print cost estimate
  .venv/bin/python scripts/04_generate_rewrites.py --confirm-cost # generate rewrites
  ```
- **Output:** `data/rewrites/<page_id>__<model_id>.txt` for each included page × each of the 3 models in `config/models.yaml`. One `_provenance.json` per rewrite.
- **Watch for:** any safety/refusal flag in provenance, log to `stats_deviations.md` if a model declines a page rather than rewriting it.
- **Done when:** 26 pages × 3 models = 78 rewrites exist (or excluded with explicit refusal reason), each with full provenance.

### Step 4: Score the rewrites
- **Command:** `.venv/bin/python scripts/05_score_rewrites.py`
- **Outputs:** `data/scores/rewrites.csv` (per-rewrite six-formula scores) and `data/scores/deltas.csv` (post − pre for all six formulas, keyed `page_id × model_id`).
- **Done when:** `deltas.csv` joins cleanly to `originals.csv` on `page_id`.

### Step 5: Build the blinded review packet
- **Command:** `.venv/bin/python scripts/06_build_review_packet.py`
- **Outputs:** `data/review/review_packet.csv` (for Naeem; original text + three model-stripped rewrites in randomized order, each tagged with `blind_id`) and `data/review/blind_key.csv` (NOT shared with Naeem; maps `blind_id` → `(page_id, model_id)`).
- **Hand-off:** send `review_packet.csv` to Naeem along with `docs/accuracy_scoring_rubric.md`. Do NOT send `blind_key.csv`.
- **Done when:** the packet is sent and the blind key is committed locally but not surfaced to the reviewer.

### Step 6: Receive Naeem's scored sheets, unblind, and run full statistics
- **Input (from Naeem):** a CSV with columns `blind_id, accuracy_1_5, completeness_1_5, added_errors_1_5, notes`.
- **Local processing:** join Naeem's CSV to `blind_key.csv` on `blind_id`, write `data/scores/accuracy.csv` keyed `page_id × model_id`.
- **Commands:**
  ```bash
  .venv/bin/python scripts/07_run_statistics.py
  .venv/bin/python scripts/08_generate_figures.py
  ```
- **Outputs:** Aim 2 and Aim 3 reports under `reports/` and figures under `reports/figures/`.
- **Done when:** every result number cited in the manuscript draft has a deterministic source CSV.

### Step 7: Manuscript support (Phase 6)
- Generate every table/figure from a script (no hand-edited Illustrator).
- Build `reports/manuscript_numbers.md` listing every number in the manuscript with the source script + CSV row.
- Run the full reproducibility checklist in [implementation_guidelines.md](implementation_guidelines.md#reproducibility-checklist-run-before-any-manuscript-submission) before submission.

## Resume commands (quick reference)

After clearing **B1 (API keys)**, the minimum sequence to go from current state to finished pipeline (assuming no manual re-captures):

```bash
# Phase 3: rewrites
.venv/bin/python scripts/04_generate_rewrites.py --confirm-cost
.venv/bin/python scripts/05_score_rewrites.py

# Phase 4: blinded packet for clinical scoring
.venv/bin/python scripts/06_build_review_packet.py
# … send data/review/review_packet.csv to Naeem with docs/accuracy_scoring_rubric.md …
# … receive scored sheet: save as data/scores/accuracy_raw_from_naeem.csv …
# … join on blind_id to produce data/scores/accuracy.csv …

# Phase 5: full statistics & figures
.venv/bin/python scripts/07_run_statistics.py
.venv/bin/python scripts/08_generate_figures.py
```

If Aim 1 is re-run with manually recaptured pages from B2, regenerate originals first:

```bash
.venv/bin/python scripts/02_clean_pages.py --force
.venv/bin/python scripts/03_score_originals.py --included-only
.venv/bin/python scripts/07_run_statistics.py
.venv/bin/python scripts/08_generate_figures.py
```

## Reproducibility checklist (run before submission)

From [implementation_guidelines.md](implementation_guidelines.md#reproducibility-checklist-run-before-any-manuscript-submission):

- [ ] Fresh clone + fresh venv builds clean.
- [ ] `pytest` passes.
- [ ] Running the full pipeline from `data/raw/` reproduces every number in the manuscript.
- [ ] Every figure has a script that generates it; no hand-edits.
- [ ] `requirements.lock` is committed and matches the env hash recorded in the latest report.
