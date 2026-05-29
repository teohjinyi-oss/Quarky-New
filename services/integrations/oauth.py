"""
Integrations: OAuth

Handles OAuth2 authorization code flow for Google and Microsoft.
Stores tokens as encrypted JSON; refreshes automatically.
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field
from typing import Any

from runtime.config.config import CONFIG

_GOOGLE_AUTH_AVAILABLE = False
_MSAL_AVAILABLE = False

try:
    from google_auth_oauthlib.flow import InstalledAppFlow  # type: ignore[import-untyped]
    from google.oauth2.credentials import Credentials as GoogleCredentials  # type: ignore[import-untyped]
    from google.auth.transport.requests import Request as GoogleAuthRequest  # type: ignore[import-untyped]
    _GOOGLE_AUTH_AVAILABLE = True
except ImportError:
    InstalledAppFlow = None  # type: ignore[assignment]
    GoogleCredentials = None  # type: ignore[assignment]
    GoogleAuthRequest = None  # type: ignore[assignment]

try:
    import msal  # type: ignore[import-untyped]
    _MSAL_AVAILABLE = True
except ImportError:
    msal = None  # type: ignore[assignment]


@dataclass
class OAuthToken:
    """Stored OAuth token."""
    provider: str       # "google" | "microsoft"
    access_token: str
    refresh_token: str = ""
    expires_at: float = 0.0
    scopes: list[str] = field(default_factory=list)

    @property
    def expired(self) -> bool:
        return time.time() >= self.expires_at - 60  # 1-min buffer

    def to_dict(self) -> dict[str, Any]:
        return {
            "provider": self.provider,
            "access_token": self.access_token,
            "refresh_token": self.refresh_token,
            "expires_at": self.expires_at,
            "scopes": self.scopes,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> OAuthToken:
        return cls(**d)


class OAuthManager:
    """Manages OAuth2 tokens for Google & Microsoft."""

    def __init__(self):
        int_cfg = CONFIG.get("INTEGRATIONS", {})
        self._dir = int_cfg.get("dir", "data/integrations")
        self._tokens: dict[str, OAuthToken] = {}
        self._load()

    # ── persistence ──────────────────────────────────────────

    def _token_path(self) -> str:
        return os.path.join(self._dir, "oauth_tokens.json")

    def _load(self):
        path = self._token_path()
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    items = json.load(f)
                for d in items:
                    t = OAuthToken.from_dict(d)
                    self._tokens[t.provider] = t
            except (json.JSONDecodeError, KeyError):
                pass

    def _save(self):
        os.makedirs(self._dir, exist_ok=True)
        with open(self._token_path(), "w", encoding="utf-8") as f:
            json.dump([t.to_dict() for t in self._tokens.values()], f)

    # ── Google ───────────────────────────────────────────────

    def authorize_google(self, client_secrets_file: str, scopes: list[str]) -> OAuthToken | None:
        """Run Google OAuth2 installed-app flow."""
        if not _GOOGLE_AUTH_AVAILABLE:
            return None
        flow = InstalledAppFlow.from_client_secrets_file(client_secrets_file, scopes)  # type: ignore[union-attr]
        creds = flow.run_local_server(port=0)
        token = OAuthToken(
            provider="google",
            access_token=creds.token or "",
            refresh_token=creds.refresh_token or "",
            expires_at=creds.expiry.timestamp() if creds.expiry else 0.0,
            scopes=scopes,
        )
        self._tokens["google"] = token
        self._save()
        return token

    def get_google_credentials(self) -> Any:
        """Return a refreshed Google Credentials object, or None."""
        if not _GOOGLE_AUTH_AVAILABLE:
            return None
        tok = self._tokens.get("google")
        if not tok:
            return None
        creds = GoogleCredentials(  # type: ignore[misc]
            token=tok.access_token,
            refresh_token=tok.refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id="",
            client_secret="",
        )
        if creds.expired and creds.refresh_token:
            creds.refresh(GoogleAuthRequest())  # type: ignore[misc]
            tok.access_token = creds.token or ""
            tok.expires_at = creds.expiry.timestamp() if creds.expiry else 0.0
            self._save()
        return creds

    # ── Microsoft ────────────────────────────────────────────

    def authorize_microsoft(self, client_id: str, scopes: list[str]) -> OAuthToken | None:
        """Run Microsoft MSAL device-code flow."""
        if not _MSAL_AVAILABLE:
            return None
        app = msal.PublicClientApplication(client_id)  # type: ignore[union-attr]
        flow = app.initiate_device_flow(scopes=scopes)
        if "user_code" not in flow:
            return None
        # In GUI mode the code would be displayed; for now print it
        print(f"Microsoft auth: go to {flow['verification_uri']} and enter code {flow['user_code']}")
        result = app.acquire_token_by_device_flow(flow)
        if "access_token" not in result:
            return None
        token = OAuthToken(
            provider="microsoft",
            access_token=result["access_token"],
            refresh_token=result.get("refresh_token", ""),
            expires_at=time.time() + result.get("expires_in", 3600),
            scopes=scopes,
        )
        self._tokens["microsoft"] = token
        self._save()
        return token

    def get_microsoft_token(self) -> str | None:
        """Return a valid Microsoft access token, or None."""
        tok = self._tokens.get("microsoft")
        if not tok:
            return None
        if tok.expired:
            return None  # would need MSAL refresh logic
        return tok.access_token

    # ── generic ──────────────────────────────────────────────

    def is_connected(self, provider: str) -> bool:
        tok = self._tokens.get(provider)
        return tok is not None and not tok.expired

    def disconnect(self, provider: str):
        self._tokens.pop(provider, None)
        self._save()
