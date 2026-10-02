# Findings and design implications: review draft

This draft is generated from the current codebook structure and should be
reviewed against full interview context before thesis use. Theme names and
codes are inherited from the workbook. The short quotations are illustrative
excerpts, not a complete account of each participant. Each should be checked
against transcript context and disclosure/consent requirements.

## Corpus descriptors

The workbook contains 76 coded excerpt rows, 10 participants (P01–P10), 9
question IDs, and 5 manual themes. A theme count below means “participants
with at least one excerpt assigned this theme / 10 participants represented in
the codebook.” These counts describe only the coded material; they are not
measures of importance, agreement, depth, saturation, or population frequency.
For question-specific summaries, the observable denominator is the number of
participants with any coded excerpt under that question ID. It is not known
from this workbook whether every person received the prompt. See the generated
question coverage table for the denominator and excerpt rows.

## Theme accounts and evidence

### Dinamiche di delega e ricerca autonoma

**Working meaning:** the assigned codes bring together ways of seeking
financial guidance, from family and peers to independent online research,
professionals, and AI tools. The label spans both delegation and self-directed
search, so those should be examined as distinct strategies in interpretation.

**Corpus descriptor:** 10 of 10 participants; 13 excerpt rows across 3 question
IDs. This reflects codebook assignment and is not a claim that all participants
share the same approach.

**Variation to inspect:** codes range from family/professional delegation and
fear of making errors to independent research and proactive literacy. Compare
who combines sources, who delegates, and who expresses distrust or a need for
formal education; do not flatten these into one preference.

Illustrative excerpts:

- P01, Q_Autonomy, E001: “Passaparola da altri, famiglia, amici…”
- P02, Q_Autonomy, E002: “O facendo ricerca da sola, utilizzando Claude…”

**Interpretive check:** read the full responses and the exact prompts for
Q_Autonomy, Q_Literacy, and Q_Security. Confirm whether these are accounts of
actual behavior, hypothetical sources, or both.

### Impatto psicologico della gestione finanziaria

**Working meaning:** codes describe emotional reactions and orientations
associated with financial management, including anxiety, confidence,
dissatisfaction, vigilance, motivation, and mixed feelings. The broad theme
contains positive, negative, and ambivalent experiences.

**Corpus descriptor:** 10 of 10 participants; 13 excerpt rows across 3 question
IDs. The count does not imply a uniform or equally intense emotional impact.

**Variation to inspect:** anxiety can relate to numeric displays, overspending,
fraud, or notifications; other codes indicate control-related calm, confidence,
or pride mixed with stress. Examine triggers and conditions, not just emotional
valence.

Illustrative excerpts:

- P02, Q_Emotion, E012: “vedere un numero e basta mi fa un po’ d’ansia.”
- P01, Q_Emotion, E011: “Delle volte ansia… anche proprio il terrore truffa.”

**Interpretive check:** distinguish reactions to money management from reactions
to a particular interface, fraud experience, or interviewer prompt. The
Q_Future and Q_Security assignments need context before claiming recurrence
across settings.

### Gap tra competenze attuali e complessità futura

**Working meaning:** assigned codes connect perceived capability or knowledge
with anticipated future financial demands, including investment, taxes,
bureaucracy, housing, income, and long-term costs.

**Corpus descriptor:** 10 of 10 participants; 16 excerpt rows across 2 question
IDs. The question coverage is concentrated in Q_Future and Q_Literacy, so
cross-question recurrence is limited and prompt-shaped.

**Variation to inspect:** some codes indicate confidence or academic mastery;
others describe gaps in investment or tax knowledge and uncertainty. Compare
reported current competence with future expectations rather than treating the
theme as a single literacy deficit.

Illustrative excerpts:

- P02, Q_Future, E022: “in cosa investire… devi trovare un modo di non perdere il valore del denaro.”
- P01, Q_Future, E021: “in cinque anni, immagino che le spese siano molto diverse.”

**Interpretive check:** establish whether future concerns came from a direct
prompt and whether the respondent discussed an actual plan, a worry, or a
hypothetical scenario.

### Tattiche di autocontrollo e gestione della liquidità

**Working meaning:** the assigned codes cover budgeting, tracking, saving,
payment timing, debt/installment choices, and mental strategies for preserving
liquidity. These practices include both explicit systems and less formal rules.

