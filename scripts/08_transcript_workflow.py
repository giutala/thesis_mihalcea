"""Human-review workflow for transcript alignment, retrieval, and affinity cues."""

from __future__ import annotations

import re
import unicodedata
from itertools import pairwise
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from scripts._common import (
    CODEBOOK_WORKBOOK,
    QUESTIONS_WORKBOOK,
    TRANSCRIPTS_WORKBOOK,
)

MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
SENTIMENT_MODEL = "MilaNLProc/feel-it-italian-sentiment"
EMOTION_MODEL = "MilaNLProc/feel-it-italian-emotion"
ROLE_PATTERN = re.compile(r"^\s*(Intervistatrice|P\d{1,2})(?:\s+\d+)?\s*:\s*", re.I)
INTERROGATIVE_CUE = re.compile(
    r"\b(come|quale|quali|quanto|quanti|quanta|quante|cosa|perche|"
    r"quando|dove|chi|quale|hai|pensi|ti capita|ci sono|in quali|su quali)\b",
    re.I,
)


def _participant_id(value: Any) -> str:
    """Normalize transcript and codebook labels to IDs such as ``P01``."""
    match = re.match(r"\s*(P\d{1,2})", str(value), flags=re.I)
    if not match:
        raise ValueError(f"Unrecognized participant identifier: {value!r}")
    return match.group(1).upper()


def _normalize_text(value: Any) -> str:
    """Normalize punctuation, accents, and spacing for quote matching."""
    text = unicodedata.normalize("NFKD", str(value).casefold())
    text = "".join(char for char in text if not unicodedata.combining(char))
    return " ".join(re.findall(r"[a-z0-9]+", text))


def load_question_guide(path: Path = QUESTIONS_WORKBOOK) -> pd.DataFrame:
    """Read the guide table without treating its prompts as verbatim turns."""
    raw = pd.read_excel(path, sheet_name=0, header=None, dtype=object)
    header_row = next(
        (
            row_index
            for row_index in range(len(raw))
            if [_normalize_text(value) for value in raw.iloc[row_index, :3]]
            == ["id", "sezione", "domanda"]
        ),
        None,
    )
    if header_row is None:
        raise ValueError("Question guide needs ID, Sezione, and Domanda columns")
    rows = raw.iloc[header_row + 1 :, :3].copy()
    rows.columns = ["question_id", "section", "base_question"]
    rows = rows.dropna(subset=["question_id", "base_question"])
    rows["question_id"] = rows["question_id"].astype(str).str.strip()
    rows["section"] = rows["section"].ffill().astype(str).str.strip()
    rows["base_question"] = rows["base_question"].astype(str).str.strip()
    rows = rows[rows["question_id"].str.match(r"^Q\d+$", case=False)].reset_index(
        drop=True
    )
    rows["guide_note"] = "Common base question; wording and exposure may vary."
    return rows


def load_transcript_rows(path: Path = TRANSCRIPTS_WORKBOOK) -> pd.DataFrame:
    """Load transcript rows, recognize explicit speakers, retain row references."""
    raw = pd.read_excel(path, sheet_name=0, dtype=object)
    required = {"Partecipante", "Riga", "Trascrizione"}
    if not required.issubset(raw.columns):
        raise ValueError(f"Transcript workbook needs columns: {sorted(required)}")
    raw = raw.dropna(subset=["Partecipante", "Riga", "Trascrizione"]).copy()
    raw["participant_id"] = raw["Partecipante"].map(_participant_id)
    raw["row_number"] = pd.to_numeric(raw["Riga"], errors="raise").astype(int)
    raw["source_text"] = raw["Trascrizione"].astype(str).str.strip()
    raw = raw.sort_values(["participant_id", "row_number"], kind="stable")

    speakers: list[str] = []
    texts: list[str] = []
    for participant, text in zip(
        raw["participant_id"], raw["source_text"], strict=True
    ):
        match = ROLE_PATTERN.match(text)
        if match:
            role = (
                "interviewer"
                if match.group(1).casefold() == "intervistatrice"
                else "participant"
            )
            expected_id = (
                _participant_id(match.group(1)) if role == "participant" else None
            )
            if expected_id is not None and expected_id != participant:
                raise ValueError(
                    f"Speaker label {expected_id} disagrees with row "
                    f"participant {participant}"
                )
            speakers.append(role)
            texts.append(text[match.end() :].strip())
        elif ":" in text and len(text.split(":", 1)[0]) < 40:
            # A timestamp/other tag is a boundary, not safe to attribute by inheritance.
            speakers.append("unknown")
            texts.append(text)
        else:
            speakers.append("continuation")
            texts.append(text)
    raw["speaker_marker"] = speakers
    raw["text"] = texts

    resolved: list[str] = []
    for _, subset in raw.groupby("participant_id", sort=False):
        current = "unknown"
        for marker in subset["speaker_marker"]:
            if marker in {"interviewer", "participant", "unknown"}:
                current = marker
            resolved.append(current)
    raw["speaker"] = resolved
    raw["row_id"] = raw.apply(
        lambda row: f"{row.participant_id}-R{row.row_number:04d}", axis=1
    )
    return raw[
        ["row_id", "participant_id", "row_number", "speaker", "speaker_marker", "text"]
    ].reset_index(drop=True)


