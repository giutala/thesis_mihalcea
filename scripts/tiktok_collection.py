"""Resumable collection of the Italian BNPL TikTok corpus.

Each weekly window, profile, and comment thread is written to its own JSON
Lines file as soon as it is complete, so a run interrupted by the daily quota
resumes where it stopped. The query and field list are frozen in
``query_config.json``; resuming with a different query is refused so that one
corpus never mixes two search definitions.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Iterable, Sequence
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

import pandas as pd

from scripts._common import RAW_DATA
from scripts.tiktok_client import (
    VIDEO_FIELDS,
    QuotaExceededError,
    TikTokAPIError,
    TikTokClient,
)

LOGGER = logging.getLogger(__name__)
RAW_TIKTOK = RAW_DATA / "tiktok"
REGION_CODES: tuple[str, ...] = ("IT",)
WINDOW_DAYS = 7
# Recent days are skipped because TikTok indexes new videos with a delay.
INDEXING_LAG_DAYS = 3


def build_query(
    keywords: Sequence[str],
    hashtags: Sequence[str],
    region_codes: Sequence[str] = REGION_CODES,
) -> dict[str, Any]:
    """Build a video query: Italian accounts and any keyword or hashtag.

    Parameters
    ----------
    keywords : sequence of str
        Phrases matched against video descriptions.
    hashtags : sequence of str
        Hashtag names without ``#``.
    region_codes : sequence of str, default=("IT",)
        Creator account regions.

    Returns
    -------
    dict
        Research API query with ``and``, ``or``, and ``not`` lists.

    Raises
    ------
    ValueError
        If neither keywords nor hashtags are supplied.

    Notes
    -----
    Conditions in ``or`` require at least one match, so a video qualifies
    through a keyword, a hashtag, or both.
    """
    if not keywords and not hashtags:
        raise ValueError("At least one keyword or hashtag is required")
    any_of = []
    if keywords:
        any_of.append(
            {"operation": "IN", "field_name": "keyword", "field_values": list(keywords)}
        )
    if hashtags:
        any_of.append(
            {
                "operation": "IN",
                "field_name": "hashtag_name",
                "field_values": [tag.lstrip("#").lower() for tag in hashtags],
            }
        )
    return {
        "and": [
            {
                "operation": "IN",
                "field_name": "region_code",
                "field_values": list(region_codes),
            }
        ],
        "or": any_of,
        "not": [],
    }


def date_windows(
    start: date,
    end: date,
    days: int = WINDOW_DAYS,
    today: date | None = None,
) -> list[tuple[date, date]]:
    """Split a period into consecutive complete windows of fixed length.

    Parameters
    ----------
    start, end : datetime.date
        Inclusive study period.
    days : int, default=7
        Window length; must be between 1 and 30.
    today : datetime.date or None, default=None
        Reference date for the indexing lag; the current date when omitted.

    Returns
    -------
    list of tuple of datetime.date
        Inclusive ``(window_start, window_end)`` pairs.

    Raises
    ------
    ValueError
        If ``days`` is outside the API's 30-day limit.

    Notes
    -----
    Only windows that end before the indexing cutoff are returned. A trailing
    partial week is left for a later run, so every window file is complete and
    window boundaries never shift between runs.
    """
    if not 1 <= days <= 30:
        raise ValueError("Window length must be between 1 and 30 days")
    cutoff = (today or date.today()) - timedelta(days=INDEXING_LAG_DAYS)
    last = min(end, cutoff)
    windows = []
    current = start
    while current + timedelta(days=days - 1) <= last:
        windows.append((current, current + timedelta(days=days - 1)))
        current += timedelta(days=days)
    if current <= end < cutoff:
        windows.append((current, end))
    return windows


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def _write_jsonl(path: Path, records: Iterable[dict[str, Any]]) -> int:
    """Write records atomically and return their number."""
    temporary = path.with_suffix(".partial")
    count = 0
    with temporary.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
            count += 1
    temporary.replace(path)
    return count


def _append_log(path: Path, entry: dict[str, Any]) -> None:
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, ensure_ascii=False) + "\n")


def read_jsonl(paths: Iterable[Path]) -> list[dict[str, Any]]:
    """Read and concatenate JSON Lines files.

    Parameters
    ----------
    paths : iterable of pathlib.Path
        Files to read in order.

    Returns
    -------
    list of dict
        One record per non-empty line.

    Raises
    ------
    json.JSONDecodeError
        If a line is not valid JSON.

    Notes
    -----
    Atomic writes mean only complete files exist, so no truncated line is
    expected.
    """
    records: list[dict[str, Any]] = []
    for path in paths:
        with path.open(encoding="utf-8") as handle:
            records.extend(json.loads(line) for line in handle if line.strip())
    return records


def freeze_query_config(
    raw_dir: Path, query: dict[str, Any], fields: str = VIDEO_FIELDS
) -> None:
    """Save the query definition, or check that it matches the saved one.

    Parameters
    ----------
    raw_dir : pathlib.Path
        Corpus directory.
    query : dict
        Research API query.
    fields : str, default=VIDEO_FIELDS
        Requested video fields.

    Returns
    -------
    None

    Raises
    ------
    ValueError
        If the directory already holds a corpus collected with another query.

    Notes
    -----
    Start a new corpus directory to change the query after collection began.
    """
    raw_dir.mkdir(parents=True, exist_ok=True)
    path = raw_dir / "query_config.json"
    config = {"query": query, "fields": fields}
    if path.exists():
        saved = json.loads(path.read_text(encoding="utf-8"))
        if {"query": saved["query"], "fields": saved["fields"]} != config:
            raise ValueError(
                f"{path} holds a different query; use a new directory to change it"
            )
        return
    path.write_text(
        json.dumps({**config, "created_at": _now()}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def run_pilot(
    client: TikTokClient,
    keywords: Sequence[str],
    hashtags: Sequence[str],
    start: date,
    end: date,
    sample_size: int = 20,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Measure the yield of each candidate term over one pilot window.

    Parameters
    ----------
    client : TikTokClient
        Authenticated client.
    keywords, hashtags : sequence of str
        Candidate terms; each is queried alone.
    start, end : datetime.date
        Pilot window, at most 30 days.
    sample_size : int, default=20
        Videos kept per term for manual relevance review.

    Returns
    -------
    tuple of pandas.DataFrame
        Per-term yield table and per-term video samples.

    Raises
    ------
    TikTokAPIError
        Propagated from the client.

    Notes
    -----
    Only the first page is requested, so each term costs one request.
    ``has_more`` shows whether the term returns more than one page.
    """
    yields, samples = [], []
    terms = [("keyword", term) for term in keywords]
    terms += [("hashtag_name", term) for term in hashtags]
    for field_name, term in terms:
        query = build_query(
            [term] if field_name == "keyword" else [],
            [term] if field_name == "hashtag_name" else [],
        )
        page = next(
            client.iter_video_pages(
                query, start.strftime("%Y%m%d"), end.strftime("%Y%m%d"), max_pages=1
            )
        )
        videos = page.get("videos") or []
        yields.append(
            {
                "field": field_name,
                "term": term,
                "first_page_videos": len(videos),
                "has_more": bool(page.get("has_more")),
            }
        )
        for video in videos[:sample_size]:
            samples.append({"field": field_name, "term": term, **video})
        LOGGER.info("Pilot %s=%s: %s videos", field_name, term, len(videos))
    return pd.DataFrame(yields), pd.DataFrame(samples)


