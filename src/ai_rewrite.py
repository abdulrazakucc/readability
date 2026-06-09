"""LLM rewrite arm — three providers, one locked prompt, temperature 0.

Per `docs/ai_rewrite_protocol.md`:
- Lock model versions in config (`config/models.yaml`).
- Lock the prompt in `prompts/rewrite_v1.txt`.
- Record provenance for every call (model, version returned by API, tokens, finish reason).
- Refusals are surfaced, not retried with a softer prompt.

The provider client classes here are thin wrappers around the official SDKs so
the orchestrator (`scripts/04_generate_rewrites.py`) does not care which model
is being called.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from .config import get_api_key
from .provenance import sha256_text, utc_now_iso, write_provenance

log = logging.getLogger(__name__)

REWRITE_PROMPT_VERSION = "v1"


@dataclass
class RewriteResult:
    page_id: str
    model_id: str
    rewrite_path: Path
    provenance_path: Path
    text: str
    model_returned: str
    input_tokens: int | None
    output_tokens: int | None
    finish_reason: str | None
    refusal: bool
    refusal_text: str | None
    elapsed_seconds: float


class Rewriter(Protocol):
    model_id: str
    provider: str
    model: str
    temperature: float
    max_tokens: int

    def rewrite(self, prompt: str) -> dict[str, Any]: ...


# --- Provider implementations ----------------------------------------------

class AnthropicRewriter:
    def __init__(self, spec: dict[str, Any]):
        from anthropic import Anthropic
        self.model_id = spec["id"]
        self.provider = "anthropic"
        self.model = spec["model"]
        self.max_tokens = spec.get("max_tokens", 8192)
        # Opus 4.7/4.8 removed sampling params: sending `temperature` 400s.
        # Omit `temperature` from the config to run on those models.
        self.temperature = spec.get("temperature")
        self.reasoning_effort = None
        self._client = Anthropic(api_key=get_api_key("anthropic"))

    def rewrite(self, prompt: str) -> dict[str, Any]:
        kwargs: dict[str, Any] = dict(
            model=self.model,
            max_tokens=self.max_tokens,
            messages=[{"role": "user", "content": prompt}],
        )
        if self.temperature is not None:
            kwargs["temperature"] = self.temperature
        resp = self._client.messages.create(**kwargs)
        body = "".join(block.text for block in resp.content if getattr(block, "type", "") == "text")
        return {
            "text": body,
            "model_returned": getattr(resp, "model", self.model),
            "input_tokens": getattr(resp.usage, "input_tokens", None),
            "output_tokens": getattr(resp.usage, "output_tokens", None),
            "finish_reason": getattr(resp, "stop_reason", None),
        }


class OpenAIRewriter:
    def __init__(self, spec: dict[str, Any]):
        from openai import OpenAI
        self.model_id = spec["id"]
        self.provider = "openai"
        self.model = spec["model"]
        # GPT-5.x reasoning models require `max_completion_tokens` (not `max_tokens`)
        # and reject non-default `temperature`. Budget covers reasoning + output.
        self.max_tokens = spec.get("max_completion_tokens", spec.get("max_tokens", 16000))
        self.temperature = spec.get("temperature")
        self.reasoning_effort = spec.get("reasoning_effort")
        self._client = OpenAI(api_key=get_api_key("openai"))

    def rewrite(self, prompt: str) -> dict[str, Any]:
        kwargs: dict[str, Any] = dict(
            model=self.model,
            max_completion_tokens=self.max_tokens,
            messages=[{"role": "user", "content": prompt}],
        )
        if self.temperature is not None:
            kwargs["temperature"] = self.temperature
        if self.reasoning_effort:
            kwargs["reasoning_effort"] = self.reasoning_effort
        resp = self._client.chat.completions.create(**kwargs)
        choice = resp.choices[0]
        return {
            "text": choice.message.content or "",
            "model_returned": getattr(resp, "model", self.model),
            "input_tokens": getattr(resp.usage, "prompt_tokens", None),
            "output_tokens": getattr(resp.usage, "completion_tokens", None),
            "finish_reason": getattr(choice, "finish_reason", None),
        }


def _gemini_text(resp: Any) -> str:
    """Extract text without tripping the `.text` accessor, which raises when a
    candidate returns no text part (e.g. truncated by a thinking budget)."""
    try:
        return resp.text or ""
    except (ValueError, AttributeError):
        pass
    parts: list[str] = []
    for cand in getattr(resp, "candidates", []) or []:
        content = getattr(cand, "content", None)
        for part in getattr(content, "parts", []) or []:
            t = getattr(part, "text", "")
            if t:
                parts.append(t)
    return "".join(parts)


class GoogleRewriter:
    def __init__(self, spec: dict[str, Any]):
        import google.generativeai as genai
        genai.configure(api_key=get_api_key("google"))
        self.model_id = spec["id"]
        self.provider = "google"
        self.model = spec["model"]
        self.max_tokens = spec.get("max_tokens", spec.get("max_output_tokens", 8192))
        self.temperature = spec.get("temperature")
        self.reasoning_effort = None
        self._model = genai.GenerativeModel(self.model)

    def rewrite(self, prompt: str) -> dict[str, Any]:
        cfg: dict[str, Any] = {"max_output_tokens": self.max_tokens}
        if self.temperature is not None:
            cfg["temperature"] = self.temperature
        resp = self._model.generate_content(prompt, generation_config=cfg)
        usage = getattr(resp, "usage_metadata", None)
        return {
            "text": _gemini_text(resp),
            "model_returned": self.model,
            "input_tokens": getattr(usage, "prompt_token_count", None) if usage else None,
            "output_tokens": getattr(usage, "candidates_token_count", None) if usage else None,
            "finish_reason": str(getattr(resp.candidates[0], "finish_reason", "")) if resp.candidates else None,
        }


PROVIDER_CLASSES = {
    "anthropic": AnthropicRewriter,
    "openai": OpenAIRewriter,
    "google": GoogleRewriter,
}


def build_rewriter(spec: dict[str, Any]) -> Rewriter:
    provider = spec["provider"]
    cls = PROVIDER_CLASSES[provider]
    return cls(spec)


# --- Orchestration ---------------------------------------------------------

REFUSAL_MARKERS = [
    "i can't help with",
    "i cannot provide",
    "i'm not able to",
    "i am unable to",
    "as an ai language model",
    "i won't",
]


def looks_like_refusal(text: str) -> bool:
    low = text.lower()
    return any(marker in low for marker in REFUSAL_MARKERS) and len(text) < 600


def fill_prompt(prompt_template: str, original_text: str) -> str:
    return prompt_template.replace("{ORIGINAL_TEXT}", original_text)


def generate_one(
    rewriter: Rewriter,
    page_id: str,
    cleaned_text: str,
    prompt_template: str,
    rewrites_dir: Path,
    force: bool = False,
    max_retries: int = 5,
    backoff_base: float = 2.0,
) -> RewriteResult:
    rewrite_path = rewrites_dir / f"{page_id}__{rewriter.model_id}.txt"
    prov_path = rewrites_dir / f"{page_id}__{rewriter.model_id}.provenance.json"

    if rewrite_path.exists() and prov_path.exists() and not force:
        text = rewrite_path.read_text(encoding="utf-8")
        return RewriteResult(
            page_id=page_id,
            model_id=rewriter.model_id,
            rewrite_path=rewrite_path,
            provenance_path=prov_path,
            text=text,
            model_returned="(cached)",
            input_tokens=None,
            output_tokens=None,
            finish_reason="cached",
            refusal=False,
            refusal_text=None,
            elapsed_seconds=0.0,
        )

    prompt = fill_prompt(prompt_template, cleaned_text)
    prompt_sha = sha256_text(prompt_template)

    last_err: Exception | None = None
    for attempt in range(max_retries):
        try:
            t0 = time.time()
            out = rewriter.rewrite(prompt)
            elapsed = time.time() - t0
            break
        except Exception as exc:
            last_err = exc
            wait = backoff_base ** attempt
            log.warning("rewrite call failed (attempt %d/%d): %s — retrying in %.1fs",
                        attempt + 1, max_retries, exc, wait)
            time.sleep(wait)
    else:
        raise RuntimeError(f"Rewriter failed after {max_retries} attempts: {last_err}")

    text = out["text"]
    refusal = looks_like_refusal(text)

    rewrite_path.write_text(text, encoding="utf-8")
    write_provenance(
        prov_path,
        {
            "page_id": page_id,
            "model_id": rewriter.model_id,
            "provider": rewriter.provider,
            "model_requested": rewriter.model,
            "model_returned": out["model_returned"],
            "prompt_version": REWRITE_PROMPT_VERSION,
            "prompt_sha256": prompt_sha,
            "temperature": rewriter.temperature,
            "reasoning_effort": getattr(rewriter, "reasoning_effort", None),
            "max_tokens": rewriter.max_tokens,
            "generated_at_utc": utc_now_iso(),
            "input_tokens": out["input_tokens"],
            "output_tokens": out["output_tokens"],
            "finish_reason": out["finish_reason"],
            "refusal_flag": refusal,
            "refusal_text": text if refusal else None,
            "elapsed_seconds": round(elapsed, 2),
        },
    )

    return RewriteResult(
        page_id=page_id,
        model_id=rewriter.model_id,
        rewrite_path=rewrite_path,
        provenance_path=prov_path,
        text=text,
        model_returned=out["model_returned"],
        input_tokens=out["input_tokens"],
        output_tokens=out["output_tokens"],
        finish_reason=out["finish_reason"],
        refusal=refusal,
        refusal_text=text if refusal else None,
        elapsed_seconds=round(elapsed, 2),
    )
