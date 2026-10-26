"""Checks for the TikTok Research API client's retry, quota, and auth handling."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import requests

from scripts.tiktok_client import (
    QuotaExceededError,
    TikTokAPIError,
    TikTokClient,
    read_credentials,
)


class FakeResponse:
    def __init__(self, status_code: int, payload: dict[str, Any]) -> None:
        self.status_code = status_code
        self._payload = payload

    def json(self) -> dict[str, Any]:
        return self._payload


class FakeSession:
    """Serve a token, then queued data responses, recording request bodies."""

    def __init__(self, responses: list[Any]) -> None:
        self.responses = responses
        self.bodies: list[dict[str, Any]] = []
        self.token_requests = 0

    def post(self, url: str, **kwargs: Any) -> FakeResponse:
        if url.endswith("/oauth/token/"):
            self.token_requests += 1
            return FakeResponse(200, {"access_token": "token", "expires_in": 7200})
        self.bodies.append(dict(kwargs.get("json") or {}))
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


def _ok(data: dict[str, Any]) -> FakeResponse:
    return FakeResponse(200, {"data": data, "error": {"code": "ok"}})


def _error(status: int, code: str) -> FakeResponse:
    return FakeResponse(status, {"error": {"code": code, "message": code}})


def _client(responses: list[Any]) -> tuple[TikTokClient, FakeSession]:
    session = FakeSession(responses)
    client = TikTokClient("key", "secret", session=session, sleep=lambda _: None)  # type: ignore[arg-type]
    return client, session


def test_client_follows_pages_with_cursor_and_search_id() -> None:
    client, session = _client(
        [
            _ok(
                {
                    "videos": [{"id": 1}],
                    "has_more": True,
                    "cursor": 100,
                    "search_id": "s",
                }
            ),
            _ok({"videos": [], "has_more": True, "cursor": 200, "search_id": "s"}),
            _ok({"videos": [{"id": 2}], "has_more": False}),
        ]
    )
    pages = list(client.iter_video_pages({"and": []}, "20260101", "20260107"))

    assert [len(page["videos"]) for page in pages] == [1, 0, 1]
    assert session.bodies[1]["cursor"] == 100
    assert session.bodies[1]["search_id"] == "s"


def test_client_retries_rate_limit_then_succeeds() -> None:
    client, _ = _client([_error(429, "rate_limit_exceeded"), _ok({"has_more": False})])
    pages = list(client.iter_video_pages({}, "20260101", "20260107"))

    assert len(pages) == 1
    assert client.request_count == 2


def test_client_retries_dropped_connections() -> None:
    client, _ = _client([requests.ConnectionError("dropped"), _ok({"has_more": False})])
    pages = list(client.iter_video_pages({}, "20260101", "20260107"))

    assert len(pages) == 1
    assert client.request_count == 2


def test_client_raises_quota_error_when_rate_limit_persists() -> None:
    client, _ = _client([_error(429, "rate_limit_exceeded") for _ in range(10)])

    with pytest.raises(QuotaExceededError):
        list(client.iter_video_pages({}, "20260101", "20260107"))


def test_client_stops_immediately_on_daily_quota_code() -> None:
    client, _ = _client([_error(429, "daily_quota_limit_exceeded")])

    with pytest.raises(QuotaExceededError):
        list(client.iter_video_pages({}, "20260101", "20260107"))
    assert client.request_count == 1


def test_client_does_not_retry_invalid_requests() -> None:
    client, _ = _client([_error(400, "invalid_params")])

    with pytest.raises(TikTokAPIError):
        list(client.iter_video_pages({}, "20260101", "20260107"))
    assert client.request_count == 1


def test_client_refreshes_token_once_on_401() -> None:
    client, session = _client([_error(401, "access_token_invalid"), _ok({})])
    client.user_info("someone")

    assert session.token_requests == 2


def test_credentials_prefer_environment_over_env_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(
        "# comment\nTIKTOK_CLIENT_KEY='file-key'\nTIKTOK_CLIENT_SECRET=file-secret\n",
        encoding="utf-8",
    )
    monkeypatch.delenv("TIKTOK_CLIENT_KEY", raising=False)
    monkeypatch.delenv("TIKTOK_CLIENT_SECRET", raising=False)
    assert read_credentials(env_file) == ("file-key", "file-secret")

    monkeypatch.setenv("TIKTOK_CLIENT_KEY", "env-key")
    assert read_credentials(env_file) == ("env-key", "file-secret")
    assert read_credentials(tmp_path / "missing.env") is None
