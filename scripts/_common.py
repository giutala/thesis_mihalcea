"""Shared paths and codebook loading for analysis modules."""

from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

LOGGER = logging.getLogger(__name__)
ROOT = Path(__file__).resolve().parents[1]


def get_data(codes: pd.DataFrame | None = None) -> pd.DataFrame:
    """Return supplied coded excerpts or load the project's processed/source data.

    Parameters
    ----------
    codes : pandas.DataFrame or None, default=None
        Already loaded excerpts. When omitted, use ``codes.csv`` if available,
        falling back to the workbook's Codebook sheet.

    Returns
    -------
    pandas.DataFrame
        A copy of the coded excerpt records.

    Raises
    ------
    FileNotFoundError
        If neither the processed CSV nor the source workbook exists.

    Notes
    -----
    Returning a copy prevents analysis functions from mutating authoritative
    codebook data passed in by their caller.
    """
    if codes is not None:
        return codes.copy()
    path = ROOT / "data/processed/codes.csv"
    if path.exists():
        LOGGER.info("Loading processed codebook from %s", path)
        return pd.read_csv(path, encoding="utf-8-sig")
    workbook = ROOT / "final_codebook_updated_visual.xlsx"
    if not workbook.exists():
        raise FileNotFoundError(f"Codebook workbook not found: {workbook}")
    LOGGER.info("Loading codebook from %s", workbook)
    return pd.read_excel(workbook, sheet_name="Codebook")
