"""
Creative Brain: Concept Expander Department (v2)

Generates related concepts, associations, and tangential ideas.
Worker-pool capable — spawns multiple idea threads in parallel.

v2 enhancements:
  - Memory-backed associations: supplement static maps with graph lookups
  - Pattern abstraction: learn new associations from stored tokens
  - Richer metaphor generation using cross-domain bridges

Strategy: From keywords, expand outward using:
  - Synonym/antonym associations (static + graph-backed)
  - Conceptual categories (broader/narrower terms)
  - Domain cross-pollination (apply concept from one field to another)
  - "What if" inversion (flip assumptions)
"""

import random
from dataclasses import dataclass, field
from typing import Any

from AppStudio.Infrastructure.base import Department, BrainInput


@dataclass
class ConceptWeb:
    """Expanded concept network from user input."""
    seed_keywords: list[str]
    associations: list[str] = field(default_factory=list)
    inversions: list[str] = field(default_factory=list)
    questions: list[str] = field(default_factory=list)
    metaphors: list[str] = field(default_factory=list)
    graph_associations: list[str] = field(default_factory=list)  # v2: from memory


# ═══════════════════════════════════════════════════════════════
#  Association Maps
#  These grow over time as the system learns. Starting with
#  a core set of conceptual links.
# ═══════════════════════════════════════════════════════════════

_CONCEPT_ASSOCIATIONS: dict[str, list[str]] = {
    # Technology
    "computer": ["machine", "processor", "digital", "network", "silicon", "logic"],
    "code": ["algorithm", "syntax", "logic", "craft", "architecture", "puzzle"],
    "internet": ["connection", "web", "global", "network", "communication"],
    "ai": ["intelligence", "learning", "neural", "pattern", "prediction", "automation"],
    "robot": ["automation", "mechanism", "precision", "helper", "companion"],
    "data": ["information", "pattern", "signal", "truth", "evidence", "noise"],

    # Nature
    "water": ["flow", "adapt", "life", "cleanse", "reflect", "depth"],
    "fire": ["energy", "transform", "passion", "destruction", "warmth", "light"],
    "tree": ["growth", "roots", "shelter", "patience", "network", "seasons"],
    "ocean": ["vastness", "depth", "mystery", "rhythm", "power", "calm"],
    "mountain": ["challenge", "perspective", "endurance", "peak", "foundation"],
    "star": ["distant", "bright", "guide", "ancient", "energy", "wonder"],

    # Abstract
    "time": ["change", "cycle", "memory", "moment", "flow", "irreversible"],
    "music": ["rhythm", "emotion", "harmony", "expression", "pattern", "silence"],
    "art": ["expression", "perspective", "beauty", "craft", "imagination", "emotion"],
    "love": ["connection", "care", "vulnerability", "growth", "trust", "sacrifice"],
    "fear": ["unknown", "boundary", "signal", "growth", "courage", "survival"],
    "dream": ["imagination", "subconscious", "possibility", "vision", "freedom"],
    "idea": ["spark", "seed", "connection", "possibility", "innovation", "question"],
    "story": ["journey", "character", "conflict", "meaning", "connection", "memory"],

    # Actions
    "create": ["build", "imagine", "combine", "express", "birth", "design"],
    "learn": ["grow", "adapt", "discover", "struggle", "connect", "transform"],
    "play": ["explore", "joy", "experiment", "freedom", "creativity", "risk"],
}

# Inversion prompts — flip the assumption
_INVERSION_TEMPLATES = [
    "What if {} didn't exist?",
    "What's the opposite of {}?",
    "What if {} worked backwards?",
    "What if everyone had unlimited {}?",
    "What if {} was invisible?",
    "What would a world without {} look like?",
]

# Question generators
_QUESTION_TEMPLATES = [
    "Why does {} matter?",
    "How could {} be different?",
    "What connects {} to everyday life?",
    "Who benefits most from {}?",
    "What's the most surprising thing about {}?",
    "How would you explain {} to someone from 1000 years ago?",
]

# Metaphor bridges
_METAPHOR_TEMPLATES = [
    "{} is like a {} — both involve {}.",
    "Think of {} as a {} that {}.",
    "If {} were a {}, it would {}.",
]

_METAPHOR_VEHICLES = [
    ("river", "flows and carves new paths"),
    ("garden", "needs tending and patience to flourish"),
    ("bridge", "connects two separate worlds"),
    ("mirror", "reflects back what you bring to it"),
    ("puzzle", "reveals its picture one piece at a time"),
    ("song", "builds layers into something greater than its parts"),
    ("key", "unlocks something that was always there"),
    ("seed", "holds enormous potential in a small package"),
]


class ConceptExpander(Department):
    """
    Expands input keywords into a rich concept web.
    This is the creative brain's imagination engine.

    v2: Also pulls associations from the knowledge graph.
    """

    def __init__(self):
        super().__init__("concept_expander", "core.creative")
        self._memory_manager = None

    def set_memory(self, memory_manager: Any) -> None:
        """Inject the v2 memory manager for graph-backed expansion."""
        self._memory_manager = memory_manager

    def process(self, data: Any) -> Any:
        if not isinstance(data, BrainInput):
            return data

        keywords = data.keywords or data.tokens[:5]
        web = self.expand(keywords)
        data.context["concept_web"] = web
        return data

    def expand(self, keywords: list[str]) -> ConceptWeb:
        """Build a concept web from seed keywords."""
        web = ConceptWeb(seed_keywords=list(keywords))

        # 1. Direct associations (static)
        for kw in keywords:
            assocs = _CONCEPT_ASSOCIATIONS.get(kw, [])
            web.associations.extend(assocs)

            # Also check partial matches
            for concept, related in _CONCEPT_ASSOCIATIONS.items():
                if kw in concept or concept in kw:
                    web.associations.extend(related[:3])

        # Deduplicate, remove seeds
        seen = set(keywords)
        unique = []
        for a in web.associations:
            if a not in seen:
                seen.add(a)
                unique.append(a)
        web.associations = unique[:10]  # cap at 10

        # 1b. Graph-backed associations (v2)
        if self._memory_manager is not None:
            for kw in keywords[:3]:
                try:
                    related = self._memory_manager.get_related(kw)
                    for neighbor_id, relation, _ in related:
                        if neighbor_id not in seen:
                            seen.add(neighbor_id)
                            web.graph_associations.append(neighbor_id)
                except Exception:
                    pass

        # 2. Inversions (pick 2-3 keywords)
        inversion_seeds = keywords[:3]
        for seed in inversion_seeds:
            template = random.choice(_INVERSION_TEMPLATES)
            web.inversions.append(template.format(seed))

        # 3. Questions
        for seed in keywords[:2]:
            template = random.choice(_QUESTION_TEMPLATES)
            web.questions.append(template.format(seed))

        # 4. Metaphors (pick 1-2)
        for seed in keywords[:2]:
            vehicle, action = random.choice(_METAPHOR_VEHICLES)
            web.metaphors.append(
                f"{seed.capitalize()} is like a {vehicle} — it {action}."
            )

        return web
