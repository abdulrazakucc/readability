# Implementation Guidelines

Engineering rules for the cardiac CT readability project. These keep the analysis reproducible, the manuscript defensible, and the codebase pleasant.

## Repository layout

```
readability/
├── docs/                  Plan, protocols, stats plan, this guide
├── literature/            Background papers (PDFs and citations)
├── config/                YAML config: sites, models, prompts
├── prompts/               The exact rewrite prompt(s), versioned
├── src/                   Library code (importable modules)
├── scripts/               Numbered, idempotent pipeline steps
├── data/
│   ├── raw/               Captured HTML (immutable)
│   ├── cleaned/           Body-only text
│   ├── rewrites/          Per-model rewrites
│   └── scores/            CSV outputs
├── reports/               Auto-generated tables and figures
├── notebooks/             Exploratory analysis ONLY
├── tests/                 Unit tests
├── requirements.txt
├── pyproject.toml
└── README.md
```

## Environment

- Python 3.10 or newer.
- Virtual environment in `.venv/` (gitignored).
- Install pinned versions from `requirements.txt`. On first significant release, generate `requirements.lock` via `pip freeze` and commit it for full reproducibility.
- API keys live in `.env` (gitignored). `.env.example` documents the required keys without leaking real values.

## Pipeline philosophy

Each step in `scripts/` is **idempotent** and **resumable**:

- Re-running a step must not corrupt earlier outputs.
- A step skips work it has already completed (existence + content hash check).
- A `--force` flag re-does work explicitly.

Step files are numbered (`01_`, `02_`, ...) so the run order is obvious. Each script accepts `--config config/default.yaml` and a `--dry-run` flag.

## Data immutability

`data/raw/` is **never** modified after capture. If a re-capture is needed, write to a new path (e.g., suffix with capture date). Treat raw as a source of truth a co-author could audit five years from now.

`data/cleaned/`, `data/rewrites/`, and `data/scores/` are derivable from raw + code + locked config. Deleting them and rerunning the pipeline must reproduce identical files (modulo timestamp metadata).

## Provenance metadata

Every artifact records:

- Source content hash (SHA-256 of input)
- Code version (git SHA, or "dirty" if uncommitted)
- Timestamp (UTC, ISO 8601)
- Config hash (SHA-256 of the YAML used)

For LLM outputs additionally:

- Model name and exact version string from the API response
- Temperature, top_p, max_tokens, system prompt
- Prompt hash
- Token usage (input/output)
- Any safety/refusal flag

Tip: put a small `_provenance.json` next to every generated file. Future-you will thank present-you.

## LLM rewrite arm — non-negotiables

1. **One prompt, three models.** Same exact prompt string for every model. Prompt lives in `prompts/rewrite_v1.txt`. Prompt changes get a new version number; old data is *not* regenerated under the new prompt without a clear note in `docs/stats_deviations.md`.
2. **Lock model versions in config.** Use specific snapshot IDs where the API supports them. The locked panel for this run (`config/models.yaml`) is `claude-opus-4-8`, `gpt-5.5-2026-04-23`, and `gemini-3.1-pro-preview`. (The earlier placeholder panel `claude-opus-4-7` / `gpt-4o-2024-08-06` / `gemini-1.5-pro-002` was replaced; the change and its rationale are logged in `docs/stats_deviations.md`.)
3. **Lowest-variance sampling the API allows.** The goal is reproducibility, not creativity. Gemini still accepts and uses `temperature = 0`. The two reasoning models do **not**: Claude Opus 4.8 and GPT-5.5 reject a sampling `temperature` (HTTP 400), so `temperature` is omitted for those arms and recorded as null in provenance. GPT-5.5 additionally needs `max_completion_tokens` (not `max_tokens`) with the budget shared between reasoning and output, and uses `reasoning_effort = "low"`. All of this is in the deviations log.
4. **No streaming.** Collect the full response so token usage and finish reason are recorded.
5. **Retry policy.** Retry on transient errors (429, 5xx) with exponential backoff up to 5 attempts. Refusal is NOT a transient error — log it and move on.
6. **Cost guardrail.** The rewrite script prints an estimated cost before running and requires `--confirm-cost` to proceed at scale.

## Cleaning rules

Web pages are messy. The cleaning step must:

