# Rough Cost Estimates: AI Rewrite Arm

What it costs in USD to run **Phase 3 (AI rewrite generation)** of this project on the current corpus, using one of several frontier models. Useful before populating `.env` with paid API keys, and before flipping the `--confirm-cost` switch in `scripts/04_generate_rewrites.py`.

**Bottom line:** the entire 3-model rewrite arm on the current 21-page corpus is expected to land in the **USD $3–15 range** across all three providers combined, well under the `cost_warn_usd: 20` guardrail in `config/default.yaml`. The whole study is small (≈ 18k words of cleaned text); even at flagship-Opus prices the workload is sub-coffee-cup-money.

> **Prices below are best-effort list-price snapshots, not invoices.** Provider list prices change, verify the current per-MTok rate at each provider's pricing page before running. Each row links out.

## 1. Workload (computed from the current corpus, 2026-06-03)

These numbers come straight from `data/manifest.csv` and `prompts/rewrite_v1.txt`:

| Quantity | Value |
|---------------------------------------------------|----------------|
| Included pages (`include = Y`) | 21 |
| Total cleaned words | 17,580 |
| Min / median / max words per page | 252 / 713 / 3,153 |
| Prompt-template tokens per call (fixed overhead) | ~71 |
| Tokens-per-word heuristic used | 1 token ≈ 0.75 words |
| Mean input tokens per call | ~1,187 |
| Mean output tokens per call (same-length rewrite) | ~1,116 |
| **Total input tokens, 1 model × 21 pages** | **~24,900** |
| **Total output tokens, 1 model × 21 pages** | **~23,400** |
| **Total input tokens, 3 models × 21 pages** | **~74,800** |
| **Total output tokens, 3 models × 21 pages** | **~70,300** |

> The "tokens-per-word" heuristic is what every major provider publishes for English. Medical text trends 5–10% higher tokens-per-word due to drug names and Latinate terms, bake a +10% buffer into the totals if you want a worst-case figure.

Sensitivity: if the rewrites come back **30% longer** than the originals (the model adds plain-English definitions), output tokens rise to ~30,500 per model. If they come back **30% shorter** (the model compresses), output tokens drop to ~16,400 per model. Both regimes are folded into the high/low columns below.

The math you can paste into a spreadsheet:

```
cost_per_model_usd = (input_tokens / 1_000_000) * input_price_per_MTok
  + (output_tokens / 1_000_000) * output_price_per_MTok

For one model on the 21-page corpus, "mid" output assumption:
cost_per_model_usd ≈ 0.0249 * input_price + 0.0234 * output_price
```

## 2. Per-model list prices (as of writing, verify before run)

For each model the user asked about. Where a model is **not yet generally available** as of this writing, the row is marked **projected** and uses the most-recent published tier-equivalent pricing as a placeholder. Anyone running this study should overwrite the placeholder with the real pricing page.

