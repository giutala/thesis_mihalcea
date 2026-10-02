"""Shared paths and codebook loading for analysis modules."""

from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

LOGGER = logging.getLogger(__name__)
ROOT = Path(__file__).resolve().parents[1]
RAW_DATA = ROOT / "data" / "raw"
CODEBOOK_WORKBOOK = RAW_DATA / "final_codebook_updated_visual.xlsx"
TRANSCRIPTS_WORKBOOK = RAW_DATA / "interviste_trascrizioni.xlsx"
QUESTIONS_WORKBOOK = RAW_DATA / "domande_comuni.xlsx"


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
        result = codes.copy()
    else:
        path = ROOT / "data/processed/codes.csv"
        if path.exists():
            LOGGER.info("Loading processed codebook from %s", path)
            result = pd.read_csv(path, encoding="utf-8-sig")
        else:
            workbook = CODEBOOK_WORKBOOK
            if not workbook.exists():
                raise FileNotFoundError(f"Codebook workbook not found: {workbook}")
            LOGGER.info("Loading codebook from %s", workbook)
            result = pd.read_excel(workbook, sheet_name="Codebook")
    if "participant_id" in result:
        result["participant_id"] = (
            result["participant_id"].astype(str).str.extract(r"^(P\d+)", expand=False)
        )
    return result
