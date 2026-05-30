"""
Generation Backend Registry

A tiny registry so backends are interchangeable. The default backend is the
deterministic :class:`TemplateBackend`; a heavier local model can be registered
at runtime under the same interface and selected as default without touching
callers.
"""

from __future__ import annotations

from core.generation.backend import GenerationBackend
from core.generation.template_backend import TemplateBackend

_REGISTRY: dict[str, GenerationBackend] = {}
_DEFAULT_NAME: str = "template"


def register_backend(backend: GenerationBackend, *, make_default: bool = False) -> None:
    """Register a backend instance under its ``name``."""
    if not getattr(backend, "name", ""):
        raise ValueError("Backend must define a non-empty 'name'.")
    _REGISTRY[backend.name] = backend
    if make_default:
        set_default_backend(backend.name)


def set_default_backend(name: str) -> None:
    """Choose which registered backend ``get_backend()`` returns by default."""
    if name not in _REGISTRY:
        raise KeyError(f"Unknown generation backend: {name!r}")
    global _DEFAULT_NAME
    _DEFAULT_NAME = name


def get_backend(name: str | None = None) -> GenerationBackend:
    """Return a backend by name, or the current default.

    Falls back to the always-available template backend if the requested (or
    default) backend is unavailable in this environment.
    """
    chosen = name or _DEFAULT_NAME
    backend = _REGISTRY.get(chosen)
    if backend is None or not backend.available:
        return _REGISTRY["template"]
    return backend


def available_backends() -> list[str]:
    """Names of registered backends that can run in this environment."""
    return [n for n, b in _REGISTRY.items() if b.available]


# Register the built-in default eagerly so the package is usable on import.
register_backend(TemplateBackend(), make_default=True)
