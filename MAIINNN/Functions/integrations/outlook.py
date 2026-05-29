"""
Integrations: Outlook / Microsoft Graph

Read / send email via Microsoft Graph API.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any
from urllib.request import Request, urlopen
from urllib.error import URLError

_GRAPH_BASE = "https://graph.microsoft.com/v1.0"


@dataclass
class OutlookEmail:
    """Simplified Outlook email."""
    id: str
    subject: str
    sender: str
    snippet: str
    date: str = ""
    is_read: bool = False


class OutlookClient:
    """Microsoft Graph mail client using raw HTTP (no extra deps)."""

    def __init__(self, access_token: str | None):
        self._token = access_token

    @property
    def available(self) -> bool:
        return self._token is not None

    def _get(self, path: str) -> dict[str, Any]:
        if not self._token:
            return {}
        req = Request(f"{_GRAPH_BASE}{path}")
        req.add_header("Authorization", f"Bearer {self._token}")
        req.add_header("Accept", "application/json")
        try:
            with urlopen(req, timeout=10) as resp:
                return json.loads(resp.read())
        except (URLError, json.JSONDecodeError):
            return {}

    def _post(self, path: str, body: dict[str, Any]) -> dict[str, Any]:
        if not self._token:
            return {}
        data = json.dumps(body).encode()
        req = Request(f"{_GRAPH_BASE}{path}", data=data, method="POST")
        req.add_header("Authorization", f"Bearer {self._token}")
        req.add_header("Content-Type", "application/json")
        try:
            with urlopen(req, timeout=10) as resp:
                return json.loads(resp.read())
        except (URLError, json.JSONDecodeError):
            return {}

    # ── read ─────────────────────────────────────────────────

    def inbox(self, top: int = 10) -> list[OutlookEmail]:
        data = self._get(f"/me/mailFolders/inbox/messages?$top={top}&$orderby=receivedDateTime desc")
        emails: list[OutlookEmail] = []
        for m in data.get("value", []):
            sender_info = m.get("from", {}).get("emailAddress", {})
            emails.append(OutlookEmail(
                id=m.get("id", ""),
                subject=m.get("subject", ""),
                sender=sender_info.get("address", ""),
                snippet=m.get("bodyPreview", ""),
                date=m.get("receivedDateTime", ""),
                is_read=m.get("isRead", False),
            ))
        return emails

    def unread_count(self) -> int:
        data = self._get("/me/mailFolders/inbox")
        return data.get("unreadItemCount", 0)

    # ── send ─────────────────────────────────────────────────

    def send(self, to: str, subject: str, body: str) -> bool:
        payload = {
            "message": {
                "subject": subject,
                "body": {"contentType": "Text", "content": body},
                "toRecipients": [{"emailAddress": {"address": to}}],
            }
        }
        self._post("/me/sendMail", payload)
        return True