def collect_videos(
    client: TikTokClient,
    query: dict[str, Any],
    windows: Sequence[tuple[date, date]],
    raw_dir: Path = RAW_TIKTOK,
) -> pd.DataFrame:
    """Collect every video for each window, skipping completed windows.

    Parameters
    ----------
    client : TikTokClient
        Authenticated client.
    query : dict
        Research API query, frozen in ``query_config.json``.
    windows : sequence of tuple of datetime.date
        Inclusive date windows of at most 30 days.
    raw_dir : pathlib.Path, default=RAW_TIKTOK
        Corpus directory.

    Returns
    -------
    pandas.DataFrame
        One status row per window: ``done``, ``collected``, or ``pending``.

    Raises
    ------
    ValueError
        If the directory holds a corpus collected with another query.
    TikTokAPIError
        For non-quota API errors; completed windows stay on disk.

    Notes
    -----
    When the quota is exhausted the run stops cleanly and the remaining
    windows are reported as ``pending``; rerun on the next day to continue.
    """
    freeze_query_config(raw_dir, query)
    video_dir = raw_dir / "videos"
    video_dir.mkdir(parents=True, exist_ok=True)
    status: list[dict[str, Any]] = []
    stopped = False
    for start, end in windows:
        label = f"{start:%Y%m%d}_{end:%Y%m%d}"
        path = video_dir / f"{label}.jsonl"
        if path.exists():
            status.append({"window": label, "status": "done", "videos": None})
            continue
        if stopped:
            status.append({"window": label, "status": "pending", "videos": None})
            continue
        videos: list[dict[str, Any]] = []
        search_id = None
        try:
            for page in client.iter_video_pages(
                query, f"{start:%Y%m%d}", f"{end:%Y%m%d}"
            ):
                search_id = page.get("search_id", search_id)
                fetched_at = _now()
                videos.extend(
                    {**video, "fetched_at": fetched_at}
                    for video in page.get("videos") or []
                )
        except QuotaExceededError as error:
            LOGGER.warning("Quota exhausted at window %s: %s", label, error)
            stopped = True
            status.append({"window": label, "status": "pending", "videos": None})
            continue
        count = _write_jsonl(path, videos)
        _append_log(
            raw_dir / "collection_log.jsonl",
            {
                "kind": "videos",
                "window": label,
                "videos": count,
                "search_id": search_id,
                "fetched_at": _now(),
            },
        )
        status.append({"window": label, "status": "collected", "videos": count})
        LOGGER.info("Window %s: %s videos", label, count)
    LOGGER.info("Requests sent in this session: %s", client.request_count)
    return pd.DataFrame(status)


