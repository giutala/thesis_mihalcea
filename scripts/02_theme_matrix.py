"""Participant-by-theme presence matrix and thesis-ready heatmap."""

from __future__ import annotations

import logging

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
from matplotlib.figure import Figure

from scripts._common import ROOT, get_data

LOGGER = logging.getLogger(__name__)


def build_theme_matrix(codes: pd.DataFrame) -> pd.DataFrame:
    """Build binary participant-by-theme presence from coded excerpts.

    Parameters
    ----------
    codes : pandas.DataFrame
        Excerpts with ``theme``, ``participant_id``, and ``quote`` columns.

    Returns
    -------
    pandas.DataFrame
        Themes as rows and participants as columns; 1 means at least one
        excerpt has that theme for the participant.

    Raises
    ------
    KeyError
        If a required input column is absent.

    Notes
    -----
    Binary presence supports descriptive participant counts and avoids treating
    repeated excerpts from one person as independent participants.
    """
    return (
        codes.pivot_table(
            index="theme",
            columns="participant_id",
            values="quote",
            aggfunc="size",
            fill_value=0,
        )
        .gt(0)
        .astype(int)
    )


def make_theme_matrix(
    codes: pd.DataFrame | None = None, save: bool = True
) -> tuple[pd.DataFrame, Figure]:
    """Create and optionally save the theme matrix and its heatmap.

    Parameters
    ----------
    codes : pandas.DataFrame or None, default=None
        Coded excerpt data; loaded from the project when omitted.
    save : bool, default=True
        Save the CSV matrix and 300 dpi PNG under ``outputs``.

    Returns
    -------
    tuple of pandas.DataFrame and matplotlib.figure.Figure
        Numeric presence matrix and rendered heatmap.

    Raises
    ------
    KeyError
        If required excerpt columns are missing.

    Notes
    -----
    The static PNG is sized for direct insertion into a thesis document.
    """
    codes = get_data(codes)
    matrix = build_theme_matrix(codes)
    fig, ax = plt.subplots(figsize=(12, max(5, len(matrix) * 0.55)))
    sns.heatmap(
        matrix,
        cmap=sns.color_palette(["#F2F3F5", "#285F6D"]),
        vmin=0,
        vmax=1,
        linewidths=0.5,
        linecolor="white",
        cbar=False,
        annot=True,
        fmt="d",
        ax=ax,
    )
    ax.set(
        xlabel="Participant ID",
        ylabel="Manually assigned theme",
        title="Participants with at least one coded excerpt per theme",
    )
    ax.tick_params(axis="x", rotation=45)
    fig.tight_layout()
    if save:
        (ROOT / "outputs/figures").mkdir(parents=True, exist_ok=True)
        (ROOT / "outputs/tables").mkdir(parents=True, exist_ok=True)
        fig.savefig(
            ROOT / "outputs/figures/theme_matrix.png", dpi=300, bbox_inches="tight"
        )
        matrix.to_csv(ROOT / "outputs/tables/theme_matrix.csv", encoding="utf-8-sig")
        LOGGER.info("Saved theme matrix table and figure")
    return matrix, fig


if __name__ == "__main__":
    make_theme_matrix()
