"""
Tests for the Phase 1 pluggable generation layer (core/generation/).
"""

import pytest

from core.generation import (
    GenerationRequest,
    GenerationResult,
    TemplateBackend,
    available_backends,
    generate,
    get_backend,
    register_backend,
    set_default_backend,
    should_generate,
)
from core.generation.backend import GenerationBackend


class TestTemplateBackend:
    def test_enriches_gs(self):
        b = TemplateBackend()
        r = b.generate(GenerationRequest(query="tell me about france",
                                         answer="Paris is the capital", tier="GS"))
        assert r.backend == "template"
        assert "Paris is the capital" in r.text
        assert r.text.endswith(".")
        assert r.enriched

    def test_ss_passthrough_adds_only_punctuation(self):
        b = TemplateBackend()
        r = b.generate(GenerationRequest(query="2+2", answer="4", tier="SS"))
        assert r.text == "4."

    def test_empty_answer_handled(self):
        b = TemplateBackend()
        r = b.generate(GenerationRequest(query="x", answer="", tier="GG"))
        assert not r.enriched
        assert r.text

    def test_deterministic(self):
        b = TemplateBackend()
        req = GenerationRequest(query="q", answer="some answer", tier="GG")
        assert b.generate(req).text == b.generate(req).text


class TestRegistry:
    def test_default_is_template(self):
        assert get_backend().name == "template"

    def test_register_and_select(self):
        class DummyBackend(GenerationBackend):
            name = "dummy"

            def generate(self, request):
                return GenerationResult(text="dummy", backend=self.name)

        register_backend(DummyBackend())
        assert "dummy" in available_backends()
        assert get_backend("dummy").name == "dummy"
        set_default_backend("dummy")
        assert get_backend().name == "dummy"
        # Reset to template so other tests are unaffected.
        set_default_backend("template")

    def test_unavailable_backend_falls_back(self):
        class BrokenBackend(GenerationBackend):
            name = "broken"

            @property
            def available(self):
                return False

            def generate(self, request):
                return GenerationResult(text="x", backend=self.name)

        register_backend(BrokenBackend())
        # Requesting an unavailable backend falls back to template.
        assert get_backend("broken").name == "template"


class TestGate:
    def test_high_confidence_skips(self):
        assert should_generate("SS", 0.95) is False

    def test_low_confidence_general_enriches(self):
        assert should_generate("GG", 0.4) is True
        assert should_generate("GS", 0.5) is True

    def test_ss_tier_not_enriched_by_default(self):
        assert should_generate("SS", 0.5) is False

    def test_generate_wrapper(self):
        res = generate(GenerationRequest(query="q", answer="hello world", tier="GG"))
        assert isinstance(res, GenerationResult)
        assert "hello world" in res.text

    def test_generate_never_raises(self):
        class ExplodingBackend(GenerationBackend):
            name = "boom"

            def generate(self, request):
                raise RuntimeError("kaboom")

        register_backend(ExplodingBackend())
        res = generate(GenerationRequest(query="q", answer="safe answer"),
                       backend="boom")
        # Falls back to the deterministic answer instead of raising.
        assert res.text == "safe answer"
        assert "error" in res.metadata
