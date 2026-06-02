# Sample Selection Protocol

Pre-registered procedure for selecting patient-education pages. Lock this document before any capture run. Any deviation must be recorded in `docs/stats_deviations.md`.

## Procedures studied (3)

1. **Pre-TAVR cardiac CT** — CT planning before transcatheter aortic valve replacement.
2. **Coronary CTA** — coronary CT angiography.
3. **Left atrial appendage closure CT** — pre-procedure CT for Watchman / LAAO devices.

## Locked site allowlist

Pages are sourced from these patient-facing sites:

- RadiologyInfo.org
- American Heart Association (heart.org)
- American College of Cardiology — CardioSmart (cardiosmart.org)
- British Heart Foundation (bhf.org.uk)
- Mayo Clinic (mayoclinic.org)
- Cleveland Clinic (clevelandclinic.org)
- Top hospital pages appearing in the first 2 pages of Google search (Johns Hopkins, Brigham and Women's, Stanford Health, UCSF Health, etc. — captured per-search, never invented)

The exact list is in `config/sites.yaml`. Lock with a git commit before Phase 1.

## Search procedure

Reproducibility of search is hard but possible if you follow these rules exactly:

1. **One person, one machine, one week.** All searches done from the same browser profile within a single ≤7-day window. Record start and end dates.
2. **Incognito / private mode.** Sign out of Google. Use the same geographic location for every search. Record location (city/region).
3. **Fixed queries per procedure.** Use the queries in `config/search_queries.yaml`. Examples:
   - "pre-TAVR cardiac CT patient information"
   - "coronary CT angiography what to expect"
   - "Watchman procedure CT scan preparation"
4. **First 2 pages of results.** Record top 20 organic results per query (skip ads, knowledge panel, video carousel, "people also ask"). Save the SERP HTML for archival.
5. **Filter to allowlisted sites.** Drop results from sites not on the allowlist. If a new high-quality site appears repeatedly across queries (e.g., on >2 of 3 procedures' SERPs), add it to the allowlist by amending `config/sites.yaml` AND log the addition in `docs/stats_deviations.md` with date and reason.

## Inclusion criteria

A page is **included** if all are true:

- Written in English.
- Aimed at patients (not clinicians, students, or researchers).
- About one of the three procedures (CT-specific pages preferred for TAVR and LAAO; for coronary CTA, the procedure is itself a CT scan).
- Body text length ≥ 200 words after cleaning.
- Publicly accessible without login or paywall.
- Captured cleanly (no extraction errors flagged by the cleaner).

## Exclusion criteria

A page is **excluded** if any are true:

- Pop-up or modal-only content (no substantive body).
- Behind a login or paywall.
- Video-only, podcast-only, or image-only pages.
- Forum / Q&A / patient-community user-generated content.
- Duplicate URL (canonicalize first; if the page exists at multiple URLs on the same site, take the canonical one).
- Translated machine-generated content (rare but possible on hospital sites).
- Aimed at clinicians or trainees (look for "for clinicians" or DOI-linked journal content).

For every excluded page, record the URL and the exclusion reason in `data/manifest.csv` with `include = N`.

## Target sample size

20–40 included pages total, with each procedure contributing at least 5 pages if possible. If a procedure cannot reach 5 from the allowlisted sites, report the cap honestly in the manuscript Methods.

## Capture mechanics

- The capture script downloads each URL using a fixed User-Agent (record it in config), with a 30-second timeout and one retry.
- Save raw HTML to `data/raw/<page_id>.html` where `page_id = <site_short>__<procedure>__<sha8>`.
- Save a `_provenance.json` next to each raw file with URL, captured_at (UTC ISO 8601), HTTP status, content hash, User-Agent.
- If the site has a `robots.txt` disallow, do not scrape — record a manual-capture path in the manifest and have the human paste the visible body text into `data/raw/<page_id>.txt`.

## Cleaning

See `docs/implementation_guidelines.md#cleaning-rules`. Cleaning is deterministic given raw HTML and the locked cleaner config — never tweak the cleaner per-page.

## Deviation logging

If you discover after capture that a site is broken, or that a query gave zero allowlisted results, or that the cleaner failed on a page, record:

- What you found
- What you changed (allowlist addition, query addition, manual capture, etc.)
- Date

In `docs/stats_deviations.md`. Reviewers will ask. Better to volunteer than to be caught.

## Manifest schema (`data/manifest.csv`)

| column              | type     | notes                                                |
|---------------------|----------|------------------------------------------------------|
| page_id             | string   | site_short__procedure__sha8                          |
| procedure           | enum     | tavr / cta / laao                                    |
| site                | string   | short name (mayo, cleveland, ...)                    |
| url                 | string   | canonical URL                                        |
| captured_at         | ISO8601  | UTC                                                  |
| http_status         | int      |                                                      |
| raw_path            | string   | relative to repo root                                |
| cleaned_path        | string   | relative to repo root                                |
| word_count_raw      | int      | from raw HTML body                                   |
| word_count_cleaned  | int      | from cleaned text                                    |
| include             | enum     | Y / N                                                |
| exclusion_reason    | string   | empty if include = Y                                 |
| notes               | string   | free text                                            |
