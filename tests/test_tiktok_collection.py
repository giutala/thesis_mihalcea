"""Checks for query building, date windows, and resumable collection."""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any

import pytest

from scripts import tiktok_collection as collection
from scripts.tiktok_client import QuotaExceededError


def test_query_requires_region_and_any_term() -> None:
    query = collection.build_query(["paga in 3 rate"], ["#Klarna"])

    assert query["and"][0]["field_values"] == ["IT"]
    assert query["or"][1]["field_values"] == ["klarna"]
    with pytest.raises(ValueError):
        collection.build_query([], [])


def test_date_windows_skip_incomplete_recent_week() -> None:
    windows = collection.date_windows(
        date(2026, 1, 1), date(2026, 12, 31), today=date(2026, 1, 20)
    )

    assert windows == [
        (date(2026, 1, 1), date(2026, 1, 7)),
        (date(2026, 1, 8), date(2026, 1, 14)),
    ]


def test_date_windows_keep_short_final_window_at_study_end() -> None:
    windows = collection.date_windows(
        date(2026, 1, 1), date(2026, 1, 10), today=date(2026, 2, 1)
    )

    assert windows[-1] == (date(2026, 1, 8), date(2026, 1, 10))


class FakeCollectionClient:
    """Return one page per window and hit the quota on a chosen window."""

    def __init__(self, quota_at: int | None = None) -> None:
        self.calls = 0
        self.quota_at = quota_at
        self.request_count = 0

    def iter_video_pages(self, query: dict[str, Any], start: str, end: str):
        self.calls += 1
        if self.quota_at is not None and self.calls >= self.quota_at:
            raise QuotaExceededError("quota")
        yield {"videos": [{"id": int(start), "username": "u"}], "search_id": "s"}


def test_collection_resumes_and_stops_cleanly_on_quota(tmp_path: Path) -> None:
    query = collection.build_query(["klarna"], [])
    windows = collection.date_windows(
        date(2026, 1, 1), date(2026, 1, 21), today=date(2026, 3, 1)
    )
    first = collection.collect_videos(
        FakeCollectionClient(quota_at=2), query, windows, tmp_path
    )
    assert first["status"].tolist() == ["collected", "pending", "pending"]

    resumed_client = FakeCollectionClient()
    second = collection.collect_videos(resumed_client, query, windows, tmp_path)
    assert second["status"].tolist() == ["done", "collected", "collected"]
    assert resumed_client.calls == 2

    with pytest.raises(ValueError):
        collection.collect_videos(
            resumed_client, collection.build_query(["scalapay"], []), windows, tmp_path
        )
