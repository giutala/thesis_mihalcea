# Qualitative interview coding analysis

This project produces descriptive summaries and figures from the manually coded
interview codebook in `final_codebook_updated_visual.xlsx`. The workbook's `code`
and `theme` columns are fixed source data. No analysis step edits them.

All counts describe this small interview sample. The embedding and clustering
step is a validation layer and second opinion only; it does not replace the
researcher's manual coding or establish new findings.

## Setup

Install Python 3.12 and [`uv`](https://docs.astral.sh/uv/), place the source
workbook in the project root, then run:

```powershell
uv sync --all-groups
```

`uv.lock` pins the full environment. No `.env` file or API key is required. The
embedding step downloads the multilingual sentence-transformer model on its
first run and caches it locally.

## Reproduce the results

Run the notebook from the project root:

```powershell
uv run jupyter nbconvert --to notebook --execute --inplace notebooks/results.ipynb
```

The notebook is the presentation deliverable: it shows the workbook validation,
theme matrix, question comparison, participant-level co-occurrence network, and
the clearly labeled embedding cross-check in reading order. It displays figures
inline and saves thesis-ready PNGs at 300 dpi.

Individual analyses are importable modules under `scripts/`. For example:

Because Python import syntax cannot name a module whose filename starts with a
digit, load numbered modules with `importlib.import_module`:

```python
import importlib

make_theme_matrix = importlib.import_module(
    "scripts.02_theme_matrix"
).make_theme_matrix
```

The shared codebook loader is `scripts._common.get_data`.

## Files produced

- `data/processed/codes.csv` and `participants.csv`: normalized codebook data
  and parsed participant details; `analysis.sqlite` provides a local,
  serverless inspection database.
- `data/checkpoints/`: pickled parsed and validated DataFrames for re-running
  downstream stages without reopening or re-parsing the workbook.
- `outputs/tables/`: participant/theme, per-question, co-occurrence, and
  cluster/theme tables.
- `outputs/figures/`: static thesis figures.
- `outputs/interactive/`: HTML network and embedding visualizations.
- `vault/`: linked Obsidian notes for participants and themes.

The codebook, processed excerpts, checkpoint pickles, notebook outputs, HTML
hover text, and Obsidian notes can contain participant names and interview
quotations. They are ignored by Git by default; review them for consent and
disclosure requirements before sharing or changing the ignore rules.

## Development checks

```powershell
uv run ruff check scripts tests
uv run ruff format --check scripts tests
uv run mypy scripts
uv run pytest
```

After this directory is initialized or cloned as a Git repository, install the
hooks with:

```powershell
uv run pre-commit install --hook-type pre-commit --hook-type commit-msg
```

The commit-message hook enforces Conventional Commits (for example,
`feat: add question comparison`).
The analysis has no trade-date or pricing inputs, external API credentials,
database service, or desktop UI, so the unrelated date-filtering, `.env`, and Qt
guidelines do not apply. The requested executable Jupyter notebook is retained
as the main designer deliverable; the analysis also saves interactive Plotly
HTML for exploration.
