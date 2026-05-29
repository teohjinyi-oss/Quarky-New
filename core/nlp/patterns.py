"""
NLP: Pattern Bank

Keyword and regex patterns for intent detection + entity extraction.
Four intent types: COMMAND, QUESTION, TASK, CREATIVE.
Entity types: URL, APP_NAME, FILE_PATH, QUOTED_STRING, NUMBER, TIME.
"""

import re
from typing import Optional


# ═══════════════════════════════════════════════════════════════
#  INTENT PATTERNS
# ═══════════════════════════════════════════════════════════════

# Each group: list of (pattern, weight) tuples.
# Higher weight = stronger signal for that intent.

COMMAND_PATTERNS: list[tuple[re.Pattern, float]] = [
    (re.compile(r'\b(open|close|launch|start|stop|run|execute|kill)\b'), 1.0),
    (re.compile(r'\b(turn on|turn off|switch|toggle|enable|disable)\b'), 1.0),
    (re.compile(r'\b(set|change|adjust|increase|decrease|lower|raise)\b'), 0.8),
    (re.compile(r'\b(mute|unmute|pause|resume|play|skip|next|previous)\b'), 0.9),
    (re.compile(r'\b(minimize|maximize|fullscreen|restore)\b'), 0.9),
    (re.compile(r'\b(shutdown|restart|reboot|sleep|hibernate|lock)\b'), 1.0),
    (re.compile(r'\b(copy|paste|cut|delete|undo|redo|select all)\b'), 0.8),
    (re.compile(r'\b(screenshot|screen\s?shot|capture screen)\b'), 0.9),
    (re.compile(r'\b(navigate to|go to|switch to|focus)\b'), 0.7),
    (re.compile(r'\b(install|uninstall|update|download)\b'), 0.8),
]

QUESTION_PATTERNS: list[tuple[re.Pattern, float]] = [
    (re.compile(r'^(what|who|where|when|why|how)\b'), 1.0),
    (re.compile(r'^(is|are|was|were|do|does|did|can|could|will|would|should)\b'), 0.8),
    (re.compile(r'\?$'), 0.9),
    (re.compile(r'\b(tell me|explain|describe|define|meaning of)\b'), 0.8),
    (re.compile(r'\b(difference between|compare)\b'), 0.7),
    (re.compile(r'\b(how (much|many|long|far|often))\b'), 0.9),
]

TASK_PATTERNS: list[tuple[re.Pattern, float]] = [
    (re.compile(r'\b(remind me|set (a )?reminder|alarm|timer|schedule)\b'), 1.0),
    (re.compile(r'\b(create|make|build|generate|write|draft)\b'), 0.7),
    (re.compile(r'\b(find|search|look up|look for|locate)\b'), 0.8),
    (re.compile(r'\b(calculate|compute|convert|count)\b'), 0.8),
    (re.compile(r'\b(send|email|message|notify|call)\b'), 0.7),
    (re.compile(r'\b(save|store|remember|note|bookmark)\b'), 0.8),
    (re.compile(r'\b(organize|sort|filter|list|show me)\b'), 0.7),
    (re.compile(r'\b(check|verify|confirm|validate)\b'), 0.6),
]

CREATIVE_PATTERNS: list[tuple[re.Pattern, float]] = [
    (re.compile(r'\b(imagine|brainstorm|suggest|idea|creative)\b'), 1.0),
    (re.compile(r'\b(write (a )?(story|poem|song|essay|joke))\b'), 1.0),
    (re.compile(r'\b(come up with|think of|invent|design)\b'), 0.9),
    (re.compile(r'\b(what if|hypothetical|suppose|pretend)\b'), 0.8),
    (re.compile(r'\b(roleplay|role play|act as|pretend to be)\b'), 0.9),
    (re.compile(r'\b(alternative|another way|different approach)\b'), 0.7),
]

# Master pattern bank for classifier lookups
INTENT_BANK = {
    "command":  COMMAND_PATTERNS,
    "question": QUESTION_PATTERNS,
    "task":     TASK_PATTERNS,
    "creative": CREATIVE_PATTERNS,
}


# ═══════════════════════════════════════════════════════════════
#  ENTITY EXTRACTION PATTERNS
# ═══════════════════════════════════════════════════════════════

# Each returns list of matched strings

_URL_RE = re.compile(
    r'https?://[^\s<>\"\']+|www\.[^\s<>\"\']+',
    re.IGNORECASE,
)

_FILE_PATH_RE = re.compile(
    r'[A-Za-z]:\\[\w\\.\-\s]+|'                    # Windows: C:\path\to\file
    r'/(?:home|usr|var|etc|tmp|opt)/[\w/.\-]+|'     # Unix absolute
    r'~/[\w/.\-]+',                                 # Unix home shortcut
)

_APP_NAME_RE = re.compile(
    r'\b(chrome|firefox|edge|safari|opera|brave|'
    r'notepad|vscode|code|visual studio|word|excel|powerpoint|'
    r'spotify|discord|slack|teams|zoom|telegram|whatsapp|'
    r'explorer|terminal|cmd|powershell|bash|'
    r'photoshop|gimp|blender|obs|vlc|'
    r'steam|epic games|task manager|calculator|calendar|'
    r'outlook|thunderbird|git|github|docker)\b',
    re.IGNORECASE,
)

_QUOTED_RE = re.compile(r'"([^"]+)"|\'([^\']+)\'')

_NUMBER_RE = re.compile(r'\b\d+(?:\.\d+)?(?:%|px|em|rem|gb|mb|kb|ms|s|m|h)?\b')

_TIME_RE = re.compile(
    r'\b\d{1,2}:\d{2}(?::\d{2})?\s*(?:am|pm)?\b|'
    r'\b(?:in )?\d+\s*(?:minute|hour|second|min|hr|sec)s?\b|'
    r'\b(?:at )?\d{1,2}\s*(?:am|pm)\b',
    re.IGNORECASE,
)


def extract_urls(text: str) -> list[str]:
    return _URL_RE.findall(text)


def extract_file_paths(text: str) -> list[str]:
    return _FILE_PATH_RE.findall(text)


def extract_app_names(text: str) -> list[str]:
    return [m.lower() for m in _APP_NAME_RE.findall(text)]


def extract_quoted(text: str) -> list[str]:
    matches = _QUOTED_RE.findall(text)
    return [m[0] or m[1] for m in matches]


def extract_numbers(text: str) -> list[str]:
    return _NUMBER_RE.findall(text)


def extract_times(text: str) -> list[str]:
    return _TIME_RE.findall(text)


def extract_all_entities(text: str) -> dict[str, list[str]]:
    """Run all entity extractors, return non-empty results."""
    entities: dict[str, list[str]] = {}

    urls = extract_urls(text)
    if urls:
        entities["urls"] = urls

    paths = extract_file_paths(text)
    if paths:
        entities["file_paths"] = paths

    apps = extract_app_names(text)
    if apps:
        entities["app_names"] = apps

    quoted = extract_quoted(text)
    if quoted:
        entities["quoted"] = quoted

    numbers = extract_numbers(text)
    if numbers:
        entities["numbers"] = numbers

    times = extract_times(text)
    if times:
        entities["times"] = times

    return entities


def score_intent(text: str, patterns: list[tuple[re.Pattern, float]]) -> float:
    """Score text against a pattern group. Returns sum of matched weights."""
    total = 0.0
    for pattern, weight in patterns:
        if pattern.search(text):
            total += weight
    return total
