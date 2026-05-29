"""
Intelligence: Token Value Engine

The token-value system is the foundation of Quarky v2's intelligence.
Every piece of information gets scored across multiple dimensions.
These scores drive memory storage, retrieval ranking, response routing,
learning priority, and eviction decisions.

Modules:
- token.py       — Token dataclass with multi-dimensional values
- scorer.py      — Composite scoring engine
- classifier.py  — Specificity classifier for response routing
- tracker.py     — Token lifecycle management
"""

from core.intelligence.token import Token, SpecificityTier, ConfirmationTier
from core.intelligence.scorer import TokenScorer
from core.intelligence.classifier import SpecificityClassifier
from core.intelligence.tracker import TokenTracker

__all__ = [
    "Token",
    "SpecificityTier",
    "ConfirmationTier",
    "TokenScorer",
    "SpecificityClassifier",
    "TokenTracker",
]
