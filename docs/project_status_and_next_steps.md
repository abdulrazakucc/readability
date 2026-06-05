# Project Status and Next Steps

A living document that captures **where the pipeline is right now** and **exactly what to do next** to take the project from current state to a finished manuscript. Update this file at the end of every work session.

Master task plan: [data_scientist_tasks.md](data_scientist_tasks.md). This file is the *state snapshot* on top of that plan.

## Last updated

2026-06-03, end of Phase 2 (Aim 1 complete on n=21 originals; Phases 3–6 blocked on API keys).

## At-a-glance status

| Phase | Description | State |
|-------|-------------|-------|
| 0 | Bootstrap (venv, deps, model lock, scorer sanity) | partial, `requirements.txt` works, `pytest` not yet run on fresh clone; `config/models.yaml` already locked; `docs/background_summary.md` is still a stub |
| 1 | Sample selection, capture, clean, manifest | **done**, 26 captured, 21 included, all 3 procedures clear the 5-page floor |
| 2 | Aim 1 readability of originals | **done**, `reports/aim1_*.csv` + 2 figures generated; 0/21 meet FKGL ≤ 6 |
| 3 | AI rewrite arm (Aim 2) | **blocked**, needs API keys for Anthropic, OpenAI, Google |
| 4 | Clinical accuracy scoring (Aim 3) | not started, depends on Phase 3 + reviewer Naeem's availability |
| 5 | Statistics (Aims 2 & 3 portion) | partial, Aim 1 portion done; Aim 2/3 portion blocked on Phases 3–4 |
| 6 | Manuscript support | not started |

See [stats_deviations.md](stats_deviations.md) for protocol deviations logged in this session.

## What is in the repo right now

- `data/urls.csv`, 26 URLs across 3 procedures from the locked allowlist in `config/sites.yaml`
- `data/raw/`, 26 captured HTML files + 26 `.provenance.json` (5 of the HTMLs are 403 error pages)
- `data/cleaned/`, 26 cleaned `.txt` + 26 `.provenance.json`
- `data/manifest.csv`, 26 rows; 21 marked `include=Y`, 5 marked `include=N` with reason
- `data/scores/originals.csv`, 21 scored pages (six formulas)
- `reports/aim1_*.csv`, descriptives, inference, benchmark-meeting
- `reports/figures/aim1_fkgl_by_*.png`, 2 figures

Headline finding (Aim 1): **0/21 included pages meet FKGL ≤ 6** (NIH/AMA 6th-grade benchmark). Median FKGL = 10.4 (IQR 9.5–12.3).

## Open blockers

### B1: API keys for the three rewrite models (high priority)

Required to start Phase 3. Add to a local `.env` (gitignored) from `.env.example`:

```
ANTHROPIC_API_KEY=...
OPENAI_API_KEY=...
GOOGLE_API_KEY=...
```

Cost estimate before running the full arm: roughly **USD $4–6** for the locked 3-model panel on the current 21-page corpus, well under the `cost_warn_usd: 20` guardrail in `config/default.yaml`. Full breakdown (with sensitivity to model choice, corpus growth, and output length) is in [cost_estimates.md](cost_estimates.md). `scripts/04_generate_rewrites.py` will print the actual estimate and require `--confirm-cost` to proceed.

### B2: Five sites blocked by bot detection (low priority)

Johns Hopkins (×3 pages: CCTA, TAVR, LAAO) and Mayo Clinic (×2 pages: CCTA, TAVR) returned HTTP 403 to both the locked research User-Agent and to a clean Chrome User-Agent via headless fetcher. Logged in [stats_deviations.md](stats_deviations.md).

Recovery path per the sample-selection protocol: open each URL in a real browser, paste the visible body text into `data/raw/<page_id>.txt`, then re-run cleaning. The five `page_id`s and URLs are listed under "Resume commands" below. Optional, current n=21 already exceeds the protocol floor.

### B3: Clinical reviewer (Naeem) availability for Aim 3

Required after Phase 3 produces rewrites and Phase 4 builds the blinded review packet. Estimated reviewer effort: 21 pages × 3 rewrites = 63 rewrites to score on accuracy, completeness, and added errors (1–5 each). At 3–5 minutes per rewrite, ~3–5 hours total.

## Next steps (ordered)

Each step lists: inputs → outputs → command → done-when. Steps are mostly idempotent, re-running is safe.

### Step 1: Fill in the background summary (independent of blockers)
- **Why:** Phase 0 deliverable; becomes the manuscript intro.
- **Input:** 4 sources in `literature/`.
- **Output:** `docs/background_summary.md` rewritten as a 250–500-word narrative (currently a stub with bullets).
- **Done when:** A co-author can read it and understand the gap this study fills without opening the PDFs.

### Step 2: (Optional) Manual capture of 5 blocked pages
- **Why:** Bring n from 21 to 26 and recover the two largest-traffic US hospital sites.
- **Input:** browser access to each URL listed below.
- **Command path:**
  - For each `page_id` below, open the URL in a browser. Copy the visible patient-content body (not nav, not footer). Save as `data/raw/<page_id>.txt` (note: `.txt`, not `.html`, the cleaner needs a per-page bypass; see Step 2a).
  - The five pages to recover:
  - `jhmi__cta__f15ba785`, https://www.hopkinsmedicine.org/health/treatment-tests-and-therapies/coronary-computed-tomography-angiography-ccta
  - `jhmi__tavr__7bdb4834`, https://www.hopkinsmedicine.org/health/treatment-tests-and-therapies/transcatheter-aortic-valve-replacement-tavr
  - `jhmi__laao__b5350128`, https://www.hopkinsmedicine.org/health/treatment-tests-and-therapies/left-atrial-appendage-closure-procedures
  - `mayo__cta__7756ee3c`, https://www.mayoclinic.org/tests-procedures/ct-coronary-angiogram/about/pac-20385117
  - `mayo__tavr__739229dd`, https://www.mayoclinic.org/tests-procedures/transcatheter-aortic-valve-replacement/about/pac-20384698
- **Step 2a (code path that does not currently exist):** `02_clean_pages.py` does not yet handle `.txt` manual captures, it expects HTML. Either (a) extend it to detect a `.txt` sibling and copy it through cleaning verbatim, or (b) hand-paste cleaned text directly to `data/cleaned/<page_id>.txt` and patch the manifest `include=Y` + `word_count_cleaned` by hand. Document either choice in `stats_deviations.md`.
- **Done when:** `data/cleaned/<page_id>.txt` exists for all 5 recovered IDs, manifest is updated, and `03_score_originals.py --included-only` reruns to include them. Aim 1 outputs (steps further below) regenerate cleanly.

### Step 3: Unblock B1 (API keys), then run the rewrite arm
- **Input:** populated `.env`.
- **Commands:**
  ```bash
  .venv/bin/python scripts/04_generate_rewrites.py --dry-run # print cost estimate
  .venv/bin/python scripts/04_generate_rewrites.py --confirm-cost # generate rewrites
  ```
- **Output:** `data/rewrites/<page_id>__<model_id>.txt` for each included page × each of the 3 models in `config/models.yaml`. One `_provenance.json` per rewrite.
- **Watch for:** any safety/refusal flag in provenance, log to `stats_deviations.md` if a model declines a page rather than rewriting it.
- **Done when:** 21 pages × 3 models = 63 rewrites exist (or excluded with explicit refusal reason), each with full provenance.

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
