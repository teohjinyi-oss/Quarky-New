"""
NLP: Conversational Context Manager (v2)

Tracks conversation state across turns:
- Sliding window of recent messages
- Topic detection and tracking
- Pronoun resolution (he/she/it/they → last mentioned entity)
- Context injection into brain inputs

This is what makes Quarky feel like a real conversation partner
instead of a stateless Q&A bot.
"""

from __future__ import annotations

import re
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Optional

from MAIINNN.NLP.embeddings import text_similarity
from MAIINNN.NLP.tokenizer import keyword_tokens


@dataclass(slots=True)
class Turn:
    """A single conversation turn."""
    role: str          # "user" or "quarky"
    text: str
    intent: str = ""
    entities: dict[str, list[str]] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    topic: str = ""


@dataclass(slots=True)
class ContextState:
    """Current conversation context snapshot."""
    current_topic: str = ""
    topic_confidence: float = 0.0
    turn_count: int = 0
    last_entities: dict[str, list[str]] = field(default_factory=dict)
    pronoun_map: dict[str, str] = field(default_factory=dict)  # "it" → "chrome"
    recent_intents: list[str] = field(default_factory=list)


class ContextManager:
    """
    Manages conversational context across turns.

    Features:
    - Sliding window of N recent turns
    - Topic tracking (detects when topic changes)
    - Pronoun resolution (it/he/she/they → entity)
    - Context dict for brain input enrichment
    """

    def __init__(
        self,
        window_size: int = 10,
        topic_change_threshold: float = 0.4,
    ):
        self._window: deque[Turn] = deque(maxlen=window_size)
        self._topic_threshold = topic_change_threshold
        self._state = ContextState()
        self._pronoun_patterns: dict[str, tuple[re.Pattern, str]] = {}

    def add_turn(
        self,
        role: str,
        text: str,
        intent: str = "",
        entities: dict[str, list[str]] | None = None,
    ) -> None:
        """Add a new conversation turn."""
        entities = entities or {}

        # Detect topic change
        topic = self._detect_topic(text)

        turn = Turn(
            role=role,
            text=text,
            intent=intent,
            entities=entities,
            topic=topic,
        )
        self._window.append(turn)

        # Update state
        self._state.turn_count += 1
        self._state.current_topic = topic
        if intent:
            self._state.recent_intents.append(intent)
            if len(self._state.recent_intents) > 5:
                self._state.recent_intents = self._state.recent_intents[-5:]

        # Update entity tracking for pronoun resolution
        if entities:
            self._state.last_entities.update(entities)
            self._update_pronoun_map(entities)

    def resolve_pronouns(self, text: str) -> str:
        """
        Replace pronouns with their likely referents.
        E.g., "close it" → "close chrome" (if chrome was last mentioned app).
        """
        if not self._pronoun_patterns:
            return text

        result = text
        for pronoun, (pattern, referent) in self._pronoun_patterns.items():
            result = pattern.sub(referent, result)
        return result

    def get_context_dict(self) -> dict:
        """
        Build context dict for enriching brain inputs.
        Includes recent history, topic, and pronoun map.
        """
        recent_texts = [
            {"role": t.role, "text": t.text[:200]}
            for t in list(self._window)[-3:]
        ]

        return {
            "conversation_history": recent_texts,
            "current_topic": self._state.current_topic,
            "topic_confidence": self._state.topic_confidence,
            "pronoun_map": dict(self._state.pronoun_map),
            "turn_count": self._state.turn_count,
            "recent_intents": list(self._state.recent_intents),
            "last_entities": dict(self._state.last_entities),
        }

    def get_state(self) -> ContextState:
        """Get current context state snapshot."""
        return self._state

    def get_recent_turns(self, n: int = 3) -> list[Turn]:
        """Get last N turns."""
        turns = list(self._window)
        return turns[-n:] if len(turns) >= n else turns

    def get_last_user_text(self) -> str:
        """Get the last thing the user said."""
        for turn in reversed(self._window):
            if turn.role == "user":
                return turn.text
        return ""

    def clear(self) -> None:
        """Reset conversation context."""
        self._window.clear()
        self._state = ContextState()
        self._pronoun_patterns = {}

    @property
    def is_empty(self) -> bool:
        return len(self._window) == 0

    @property
    def turn_count(self) -> int:
        return self._state.turn_count

    # ── Internal ────────────────────────────────────────────

    def _detect_topic(self, text: str) -> str:
        """
        Detect or carry forward the current topic.
        Uses text similarity with recent turns to detect topic shifts.
        """
        if not self._window:
            self._state.topic_confidence = 0.5
            return self._extract_topic_label(text)

        # Compare with last turn
        last_turn = self._window[-1]
        sim = text_similarity(text, last_turn.text)

        if sim >= self._topic_threshold:
            # Same topic — carry forward
            self._state.topic_confidence = min(1.0, sim + 0.2)
            return last_turn.topic or self._extract_topic_label(text)
        else:
            # Topic change detected
            self._state.topic_confidence = 0.5
            return self._extract_topic_label(text)

    def _extract_topic_label(self, text: str) -> str:
        """Extract a simple topic label from text (first noun-like keyword)."""
        keywords = keyword_tokens(text)
        return keywords[0] if keywords else "general"

    def _update_pronoun_map(self, entities: dict[str, list[str]]) -> None:
        """Update pronoun → entity mappings based on new entities."""
        # "it" → last mentioned app or thing
        if "app_names" in entities and entities["app_names"]:
            self._state.pronoun_map["it"] = entities["app_names"][-1]
            self._state.pronoun_map["that"] = entities["app_names"][-1]

        # Person pronouns
        if "persons" in entities and entities["persons"]:
            last_person = entities["persons"][-1]
            # Simple heuristic — would need NER for gender
            self._state.pronoun_map["they"] = last_person
            self._state.pronoun_map["them"] = last_person

        # File/path → "it"
        if "file_paths" in entities and entities["file_paths"]:
            self._state.pronoun_map["it"] = entities["file_paths"][-1]

        # Rebuild compiled patterns cache
        self._pronoun_patterns = {
            pronoun: (re.compile(r'\b' + re.escape(pronoun) + r'\b', re.I), referent)
            for pronoun, referent in self._state.pronoun_map.items()
        }
