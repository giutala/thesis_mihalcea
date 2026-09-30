"""Explore embeddings as a cross-check, not a replacement for manual coding."""

from __future__ import annotations

import logging

import hdbscan
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import umap
from sentence_transformers import SentenceTransformer

from scripts._common import ROOT, get_data

LOGGER = logging.getLogger(__name__)
VALIDATION_NOTE = "Algorithmic cross-check only; manual coding remains authoritative."


def embedding_crosscheck(
    codes: pd.DataFrame | None = None,
    save: bool = True,
    model_name: str = "paraphrase-multilingual-MiniLM-L12-v2",
) -> tuple[pd.DataFrame, go.Figure, pd.DataFrame]:
    """Create an exploratory semantic clustering cross-check of coded quotes.

    Parameters
    ----------
    codes : pandas.DataFrame or None, default=None
        Manually coded excerpts; load project data when omitted.
    save : bool, default=True
        Save the cluster/theme crosstab and interactive HTML scatterplot.
    model_name : str, default="paraphrase-multilingual-MiniLM-L12-v2"
        Multilingual sentence-transformer model identifier.

    Returns
    -------
    tuple of pandas.DataFrame, plotly.graph_objects.Figure, pandas.DataFrame
        Cluster-by-manual-theme counts, interactive scatter, and excerpts with
        cluster labels and two-dimensional UMAP coordinates.

    Raises
    ------
    KeyError
        If required excerpt fields are absent.
    OSError
        If the model cannot be loaded from the local cache or model repository.

    Notes
    -----
    Clusters are noisy with this small dataset and serve only as a validation
    layer and second opinion. The manual ``theme`` column remains authoritative.
    """
    codes = get_data(codes).reset_index(drop=True)
    embeddings = SentenceTransformer(model_name).encode(
        codes.quote.fillna("").tolist(), show_progress_bar=False
    )
    n = len(codes)
    coords = umap.UMAP(
        n_components=2,
        n_neighbors=min(5, max(2, n - 1)),
        min_dist=0.15,
        metric="cosine",
        random_state=17,
        n_jobs=1,
    ).fit_transform(embeddings)
    labels = hdbscan.HDBSCAN(min_cluster_size=2, min_samples=1).fit_predict(coords)
    assert len(labels) == len(codes), "Every excerpt must receive one cluster label"
    result = codes[["participant_id", "question_id", "quote", "theme"]].copy()
    result["cluster"] = labels
    table = pd.crosstab(result.cluster, result.theme)
    result["UMAP 1"], result["UMAP 2"] = coords[:, 0], coords[:, 1]
    result["cluster"] = result.cluster.astype(str)
    fig = px.scatter(
        result,
        x="UMAP 1",
        y="UMAP 2",
        color="cluster",
        symbol="theme",
        hover_data=["participant_id", "question_id", "quote"],
        title="Embedding cross-check (exploratory; manual themes remain authoritative)",
    )
    if save:
        (ROOT / "outputs/tables").mkdir(parents=True, exist_ok=True)
        (ROOT / "outputs/interactive").mkdir(parents=True, exist_ok=True)
        table.to_csv(ROOT / "outputs/tables/cluster_vs_theme.csv", encoding="utf-8-sig")
        fig.write_html(str(ROOT / "outputs/interactive/embedding_crosscheck.html"))
        LOGGER.info("Saved exploratory cluster cross-check table and figure")
    return table, fig, result
