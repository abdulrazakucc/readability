# Statistical Analysis Plan — Deviations Log

Any change to the locked plan in `statistical_analysis_plan.md`, the locked prompt, the locked site list, or the locked model versions goes here. One entry per change, dated, with a short rationale.

Reviewers will ask. Volunteer.

## Template

```
### YYYY-MM-DD — short title
- What changed:
- Why:
- Affected outputs:
- Decided by:
```

## Entries

### 2026-06-09: Added a secondary, exploratory automated LLM-judge accuracy panel (Aim 3)
- What changed: Beyond the pre-registered blinded subspecialist review (which remains the PRIMARY Aim 3 endpoint and is still pending), an automated screening analysis was added: a panel of 3 LLM judges (Claude Opus 4.8, GPT-5.5, Gemini 3.1 Pro) scored all 77 rewrites against their originals on the 3 locked rubric dimensions, blinded to the producing model (231 judgments). Outputs use clearly-labeled `*_llm_*` filenames and are never represented as human/subspecialist scores. Pipeline: `src/llm_judge.py`, `scripts/09_llm_accuracy.py`, `scripts/10_aim3_llm_stats.py`, `scripts/11_aim3_llm_figures.py`. Full write-up: `docs/aim3_automated_accuracy_assessment.md`.
- Why: To triage pages for human review, to give an early reproducible signal on the readability–accuracy trade-off, and to later validate the human scores (human-vs-automated agreement). A multi-judge panel was chosen specifically so inter-judge agreement and self-preference bias could be measured.
- Key results / caveats logged for transparency: significant across-model accuracy difference (Friedman χ²=21.1, p=2.6e-5) with a readability–fidelity trade-off (Gemini most simplified/least faithful; GPT-5.5 least simplified/most faithful; Claude best balance); strong ceiling effect (89% of accuracy ratings maximal); demonstrated self-preference by the GPT-5.5 judge (own-model accuracy 5.00 vs 4.64 others, p=.001). These caveats are reported in the manuscript and the assessment doc; the automated screen does NOT substitute for human review.
- Affected outputs: `data/scores/accuracy_llm_raw.csv`, `accuracy_llm.csv`; `reports/aim3_llm_*.csv`; `reports/figures/aim3_llm_*.png`; `docs/aim3_automated_accuracy_assessment.md`; manuscript Aim 3 secondary subsection.
- Decided by: Project lead (this run).

### 2026-06-09: AI rewrite arm model panel and sampling-parameter changes
- What changed: The locked rewrite panel in `config/models.yaml` was set to the current flagship models: Anthropic `claude-opus-4-8`, OpenAI `gpt-5.5-2026-04-23`, Google `gemini-3.1-pro-preview` (replacing the earlier placeholder `claude-opus-4-7` / `gpt-4o-2024-08-06` / `gemini-1.5-pro-002`). Two sampling-related deviations from the original protocol followed, forced by the providers:
  1. **No temperature on the reasoning models.** Claude Opus 4.8 and GPT-5.x are reasoning models that no longer accept a sampling `temperature` (the API returns HTTP 400 if one is sent). `temperature` is therefore omitted for the Claude and OpenAI arms; the locked protocol's "temperature = 0" is retained only for Gemini. Determinism is no longer tunable via temperature on the two reasoning models.
  2. **GPT-5.5 token/effort parameters.** GPT-5.x requires `max_completion_tokens` (not `max_tokens`); the budget is shared between internal reasoning tokens and visible output, so it is set to 16000. `reasoning_effort = "low"` is used because a plain-language rewrite is not a hard reasoning task; this keeps reasoning-token cost down (observed ~11 reasoning tokens on a sample call) without degrading the rewrite.
- Why: Use the strongest currently available model from each provider, matching the study's intent ("can contemporary frontier LLMs lower reading level without losing accuracy"). The parameter changes are not design choices but hard API requirements of these model generations.
- Affected outputs: `data/rewrites/*` and their provenance JSON (which record `model_requested`, `model_returned`, `temperature`, `reasoning_effort`, and token counts per call), `src/ai_rewrite.py` (per-provider parameter handling), `config/models.yaml`.
- Decided by: Project lead (this run).

