"""Tests for the REST API endpoints."""

import pytest


@pytest.fixture
def client():
    """Create a test client for the API."""
    try:
        from fastapi.testclient import TestClient
        from interfaces.api.server import app
        return TestClient(app)
    except ImportError:
        pytest.skip("fastapi or httpx not installed")


class TestAPIHealth:
    def test_health(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"


class TestAPIChat:
    def test_chat(self, client):
        resp = client.post("/chat", json={"text": "hello"})
        assert resp.status_code == 200
        data = resp.json()
        assert "response" in data
        assert "metadata" in data

    def test_chat_empty_rejected(self, client):
        resp = client.post("/chat", json={"text": ""})
        assert resp.status_code == 422  # validation error


class TestAPIMemory:
    def test_memory_stats(self, client):
        resp = client.get("/memory/stats")
        assert resp.status_code == 200
        data = resp.json()
        assert "temporary" in data

    def test_memory_search(self, client):
        resp = client.get("/memory/search", params={"q": "test"})
        assert resp.status_code == 200
        data = resp.json()
        assert "total" in data

    def test_memory_store_permanent(self, client):
        resp = client.post("/memory/permanent", json={
            "text": "test fact",
            "tags": ["test"],
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"]


class TestAPIActions:
    def test_actions_recent(self, client):
        resp = client.get("/actions/recent")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_actions_stats(self, client):
        resp = client.get("/actions/stats")
        assert resp.status_code == 200
        data = resp.json()
        assert "total_actions" in data

    def test_actions_undo(self, client):
        resp = client.post("/actions/undo")
        assert resp.status_code == 200
        data = resp.json()
        assert "message" in data


class TestAPISystem:
    def test_system_status(self, client):
        resp = client.get("/system/status")
        assert resp.status_code == 200
        data = resp.json()
        assert "timestamp" in data

    def test_system_config(self, client):
        resp = client.get("/system/config")
        assert resp.status_code == 200
        data = resp.json()
        assert "fast_threshold" in data
