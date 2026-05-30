"""
Quarky Pluggable Generation Layer (Phase 1)

The biggest gap for a zero-LLM assistant is *fluent* response generation. This
package introduces a clean adapter boundary so a local generation backend can be
plugged in **without** changing the rest of the pipeline and **without** taking
control away from the decision engine.

Key principles (from the upgrade plan):
  - The rule/token-value engine stays the authority. Generation is an *optional*
    enhancement that runs only when the confidence gate asks for it.
  - Backends are interchangeable via a registry. The default backend is a
    deterministic, dependency-free template backend — so the system works fully
    offline with zero extra installs. A heavier local model can be registered
    later behind the same interface.
  - Selecting a backend never bypasses gating: ``should_generate()`` decides,
    based on the specificity tier / confidence, whether to enrich at all.

Public API::

    from core.generation import GenerationRequest, generate, should_generate

    if should_generate(tier="GG", confidence=0.4):
        result = generate(GenerationRequest(query=q, answer=a, tier="GG"))
"""

from core.generation.backend import (
    GenerationBackend,
    GenerationRequest,
    GenerationResult,
)
from core.generation.template_backend import TemplateBackend
from core.generation.registry import (
    available_backends,
    get_backend,
    register_backend,
    set_default_backend,
)
from core.generation.gate import generate, should_generate

__all__ = [
    "GenerationBackend",
    "GenerationRequest",
    "GenerationResult",
    "TemplateBackend",
    "available_backends",
    "get_backend",
    "register_backend",
    "set_default_backend",
    "generate",
    "should_generate",
]
