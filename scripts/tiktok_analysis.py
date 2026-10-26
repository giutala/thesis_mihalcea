"""Corpus building, descriptive tables, and figures for BNPL TikToks.

Raw API records are turned into a deduplicated, pseudonymized video corpus and
a comment corpus. Every video gets rule-based labels: how explicitly it refers
to BNPL, which providers it names, what kind of post it is, and which theme
cues it mentions. Tables and figures describe volume over time, providers,
post and creator types, engagement, theme mentions, Black Friday effects, and
comment themes. All labels are lexical rules; the README and methodology state
their limits.
"""

from __future__ import annotations

import hashlib
import logging
import secrets
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.figure import Figure

from scripts import tiktok_collection as collection
from scripts._common import ROOT
from scripts.tiktok_terms import (
    BLACK_FRIDAYS,
    CANDIDATE_HASHTAGS,
    CCD2_APPLICATION_DATE,
    CUE_PATTERNS,
    POST_TYPES,
    PROVIDER_PATTERNS,
    bnpl_signal,
    classify_creator,
    classify_post,
    compile_pattern,
    mentioned_providers,
)

LOGGER = logging.getLogger(__name__)

RAW_TIKTOK: Path = collection.RAW_TIKTOK
PROCESSED_TIKTOK = ROOT / "data" / "processed" / "tiktok"
OUTPUT_TIKTOK = ROOT / "outputs" / "tiktok"
FIGURES_TIKTOK = ROOT / "outputs" / "figures" / "tiktok"
LOCAL_TIMEZONE = "Europe/Rome"
CUE_COLUMNS = [f"cue_{name}" for name in CUE_PATTERNS]
BLACK_FRIDAY_WINDOW_WEEKS = 6
MERCHANT_AD_SHARE = 0.5
# Categorical slots from the validated reference palette; ink stays neutral.
SERIES_COLORS = ("#2a78d6", "#eb6834", "#1baf7a")
SEQUENTIAL_CMAP = "Blues"
MUTED_INK = "#52514e"
GRID_INK = "#dddcd8"


def pseudonym_salt(raw_dir: Path = RAW_TIKTOK) -> str:
    """Return the local salt for creator pseudonyms, creating it once.

    Parameters
    ----------
    raw_dir : pathlib.Path, default=RAW_TIKTOK
        Corpus directory that holds ``pseudonym_salt.txt``.

    Returns
    -------
    str
        Hex salt.

    Raises
    ------
    OSError
        If the salt file cannot be written.

    Notes
    -----
    The salt never leaves the ignored raw directory, so a pseudonym cannot be
    reversed by hashing candidate usernames without it.
    """
    path = raw_dir / "pseudonym_salt.txt"
    if not path.exists():
        raw_dir.mkdir(parents=True, exist_ok=True)
        path.write_text(secrets.token_hex(16), encoding="utf-8")
    return path.read_text(encoding="utf-8").strip()


def pseudonymize(username: str, salt: str) -> str:
    """Map a username to a stable, non-reversible creator ID.

    Parameters
    ----------
    username : str
        TikTok handle.
    salt : str
        Project salt from ``pseudonym_salt``.

    Returns
    -------
    str
        ``C`` followed by ten hex characters.

    Raises
    ------
    None

    Notes
    -----
    Ten hex characters keep collisions negligible at corpus scale.
    """
    digest = hashlib.sha256(f"{salt}:{username}".encode()).hexdigest()
    return f"C{digest[:10]}"


def _column(frame: pd.DataFrame, name: str) -> pd.Series:
    """Return a column, or an empty object column when the API omitted it."""
    if name in frame:
        return frame[name]
    return pd.Series([None] * len(frame), index=frame.index, dtype=object)


def combined_text(frame: pd.DataFrame) -> pd.Series:
    """Join description, hashtags, and transcript into one searchable text.

    Parameters
    ----------
    frame : pandas.DataFrame
        Raw video records; any of the three text fields may be absent.

    Returns
    -------
    pandas.Series
        One string per video, with hashtags prefixed by ``#``.

    Raises
    ------
    None

    Notes
    -----
    Keyword search in the API covers descriptions only; adding transcripts
    lets the relevance rule and cues also see spoken mentions.
    """
    hashtag_text = _column(frame, "hashtag_names").apply(
        lambda tags: (
            " ".join(f"#{tag}" for tag in tags) if isinstance(tags, list) else ""
        )
    )
    return (
        _column(frame, "video_description").fillna("").astype(str)
        + " "
        + hashtag_text
        + " "
        + _column(frame, "voice_to_text").fillna("").astype(str)
    ).str.strip()


def add_cue_flags(frame: pd.DataFrame, text_column: str = "text") -> pd.DataFrame:
    """Add one boolean ``cue_*`` column per theme cue.

    Parameters
    ----------
    frame : pandas.DataFrame
        Records with a text column.
    text_column : str, default="text"
        Column to search.

    Returns
    -------
    pandas.DataFrame
        Copy with ``cue_<name>`` columns and ``any_cue``.

    Raises
    ------
    KeyError
        If ``text_column`` is missing.

    Notes
    -----
    Cues are lexical and miss irony, negation, and visual content; shares are
    mention rates, not validated theme prevalence.
    """
    result = frame.copy()
    for name, pattern in CUE_PATTERNS.items():
        result[f"cue_{name}"] = result[text_column].str.contains(
            compile_pattern(pattern), regex=True
        )
    result["any_cue"] = result[CUE_COLUMNS].any(axis=1)
    return result


