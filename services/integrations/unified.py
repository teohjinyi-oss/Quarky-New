"""
Integrations: Unified Interface

Single entry point for all email and calendar providers.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from services.integrations.oauth import OAuthManager
from services.integrations.gmail import GmailClient, Email
from services.integrations.outlook import OutlookClient, OutlookEmail
from services.integrations.google_calendar import GoogleCalendarClient, CalendarEvent
from services.integrations.ms_calendar import MSCalendarClient, MSCalendarEvent


@dataclass
class UnifiedEmail:
    """Provider-agnostic email."""
    id: str
    subject: str
    sender: str
    snippet: str
    date: str = ""
    provider: str = ""


@dataclass
class UnifiedEvent:
    """Provider-agnostic calendar event."""
    id: str
    summary: str
    start: str
    end: str
    location: str = ""
    provider: str = ""


class UnifiedIntegrations:
    """Single interface across Google and Microsoft services."""

    def __init__(self, oauth: OAuthManager | None = None):
        self._oauth = oauth or OAuthManager()
        self._gmail: GmailClient | None = None
        self._outlook: OutlookClient | None = None
        self._gcal: GoogleCalendarClient | None = None
        self._mscal: MSCalendarClient | None = None
        self._init_clients()

    def _init_clients(self):
        if self._oauth.is_connected("google"):
            creds = self._oauth.get_google_credentials()
            self._gmail = GmailClient(creds)
            self._gcal = GoogleCalendarClient(creds)
        if self._oauth.is_connected("microsoft"):
            token = self._oauth.get_microsoft_token()
            self._outlook = OutlookClient(token)
            self._mscal = MSCalendarClient(token)

    # ── email ────────────────────────────────────────────────

    def emails(self, max_per_provider: int = 10) -> list[UnifiedEmail]:
        """Fetch emails from all connected providers."""
        result: list[UnifiedEmail] = []
        if self._gmail and self._gmail.available:
            for e in self._gmail.inbox(max_per_provider):
                result.append(UnifiedEmail(
                    id=e.id, subject=e.subject, sender=e.sender,
                    snippet=e.snippet, date=e.date, provider="google",
                ))
        if self._outlook and self._outlook.available:
            for e in self._outlook.inbox(max_per_provider):
                result.append(UnifiedEmail(
                    id=e.id, subject=e.subject, sender=e.sender,
                    snippet=e.snippet, date=e.date, provider="microsoft",
                ))
        return result

    def unread_count(self) -> int:
        total = 0
        if self._gmail and self._gmail.available:
            total += self._gmail.unread_count()
        if self._outlook and self._outlook.available:
            total += self._outlook.unread_count()
        return total

    def send_email(self, to: str, subject: str, body: str, provider: str = "google") -> bool:
        if provider == "google" and self._gmail and self._gmail.available:
            return self._gmail.send(to, subject, body) is not None
        if provider == "microsoft" and self._outlook and self._outlook.available:
            return self._outlook.send(to, subject, body)
        return False

    # ── calendar ─────────────────────────────────────────────

    def events(self, max_per_provider: int = 10) -> list[UnifiedEvent]:
        """Fetch upcoming events from all connected providers."""
        result: list[UnifiedEvent] = []
        if self._gcal and self._gcal.available:
            for e in self._gcal.upcoming(max_per_provider):
                result.append(UnifiedEvent(
                    id=e.id, summary=e.summary, start=e.start,
                    end=e.end, location=e.location, provider="google",
                ))
        if self._mscal and self._mscal.available:
            for e in self._mscal.upcoming(max_per_provider):
                result.append(UnifiedEvent(
                    id=e.id, summary=e.subject, start=e.start,
                    end=e.end, location=e.location, provider="microsoft",
                ))
        return result

    def create_event(
        self,
        summary: str,
        start: str,
        end: str,
        provider: str = "google",
        **kwargs: Any,
    ) -> str | None:
        if provider == "google" and self._gcal and self._gcal.available:
            return self._gcal.create_event(summary, start, end, **kwargs)
        if provider == "microsoft" and self._mscal and self._mscal.available:
            return self._mscal.create_event(summary, start, end, **kwargs)
        return None

    # ── status ───────────────────────────────────────────────

    def connected_providers(self) -> list[str]:
        providers: list[str] = []
        if self._oauth.is_connected("google"):
            providers.append("google")
        if self._oauth.is_connected("microsoft"):
            providers.append("microsoft")
        return providers
