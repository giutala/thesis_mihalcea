# BNPL on Italian TikTok

This repository collects and analyses public TikTok content about Buy Now, Pay
Later (BNPL) from accounts registered in Italy, through the TikTok Research
API. It supports a thesis on how young adults in Italy keep track of BNPL
commitments. The corpus feeds the market, benchmark, and regulatory analysis.

It is not a sample of the thesis population (20-27 year olds): the API reports
no age, and `region_code` is only the country of the creator's account. All
labels come from transparent text rules, with no manual coding. Read the
results together with [Validity and bias](#validity-and-bias). The full
method, pilot, and limitations are in `docs/tiktok_methodology.md`.

## Folder layout

```text
data/
  raw/tiktok/             Raw API records, pilot, query config, log (ignored)
  processed/tiktok/       Labelled video and comment corpora (ignored)
docs/                     Methodology
notebooks/
  tiktok_collection.ipynb Pilot, query, and resumable collection
  tiktok_analysis.ipynb   Tables, figures, and interpretation
outputs/
  tiktok/                 Aggregate tables and findings_summary.md
  figures/tiktok/         Aggregate figures (300 dpi PNG)
scripts/                  Client, rules, collection, and analysis modules
tests/                    Behaviour checks on synthetic data
```

| Module | Role |
|---|---|
| `scripts/tiktok_terms.py` | Search terms and pilot decisions, period, CCD2 and Black Friday dates, BNPL, provider, post-type, creator-type, and theme rules |
| `scripts/tiktok_client.py` | Research API client: credential loading, token refresh, bounded retries, quota detection |
| `scripts/tiktok_collection.py` | Query builder, weekly windows, pilot, and resumable collection of videos, profiles, and comments |
| `scripts/tiktok_analysis.py` | Corpus building, labels, pseudonymization, tables, figures, and summary |

## Run it

Research API access must be approved first. Put the credentials in an ignored
`.env` file in the project root, or in the environment:

```text
TIKTOK_CLIENT_KEY=...
TIKTOK_CLIENT_SECRET=...
```

Install Python 3.12 and `uv`, then run:

```powershell
uv sync --all-groups
uv run jupyter nbconvert --to notebook --execute --inplace notebooks/tiktok_collection.ipynb
uv run jupyter nbconvert --to notebook --execute --inplace notebooks/tiktok_analysis.ipynb
```

Video search and profile lookups each allow about 1,000 requests a day. When a
quota runs out, the collection stops cleanly; rerun it the next day and it
resumes from the first pending window, profile, or comment thread. Rerunning
after 20 November 2026 adds the weeks after CCD2 applies.

## How the data is handled

1. **What is requested.** Only public videos from accounts registered in Italy
   that match the kept BNPL keywords or hashtags are requested, from January
   2024 onward. Each video has 13 fields: ID, handle, time, region,
   description, automatic transcript, hashtags, four engagement counts,
   duration, and the STEM flag. Public profiles are fetched for creators of
   non-ad posts and for the 300 most active creators. Comments are fetched for
   up to 800 of the most-commented videos, selected by post type (309 in the
   current run). Comments carry no author handle.
2. **How the terms were chosen.** A pilot queried each of 20 candidate terms
   alone over 30 days, at one request per term, and read 20 videos per term.
   Three terms were dropped as off-topic. The yields and decisions are in
   `docs/tiktok_methodology.md`.
3. **How it is collected.** Requests go through a small client instead of the
   `TikTokResearchApi` package. That package retried every error, including
   exhausted quota, 60 times without reporting it, and returned more records
   than `max_total`. The new client:
   - retries throttling, server errors, and dropped connections with growing
     delays;
   - stops at once on the daily-quota error or any invalid request;
   - counts every request.
4. **Where raw data lives.** Each 7-day window, profile, and comment thread is
   saved as JSON Lines in `data/raw/tiktok/` only once it is complete. The
   exact query and field list are frozen in `query_config.json`, and the
   collection refuses to resume with a different query. Every completed window
   and comment thread is logged in `collection_log.jsonl` with its `search_id`
   and fetch time. The folder is ignored by Git.
5. **How the corpus is built.** Duplicates are removed by video ID, keeping the
   latest engagement snapshot. A video is kept only if its description,
   hashtags, or transcript name a BNPL provider or a BNPL phrase. Each video
   is labelled with:
   - its BNPL signal (named provider or generic phrase);
   - the providers it names;
   - its post type (personal experience, financial commentary, shop ad, or
     other);
   - its creator type (for profiled creators);
   - nine theme cues;
   - its period (before or after CCD2 applies on 20 November 2026).

   Every filtering step is reported as a count in
   `outputs/tiktok/tables/corpus_funnel.csv`. Trend charts use fully collected
   months only.
6. **Pseudonymization.** Handles are replaced by salted SHA-256 creator IDs in
   the processed corpora and in every table and figure. The salt never leaves
   the raw folder.
7. **What is shared.** Only aggregate tables, figures, and the generated
   `findings_summary.md` are committed. The notebooks display aggregates only.
   The thesis paraphrases quotes and names no individual accounts. Raw data is
   deleted at the end of the thesis, subject to the TikTok Research API terms
   and university data policy.
8. **Credentials.** Credentials are read from the environment or the ignored
   `.env` file and are never written to notebooks or outputs.

## Main findings

From the run of 26 October 2026: 97,166 BNPL videos from 8,099 accounts,
covering January 2024 to August 2026, plus 18,078 comments on 309 videos and
997 creator profiles. The weeks from 14 September to 18 October 2026 and about
1,350 profiles are still to be collected. The tables, figures, and full
interpretation are in `notebooks/tiktok_analysis.ipynb`.

1. **BNPL reaches people on TikTok mainly as a merchant feature.** 91% of BNPL
   videos are shop ads: "paga in 3 rate con Klarna" next to a price and a
   WhatsApp number. Financial commentary is 159 videos (0.16%), and
   first-person posts are 37 (0.04%), about half of them creator product
   reviews. The 100 most active accounts produce 47% of all videos, and BNPL
   providers' own accounts are almost absent.
2. **Ads and critics tell opposite stories.** 31% of ads present BNPL as free
   and easy ("senza interessi", "0%"), and almost none mention fees, missed
   payments, or totals. In commentary, 33% discuss fees and failed payments,
   20% losing track of installments, and 11% regulation. Commentary reaches no
   more viewers than an ad: both have a median of about 1,050 views.
3. **Klarna dominates, and shops offer several providers side by side.**
   Klarna accounts for 66% of provider mentions and grew 6.6 times from the
   first quarter of 2024 to the second quarter of 2026; Scalapay grew 3.8
   times. 18% of videos that name a provider name two or more. This is the
   checkout-level counterpart of the fragmentation the thesis studies.
4. **Critical discussion is small but growing.** Commentary rose from 14 videos
   in 2024 to 60 in 2025 and 85 in January-September 2026. It peaked in August
   2026 around paying for groceries and holidays in installments, and posts
   explaining the new consumer credit rules appear from that month.
5. **TikTok does not show how users track their commitments.** Comments under
   ads are mostly purchase questions (24% ask about price, availability, or
   shipping). Theme words appear in under 5% of comments. Evidence for RQ1 and
   RQ2 therefore has to come from the interviews and artefact walk-throughs.
6. **Volume and timing.** BNPL content roughly quadrupled, from about 1,300
   videos a month in early 2024 to about 5,900 in July 2026, with a dip every
   August. There is no consistent Black Friday peak in posting. No data after
   CCD2 exists yet; the before-and-after comparison appears automatically
   after a rerun.

## Validity and bias

These results describe what was posted publicly on one platform. They are not
measurements of how young adults in Italy use BNPL. Read every number with the
following biases in mind.

**One platform, not the whole media environment.** TikTok is one app among
many: Instagram, YouTube, Facebook, Telegram, and the providers' own apps and
websites are not covered. TikTok has its own formats, such as short videos,
TikTok Shop, and affiliate content, and its own recommendation algorithm.
Results such as "91% of BNPL videos are shop ads" hold for TikTok and cannot
be generalized to social media as a whole.

**The link to young adults is an assumption, not a measurement.** The thesis
studies 20-27 year olds. The Research API returns no age for creators or
viewers. Using TikTok rests on a working hypothesis: TikTok's audience skews
young, with the 18-24 group commonly reported as its largest age group, so
BNPL content on TikTok approximates what young adults in Italy are exposed to.
Before relying on this hypothesis, the thesis should:

- cite a current audience source for Italy, such as DataReportal or
  Audiweb/AGCOM, with its date;
- state that the hypothesis concerns exposure, not use;
- keep in mind that creators are not viewers, so a shop's video can be posted
  by anyone and watched by anyone.

**Selection bias in what was collected.**
- `region_code` is the country where the creator's account is registered. It
  is not the viewer's country or the language, and Italian accounts post some
  content in other languages.
- API keyword search covers descriptions only, so videos that mention BNPL
  only in speech or on screen are missed unless a hashtag matches.
- The search terms were chosen in a pilot. Different terms would give a
  different corpus, and colloquial or misspelled mentions are under-covered.
- Only public videos still online at collection time are included. Deleted,
  private, and moderated videos are missing, which may remove the most
  critical or problematic content.
- TikTok does not document how complete Research API results are. Weekly
  counts swing by up to ±40% without an obvious cause, which points to
  variation in coverage.
- Comments were collected for the most-commented videos only, which favours
  popular videos. Profiles cover a selected subset of creators.

**Measurement error in the labels.** Post types, creator types, and themes are
keyword rules applied to short, informal text. They miss irony, negation,
slang, and anything shown only in the video. Reading samples showed that about
half of the "personal experience" posts are creator product reviews. The rules
were checked by reading samples, not formally validated: there is no
precision, recall, or inter-rater agreement estimate. If the thesis relies on
a label-based share, a validation check would make it defensible. This means
hand-labelling a random sample, about 100 videos per post type, and reporting
the agreement with the rules.

**What the statistics can and cannot support.**
- The corpus is everything the API returned for the query, not a random
  sample of a defined population. Confidence intervals and significance tests
  about "Italian TikTok" or "young Italians" would therefore not be
  meaningful. The figures are descriptive.
- Rare categories rest on small numbers: 159 commentary videos, 37
  first-person posts, and 26 discourse posts in the August 2026 peak.
  Percentages for them move a lot when a few videos are added. Report counts
  with their denominators, and avoid strong claims about month-to-month
  changes.
- Content is concentrated: 100 accounts produce 47% of videos. Shares
  therefore partly reflect the habits of a few hundred shops rather than
  broad behaviour.
- Trends over time mix three things: changes in BNPL, TikTok's own growth,
  and changes in API coverage. Compare shapes and shares, not absolute
  levels, and do not read growth in posts as growth in BNPL use.
- Engagement counts are a single snapshot taken at collection time and are
  shaped by the recommendation algorithm. They are not comparable across
  videos of different ages.

**What makes the conclusions valid.** Claims stay within what the data can
carry:

- they concern public content from accounts registered in Italy that matches
  these terms;
- they report counts with denominators and state the collection date;
- they are triangulated with the thesis's survey and interviews, which do
  measure the 20-27 population.

The search query, field list, collection log, and labelling rules are all
recorded (`query_config.json`, `collection_log.jsonl`,
`scripts/tiktok_terms.py`). Anyone can therefore reproduce the corpus
definition and check how each label was assigned.

## Quality checks

```powershell
uv run ruff check scripts tests
uv run ruff format --check scripts tests
uv run mypy scripts
uv run pytest
```

The tests run on synthetic data and need no API access.
