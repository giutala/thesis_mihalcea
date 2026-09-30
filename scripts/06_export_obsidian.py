"""Export the manually coded excerpts as linked Obsidian participant/theme notes."""

from __future__ import annotations

import logging
from pathlib import Path

import frontmatter
import pandas as pd

from scripts._common import ROOT, get_data

LOGGER = logging.getLogger(__name__)


def _theme_filename(theme):
    """Keep note filenames portable while preserving the displayed theme label."""
    safe = (
        "".join("-" if char in '<>:/\\|?*"' else char for char in str(theme))
        .strip()
        .rstrip(".")
    )
    return safe


def export_obsidian(
    codes: pd.DataFrame | None = None,
    participants: pd.DataFrame | None = None,
    vault: Path | None = None,
) -> Path:
    """Write linked Obsidian notes for every participant and manual theme.

    Parameters
    ----------
    codes : pandas.DataFrame or None, default=None
        Manually coded excerpts; load project data when omitted.
    participants : pandas.DataFrame or None, default=None
        Participant details. Read the processed participant CSV when omitted.
    vault : pathlib.Path or None, default=None
        Output directory; defaults to the project's ``vault`` directory.

    Returns
    -------
    pathlib.Path
        Directory containing generated Markdown notes.

    Raises
    ------
    FileNotFoundError
        If participant details are needed but their processed CSV is missing.
    OSError
        If the output directory or a note cannot be written.

    Notes
    -----
    Theme labels are kept verbatim in frontmatter and note text. Only filenames
    are sanitized for portability, with Obsidian aliases preserving the labels.
    """
    codes = get_data(codes)
    participants = (
        participants
        if participants is not None
        else pd.read_csv(ROOT / "data/processed/participants.csv", encoding="utf-8-sig")
    )
    vault = ROOT / "vault" if vault is None else vault
    vault.mkdir(parents=True, exist_ok=True)
    prevalence = codes.groupby("theme").participant_id.nunique()
    for theme, subset in codes.groupby("theme", sort=True):
        people = sorted(subset.participant_id.unique())
        body = "\n".join(
            f'- [[{pid}]]: "{quote}"'
            for pid, quote in zip(subset.participant_id, subset.quote, strict=True)
        )
        post = frontmatter.Post(
            body, theme=theme, participants=people, prevalence=int(prevalence[theme])
        )
        (vault / f"{_theme_filename(theme)}.md").write_text(
            frontmatter.dumps(post), encoding="utf-8"
        )
    info = participants.set_index("participant_id").to_dict("index")
    for pid, subset in codes.groupby("participant_id", sort=True):
        p = info.get(pid, {})
        body = "\n".join(
            f'- [[{_theme_filename(theme)}|{theme}]]: "{quote}"'
            for theme, quote in zip(subset.theme, subset.quote, strict=True)
        )
        post = frontmatter.Post(
            body, participant_id=pid, name=p.get("name"), age=p.get("age")
        )
        (vault / f"{pid}.md").write_text(frontmatter.dumps(post), encoding="utf-8")
    LOGGER.info(
        "Wrote %d theme notes and %d participant notes to %s",
        len(prevalence),
        len(info),
        vault,
    )
    return vault
