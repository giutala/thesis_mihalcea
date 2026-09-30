"""Descriptive participant-level theme co-occurrence network."""

from __future__ import annotations

import logging

import matplotlib.pyplot as plt
import networkx as nx
import pandas as pd
from matplotlib.figure import Figure

from scripts._common import ROOT, get_data

LOGGER = logging.getLogger(__name__)


def cooccurrence_network(
    codes: pd.DataFrame | None = None, save: bool = True
) -> tuple[pd.DataFrame, nx.Graph, Figure]:
    """Build the participant-level theme co-occurrence graph.

    Parameters
    ----------
    codes : pandas.DataFrame or None, default=None
        Coded excerpts; load project data when omitted.
    save : bool, default=True
        Save the matrix, static 300 dpi figure, and interactive HTML graph.

    Returns
    -------
    tuple of pandas.DataFrame, networkx.Graph, matplotlib.figure.Figure
        Co-occurrence matrix, weighted graph, and static thesis figure.

    Raises
    ------
    KeyError
        If ``theme`` or ``participant_id`` is absent.

    Notes
    -----
    Each participant contributes at most one count to a theme pair, regardless
    of how many excerpts they supplied for either theme.
    """
    codes = get_data(codes)
    themes = sorted(codes.theme.dropna().unique())
    present = codes.groupby("participant_id").theme.apply(lambda s: set(s))
    matrix = pd.DataFrame(0, index=themes, columns=themes)
    for themes_for_person in present:
        for a in themes_for_person:
            for b in themes_for_person:
                matrix.loc[a, b] += 1
    assert matrix.equals(matrix.T), "Co-occurrence matrix must be symmetric"
    graph = nx.Graph()
    prevalence = codes.groupby("theme").participant_id.nunique()
    assert (
        matrix.to_numpy().diagonal() == prevalence.reindex(themes).to_numpy()
    ).all(), "Diagonal must equal participant prevalence"
    for theme in themes:
        graph.add_node(theme, prevalence=int(prevalence[theme]))
    for i, a in enumerate(themes):
        for b in themes[i + 1 :]:
            weight = int(matrix.loc[a, b])
            if weight:
                graph.add_edge(a, b, weight=weight)
    fig, ax = plt.subplots(figsize=(11, 8))
    pos = nx.spring_layout(graph, seed=17, weight="weight")
    nx.draw_networkx_nodes(
        graph,
        pos,
        node_size=[500 + graph.nodes[n]["prevalence"] * 130 for n in graph],
        node_color="#A8C8C5",
        edgecolors="#285F6D",
        ax=ax,
    )
    nx.draw_networkx_edges(
        graph,
        pos,
        width=[graph[u][v]["weight"] * 1.2 for u, v in graph.edges],
        alpha=0.6,
        edge_color="#55747A",
        ax=ax,
    )
    nx.draw_networkx_labels(graph, pos, font_size=8, ax=ax)
    ax.set_title("Themes co-occurring within participants")
    ax.axis("off")
    fig.tight_layout()
    if save:
        (ROOT / "outputs/figures").mkdir(parents=True, exist_ok=True)
        (ROOT / "outputs/tables").mkdir(parents=True, exist_ok=True)
        (ROOT / "outputs/interactive").mkdir(parents=True, exist_ok=True)
        fig.savefig(
            ROOT / "outputs/figures/cooccurrence_network.png",
            dpi=300,
            bbox_inches="tight",
        )
        matrix.to_csv(
            ROOT / "outputs/tables/cooccurrence_matrix.csv", encoding="utf-8-sig"
        )
        try:
            from pyvis.network import Network

            net = Network(height="750px", width="100%", notebook=False)
            for node, attrs in graph.nodes(data=True):
                net.add_node(node, label=node, value=attrs["prevalence"])
            for source, target, attrs in graph.edges(data=True):
                net.add_edge(
                    source,
                    target,
                    value=attrs["weight"],
                    title=f"{attrs['weight']} participants",
                )
            net.write_html(str(ROOT / "outputs/interactive/cooccurrence_network.html"))
        except ImportError:
            LOGGER.exception("Could not import pyvis to create the interactive network")
        LOGGER.info("Saved co-occurrence matrix, figure, and interactive network")
    return matrix, graph, fig
