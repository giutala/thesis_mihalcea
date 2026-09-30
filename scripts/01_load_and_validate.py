"""Load the qualitative codebook and compare its summaries with the workbook."""

from __future__ import annotations

import logging
import sqlite3
from pathlib import Path
from typing import TypedDict

import pandas as pd
from rich.console import Console
from rich.table import Table

ROOT = Path(__file__).resolve().parents[1]
WORKBOOK = ROOT / "final_codebook_updated_visual.xlsx"
CODE_COLUMNS = ["participant_id", "question_id", "quote", "code", "theme"]
LOGGER = logging.getLogger(__name__)


class WorkbookSchemaError(ValueError):
    """Raised when the workbook sheets do not match the expected schema."""


class ValidationResult(TypedDict):
    """Dataframes returned by the workbook validation pipeline."""

    codes: pd.DataFrame
    participants: pd.DataFrame
    matrix: pd.DataFrame
    matrix_diff: pd.DataFrame
    stats_diff: pd.DataFrame


def _participant_id(value: str) -> str:
    """Return the stable participant token from a full participant label."""
    return str(value).split("_", 1)[0]


def _read_matrix(path: Path) -> pd.DataFrame:
    """Read the manually prepared theme matrix from the source workbook.

    Parameters
    ----------
    path : pathlib.Path
        Workbook containing the Theme Matrix sheet.

    Returns
    -------
    pandas.DataFrame
        Binary matrix indexed by theme and short participant ID.

    Raises
    ------
    WorkbookSchemaError
        If the expected Theme header row is absent.

    Notes
    -----
    The workbook's decorative title rows are skipped by locating the Theme
    header, rather than assuming a fixed row number.
    """
    raw = pd.read_excel(path, sheet_name="Theme Matrix", header=None)
    header_row = next(
        (i for i in range(len(raw)) if str(raw.iat[i, 0]).strip() == "Theme"),
        None,
    )
    if header_row is None:
        raise WorkbookSchemaError("Theme Matrix sheet is missing its Theme header")
    header = raw.iloc[header_row].tolist()
    body = raw.iloc[header_row + 1 :].copy()
    body.columns = header
    body = body[body["Theme"].notna()]
    body = body[~body["Theme"].astype(str).str.lower().str.startswith("prevalence")]
    participants = [c for c in body.columns if str(c).startswith("P")]
    # Workbook headers contain short participant labels; compare by their Pxx prefix.
    out = body.set_index("Theme")[participants].copy()
    out.columns = [str(c).split("\n", 1)[0] for c in out.columns]
    return out.apply(pd.to_numeric, errors="coerce").fillna(0).astype(int)


