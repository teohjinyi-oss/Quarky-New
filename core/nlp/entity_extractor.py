"""
NLP: Entity Extractor (v2)

Slot-filling entity extraction using templates + regex patterns.
Builds on v1 patterns.py but adds:
- Slot templates for structured extraction
- Named entity grouping
- Confidence scoring per entity
- Integration with token-value system
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional

from core.nlp.patterns import (
    extract_urls,
    extract_file_paths,
    extract_app_names,
    extract_quoted,
    extract_numbers,
    extract_times,
    extract_all_entities,
)


@dataclass
class Entity:
    """A named entity extracted from text."""
    type: str           # url, file_path, app_name, person, date, number, time, quoted
    value: str          # the extracted text
    start: int = 0      # character position in original text
    end: int = 0        # character position end
    confidence: float = 1.0


@dataclass
class ExtractionResult:
    """Result of entity extraction from text."""
    text: str
    entities: list[Entity] = field(default_factory=list)

    def by_type(self, entity_type: str) -> list[Entity]:
        """Get entities of a specific type."""
        return [e for e in self.entities if e.type == entity_type]

    def has_type(self, entity_type: str) -> bool:
        return any(e.type == entity_type for e in self.entities)

    def to_dict(self) -> dict[str, list[str]]:
        """Convert to simple dict format (backwards compatible with v1)."""
        result: dict[str, list[str]] = {}
        for e in self.entities:
            key = e.type + "s" if not e.type.endswith("s") else e.type
            if key not in result:
                result[key] = []
            result[key].append(e.value)
        return result


# ── Slot Templates ──────────────────────────────────────────
# Patterns like "open {app}" or "remind me at {time} to {task}"

@dataclass
class SlotTemplate:
    """A template with named slots for structured extraction."""
    pattern: re.Pattern
    slots: list[str]   # named groups in order
    intent_hint: str = ""


_SLOT_TEMPLATES = [
    SlotTemplate(
        re.compile(r'(?:open|launch|start|run)\s+(?P<app>.+)', re.I),
        ["app"], "command",
    ),
    SlotTemplate(
        re.compile(r'(?:remind me|set (?:a )?reminder)\s+(?:at\s+)?(?P<time>[\d:]+\s*(?:am|pm)?)\s+(?:to\s+)?(?P<task>.+)', re.I),
        ["time", "task"], "task",
    ),
    SlotTemplate(
        re.compile(r'(?:search|look up|find)\s+(?:for\s+)?(?P<query>.+)', re.I),
        ["query"], "task",
    ),
    SlotTemplate(
        re.compile(r'(?:set|change|adjust)\s+(?:the\s+)?(?P<setting>volume|brightness)\s+(?:to\s+)?(?P<value>\d+)', re.I),
        ["setting", "value"], "command",
    ),
    SlotTemplate(
        re.compile(r'(?:create|make|write)\s+(?:a\s+)?(?P<type>file|folder|note|document)\s+(?:called|named)\s+(?P<name>.+)', re.I),
        ["type", "name"], "task",
    ),
    SlotTemplate(
        re.compile(r'(?:send|email)\s+(?:an?\s+)?(?:email\s+)?(?:to\s+)?(?P<recipient>.+?)\s+(?:about|saying|with)\s+(?P<content>.+)', re.I),
        ["recipient", "content"], "task",
    ),
    SlotTemplate(
        re.compile(r'(?:what(?:\'s| is) the )?(?:weather|temperature)\s+(?:in|at|for)\s+(?P<location>.+)', re.I),
        ["location"], "question",
    ),
]

# Person name patterns (simple heuristic)
_PERSON_RE = re.compile(
    r'\b(?:(?:Mr|Mrs|Ms|Dr|Prof)\.?\s+)?'
    r'(?:[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\b'
)

# Date patterns
_DATE_RE = re.compile(
    r'\b\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4}\b|'
    r'\b(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|'
    r'jul(?:y)?|aug(?:ust)?|sep(?:tember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)'
    r'\s+\d{1,2}(?:st|nd|rd|th)?,?\s*\d{0,4}\b',
    re.I,
)


class EntityExtractor:
    """
    Extracts entities from text using regex patterns and slot templates.
    """

    def extract(self, text: str) -> ExtractionResult:
        """Full entity extraction pipeline."""
        if not text:
            return ExtractionResult(text=text)

        entities: list[Entity] = []

        # Regex-based entities (from v1 patterns)
        for url in extract_urls(text):
            entities.append(Entity(type="url", value=url, confidence=0.95))

        for path in extract_file_paths(text):
            entities.append(Entity(type="file_path", value=path, confidence=0.9))

        for app in extract_app_names(text):
            entities.append(Entity(type="app_name", value=app, confidence=0.85))

        for quoted in extract_quoted(text):
            entities.append(Entity(type="quoted", value=quoted, confidence=1.0))

        for number in extract_numbers(text):
            entities.append(Entity(type="number", value=number, confidence=0.9))

        for t in extract_times(text):
            entities.append(Entity(type="time", value=t, confidence=0.85))

        # Person names
        for match in _PERSON_RE.finditer(text):
            entities.append(Entity(
                type="person",
                value=match.group(),
                start=match.start(),
                end=match.end(),
                confidence=0.7,
            ))

        # Dates
        for match in _DATE_RE.finditer(text):
            entities.append(Entity(
                type="date",
                value=match.group(),
                start=match.start(),
                end=match.end(),
                confidence=0.85,
            ))

        return ExtractionResult(text=text, entities=entities)

    def extract_slots(self, text: str) -> dict[str, str]:
        """
        Try slot templates and return filled slots from best match.
        Returns empty dict if no template matches.
        """
        for template in _SLOT_TEMPLATES:
            match = template.pattern.search(text)
            if match:
                slots = {}
                for slot_name in template.slots:
                    value = match.group(slot_name)
                    if value:
                        slots[slot_name] = value.strip()
                if slots:
                    return slots
        return {}

    def extract_with_slots(self, text: str) -> tuple[ExtractionResult, dict[str, str]]:
        """Extract both regex entities and slot templates."""
        result = self.extract(text)
        slots = self.extract_slots(text)
        return result, slots