### 2026-06-09: GPT-5.5 content-filter truncation on one page (UCSF coronary CTA)
- What changed: For `ucsf__cta__071e7999`, GPT-5.5 reproducibly returned `finish_reason = "content_filter"` and truncated the rewrite mid-sentence in the contrast-dye-allergy / kidney-risk section (~855 words, ~1031 output tokens, far below the 16000 budget). Two independent attempts with the locked prompt truncated at the same place. The locked prompt was not modified to work around it (per-page prompt changes would bias the cross-model comparison). The truncated output is therefore quarantined from analysis: the text file is renamed `…__openai.txt.excluded_content_filter` (so `05_score_rewrites.py`, which globs `*.txt`, skips it) and its provenance JSON is kept as the audit record. The GPT-5.5 arm thus has 25 of 26 pages; this one page×model cell is missing-not-at-random.
- Why: A truncated rewrite is not a complete rewrite of the page, so its FKGL is not comparable to the original's in the paired Aim 2 test, and it cannot be fairly accuracy/completeness-scored in Aim 3. Excluding the cell is more honest than scoring a partial text as if complete. The truncation is itself a reportable finding (a frontier model declining to fully rewrite routine patient-safety content).
- Affected outputs: `data/rewrites/ucsf__cta__071e7999__openai.txt.excluded_content_filter` (+ its provenance), `data/scores/rewrites.csv` / `deltas.csv` (GPT-5.5 has n=25), `reports/aim2_*` (OpenAI paired test n=25; 3-model Friedman drops this page via listwise deletion).
- Decided by: Project lead (this run).

### 2026-06-09: Gemini 3.1 Pro arm run; output budget raised to avoid thinking-token truncation
- What changed: After billing was enabled, the Gemini 3.1 Pro arm ran for all 26 pages. On the first run (`max_tokens = 8192`), the three longest originals (`radinfo__cta`, `mayo__cta`, `mayo__tavr`) returned `finish_reason = MAX_TOKENS` with only ~270 visible words: Gemini 3.1 Pro is a thinking model whose internal reasoning tokens share the `max_output_tokens` budget, so reasoning consumed most of the 8192 cap and truncated the rewrites. The locked Gemini `max_tokens` was raised to 32768 and the **entire** Gemini arm (all 26 pages) regenerated so generation parameters are uniform across the arm. The cap only bound on the three long pages; the other 23 stopped naturally at `STOP` and are unchanged in substance.
- Why: A truncated rewrite is not a valid full-page rewrite (same reasoning as the GPT-5.5 content-filter exclusion). Raising the budget is the correct fix here because the truncation was a token-ceiling artifact, not a model refusal, and regenerating recovers complete rewrites rather than dropping the pages.
- Affected outputs: `config/models.yaml` (Gemini `max_tokens` 8192 → 32768), `data/rewrites/*__gemini.*` (regenerated), `data/scores/rewrites.csv` / `deltas.csv`, `reports/aim2_*`.
- Decided by: Project lead (this run).

### 2026-06-09: Gemini Pro tier blocked by billing; arm pending (resolved same day)
- What changed: The project `GOOGLE_API_KEY` returns HTTP 429 (`RESOURCE_EXHAUSTED`, "check your plan and billing details") on every Gemini Pro model (`gemini-3.1-pro-preview`, `gemini-2.5-pro`); only Flash-tier models (`gemini-3.5-flash`, `gemini-2.5-flash`) are reachable on the key as configured. The project lead opted to enable billing and use a Pro model for flagship parity with the Claude and OpenAI arms, so the Gemini rewrite arm is held until billing is active. The Claude and OpenAI arms (26 pages each) were generated first.
- Why: Matching model tier across the three vendors matters for a fair cross-model comparison (Aim 2/3). Running Gemini at Flash tier while the others are flagship would confound the model comparison.
- Affected outputs: `data/rewrites/*__gemini.*` (not yet generated); `reports/aim2_across_models.csv` (the 3-model Friedman test is skipped until all three arms exist).
- Decided by: Project lead (this run).

