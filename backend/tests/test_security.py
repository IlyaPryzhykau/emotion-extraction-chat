"""Unit tests for password hashing and session tokens (no DB needed)."""

import uuid

from app.core.security import (
    hash_password,
    issue_session_token,
    read_session_token,
    verify_password,
)


def test_hash_is_not_plaintext_and_verifies() -> None:
    hashed = hash_password("s3cret-password")
    assert hashed != "s3cret-password"
    assert verify_password("s3cret-password", hashed)


def test_verify_rejects_wrong_password() -> None:
    hashed = hash_password("s3cret-password")
    assert not verify_password("wrong", hashed)


def test_token_round_trips_user_id() -> None:
    user_id = str(uuid.uuid4())
    assert read_session_token(issue_session_token(user_id)) == user_id


def test_tampered_or_garbage_token_returns_none() -> None:
    token = issue_session_token(str(uuid.uuid4()))
    assert read_session_token(token + "x") is None
    assert read_session_token("not-a-token") is None
