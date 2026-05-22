"""Integration tests for the auth API, exercised through the HTTP layer."""

import uuid

from fastapi.testclient import TestClient

PASSWORD = "supersecret"


def _fresh_email() -> str:
    return f"user_{uuid.uuid4().hex[:8]}@test.com"


def test_signup_returns_user_and_sets_cookie(client: TestClient) -> None:
    email = _fresh_email()
    resp = client.post("/api/auth/signup", json={"email": email, "password": PASSWORD})
    assert resp.status_code == 201
    body = resp.json()
    assert body["email"] == email
    assert "id" in body
    assert "password_hash" not in body  # never leak the hash
    assert "session" in resp.cookies


def test_signup_normalizes_email(client: TestClient) -> None:
    email = _fresh_email().upper()
    resp = client.post(
        "/api/auth/signup", json={"email": f"  {email}  ", "password": PASSWORD}
    )
    assert resp.status_code == 201
    assert resp.json()["email"] == email.lower()


def test_signup_duplicate_is_409(client: TestClient) -> None:
    email = _fresh_email()
    client.post("/api/auth/signup", json={"email": email, "password": PASSWORD})
    resp = client.post("/api/auth/signup", json={"email": email, "password": PASSWORD})
    assert resp.status_code == 409


def test_signup_rejects_short_password_and_bad_email(client: TestClient) -> None:
    assert (
        client.post(
            "/api/auth/signup", json={"email": _fresh_email(), "password": "short"}
        ).status_code
        == 422
    )
    assert (
        client.post(
            "/api/auth/signup", json={"email": "not-an-email", "password": PASSWORD}
        ).status_code
        == 422
    )


def test_login_succeeds_and_fails_appropriately(client: TestClient) -> None:
    email = _fresh_email()
    client.post("/api/auth/signup", json={"email": email, "password": PASSWORD})
    client.post("/api/auth/logout")

    assert (
        client.post(
            "/api/auth/login", json={"email": email, "password": PASSWORD}
        ).status_code
        == 200
    )
    assert (
        client.post(
            "/api/auth/login", json={"email": email, "password": "wrong"}
        ).status_code
        == 401
    )


def test_me_requires_authentication(client: TestClient) -> None:
    assert client.get("/api/auth/me").status_code == 401


def test_me_returns_current_user_when_logged_in(client: TestClient) -> None:
    email = _fresh_email()
    client.post("/api/auth/signup", json={"email": email, "password": PASSWORD})
    resp = client.get("/api/auth/me")  # TestClient keeps the session cookie
    assert resp.status_code == 200
    assert resp.json()["email"] == email


def test_logout_clears_session(client: TestClient) -> None:
    email = _fresh_email()
    client.post("/api/auth/signup", json={"email": email, "password": PASSWORD})
    assert client.get("/api/auth/me").status_code == 200
    assert client.post("/api/auth/logout").status_code == 204
    assert client.get("/api/auth/me").status_code == 401