**Corpus descriptor:** 10 of 10 participants; 28 excerpt rows across 3 question
IDs. This is the largest theme by excerpt rows in this codebook, not evidence
that it is the most important theme. Repeated rows can reflect coding density.

**Variation to inspect:** codes include structured and reactive budgeting,
manual and app-based tracking, automated saving, debt aversion, strategic
installment use, and no explicit planning. Compare practices and circumstances;
avoid assuming that an installment choice reflects either poor control or
financial distress.

Illustrative excerpts:

- P01, Q_Installments, E030: “cerco di avere un buon bilanciamento economico…”
- P02, Q_Installments, E031: “utilizzo molto spesso il servizio di PayPal…”

**Interpretive check:** inspect Q_Installments, Q_Planning, and Q_Tracking
separately. The theme’s breadth may warrant splitting or refining it in the
researcher’s conceptual analysis; this repository does not recode it.

### Attrito e limiti degli strumenti digitali

**Working meaning:** the codes concern friction or limitations in digital
financial tools, including manual tracking effort, privacy concerns, alerts,
and requests for more contextual system feedback.

**Corpus descriptor:** 5 of 10 participants; 6 excerpt rows across 3 question
IDs. The smaller count is a corpus description, not evidence that the issue is
unimportant.

**Variation to inspect:** the assigned material spans observed friction,
privacy concerns, and desired system features. Separate problems participants
currently experience from speculative feature requests.

Illustrative excerpts:

- P02, Q_System, E064: “non vedo per forza solo il numero… ma magari dei rapporti”
- P10, Q_Security, E063: “privacy che riguardo le entrate è un’altra cosa”

**Interpretive check:** only a few participants have excerpts assigned to this
theme, and they occur under different question IDs. Inspect the full responses
before describing these as one common product need.

## Prompt-level reading

The codebook distributes themes unevenly across prompts. Q_Autonomy has 10
participants represented; Q_Emotion 10; Q_Future 9 total coded participants,
with the theme-specific rows representing 8 under the future-gap theme and 1
under the psychological-impact theme; Q_Installments 10; Q_Literacy 10;
Q_Planning 10; Q_Security 4; Q_System 3; and Q_Tracking 10. Prompt text is
absent. The reported counts therefore describe coded response coverage only.
Review participant excerpts within each question before making claims about
differences between prompts. A theme appearing under multiple IDs may reflect
overlapping coding or interviewer framing.

## Design implications: hypotheses for later evaluation

These are candidate directions to investigate, not requirements established by
the counts. Each needs confirmation through contextual transcript review and
separate user research/prototype evaluation.

| Evidence | Interpretation to verify | Bounded user need hypothesis | Design opportunity to evaluate |
| --- | --- | --- | --- |
| P02, Q_Emotion, E012: a number-only view causes some anxiety | Numeric totals may lack context for this participant | Understand what a balance or spending total means without added worry | Test optional breakdowns, trend context, and user-controlled detail; measure comprehension and anxiety |
| P02, Q_System, E064: asks for ratios/progress rather than only a number | This participant wants comparison to a plan or target | See current spending in relation to a self-chosen plan | Prototype a simple progress view with adjustable limits; test whether it supports decisions without shame or overload |
| P10, Q_Security, E063: raises privacy concerns about income-related data | Perceived data use may affect trust | Understand and control how sensitive financial information is used | Test clear data-use explanations and granular controls; evaluate comprehension and trust |
| P01 and P02, Q_Installments, E030–E031: avoid installments vs use fee-free installments | Choices vary by perceived cost and liquidity strategy | Compare total obligation and timing before committing | Test an installment comparison/obligation summary with users; assess understanding, not adoption alone |

Do not generalize these hypotheses to all users from this corpus. Any design
claim requires evaluation with relevant users and an explicit method, sample,
and outcome measure.

## Conclusion

The codebook records varied strategies for seeking guidance, managing money,
responding emotionally to financial information, and using or wanting digital
support. Participant counts range from 5 to 10 of the 10 represented IDs, but
these distributions are properties of the coded excerpt set and are shaped by
the interview prompts and the original coding process. They do not rank user
needs or establish broader prevalence. The most defensible use of these
materials is to guide close case comparison and formulate design hypotheses
that can be tested separately. The original study method and full transcript
context remain necessary to finalize the interpretations.
