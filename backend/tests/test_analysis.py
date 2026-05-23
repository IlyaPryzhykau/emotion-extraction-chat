"""Integration tests for the end-of-session analysis (extractor mocked)."""

import uuid

import pytest
from fastapi.testclient import TestClient
from openai import OpenAIError
from sqlalchemy.orm import Session

from app.db.enums import MessageRole
from app.db.models import Message
from app.llm.extractor import EmotionExtraction, EmotionFinding
from app.llm.taxonomy import EmotionLabel, Intensity
from app.main import app

PASSWORD = "supersecret"


def _signup(client: TestClient) -> None:
    email = f"u_{uuid.uuid4().hex[:8]}@test.com"
    assert (
        client.post(
            "/api/auth/signup", json={"email": email, "password": PASSWORD}
        ).status_code
        == 201
    )


def _conversation_with_message(client: TestClient, db_session: Session) -> str:
    """Create a conversation and seed one user message directly in the DB."""
    conv_id = client.post("/api/conversations").json()["id"]
    db_session.add(
        Message(
            conversation_id=uuid.UUID(conv_id),
            role=MessageRole.USER,
            content="work was rough and I felt stretched too thin",
        )
    )
    db_session.commit()
    return conv_id


def _finding(confidence: float, label: EmotionLabel = EmotionLabel.STRESS) -> EmotionFinding:
    return EmotionFinding(
        label=label,
        intensity=Intensity.HIGH,
        trigger="work",
        evidence="work was rough",
        confidence=confidence,
    )


def _mock_extract(monkeypatch: pytest.MonkeyPatch, extraction: EmotionExtraction) -> None:
    monkeypatch.setattr(
        "app.services.emotion_service.extract_emotions", lambda messages: extraction
    )


def test_analyze_persists_findings_drops_low_confidence_and_closes(
    client: TestClient, db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    _signup(client)
    conv_id = _conversation_with_message(client, db_session)
    # One confident finding kept, one below the 0.5 floor dropped.
    _mock_extract(
        monkeypatch,
        EmotionExtraction(findings=[_finding(0.9), _finding(0.3, EmotionLabel.ANGER)]),
    )

    resp = client.post(f"/api/conversations/{conv_id}/analyze")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 1
    assert body[0]["label"] == "stress/overwhelm"
    assert body[0]["evidence"] == "work was rough"

    detail = client.get(f"/api/conversations/{conv_id}").json()
    assert detail["status"] == "analyzed"
    assert detail["ended_at"] is not None

    report = client.get(f"/api/conversations/{conv_id}/report").json()
    assert len(report) == 1


def test_analyze_with_no_negative_emotions_returns_empty(
    client: TestClient, db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    _signup(client)
    conv_id = _conversation_with_message(client, db_session)
    _mock_extract(monkeypatch, EmotionExtraction(findings=[]))

    resp = client.post(f"/api/conversations/{conv_id}/analyze")
    assert resp.status_code == 200
    assert resp.json() == []
    assert client.get(f"/api/conversations/{conv_id}").json()["status"] == "analyzed"


def test_analyze_empty_conversation_is_400(client: TestClient) -> None:
    _signup(client)
    conv_id = client.post("/api/conversations").json()["id"]
    assert client.post(f"/api/conversations/{conv_id}/analyze").status_code == 400


def test_analyze_twice_is_409(
    client: TestClient, db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    _signup(client)
    conv_id = _conversation_with_message(client, db_session)
    _mock_extract(monkeypatch, EmotionExtraction(findings=[]))

    assert client.post(f"/api/conversations/{conv_id}/analyze").status_code == 200
    assert client.post(f"/api/conversations/{conv_id}/analyze").status_code == 409


def test_analyze_surfaces_extractor_failure_as_503(
    client: TestClient, db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    _signup(client)
    conv_id = _conversation_with_message(client, db_session)

    def boom(messages):
        raise OpenAIError("upstream down")

    monkeypatch.setattr("app.services.emotion_service.extract_emotions", boom)
    assert client.post(f"/api/conversations/{conv_id}/analyze").status_code == 503


def test_analyze_requires_auth_and_ownership(
    client: TestClient, db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Unauthenticated.
    assert (
        client.post(f"/api/conversations/{uuid.uuid4()}/analyze").status_code == 401
    )
    # Authenticated but not the owner -> 404.
    _signup(client)
    conv_id = _conversation_with_message(client, db_session)
    other = TestClient(app)
    _signup(other)
    assert other.post(f"/api/conversations/{conv_id}/analyze").status_code == 404
    assert other.get(f"/api/conversations/{conv_id}/report").status_code == 404
