# Transcript exploration workflow

## Inputs and alignment boundaries

The raw inputs are stored in `data/raw/`. `interviste_trascrizioni.xlsx` has
participant IDs, sequential row numbers, and transcript text. Speaker labels are
recognized where present (`Intervistatrice` and `P01`-style IDs); unlabelled
rows inherit the preceding speaker only within that participant's transcript.
Unrecognized colon-prefixed rows form an `unknown` boundary and are not
silently assigned to a speaker. A transcript turn is a run of adjacent rows
with the same recognized speaker role, with its original row range retained.

`domande_comuni.xlsx` contains 41 base questions in five sections. Its own
description says questions recur but are not necessarily asked of everyone and
that equivalent formulations have been unified. The workflow preserves base
wording and ranks semantic candidates for interviewer turns. It deliberately
leaves `reviewed_question_id` blank: a human must confirm, adapt, or reject each
match. The resulting question counts must not be interpreted as prompt
exposure counts until reviewed.

The manually coded workbook has a different set of nine legacy question IDs.
No crosswalk between those IDs and guide questions is assumed. Quote-to-
transcript alignment provides transcript row candidates for manual excerpts;
exact normalized matches are distinct from lexical nearest candidates. A
candidate-only alignment is never treated as verified.

## Local analyses

`scripts/08_transcript_workflow.py` and
`notebooks/transcript_exploration.ipynb` produce review tables:

1. **Quote alignment:** normalize case, accents, punctuation, and spacing to
   identify exact quote spans. For unmatched quotes, rank short transcript row
   windows by character n-gram similarity. The score is only a navigation aid;
   edited or paraphrased quotes still need source review.
2. **Question-turn candidates:** encode interviewer turns and the 41 base
   prompts with `paraphrase-multilingual-MiniLM-L12-v2`; list the three closest
   prompt candidates and scores. A weak lexical question cue helps prioritize
   review but does not determine whether a turn is a prompt. No threshold or
   top match automatically assigns a question because interviewer wording can
   be adapted and a turn can contain probes or multiple prompts.
3. **Theme passage retrieval:** average embeddings of existing coded excerpts
   by manual theme, then retrieve participant turns from every interview near
   those examples. Exact-aligned source passages are excluded where possible.
   Retrieval is a way to find potentially relevant, additional, or disconfirming
   material; it does not validate the theme label.
4. **Affinity suggestions:** produce participant evidence cards and top three
   cross-participant semantic-neighbor links. An analyst writes the affinity
   group, summary, and counterexample/tension after reviewing the full passage
   and context. Similarity links are candidate navigation edges, not claims
   that participants share a meaning.
5. **Optional sentiment and emotion cues:** `run_feelit_cues` can classify
   participant turns with FEEL-IT sentiment and emotion checkpoints. It is off
   by default. Models are based on Italian social-media posts, so outputs may
   fail on conversational interviews, negation, irony, mixed affect, or
   target-specific emotion. Use predictions only to locate passages for human
   annotation. Do not report them as measured participant sentiment or mental
   state.

The multilingual embedding model is already used elsewhere in this project and
is loaded from the local Hugging Face cache by default. For a fresh setup, the
notebook's `ALLOW_MODEL_DOWNLOAD` switch must be explicitly enabled once to get
the model weights. In the current source snapshot, 36 of 76 codebook quotes
have exact normalized matches; the other 40 receive lexical candidates only.
The FEEL-IT checkpoints are optional and are not bundled. To permit their
download, explicitly call `run_feelit_cues(turns, allow_model_download=True)`
after reviewing whether the study's data-handling terms allow the software to
contact the model repository. The transcript itself is processed locally;
model downloads send no transcript content.

## Review protocol

For each candidate row, record a decision and reason in the corresponding
`*_review.csv` file; these review boards carry decisions forward when candidate
tables are regenerated.
For affinity groups, retain at least one counterexample or tension where
present. Review high-similarity and low-similarity examples, not only the
nearest matches. Compare retrieval against manual coding without treating
agreement as proof of correctness. Record any codebook changes in study notes
with the analyst, date, rationale, and affected excerpt/turn references.

Generated tables under `outputs/transcript_review/` contain full transcript
passages and are ignored by Git. Candidate tables are regenerated; separate
`*_review.csv` files retain human decisions by stable IDs across reruns. Do not
share them until consent, anonymization, and disclosure requirements have been
checked. Notebook outputs are cleared before versioning to avoid storing
transcript text in the `.ipynb` file.

## Reporting boundary

The current codebook represents 76 selected excerpt rows; the transcript
workbook contains longer interview material. This workflow can surface text not
included in the existing codebook, but it cannot establish why excerpts were
originally selected or whether omitted context changes an interpretation.
Report the human review method, prompt adaptations, excerpt selection, and
researcher decisions alongside any transcript-derived finding. The output
tables are an audit trail and exploration aid, not an automated qualitative
analysis.

The sentence-transformer model documents Italian as a supported language in
its multilingual model family ([model information](https://github.com/sentence-transformers/sentence-transformers/blob/main/docs/sentence_transformer/pretrained_models.md)).
FEEL-IT describes its underlying benchmark as Italian Twitter posts annotated
for anger, fear, joy, and sadness ([paper](https://aclanthology.org/2021.wassa-1.8/));
the domain difference is why its labels are treated as tentative cues here.
## Visual outputs

`scripts/09_visual_review.py` creates JPEG figures in
`outputs/figures/transcript_review/`, and the transcript notebook displays them
inline. The figures include a participant-by-theme matrix, quote-match status,
question-guide section candidates, theme retrieval score distributions, and a semantic
affinity-neighbor map. The map shows at most 250 candidate links with similarity
at least 0.55 so the figure remains readable; all candidate links remain in
`affinity_edge_review.csv`. Edges and proximity are navigation aids, not
evidence that excerpts share a meaning. Treat counts as corpus descriptors.
