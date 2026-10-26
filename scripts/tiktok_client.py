"""Minimal TikTok Research API client with explicit error handling.

The client replaces the ``TikTokResearchApi`` package for collection because
that package retries every error, including invalid requests and exhausted
quota, sixty times without surfacing it, and only checks ``max_total`` after a
whole page. Here, retryable errors back off and then raise, and every other
error raises immediately so that no partial result is mistaken for a complete
one.
"""

from __future__ import annotations

import logging
import os
import time
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import requests

LOGGER = logging.getLogger(__name__)

BASE_URL = "https://open.tiktokapis.com"
VIDEO_FIELDS = (
    "id,username,create_time,region_code,video_description,voice_to_text,"
    "hashtag_names,view_count,like_count,comment_count,share_count,"
    "video_duration,is_stem_verified"
)
COMMENT_FIELDS = "id,video_id,text,like_count,reply_count,parent_comment_id,create_time"
USER_FIELDS = (
    "display_name,bio_description,is_verified,follower_count,following_count,"
    "likes_count,video_count"
)
MAX_PAGE_SIZE = 100
RETRY_DELAYS_SECONDS: tuple[float, ...] = (2, 4, 8, 16, 32, 60)
TOKEN_REFRESH_MARGIN_SECONDS = 300


def read_credentials(env_file: Path) -> tuple[str, str] | None:
    """Return the client key and secret from the environment or a ``.env`` file.

    Parameters
    ----------
    env_file : pathlib.Path
        Ignored ``KEY=value`` file, read only when the environment lacks a value.

    Returns
    -------
    tuple of str or None
        ``(client_key, client_secret)``, or ``None`` when either is missing.

    Raises
    ------
    OSError
        If the file exists but cannot be read.

    Notes
    -----
    Environment variables take precedence so that a shell session can override
    the file. Values are never logged.
    """
    values = {}
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            name, separator, value = line.partition("=")
            if separator and not name.strip().startswith("#"):
                values[name.strip()] = value.strip().strip("'\"")
    key = os.environ.get("TIKTOK_CLIENT_KEY") or values.get("TIKTOK_CLIENT_KEY")
    secret = os.environ.get("TIKTOK_CLIENT_SECRET") or values.get(
        "TIKTOK_CLIENT_SECRET"
    )
    return (key, secret) if key and secret else None


class TikTokAPIError(RuntimeError):
    """Raised for a non-retryable API error or exhausted retries."""


class QuotaExceededError(TikTokAPIError):
    """Raised when rate-limit responses persist; usually the daily quota."""


