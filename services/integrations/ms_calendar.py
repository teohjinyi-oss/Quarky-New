"""
Integrations: Microsoft Calendar (Graph API)

Read / create events via Microsoft Graph.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any
from urllib.request import Request, urlopen
from urllib.error import URLError

_GRAPH_BASE = "https://graph.microsoft.com/v1.0"


@dataclass
class MSCalendarEvent:
    """Simplified Microsoft calendar event."""
    id: str
    subject: str
    start: str
    end: str
    location: str = ""
    body: str = ""


class MSCalendarClient:
    """Microsoft Graph calendar client using raw HTTP."""

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

    def upcoming(self, top: int = 10) -> list[MSCalendarEvent]:
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        data = self._get(
            f"/me/calendarview?startdatetime={now}&enddatetime=2099-12-31T00:00:00Z"
            f"&$top={top}&$orderby=start/dateTime"
        )
        events: list[MSCalendarEvent] = []
        for item in data.get("value", []):
            events.append(MSCalendarEvent(
                id=item.get("id", ""),
                subject=item.get("subject", ""),
                start=item.get("start", {}).get("dateTime", ""),
                end=item.get("end", {}).get("dateTime", ""),
                location=item.get("location", {}).get("displayName", ""),
                body=item.get("bodyPreview", ""),
            ))
        return events

    # ── write ────────────────────────────────────────────────

    def create_event(
        self,
        subject: str,
        start: str,
        end: str,
        body: str = "",
        location: str = "",
    ) -> str | None:
        payload: dict[str, Any] = {
            "subject": subject,
            "start": {"dateTime": start, "timeZone": "UTC"},
            "end": {"dateTime": end, "timeZone": "UTC"},
        }
        if body:
            payload["body"] = {"contentType": "Text", "content": body}
        if location:
            payload["location"] = {"displayName": location}
        result = self._post("/me/events", payload)
        return result.get("id")
