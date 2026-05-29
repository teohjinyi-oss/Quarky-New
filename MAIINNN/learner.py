"""
Quarky_Ai — Interaction Learning Engine

Tracks which responses get positive follow-up (thanks, yes, correct, etc.)
and boosts pattern weights for successful intents. Tracks intent frequency
per session to adapt NLP confidence weighting.

Stores learning data in data/learning.json.
"""

import json
import threading
import time
from typing import Any

from AppStudio.Config import DATA_DIR


_LEARNING_FILE = DATA_DIR / "learning.json"
_lock = threading.Lock()

# Positive feedback signals
_POSITIVE_SIGNALS = {
    "thanks", "thank you", "thx", "perfect", "correct", "right",
    "yes", "yeah", "yep", "exactly", "great", "good", "nice",
    "awesome", "cool", "ok", "okay", "got it", "that works",
}

# Negative feedback signals
_NEGATIVE_SIGNALS = {
    "no", "nope", "wrong", "incorrect", "not right", "bad",
    "that's wrong", "try again", "not what i asked",
}


def _load_data() -> dict[str, Any]:
    """Load learning data from file."""
    try:
        if _LEARNING_FILE.exists():
            data = json.loads(_LEARNING_FILE.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return data
    except (json.JSONDecodeError, OSError):
        pass
    return {
        "intent_boosts": {},
        "intent_frequency": {},
        "positive_count": 0,
        "negative_count": 0,
        "total_interactions": 0,
    }


def _save_data(data: dict[str, Any]) -> None:
    """Save learning data to file."""
    try:
        _LEARNING_FILE.write_text(
            json.dumps(data, indent=2, default=str),
            encoding="utf-8",
        )
    except OSError:
        pass


def _is_positive(text: str) -> bool:
    """Check if text contains positive feedback signals."""
    lower = text.lower().strip()
    return any(sig in lower for sig in _POSITIVE_SIGNALS)


def _is_negative(text: str) -> bool:
    """Check if text contains negative feedback signals."""
    lower = text.lower().strip()
    return any(sig in lower for sig in _NEGATIVE_SIGNALS)


def update_from_interaction(user_text: str, response: str,
                            follow_up: str, intent: str = "",
                            source: str = "") -> dict[str, Any]:
    """
    Learn from a user interaction triple (input, response, follow-up).
    Returns a dict summarizing what was learned.

    Args:
        user_text: The original user input
        response: What Quarky responded
        follow_up: The user's next message (feedback signal)
        intent: The classified intent of user_text
        source: The brain source (analytical/creative/merged)
    """
    adjustments: dict[str, Any] = {"action": "none"}

    with _lock:
        data = _load_data()
        data["total_interactions"] = data.get("total_interactions", 0) + 1

        # Track intent frequency
        if intent:
            freq = data.get("intent_frequency", {})
            freq[intent] = freq.get(intent, 0) + 1
            data["intent_frequency"] = freq

        # Check for positive/negative feedback
        if _is_positive(follow_up):
            data["positive_count"] = data.get("positive_count", 0) + 1
            adjustments["action"] = "positive_boost"

            # Boost the intent that produced a good response
            if intent:
                boosts = data.get("intent_boosts", {})
                current = boosts.get(intent, 0.0)
                boosts[intent] = min(current + 0.05, 1.0)
                data["intent_boosts"] = boosts
                adjustments["intent_boosted"] = intent
                adjustments["new_boost"] = boosts[intent]

        elif _is_negative(follow_up):
            data["negative_count"] = data.get("negative_count", 0) + 1
            adjustments["action"] = "negative_penalty"

            # Slight penalty to the intent
            if intent:
                boosts = data.get("intent_boosts", {})
                current = boosts.get(intent, 0.0)
                boosts[intent] = max(current - 0.02, -0.5)
                data["intent_boosts"] = boosts
                adjustments["intent_penalized"] = intent
                adjustments["new_boost"] = boosts[intent]

        _save_data(data)

    return adjustments


def get_intent_boost(intent: str) -> float:
    """Get the learned boost value for an intent (+/- float)."""
    with _lock:
        data = _load_data()
    return data.get("intent_boosts", {}).get(intent, 0.0)


def get_stats() -> dict[str, Any]:
    """Get learning statistics."""
    with _lock:
        data = _load_data()
    return {
        "total_interactions": data.get("total_interactions", 0),
        "positive_feedback": data.get("positive_count", 0),
        "negative_feedback": data.get("negative_count", 0),
        "intent_frequency": data.get("intent_frequency", {}),
        "intent_boosts": data.get("intent_boosts", {}),
    }


def reset() -> None:
    """Reset all learning data."""
    with _lock:
        _save_data({
            "intent_boosts": {},
            "intent_frequency": {},
            "positive_count": 0,
            "negative_count": 0,
            "total_interactions": 0,
        })
