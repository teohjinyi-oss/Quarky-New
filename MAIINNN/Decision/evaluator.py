"""
Decision Engine: Evaluator Department (v2)

Token-value-aware scoring of brain results.

v2 enhancements:
  - Uses specificity tier from RouteDecision to weight brain scores
  - Memory bonus scaled by token importance
  - Smarter action detection via entity extraction
"""

from dataclasses import dataclass
from MAIINNN.Decision.collector import DecisionContext


@dataclass
class EvalScores:
    """Evaluated signal strengths."""
    analytical_score: float = 0.0
    creative_score: float = 0.0
    memory_bonus: float = 0.0
    needs_action: bool = False
    action_type: str = ""           # "app_launch", "system", "file", "code", etc.
    dominant: str = "none"          # "analytical", "creative", "both", "none"
    specificity_tier: str = ""      # v2: passed through from routing


# Intents that signal an action is needed
_ACTION_INTENTS = {"COMMAND", "TASK"}

# Keywords that indicate specific action types
_ACTION_KEYWORDS = {
    "open":       "app_launch",
    "launch":     "app_launch",
    "start":      "app_launch",
    "run":        "code_run",
    "execute":    "code_run",
    "volume":     "system_control",
    "brightness": "system_control",
    "mute":       "system_control",
    "unmute":     "system_control",
    "shutdown":   "system_control",
    "restart":    "system_control",
    "create":     "file_op",
    "delete":     "file_op",
    "move":       "file_op",
    "copy":       "file_op",
    "rename":     "file_op",
    "clipboard":  "clipboard",
    "paste":      "clipboard",
    "search":     "web_search",
    "google":     "web_search",
    "look up":    "web_search",
    "email":      "email",
    "send":       "email",
    "calendar":   "calendar",
    "schedule":   "calendar",
    "remind":     "notification",
    "reminder":   "notification",
    "timer":      "notification",
    "alarm":      "notification",
}

# Specificity tier bonuses: SS/GS boost analytical, SG/GG boost creative
_TIER_BONUSES = {
    "SS": (0.15, 0.0),   # (analytical_boost, creative_boost)
    "GS": (0.10, 0.0),
    "SG": (0.05, 0.10),
    "GG": (0.0, 0.15),
}


def evaluate(ctx: DecisionContext) -> EvalScores:
    """
    Score the decision context:
    1. Rate analytical vs creative strength
    2. Apply specificity tier bonuses
    3. Check if memory recall adds relevance
    4. Detect whether an action is required
    """
    scores = EvalScores()

    # Extract specificity tier from context
    tier = ctx.extra.get("specificity_tier", "")
    scores.specificity_tier = tier

    # Score analytical brain
    if ctx.analytical:
        scores.analytical_score = ctx.analytical.confidence
        # Boost if the brain produced a non-trivial response
        if len(ctx.analytical.response) > 10:
            scores.analytical_score = min(1.0, scores.analytical_score + 0.1)

    # Score creative brain
    if ctx.creative:
        scores.creative_score = ctx.creative.confidence
        if len(ctx.creative.response) > 20:
            scores.creative_score = min(1.0, scores.creative_score + 0.05)

    # v2: Apply specificity tier bonuses
    if tier in _TIER_BONUSES:
        a_boost, c_boost = _TIER_BONUSES[tier]
        scores.analytical_score = min(1.0, scores.analytical_score + a_boost)
        scores.creative_score = min(1.0, scores.creative_score + c_boost)

    # Memory bonus — if we have hits, slightly boost overall confidence
    if ctx.memory_hits > 0:
        scores.memory_bonus = min(0.2, ctx.memory_hits * 0.05)

    # Determine dominant source
    if scores.analytical_score > 0 and scores.creative_score > 0:
        diff = scores.analytical_score - scores.creative_score
        if diff > 0.2:
            scores.dominant = "analytical"
        elif diff < -0.2:
            scores.dominant = "creative"
        else:
            scores.dominant = "both"
    elif scores.analytical_score > 0:
        scores.dominant = "analytical"
    elif scores.creative_score > 0:
        scores.dominant = "creative"

    # Detect action need (case-insensitive intent match)
    if ctx.intent.upper() in _ACTION_INTENTS:
        action_type = _detect_action_type(ctx.user_text)
        if action_type != "general":
            scores.needs_action = True
            scores.action_type = action_type

    return scores


def _detect_action_type(text: str) -> str:
    """Match first keyword in text to an action type."""
    lower = text.lower()
    for keyword, action_type in _ACTION_KEYWORDS.items():
        if keyword in lower:
            return action_type
    return "general"
