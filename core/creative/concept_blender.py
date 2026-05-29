"""
Creative Brain: Concept Blender (v2)

Cross-domain conceptual blending using knowledge graph and embeddings.
Takes concepts from different domains and finds unexpected connections.

The creative brain's "innovation engine": blends ideas from unrelated
fields to generate novel insights.

Design philosophy: Absorb → Learn → Understand → Create OWN answers.
"""

import random
from dataclasses import dataclass, field
from typing import Any

from runtime.infrastructure.base import Department, BrainInput
from core.nlp.embeddings import text_similarity


@dataclass
class Blend:
    """A single conceptual blend between two domains."""
    concept_a: str
    concept_b: str
    bridge: str              # the connecting idea
    insight: str             # the generated insight
    novelty: float = 0.5    # 0-1 how novel the blend is


@dataclass
class BlendResult:
    """Output from the concept blender."""
    blends: list[Blend] = field(default_factory=list)
    best_blend: Blend | None = None


# Cross-domain bridge patterns: (domain_a, domain_b) → bridge concepts
_DOMAIN_BRIDGES: dict[tuple[str, str], list[str]] = {
    ("technology", "nature"): ["network", "evolution", "adaptation", "growth", "ecosystem"],
    ("technology", "art"): ["design", "craft", "expression", "pattern", "vision"],
    ("nature", "music"): ["rhythm", "harmony", "pattern", "flow", "resonance"],
    ("science", "philosophy"): ["truth", "observation", "model", "uncertainty", "meaning"],
    ("math", "art"): ["symmetry", "proportion", "pattern", "beauty", "structure"],
    ("psychology", "technology"): ["interface", "attention", "habit", "feedback", "learning"],
}

# Domain classification hints
_DOMAIN_KEYWORDS: dict[str, set[str]] = {
    "technology": {"computer", "code", "software", "hardware", "internet", "ai", "robot", "data", "digital", "app"},
    "nature": {"water", "fire", "tree", "ocean", "mountain", "animal", "plant", "earth", "sky", "forest"},
    "art": {"art", "music", "paint", "draw", "create", "design", "beauty", "aesthetic", "craft", "sculpture"},
    "science": {"physics", "chemistry", "biology", "experiment", "theory", "atom", "energy", "force"},
    "math": {"number", "equation", "calculate", "algebra", "geometry", "pattern", "proof", "formula"},
    "philosophy": {"meaning", "truth", "existence", "mind", "consciousness", "ethics", "logic", "wisdom"},
    "psychology": {"mind", "emotion", "behavior", "memory", "attention", "perception", "habit", "motivation"},
}

# Insight templates
_BLEND_TEMPLATES = [
    "Just as {a} involves {bridge}, {b} works the same way — through {bridge}.",
    "The connection between {a} and {b}? Both rely on {bridge}.",
    "If you think about {a} as a form of {bridge}, then {b} is its natural counterpart.",
    "What {a} and {b} share is {bridge} — the principle that ties them together.",
    "{a} and {b} seem unrelated, but they're both expressions of {bridge}.",
]


class ConceptBlender(Department):
    """
    Cross-domain conceptual blending.
    Finds unexpected connections between ideas from different fields.
    """

    def __init__(self):
        super().__init__("concept_blender", "core.creative")
        self._memory_manager = None

    def set_memory(self, memory_manager: Any) -> None:
        """Inject memory for graph-based blending."""
        self._memory_manager = memory_manager

    def process(self, data: Any) -> Any:
        if not isinstance(data, BrainInput):
            return data

        keywords = data.keywords or data.tokens[:5]
        blend_result = self.blend(keywords)
        data.context["blend_result"] = blend_result
        return data

    def blend(self, keywords: list[str]) -> BlendResult:
        """Find cross-domain blends for the given keywords."""
        # Classify keywords into domains
        domain_map: dict[str, list[str]] = {}
        for kw in keywords:
            domain = self._classify_domain(kw)
            domain_map.setdefault(domain, []).append(kw)

        blends: list[Blend] = []

        # Try to blend across detected domains
        domains = list(domain_map.keys())
        for i in range(len(domains)):
            for j in range(i + 1, len(domains)):
                d_a, d_b = domains[i], domains[j]
                kw_a = domain_map[d_a][0]
                kw_b = domain_map[d_b][0]
                blend = self._create_blend(kw_a, kw_b, d_a, d_b)
                if blend:
                    blends.append(blend)

        # If only one domain, blend within it using similarity
        if len(domains) <= 1 and len(keywords) >= 2:
            blend = self._create_within_domain_blend(keywords)
            if blend:
                blends.append(blend)

        # Graph-backed blending if memory available
        if self._memory_manager and keywords:
            graph_blend = self._graph_blend(keywords[0])
            if graph_blend:
                blends.append(graph_blend)

        best = max(blends, key=lambda b: b.novelty) if blends else None
        return BlendResult(blends=blends, best_blend=best)

    def _classify_domain(self, keyword: str) -> str:
        """Classify a keyword into a domain."""
        kw_lower = keyword.lower()
        best_domain = "general"
        best_overlap = 0

        for domain, domain_kws in _DOMAIN_KEYWORDS.items():
            if kw_lower in domain_kws:
                return domain
            # Partial match via similarity
            overlap = sum(1 for dk in domain_kws if dk in kw_lower or kw_lower in dk)
            if overlap > best_overlap:
                best_overlap = overlap
                best_domain = domain

        return best_domain

    def _create_blend(
        self, kw_a: str, kw_b: str, domain_a: str, domain_b: str
    ) -> Blend | None:
        """Create a blend between two concepts from different domains."""
        key = (domain_a, domain_b)
        reverse_key = (domain_b, domain_a)

        bridges = _DOMAIN_BRIDGES.get(key) or _DOMAIN_BRIDGES.get(reverse_key)
        if not bridges:
            bridges = ["connection", "pattern", "structure"]

        bridge = random.choice(bridges)
        template = random.choice(_BLEND_TEMPLATES)
        insight = template.format(a=kw_a, b=kw_b, bridge=bridge)

        # Novelty: higher if domains are more different
        novelty = 0.7 if key in _DOMAIN_BRIDGES or reverse_key in _DOMAIN_BRIDGES else 0.4

        return Blend(
            concept_a=kw_a,
            concept_b=kw_b,
            bridge=bridge,
            insight=insight,
            novelty=novelty,
        )

    def _create_within_domain_blend(self, keywords: list[str]) -> Blend | None:
        """Blend two concepts within the same domain."""
        kw_a, kw_b = keywords[0], keywords[1]
        sim = text_similarity(kw_a, kw_b)

        # Less similar = more novel blend
        novelty = max(0.3, 1.0 - sim)
        bridge = "unexpected similarity"
        insight = f"What if {kw_a} and {kw_b} are really two sides of the same coin?"

        return Blend(
            concept_a=kw_a,
            concept_b=kw_b,
            bridge=bridge,
            insight=insight,
            novelty=novelty,
        )

    def _graph_blend(self, keyword: str) -> Blend | None:
        """Use the knowledge graph to find an unexpected connection."""
        if self._memory_manager is None:
            return None
        related = self._memory_manager.get_related(keyword)
        if not related:
            return None

        # Pick least obvious relation
        neighbor_id, relation, _ = related[-1]  # last = least expected

        return Blend(
            concept_a=keyword,
            concept_b=neighbor_id,
            bridge=relation,
            insight=f"Through the graph: {keyword} connects to {neighbor_id} via {relation}.",
            novelty=0.6,
        )
