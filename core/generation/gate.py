"""
Generation Gate

The confidence gate that keeps the *decision engine* in charge. Enrichment via a
generation backend runs **only** when this gate says so — high-confidence,
specific answers (e.g. a calculator result) are delivered verbatim, while low
specificity / low confidence answers are the ones smoothed into more natural
language.

This mirrors the plan's requirement: "fluent answers when needed, deterministic
answers when high-confidence — fluency *without* losing transparency."
"""

from __future__ import annotations

from core.generation.backend import GenerationRequest, GenerationResult
from core.generation.registry import get_backend


def _config() -> dict:
    try:
        from runtime.config.config import GENERATION as _G
        return _G
    except Exception:
        return {}


def should_generate(tier: str, confidence: float) -> bool:
    """Decide whether to enrich a response with the generation backend.

    Rules (configurable via the GENERATION config block):
      - Disabled globally → never generate.
      - Very high confidence specific (SS) answers are delivered verbatim.
      - Tiers listed in ``enrich_tiers`` are eligible for enrichment.
      - Confidence at/above ``skip_above_confidence`` skips enrichment so exact
        answers are never reworded.
    """
    cfg = _config()
    if not cfg.get("enabled", True):
        return False

    skip_above = cfg.get("skip_above_confidence", 0.85)
    if confidence >= skip_above:
        return False

    enrich_tiers = cfg.get("enrich_tiers", ["GS", "SG", "GG"])
    return tier in enrich_tiers


def generate(request: GenerationRequest, backend: str | None = None) -> GenerationResult:
    """Run the selected (or default) backend on a request.

    This is a thin, safe wrapper: any backend failure degrades to returning the
    original deterministic answer rather than raising into the pipeline.
    """
    chosen = get_backend(backend)
    try:
        return chosen.generate(request)
    except Exception as exc:  # never let generation break the response path
        return GenerationResult(
            text=(request.answer or "").strip(),
            backend=chosen.name,
            enriched=False,
            confidence=request.confidence,
            metadata={"error": str(exc)},
        )