def label_period(timestamps: pd.Series) -> pd.Series:
    """Label local timestamps as before or after CCD2 application.

    Parameters
    ----------
    timestamps : pandas.Series
        Timezone-aware datetimes.

    Returns
    -------
    pandas.Series
        ``pre_ccd2`` or ``post_ccd2``.

    Raises
    ------
    None

    Notes
    -----
    The boundary is the CCD2 application date in Italian local time.
    """
    boundary = pd.Timestamp(CCD2_APPLICATION_DATE, tz=LOCAL_TIMEZONE)
    return pd.Series(
        ["post_ccd2" if value >= boundary else "pre_ccd2" for value in timestamps],
        index=timestamps.index,
    )


def build_creator_table(
    videos: pd.DataFrame, users: pd.DataFrame, salt: str
) -> pd.DataFrame:
    """Build one row per creator with a rule-based creator type.

    Parameters
    ----------
    videos : pandas.DataFrame
        Video records with ``username``.
    users : pandas.DataFrame
        Stored profiles with ``username``, ``found``, and profile fields.
    salt : str
        Pseudonym salt.

    Returns
    -------
    pandas.DataFrame
        Handle, pseudonym, ``profiled`` flag, profile fields, and
        ``creator_type``.

    Raises
    ------
    KeyError
        If ``username`` is missing from ``videos``.

    Notes
    -----
    Creators whose profile was not requested are ``not_profiled``; creators
    whose profile TikTok did not serve are ``unknown``. Many shops have an
    empty bio, so a creator the bio rules leave as ``ordinary_user`` becomes
    ``merchant_brand`` when most of their BNPL posts are shop ads.
    """
    creators = pd.DataFrame({"username": sorted(videos["username"].dropna().unique())})
    if not users.empty:
        profile = users.drop_duplicates("username", keep="last")
        creators = creators.merge(profile, on="username", how="left")
    for column, default in (
        ("found", None),
        ("bio_description", ""),
        ("is_verified", False),
        ("follower_count", pd.NA),
    ):
        if column not in creators:
            creators[column] = default
    creators["profiled"] = creators["found"].notna()
    creators["bio_description"] = creators["bio_description"].fillna("").astype(str)
    creators["creator_id"] = creators["username"].map(
        lambda name: pseudonymize(name, salt)
    )
    creators["creator_type"] = [
        classify_creator(name, bio, bool(found)) if profiled else "not_profiled"
        for name, bio, found, profiled in zip(
            creators["username"],
            creators["bio_description"],
            creators["found"],
            creators["profiled"],
            strict=True,
        )
    ]
    ad_share = (
        combined_text(videos)
        .map(classify_post)
        .eq("shop_ad")
        .groupby(videos["username"])
        .mean()
    )
    creators["ad_share"] = creators["username"].map(ad_share).fillna(0.0)
    mostly_ads = (creators["creator_type"] == "ordinary_user") & (
        creators["ad_share"] >= MERCHANT_AD_SHARE
    )
    creators.loc[mostly_ads, "creator_type"] = "merchant_brand"
    return creators


