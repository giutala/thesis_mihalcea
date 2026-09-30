"""Descriptive theme comparison across the interview questions."""

from __future__ import annotations

import logging

import matplotlib.figure
import pandas as pd
from matplotlib import pyplot as plt

from scripts._common import ROOT, get_data

LOGGER = logging.getLogger(__name__)


def compare_questions(
    codes: pd.DataFrame | None = None, save: bool = True
) -> tuple[pd.DataFrame, pd.DataFrame, matplotlib.figure.Figure]:
    """Summarize coded themes by question and participant.

    Parameters
    ----------
    codes : pandas.DataFrame or None, default=None
        Coded excerpts; load project data when omitted.
    save : bool, default=True
        Save the summary CSV and 300 dpi question chart.

    Returns
    -------
    tuple of pandas.DataFrame, pandas.DataFrame, matplotlib.figure.Figure
        Question/theme excerpt crosstab, readable participant summary, and
        question-level bar chart.

    Raises
    ------
    KeyError
        If required question, theme, participant, or quote columns are absent.

    Notes
    -----
    Counts are descriptive of the supplied interview sample and do not imply
    population-level agreement or statistical significance.
    """
    codes = get_data(codes)
    counts = pd.crosstab(codes["question_id"], codes["theme"])
    long = counts.stack().rename("excerpt_count").reset_index()
    long = long[long.excerpt_count > 0]
    participants = (
        codes.groupby(["question_id", "theme"])["participant_id"]
        .agg(lambda x: ", ".join(sorted(set(x))))
        .rename("participants")
        .reset_index()
    )
    summary = long.merge(participants, on=["question_id", "theme"])
    summary["participant_count"] = summary["participants"].map(
        lambda x: len(x.split(", "))
    )
    assert int(counts.to_numpy().sum()) == len(codes), "Question crosstab lost excerpts"
    assert (summary["participant_count"] <= summary["excerpt_count"]).all()
    fig, axes = plt.subplots(
        len(counts), 1, figsize=(11, max(3, 2.8 * len(counts))), squeeze=False
    )
    for ax, (question, row) in zip(axes[:, 0], counts.iterrows(), strict=True):
        present = row[row > 0].sort_values(ascending=False)
        ax.barh(present.index, present.values, color="#4B8490")
        ax.set_title(str(question), loc="left")
        ax.set_xlabel("Coded excerpts")
        ax.invert_yaxis()
    fig.tight_layout()
    if save:
        (ROOT / "outputs/figures").mkdir(parents=True, exist_ok=True)
        (ROOT / "outputs/tables").mkdir(parents=True, exist_ok=True)
        fig.savefig(
            ROOT / "outputs/figures/question_comparison.png",
            dpi=300,
            bbox_inches="tight",
        )
        summary.to_csv(
            ROOT / "outputs/tables/question_comparison.csv",
            index=False,
            encoding="utf-8-sig",
        )
        LOGGER.info("Saved question comparison table and figure")
    return counts, summary, fig
