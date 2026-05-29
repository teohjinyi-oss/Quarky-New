"""
Integrations: Google Calendar

Read / create events via the Google Calendar API.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

_GCAL_AVAILABLE = False
try:
    from googleapiclient.discovery import build as google_build  # type: ignore[import-untyped]
    _GCAL_AVAILABLE = True
except ImportError:
    google_build = None  # type: ignore[assignment]


@dataclass
class CalendarEvent:
    """A simplified calendar event."""
    id: str
    summary: str
    start: str
    end: str
    location: str = ""
    description: str = ""


class GoogleCalendarClient:
    """Thin wrapper around the Google Calendar API."""

    def __init__(self, credentials: Any):
        self._creds = credentials
        self._service: Any = None
        if _GCAL_AVAILABLE and credentials:
            self._service = google_build("calendar", "v3", credentials=credentials)  # type: ignore[misc]

    @property
    def available(self) -> bool:
        return self._service is not None

    # ── read ─────────────────────────────────────────────────

    def upcoming(self, max_results: int = 10) -> list[CalendarEvent]:
        """Return upcoming events from the primary calendar."""
        if not self._service:
            return []
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc).isoformat()
        result = (
            self._service.events()
            .list(
                calendarId="primary",
                timeMin=now,
                maxResults=max_results,
                singleEvents=True,
                orderBy="startTime",
            )
            .execute()
        )
        events: list[CalendarEvent] = []
        for item in result.get("items", []):
            events.append(CalendarEvent(
                id=item.get("id", ""),
                summary=item.get("summary", ""),
                start=item.get("start", {}).get("dateTime", item.get("start", {}).get("date", "")),
                end=item.get("end", {}).get("dateTime", item.get("end", {}).get("date", "")),
                location=item.get("location", ""),
                description=item.get("description", ""),
            ))
        return events

    # ── write ────────────────────────────────────────────────

    def create_event(
        self,
        summary: str,
        start: str,
        end: str,
        description: str = "",
        location: str = "",
    ) -> str | None:
        """Create a calendar event. Returns event ID or None."""
        if not self._service:
            return None
        body: dict[str, Any] = {
            "summary": summary,
            "start": {"dateTime": start},
            "end": {"dateTime": end},
        }
        if description:
            body["description"] = description
        if location:
            body["location"] = location
        result = (
            self._service.events()
            .insert(calendarId="primary", body=body)
            .execute()
        )
        return result.get("id")
