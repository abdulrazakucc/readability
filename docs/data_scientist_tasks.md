# Data Scientist Tasks — Cardiac CT Readability Project

This document operationalizes the project plan in `cardiac_readability_plan.docx` for the data scientist / mentee. It maps every aim to discrete, ship-shaped tasks with inputs, outputs, and acceptance criteria.

## Role and scope

The data scientist owns everything from URL capture through statistical analysis. The subspecialist (Naeem) owns clinical scoring of rewrites. The biostatistician validates the statistics plan but does not run it.

You are NOT just a script-runner: you are responsible for the *reproducibility* of every number that lands in the manuscript. If a future reviewer or co-author cannot rerun your pipeline and get the same CSV out, the work is not done.

## Phase-by-phase tasks

### Phase 0 — Project bootstrap (Week 1)

- [ ] Read all four background papers in `literature/` and write the one-page "what's known / what's the gap" summary into `docs/background_summary.md` (this becomes the manuscript intro).
- [ ] Confirm the Python venv builds clean from `requirements.txt` on a fresh checkout. Document your Python version in `docs/environment.md`.
- [ ] Decide and lock the API keys and model versions you will use for the rewrite arm. Write the exact model IDs and date into `config/models.yaml`.
- [ ] Sanity-check the readability scorer against a known reference (see Phase 2).

**Done when:** a co-author can `git clone`, create a venv, and run `pytest` green without any tribal knowledge.

### Phase 1 — Sample selection (Weeks 1–3)

See [sample_selection_protocol.md](sample_selection_protocol.md) for the procedural rules — this section is the data-side task list.

- [ ] Finalize the site allowlist in `config/sites.yaml`. Lock this before any capture.
- [ ] Capture pages using `scripts/01_capture_pages.py`. The script must record: URL, capture timestamp (UTC ISO 8601), HTTP status, raw HTML, content hash, user-agent.
- [ ] Clean each page to body-only text using `scripts/02_clean_pages.py`. Keep both `raw/` and `cleaned/` versions — never overwrite raw.
- [ ] Maintain `data/manifest.csv` with one row per page: `page_id`, `procedure`, `site`, `url`, `captured_at`, `word_count`, `cleaned_word_count`, `include` (Y/N), `exclusion_reason`.
- [ ] For each excluded page, write the exclusion reason — never silently drop.
- [ ] Hand-spot-check 10% of the cleaned pages against the original HTML. Log any cleaning failures and re-run if menus or footer text crept in.

**Done when:** the manifest has 20–40 included pages spread across all three procedures and all locked sites, and a colleague reading the manifest can reproduce the corpus without re-asking you.

### Phase 2 — Readability scoring of originals (Aim 1, Week 5)

- [ ] Run `scripts/03_score_originals.py` to produce `data/scores/originals.csv` with columns: `page_id`, plus six readability scores (`fkre`, `fkgl`, `gfi`, `smog`, `cli`, `ari`), plus `word_count`, `sentence_count`, `avg_words_per_sentence`, `avg_syllables_per_word`, `scorer_version`.
- [ ] Verify on 2–3 pages with an online calculator (e.g., readabilityformulas.com). Acceptable drift: ±0.5 grade level. If larger, debug.
- [ ] Generate Aim 1 descriptives (mean ± SD per site, per procedure) — see [statistical_analysis_plan.md](statistical_analysis_plan.md).
- [ ] Report what fraction of pages meet the 6th-grade NIH/AMA benchmark.

**Done when:** `reports/aim1_descriptives.md` is generated automatically and matches the numbers the stats script outputs.

### Phase 3 — AI rewrite arm (Aim 2, Weeks 6–7)

See [ai_rewrite_protocol.md](ai_rewrite_protocol.md) for the exact prompt, model version policy, and reproducibility rules.

- [ ] For each included page × each of the three models, generate one rewrite via `scripts/04_generate_rewrites.py`.
- [ ] Every rewrite must record: model name, model version string returned by the API, prompt hash, generation timestamp, token usage, temperature, any safety/refusal flag.
- [ ] Re-score every rewrite using the same scorer from Phase 2. Output `data/scores/rewrites.csv`.
- [ ] Compute deltas per page per model (post − pre) for all six formulas. Save to `data/scores/deltas.csv`.

