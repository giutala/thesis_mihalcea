"""Checks for corpus building, labels, coverage, and outputs on synthetic data."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd
from matplotlib import pyplot as plt

from scripts import tiktok_analysis as analysis


def _write_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(record, ensure_ascii=False) + "\n" for record in records),
        encoding="utf-8",
    )


def _timestamp(day: str) -> int:
    return int(datetime.fromisoformat(f"{day}T12:00:00+00:00").timestamp())


def _synthetic_raw(raw_dir: Path) -> None:
    videos = [
        {
            "id": 1,
            "username": "anna",
            "create_time": _timestamp("2026-10-01"),
            "video_description": "Ho pagato con Klarna, non mi ricordo le scadenze",
            "hashtag_names": ["klarna"],
            "view_count": 1000,
            "comment_count": 3,
            "fetched_at": "2026-10-20T00:00:00+00:00",
        },
        {
            "id": 2,
            "username": "scalapay_it",
            "create_time": _timestamp("2026-11-25"),
            "video_description": "Black Friday: offerta in 3 rate senza interessi",
            "hashtag_names": ["scalapay"],
            "view_count": 50000,
            "comment_count": 10,
            "fetched_at": "2026-12-01T00:00:00+00:00",
        },
        {
            "id": 3,
            "username": "cucina",
            "create_time": _timestamp("2026-10-02"),
            "video_description": "Ricetta della pasta",
            "hashtag_names": [],
            "view_count": 10,
            "comment_count": 0,
            "fetched_at": "2026-10-20T00:00:00+00:00",
        },
    ]
    duplicate = {
        **videos[0],
        "view_count": 2000,
        "fetched_at": "2026-11-01T00:00:00+00:00",
    }
    _write_jsonl(
        raw_dir / "videos" / "20261001_20261007.jsonl", videos[:2] + [videos[2]]
    )
    _write_jsonl(raw_dir / "videos" / "20261008_20261014.jsonl", [duplicate])
    _write_jsonl(
        raw_dir / "users.jsonl",
        [
            {"username": "anna", "found": True, "bio_description": "studentessa"},
            {"username": "scalapay_it", "found": True, "bio_description": ""},
        ],
    )
    _write_jsonl(
        raw_dir / "comments" / "1.jsonl",
        [
            {
                "id": 10,
                "video_id": 1,
                "parent_comment_id": 1,
                "text": "Anche io, me ne sono scordata e ho pagato la mora",
                "create_time": _timestamp("2026-10-02"),
                "fetched_at": "2026-10-20T00:00:00+00:00",
            }
        ],
    )


def test_analysis_builds_labelled_pseudonymized_corpus(tmp_path: Path) -> None:
    raw_dir = tmp_path / "raw"
    _synthetic_raw(raw_dir)
    dirs = {
        "raw_dir": raw_dir,
        "processed_dir": tmp_path / "processed",
        "output_dir": tmp_path / "out",
        "figure_dir": tmp_path / "figures",
    }
    result = analysis.run_analysis(**dirs)
    plt.close("all")
    corpus = result["corpus"].set_index("id")

    assert result["funnel"]["videos"].tolist() == [4, 3, 2]
    assert corpus.loc["1", "view_count"] == 2000
    assert corpus.loc["1", "post_type"] == "personal_experience"
    assert corpus.loc["2", "post_type"] == "shop_ad"
    assert corpus.loc["2", "bnpl_signal"] == "named_provider"
    assert corpus.loc["2", "period"] == "post_ccd2"
    assert corpus.loc["1", "creator_type"] == "ordinary_user"
    assert corpus.loc["2", "creator_type"] == "provider_official"
    assert bool(corpus.loc["1", "cue_losing_track"])
    assert bool(result["comments"].loc[0, "cue_payment_failure_fees"])
    assert (
        result["tables"]["providers"].set_index("provider").loc["klarna", "videos"] == 1
    )
    saved = pd.read_csv(dirs["processed_dir"] / "video_corpus.csv")
    assert "username" not in saved
    for name in ("monthly_volume", "post_types", "cues_by_post_type", "cues_by_period"):
        assert (dirs["figure_dir"] / f"{name}.png").exists()
    assert "Post types" in result["summary"]


def test_comment_selection_caps_each_post_type() -> None:
    corpus = pd.DataFrame(
        {
            "id": [str(n) for n in range(6)],
            "post_type": ["shop_ad"] * 4 + ["personal_experience"] * 2,
            "comment_count": [5, 4, 3, 0, 1, 9],
        }
    )
    selected = analysis.select_comment_videos(
        corpus, {"personal_experience": 5, "shop_ad": 2}
    )

    assert selected == ["5", "4", "0", "1"]


def test_complete_months_require_every_day_collected() -> None:
    files = [
        Path("20260101_20260131.jsonl"),
        Path("20260201_20260214.jsonl"),
        Path("20260216_20260228.jsonl"),
    ]

    assert analysis.complete_months(files) == {"2026-01"}
