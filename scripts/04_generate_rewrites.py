#!/usr/bin/env python3
"""Generate AI rewrites for every included page × every model in config/models.yaml.

Requires API keys in `.env`:
  ANTHROPIC_API_KEY, OPENAI_API_KEY, GOOGLE_API_KEY.

Cost guardrail: estimates input/output tokens, prints estimated cost, and
requires --confirm-cost if estimate exceeds `cost_warn_usd` in default.yaml.
"""

from __future__ import annotations

import argparse
import csv
import logging
import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from src.ai_rewrite import build_rewriter, generate_one  # noqa: E402
from src.config import (  # noqa: E402
    CLEANED_DIR,
    CONFIG_DIR,
    MANIFEST_PATH,
    PROMPTS_DIR,
    REWRITES_DIR,
    ensure_dirs,
    load_config,
)

log = logging.getLogger("rewrite")

# Rough per-1k-token USD pricing for the cost guardrail only. Approximate list
# prices for the locked panel (Opus 4.8, GPT-5.5, Gemini 3.5 Flash); the true
# cost is computed from per-call token counts in each rewrite's provenance JSON.
PRICE_PER_1K_INPUT_USD = {
    "claude": 0.005,
    "openai": 0.00125,
    "gemini": 0.0003,
}
PRICE_PER_1K_OUTPUT_USD = {
    "claude": 0.025,
    "openai": 0.010,
    "gemini": 0.0025,
}


def estimate_cost(
    cleaned_texts: list[tuple[str, str]],
    models: list[dict],
) -> tuple[float, dict]:
    """Estimate total USD cost. Assumes output tokens <= input tokens."""
    total = 0.0
    per_model = {}
    for m in models:
        mid = m["id"]
        total_in_tokens = sum(int(len(t.split()) * 1.3) for _, t in cleaned_texts)
        # Assume output ~= input length (conservative)
        total_out_tokens = total_in_tokens
        cost = (
            (total_in_tokens / 1000) * PRICE_PER_1K_INPUT_USD.get(mid, 0)
            + (total_out_tokens / 1000) * PRICE_PER_1K_OUTPUT_USD.get(mid, 0)
        )
        per_model[mid] = round(cost, 2)
        total += cost
    return round(total, 2), per_model


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--models", default=str(CONFIG_DIR / "models.yaml"))
    parser.add_argument("--config", default=None)
    parser.add_argument("--only-model", default=None, help="Limit to one model_id (claude/openai/gemini)")
    parser.add_argument("--only-page", default=None, help="Limit to one page_id (for spot-checking)")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--confirm-cost", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    ensure_dirs()
    cfg = load_config(args.config)
    prompt_path = REPO_ROOT / cfg.get("prompt_path", default="prompts/rewrite_v1.txt")
    prompt_template = prompt_path.read_text(encoding="utf-8")

    with open(args.models, "r", encoding="utf-8") as f:
        model_specs = yaml.safe_load(f)["models"]
    if args.only_model:
        model_specs = [m for m in model_specs if m["id"] == args.only_model]
        if not model_specs:
            log.error("no model in config matches --only-model %s", args.only_model)
            return 2

    with MANIFEST_PATH.open("r", encoding="utf-8") as f:
        manifest = list(csv.DictReader(f))
    included = [r for r in manifest if r.get("include", "").upper() == "Y"]
    if args.only_page:
        included = [r for r in included if r["page_id"] == args.only_page]
        if not included:
            log.error("page %s not found or not included", args.only_page)
            return 2

    cleaned: list[tuple[str, str]] = []
    for r in included:
        pid = r["page_id"]
        path = CLEANED_DIR / f"{pid}.txt"
        if not path.exists():
            log.warning("cleaned text missing for %s — skipping", pid)
            continue
        cleaned.append((pid, path.read_text(encoding="utf-8")))

    total_cost, per_model = estimate_cost(cleaned, model_specs)
    cost_warn = float(cfg.get("cost_warn_usd", default=20))
    log.info("estimated cost: $%.2f total, per-model %s", total_cost, per_model)
    if total_cost > cost_warn and not args.confirm_cost:
        log.error("estimated cost ($%.2f) exceeds warn threshold ($%.2f). Rerun with --confirm-cost.",
                  total_cost, cost_warn)
        return 3

    if args.dry_run:
        log.info("[dry-run] would generate %d rewrites", len(cleaned) * len(model_specs))
        return 0

    rewriters = []
    for spec in model_specs:
        try:
            rewriters.append(build_rewriter(spec))
        except Exception as exc:
            log.error("failed to build rewriter for %s: %s", spec["id"], exc)

    successes = 0
    refusals = 0
    failures = 0
    for pid, text in cleaned:
        for r in rewriters:
            try:
                result = generate_one(
                    rewriter=r,
                    page_id=pid,
                    cleaned_text=text,
                    prompt_template=prompt_template,
                    rewrites_dir=REWRITES_DIR,
                    force=args.force,
                )
                if result.refusal:
                    refusals += 1
                    log.warning("REFUSAL %s by %s", pid, r.model_id)
                else:
                    successes += 1
                    log.info("rewrote %s with %s (%.1fs)", pid, r.model_id, result.elapsed_seconds)
            except Exception as exc:
                failures += 1
                log.exception("failed %s × %s: %s", pid, r.model_id, exc)

    log.info("rewrite arm: %d successes, %d refusals, %d failures", successes, refusals, failures)
    return 0


if __name__ == "__main__":
    sys.exit(main())