@dataclass
class TikTokClient:
    """Authenticated client for the video, comment, and user research endpoints.

    Parameters
    ----------
    client_key : str
        Research API client key.
    client_secret : str
        Research API client secret.
    session : requests.Session, optional
        HTTP session; injectable for tests.
    sleep : callable, default=time.sleep
        Delay function used between retries; injectable for tests.

    Notes
    -----
    ``request_count`` counts every data request sent, including retries, so it
    can be compared with the daily quota shown in the developer portal.
    """

    client_key: str
    client_secret: str
    session: requests.Session = field(default_factory=requests.Session)
    sleep: Callable[[float], None] = time.sleep
    request_count: int = 0
    _token: str = field(default="", repr=False)
    _token_expires_at: float = field(default=0.0, repr=False)

    def _refresh_token(self) -> None:
        response = self.session.post(
            f"{BASE_URL}/v2/oauth/token/",
            data={
                "client_key": self.client_key,
                "client_secret": self.client_secret,
                "grant_type": "client_credentials",
            },
            timeout=30,
        )
        payload = response.json()
        if response.status_code != 200 or "access_token" not in payload:
            raise TikTokAPIError(
                f"Token request failed ({response.status_code}): "
                f"{payload.get('error')} {payload.get('error_description', '')}"
            )
        self._token = str(payload["access_token"])
        self._token_expires_at = time.time() + float(payload.get("expires_in", 7200))
        LOGGER.info("Obtained client access token")

    def _post(self, path: str, fields: str, body: dict[str, Any]) -> dict[str, Any]:
        """Send one data request with token refresh and bounded retries.

        Parameters
        ----------
        path : str
            Endpoint path below ``BASE_URL``.
        fields : str
            Comma-separated response fields.
        body : dict
            JSON request body.

        Returns
        -------
        dict
            The response ``data`` object.

        Raises
        ------
        QuotaExceededError
            If HTTP 429 persists after all retry delays.
        TikTokAPIError
            For any other error status or exhausted server-error retries.

        Notes
        -----
        A 401 triggers one token refresh; 429 and 5xx responses and network
        errors are retried with growing delays because TikTok reports both
        transient throttling and backend cache warm-up this way.
        """
        refreshed = False
        attempt = 0
        while True:
            if time.time() > self._token_expires_at - TOKEN_REFRESH_MARGIN_SECONDS:
                self._refresh_token()
            self.request_count += 1
            try:
                response = self.session.post(
                    f"{BASE_URL}{path}",
                    params={"fields": fields},
                    json=body,
                    headers={"Authorization": f"Bearer {self._token}"},
                    timeout=60,
                )
            except (requests.ConnectionError, requests.Timeout) as network_error:
                # Dropped connections (sleep, Wi-Fi changes) are transient.
                if attempt >= len(RETRY_DELAYS_SECONDS):
                    raise TikTokAPIError(f"{path} failed: {network_error}") from (
                        network_error
                    )
                delay = RETRY_DELAYS_SECONDS[attempt]
                attempt += 1
                LOGGER.warning("%s network error; retrying in %s s", path, delay)
                self.sleep(delay)
                continue
            try:
                payload = response.json()
            except ValueError:
                payload = {}
            error = payload.get("error") or {}
            code = error.get("code", "")
            if response.status_code == 200 and code in ("", "ok"):
                return dict(payload.get("data") or {})
            message = (
                f"{path} failed ({response.status_code}, {code}): "
                f"{error.get('message', '')} [log_id={error.get('log_id', '')}]"
            )
            if response.status_code == 401 and not refreshed:
                refreshed = True
                self._token_expires_at = 0.0
                continue
            if code == "daily_quota_limit_exceeded":
                raise QuotaExceededError(message)
            retryable = response.status_code == 429 or response.status_code >= 500
            if not retryable:
                raise TikTokAPIError(message)
            if attempt >= len(RETRY_DELAYS_SECONDS):
                if response.status_code == 429:
                    raise QuotaExceededError(message)
                raise TikTokAPIError(message)
            delay = RETRY_DELAYS_SECONDS[attempt]
            attempt += 1
            LOGGER.warning("%s; retrying in %s s", message, delay)
            self.sleep(delay)

    def iter_video_pages(
        self,
        query: dict[str, Any],
        start_date: str,
        end_date: str,
        fields: str = VIDEO_FIELDS,
        max_count: int = MAX_PAGE_SIZE,
        max_pages: int | None = None,
    ) -> Iterator[dict[str, Any]]:
        """Yield result pages for one video query and date window.

        Parameters
        ----------
        query : dict
            Query object with ``and``, ``or``, and ``not`` condition lists.
        start_date, end_date : str
            Inclusive ``YYYYMMDD`` bounds; at most 30 days apart.
        fields : str, default=VIDEO_FIELDS
            Comma-separated video fields.
        max_count : int, default=100
            Page size requested from the API.
        max_pages : int or None, default=None
            Stop after this many pages; ``None`` follows ``has_more``.

        Yields
        ------
        dict
            Page data with ``videos``, ``cursor``, ``has_more``, ``search_id``.

        Raises
        ------
        TikTokAPIError
            Propagated from the request layer.

        Notes
        -----
        Pages may hold fewer than ``max_count`` videos, or none, while
        ``has_more`` is still true; pagination therefore follows ``has_more``
        rather than page length.
        """
        body: dict[str, Any] = {
            "query": query,
            "start_date": start_date,
            "end_date": end_date,
            "max_count": max_count,
        }
        pages = 0
        while True:
            data = self._post("/v2/research/video/query/", fields, body)
            pages += 1
            yield data
            if not data.get("has_more") or (max_pages and pages >= max_pages):
                return
            body["cursor"] = data.get("cursor")
            body["search_id"] = data.get("search_id")

    def iter_comments(
        self, video_id: str, fields: str = COMMENT_FIELDS
    ) -> Iterator[dict[str, Any]]:
        """Yield all comments the API returns for one video.

        Parameters
        ----------
        video_id : str
            Numeric video ID as text.
        fields : str, default=COMMENT_FIELDS
            Comma-separated comment fields.

        Yields
        ------
        dict
            One comment record.

        Raises
        ------
        TikTokAPIError
            Propagated from the request layer.

        Notes
        -----
        TikTok caps the comments returned per video, so very popular videos are
        truncated; this is recorded as a corpus limitation.
        """
        body: dict[str, Any] = {"video_id": int(video_id), "max_count": MAX_PAGE_SIZE}
        while True:
            data = self._post("/v2/research/video/comment/list/", fields, body)
            yield from data.get("comments") or []
            if not data.get("has_more"):
                return
            body["cursor"] = data.get("cursor")

    def user_info(
        self, username: str, fields: str = USER_FIELDS
    ) -> dict[str, Any] | None:
        """Return a public profile, or ``None`` when TikTok does not serve it.

        Parameters
        ----------
        username : str
            TikTok handle without ``@``.
        fields : str, default=USER_FIELDS
            Comma-separated profile fields.

        Returns
        -------
        dict or None
            Profile data, or ``None`` for private, deleted, or unknown accounts.

        Raises
        ------
        QuotaExceededError
            If the user-info quota is exhausted.

        Notes
        -----
        Private and deleted accounts return a client error, which is expected
        and recorded rather than raised.
        """
        try:
            return self._post("/v2/research/user/info/", fields, {"username": username})
        except QuotaExceededError:
            raise
        except TikTokAPIError as error:
            LOGGER.info("No profile for %s: %s", username, error)
            return None