**Done when:** every original page has exactly three rewrites with full provenance, and the deltas table joins cleanly to the originals table on `page_id`.

### Phase 4 — Accuracy and completeness scoring (Aim 3, Weeks 8–9)

The data scientist does NOT score clinical accuracy — Naeem does. But the data scientist builds the scoring infrastructure.

- [ ] Build the blinded review packet via `scripts/05_build_review_packet.py`. For each page, emit a packet with the original text, the three rewrites with model identifiers stripped, in randomized order, plus a unique blinded ID per rewrite (`blind_id`).
- [ ] Maintain the unblinding key in `data/scores/blind_key.csv`. Keep it out of the review packet.
- [ ] Provide the reviewer (Naeem) a clean spreadsheet template (`reports/review_template.csv`) with columns: `blind_id`, `accuracy_1_5`, `completeness_1_5`, `added_errors_1_5`, `notes`.
- [ ] After Naeem returns scored sheets, join on `blind_id` to unblind. Output `data/scores/accuracy.csv`.
- [ ] If a second reader is available for a subset, compute inter-rater agreement (Cohen's weighted kappa for ordinal 1–5 scores).

**Done when:** every rewrite has a clinical score linked to its model identity, but the reviewer was blinded at scoring time.

### Phase 5 — Statistics (Weeks 10–11)

See [statistical_analysis_plan.md](statistical_analysis_plan.md) for the pre-registered tests. Implement them, do not invent new ones mid-analysis.

- [ ] Run `scripts/06_run_statistics.py`. This file must be locked (no edits) before any p-value is read.
- [ ] Output `reports/aim1_stats.csv`, `reports/aim2_stats.csv`, `reports/aim3_stats.csv` plus rendered tables/figures in `reports/figures/`.
- [ ] If anything in the data forces an unplanned test (e.g., severe non-normality), document the deviation in `docs/stats_deviations.md` with the date and the reason — this is what a journal will ask.

**Done when:** the stats report is reproducible from the locked script and the CSVs.

### Phase 6 — Manuscript support (Weeks 12–14)

- [ ] Generate every table and figure in the manuscript from a script in `scripts/` so that any data update propagates automatically.
- [ ] Provide a `reports/manuscript_numbers.md` file that lists every number cited in the manuscript with its source script and CSV row. This is your shield against "where did 47% come from?" questions.

## Cross-cutting standards

**Reproducibility floor.** Every CSV the pipeline emits must be regenerable from the raw HTML in `data/raw/` plus the locked code. No manual Excel edits. No copy-paste of model output into spreadsheets.

**Provenance over cleverness.** When in doubt, record more metadata, not less. Model versions, timestamps, prompt hashes, and content hashes are cheap to record and impossible to reconstruct after the fact.

**Bias control.** The data scientist never sees clinical scores during data prep, and the clinical reviewer never sees model identities during scoring. Both directions matter.

**Pre-registration.** The statistical analysis plan is locked before Phase 5 starts. The prompt is locked before Phase 3 starts. The site list is locked before Phase 1 starts. "Locked" means the file is tagged in git and any later change is explicitly logged.

**Honest sample size.** If a procedure has too few pages, the manuscript reports that. Do not pad with marginal pages to hit a sample-size target.

## Deliverables checklist (final)

- [ ] `data/manifest.csv` — every page with capture provenance
- [ ] `data/raw/` — original HTML, untouched
- [ ] `data/cleaned/` — body-only text
- [ ] `data/rewrites/` — every rewrite with model provenance
- [ ] `data/scores/originals.csv`, `rewrites.csv`, `deltas.csv`, `accuracy.csv`
- [ ] `reports/` — all auto-generated tables and figures
- [ ] `scripts/` — locked, runnable end-to-end with one command
- [ ] `docs/` — protocol, stats plan, prompt, deviations log
