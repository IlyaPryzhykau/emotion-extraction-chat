"""Integration tests for the conversations CRUD endpoints."""

import uuid

from fastapi.testclient import TestClient

from app.main import app

PASSWORD = "supersecret"


def _signup(client: TestClient) -> str:
    email = f"u_{uuid.uuid4().hex[:8]}@test.com"
    resp = client.post("/api/auth/signup", json={"email": email, "password": PASSWORD})
    assert resp.status_code == 201
    return email


def test_create_conversation_starts_active(client: TestClient) -> None:
    _signup(client)
    resp = client.post("/api/conversations")
    assert resp.status_code == 201
    body = resp.json()
    assert body["status"] == "active"
    assert body["ended_at"] is None
    assert uuid.UUID(body["id"])  # valid UUID


def test_get_conversation_returns_empty_message_history(client: TestClient) -> None:
    _signup(client)
    conv_id = client.post("/api/conversations").json()["id"]
    resp = client.get(f"/api/conversations/{conv_id}")
    assert resp.status_code == 200
    assert resp.json()["messages"] == []


def test_list_returns_user_conversations(client: TestClient) -> None:
    _signup(client)
    client.post("/api/conversations")
    client.post("/api/conversations")
    resp = client.get("/api/conversations")
    assert resp.status_code == 200
    assert len(resp.json()) == 2


def test_conversations_require_authentication(client: TestClient) -> None:
    assert client.get("/api/conversations").status_code == 401
    assert client.post("/api/conversations").status_code == 401


def test_cannot_access_another_users_conversation(client: TestClient) -> None:
    _signup(client)
    conv_id = client.post("/api/conversations").json()["id"]

    # A second user (separate cookie jar, same test DB) must not see it: 404, not 403,
    # so existence isn't revealed.
    other = TestClient(app)
    _signup(other)
    assert other.get(f"/api/conversations/{conv_id}").status_code == 404