def build_transcript_turns(rows: pd.DataFrame) -> pd.DataFrame:
    """Join consecutive speaker rows into traceable turns."""
    turns: list[dict[str, Any]] = []
    for participant, subset in rows.groupby("participant_id", sort=True):
        current: list[pd.Series] = []
        participant_turn_number = 0
        for _, row in subset.iterrows():
            if current and row["speaker"] != current[-1]["speaker"]:
                turns.append(
                    _turn_record(participant, participant_turn_number, current)
                )
                participant_turn_number += 1
                current = []
            current.append(row)
        if current:
            turns.append(_turn_record(participant, participant_turn_number, current))

    result = pd.DataFrame(turns)
    result["previous_interviewer_turn_id"] = pd.NA
    for _, subset in result.groupby("participant_id", sort=False):
        previous_interviewer = pd.NA
        for index in subset.index:
            if result.at[index, "speaker"] == "interviewer":
                previous_interviewer = result.at[index, "turn_id"]
            elif result.at[index, "speaker"] == "participant":
                result.at[index, "previous_interviewer_turn_id"] = previous_interviewer
    return result


def _turn_record(
    participant: str, turn_number: int, rows: list[pd.Series]
) -> dict[str, Any]:
    return {
        "turn_id": f"{participant}-T{turn_number + 1:04d}",
        "participant_id": participant,
        "speaker": rows[0]["speaker"],
        "row_start": int(rows[0]["row_number"]),
        "row_end": int(rows[-1]["row_number"]),
        "text": " ".join(str(row["text"]) for row in rows if str(row["text"]).strip()),
        "source_row_ids": ";".join(str(row["row_id"]) for row in rows),
    }


def _find_exact_quote(
    quote: str, subset: pd.DataFrame
) -> tuple[int | None, int | None]:
    target = _normalize_text(quote)
    if not target:
        return None, None
    parts: list[str] = []
    offsets: list[tuple[int, int, int]] = []
    cursor = 0
    for row in subset.itertuples(index=False):
        text = _normalize_text(row.text)
        if not text:
            continue
        if parts:
            cursor += 1
        start = cursor
        parts.append(text)
        cursor += len(text)
        offsets.append((start, cursor, int(row.row_number)))
    corpus = " ".join(parts)
    location = corpus.find(target)
    if location < 0:
        return None, None
    end = location + len(target)
    matched = [
        row_number
        for start, stop, row_number in offsets
        if start < end and stop > location
    ]
    return (min(matched), max(matched)) if matched else (None, None)


def align_codebook_quotes(
    codes: pd.DataFrame,
    rows: pd.DataFrame,
    fuzzy_windows: int = 4,
) -> pd.DataFrame:
    """Find exact quote spans and rank lexical candidates for manual review."""
    entries = codes.copy().reset_index(drop=True)
    entries["participant_id"] = entries["participant_id"].map(_participant_id)
    entries.insert(0, "excerpt_id", [f"E{i:03d}" for i in range(1, len(entries) + 1)])
    output: list[dict[str, Any]] = []

    for participant, participant_codes in entries.groupby("participant_id", sort=False):
        subset = rows[rows["participant_id"] == participant].sort_values("row_number")
        candidates = _row_windows(subset, fuzzy_windows)
        normalized_candidates = [_normalize_text(item["text"]) for item in candidates]
        queries = [_normalize_text(value) for value in participant_codes["quote"]]
        vectorizer = TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5))
        candidate_matrix = vectorizer.fit_transform(normalized_candidates + queries)
        candidate_vectors = candidate_matrix[: len(candidates)]
        query_vectors = candidate_matrix[len(candidates) :]

        for local_index, (_, code) in enumerate(participant_codes.iterrows()):
            exact_start, exact_end = _find_exact_quote(code["quote"], subset)
            similarities = cosine_similarity(
                query_vectors[local_index], candidate_vectors
            ).ravel()
            best_index = int(np.argmax(similarities)) if len(similarities) else 0
            best = candidates[best_index] if candidates else {}
            exact = exact_start is not None
            output.append(
                {
                    "excerpt_id": code["excerpt_id"],
                    "participant_id": participant,
                    "question_id_in_codebook": code.get("question_id"),
                    "theme": code.get("theme"),
                    "manual_code": code.get("code"),
                    "codebook_quote": code.get("quote"),
                    "alignment_status": "exact_normalized"
                    if exact
                    else "candidate_only",
                    "transcript_row_start": exact_start
                    if exact
                    else best.get("row_start"),
                    "transcript_row_end": exact_end if exact else best.get("row_end"),
                    "candidate_similarity": (
                        1.0 if exact else float(similarities[best_index])
                    ),
                    "candidate_text": "" if exact else best.get("text", ""),
                    "review_status": "verified exact"
                    if exact
                    else "needs human review",
                }
            )
    return pd.DataFrame(output)


