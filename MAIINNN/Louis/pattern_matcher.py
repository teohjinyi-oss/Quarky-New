"""
Analytical Brain: Pattern Matcher Department (v2)

Matches user input against known patterns AND the knowledge graph.

Strategy (v2):
  1. Regex patterns for identity/system/definitions (fast path)
  2. Graph-backed lookup: search the memory graph for answers
  3. Combine both sources, rank by confidence
"""

import re
from dataclasses import dataclass, field
from typing import Any

from AppStudio.Infrastructure.base import Department
from MAIINNN.Louis.parser import ParsedInput
from MAIINNN.NLP.embeddings import text_similarity


@dataclass
class PatternMatch:
    """A matched knowledge pattern."""
    category: str           # "definition", "factual", "system", "identity", "graph"
    template: str           # the pattern that matched
    answer: str             # the response
    confidence: float       # how well it matched (0.0–1.0)
    source: str = "regex"   # "regex" | "graph" | "memory"


@dataclass
class MatchResult:
    """Output of the pattern matching stage."""
    matches: list[PatternMatch] = field(default_factory=list)
    best_match: PatternMatch | None = None
    has_match: bool = False


# ═══════════════════════════════════════════════════════════════
#  KNOWLEDGE PATTERNS (built-in, fast-path)
# ═══════════════════════════════════════════════════════════════

_IDENTITY_PATTERNS: list[tuple[re.Pattern, str, float]] = [
    (re.compile(r'\b(?:who|what) are you\b', re.I),
     "I'm Quarky, your personal AI assistant. I run entirely on your machine — no cloud, no LLM. "
     "I think with two brain hemispheres: analytical for logic and creative for ideas.", 0.95),

    (re.compile(r"\bwhat(?:'s| is) your name\b", re.I),
     "My name is Quarky.", 0.95),

    (re.compile(r'\bwhat can you do\b', re.I),
     "I can answer questions, do math, run desktop commands, manage files, "
     "control your apps, and remember things for you. Ask me anything.", 0.9),

    (re.compile(r'\bhow do you work\b', re.I),
     "I have 6 systems: a dual brain (analytical + creative), infrastructure for routing, "
     "a 3-tier memory system, a decision engine, an action system for desktop control, "
     "and a start system for input. Everything runs locally.", 0.9),
]

_SYSTEM_PATTERNS: list[tuple[re.Pattern, str, float]] = [
    (re.compile(r'\bwhat time is it\b', re.I),
     "__DYNAMIC:TIME__", 0.95),

    (re.compile(r'\bwhat(?:\'s| is) (?:the )?date\b', re.I),
     "__DYNAMIC:DATE__", 0.95),

    (re.compile(r'\bwhat(?:\'s| is) (?:today|the day)\b', re.I),
     "__DYNAMIC:DATE__", 0.9),
]

_DEFINITION_PATTERNS: list[tuple[re.Pattern, str, float]] = [
    (re.compile(r'\bwhat is (?:a |an )?computer\b', re.I),
     "A computer is an electronic device that processes data according to instructions "
     "(programs) to produce meaningful output.", 0.85),

    (re.compile(r'\bwhat is (?:a |an )?algorithm\b', re.I),
     "An algorithm is a step-by-step set of instructions for solving a specific problem "
     "or performing a computation.", 0.85),

    (re.compile(r'\bwhat is (?:a |an )?variable\b', re.I),
     "A variable is a named storage location in a program that holds a value "
     "which can change during execution.", 0.85),

    (re.compile(r'\bwhat is (?:a |an )?function\b', re.I),
     "A function is a reusable block of code that performs a specific task. "
     "It takes inputs (parameters) and may return an output.", 0.85),

    (re.compile(r'\bwhat is (?:an? )?(?:AI|artificial intelligence)\b', re.I),
     "Artificial intelligence is the simulation of human intelligence by computer systems. "
     "It includes learning, reasoning, and self-correction.", 0.85),

    (re.compile(r'\bwhat is python\b', re.I),
     "Python is a high-level, interpreted programming language known for its clear syntax "
     "and versatility. It's used in web development, data science, AI, and automation.", 0.85),
]

