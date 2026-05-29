"""
Learning System: Pattern Extractor

Extracts abstract patterns from concrete examples.
This is the "Understand" phase of Absorb→Learn→Understand→Create.

Given multiple concrete Q&A pairs, it identifies:
  - Common question structures ("what is X", "how does X work")
  - Answer templates ("X is a Y that Z")
  - Concept categories (technology, nature, etc.)

These patterns allow Quarky to create OWN answers for NEW questions
that fit learned patterns, even without memorizing every fact.
"""

from __future__ import annotations

import re
import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from runtime.config.config import DATA_DIR
from core.nlp.embeddings import text_similarity


@dataclass
class LearnedPattern:
    """An abstract pattern extracted from concrete examples."""
    pattern_type: str        # "question_template", "answer_template", "concept_category"
    template: str            # e.g., "what is {concept}" or "{concept} is a {category} that {description}"
    examples: list[str] = field(default_factory=list)
    confidence: float = 0.5
    use_count: int = 0
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "type": self.pattern_type,
            "template": self.template,
            "examples": self.examples[-10:],
            "confidence": self.confidence,
            "use_count": self.use_count,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, d: dict) -> LearnedPattern:
        return cls(
            pattern_type=d["type"],
            template=d["template"],
            examples=d.get("examples", []),
            confidence=d.get("confidence", 0.5),
            use_count=d.get("use_count", 0),
            created_at=d.get("created_at", 0),
        )


# Common question structures to detect
_Q_TEMPLATES = [
    (re.compile(r"^what is (?:a |an )?(.+?)[\?\.]?$", re.I), "what is {concept}"),
    (re.compile(r"^how does (.+?) work[\?\.]?$", re.I), "how does {concept} work"),
    (re.compile(r"^why (?:is|are|do|does) (.+?)[\?\.]?$", re.I), "why {predicate}"),
    (re.compile(r"^who (?:is|was) (.+?)[\?\.]?$", re.I), "who is {entity}"),
    (re.compile(r"^when (?:did|was|is) (.+?)[\?\.]?$", re.I), "when {event}"),
    (re.compile(r"^where (?:is|are|was|were) (.+?)[\?\.]?$", re.I), "where is {thing}"),
    (re.compile(r"^can you (.+?)[\?\.]?$", re.I), "can you {action}"),
    (re.compile(r"^tell me (?:about )?(.+?)[\?\.]?$", re.I), "tell me about {topic}"),
]

# Common answer structures
_A_TEMPLATES = [
    (re.compile(r"^(.+?) is (?:a|an) (.+?) that (.+?)\.?$", re.I),
     "{concept} is a {category} that {description}"),
    (re.compile(r"^(.+?) (?:means|refers to) (.+?)\.?$", re.I),
     "{term} means {definition}"),
]


class PatternExtractor:
    """
    Extracts and manages abstract patterns from concrete examples.
    """

    def __init__(self):
        self._patterns: list[LearnedPattern] = []
        self._store_path = Path(DATA_DIR) / "learning" / "patterns.json"
        self._store_path.parent.mkdir(parents=True, exist_ok=True)
        self._memory_manager = None
        self._load()

    def set_memory(self, memory_manager) -> None:
        """Inject memory manager for semantic answer generation."""
        self._memory_manager = memory_manager

    def extract_from_pair(self, query: str, answer: str) -> list[LearnedPattern]:
        """Extract patterns from a concrete Q&A pair."""
        found: list[LearnedPattern] = []

        # Extract question pattern
        for regex, template in _Q_TEMPLATES:
            m = regex.match(query.strip())
            if m:
                pattern = self._get_or_create(template, "question_template")
                pattern.examples.append(query)
                pattern.confidence = min(1.0, pattern.confidence + 0.05)
                found.append(pattern)
                break

        # Extract answer pattern
        for regex, template in _A_TEMPLATES:
            m = regex.match(answer.strip())
            if m:
                pattern = self._get_or_create(template, "answer_template")
                pattern.examples.append(answer)
                pattern.confidence = min(1.0, pattern.confidence + 0.05)
                found.append(pattern)
                break

        if found:
            self._save()

        return found

    def match_query(self, query: str) -> LearnedPattern | None:
        """Find a matching question pattern for a new query."""
        for regex, template in _Q_TEMPLATES:
            if regex.match(query.strip()):
                for p in self._patterns:
                    if p.template == template and p.pattern_type == "question_template":
                        p.use_count += 1
                        return p
        return None

    def generate_from_pattern(
        self, pattern: LearnedPattern, concept: str
    ) -> str | None:
        """
        Try to generate an answer by finding the most semantically similar
        example in memory or stored patterns.
        Returns None if no suitable answer can be generated.
        """
        # Strategy 1: Search memory for similar concepts
        if self._memory_manager is not None:
            try:
                query = pattern.template.replace("{concept}", concept)
                results = self._memory_manager.search(query, top_k=5)
                if hasattr(results, "tokens") and results.tokens:
                    best_token = None
                    best_sim = 0.0
                    for token in results.tokens:
                        if hasattr(token, "text") and token.text:
                            sim = text_similarity(query, token.text)
                            if sim > best_sim:
                                best_sim = sim
                                best_token = token
                    if best_token and best_sim > 0.3:
                        answer_text = best_token.text
                        if "\nA: " in answer_text:
                            answer_text = answer_text.split("\nA: ", 1)[1]
                        pattern.use_count += 1
                        self._save()
                        return answer_text
            except Exception:
                pass

        # Strategy 2: Find the most similar stored example and adapt it
        if pattern.examples:
            best_example = None
            best_sim = 0.0
            for ex in pattern.examples:
                sim = text_similarity(concept, ex)
                if sim > best_sim:
                    best_sim = sim
                    best_example = ex
            if best_example and best_sim > 0.25:
                pattern.use_count += 1
                self._save()
                return best_example

        # Strategy 3: Fallback to answer templates with concept fill
        answer_patterns = [
            p for p in self._patterns
            if p.pattern_type == "answer_template" and p.confidence > 0.6
        ]
        if not answer_patterns:
            return None

        best = max(answer_patterns, key=lambda p: p.confidence)
        filled = best.template.replace("{concept}", concept)
        # Only return if the template was actually filled meaningfully
        if "{" not in filled and filled != best.template:
            pattern.use_count += 1
            self._save()
            return filled

        return None

    def _get_or_create(self, template: str, ptype: str) -> LearnedPattern:
        """Get existing pattern or create new one."""
        for p in self._patterns:
            if p.template == template and p.pattern_type == ptype:
                return p
        new_pattern = LearnedPattern(
            pattern_type=ptype,
            template=template,
        )
        self._patterns.append(new_pattern)
        return new_pattern

    def _save(self) -> None:
        data = [p.to_dict() for p in self._patterns]
        try:
            self._store_path.write_text(json.dumps(data, indent=2))
        except OSError:
            pass

    def _load(self) -> None:
        if not self._store_path.exists():
            return
        try:
            data = json.loads(self._store_path.read_text())
            self._patterns = [LearnedPattern.from_dict(d) for d in data]
        except (json.JSONDecodeError, OSError):
            pass

    @property
    def patterns(self) -> list[LearnedPattern]:
        return list(self._patterns)

    @property
    def count(self) -> int:
        return len(self._patterns)
