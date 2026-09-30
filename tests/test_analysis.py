"""Unit checks for descriptive summaries on a tiny in-memory codebook."""

from __future__ import annotations

import logging
from importlib import import_module

import pandas as pd
from matplotlib import pyplot as plt

build_theme_matrix = import_module("scripts.02_theme_matrix").build_theme_matrix
compare_questions = import_module("scripts.03_question_comparison").compare_questions
cooccurrence_network = import_module(
    "scripts.04_cooccurrence_network"
).cooccurrence_network
is_conventional_commit = import_module(
    "scripts.check_commit_message"
).is_conventional_commit

LOGGER = logging.getLogger(__name__)


def _sample_codes() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "participant_id": ["P01", "P01", "P01", "P02", "P02"],
            "question_id": ["Q1", "Q1", "Q2", "Q1", "Q2"],
            "quote": ["uno", "due", "tre", "quattro", "cinque"],
            "code": ["a", "b", "b", "b", "c"],
            "theme": ["A", "B", "B", "B", "C"],
        }
    )


def test_theme_matrix_counts_participant_presence() -> None:
    codes = _sample_codes()
    matrix = build_theme_matrix(codes)

    assert matrix.loc["A", "P01"] == 1
    assert matrix.loc["B", "P01"] == 1
    assert matrix.loc["B", "P02"] == 1
    assert matrix.loc["C", "P01"] == 0


def test_question_comparison_preserves_excerpt_and_participant_counts() -> None:
    codes = _sample_codes()
    counts, summary, figure = compare_questions(codes, save=False)

    assert int(counts.to_numpy().sum()) == len(codes)
    row = summary.loc[
        (summary["question_id"] == "Q1") & (summary["theme"] == "B")
    ].iloc[0]
    assert row["excerpt_count"] == 2
    assert row["participant_count"] == 2
    plt.close(figure)


def test_cooccurrence_counts_people_once_per_theme_pair() -> None:
    matrix, graph, figure = cooccurrence_network(_sample_codes(), save=False)

    assert matrix.loc["B", "B"] == 2
    assert matrix.loc["A", "B"] == 1
    assert matrix.loc["A", "C"] == 0
    assert graph["A"]["B"]["weight"] == 1
    plt.close(figure)


def test_commit_message_hook_accepts_and_rejects_subjects() -> None:
    assert is_conventional_commit("docs: explain the analysis")
    assert is_conventional_commit("feat(matrix)!: change matrix encoding")
    assert not is_conventional_commit("update docs")
