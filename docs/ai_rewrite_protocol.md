# AI Rewrite Protocol

How the three chatbots are run to produce rewrites for Aim 2 and Aim 3. Lock the prompt, model versions, and parameters before any rewrite is generated. Any change starts a new prompt version and is logged.

## The locked prompt (version 1)

Stored in `prompts/rewrite_v1.txt`. Use verbatim — no per-page tweaks, no per-model tweaks.

```
Rewrite the following patient education text at a 6th-grade reading level.
Keep all medical facts accurate. Do not add new medical claims. Do not remove
important safety or preparation information. Use plain words and short
sentences.

ORIGINAL TEXT:
<<<
{ORIGINAL_TEXT}
>>>

Provide only the rewritten text. Do not add headings, summaries, disclaimers,
or commentary.
```

The `{ORIGINAL_TEXT}` placeholder is filled in by the script. The triple-angle-bracket fences make the boundary unambiguous.

## Locked model versions

In `config/models.yaml`:

```yaml
models:
  - id: claude
    provider: anthropic
    model: claude-opus-4-7
    temperature: 0
    max_tokens: 8192

  - id: openai
    provider: openai
    model: gpt-4o-2024-08-06
    temperature: 0
    max_tokens: 8192

  - id: gemini
    provider: google
    model: gemini-1.5-pro-002
    temperature: 0
    max_output_tokens: 8192
```

Lock with a git commit before any rewrite runs. Subsequent re-runs with newer model snapshots are a different study.

## Run mechanics

For each `(page_id, model_id)` pair:

1. Read cleaned text from `data/cleaned/<page_id>.txt`.
2. Format the prompt by substituting `{ORIGINAL_TEXT}`.
3. Call the provider API with the locked temperature and the same system prompt (empty / default).
4. Capture the full response — text body, model version string returned by the API, token usage, finish reason.
5. Write rewrite to `data/rewrites/<page_id>__<model_id>.txt`.
6. Write provenance to `data/rewrites/<page_id>__<model_id>.provenance.json` with: model_id, model_returned_by_api, prompt_version, prompt_sha256, generated_at_utc, input_tokens, output_tokens, finish_reason, temperature, max_tokens, refusal_flag (bool), refusal_text (if any).

## Reproducibility safeguards

- Temperature = 0 across all three providers.
- Top-p / top-k left at provider defaults (record them, but the temperature-0 setting dominates).
- No streaming.
- Re-running for a `(page_id, model_id)` pair that already has a non-refused output is a no-op unless `--force` is passed.

## Refusal handling

If a model refuses (declines to rewrite, returns a safety message, or returns an empty body):

- Record `refusal_flag = true` and the refusal text in the provenance file.
- Do NOT retry with a softer prompt or strip-down the input. That would corrupt the comparison.
- Note in the manifest that this rewrite is missing.

Refusals on patient-education text are unlikely with the locked prompt, but the safeguard exists in case a page contains content (e.g., medication dosing) that triggers safety filters.

## Cost guardrail

Before running at scale, the script prints:

- Number of pages × number of models = total calls.
- Estimated input tokens (sum of cleaned word counts × ~1.3).
- Estimated output tokens (assume ≤ input).
- Estimated USD cost per provider (from a small price table in the script — update before each run; pricing changes).

Run requires `--confirm-cost` to proceed if estimated total exceeds $20.

## Spot check

After generating one rewrite per model on the first page, stop and have a human eyeball the output for sanity:

- Does it read like a 6th-grader could understand it?
- Did it preserve the key medical points?
- Is the length sensible (not 3 sentences, not 5x the original)?

Then proceed with the rest.

## Output and analysis hand-off

After all rewrites are generated:

1. Run the readability scorer on every rewrite → `data/scores/rewrites.csv`.
2. Compute per-page per-model deltas vs originals → `data/scores/deltas.csv`.
3. Build blinded review packets for Phase 4 → `data/review/`.
4. Hand the packets to Naeem.