| Model | Provider | Status | Input $ / MTok | Output $ / MTok | Verify at |
|----------------------|-----------|-----------------|----------------|-----------------|-----------|
| Claude Opus 4.7 | Anthropic | GA | $15.00 | $75.00 | [anthropic.com/pricing](https://www.anthropic.com/pricing) |
| Claude Opus 4.8 | Anthropic | **projected*** | $15.00 | $75.00 | [anthropic.com/pricing](https://www.anthropic.com/pricing) |
| ChatGPT 5.5 / GPT-5.5 | OpenAI | **projected*** | $12.50 | $50.00 | [openai.com/api/pricing](https://openai.com/api/pricing) |
| Gemini 3 Pro | Google | **projected*** | $1.25 | $10.00 | [ai.google.dev/pricing](https://ai.google.dev/pricing) |
| Gemini 3 Deep | Google | **projected*** | $5.00 | $30.00 | [ai.google.dev/pricing](https://ai.google.dev/pricing) |

*\*"projected" means the exact model name was not confirmed as a publicly available API endpoint at the time of writing. The placeholder price assumes the model lands in the same pricing tier as its current flagship sibling. If the real price differs, scale the per-model cost rows below linearly.*

Two general patterns the placeholders are based on:

- **Anthropic Opus tier** has historically held at $15 / $75 per MTok across the 3.x and 4.x families; this is a reasonable default for any unreleased Opus point version.
- **Google Gemini "Deep" / extended-reasoning tiers** have historically charged 2–6× the per-MTok rate of the same-generation Pro tier. The Gemini 3 Deep placeholder uses 4× the Pro placeholder.

## 3. Estimated total cost (per model, on current 21-page corpus)

Using the workload from §1 and the prices from §2. Three columns for the three output-length scenarios (compressed, same-length, expanded):

| Model | Compressed output | Same-length output | Expanded output |
|----------------------|------------------:|-------------------:|----------------:|
| Claude Opus 4.7 | $1.60 | $2.13 | $2.66 |
| Claude Opus 4.8 *(projected)* | $1.60 | $2.13 | $2.66 |
| ChatGPT 5.5 *(projected)* | $1.13 | $1.48 | $1.84 |
| Gemini 3 Pro *(projected)* | $0.19 | $0.27 | $0.34 |
| Gemini 3 Deep *(projected)* | $0.62 | $0.83 | $1.04 |

(Worked example for Opus 4.7, same-length: 0.0249 × $15 + 0.0234 × $75 = $0.374 + $1.755 = **$2.13**.)

## 4. Full 3-model arm cost (what `scripts/04_generate_rewrites.py` actually runs)

The locked model panel in `config/models.yaml` is Claude + GPT + Gemini. The estimates below assume the *same-length output* scenario from §3 and substitute different model combinations:

| Model panel | Estimated total |
|----------------------------------------------------------------------------|----------------:|
| **Locked panel** (Opus 4.7 + GPT-4o + Gemini 1.5 Pro from current config) | **~$4–6** |
| Opus 4.7 + ChatGPT 5.5 *(projected)* + Gemini 3 Pro *(projected)* | ~$3.88 |
| Opus 4.8 *(projected)* + ChatGPT 5.5 *(projected)* + Gemini 3 Pro *(projected)* | ~$3.88 |
| Opus 4.7 + ChatGPT 5.5 *(projected)* + Gemini 3 Deep *(projected)* | ~$4.44 |
| Opus 4.8 *(projected)* + ChatGPT 5.5 *(projected)* + Gemini 3 Deep *(projected)* | ~$4.44 |

If you want a worst-case headline: assume +10% for medical-jargon tokenization, +30% for expanded output, and 4× the corpus size if someone expands to ~80 pages. The 3-model arm on 80 pages with the most expensive combo (Opus + ChatGPT 5.5 + Gemini 3 Deep) lands around **$24**. Still under any reasonable research budget, but at that point you do want batch-API discounts (next section).

## 5. Discount paths that meaningfully change the number

- **Batch / async APIs**, Anthropic's Message Batches API and OpenAI's Batch API both run at roughly **50% off list price** with a 24-hour SLA. For a research pipeline like this (no latency requirement; you press go and walk away), batch mode roughly halves the totals above. Google's batch / "long-running" generation discount varies. The current code paths in `scripts/04_generate_rewrites.py` use the synchronous API; modifying it to batch is a small change worth doing if a future run scales the corpus.
- **Prompt caching**, Anthropic caches input prompt prefixes at a discount (~10% of the input rate after the first call). Because every page in this study sends a *different* `ORIGINAL_TEXT`, only the ~71-token prompt header benefits from caching, which is negligible. Not a meaningful lever for this study.
- **Free tiers**, Google Gemini's API offers a free tier with rate limits that would cover the whole 21-page corpus in a few hours of throttled traffic. Suitable for a sanity-check run before paying for the full arm.

## 6. When to re-run this estimate

This document goes stale when **any** of these change:

1. **Provider list prices** change (re-check the three pricing pages in §2).
2. **The corpus grows** (e.g., if the 5 blocked Hopkins/Mayo pages get manually recaptured, n goes from 21 to 26 → multiply §3 column by 26/21 ≈ 1.24).
3. **The locked model panel** in `config/models.yaml` changes (a new model with new prices).
4. **The prompt** in `prompts/rewrite_v1.txt` grows substantially (currently 71 tokens of overhead, large changes here would shift the input-token totals).

To regenerate the workload numbers in §1 deterministically, run the script block at the top of this file's git history (the Python in the commit that introduced this doc) against the current `data/manifest.csv`. The math in §3 is purely linear in the per-MTok prices, so updating just §2 lets you recompute §3 in a spreadsheet without re-running anything.

## 7. Cost-related guardrails already in the code

- `config/default.yaml` sets `cost_warn_usd: 20`. If `scripts/04_generate_rewrites.py` estimates the run will exceed $20, it refuses to run without the explicit `--confirm-cost` flag. Adjust the threshold by editing the config (and committing).
- The script's `--dry-run` mode prints the estimate without making any API calls. Always run `--dry-run` first.
- Every rewrite written to `data/rewrites/<page_id>__<model_id>.txt` is accompanied by a `_provenance.json` that records exact token usage as returned by the API, so the actual spend can be reconciled against the estimate after the fact.