def _row_windows(rows: pd.DataFrame, max_window: int) -> list[dict[str, Any]]:
    records = list(rows.itertuples(index=False))
    candidates = []
    for start in range(len(records)):
        for size in range(1, max_window + 1):
            window = records[start : start + size]
            if not window or any(
                int(right.row_number) != int(left.row_number) + 1
                for left, right in pairwise(window)
            ):
                continue
            candidates.append(
                {
                    "row_start": int(window[0].row_number),
                    "row_end": int(window[-1].row_number),
                    "text": " ".join(str(item.text) for item in window),
                }
            )
    return candidates


def _load_embedding_model(local_files_only: bool = True):
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(MODEL_NAME, local_files_only=local_files_only)


def build_question_alignment_candidates(
    turns: pd.DataFrame,
    guide: pd.DataFrame,
    model=None,
    top_k: int = 3,
) -> pd.DataFrame:
    """Rank guide questions for interviewer turns; every match needs review."""
    model = _load_embedding_model() if model is None else model
    interviewer = turns[turns["speaker"] == "interviewer"].copy().reset_index(drop=True)
    if interviewer.empty:
        return pd.DataFrame()
    question_vectors = model.encode(
        guide["base_question"].tolist(), normalize_embeddings=True
    )
    turn_vectors = model.encode(
        interviewer["text"].tolist(), normalize_embeddings=True, show_progress_bar=False
    )
    scores = cosine_similarity(turn_vectors, question_vectors)
    ranked = []
    for row_index, turn in interviewer.iterrows():
        for rank, question_index in enumerate(
            np.argsort(scores[row_index])[::-1][:top_k], start=1
        ):
            question = guide.iloc[int(question_index)]
            ranked.append(
                {
                    "turn_id": turn["turn_id"],
                    "participant_id": turn["participant_id"],
                    "row_start": turn["row_start"],
                    "row_end": turn["row_end"],
                    "interviewer_turn": turn["text"],
                    "question_like_cue": bool(
                        "?" in turn["text"]
                        or INTERROGATIVE_CUE.search(_normalize_text(turn["text"]))
                    ),
                    "candidate_rank": rank,
                    "candidate_question_id": question["question_id"],
                    "guide_section": question["section"],
                    "base_question": question["base_question"],
                    "similarity": float(scores[row_index, question_index]),
                    "alignment_status": "candidate; wording/exposure may vary",
                    "reviewed_question_id": "",
                    "review_note": "",
                }
            )
    return pd.DataFrame(ranked)