def build_video_corpus(
    videos: pd.DataFrame, creators: pd.DataFrame
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Deduplicate, label, and filter raw video records.

    Parameters
    ----------
    videos : pandas.DataFrame
        Raw API video records with ``fetched_at``.
    creators : pandas.DataFrame
        Creator table with ``username``, ``creator_id``, and ``creator_type``.

    Returns
    -------
    tuple of pandas.DataFrame
        Relevant video corpus and a funnel table of record counts per step.

    Raises
    ------
    KeyError
        If required API fields are missing.

    Notes
    -----
    Duplicates arise when a video matches in two windows or runs; the most
    recently fetched copy is kept so engagement counts are the latest
    snapshot.
    """
    funnel = [{"step": "records returned by the API", "videos": len(videos)}]
    frame = videos.copy()
    frame["id"] = frame["id"].astype(str)
    frame = frame.sort_values("fetched_at").drop_duplicates("id", keep="last")
    funnel.append({"step": "unique video IDs", "videos": len(frame)})
    frame["created_at"] = pd.to_datetime(
        frame["create_time"], unit="s", utc=True
    ).dt.tz_convert(LOCAL_TIMEZONE)
    frame["text"] = combined_text(frame)
    frame["bnpl_signal"] = frame["text"].map(bnpl_signal)
    frame = frame.loc[frame["bnpl_signal"] != "none"].copy()
    funnel.append(
        {
            "step": "BNPL provider or phrase in description, hashtags, or transcript",
            "videos": len(frame),
        }
    )
    frame["providers"] = frame["text"].map(
        lambda text: ";".join(mentioned_providers(text))
    )
    frame["post_type"] = frame["text"].map(classify_post)
    frame["period"] = label_period(frame["created_at"])
    local = frame["created_at"].dt.tz_localize(None)
    frame["month"] = local.dt.to_period("M").astype(str)
    frame["quarter"] = local.dt.to_period("Q").astype(str)
    frame["week_start"] = local.dt.to_period("W-SUN").dt.start_time
    frame = frame.merge(
        creators[["username", "creator_id", "creator_type"]], on="username", how="left"
    )
    frame["creator_type"] = frame["creator_type"].fillna("not_profiled")
    frame["video_url"] = (
        "https://www.tiktok.com/@" + frame["username"] + "/video/" + frame["id"]
    )
    for column in ("view_count", "like_count", "comment_count", "share_count"):
        frame[column] = pd.to_numeric(_column(frame, column), errors="coerce")
    frame = add_cue_flags(frame)
    return frame.reset_index(drop=True), pd.DataFrame(funnel)


def build_comment_corpus(comments: pd.DataFrame, corpus: pd.DataFrame) -> pd.DataFrame:
    """Attach parent-video context and cue flags to raw comments.

    Parameters
    ----------
    comments : pandas.DataFrame
        Raw comment records with ``video_id`` and ``text``.
    corpus : pandas.DataFrame
        Video corpus from ``build_video_corpus``.

    Returns
    -------
    pandas.DataFrame
        Deduplicated comments with parent post type, period, and cues.

    Raises
    ------
    KeyError
        If required comment fields are missing.

    Notes
    -----
    Comments inherit the parent video's period; their own timestamp is kept
    as ``created_at``.
    """
    if comments.empty:
        return comments
    frame = comments.copy()
    frame["id"] = frame["id"].astype(str)
    frame["video_id"] = frame["video_id"].astype(str)
    frame = frame.sort_values("fetched_at").drop_duplicates("id", keep="last")
    frame["created_at"] = pd.to_datetime(
        frame["create_time"], unit="s", utc=True
    ).dt.tz_convert(LOCAL_TIMEZONE)
    frame["text"] = frame["text"].fillna("").astype(str)
    frame["is_reply"] = frame["parent_comment_id"].astype(str) != frame["video_id"]
    context = corpus[["id", "post_type", "creator_type", "period"]].rename(
        columns={
            "id": "video_id",
            "post_type": "video_post_type",
            "creator_type": "video_creator_type",
        }
    )
    frame = frame.merge(context, on="video_id", how="inner")
    return add_cue_flags(frame).reset_index(drop=True)


def select_profile_creators(corpus: pd.DataFrame, top_active: int = 300) -> list[str]:
    """Choose the creators whose public profiles will be requested.

    Parameters
    ----------
    corpus : pandas.DataFrame
        Video corpus with ``username`` and ``post_type``.
    top_active : int, default=300
        Most active creators (by BNPL videos) always included.

    Returns
    -------
    list of str
        Handles, deduplicated.

    Raises
    ------
    KeyError
        If required columns are missing.

    Notes
    -----
    Every creator of a non-ad post is included because those posts carry the
    discourse of interest; for ads, only the most active accounts are
    profiled to stay within the user-info quota.
    """
    discourse = corpus.loc[corpus["post_type"] != "shop_ad", "username"]
    active = corpus["username"].value_counts().head(top_active).index
    return sorted(set(discourse.dropna()) | set(active))


def select_comment_videos(
    corpus: pd.DataFrame,
    per_post_type: dict[str, int] | None = None,
) -> list[str]:
    """Choose the videos whose comments will be collected.

    Parameters
    ----------
    corpus : pandas.DataFrame
        Video corpus with ``post_type`` and ``comment_count``.
    per_post_type : dict of str to int, optional
        Most-commented videos kept per post type.

    Returns
    -------
    list of str
        Video IDs, discourse post types first.

    Raises
    ------
    KeyError
        If required columns are missing.

    Notes
    -----
    Each video costs at least one request, so the selection is capped and
    weighted toward personal experience and commentary, where users discuss
    BNPL rather than ask about a product.
    """
    limits = per_post_type or {
        "personal_experience": 300,
        "financial_commentary": 300,
        "other": 100,
        "shop_ad": 100,
    }
    commented = corpus.loc[corpus["comment_count"].fillna(0) > 0]
    selected: list[str] = []
    for post_type, limit in limits.items():
        subset = commented.loc[commented["post_type"] == post_type]
        top = subset.sort_values("comment_count", ascending=False).head(limit)
        selected.extend(str(video_id) for video_id in top["id"])
    return selected


def _explode_providers(corpus: pd.DataFrame) -> pd.DataFrame:
    exploded = corpus.assign(provider=corpus["providers"].str.split(";")).explode(
        "provider"
    )
    return exploded.loc[exploded["provider"].fillna("") != ""]


def black_friday_index(corpus: pd.DataFrame) -> pd.DataFrame:
    """Index weekly volume around each Black Friday to the preceding weeks.

    Parameters
    ----------
    corpus : pandas.DataFrame
        Video corpus with ``week_start``.

    Returns
    -------
    pandas.DataFrame
        ``year``, ``week_offset`` (0 = Black Friday week), ``videos``, and
        ``index`` (100 = mean of the six weeks before).

    Raises
    ------
    KeyError
        If ``week_start`` is missing.

    Notes
    -----
    Indexing removes the level difference between years, so the shape of the
    seasonal peak can be compared even as overall volume grows.
    """
    weekly = corpus.groupby("week_start").size()
    rows = []
    for black_friday in BLACK_FRIDAYS:
        anchor = pd.Timestamp(black_friday).to_period("W-SUN").start_time
        offsets = range(-BLACK_FRIDAY_WINDOW_WEEKS, BLACK_FRIDAY_WINDOW_WEEKS + 1)
        weeks = [anchor + pd.Timedelta(weeks=offset) for offset in offsets]
        if weeks[-1] > weekly.index.max() or weeks[0] < weekly.index.min():
            continue
        counts = weekly.reindex(weeks, fill_value=0)
        baseline = counts.iloc[:BLACK_FRIDAY_WINDOW_WEEKS].mean()
        for offset, count in zip(offsets, counts, strict=True):
            rows.append(
                {
                    "year": black_friday.year,
                    "week_offset": offset,
                    "videos": int(count),
                    "index": 100 * count / baseline if baseline else float("nan"),
                }
            )
    return pd.DataFrame(rows, columns=["year", "week_offset", "videos", "index"])


def complete_months(video_files: list[Path]) -> set[str]:
    """Return the months whose every day lies in a collected window.

    Parameters
    ----------
    video_files : list of pathlib.Path
        Window files named ``<YYYYMMDD>_<YYYYMMDD>.jsonl``.

    Returns
    -------
    set of str
        ``YYYY-MM`` labels of fully collected months.

    Raises
    ------
    ValueError
        If a file name is not a date range.

    Notes
    -----
    A month missing even one window would show a false drop in volume, so
    trend charts use complete months only.
    """
    covered: set[pd.Timestamp] = set()
    for path in video_files:
        start, end = path.stem.split("_")
        covered.update(pd.date_range(start, end, freq="D"))
    if not covered:
        return set()
    months = pd.period_range(min(covered), max(covered), freq="M")
    return {
        str(month)
        for month in months
        if set(pd.date_range(month.start_time, month.end_time.normalize(), freq="D"))
        <= covered
    }


def summarize_corpus(
    corpus: pd.DataFrame,
    creators: pd.DataFrame,
    comments: pd.DataFrame,
    full_months: set[str] | None = None,
) -> dict[str, pd.DataFrame]:
    """Compute the descriptive tables reported in the notebook and README.

    Parameters
    ----------
    corpus : pandas.DataFrame
        Output of ``build_video_corpus``.
    creators : pandas.DataFrame
        Output of ``build_creator_table``.
    comments : pandas.DataFrame
        Output of ``build_comment_corpus``.
    full_months : set of str or None, default=None
        Fully collected months; all months count as complete when omitted.

    Returns
    -------
    dict of str to pandas.DataFrame
        Named tables; see ``run_analysis`` for the file names.

    Raises
    ------
    KeyError
        If required columns are missing.

    Notes
    -----
    Medians are used for engagement because view counts are highly skewed.
    Shares are proportions within a group, which corrects for group size but
    not for platform-wide growth.
    """
    monthly = (
        corpus.pivot_table(
            index="month",
            columns="post_type",
            values="id",
            aggfunc="size",
            fill_value=0,
        )
        .reindex(columns=list(POST_TYPES), fill_value=0)
        .assign(total=lambda table: table.sum(axis=1))
        .reset_index()
    )
    monthly.columns.name = None
    monthly["discourse_share"] = (
        monthly["personal_experience"] + monthly["financial_commentary"]
    ) / monthly["total"]
    monthly["complete"] = (
        monthly["month"].isin(full_months) if full_months is not None else True
    )

    signal = corpus["bnpl_signal"].value_counts().rename("videos").reset_index()

    exploded = _explode_providers(corpus)
    providers = (
        exploded.groupby("provider")
        .agg(
            videos=("id", "nunique"),
            creators=("creator_id", "nunique"),
            share_shop_ad=("post_type", lambda types: (types == "shop_ad").mean()),
        )
        .reindex(list(PROVIDER_PATTERNS))
        .fillna({"videos": 0, "creators": 0})
        .sort_values("videos", ascending=False)
        .reset_index()
    )
    provider_quarterly = (
        exploded.pivot_table(
            index="quarter", columns="provider", values="id", aggfunc="nunique"
        )
        .fillna(0)
        .astype(int)
        .reset_index()
    )
    provider_quarterly.columns.name = None
    complete_month_labels = set(monthly.loc[monthly["complete"], "month"])
    provider_quarterly["complete"] = [
        all(
            str(pd.Period(quarter, freq="Q").asfreq("M", "start") + offset)
            in complete_month_labels
            for offset in range(3)
        )
        for quarter in provider_quarterly["quarter"]
    ]

    post_types = (
        corpus.groupby("post_type")
        .agg(
            videos=("id", "size"),
            creators=("creator_id", "nunique"),
            median_views=("view_count", "median"),
            median_likes=("like_count", "median"),
            median_comments=("comment_count", "median"),
            median_shares=("share_count", "median"),
        )
        .reindex(list(POST_TYPES))
        .dropna(how="all")
        .reset_index()
    )
    post_types["share"] = post_types["videos"] / post_types["videos"].sum()

    profiled = creators.loc[creators["profiled"]]
    creator_types = (
        profiled["creator_type"].value_counts().rename("creators").reset_index()
    )
    creator_types["share"] = creator_types["creators"] / creator_types["creators"].sum()

    cues_by_post_type = (
        corpus.groupby("post_type")[CUE_COLUMNS]
        .mean()
        .reindex(list(POST_TYPES))
        .dropna(how="all")
        .T.rename(index=lambda column: column.removeprefix("cue_"))
        .rename_axis("cue")
        .reset_index()
    )
    cues_by_post_type.columns.name = None
    cues_by_period = (
        corpus.groupby("period")[CUE_COLUMNS]
        .mean()
        .T.rename(index=lambda column: column.removeprefix("cue_"))
        .rename_axis("cue")
        .reset_index()
    )
    cues_by_period.columns.name = None

    search_tags = {tag.lower() for tag in CANDIDATE_HASHTAGS}
    tags = _column(corpus, "hashtag_names").explode().dropna().astype(str).str.lower()
    tags = tags.loc[~tags.isin(search_tags) & (tags != "")]
    top_hashtags = (
        tags.groupby(tags)
        .size()
        .sort_values(ascending=False)
        .head(20)
        .rename_axis("hashtag")
        .rename("videos")
        .reset_index()
    )

    if comments.empty:
        comment_cues = pd.DataFrame(columns=["cue", "share"])
    else:
        comment_cues = (
            comments.groupby("video_post_type")[CUE_COLUMNS]
            .mean()
            .reindex([t for t in POST_TYPES if t in set(comments["video_post_type"])])
            .T.rename(index=lambda column: column.removeprefix("cue_"))
            .rename_axis("cue")
            .reset_index()
        )
        comment_cues.columns.name = None
        comment_cues["all_comments"] = comments[CUE_COLUMNS].mean().to_numpy()

    return {
        "monthly": monthly,
        "bnpl_signal": signal,
        "providers": providers,
        "provider_quarterly": provider_quarterly,
        "post_types": post_types,
        "creator_types": creator_types,
        "cues_by_post_type": cues_by_post_type,
        "cues_by_period": cues_by_period,
        "black_friday": black_friday_index(corpus),
        "top_hashtags": top_hashtags,
        "comment_cues": comment_cues,
    }


def _style_axes(axis: Any, grid_axis: str = "y") -> None:
    axis.spines[["top", "right"]].set_visible(False)
    axis.spines[["left", "bottom"]].set_color(GRID_INK)
    axis.tick_params(colors=MUTED_INK, labelsize=9)
    axis.grid(axis=grid_axis, color=GRID_INK, linewidth=0.6)
    axis.set_axisbelow(True)


def _title(axis: Any, title: str, subtitle: str = "") -> None:
    axis.set_title(title, loc="left", fontsize=11, pad=18 if subtitle else 6)
    if subtitle:
        axis.annotate(
            subtitle,
            (0, 1),
            xycoords="axes fraction",
            xytext=(0, 5),
            textcoords="offset points",
            fontsize=8,
            color=MUTED_INK,
        )


def _no_data_figure(title: str) -> Figure:
    """Return a small placeholder figure for a chart without input rows."""
    figure, axis = plt.subplots(figsize=(7, 1.6))
    axis.axis("off")
    axis.text(0, 0.5, f"{title}: no fully collected period yet", color=MUTED_INK)
    return figure


def plot_monthly_volume(monthly: pd.DataFrame) -> Figure:
    """Plot BNPL videos per month with CCD2 and Black Friday marked.

    Parameters
    ----------
    monthly : pandas.DataFrame
        ``month`` (``YYYY-MM``) and ``total`` columns.

    Returns
    -------
    matplotlib.figure.Figure
        Line chart sized for a thesis page.

    Raises
    ------
    KeyError
        If required columns are missing.

    Notes
    -----
    Event lines are drawn in neutral ink so that they do not read as a
    second series.
    """
    if monthly.empty:
        return _no_data_figure("Monthly volume")
    figure, axis = plt.subplots(figsize=(9, 3.6))
    months = pd.PeriodIndex(monthly["month"], freq="M").to_timestamp()
    axis.plot(
        months,
        monthly["total"],
        color=SERIES_COLORS[0],
        linewidth=2,
        marker="o",
        markersize=4,
    )
    # CCD2 falls a week before Black Friday 2026, so its label sits at the
    # bottom of the plot to avoid overlapping the Black Friday label.
    events = [(day, "Black Friday", 1.0, "top") for day in BLACK_FRIDAYS]
    events.append((CCD2_APPLICATION_DATE, "CCD2 applies", 0.02, "bottom"))
    lower, upper = months.min(), months.max() + pd.offsets.MonthEnd(0)
    for day, label, height, vertical_align in events:
        stamp = pd.Timestamp(day)
        if lower <= stamp <= upper:
            axis.axvline(stamp, color=MUTED_INK, linestyle="--", linewidth=0.8)
            axis.annotate(
                label,
                (stamp, height),
                xycoords=("data", "axes fraction"),
                rotation=90,
                va=vertical_align,
                ha="right",
                fontsize=8,
                color=MUTED_INK,
            )
    axis.set_ylabel("BNPL videos per month", color=MUTED_INK)
    axis.set_ylim(bottom=0)
    _title(axis, "Italian TikTok videos mentioning BNPL")
    _style_axes(axis)
    figure.tight_layout()
    return figure


def plot_discourse_share(monthly: pd.DataFrame) -> Figure:
    """Plot the monthly share of videos that are commentary or experience.

    Parameters
    ----------
    monthly : pandas.DataFrame
        ``month`` and ``discourse_share`` columns.

    Returns
    -------
    matplotlib.figure.Figure
        Single-series line chart with a percentage axis.

    Raises
    ------
    KeyError
        If required columns are missing.

    Notes
    -----
    A share isolates the change in what is said from the growth in how much
    is posted.
    """
    if monthly.empty:
        return _no_data_figure("Discourse share")
    figure, axis = plt.subplots(figsize=(9, 3.2))
    months = pd.PeriodIndex(monthly["month"], freq="M").to_timestamp()
    axis.plot(months, monthly["discourse_share"], color=SERIES_COLORS[0], linewidth=2)
    axis.yaxis.set_major_formatter(lambda value, _: f"{value:.1%}")
    axis.set_ylim(bottom=0)
    _title(
        axis,
        "Share of BNPL videos that are commentary or personal experience",
        "Rest: shop and service ads, and unclassified posts",
    )
    _style_axes(axis)
    figure.tight_layout()
    return figure


def plot_provider_trends(provider_quarterly: pd.DataFrame, top: int = 3) -> Figure:
    """Plot quarterly videos for the most-mentioned providers.

    Parameters
    ----------
    provider_quarterly : pandas.DataFrame
        ``quarter`` plus one count column per provider.
    top : int, default=3
        Providers shown; the rest are listed in the table only.

    Returns
    -------
    matplotlib.figure.Figure
        Multi-series line chart with direct labels and a legend.

    Raises
    ------
    KeyError
        If ``quarter`` is missing.

    Notes
    -----
    Three series is the palette's safe maximum for distinguishable lines.
    Incomplete quarters are left out so that a partial quarter never reads as
    a decline.
    """
    table = provider_quarterly.loc[provider_quarterly["complete"]].set_index("quarter")
    table = table.drop(columns="complete")
    if table.empty:
        return _no_data_figure("Provider trends")
    leaders = table.sum().sort_values(ascending=False).head(top).index
    figure, axis = plt.subplots(figsize=(9, 3.6))
    quarters = pd.PeriodIndex(table.index, freq="Q").to_timestamp()
    for color, provider in zip(SERIES_COLORS, leaders, strict=False):
        values = table[provider]
        axis.plot(quarters, values, color=color, linewidth=2, label=provider)
        axis.annotate(
            provider,
            (quarters[-1], values.iloc[-1]),
            xytext=(4, 0),
            textcoords="offset points",
            va="center",
            fontsize=8,
            color=MUTED_INK,
        )
    axis.set_ylim(bottom=0)
    axis.set_ylabel("Videos per quarter", color=MUTED_INK)
    axis.legend(frameon=False, fontsize=8, loc="upper left")
    _title(axis, "Videos naming each provider", "Fully collected quarters only")
    _style_axes(axis)
    figure.tight_layout()
    return figure


def plot_horizontal_bars(
    table: pd.DataFrame,
    label: str,
    value: str,
    title: str,
    subtitle: str = "",
    percent: bool = False,
    count: str | None = None,
) -> Figure:
    """Plot a ranked horizontal bar chart with direct value labels.

    Parameters
    ----------
    table : pandas.DataFrame
        One row per category.
    label, value : str
        Category and value columns.
    title, subtitle : str
        Chart title and optional note.
    percent : bool, default=False
        Format values as percentages; shares below 1% keep two decimals.
    count : str or None, default=None
        Column whose value is appended to each label as ``n=``.

    Returns
    -------
    matplotlib.figure.Figure
        Bar chart with the largest category on top.

    Raises
    ------
    KeyError
        If the columns are missing.

    Notes
    -----
    A single series needs no legend; the title names the measure.
    """
    ordered = table.dropna(subset=[value]).sort_values(value)
    figure, axis = plt.subplots(figsize=(7, 0.38 * len(ordered) + 1.4))
    bars = axis.barh(
        ordered[label].astype(str).str.replace("_", " "),
        ordered[value],
        color=SERIES_COLORS[0],
        height=0.6,
    )
    labels = [
        (f"{v:.2%}" if v < 0.01 else f"{v:.0%}") if percent else f"{v:,.0f}"
        for v in ordered[value]
    ]
    if count is not None:
        labels = [
            f"{text} (n={int(n):,})"
            for text, n in zip(labels, ordered[count], strict=True)
        ]
    axis.bar_label(bars, labels=labels, padding=3, fontsize=8, color=MUTED_INK)
    if percent:
        axis.xaxis.set_major_formatter(lambda tick, _: f"{tick:.0%}")
    _title(axis, title, subtitle)
    _style_axes(axis, grid_axis="x")
    figure.tight_layout()
    return figure


def plot_cue_heatmap(cues: pd.DataFrame, title: str, subtitle: str) -> Figure:
    """Plot cue mention rates as an annotated single-hue heatmap.

    Parameters
    ----------
    cues : pandas.DataFrame
        ``cue`` plus one share column per group.
    title, subtitle : str
        Chart title and note.

    Returns
    -------
    matplotlib.figure.Figure
        Heatmap with a percentage in every cell.

    Raises
    ------
    KeyError
        If ``cue`` is missing.

    Notes
    -----
    Each cell carries its value as text, so the color scale is never the
    only encoding.
    """
    table = cues.set_index("cue")
    figure, axis = plt.subplots(
        figsize=(1.5 * len(table.columns) + 3, 0.45 * len(table) + 1.6)
    )
    axis.imshow(
        table.to_numpy(dtype=float), cmap=SEQUENTIAL_CMAP, aspect="auto", vmin=0
    )
    peak = float(table.to_numpy(dtype=float).max()) or 1.0
    for row, cue in enumerate(table.index):
        for column, group in enumerate(table.columns):
            value = float(table.loc[cue, group])
            axis.text(
                column,
                row,
                f"{value:.0%}",
                ha="center",
                va="center",
                fontsize=8,
                color="white" if value > 0.6 * peak else "#0b0b0b",
            )
    axis.set_xticks(range(len(table.columns)))
    axis.set_xticklabels([str(c).replace("_", " ") for c in table.columns], fontsize=8)
    axis.set_yticks(range(len(table)))
    axis.set_yticklabels([str(c).replace("_", " ") for c in table.index], fontsize=8)
    axis.tick_params(length=0, colors=MUTED_INK)
    for spine in axis.spines.values():
        spine.set_visible(False)
    _title(axis, title, subtitle)
    figure.tight_layout()
    return figure


def plot_black_friday(black_friday: pd.DataFrame) -> Figure:
    """Plot indexed weekly volume around each Black Friday.

    Parameters
    ----------
    black_friday : pandas.DataFrame
        Output of ``black_friday_index``.

    Returns
    -------
    matplotlib.figure.Figure
        One line per year with a reference line at 100.

    Raises
    ------
    KeyError
        If required columns are missing.

    Notes
    -----
    Years are colored by fixed palette order, so the earliest year is always
    the first slot.
    """
    figure, axis = plt.subplots(figsize=(7, 3.4))
    for color, (year, group) in zip(
        SERIES_COLORS, black_friday.groupby("year"), strict=False
    ):
        axis.plot(
            group["week_offset"],
            group["index"],
            color=color,
            linewidth=2,
            marker="o",
            markersize=4,
            label=str(year),
        )
    axis.axhline(100, color=MUTED_INK, linewidth=0.8, linestyle="--")
    axis.axvline(0, color=GRID_INK, linewidth=0.8)
    axis.set_xlabel("Weeks from Black Friday week", color=MUTED_INK)
    axis.set_ylabel("Index (6 weeks before = 100)", color=MUTED_INK)
    if not black_friday.empty:
        axis.legend(frameon=False, fontsize=8)
    _title(axis, "BNPL videos around Black Friday")
    _style_axes(axis)
    figure.tight_layout()
    return figure


def markdown_table(frame: pd.DataFrame, percent_columns: tuple[str, ...] = ()) -> str:
    """Render a small DataFrame as a GitHub Markdown table.

    Parameters
    ----------
    frame : pandas.DataFrame
        Table to render; the index is ignored.
    percent_columns : tuple of str, default=()
        Numeric columns shown as whole percentages.

    Returns
    -------
    str
        Markdown table, or ``_No rows._`` when empty.

    Raises
    ------
    None

    Notes
    -----
    Avoids an extra dependency for the few summary tables the project writes.
    """
    if frame.empty:
        return "_No rows._"

    def cell(column: str, value: Any) -> str:
        if pd.isna(value):
            return ""
        if column in percent_columns:
            return f"{float(value):.0%}"
        if isinstance(value, float):
            return f"{value:,.0f}"
        return str(value).replace("|", "/")

    header = "| " + " | ".join(map(str, frame.columns)) + " |"
    divider = "|" + "---|" * len(frame.columns)
    rows = [
        "| " + " | ".join(cell(column, row[column]) for column in frame.columns) + " |"
        for _, row in frame.iterrows()
    ]
    return "\n".join([header, divider, *rows])


def write_findings_summary(
    path: Path, funnel: pd.DataFrame, tables: dict[str, pd.DataFrame], comments: int
) -> str:
    """Write a dated Markdown summary of the descriptive results.

    Parameters
    ----------
    path : pathlib.Path
        Markdown output path.
    funnel : pandas.DataFrame
        Corpus funnel from ``build_video_corpus``.
    tables : dict of str to pandas.DataFrame
        Output of ``summarize_corpus``.
    comments : int
        Number of comments in the comment corpus.

    Returns
    -------
    str
        The Markdown text.

    Raises
    ------
    OSError
        If the file cannot be written.

    Notes
    -----
    Only numbers computed from the data are written; interpretation lives in
    the notebook and README.
    """
    monthly = tables["monthly"].loc[tables["monthly"]["complete"]]
    coverage = "No month has been fully collected yet."
    if not monthly.empty:
        peak = monthly.loc[monthly["total"].idxmax()]
        coverage = (
            f"Fully collected months: {monthly['month'].iloc[0]} to "
            f"{monthly['month'].iloc[-1]}. Peak month: {peak['month']} "
            f"({int(peak['total'])} videos)."
        )
    cue_shares = [
        column for column in tables["cues_by_post_type"].columns if column != "cue"
    ]
    lines = [
        "# TikTok BNPL corpus: descriptive summary",
        "",
        f"Generated {pd.Timestamp.now(tz=LOCAL_TIMEZONE):%Y-%m-%d %H:%M} "
        "from local data. Post types and theme cues are lexical rules.",
        "",
        "## Corpus",
        "",
        markdown_table(funnel),
        "",
        f"{coverage} Comments collected: {comments}.",
        "",
        "## Post types",
        "",
        markdown_table(tables["post_types"], percent_columns=("share",)),
        "",
        "## Providers named",
        "",
        markdown_table(tables["providers"], percent_columns=("share_shop_ad",)),
        "",
        "## Theme mentions by post type (share of videos)",
        "",
        markdown_table(tables["cues_by_post_type"], percent_columns=tuple(cue_shares)),
        "",
        "## Black Friday (index, 6 weeks before = 100)",
        "",
        markdown_table(
            tables["black_friday"]
            .pivot_table(index="week_offset", columns="year", values="index")
            .reset_index()
        ),
        "",
    ]
    if not tables["comment_cues"].empty:
        comment_columns = tuple(
            column for column in tables["comment_cues"].columns if column != "cue"
        )
        lines += [
            "## Theme mentions in comments (share of comments)",
            "",
            markdown_table(tables["comment_cues"], percent_columns=comment_columns),
            "",
        ]
    text = "\n".join(lines)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return text


def load_raw(raw_dir: Path = RAW_TIKTOK) -> dict[str, pd.DataFrame]:
    """Load stored videos, profiles, and comments from the corpus directory.

    Parameters
    ----------
    raw_dir : pathlib.Path, default=RAW_TIKTOK
        Corpus directory written by the collection notebook.

    Returns
    -------
    dict of str to pandas.DataFrame
        ``videos``, ``users``, and ``comments``; missing parts are empty.

    Raises
    ------
    FileNotFoundError
        If no video windows have been collected.

    Notes
    -----
    Files are read in name order, so loading is deterministic.
    """
    video_files = sorted((raw_dir / "videos").glob("*.jsonl"))
    if not video_files:
        raise FileNotFoundError(f"No collected video windows in {raw_dir / 'videos'}")
    users_path = raw_dir / "users.jsonl"
    comment_files = sorted((raw_dir / "comments").glob("*.jsonl"))
    return {
        "videos": pd.DataFrame(collection.read_jsonl(video_files)),
        "users": pd.DataFrame(collection.read_jsonl([users_path]))
        if users_path.exists()
        else pd.DataFrame(),
        "comments": pd.DataFrame(collection.read_jsonl(comment_files)),
    }


def build_figures(tables: dict[str, pd.DataFrame]) -> dict[str, Figure]:
    """Render every figure from the summary tables.

    Parameters
    ----------
    tables : dict of str to pandas.DataFrame
        Output of ``summarize_corpus``.

    Returns
    -------
    dict of str to matplotlib.figure.Figure
        Figures keyed by output file stem.

    Raises
    ------
    KeyError
        If a table is missing.

    Notes
    -----
    The pre/post CCD2 heatmap is drawn only once both periods have data.
    """
    complete = tables["monthly"].loc[tables["monthly"]["complete"]]
    figures = {
        "monthly_volume": plot_monthly_volume(complete),
        "discourse_share": plot_discourse_share(complete),
        "provider_trends": plot_provider_trends(tables["provider_quarterly"]),
        "providers": plot_horizontal_bars(
            tables["providers"], "provider", "videos", "Videos naming each provider"
        ),
        "post_types": plot_horizontal_bars(
            tables["post_types"],
            "post_type",
            "share",
            "What kind of post mentions BNPL",
            "Share of BNPL videos, rule-based classification",
            percent=True,
            count="videos",
        ),
        "engagement_by_post_type": plot_horizontal_bars(
            tables["post_types"],
            "post_type",
            "median_views",
            "Median views per video",
            "Snapshot at collection time",
        ),
        "creator_types": plot_horizontal_bars(
            tables["creator_types"],
            "creator_type",
            "share",
            "Who posts about BNPL",
            "Share of profiled creators, rule-based classification",
            percent=True,
        ),
        "cues_by_post_type": plot_cue_heatmap(
            tables["cues_by_post_type"],
            "Theme mentions by post type",
            "Share of videos whose text matches each theme dictionary",
        ),
        "black_friday": plot_black_friday(tables["black_friday"]),
        "top_hashtags": plot_horizontal_bars(
            tables["top_hashtags"],
            "hashtag",
            "videos",
            "Hashtags used alongside BNPL",
            "Search hashtags excluded",
        ),
    }
    if not tables["comment_cues"].empty:
        figures["comment_cues"] = plot_cue_heatmap(
            tables["comment_cues"],
            "Theme mentions in comments",
            "Share of comments, by the type of video they reply to",
        )
    if {"pre_ccd2", "post_ccd2"} <= set(tables["cues_by_period"].columns):
        figures["cues_by_period"] = plot_cue_heatmap(
            tables["cues_by_period"][["cue", "pre_ccd2", "post_ccd2"]],
            "Theme mentions before and after CCD2",
            "Share of videos per period",
        )
    return figures


def run_analysis(
    raw_dir: Path = RAW_TIKTOK,
    processed_dir: Path = PROCESSED_TIKTOK,
    output_dir: Path = OUTPUT_TIKTOK,
    figure_dir: Path = FIGURES_TIKTOK,
) -> dict[str, Any]:
    """Build corpora, tables, figures, and the summary file.

    Parameters
    ----------
    raw_dir : pathlib.Path, default=RAW_TIKTOK
        Collected API data.
    processed_dir : pathlib.Path, default=PROCESSED_TIKTOK
        Ignored folder for text-bearing corpus CSVs.
    output_dir : pathlib.Path, default=OUTPUT_TIKTOK
        Folder for aggregate tables and the summary.
    figure_dir : pathlib.Path, default=FIGURES_TIKTOK
        Folder for 300 dpi PNG figures.

    Returns
    -------
    dict
        Creators, corpora, funnel, tables, figures, and summary text.

    Raises
    ------
    FileNotFoundError
        If no videos have been collected.

    Notes
    -----
    Every output is regenerated from the raw files, so reruns are safe.
    """
    raw = load_raw(raw_dir)
    salt = pseudonym_salt(raw_dir)
    creators = build_creator_table(raw["videos"], raw["users"], salt)
    corpus, funnel = build_video_corpus(raw["videos"], creators)
    comments = build_comment_corpus(raw["comments"], corpus)
    full_months = complete_months(sorted((raw_dir / "videos").glob("*.jsonl")))
    tables = summarize_corpus(corpus, creators, comments, full_months)

    processed_dir.mkdir(parents=True, exist_ok=True)
    corpus.drop(columns=["username"]).to_csv(
        processed_dir / "video_corpus.csv", index=False, encoding="utf-8-sig"
    )
    comments.to_csv(
        processed_dir / "comment_corpus.csv", index=False, encoding="utf-8-sig"
    )
    table_dir = output_dir / "tables"
    table_dir.mkdir(parents=True, exist_ok=True)
    funnel.to_csv(table_dir / "corpus_funnel.csv", index=False)
    for name, table in tables.items():
        table.to_csv(table_dir / f"{name}.csv", index=False)

    figures = build_figures(tables)
    figure_dir.mkdir(parents=True, exist_ok=True)
    for name, figure in figures.items():
        figure.savefig(figure_dir / f"{name}.png", dpi=300, bbox_inches="tight")

    summary = write_findings_summary(
        output_dir / "findings_summary.md", funnel, tables, len(comments)
    )
    return {
        "creators": creators,
        "corpus": corpus,
        "comments": comments,
        "funnel": funnel,
        "tables": tables,
        "figures": figures,
        "summary": summary,
    }
