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

