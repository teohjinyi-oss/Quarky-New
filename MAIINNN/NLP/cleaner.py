"""
NLP: Input Cleaner

Text normalization and sanitization.
First thing that touches user input — cleans before anything processes it.

Rules:
- Normalize whitespace and case
- Strip dangerous characters (injection prevention)
- Preserve meaningful punctuation
- Trim to reasonable length
"""

import re
import html


# Characters that could be used for injection attacks
_DANGEROUS_PATTERNS = [
    re.compile(r'[;\|`$]'),               # shell metacharacters
    re.compile(r'<script.*?>.*?</script>', re.IGNORECASE | re.DOTALL),
    re.compile(r'<!--.*?-->', re.DOTALL),  # HTML comments
]

# Max input length (prevent memory bombs)
MAX_INPUT_LENGTH = 10000


def clean(text: str) -> str:
    """
    Full cleaning pipeline: normalize → sanitize → trim.

    Args:
        text: raw user input

    Returns:
        Cleaned text safe for processing
    """
    if not text:
        return ""

    text = _normalize(text)
    text = _sanitize(text)
    text = _trim(text)
    return text


def _normalize(text: str) -> str:
    """Normalize whitespace, case, and encoding."""
    # Decode HTML entities
    text = html.unescape(text)

    # Normalize Unicode whitespace to regular spaces
    text = re.sub(r'[\u00a0\u2000-\u200b\u202f\u205f\u3000]', ' ', text)

    # Collapse multiple spaces/newlines to single space
    text = re.sub(r'\s+', ' ', text)

    # Strip leading/trailing whitespace
    text = text.strip()

    # Lowercase for processing (preserve original in metadata if needed)
    text = text.lower()

    return text


def _sanitize(text: str) -> str:
    """Remove potentially dangerous content."""
    # Remove shell metacharacters
    text = re.sub(r'[;\|`$\\]', '', text)

    # Remove HTML/script tags
    text = re.sub(r'<[^>]+>', '', text)

    # Remove null bytes
    text = text.replace('\x00', '')

    # Remove control characters (keep newline, tab)
    text = re.sub(r'[\x01-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)

    return text


def _trim(text: str) -> str:
    """Trim to max length."""
    if len(text) > MAX_INPUT_LENGTH:
        text = text[:MAX_INPUT_LENGTH]
    return text


def is_empty(text: str) -> bool:
    """Check if cleaned text is effectively empty."""
    return len(text.strip()) == 0


def extract_quoted(text: str) -> list[str]:
    """Extract quoted strings from input."""
    # Match both "double" and 'single' quotes
    matches = re.findall(r'"([^"]+)"|\'([^\']+)\'', text)
    return [m[0] or m[1] for m in matches]