def load_and_validate(
    workbook: Path = WORKBOOK, export: bool = True
) -> ValidationResult:
    """Load the codebook and compare recomputed summaries to workbook sheets.

    Parameters
    ----------
    workbook : pathlib.Path, default=WORKBOOK
        Excel source workbook.
    export : bool, default=True
        Write normalized codes and participant records to ``data/processed``.

    Returns
    -------
    ValidationResult
        Source records, parsed participants, recomputed matrix, and mismatch
        tables for the workbook's manual matrix and overview.

    Raises
    ------
    FileNotFoundError
        If the workbook does not exist.
    WorkbookSchemaError
        If required columns or parseable participant labels are missing.

    Notes
    -----
    Workbook coding is treated as fixed input. The recomputed matrix and
    overview are diagnostics; this function never changes code or theme labels.
    """
    workbook = Path(workbook)
    if not workbook.is_file():
        raise FileNotFoundError(f"Workbook not found: {workbook}")
    codes = pd.read_excel(workbook, sheet_name="Codebook")
    missing = sorted(set(CODE_COLUMNS).difference(codes.columns))
    if missing:
        raise WorkbookSchemaError(f"Codebook is missing required columns: {missing}")
    codes = codes[CODE_COLUMNS].dropna(subset=["participant_id", "theme"]).copy()
    codes["participant_id"] = codes["participant_id"].astype(str)
    ids = codes["participant_id"].drop_duplicates()
    participants = pd.DataFrame({"participant_id": ids})
    # Current workbook labels use Pxx_<participant description> and omit age.
    participants["id"] = participants["participant_id"].str.extract(r"^(P\d+)")
    participants["name"] = participants["participant_id"].str.replace(r"^P\d+_", "", regex=True)
    participants["age"] = pd.NA
    if participants["id"].isna().any():
        bad_ids = participants.loc[participants["id"].isna(), "participant_id"].tolist()
        raise WorkbookSchemaError(f"Could not parse participant IDs: {bad_ids}")
    matrix = pd.crosstab(codes["theme"], codes["participant_id"])
    matrix = (matrix > 0).astype(int)
    matrix.index.name = "Theme"
    matrix.columns.name = "participant_id"

    sheets = pd.ExcelFile(workbook).sheet_names
    if "Theme Matrix" in sheets:
        manual = _read_matrix(workbook)
        manual.columns = [str(c).split("\\n", 1)[0] for c in manual.columns]
        expected = matrix.copy()
        expected.columns = [_participant_id(c) for c in expected.columns]
        all_themes = manual.index.union(expected.index)
        all_participants = manual.columns.union(expected.columns)
        expected = expected.reindex(index=all_themes, columns=all_participants, fill_value=0)
        actual = manual.reindex(index=all_themes, columns=all_participants, fill_value=0)
        matrix_diff = actual.compare(expected, keep_equal=False)
    else:
        matrix_diff = pd.DataFrame()

    assert matrix.isin([0, 1]).all().all(), "Theme matrix must contain only presence values"
    recomputed = {
        "Participants": int(codes["participant_id"].nunique()),
        "Coded excerpts": int(len(codes)),
        "Themes": int(codes["theme"].nunique()),
    }
    if "Overview" in sheets:
        overview = pd.read_excel(workbook, sheet_name="Overview", header=None)
        metric_values = {}
        for _, row in overview.iterrows():
            if len(row) > 1 and pd.notna(row.iloc[0]) and pd.notna(row.iloc[1]):
                metric_values[str(row.iloc[0]).strip()] = row.iloc[1]
        stats_diff = pd.DataFrame([
            {"metric": k, "workbook": metric_values.get(k), "recomputed": v,
             "match": str(metric_values.get(k)) == str(v)
             or (pd.notna(metric_values.get(k)) and float(metric_values[k]) == v)}
            for k, v in recomputed.items()
        ])
        theme_counts = codes.groupby("theme")["participant_id"].nunique().rename("recomputed")
        manual_counts = {}
        for _, row in overview.iterrows():
            if len(row) > 4 and pd.notna(row.iloc[3]) and pd.notna(row.iloc[4]):
                manual_counts[str(row.iloc[3]).strip()] = row.iloc[4]
        for theme, n in theme_counts.items():
            stats_diff.loc[len(stats_diff)] = {
                "metric": f"Theme prevalence: {theme}", "workbook": manual_counts.get(theme),
                "recomputed": int(n), "match": pd.notna(manual_counts.get(theme))
                and int(manual_counts[theme]) == int(n)}
    else:
        stats_diff = pd.DataFrame(columns=["metric", "workbook", "recomputed", "match"])

    LOGGER.info(
        "Validated %d participants, %d excerpts, and %d themes",
        recomputed["Participants"],
        recomputed["Coded excerpts"],
        recomputed["Themes"],
    )
    if export:
        destination = ROOT / "data" / "processed"
        destination.mkdir(parents=True, exist_ok=True)
        codes.to_csv(destination / "codes.csv", index=False, encoding="utf-8-sig")
        participants.to_csv(
            destination / "participants.csv", index=False, encoding="utf-8-sig"
        )
        checkpoint_dir = ROOT / "data" / "checkpoints"
        checkpoint_dir.mkdir(parents=True, exist_ok=True)
        codes.to_pickle(checkpoint_dir / "parsed_codes.pkl")
        participants.to_pickle(checkpoint_dir / "parsed_participants.pkl")
        matrix.to_pickle(checkpoint_dir / "validated_theme_matrix.pkl")
        matrix_diff.to_pickle(checkpoint_dir / "matrix_diff.pkl")
        stats_diff.to_pickle(checkpoint_dir / "overview_diff.pkl")
        database_path = destination / "analysis.sqlite"
        with sqlite3.connect(database_path) as connection:
            codes.to_sql("codes", connection, if_exists="replace", index=False)
            participants.to_sql(
                "participants", connection, if_exists="replace", index=False
            )
            matrix.to_sql("theme_matrix", connection, if_exists="replace", index=True)
            stats_diff.to_sql(
                "validation_checks", connection, if_exists="replace", index=False
            )
        LOGGER.info(
            "Saved processed CSVs, stage checkpoints, and SQLite inspection database"
        )
    return {
        "codes": codes,
        "participants": participants,
        "matrix": matrix,
        "matrix_diff": matrix_diff,
        "stats_diff": stats_diff,
    }


if __name__ == "__main__":
    result = load_and_validate()
    console = Console()
    console.print("[bold]Matrix mismatches[/bold]")
    console.print(
        result["matrix_diff"].to_string() if not result["matrix_diff"].empty else "None"
    )
    overview_table = Table(title="Overview checks")
    for column in result["stats_diff"].columns:
        overview_table.add_column(str(column))
    for row in result["stats_diff"].itertuples(index=False, name=None):
        overview_table.add_row(*(str(value) for value in row))
    console.print(overview_table)