def build_theme_retrieval_candidates(
    turns: pd.DataFrame,
    codes: pd.DataFrame,
    alignment: pd.DataFrame,
    model=None,
    per_participant: int = 2,
) -> pd.DataFrame:
    """Retrieve additional participant passages near each existing theme's evidence."""
    model = _load_embedding_model() if model is None else model
    passages = turns[turns["speaker"] == "participant"].copy().reset_index(drop=True)
    if passages.empty:
        return pd.DataFrame()
    passage_vectors = model.encode(
        passages["text"].tolist(), normalize_embeddings=True, show_progress_bar=False
    )
    excluded = set()
    for row in alignment.itertuples(index=False):
        if row.alignment_status == "exact_normalized":
            excluded.add(
                (row.participant_id, row.transcript_row_start, row.transcript_row_end)
            )

    entries = codes.copy()
    entries["participant_id"] = entries["participant_id"].map(_participant_id)
    output = []
    for theme, subset in entries.groupby("theme", sort=True):
        seed_vectors = model.encode(
            subset["quote"].fillna("").astype(str).tolist(),
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        centroid = np.asarray(seed_vectors).mean(axis=0, keepdims=True)
        centroid /= np.linalg.norm(centroid, axis=1, keepdims=True)
        scores = cosine_similarity(passage_vectors, centroid).ravel()
        for participant, indexes in passages.groupby(
            "participant_id", sort=True
        ).groups.items():
            available = [
                index
                for index in indexes
                if not any(
                    p == participant
                    and not (
                        int(passages.at[index, "row_end"]) < int(start)
                        or int(passages.at[index, "row_start"]) > int(end)
                    )
                    for p, start, end in excluded
                )
            ]
            selected = sorted(available, key=lambda index: scores[index], reverse=True)[
                :per_participant
            ]
            for rank, index in enumerate(selected, start=1):
                passage = passages.iloc[index]
                output.append(
                    {
                        "theme_query": theme,
                        "participant_id": participant,
                        "passage_id": passage["turn_id"],
                        "row_start": passage["row_start"],
                        "row_end": passage["row_end"],
                        "similarity": float(scores[index]),
                        "rank_within_participant": rank,
                        "passage_text": passage["text"],
                        "review_label": "",
                        "review_note": "",
                    }
                )
    return pd.DataFrame(output)


def build_affinity_candidates(
    turns: pd.DataFrame, model=None, neighbors_per_passage: int = 3
) -> pd.DataFrame:
    """Create cross-participant semantic-neighbor edges for human affinity mapping."""
    model = _load_embedding_model() if model is None else model
    passages = (
        turns[(turns["speaker"] == "participant") & (turns["text"].str.len() >= 40)]
        .copy()
        .reset_index(drop=True)
    )
    if len(passages) < 2:
        return pd.DataFrame()
    vectors = model.encode(
        passages["text"].tolist(), normalize_embeddings=True, show_progress_bar=False
    )
    scores = cosine_similarity(vectors)
    edges = []
    for source_index, source in passages.iterrows():
        candidates = [
            index
            for index in range(len(passages))
            if passages.at[index, "participant_id"] != source["participant_id"]
        ]
        nearest = sorted(
            candidates, key=lambda index: scores[source_index, index], reverse=True
        )[:neighbors_per_passage]
        for rank, target_index in enumerate(nearest, start=1):
            target = passages.iloc[target_index]
            edges.append(
                {
                    "source_passage_id": source["turn_id"],
                    "source_participant_id": source["participant_id"],
                    "source_rows": f"{source['row_start']}-{source['row_end']}",
                    "target_passage_id": target["turn_id"],
                    "target_participant_id": target["participant_id"],
                    "target_rows": f"{target['row_start']}-{target['row_end']}",
                    "cosine_similarity": float(scores[source_index, target_index]),
                    "neighbor_rank": rank,
                    "review_status": "unreviewed candidate link",
                    "analyst_affinity_label": "",
                    "review_note": "",
                }
            )
    return pd.DataFrame(edges)


def build_affinity_passages(turns: pd.DataFrame) -> pd.DataFrame:
    """Create editable evidence cards for manual affinity grouping."""
    passages = turns[
        (turns["speaker"] == "participant") & (turns["text"].str.len() >= 40)
    ].copy()
    passages = passages.rename(
        columns={"turn_id": "passage_id", "text": "passage_text"}
    )
    passages["analyst_affinity_group"] = ""
    passages["analyst_summary"] = ""
    passages["counterexample_or_tension"] = ""
    passages["review_status"] = "unreviewed"
    return passages[
        [
            "passage_id",
            "participant_id",
            "row_start",
            "row_end",
            "previous_interviewer_turn_id",
            "passage_text",
            "analyst_affinity_group",
            "analyst_summary",
            "counterexample_or_tension",
            "review_status",
        ]
    ].reset_index(drop=True)


def run_feelit_cues(
    turns: pd.DataFrame, allow_model_download: bool = False
) -> pd.DataFrame:
    """Add optional Italian sentiment/emotion cues, never interpreted as findings."""
    from transformers import (
        AutoModelForSequenceClassification,
        AutoTokenizer,
        pipeline,
    )

    passages = turns[
        (turns["speaker"] == "participant") & (turns["text"].str.len() >= 30)
    ].copy()
    local_only = not allow_model_download
    outputs = passages[
        ["turn_id", "participant_id", "row_start", "row_end", "text"]
    ].copy()
    outputs = outputs.rename(columns={"text": "passage_text"})
    for column, model_name in [
        ("sentiment", SENTIMENT_MODEL),
        ("emotion", EMOTION_MODEL),
    ]:
        tokenizer = AutoTokenizer.from_pretrained(
            model_name, local_files_only=local_only
        )
        model = AutoModelForSequenceClassification.from_pretrained(
            model_name, local_files_only=local_only
        )
        classifier = pipeline(
            "text-classification",
            model=model,
            tokenizer=tokenizer,
            truncation=True,
            max_length=512,
        )
        predictions = classifier(outputs["passage_text"].tolist(), batch_size=8)
        outputs[f"{column}_label"] = [item["label"] for item in predictions]
        outputs[f"{column}_score"] = [float(item["score"]) for item in predictions]
        outputs[f"{column}_model"] = model_name
    outputs["interpretation_note"] = (
        "Machine-generated cue only; FEEL-IT was trained on Italian tweets. "
        "Check negation, irony, mixed emotion, target, and interview context."
    )
    return outputs


def _write_preserving_review(
    path: Path,
    current: pd.DataFrame,
    key_columns: list[str],
    review_columns: list[str],
) -> None:
    """Refresh candidates while carrying analyst decisions forward by stable key."""
    previous = None
    if path.exists():
        previous = pd.read_csv(path, encoding="utf-8-sig", dtype=str).fillna("")
    context_columns = [column for column in current if column not in review_columns]
    review = current[context_columns].copy()
    if previous is not None:
        keep = [column for column in key_columns + review_columns if column in previous]
        old_review = previous[keep].drop_duplicates(key_columns, keep="last")
        review = review.merge(
            old_review, on=key_columns, how="left", validate="one_to_one"
        )
    for column in review_columns:
        if column not in review:
            review[column] = ""
        review[column] = review[column].fillna("")
    review.to_csv(path, index=False, encoding="utf-8-sig")


def build_transcript_review(
    codes: pd.DataFrame | None = None,
    output_dir: Path | None = None,
    include_emotion: bool = False,
    allow_model_download: bool = False,
) -> dict[str, pd.DataFrame]:
    """Build traceable transcript and affinity-review tables using local models."""
    if codes is None:
        codes = pd.read_excel(CODEBOOK_WORKBOOK, sheet_name="Codebook")
    guide = load_question_guide()
    rows = load_transcript_rows()
    turns = build_transcript_turns(rows)
    alignment = align_codebook_quotes(codes, rows)
    model = _load_embedding_model(local_files_only=not allow_model_download)
    question_candidates = build_question_alignment_candidates(turns, guide, model=model)
    theme_candidates = build_theme_retrieval_candidates(
        turns, codes, alignment, model=model
    )
    affinity = build_affinity_candidates(turns, model=model)
    affinity_passages = build_affinity_passages(turns)
    results = {
        "question_guide": guide,
        "transcript_rows": rows,
        "transcript_turns": turns,
        "quote_alignment": alignment,
        "question_alignment_candidates": question_candidates,
        "theme_passage_candidates": theme_candidates,
        "affinity_candidates": affinity,
        "affinity_passages": affinity_passages,
    }
    if include_emotion:
        results["emotion_cues"] = run_feelit_cues(
            turns, allow_model_download=allow_model_download
        )
    if output_dir is not None:
        output_dir.mkdir(parents=True, exist_ok=True)
        for name, frame in results.items():
            frame.to_csv(output_dir / f"{name}.csv", index=False, encoding="utf-8-sig")
        question_review = question_candidates[
            question_candidates["candidate_rank"] == 1
        ].copy()
        question_review["review_decision"] = ""
        _write_preserving_review(
            output_dir / "question_alignment_review.csv",
            question_review,
            ["turn_id"],
            ["reviewed_question_id", "review_decision", "review_note"],
        )
        _write_preserving_review(
            output_dir / "theme_passage_review.csv",
            theme_candidates,
            ["theme_query", "participant_id", "passage_id"],
            ["review_label", "review_note"],
        )
        _write_preserving_review(
            output_dir / "affinity_passage_review.csv",
            affinity_passages,
            ["passage_id"],
            [
                "analyst_affinity_group",
                "analyst_summary",
                "counterexample_or_tension",
                "review_status",
            ],
        )
        _write_preserving_review(
            output_dir / "affinity_edge_review.csv",
            affinity,
            ["source_passage_id", "target_passage_id"],
            ["accepted_affinity_link", "analyst_affinity_label", "review_note"],
        )
    return results
