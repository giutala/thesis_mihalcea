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
    denominators = codes.groupby("question_id")["participant_id"].nunique()
    summary["participants_with_any_coded_excerpt_for_question"] = summary[
        "question_id"
    ].map(denominators)
    summary["participants_in_codebook"] = codes["participant_id"].nunique()
    summary["participant_descriptor"] = summary.apply(
        lambda row: (
            f"{row.participant_count} of "
            f"{row.participants_with_any_coded_excerpt_for_question} coded respondents"
        ),
        axis=1,
    )
    assert int(counts.to_numpy().sum()) == len(codes), "Question crosstab lost excerpts"
    assert (summary["participant_count"] <= summary["excerpt_count"]).all()
    fig, axes = plt.subplots(
        len(counts), 1, figsize=(11, max(3, 2.8 * len(counts))), squeeze=False
    )
    for ax, (question, row) in zip(axes[:, 0], counts.iterrows(), strict=True):
        present = row[row > 0].sort_values(ascending=False)
        participant_counts = (
            summary.loc[summary.question_id == question]
            .set_index("theme")["participant_count"]
            .reindex(present.index)
        )
        y = range(len(present))
        ax.barh(
            [v - 0.18 for v in y],
            participant_counts,
            height=0.34,
            color="#285F6D",
            label="Participants",
        )
        ax.barh(
            [v + 0.18 for v in y],
            present.values,
            height=0.34,
            color="#B8C9CC",
            label="Excerpt rows",
        )
        ax.set_yticks(list(y), labels=present.index)
        ax.set_title(str(question), loc="left")
        ax.set_xlabel("Corpus descriptors (people and excerpt rows)")
        ax.legend(frameon=False, fontsize=8)
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
