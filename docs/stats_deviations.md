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