def collect_users(
    client: TikTokClient, usernames: Iterable[str], raw_dir: Path = RAW_TIKTOK
) -> pd.DataFrame:
    """Fetch public profiles for creators not yet collected.

    Parameters
    ----------
    client : TikTokClient
        Authenticated client.
    usernames : iterable of str
        Creator handles.
    raw_dir : pathlib.Path, default=RAW_TIKTOK
        Corpus directory; profiles are appended to ``users.jsonl``.

    Returns
    -------
    pandas.DataFrame
        All stored profiles, including ``found=False`` records.

    Raises
    ------
    TikTokAPIError
        Propagated for unexpected errors.

    Notes
    -----
    Each profile is appended as soon as it is fetched, so the quota stop loses
    nothing; unavailable profiles are stored too, to avoid re-querying them.
    """
    path = raw_dir / "users.jsonl"
    done = (
        {record["username"] for record in read_jsonl([path])}
        if path.exists()
        else set()
    )
    todo = sorted(set(usernames) - done)
    LOGGER.info("%s profiles to fetch, %s already stored", len(todo), len(done))
    for username in todo:
        try:
            profile = client.user_info(username)
        except QuotaExceededError as error:
            LOGGER.warning("Quota exhausted while fetching profiles: %s", error)
            break
        _append_log(
            path,
            {
                "username": username,
                "found": profile is not None,
                "fetched_at": _now(),
                **(profile or {}),
            },
        )
    return pd.DataFrame(read_jsonl([path])) if path.exists() else pd.DataFrame()


def collect_comments(
    client: TikTokClient, video_ids: Iterable[str], raw_dir: Path = RAW_TIKTOK
) -> pd.DataFrame:
    """Fetch the comment threads of selected videos, skipping stored ones.

    Parameters
    ----------
    client : TikTokClient
        Authenticated client.
    video_ids : iterable of str
        Videos whose comments are needed.
    raw_dir : pathlib.Path, default=RAW_TIKTOK
        Corpus directory; one file per video under ``comments/``.

    Returns
    -------
    pandas.DataFrame
        One status row per requested video.

    Raises
    ------
    TikTokAPIError
        For non-quota API errors; stored threads stay on disk.

    Notes
    -----
    Comments carry no author handle in the API response, which limits
    re-identification risk but also prevents per-commenter analysis.
    """
    comment_dir = raw_dir / "comments"
    comment_dir.mkdir(parents=True, exist_ok=True)
    status: list[dict[str, Any]] = []
    stopped = False
    for video_id in video_ids:
        path = comment_dir / f"{video_id}.jsonl"
        if path.exists():
            status.append({"video_id": video_id, "status": "done"})
            continue
        if stopped:
            status.append({"video_id": video_id, "status": "pending"})
            continue
        try:
            fetched_at = _now()
            comments = [
                {**comment, "fetched_at": fetched_at}
                for comment in client.iter_comments(video_id)
            ]
        except QuotaExceededError as error:
            LOGGER.warning("Quota exhausted while fetching comments: %s", error)
            stopped = True
            status.append({"video_id": video_id, "status": "pending"})
            continue
        except TikTokAPIError as error:
            # Deleted videos or disabled comments fail per video; others continue.
            LOGGER.info("No comments for %s: %s", video_id, error)
            status.append({"video_id": video_id, "status": "error"})
            continue
        count = _write_jsonl(path, comments)
        _append_log(
            raw_dir / "collection_log.jsonl",
            {
                "kind": "comments",
                "video_id": video_id,
                "comments": count,
                "fetched_at": _now(),
            },
        )
        status.append({"video_id": video_id, "status": "collected"})
    return pd.DataFrame(status)
