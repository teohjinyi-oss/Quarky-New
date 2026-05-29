"""
Integrations: Gmail

Read / send email via the Gmail API.
"""

from __future__ import annotations

import base64
from dataclasses import dataclass, field
from email.mime.text import MIMEText
from typing import Any

_GMAIL_AVAILABLE = False
try:
    from googleapiclient.discovery import build as google_build  # type: ignore[import-untyped]
    _GMAIL_AVAILABLE = True
except ImportError:
    google_build = None  # type: ignore[assignment]


@dataclass
class Email:
    """A simplified email representation."""
    id: str
    subject: str
    sender: str
    snippet: str
    date: str = ""
    body: str = ""
    labels: list[str] = field(default_factory=list)


class GmailClient:
    """Thin wrapper around the Gmail API."""

    def __init__(self, credentials: Any):
        self._creds = credentials
        self._service: Any = None
        if _GMAIL_AVAILABLE and credentials:
            self._service = google_build("gmail", "v1", credentials=credentials)  # type: ignore[misc]

    @property
    def available(self) -> bool:
        return self._service is not None

    # ── read ─────────────────────────────────────────────────

    def inbox(self, max_results: int = 10) -> list[Email]:
        """Return the latest inbox messages."""
        if not self._service:
            return []
        results = (
            self._service.users()
            .messages()
            .list(userId="me", labelIds=["INBOX"], maxResults=max_results)
            .execute()
        )
        messages = results.get("messages", [])
        emails: list[Email] = []
        for msg in messages:
            detail = (
                self._service.users()
                .messages()
                .get(userId="me", id=msg["id"], format="metadata")
                .execute()
            )
            headers = {h["name"]: h["value"] for h in detail.get("payload", {}).get("headers", [])}
            emails.append(Email(
                id=msg["id"],
                subject=headers.get("Subject", ""),
                sender=headers.get("From", ""),
                snippet=detail.get("snippet", ""),
                date=headers.get("Date", ""),
                labels=detail.get("labelIds", []),
            ))
        return emails

    def unread_count(self) -> int:
        """Count unread inbox messages."""
        if not self._service:
            return 0
        results = (
            self._service.users()
            .messages()
            .list(userId="me", labelIds=["INBOX", "UNREAD"], maxResults=1)
            .execute()
        )
        return results.get("resultSizeEstimate", 0)

    # ── send ─────────────────────────────────────────────────

    def send(self, to: str, subject: str, body: str) -> str | None:
        """Send a plain-text email. Returns message ID or None."""
        if not self._service:
            return None
        message = MIMEText(body)
        message["to"] = to
        message["subject"] = subject
        raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
        result = (
            self._service.users()
            .messages()
            .send(userId="me", body={"raw": raw})
            .execute()
        )
        return result.get("id")
