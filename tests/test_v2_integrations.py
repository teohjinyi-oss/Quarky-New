"""
Tests for v2 Integrations: OAuth, Gmail, Outlook, Calendar, Unified
"""

import pytest


class TestOAuthManager:
    def test_init(self):
        from services.integrations.oauth import OAuthManager
        om = OAuthManager()
        assert not om.is_connected("google")
        assert not om.is_connected("microsoft")

    def test_disconnect_nonexistent(self):
        from services.integrations.oauth import OAuthManager
        om = OAuthManager()
        om.disconnect("google")  # should not raise


class TestGmailClient:
    def test_unavailable(self):
        from services.integrations.gmail import GmailClient
        gc = GmailClient(credentials=None)
        assert not gc.available
        assert gc.inbox() == []
        assert gc.unread_count() == 0


class TestOutlookClient:
    def test_unavailable(self):
        from services.integrations.outlook import OutlookClient
        oc = OutlookClient(access_token=None)
        assert not oc.available
        assert oc.inbox() == []


class TestGoogleCalendarClient:
    def test_unavailable(self):
        from services.integrations.google_calendar import GoogleCalendarClient
        gc = GoogleCalendarClient(credentials=None)
        assert not gc.available
        assert gc.upcoming() == []


class TestMSCalendarClient:
    def test_unavailable(self):
        from services.integrations.ms_calendar import MSCalendarClient
        mc = MSCalendarClient(access_token=None)
        assert not mc.available
        assert mc.upcoming() == []


class TestUnifiedIntegrations:
    def test_no_providers(self):
        from services.integrations.unified import UnifiedIntegrations
        ui = UnifiedIntegrations()
        assert ui.connected_providers() == []
        assert ui.emails() == []
        assert ui.events() == []
        assert ui.unread_count() == 0
