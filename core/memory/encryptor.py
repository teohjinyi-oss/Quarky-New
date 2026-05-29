"""
Memory v2: Encryption at Rest

Encrypts memory data before writing to disk using Fernet (AES-128-CBC).
Key is generated once and stored in a protected file.
Falls back to plaintext if cryptography is not installed.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional


_fernet = None
_available = True


def _init_fernet(key_file: Path) -> None:
    """Initialize Fernet cipher with stored or new key."""
    global _fernet, _available

    if _fernet is not None:
        return

    try:
        from cryptography.fernet import Fernet

        if key_file.exists():
            key = key_file.read_bytes().strip()
        else:
            key = Fernet.generate_key()
            key_file.parent.mkdir(parents=True, exist_ok=True)
            key_file.write_bytes(key)

        _fernet = Fernet(key)
    except ImportError:
        _available = False


def encrypt(data: str, key_file: Path) -> bytes:
    """Encrypt a string. Returns encrypted bytes."""
    _init_fernet(key_file)
    if _fernet is not None:
        return _fernet.encrypt(data.encode("utf-8"))
    return data.encode("utf-8")


def decrypt(data: bytes, key_file: Path) -> str:
    """Decrypt bytes back to string."""
    _init_fernet(key_file)
    if _fernet is not None:
        return _fernet.decrypt(data).decode("utf-8")
    return data.decode("utf-8")


def encrypt_json(obj: dict | list, key_file: Path) -> bytes:
    """Encrypt a JSON-serializable object."""
    text = json.dumps(obj, ensure_ascii=False)
    return encrypt(text, key_file)


def decrypt_json(data: bytes, key_file: Path) -> dict | list:
    """Decrypt bytes and parse as JSON."""
    text = decrypt(data, key_file)
    return json.loads(text)


def is_available() -> bool:
    """Check if encryption is supported."""
    try:
        from cryptography.fernet import Fernet  # noqa: F401
        return True
    except ImportError:
        return False
