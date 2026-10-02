"""Create static JPEG figures for the transcript-review notebook."""

from __future__ import annotations

import textwrap
from pathlib import Path

import matplotlib
import networkx as nx
import pandas as pd
import seaborn as sns

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from scripts._common import ROOT

REVIEW_DIR = ROOT / "outputs" / "transcript_review"
FIGURE_DIR = ROOT / "outputs" / "figures" / "transcript_review"


def _read(name: str) -> pd.DataFrame:
    return pd.read_csv(REVIEW_DIR / name, encoding="utf-8-sig", dtype=str).fillna("")


def _save(fig: plt.Figure, name: str) -> Path:
    FIGURE_DIR.mkdir(parents=True, exist_ok=True)
    path = FIGURE_DIR / name
    fig.savefig(
        path,
        dpi=180,
        bbox_inches="tight",
        facecolor="white",
        pil_kwargs={"quality": 94},
    )
    plt.close(fig)
    return path


def _theme_retrieval(themes: pd.DataFrame) -> Path:
    data = themes.copy()
    data["similarity"] = pd.to_numeric(data["similarity"], errors="coerce")
    fig, ax = plt.subplots(figsize=(12, max(5, data["theme_query"].nunique() * 0.85)))
    sns.boxplot(
        data=data,
        x="similarity",
        y="theme_query",
        color="#8da9bd",
        showfliers=False,
        ax=ax,
    )
    sns.stripplot(
        data=data,
        x="similarity",
        y="theme_query",
        color="#244e6b",
        size=3.5,
        alpha=0.55,
        jitter=0.18,
        ax=ax,
    )
    ax.set(
        title="Embedding similarity scores for retrieved theme passages",
        xlabel="Cosine similarity to manual-theme examples (model score)",
        ylabel="Manual theme query",
    )
    ax.grid(axis="x", alpha=0.2)
    fig.subplots_adjust(bottom=0.18)
    fig.text(
        0.01,
        0.02,
        "Scores rank candidates for review; they do not measure relevance or "
        "validate a theme.",
        fontsize=9,
        color="#52606d",
    )
    return _save(fig, "theme_retrieval.jpg")


def _question_sections(questions: pd.DataFrame) -> Path:
    data = questions.copy()
    data["guide_section"] = data["guide_section"].replace("", "Section not recorded")
    summary = (
        data.groupby("guide_section")
        .agg(turns=("turn_id", "nunique"), participants=("participant_id", "nunique"))
        .sort_values("turns")
    )
    fig, ax = plt.subplots(figsize=(11, max(4.5, len(summary) * 0.9)))
    bars = ax.barh(summary.index, summary["turns"], color="#bf8050")
    ax.set(
        title="Top-ranked base-question candidates by guide section",
        xlabel="Interviewer turns with this candidate",
        ylabel="Guide section",
    )
    ax.grid(axis="x", alpha=0.2)
    for bar, people in zip(bars, summary["participants"], strict=True):
        ax.text(
            bar.get_width() + 0.3,
            bar.get_y() + bar.get_height() / 2,
            f"{int(bar.get_width())} turns · {people} participants",
            va="center",
            fontsize=9,
        )
    fig.text(
        0.01,
        0.02,
        "Candidate rankings do not confirm that a prompt was asked or answered.",
        fontsize=9,
        color="#52606d",
    )
    return _save(fig, "question_candidates_by_section.jpg")


