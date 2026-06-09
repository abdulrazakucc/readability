# Cardiac CT Readability Project

Reading-level analysis of online patient education materials for three pre-procedure cardiac CT use cases (TAVR planning, coronary CTA, LAAO/Watchman), with an AI rewrite arm comparing three chatbots on readability *and* clinical accuracy.

Project plan: [docs/cardiac_readability_plan.docx](docs/cardiac_readability_plan.docx)
**Current state & next steps: [docs/project_status_and_next_steps.md](docs/project_status_and_next_steps.md)**
Data-scientist tasks: [docs/data_scientist_tasks.md](docs/data_scientist_tasks.md)
Implementation guidelines: [docs/implementation_guidelines.md](docs/implementation_guidelines.md)
Statistical analysis plan: [docs/statistical_analysis_plan.md](docs/statistical_analysis_plan.md)
Plain-language methods, metrics & statistics companion (start here if new): [docs/methods_and_statistics_companion.md](docs/methods_and_statistics_companion.md)
Automated LLM-judge accuracy assessment (Aim 3 secondary): [docs/aim3_automated_accuracy_assessment.md](docs/aim3_automated_accuracy_assessment.md)
Reviewer guide for the clinical subspecialist: [docs/reviewer_guide_naeem.md](docs/reviewer_guide_naeem.md)
Rough cost estimates for the AI rewrite arm: [docs/cost_estimates.md](docs/cost_estimates.md)
Literature review: [docs/literature_review.md](docs/literature_review.md)
Journal-target assessment, improvements, alternative tests: [docs/jama_publishability_and_improvements.md](docs/jama_publishability_and_improvements.md)

## Layout

| Directory | Purpose |
|-----------------|----------------------------------------------------------------------|
| `docs/` | Project plan, protocols, stats plan, deviation log |
| `literature/` | Background papers (PDF + abstracts + BibTeX) |
| `config/` | Locked YAML configs (sites, models, queries, defaults) |
| `prompts/` | Locked LLM rewrite prompt(s) |
| `src/` | Library code (scrape, clean, readability, ai_rewrite, scoring, stats)|
| `scripts/` | Numbered, idempotent pipeline steps |
| `data/` | Raw HTML, cleaned text, rewrites, scores, manifest |
| `reports/` | Auto-generated tables and figures |
| `notebooks/` | Exploratory analysis only |
| `tests/` | Unit tests |

## Quick start

```bash
# 1. Create venv and install deps
python3 -m venv .venv
.venv/bin/pip install --upgrade pip
.venv/bin/pip install -r requirements.txt

# 2. Add API keys
cp .env.example .env
# fill in ANTHROPIC_API_KEY, OPENAI_API_KEY, GOOGLE_API_KEY

# 3. Sanity-check tests
.venv/bin/pytest

# 4. Seed the URL list at data/urls.csv (procedure,url,notes) and run:
.venv/bin/python scripts/01_capture_pages.py
.venv/bin/python scripts/02_clean_pages.py --included-only
.venv/bin/python scripts/03_score_originals.py --included-only

# 5. After locking config/models.yaml and prompts/rewrite_v1.txt
.venv/bin/python scripts/04_generate_rewrites.py --confirm-cost
.venv/bin/python scripts/05_score_rewrites.py
.venv/bin/python scripts/06_build_review_packet.py

# 6. Hand data/review/review_packet.csv to clinical reviewer (blinded)
# After they return scored sheets: save as data/scores/accuracy.csv with
# columns: page_id, model_id, accuracy_1_5, completeness_1_5, added_errors_1_5
.venv/bin/python scripts/07_run_statistics.py
.venv/bin/python scripts/08_generate_figures.py

# 7. Aim 3 secondary: automated LLM-judge panel (does not wait on the human review)
.venv/bin/python scripts/09_llm_accuracy.py --aggregate
.venv/bin/python scripts/10_aim3_llm_stats.py
.venv/bin/python scripts/11_aim3_llm_figures.py
```

## Pipeline dependency graph

```
data/urls.csv
  │
  ▼
01_capture_pages ─► data/raw/<page_id>.html
  │
  ▼
02_clean_pages ──► data/cleaned/<page_id>.txt
  │
  ├──► 03_score_originals ──► data/scores/originals.csv
  │
  ▼
04_generate_rewrites ──► data/rewrites/<page_id>__<model_id>.txt
  │
  ▼
05_score_rewrites ──► data/scores/rewrites.csv + deltas.csv
  │
  ▼
06_build_review_packet ──► data/review/{review_packet,blind_key}.csv
  │
  clinical scoring (Naeem) → data/scores/accuracy.csv
  │
  ▼
  07_run_statistics ──► reports/aim1_*, aim2_*
  │
  ▼
  08_generate_figures ──► reports/figures/aim1_*, aim2_*

  ── Aim 3 secondary (automated LLM-judge panel; runs off the rewrites, not blocked on Naeem) ──
  04/05 rewrites + data/cleaned ─► 09_llm_accuracy ──► data/scores/accuracy_llm{,_raw}.csv
                                      │
                                      ▼
                                   10_aim3_llm_stats ──► reports/aim3_llm_*
                                      │
                                      ▼
                                   11_aim3_llm_figures ──► reports/figures/aim3_llm_*
```

> The automated panel (09 to 11) is a clearly-labeled screening signal, **not** a substitute for the blinded human review that feeds `07`'s Aim 3 analysis. See `docs/aim3_automated_accuracy_assessment.md` and `docs/methods_and_statistics_companion.md`.

## Reproducibility floor

Every CSV the pipeline emits must be regeneratable from `data/raw/` plus the locked code and config. No manual Excel edits. No copy-paste of LLM output into spreadsheets. See `docs/implementation_guidelines.md`.

## What to lock before each phase

| Phase | Locked artifact |
|----------------|------------------------------------------------|
| Sample (1) | `config/sites.yaml`, `config/search_queries.yaml` |
| Rewrite (3) | `prompts/rewrite_v1.txt`, `config/models.yaml` |
| Stats (5) | `docs/statistical_analysis_plan.md`, `scripts/07_run_statistics.py` |

Lock = git commit. Any later change goes into `docs/stats_deviations.md` with a date and reason.
