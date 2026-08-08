# Cost Estimates: AI Rewrites

What it costs to run Phase 3 (AI rewrites) on the 21-page corpus.

## Bottom line

**Total cost for all 3 models: about $4 to $6.** The safety cap in `config/default.yaml` is $20.

## What we are sending to each model

| Item | Amount |
|---|---|
| Pages | 21 |
| Words total | ~17,600 |
| Input tokens (per model) | ~25,000 |
| Output tokens (per model) | ~23,000 |

A "token" is roughly 3/4 of a word. So 1,000 words is about 750 tokens.

## Price per model

| Model | Input price (per 1M tokens) | Output price (per 1M tokens) | Cost for 21 pages |
|---|---:|---:|---:|
| Claude Opus 4.7 | $15 | $75 | ~$2.13 |
| ChatGPT 5.5 *(projected)* | $12.50 | $50 | ~$1.48 |
| Gemini 3 Pro *(projected)* | $1.25 | $10 | ~$0.27 |
| Gemini 3 Deep *(projected)* | $5 | $30 | ~$0.83 |

*"Projected" means the price is a best guess based on similar models. Check the provider's pricing page before running.*

## How the cost is calculated

```
cost = (input_tokens / 1,000,000) x input_price
     + (output_tokens / 1,000,000) x output_price
```

**Example for Claude Opus 4.7:**

```
input cost  = (25,000 / 1,000,000) x $15 = $0.375
output cost = (23,000 / 1,000,000) x $75 = $1.725
total       = $2.10
```

## All 3 models together

Claude + ChatGPT + Gemini on 21 pages: **about $4 to $6.**

Worst case (longer outputs, bigger corpus): about **$24.**

## Ways to spend less

1. **Batch APIs**: Anthropic and OpenAI cut prices by ~50% if you can wait 24 hours.
2. **Gemini free tier**: covers all 21 pages, slow but free. Good for testing.
3. Prompt caching does not help here, because each page sends different text.

## Safety nets in the code

- `config/default.yaml` has `cost_warn_usd: 20`. The script stops if the estimate goes higher.
- `--dry-run` shows the estimate without calling any APIs. Always run it first.
- Each rewrite saves a `_provenance.json` with the real token count from the API.

## When to update this estimate

- Provider prices change
- Corpus grows (example: 42 pages would double the cost)
- Models in `config/models.yaml` change
- The prompt template changes a lot