def _affinity_map(edges: pd.DataFrame, passages: pd.DataFrame) -> Path:
    data = edges.copy()
    data["similarity"] = pd.to_numeric(data["cosine_similarity"], errors="coerce")
    data = data[data["similarity"] >= 0.55].nlargest(250, "similarity")
    graph = nx.Graph()
    for row in data.itertuples(index=False):
        graph.add_edge(
            row.source_passage_id, row.target_passage_id, weight=row.similarity
        )
    fig, ax = plt.subplots(figsize=(12, 9))
    if graph.number_of_nodes():
        layout = nx.spring_layout(graph, seed=17, weight="weight", iterations=90)
        passage_people = passages.set_index("passage_id")["participant_id"].to_dict()
        participants = sorted(
            {passage_people[node] for node in graph.nodes if node in passage_people}
        )
        palette = dict(
            zip(
                participants,
                sns.color_palette("tab10", n_colors=len(participants)),
                strict=True,
            )
        )
        nx.draw_networkx_edges(
            graph, layout, ax=ax, alpha=0.38, width=1.2, edge_color="#607080"
        )
        grouped = {
            participant: [
                node for node in graph.nodes if passage_people.get(node) == participant
            ]
            for participant in participants
        }
        for participant, nodes in grouped.items():
            nx.draw_networkx_nodes(
                graph,
                layout,
                nodelist=nodes,
                node_size=28,
                node_color=[palette[participant]],
                label=participant,
                ax=ax,
            )
        ax.legend(
            title="Participant",
            ncol=2,
            frameon=False,
            loc="upper left",
            bbox_to_anchor=(1.01, 1),
        )
        ax.set_title("Cross-participant semantic-neighbor suggestions")
    else:
        ax.text(
            0.5,
            0.5,
            "No candidate edges meet similarity threshold 0.55.",
            ha="center",
            va="center",
        )
    ax.text(
        0.01,
        0.02,
        "Exploration index only. Links do not establish shared meaning or "
        "co-occurrence.",
        transform=ax.transAxes,
        fontsize=9,
        color="#52606d",
    )
    ax.axis("off")
    return _save(fig, "affinity_neighbor_map.jpg")


def _quote_alignment(quote: pd.DataFrame) -> Path:
    counts = quote["alignment_status"].value_counts().sort_values()
    labels = {
        "exact_normalized": "Exact normalized match",
        "candidate_only": "Unverified candidate only",
    }
    fig, ax = plt.subplots(figsize=(9, 4.5))
    bars = ax.barh(
        [labels.get(label, label) for label in counts.index],
        counts.values,
        color=[
            "#6d9b78" if label == "exact_normalized" else "#d2a45f"
            for label in counts.index
        ],
    )
    ax.set(
        title="Manual codebook quote locations in transcripts",
        xlabel="Excerpt rows",
        ylabel="",
    )
    ax.grid(axis="x", alpha=0.2)
    for bar, value in zip(bars, counts.values, strict=True):
        ax.text(
            value + 0.4, bar.get_y() + bar.get_height() / 2, str(value), va="center"
        )
    return _save(fig, "quote_alignment_status.jpg")


def _case_theme_matrix(quote: pd.DataFrame) -> Path:
    presence = pd.crosstab(quote["participant_id"], quote["theme"]).gt(0).astype(int)
    fig, ax = plt.subplots(figsize=(13, 7.5))
    sns.heatmap(
        presence,
        cmap=sns.color_palette(["#edf1f4", "#416b86"], as_cmap=True),
        linewidths=0.5,
        linecolor="white",
        cbar=False,
        annot=True,
        fmt="d",
        ax=ax,
    )
    ax.set(
        title="Participants with at least one coded excerpt by manual theme",
        xlabel="Manual theme",
        ylabel="Participant",
    )
    ax.set_xticklabels(
        [
            "\n".join(textwrap.wrap(label.get_text(), width=24))
            for label in ax.get_xticklabels()
        ],
        rotation=0,
        ha="center",
        fontsize=9,
    )
    ax.set_xlabel(
        "Presence = one or more coded excerpts; not a measure of importance",
        labelpad=15,
    )
    return _save(fig, "case_by_theme.jpg")


def build_visuals() -> list[Path]:
    """Write thesis/review JPEG figures from current transcript-review tables."""
    quote = _read("quote_alignment.csv")
    questions = _read("question_alignment_review.csv")
    themes = _read("theme_passage_review.csv")
    edges = _read("affinity_edge_review.csv")
    passages = _read("affinity_passage_review.csv")
    return [
        _case_theme_matrix(quote),
        _quote_alignment(quote),
        _question_sections(questions),
        _theme_retrieval(themes),
        _affinity_map(edges, passages),
    ]


if __name__ == "__main__":
    for image_path in build_visuals():
        print(image_path)