# Master registry
_ALL_PATTERN_GROUPS: dict[str, list[tuple[re.Pattern, str, float]]] = {
    "identity":   _IDENTITY_PATTERNS,
    "system":     _SYSTEM_PATTERNS,
    "definition": _DEFINITION_PATTERNS,
}


# ─── Dynamic answer resolver ────────────────────────────────

def _resolve_dynamic(answer: str) -> str:
    """Replace __DYNAMIC:X__ placeholders with actual values."""
    import datetime
    now = datetime.datetime.now()

    if "__DYNAMIC:TIME__" in answer:
        return now.strftime("It's %I:%M %p.")
    if "__DYNAMIC:DATE__" in answer:
        return now.strftime("Today is %A, %B %d, %Y.")
    return answer


# ─── Pattern Matcher Department (v2) ────────────────────────

class PatternMatcher(Department):
    """
    Matches input against known patterns + knowledge graph.
    Fast path for recognized questions — graph fallback for learned knowledge.
    """

    def __init__(self):
        super().__init__("pattern_matcher", "core.analytical")
        self._memory_manager = None

    def set_memory(self, memory_manager: Any) -> None:
        """Inject the v2 memory manager for graph-backed lookups."""
        self._memory_manager = memory_manager

    def process(self, data: Any) -> Any:
        if not isinstance(data, ParsedInput):
            return data

        text = data.brain_input.text
        keywords = data.brain_input.keywords
        match_result = self.match(text, data.task_type, keywords)

        data.brain_input.context["pattern_match"] = match_result
        return data

    def match(
        self, text: str, task_type: str = "", keywords: list[str] | None = None
    ) -> MatchResult:
        """Score text against all pattern groups + knowledge graph."""
        matches: list[PatternMatch] = []

        # 1. Regex patterns (fast path — always runs)
        for category, patterns in _ALL_PATTERN_GROUPS.items():
            for regex, answer, base_conf in patterns:
                if regex.search(text):
                    resolved = _resolve_dynamic(answer)
                    matches.append(PatternMatch(
                        category=category,
                        template=regex.pattern,
                        answer=resolved,
                        confidence=base_conf,
                        source="regex",
                    ))

        # 2. Graph-backed lookup (runs if no high-confidence regex match)
        best_regex_conf = max((m.confidence for m in matches), default=0.0)
        if best_regex_conf < 0.8 and self._memory_manager is not None:
            graph_matches = self._search_graph(text, keywords or [])
            matches.extend(graph_matches)

        # Sort by confidence
        matches.sort(key=lambda m: m.confidence, reverse=True)
        best = matches[0] if matches else None

        return MatchResult(
            matches=matches,
            best_match=best,
            has_match=bool(matches),
        )

    def _search_graph(
        self, text: str, keywords: list[str]
    ) -> list[PatternMatch]:
        """Search the knowledge graph for matching facts."""
        results: list[PatternMatch] = []

        # Search memory for relevant tokens
        if self._memory_manager is None:
            return results
        try:
            search_result = self._memory_manager.search(text, top_k=3)
        except Exception:
            return results

        if not hasattr(search_result, "tokens") or not search_result.tokens:
            return results

        for token in search_result.tokens:
            if not hasattr(token, "text") or not token.text:
                continue
            sim = text_similarity(text, token.text)
            if sim > 0.25:
                answer_text = token.text
                # Extract answer from Q&A format if present
                if "\nA: " in answer_text:
                    answer_text = answer_text.split("\nA: ", 1)[1]
                results.append(PatternMatch(
                    category="graph",
                    template=f"memory:{token.id}",
                    answer=answer_text,
                    confidence=min(0.75, sim * 0.9),
                    source="memory",
                ))

        # Also check graph relations for keywords
        if hasattr(self._memory_manager, "_graph"):
            graph = self._memory_manager._graph
            for kw in keywords[:3]:
                try:
                    neighbors = graph.get_neighbors(kw.lower(), depth=1)
                    for neighbor_id, relation, attrs in neighbors:
                        results.append(PatternMatch(
                            category="graph",
                            template=f"graph:{kw}->{relation}->{neighbor_id}",
                            answer=f"{kw} {relation} {neighbor_id}",
                            confidence=0.5,
                            source="graph",
                        ))
                except Exception:
                    pass

        return results
