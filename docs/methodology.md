# Methodology and analysis boundaries

## Scope and source

This repository performs a secondary, case-oriented analysis of the manually
coded excerpts in `data/raw/final_codebook_updated_visual.xlsx`, alongside
transcripts in `data/raw/interviste_trascrizioni.xlsx` and a common-question
guide in `data/raw/domande_comuni.xlsx`. Each `Codebook` row is one coded
excerpt and contains a participant label, legacy question ID, Italian quote,
code, and theme. The pipeline preserves those manual assignments. It does not
independently conduct thematic analysis or validate the original coding.

At the current workbook version there are 76 excerpt rows, 10 short participant
IDs, 9 question IDs, and 5 assigned themes. These are counts of the supplied
codebook, not a statement about recruitment, the full interview corpus, or the
population. The pipeline strips participant descriptors from derived files and
uses only IDs such as `P01`. The source workbook remains unchanged.

The codebook workbook currently contains `Codebook` and `Question order` sheets.
The latter lists nine legacy IDs; it does not contain prompt text. The separate
common-question workbook lists 41 recurring base prompts and explicitly notes
that the questions were not necessarily asked of everyone and may have been
rephrased. The transcript workbook has sequential rows with interviewer and
participant speaker markers, but no question IDs. Consequently, guide-to-turn
matches produced by NLP are candidates for human review, not authoritative
assignments. The legacy codebook IDs have not been assumed to map to the
41-question guide. There are no source `Theme Matrix` or `Overview` sheets in
the codebook workbook, so older summaries are not validation targets.

## Study information that must come from primary records

The workbook does not provide enough information to establish the study's
research question, recruitment or inclusion criteria, interview setting,
verbatim interview-guide prompts, transcription process, excerpt-selection
rules, or whether the workbook includes all relevant transcript material. It
also does not document researcher positionality, codebook development, coder
roles or number, coding revisions, or how disagreements were resolved. These
facts must be added from study records before this section is presented as the
complete study methodology. No values are inferred from question IDs or code
labels.

Before treating this as a complete account, fill these items from the primary
study records:

| Required study detail | Status in supplied workbook | Information to add |
| --- | --- | --- |
| Research question and study aim | Not stated | Approved research question and how these interviews address it |
| Sample and recruitment | Not stated | Recruitment route, inclusion criteria, setting, and participant description at an appropriate disclosure level |
| Interview guide | IDs only | Exact prompt wording, order, probes, and any guide revisions |
| Transcript and excerpt selection | Not stated | Whether excerpts are exhaustive or selected, who selected them, selection rules, and omitted context |
| Coding process | Existing labels only | Codebook origin, coder identities/roles, independent or collaborative process, revision history, and disagreement resolution |
| Reflexivity and ethics | Not stated | Researcher relationship/position, consent, anonymization, and quote-use constraints |

The guide structure visible in this file is limited to nine IDs:
`Q_Autonomy`, `Q_Emotion`, `Q_Future`, `Q_Installments`, `Q_Literacy`,
`Q_Planning`, `Q_Security`, `Q_System`, and `Q_Tracking`. Prompt text is not in
the codebook. The coverage table reports participants with at least one coded
excerpt under each ID; this is not proof that every participant was asked the
prompt or that a missing coded row means no response.

## Units and descriptive summaries

The excerpt is the source-record unit. Participant summaries use the unique
short participant ID and count each person once per theme, even if that person
has multiple excerpts under the theme. Every count is a corpus descriptor. For
example, “x of 10 participants had at least one coded excerpt assigned to this
theme” describes the coded material only. It does not measure importance,
agreement, depth, saturation, or population prevalence.

The case-by-theme evidence matrix stores excerpt IDs and question IDs in each
participant/theme cell. The excerpt evidence register maps those IDs to the
short participant ID, question ID, original quote, manual code, and manual
theme. Theme descriptor tables report participant count, participant
denominator, excerpt rows, and number of question IDs. They do not automatically
generate interpretive claims.

Question summaries show both distinct participants and coded excerpt rows for
each question/theme pair. Comparisons are interpreted within the structure of
the interview guide: prompts shape what can be said and coded. For each
question, report the number of participants represented by any coded excerpt
for that ID as the observed denominator, and state that actual prompt exposure
is unknown unless confirmed from the interview records. Cross-question
recurrence is a cue to inspect the excerpts and their context, not evidence of
independent salience or a causal prompt effect.

Participant-level co-occurrence can be used to locate cases for review only.
Two themes occurring somewhere in one person's coded excerpts does not show
that they occurred in the same answer or were experienced as related. The
network is therefore excluded from substantive findings. Embedding, UMAP, and
clustering are also excluded from findings: with a small set of short quotes,
their assignments are sensitive to modeling choices and do not validate manual
themes.

## Interpretation and evidence

For each theme, the analyst should define the theme from the codebook and
study's analytic framework, compare cases, inspect variation and exceptions,
and support each interpretation with short Italian quotations and short
participant IDs. The included evidence register is an audit aid; quotes shown
in a report should be checked against surrounding transcript context and
consent/disclosure requirements. A quote is illustrative evidence, not by
itself a general claim about a theme.

The repository can prepare traceable evidence and corpus descriptors. It cannot
recover missing conversational context, explain how original codes were
produced, determine why a participant did not contribute a coded excerpt, or
substitute for the researcher's interpretive account. The current findings
document therefore labels interpretation and design implications as review
drafts until confirmed by the analyst.

The transcript exploration workflow is described in
[`transcript_workflow.md`](transcript_workflow.md). It performs quote alignment,
question-turn candidate ranking, semantic passage retrieval, and
cross-participant affinity suggestions. It does not treat similarity, sentiment
or emotion predictions, or candidate groupings as qualitative findings.

## Design implications

Any design rationale should retain this chain:

1. **Excerpt:** short quotation, participant ID, question ID, and excerpt ID.
2. **Interpretation:** what the passage suggests in context, including a
   plausible alternative reading or counterexample.
3. **User need:** a bounded need grounded in the interpretation, not simply a
   theme count.
4. **Design opportunity:** a candidate intervention or quality requirement.
5. **Separate validation:** a prototype or field evaluation with relevant
   users. The codebook analysis cannot establish usability, effectiveness,
   feasibility, adoption, or safety of a proposed design.

## Reproducibility

The notebook `notebooks/results.ipynb` loads the source workbook, rebuilds the
case/evidence tables and descriptive figures, and displays the current workbook
summary. `scripts/01_load_and_validate.py` checks source workbook summaries
when those sheets exist. A check confirms agreement between workbook summaries
and codebook rows; it does not establish coding validity. Derived files may
contain quotations and must be handled under the study's consent and disclosure
conditions.
