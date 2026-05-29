"""
Core Brain: Base Interfaces

Abstract base classes for all departments across the brain.
Every department implements `process()` and returns a typed result.
The pipeline flows: Receiver → Processors → Validator/Confidence → Responder
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Optional
import time


# ═══════════════════════════════════════════════════════════════
#  CORE DATA TYPES
# ═══════════════════════════════════════════════════════════════

@dataclass
class BrainInput:
    """Standardized input that enters a brain hemisphere."""
    text: str                                   # cleaned user input
    intent: str                                 # from NLP classifier
    confidence: float                           # classifier confidence
    entities: dict[str, list[str]]              # extracted entities
    tokens: list[str]                           # word tokens
    keywords: list[str]                         # meaningful keywords
    context: dict[str, Any] = field(default_factory=dict)  # extra metadata
    timestamp: float = field(default_factory=time.time)


@dataclass
class BrainResult:
    """Output from a brain hemisphere."""
    source: str                                 # "analytical" or "creative"
    response: str                               # the generated answer text
    confidence: float                           # 0.0–1.0 how sure
    reasoning: list[str] = field(default_factory=list)  # chain of reasoning steps
    metadata: dict[str, Any] = field(default_factory=dict)
    duration_ms: float = 0.0                    # processing time


@dataclass
class SpinalResult:
    """Combined output from spinal cord → sent to Decision Engine."""
    analytical: Optional[BrainResult] = None
    creative: Optional[BrainResult] = None
    route_decision: str = ""                    # why this routing was chosen
    input_intent: str = ""
    input_text: str = ""


# ═══════════════════════════════════════════════════════════════
#  ABSTRACT DEPARTMENT
# ═══════════════════════════════════════════════════════════════

class Department(ABC):
    """
    Base class for every department in the brain.
    Each department does ONE thing well.
    """

    def __init__(self, name: str, system: str):
        self.name = name
        self.system = system
        self.dept_id = f"{system}.{name}"

    @abstractmethod
    def process(self, data: Any) -> Any:
        """Process input and return output. Override in subclass."""
        ...

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} dept_id={self.dept_id}>"


class Pipeline:
    """
    Chains departments together: output of one feeds input of next.
    Used inside each brain hemisphere.

    Usage:
        pipe = Pipeline([receiver, parser, calculator, confidence, responder])
        result = pipe.run(brain_input)
    """

    def __init__(self, departments: list[Department]):
        self.departments = departments

    def run(self, data: Any) -> Any:
        """Run data through all departments sequentially."""
        current = data
        for dept in self.departments:
            current = dept.process(current)
            if current is None:
                return None  # department rejected input
        return current

    def __repr__(self) -> str:
        names = " → ".join(d.name for d in self.departments)
        return f"<Pipeline [{names}]>"
