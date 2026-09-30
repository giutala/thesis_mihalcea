# Methodology and engineering rationale

## Purpose and scope

This document records the analytical and computational methods used to inspect
the manually coded interview excerpts in `final_codebook_updated_visual.xlsx`.
The workbook contains 27 excerpt records from 10 participants, organized under 8
question identifiers and 9 manually assigned themes. The rows, `code` values,
and `theme` values are the authoritative research material for this pipeline.
The scripts reorganize and summarize that material; they do not recode it.

This is a secondary analysis of an existing codebook, not a claim that the
pipeline independently conducted a complete thematic analysis. The original
research question, recruitment strategy, interview setting and protocol,
transcription process, codebook development, number of coders, and resolution
of coding disagreements are not recorded in the workbook. Those details must
be supplied from the study records before this text is used as a complete thesis
methods chapter. Reporting interview research transparently also requires
context about the research team, study design, analysis, and supporting quotes;
the [COREQ checklist](https://doi.org/10.1093/intqhc/mzm042) is a useful
reporting aid for those details.

The codebook themes concern financial behavior and experience, including
planning, spending, literacy, payment practices, perceived security, and
system-initiated interventions. This domain description follows the workbook's
labels; it should be checked against the approved research question and the
actual interview protocol.

## Analytical position

The primary evidence remains participants' Italian-language quotations and the
researcher's fixed manual codes. Tables and figures provide a transparent way
to inspect how those existing assignments are distributed across people and
questions. Such counts can be useful in qualitative reporting when they help
describe and audit a corpus, but they should remain tied to meaning and context
rather than being treated as inferential estimates. This follows
[Sandelowski's discussion of numbers in qualitative research](https://doi.org/10.1002/nur.1025):
counting may document patterns and check interpretations, while decontextualized
or misleading counting should be avoided.

The participant-by-theme table is a case-by-category comparison aid related to
the logic of the [Framework Method](https://doi.org/10.1186/1471-2288-13-117),
which uses a matrix to support comparisons within and across cases. This project
uses only a compact binary summary of an already coded excerpt set; it does not
claim to have carried out every stage of a formal Framework Method analysis.
Likewise, [Braun and Clarke's account of thematic analysis](https://doi.org/10.1191/1478088706qp063oa)
supports the distinction between interpreting patterns of meaning and merely
counting labels. Since the themes are already fixed in the workbook, the present
scripts do not reproduce the interpretive decisions that produced them.

## Data and handling

### Source and unit of analysis

The Excel workbook has three sheets:

| Sheet | Role in this workflow |
| --- | --- |
| `Codebook` | Source records: participant identifier, question identifier, Italian quote, descriptive code, and manual theme. |
| `Theme Matrix` | Researcher-prepared participant-by-theme presence matrix used as a validation target. |
| `Overview` | Researcher-prepared participant, excerpt, theme, and theme-prevalence totals used as validation targets. |

The unit in the supplied `Codebook` sheet is one coded excerpt row. A
participant-level theme presence is a separate unit used for prevalence: a
participant contributes at most one presence to a particular theme, even if
multiple excerpts were ever assigned that theme. In this workbook, the excerpt
and participant-prevalence totals happen to agree theme by theme; the scripts
still compute those quantities independently.

### Parsing and validation

`scripts/01_load_and_validate.py` reads the three sheets without editing the
source workbook. It checks that the required codebook columns exist, drops only
rows without a participant ID or a theme, and preserves the remaining `code`,
`theme`, question, and quote values. Participant labels such as
`P03_GiuliaR_24` are parsed into a short ID (`P03`), name (`GiuliaR`), and age
(`24`). The full identifier remains available alongside those fields so rows
can be traced back to the codebook.

The script recomputes the binary theme matrix from the fixed `theme` values and
compares it cell by cell to `Theme Matrix`. It also recomputes participant,
excerpt, and theme totals and the number of participants represented by each
theme, then compares them with `Overview`. Mismatches are returned as data
frames so they can be displayed and reviewed. Assertions check logical
invariants, including binary matrix values. The source coding is never
overwritten by these checks.

The normalized records are exported as UTF-8 CSV files to
`data/processed/codes.csv` and `data/processed/participants.csv`. Parsed and
validated DataFrames are also checkpointed as pickle files under
`data/checkpoints/`, so later stages can be inspected or rerun without reparsing
the workbook. The same processed tables and validation matrix are written to a
local SQLite database at `data/processed/analysis.sqlite` for zero-service,
read-only inspection. The workbook is the raw boundary; there is no remote API
fetch in this project to repeat. Italian quotation text is retained as Unicode
and CSVs use a UTF-8 BOM to improve spreadsheet compatibility. No translation,
English stop-word filtering, or quote normalization is performed before the
descriptive analyses.

### Validation result for the supplied workbook

The executed notebook reports that the manually prepared participant-by-theme
matrix matches the recomputed matrix. The workbook overview also matches the
recomputed totals: 10 participants, 27 coded excerpts, and 9 themes. All nine
theme-prevalence comparisons match. These checks establish consistency between
the workbook's own summaries and its codebook records; they do not verify that
the original human coding is conceptually complete or correct.

## Descriptive analyses

### Participant-by-theme matrix and heatmap

The binary matrix is calculated as a crosstab of `theme` by `participant_id`,
then converted to presence/absence. A cell is `1` when that participant has at
least one excerpt under the theme and `0` otherwise. This makes the question
“which participants expressed each coded theme?” directly inspectable without
letting participants with more excerpts dominate the display.

The heatmap uses a two-state color scale and annotates each cell. A row total
can be reported as “x/10 participants” for this dataset. Prevalence is
descriptive of these participants; it is not a population estimate, measure of
theme importance, or evidence that less common experiences are unimportant.
The matrix CSV and 300 dpi PNG are written to `outputs/tables/` and
`outputs/figures/` respectively.

### Comparison by question

The question comparison uses a `question_id`-by-`theme` crosstab. For each
question/theme pair it reports both the number of coded excerpts and the set and
count of unique participants represented. The distinction matters: excerpt
frequency reflects the number of coded rows, whereas participant count answers
how many different people contributed a coded excerpt in that question/theme
cell. A small-multiples bar chart presents excerpt counts separately for each
question; the companion table names the associated participants.

This comparison is useful for checking convergence and divergence among
participants who received the same question. It is not an inter-rater
agreement statistic: all records already carry the researcher's manual coding,
and the table does not compare independent coders. The summary CSV and 300 dpi
PNG are saved under `outputs/tables/` and `outputs/figures/`.

### Participant-level theme co-occurrence

For each participant, the script first forms the set of distinct themes found
across all of their coded excerpts. For each theme pair it increments a
co-occurrence count once if both themes occur in that participant's set. The
result is a symmetric theme-by-theme matrix. Its diagonal equals the number of
participants represented by each theme. The graph uses theme nodes sized by
prevalence and edges weighted by the number of participants in whom the pair
co-occurs; edge width encodes that weight.

This construction follows the general use of matrices and projections for
two-mode data (cases by attributes), as discussed by
[Borgatti and Everett](https://doi.org/10.1016/S0378-8733(96)00301-2). Here it
is deliberately descriptive. “Co-occurrence” means that the same participant
has excerpts coded with both themes somewhere in their interview. The excerpts
may answer different questions and need not occur in the same sentence, answer,
or moment. An edge therefore does not establish a semantic link, causal
relationship, participant preference, or design dependency. Edge weights are
counts out of 10 participants, not statistical tests.

The fixed-seed spring layout makes the static network layout reproducible for
the installed graph-library version. A 300 dpi PNG and co-occurrence CSV are
saved for the thesis; a separate PyVis HTML file supports exploration. Visual
proximity in a force-directed graph is a layout effect, not an additional
measured relationship.

## Exploratory embedding and clustering cross-check

The final analysis encodes each Italian quote with
`sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`. Sentence
embeddings represent text as vectors intended to preserve aspects of sentence
meaning; the Sentence-BERT work motivates using sentence-level vectors for
similarity tasks, and the
[multilingual model card](https://huggingface.co/sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2)
documents the selected model's multilingual use. Multilinguality makes the
choice more suitable for Italian than an English-only model, but does not
guarantee that every idiom, cultural reference, or financial term is represented
as a participant intended it to be.

The script reduces the quote vectors to two dimensions with UMAP using cosine
distance, `n_neighbors=5` for this 27-row data set, `min_dist=0.15`, and a fixed
random seed of 17. UMAP is a nonlinear manifold-learning method designed to
construct low-dimensional representations ([McInnes et al., 2018](https://doi.org/10.21105/joss.00861)).
HDBSCAN is then run on those two-dimensional coordinates with
`min_cluster_size=2` and `min_samples=1`. HDBSCAN extracts density-based groups
across a hierarchy and can label points as noise ([Campello et al., 2013](https://doi.org/10.1007/978-3-642-37456-2_14);
[McInnes et al., 2017](https://doi.org/10.21105/joss.00205)). The small minimum
cluster size is a pragmatic exploratory setting for only 27 excerpts, not a
claim that two items define a substantively stable theme.

The cluster-by-manual-theme crosstab and interactive Plotly scatter are
cross-checks only. In the supplied run, HDBSCAN returned seven clusters; the
crosstab shows several clusters containing excerpts assigned to different
manual themes and some manual themes represented in more than one cluster.
This is an illustration of algorithmic grouping under one model and one set of
parameters, not a test of the manual codebook. The pipeline does not tune
parameters to maximize agreement, estimate uncertainty, compare multiple
models, or measure clustering quality against independent human judgments.
Moreover, clustering is applied after projecting the embeddings to two
dimensions, so projection distortions can affect the discovered groups. A
different model revision, projection, seed, or HDBSCAN setting may produce a
different result. The model identifier and Python dependencies are recorded,
but the remote model artifact itself is not pinned by a commit hash.

No p-values, confidence intervals, significance tests, or claims of
generalizability are produced. The quotes and manual labels remain the basis for
interpretation; a cluster is only a prompt to revisit those excerpts if useful.

## Results for the current codebook

### Theme prevalence

| Manual theme | Participants with theme |
| --- | ---: |
| Propensity for deferred payments (BNPL/installments) | 6/10 |
| Expense tracking | 6/10 |
| Emotional relationship with money | 4/10 |
| Approach to spending planning | 2/10 |
| Decision-making autonomy | 2/10 |
| Perceived financial literacy | 2/10 |
| System-driven initiative | 2/10 |
| Trust and security | 2/10 |
| Future financial planning | 1/10 |

Descriptively, the two themes present in the largest number of participants are
deferred payment practices and expense tracking (6/10 each). Future financial
planning is present in 1/10. Emotional relationship with money is present in
4/10, while the other themes are each present in 2/10. These counts summarize
this interview corpus only.

### Distribution across questions

The workbook contains eight question identifiers. In the current codebook,
each question maps to one or two manual themes: `Q_Autonomy` includes
Decision-making autonomy (2 participants) and Future financial planning (1);
`Q_Emotion` includes Emotional relationship with money (4); `Q_Installments`
includes deferred payments (6); `Q_Literacy` includes perceived financial
literacy (2); `Q_Planning` includes spending planning (2); `Q_Security` includes
Trust and security (2); `Q_System` includes system-driven initiative (2); and
`Q_Tracking` includes expense tracking (6). These are coded excerpt and
participant counts, not evidence that the question caused a response or that
participants agree on the meaning of a theme.

### Network and algorithmic cross-check

In the participant-level co-occurrence matrix, the largest off-diagonal edge is
Expense tracking with deferred payment practices (4/10 participants). Other
visible ties include Decision-making autonomy with Expense tracking (2/10),
Emotional relationship with money with Expense tracking (2/10), and spending
planning with deferred payment practices (2/10). The edge definition is
participant-level co-presence across excerpts, as specified above. The
embedding/clustering crosstab produced seven algorithmic clusters for this run
and should be read as a sensitivity-prone comparison with manual labels, not as
a new set of research results.

## From qualitative results to engineering/design decisions

The analysis can support a design rationale by making traceability explicit:

1. **Evidence:** cite the original Italian excerpt and participant/question
   identifier.
2. **Research interpretation:** explain why the manually assigned code and
   theme answer the research question; distinguish interpretation from the
   participant's literal statement.
3. **User need or design opportunity:** formulate a need without converting a
   frequency count directly into a universal requirement.
4. **Design requirement:** state a testable behavior, constraint, or quality
   attribute and link it back to the evidence and interpretation.
5. **Verification:** define a prototype task, usability measure, or engineering
   acceptance test that checks the requirement with relevant users.

For example, an `Expense tracking` prevalence of 6/10 is not by itself a
requirement to build a particular budgeting feature. The thesis should inspect
the supporting quotes, explain the particular difficulty or strategy they
describe, propose the relevant design response, and validate that response in
a subsequent design evaluation. The same chain applies to system-initiated
alerts, deferred-payment support, and other themes. The current workbook does
not document prototype tests or design evaluations, so this analysis alone
cannot establish usability, effectiveness, feasibility, or adoption.

For an engineering thesis, the static matrix and network provide inspectable
artifacts, while the scripts provide the transformation logic and the notebook
provides an executable results narrative. The validation assertions protect
against accidental drift between the source codebook and its manual summaries;
unit tests exercise the crosstab and co-occurrence rules on a small known data
set. Together these support reproducibility and auditability, not a claim that
software can replace qualitative interpretation.

## Reproducibility and limitations

Python 3.12 and exact dependency pins are maintained through `pyproject.toml`
and `uv.lock`. The notebook runs top to bottom with `uv run jupyter nbconvert
--to notebook --execute --inplace notebooks/results.ipynb`. Static figures use
fixed data and graph/UMAP seeds. The multilingual model is downloaded on first
use and cached locally; internet access is needed unless the model is already
cached. The scripts preserve excerpts in UTF-8 and do not use English-only
stop-word lists.

Interpretation remains bounded by the supplied materials: ten participants,
27 coded excerpts, nine pre-existing themes, and no transcript-level context in
this workbook. The sample and excerpts cannot support statistical
generalization. The codebook alone does not establish recruitment, saturation,
researcher positionality, consent, or coding reliability. Those elements
require primary study documentation and should be reported by the thesis
author, not inferred by this software pipeline.

## Method references

- Braun, V., & Clarke, V. (2006). Using thematic analysis in psychology.
  *Qualitative Research in Psychology, 3*(2), 77–101.
  [https://doi.org/10.1191/1478088706qp063oa](https://doi.org/10.1191/1478088706qp063oa)
- Borgatti, S. P., & Everett, M. G. (1997). Network analysis of 2-mode data.
  *Social Networks, 19*(3), 243–269.
  [https://doi.org/10.1016/S0378-8733(96)00301-2](https://doi.org/10.1016/S0378-8733(96)00301-2)
- Campello, R. J. G. B., Moulavi, D., & Sander, J. (2013). Density-based
  clustering based on hierarchical density estimates. In *Advances in
  Knowledge Discovery and Data Mining* (pp. 160–172).
  [https://doi.org/10.1007/978-3-642-37456-2_14](https://doi.org/10.1007/978-3-642-37456-2_14)
- Gale, N. K., Heath, G., Cameron, E., Rashid, S., & Redwood, S. (2013). Using
  the framework method for the analysis of qualitative data in
  multi-disciplinary health research. *BMC Medical Research Methodology, 13*,
  117. [https://doi.org/10.1186/1471-2288-13-117](https://doi.org/10.1186/1471-2288-13-117)
- McInnes, L., Healy, J., & Astels, S. (2017). hdbscan: Hierarchical density
  based clustering. *Journal of Open Source Software, 2*(11), 205.
  [https://doi.org/10.21105/joss.00205](https://doi.org/10.21105/joss.00205)
- McInnes, L., Healy, J., & Melville, J. (2018). UMAP: Uniform manifold
  approximation and projection for dimension reduction. *arXiv:1802.03426*.
  [https://doi.org/10.48550/arXiv.1802.03426](https://doi.org/10.48550/arXiv.1802.03426)
- Reimers, N., & Gurevych, I. (2019). Sentence-BERT: Sentence embeddings using
  Siamese BERT-networks. In *Proceedings of EMNLP-IJCNLP 2019*.
  [https://doi.org/10.48550/arXiv.1908.10084](https://doi.org/10.48550/arXiv.1908.10084)
- Reimers, N., & Gurevych, I. (2020). Making monolingual sentence embeddings
  multilingual using knowledge distillation. In *Proceedings of EMNLP 2020*.
  [https://doi.org/10.48550/arXiv.2004.09813](https://doi.org/10.48550/arXiv.2004.09813)
- Sandelowski, M. (2001). Real qualitative researchers do not count: The use
  of numbers in qualitative research. *Research in Nursing & Health, 24*(3),
  230–240. [https://doi.org/10.1002/nur.1025](https://doi.org/10.1002/nur.1025)
- Tong, A., Sainsbury, P., & Craig, J. (2007). Consolidated criteria for
  reporting qualitative research (COREQ): A 32-item checklist for interviews
  and focus groups. *International Journal for Quality in Health Care, 19*(6),
  
  349–357. [https://doi.org/10.1093/intqhc/mzm042](https://doi.org/10.1093/intqhc/mzm042)
