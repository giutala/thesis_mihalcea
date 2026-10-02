# Qualitative interview analysis workspace

This repository contains a manually coded excerpt analysis and a local,
human-reviewed transcript exploration workflow. NLP outputs are search and
organization aids. They do not assign definitive themes, reconstruct participant
meaning, or validate the original manual coding.

## Folder layout

```text
data/
  raw/                  Source workbooks; do not edit in analysis scripts
  processed/            Normalized codebook data and local SQLite inspection DB
  checkpoints/          Local pipeline checkpoints
docs/                   Methodology, findings, and workflow notes
notebooks/              Reproducible analysis and transcript exploration
outputs/
  figures/              Thesis-ready summary figures
    transcript_review/  Static JPEG review figures
  tables/               Codebook summary tables
  transcript_review/    Sensitive transcript-derived review artifacts
scripts/                Reusable analysis functions
tests/                  Small software behavior checks
```

The raw workbooks are ignored by Git because transcripts and derived excerpts
may contain sensitive data:

- `data/raw/final_codebook_updated_visual.xlsx`
- `data/raw/interviste_trascrizioni.xlsx`
- `data/raw/domande_comuni.xlsx`

## Run the analysis

Install Python 3.12 and `uv`, then run:

```powershell
uv sync --all-groups
uv run jupyter nbconvert --to notebook --execute --inplace notebooks/results.ipynb
uv run jupyter nbconvert --to notebook --execute --inplace notebooks/transcript_exploration.ipynb
```

The first notebook rebuilds descriptive codebook tables and figures. The
transcript notebook uses the cached multilingual sentence-transformer model to
create quote-alignment candidates, adapted-question candidates, theme-based
passage retrieval, and an editable affinity map. It runs embeddings locally and
does not upload transcript text. If the embedding model is not cached, set
`ALLOW_MODEL_DOWNLOAD = True` in the notebook's first code cell to download the
model weights. Model outputs are candidates for human review.

The transcript notebook generates static JPEG figures in
`outputs/figures/transcript_review/` and displays them inline: a case-by-theme
matrix, quote-alignment summary, question-guide section summary, theme retrieval
summary, and affinity-neighbor map. These are presentation aids; candidate
similarity and counts do not establish meaning, exposure, or importance. Review
the supporting CSVs before interpreting any figure.

The question workbook lists common base prompts, not a verbatim script. The
workflow ranks likely question matches but leaves the confirmed question ID and
review note blank for an analyst, since prompts may be adapted or skipped.

## Transcript-review artifacts

Generated under `outputs/transcript_review/`:

- `transcript_rows.csv` and `transcript_turns.csv`: source row references,
  speaker role, participant ID, and text.
- `quote_alignment.csv`: exact normalized quote locations plus lexical
  candidates for unmatched excerpts; candidates are explicitly unverified.
- `question_alignment_candidates.csv`: top semantic matches between
  interviewer turns and base questions.
- `question_alignment_review.csv`: persisted human decisions and notes keyed by
  interviewer turn; reruns carry these decisions forward.
- `theme_passage_candidates.csv`: additional passages near existing manual
  theme evidence.
- `theme_passage_review.csv`: persisted relevance labels and notes for retrieved
  passages.
- `affinity_passages.csv` and `affinity_candidates.csv`: evidence cards and
  cross-participant semantic-neighbor suggestions for manual affinity grouping.
- `affinity_passage_review.csv` and `affinity_edge_review.csv`: editable,
  persisted analyst groups, summaries, counterexamples, and accepted links.
- `../figures/transcript_review/`: JPEG figures displayed by the transcript
  notebook. The affinity map is an index for case review; each link needs
  excerpt-level interpretation.
- `emotion_cues.csv`: optional FEEL-IT sentiment/emotion predictions. This is
  off by default and requires model weights to be available locally or an
  explicit download choice.

Quote candidates and affinity links must be checked against the transcript
rows and surrounding dialogue. The FEEL-IT classifiers were trained on Italian
social-media text, so their outputs are cues rather than validated measures of
interview emotion. Do not interpret model confidence as certainty.

## Documentation

- `docs/methodology.md`: source, methods, limits, and study details requiring
  confirmation from primary records.
- `docs/findings_and_design_implications.md`: codebook-based interpretation
  draft and design hypotheses.
- `docs/transcript_workflow.md`: transcript NLP process, review protocol, and
  interpretation boundaries.

The existing codebook contains 76 excerpt rows, 10 participant IDs, 9 question
IDs, and 5 manual themes. Counts are corpus descriptors, not prevalence or
importance estimates. The source codebook question IDs are not mapped directly
to the 41-question common guide; the new workflow provides reviewable
turn/question candidates instead of assuming equivalence.

## Quality checks

```powershell
uv run ruff check scripts tests
uv run ruff format --check scripts tests
uv run mypy scripts
uv run pytest
```

These software checks do not establish the validity of the original coding or
the analyst's interpretations. Review quote use against participant consent
and disclosure requirements before sharing generated files.