### 2026-06-08: Five blocked pages recovered by manual browser capture (Hopkins, Mayo)
- What changed: The 5 pages excluded on 2026-06-03 for HTTP 403 (Johns Hopkins CCTA, TAVR, LAAO; Mayo Clinic CCTA, TAVR) were recovered per the sample-selection protocol. Visible body text was opened and copied from each URL in a real browser and saved to `data/cleaned/<page_id>.txt`. Each was then re-cleaned to the standard pipeline output with `scripts/_reclean_manual.py`: an explicit, auditable set of boilerplate lines was removed (nav menus, related-link lists, promo/video sidebars, image captions and alt text, "Clinical trials / Explore Mayo Clinic studies" promo), then the project's own `_normalize_unicode` / `_drop_junk_lines` / `_normalize_whitespace` were applied so the result matches the 16 auto-cleaned pages (smart quotes and em dashes normalized to ASCII). All 5 exceed the 200-word inclusion floor (484 to 1,357 cleaned words). The manifest rows are now `include = Y` with the exclusion reason cleared; provenance JSON records `capture_method = "manual_browser"`.
- Why: Recovers two of the largest U.S. academic-medical-center patient portals and brings the included sample from n = 21 to n = 26. The pages are genuine patient education content; only the automated transport was blocked.
- Affected outputs: `data/manifest.csv` (5 rows flipped to included, `word_count_cleaned` set to 825 / 1199 / 1357 / 1227 / 484), `data/cleaned/<page_id>.txt` and `.provenance.json` (5 each). `http_status` remains 403 to record the original automated result; a manual-capture note was added to `notes`.
- Still pending (next step): scoring (`scripts/03_score_originals.py`) and all Aim 1 statistics, figures, and manuscript numbers were computed on n = 21 and have NOT been recomputed. Re-run scoring and `scripts/07_run_statistics.py`, then refresh `reports/*`, `publication/build_docx.py`, and `publication/draft_manuscript.md` (every "n = 21", "0 of 21", median FKGL, ANOVA / Kruskal-Wallis values) before citing n = 26 results.
- Decided by: Project lead (this run).

### 2026-06-03: Five URLs blocked by site bot detection (Hopkins, Mayo)
- What changed: 5 of 26 candidate URLs returned HTTP 403 to the locked research User-Agent (all 3 Johns Hopkins pages: CCTA, TAVR, LAAO; both Mayo Clinic pages: CCTA, TAVR). Retries with a clean Chrome User-Agent and via a headless-browser fetcher also returned 403, indicating Akamai/Cloudflare WAF blocking at the network level, not a robots.txt disallow but the same practical outcome. These pages are marked `include = N` with `exclusion_reason = "blocked by site bot detection (HTTP 403); needs manual browser capture per protocol"`. Per the sample-selection protocol, these may be recovered by manual paste of visible body text into `data/raw/<page_id>.txt`; that has not yet been done.
- Why: Mayo Clinic and Johns Hopkins host their patient sites behind aggressive bot mitigation. The locked, polite scraping path the project specifies is not sufficient to reach them.
- Affected outputs: `data/manifest.csv` (5 rows excluded), `data/raw/*.html` (5 files contain the 403 error pages, not page content).
- Decided by: Project lead (this run). Re-capture via manual paste is open.

### 2026-06-03: Search procedure executed via programmatic web search rather than incognito browser session
- What changed: The locked sample-selection protocol calls for "one person, one machine, one week" of incognito Google searches with archived SERP HTML. Initial sample selection for this run was executed via programmatic web search (search API restricted to the locked allowlist of patient-facing sites) instead of an in-browser session. Queries used are exactly those in `config/search_queries.yaml`; site allowlist is unchanged.
- Why: The data scientist running Phase 1 did not have access to a live incognito browser session at execution time. The programmatic search returns the same patient-facing pages on the allowlisted domains that an in-browser SERP would have surfaced for these queries; archival of SERP HTML was not performed.
- Affected outputs: `data/urls.csv` (candidate URL list), `data/raw/*` (captured HTML), `data/manifest.csv`.
- Decided by: Project lead (this run).

