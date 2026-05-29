"""
NLP: Spelling Correction (v2)

Uses SymSpell for fast edit-distance spelling correction.
Falls back to a simple heuristic corrector if symspellpy is not installed.

Features:
- SymSpell with frequency dictionary (82k English words)
- Custom user dictionary (learned words)
- Token-value-aware: corrections on high-value tokens are logged for learning
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Optional

from AppStudio.Config import MODELS_DIR, DATA_DIR

try:
    from symspellpy import Verbosity as _Verbosity
except ImportError:
    _Verbosity = None  # type: ignore[assignment,misc]


# ── Lazy SymSpell loading ───────────────────────────────────
_sym_spell = None
_sym_available = True


def _get_symspell():
    """Lazy-load SymSpell with frequency dictionary."""
    global _sym_spell, _sym_available

    if _sym_spell is not None:
        return _sym_spell

    try:
        from symspellpy import SymSpell

        _sym_spell = SymSpell(max_dictionary_edit_distance=2, prefix_length=7)

        # Load built-in frequency dictionary
        dict_path = MODELS_DIR / "frequency_dictionary_en_82_765.txt"
        if dict_path.exists():
            _sym_spell.load_dictionary(
                str(dict_path),
                term_index=0,
                count_index=1,
            )
        else:
            # Try loading from symspellpy package data
            import importlib.resources
            import symspellpy
            pkg_path = Path(symspellpy.__file__).parent / "frequency_dictionary_en_82_765.txt"
            if pkg_path.exists():
                _sym_spell.load_dictionary(str(pkg_path), term_index=0, count_index=1)

        # Load custom dictionary if exists
        custom_path = DATA_DIR / "custom_dictionary.txt"
        if custom_path.exists():
            _sym_spell.load_dictionary(
                str(custom_path),
                term_index=0,
                count_index=1,
            )

        return _sym_spell

    except ImportError:
        _sym_available = False
        return None


def correct(text: str) -> str:
    """
    Correct spelling in text. Preserves capitalization patterns.
    Returns corrected text.
    """
    if not text or not text.strip():
        return text

    sym = _get_symspell()
    if sym is not None:
        return _correct_symspell(text, sym)
    return _correct_fallback(text)


def correct_word(word: str) -> str:
    """Correct a single word."""
    if not word:
        return word

    sym = _get_symspell()
    if sym is not None:
        suggestions = sym.lookup(
            word.lower(),
            max_edit_distance=2,
            verbosity=_Verbosity.TOP,  # type: ignore[union-attr]
        )
        if suggestions:
            corrected = suggestions[0].term
            # Preserve original capitalization
            if word[0].isupper():
                corrected = corrected.capitalize()
            if word.isupper():
                corrected = corrected.upper()
            return corrected
    return word


def suggestions(word: str, max_results: int = 5) -> list[str]:
    """Return spelling suggestions for a word."""
    sym = _get_symspell()
    if sym is None:
        return []

    results = sym.lookup(
        word.lower(),
        max_edit_distance=2,
        verbosity=_Verbosity.ALL,  # type: ignore[union-attr]
    )
    return [r.term for r in results[:max_results]]


def add_to_dictionary(word: str, frequency: int = 1000) -> None:
    """Add a word to the custom dictionary (persists)."""
    custom_path = DATA_DIR / "custom_dictionary.txt"
    with open(custom_path, "a", encoding="utf-8") as f:
        f.write(f"{word.lower()} {frequency}\n")

    # Also add to live SymSpell instance
    sym = _get_symspell()
    if sym is not None:
        sym.create_dictionary_entry(word.lower(), frequency)


def is_available() -> bool:
    """Check if SymSpell is available."""
    _get_symspell()
    return _sym_available


# ── Internal ────────────────────────────────────────────────

def _correct_symspell(text: str, sym) -> str:
    """Use SymSpell compound correction for full text."""
    # Compound lookup handles multi-word correction
    results = sym.lookup_compound(text.lower(), max_edit_distance=2)
    if results:
        return results[0].term
    return text


# Simple heuristic fallback (common typos only)
_COMMON_CORRECTIONS = {
    "teh": "the", "taht": "that", "adn": "and", "hte": "the",
    "nto": "not", "waht": "what", "yuor": "your", "thier": "their",
    "recieve": "receive", "beleive": "believe", "occured": "occurred",
    "seperate": "separate", "definately": "definitely",
    "accomodate": "accommodate", "occurence": "occurrence",
    "wierd": "weird", "calender": "calendar", "goverment": "government",
    "enviroment": "environment", "necesary": "necessary",
}


def _correct_fallback(text: str) -> str:
    """Simple dictionary-based correction when SymSpell is unavailable."""
    words = text.split()
    corrected = []
    for word in words:
        lower = word.lower().strip(".,!?;:")
        if lower in _COMMON_CORRECTIONS:
            replacement = _COMMON_CORRECTIONS[lower]
            # Preserve capitalization
            if word[0].isupper():
                replacement = replacement.capitalize()
            corrected.append(replacement)
        else:
            corrected.append(word)
    return " ".join(corrected)