- Strip navigation, headers, footers, sidebars, ad blocks.
- Strip image captions and figure references (these inflate scores).
- Strip the reference list at the end of clinical articles.
- Strip "related links" and "see also" blocks.
- Preserve heading structure (use newlines, not markdown) — sentence segmentation needs paragraph breaks.
- Normalize whitespace (no tabs, no double spaces, single newline between paragraphs).
- Replace common typographic quirks (smart quotes, em dashes) with ASCII equivalents so `textstat` doesn't choke.

Use [trafilatura](https://trafilatura.readthedocs.io/) for the main extraction; it handles boilerplate stripping well. Run a custom sanitizer pass after.

Spot-check 10% of cleaned pages by eye against the raw HTML. Cleaning bugs are silent killers — a stray nav bar in 30 pages will shift every score.

## Readability scoring

Use `textstat` as the implementation. It implements all six formulas the field uses:

| Formula                                  | textstat function                  |
|------------------------------------------|------------------------------------|
| Flesch-Kincaid Reading Ease (FKRE)       | `flesch_reading_ease`              |
| Flesch-Kincaid Grade Level (FKGL)        | `flesch_kincaid_grade`             |
| Gunning-Fog Index (GFI)                  | `gunning_fog`                      |
| Simple Measure of Gobbledygook (SMOG)    | `smog_index`                       |
| Coleman-Liau Index (CLI)                 | `coleman_liau_index`               |
| Automated Readability Index (ARI)        | `automated_readability_index`      |

Record `textstat.__version__` with every score (the algorithms have shifted in past releases, so pin and record). For what each of the six formulas measures, a worked FKGL calculation, and how every downstream statistic is computed, see the plain-language `docs/methods_and_statistics_companion.md`.

**Sanity verification (mandatory):** pick 2–3 pages, compute scores by hand or via an independent online tool, and confirm agreement within ±0.5 grade level. Failures here usually mean cleaning is wrong, not that the formula is wrong.

## Blinding

Two-way blinding:

- The clinical reviewer never sees which model produced a rewrite during scoring.
- The data scientist never sees clinical scores during data preparation.

Mechanism: every rewrite is assigned a random `blind_id` at packet-build time. The mapping from `blind_id` → `(page_id, model)` lives in `data/scores/blind_key.csv`, which is NOT included in the review packet. After Naeem returns scored sheets keyed by `blind_id`, the data scientist joins on the key.

## Reproducibility checklist (run before any manuscript submission)

- [ ] Fresh clone + fresh venv builds clean.
- [ ] `pytest` passes.
- [ ] Running the full pipeline from `data/raw/` reproduces every number in the manuscript.
- [ ] Every figure has a script that generates it; no hand-edits in Illustrator.
- [ ] `requirements.lock` is committed and the lock hash matches the env hash recorded in the latest report.

## Code style

- Black + Ruff for Python.
- Type hints on every public function in `src/`.
- Docstrings only where the *why* is non-obvious. Don't doc what the code already says.
- No silent `except Exception: pass`. Either handle it or let it raise.
- All randomness must seed from a fixed value in config (e.g., `random_seed: 42`). This includes packet shuffling.

## Testing

`tests/` covers:

- Readability scorer reproduces known values for a fixed sample text.
- Cleaner strips known boilerplate from a fixture HTML file.
- Manifest builder rejects duplicate URLs.
- Blind packet builder produces a key that round-trips: unblinding recovers `(page_id, model)`.

Tests do NOT make real network calls or LLM calls. Mock those.

## What to put in git, what to keep out

In:
- All code in `src/`, `scripts/`, `tests/`.
- All docs in `docs/`.
- All config in `config/`, `prompts/`.
- All of `data/` (raw HTML, cleaned text, rewrites, scores, manifest, review packet). The project's `.gitignore` was set to **track `data/`** so the corpus and every derived artifact are auditable from the repository; the earlier guidance to gitignore `data/raw|cleaned|rewrites` no longer applies. Do not change `.gitignore`.
- `reports/` outputs that the manuscript cites, including the figures.
- `requirements.txt` and (when generated) `requirements.lock`.

Out (gitignored):
- `.venv/`
- `.env` (real credentials)
- `publication/` (the working manuscript and `build_docx.py` output live here and are kept local)
- `__pycache__/`, `.pytest_cache/`, `.ipynb_checkpoints/`, `.DS_Store`, editor dirs
- API response cache directories

When in doubt about copyright: the raw HTML is currently committed for reproducibility on a private remote; if the repository is ever made public, revisit whether raw HTML should be replaced by URLs + manifest only.
