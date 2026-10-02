"""Case-oriented evidence tables for reviewing the existing manual codebook."""

from __future__ import annotations

import pandas as pd

from scripts._common import ROOT, get_data


def build_case_theme_matrix(codes: pd.DataFrame) -> pd.DataFrame:
    """Return participant by theme cells containing source row references."""
    work = codes.copy().reset_index(drop=True)
    work["excerpt_id"] = [f"E{i:03d}" for i in range(1, len(work) + 1)]
    work["cell"] = work.apply(
        lambda row: f"{row.excerpt_id} ({row.question_id})", axis=1
    )
    return work.pivot_table(
        index="participant_id",
        columns="theme",
        values="cell",
        aggfunc=lambda values: "; ".join(values),
        fill_value="—",
        sort=True,
    )


def build_evidence_table(codes: pd.DataFrame) -> pd.DataFrame:
    """Retain each coded excerpt with a stable, participant-safe reference."""
    evidence = codes[["participant_id", "question_id", "quote", "code", "theme"]].copy()
    evidence.insert(0, "excerpt_id", [f"E{i:03d}" for i in range(1, len(evidence) + 1)])
    evidence["quote"] = evidence["quote"].fillna("").astype(str).str.strip()
    return evidence


def build_theme_summary(codes: pd.DataFrame) -> pd.DataFrame:
    """Summarize corpus coverage without interpreting frequency as importance."""
    total = int(codes.participant_id.nunique())
    rows = []
    for theme, subset in codes.groupby("theme", sort=True):
        people = int(subset.participant_id.nunique())
        rows.append(
            {
                "theme": theme,
                "participants_with_at_least_one_coded_excerpt": people,
                "participant_denominator": total,
                "coded_excerpt_rows": int(len(subset)),
                "questions_with_theme": int(subset.question_id.nunique()),
                "corpus_descriptor": (
                    f"{people} of {total} participants; {len(subset)} coded excerpts"
                ),
            }
        )
    return pd.DataFrame(rows)


def export_case_analysis(codes: pd.DataFrame | None = None, save: bool = True):
    """Create case matrix, excerpt evidence register, and theme descriptors."""
    codes = get_data(codes)
    evidence = build_evidence_table(codes)
    matrix = build_case_theme_matrix(codes)
    summary = build_theme_summary(codes)
    if save:
        target = ROOT / "outputs" / "tables"
        target.mkdir(parents=True, exist_ok=True)
        matrix.to_csv(target / "case_by_theme_evidence.csv", encoding="utf-8-sig")
        evidence.to_csv(
            target / "excerpt_evidence_register.csv", index=False, encoding="utf-8-sig"
        )
        summary.to_csv(
            target / "theme_corpus_descriptors.csv", index=False, encoding="utf-8-sig"
        )
    return matrix, evidence, summary
