"""Integration tests for the streaming message endpoint.

The LLM is mocked (we never call OpenAI in tests): we patch ``stream_chat`` to
yield fixed deltas, which lets us assert the SSE framing, persistence, the
guardrails, and — importantly — that the conversationalist is sent a prompt with
no "emotion" framing.
"""

import json
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.enums import ConversationStatus
from app.db.models import Conversation

PASSWORD = "supersecret"
DELTAS = ["Hey", " there", "!"]


def _signup(client: TestClient) -> None:
    email = f"u_{uuid.uuid4().hex[:8]}@test.com"
    assert (
        client.post(
            "/api/auth/signup", json={"email": email, "password": PASSWORD}
        ).status_code
        == 201
    )


def _start_conversation(client: TestClient) -> str:
    return client.post("/api/conversations").json()["id"]


def _parse_sse(text: str) -> list[dict]:
    return [json.loads(line[6:]) for line in text.splitlines() if line.startswith("data: ")]


@pytest.fixture
def mock_stream(monkeypatch: pytest.MonkeyPatch):
    """Patch the LLM to yield DELTAS; return a dict capturing the messages sent."""
    captured: dict = {}

    def fake_stream(messages):
        captured["messages"] = messages
        yield from DELTAS

    monkeypatch.setattr("app.api.conversations.stream_chat", fake_stream)
    return captured


def test_streams_deltas_and_persists_both_turns(
    client: TestClient, mock_stream: dict
) -> None:
    _signup(client)
    conv_id = _start_conversation(client)

    resp = client.post(f"/api/conversations/{conv_id}/messages", json={"content": "hello"})
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/event-stream")

    events = _parse_sse(resp.text)
    assert "".join(e["delta"] for e in events if "delta" in e) == "Hey there!"
    done = [e for e in events if e.get("done")]
    assert len(done) == 1 and uuid.UUID(done[0]["message_id"])

    detail = client.get(f"/api/conversations/{conv_id}").json()
    by_role = {m["role"]: m["content"] for m in detail["messages"]}
    assert len(detail["messages"]) == 2
    assert by_role["user"] == "hello"
    assert by_role["assistant"] == "Hey there!"


def test_conversationalist_prompt_has_no_emotion_framing(
    client: TestClient, mock_stream: dict
) -> None:
    _signup(client)
    conv_id = _start_conversation(client)
    client.post(f"/api/conversations/{conv_id}/messages", json={"content": "busy day"})

    sent = mock_stream["messages"]
    assert sent[0]["role"] == "system"
    # Core design rule: the conversationalist must never be framed around emotions.
    assert "emotion" not in sent[0]["content"].lower()
    # The user's turn is the last message handed to the model.
    assert sent[-1] == {"role": "user", "content": "busy day"}


def test_message_requires_authentication(client: TestClient) -> None:
    resp = client.post(
        f"/api/conversations/{uuid.uuid4()}/messages", json={"content": "x"}
    )
    assert resp.status_code == 401


def test_message_to_missing_conversation_is_404(client: TestClient) -> None:
    _signup(client)
    resp = client.post(
        f"/api/conversations/{uuid.uuid4()}/messages", json={"content": "x"}
    )
    assert resp.status_code == 404


def test_message_over_length_limit_is_422(client: TestClient) -> None:
    _signup(client)
    conv_id = _start_conversation(client)
    too_long = "x" * (settings.max_message_chars + 1)
    resp = client.post(
        f"/api/conversations/{conv_id}/messages", json={"content": too_long}
    )
    assert resp.status_code == 422


def test_hard_cap_blocks_further_messages(
    client: TestClient, mock_stream: dict, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "hard_cap_turns", 1)
    _signup(client)
    conv_id = _start_conversation(client)

    assert (
        client.post(
            f"/api/conversations/{conv_id}/messages", json={"content": "one"}
        ).status_code
        == 200
    )
    # Second user turn would exceed the cap.
    assert (
        client.post(
            f"/api/conversations/{conv_id}/messages", json={"content": "two"}
        ).status_code
        == 409
    )


def test_cannot_post_to_analyzed_conversation(
    client: TestClient, db_session: Session, mock_stream: dict
) -> None:
    _signup(client)
    conv_id = _start_conversation(client)

    conversation = db_session.get(Conversation, uuid.UUID(conv_id))
    conversation.status = ConversationStatus.ANALYZED
    db_session.commit()

    resp = client.post(f"/api/conversations/{conv_id}/messages", json={"content": "x"})
    assert resp.status_code == 409
