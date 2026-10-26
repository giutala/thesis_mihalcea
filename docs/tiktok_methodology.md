# TikTok BNPL corpus: methodology

## Purpose and place in the thesis

The TikTok corpus is a separate data source from the interviews. It shows how
Buy Now, Pay Later (BNPL) is presented and talked about publicly on Italian
TikTok, and it feeds the market, benchmark, and regulatory analysis. It does
not sample the study population. The API reports no age, and `region_code` is
the country where the creator's account is registered, not the language or the
viewer's location.

| Thesis question | What the corpus can show |
|---|---|
| RQ1: tracking and mental models | How BNPL is described ("tanto sono 3 rate", "non è un debito") and how often tracking practices are mentioned |
| RQ2: when awareness breaks down | How often posts and comments mention losing track, missed payments, or fees |
| RQ3: interventions without paternalism | How often commentary warns about BNPL, and how often comments push back |
| Market and regulatory analysis | Which providers appear, who promotes them, framing ("zero interessi"), seasonality, mentions of regulation |

All labels in the corpus come from transparent text rules, with no manual
coding. Every count is therefore a measure of what is *mentioned in text*, and
the limits of that are listed below.

## Data source

The source is the TikTok Research API, used under the approved research
application. Three endpoints are used:

- `/v2/research/video/query/` to search videos;
- `/v2/research/user/info/` to read public creator profiles;
- `/v2/research/video/comment/list/` to read comments on selected videos.

The API returns public content only. Private, deleted, and moderated videos
are absent. Engagement counts are a snapshot taken on the fetch date stored
with each record.

## Search definition

1. **Pilot (25 October 2026).** Each of 13 candidate keywords and 7 hashtags in
   `scripts/tiktok_terms.py` was queried alone over the last complete 30 days,
   restricted to accounts registered in Italy. Each term cost one request. The
   yield (videos on the first page of up to 100) and a sample of 20 videos per
   term were saved to `data/raw/tiktok/pilot/`.

   | Term | Field | First-page videos | More pages | Decision |
   |---|---|---|---|---|
   | klarna | keyword / hashtag | 98 / 100 | yes / yes | kept |
   | scalapay | keyword / hashtag | 97 / 99 | yes / yes | kept |
   | heylight | keyword | 98 | yes | kept |
   | pagolight | keyword | 10 | no | kept |
   | pagodil | keyword | 15 | no | kept |
   | soisy | keyword | 1 | no | dropped: one unrelated video |
   | paga in 3 rate | keyword | 99 | yes | kept |
   | rate senza interessi | keyword | 98 | yes | kept |
   | pagare a rate | keyword | 99 | yes | dropped: mostly debt repayment and tax installments |
   | pagamento a rate | keyword | 94 | yes | dropped: mostly generic retailer financing |
   | compra ora paga dopo | keyword | 10 | no | kept |
   | buy now pay later | keyword | 10 | no | kept |
   | bnpl | keyword / hashtag | 8 / 1 | no | kept |
   | buynowpaylater, pagaarate, acquistiarate, pagain3rate | hashtag | 4-11 | no | kept |

   Reading the samples also showed that most videos are shop and service ads
   that list BNPL as a payment option. This led to the post-type
   classification described below.
2. **Final query.** `region_code IN [IT]` AND (`keyword IN [kept keywords]`
   OR `hashtag_name IN [hashtags]`). API keywords match the video description
   only. The query and field list are frozen in
   `data/raw/tiktok/query_config.json`, and the collection refuses to resume
   with a different query.
3. **Period.** From 1 January 2024, in 7-day windows, up to three days before
   the run. The last three days are skipped because TikTok indexes new videos
   with a delay. The configured end is 31 January 2027. Rerunning after 20
   November 2026 adds the post-CCD2 period, Black Friday 2026, and Christmas.
4. **Fields.** `id, username, create_time, region_code, video_description,
   voice_to_text, hashtag_names, view_count, like_count, comment_count,
   share_count, video_duration, is_stem_verified`.

## Collection procedure

- `scripts/tiktok_client.py` sends requests with `requests`. A 401 response
  triggers one token refresh. HTTP 429 and 5xx responses are retried after 2,
  4, 8, 16, 32, and 60 seconds. Any other error stops the run. When 429
  responses persist, the daily quota is treated as exhausted and the run stops
  cleanly.
- Each window is written to `data/raw/tiktok/videos/<start>_<end>.jsonl` only
  when it is complete, through a temporary file that is then renamed. Windows
  already on disk are skipped.
- `collection_log.jsonl` records the window, video count, `search_id`, and
  fetch time of each completed window and comment thread.
- Each profile costs one request. Profiles are therefore fetched for every
  creator of a non-ad post and for the 300 most active creators. Other
  creators are `not_profiled`.
- Comments are fetched for the most-commented videos of each post type: up to
  300 personal-experience videos, 300 commentary videos, 100 unclassified
  posts, and 100 shop ads. TikTok caps the comments returned per video and
  does not return comment authors.

## Corpus construction and labels

1. **Deduplication.** Records are deduplicated by video ID. The most recently
   fetched copy is kept, so engagement counts are the latest snapshot.
2. **BNPL signal.** A video is kept when its description, hashtags, or
   transcript name a provider (`named_provider`) or contain a generic BNPL
   phrase such as "paga in 3 rate", "compra ora paga dopo", or "rate senza
   interessi" (`bnpl_phrase`). PayPal and Amazon count only when installments
   are named nearby.
3. **Post type** (`POST_TYPE_RULES`). Rules are applied in this order, and the
   first match wins:
   1. `financial_commentary`: education, warnings, and news ("educazione
      finanziaria", "credito al consumo", "trappola", "è un debito",
      "indagine");
   2. `shop_ad`, strong markers: prices, "spedizioni", WhatsApp, websites,
      phone numbers, "vi aspettiamo", and TikTok Shop campaign hashtags;
   3. `personal_experience`: first-person use ("ho pagato con Klarna", "le mie
      rate", "truffata");
   4. `shop_ad`, weak markers: "paga con", "offerta", "promo", addresses;
   5. `other`: everything else, mostly hashtag-only posts.

   The order was set by reading samples. Shops use first-person phrasing, so
   strong ad markers are checked before the first-person rule. Even so, about
   half of `personal_experience` posts are creator product reviews rather
   than independent accounts, so the label means "first-person posts", not
   "user testimonies".
4. **Creator type** (profiled creators only). `provider_official` is assigned
   from the handle alone. `news_institution`, `finfluencer_educator`, and
   `merchant_brand` come from handle and bio. A creator whose bio matches none
   of these but whose BNPL posts are at least half shop ads is also
   `merchant_brand`, because many shops have no bio. Any other public profile
   is `ordinary_user`, and accounts whose profile TikTok did not serve are
   `unknown`. Profiling covered every creator of a non-ad post, so
   `ordinary_user` is over-represented among profiled creators compared with
   the whole corpus.
5. **Theme cues** (`CUE_PATTERNS`). Dictionaries flag mentions of: free or easy
   framing, not-debt or small-amount framing, tracking practices, losing
   track, payment failure and fees, reactions to paternalism, regulation,
   shopping context, and purchase enquiries (questions about price,
   availability, or shipping, mainly meaningful for comments).
6. **Time.** Timestamps are converted to Europe/Rome time. Videos from 20
   November 2026 onward are labelled `post_ccd2`. Black Friday weeks are
   indexed against the mean of the six preceding weeks.

## Outputs

| Location | Content | In Git |
|---|---|---|
| `data/raw/tiktok/` | Raw API records, pilot, query config, collection log, pseudonym salt | No |
| `data/processed/tiktok/` | Labelled video and comment corpora with text, pseudonymized creator IDs | No |
| `outputs/tiktok/tables/` | Aggregate tables only | Yes |
| `outputs/figures/tiktok/` | Aggregate figures (300 dpi PNG) | Yes |
| `outputs/tiktok/findings_summary.md` | Descriptive summary generated from the tables | Yes |

## Limitations

- The corpus covers public discourse, not the study population, and gives no
  information about age.
- Keyword search covers descriptions only, so videos that mention BNPL only in
  speech or on screen are missed unless a hashtag matches.
- Post types, creator types, and cues are lexical rules. They miss irony,
  negation, and anything shown only in the video. Rates are mention rates, not
  validated prevalence.
- API coverage and platform growth change over time. Compare shapes and
  shares, not absolute levels.
- Profiles and comments cover selected subsets because of the request quota.
- Engagement is a snapshot and is influenced by TikTok's recommendation
  system.

## Ethics and data protection

- **Lawful basis.** Only public content is processed, under the TikTok
  Research API terms of the approved project, and only for this thesis.
- **Minimization.** Only the fields listed above are requested. Profiles and
  comments are fetched for capped subsets.
- **Pseudonymization.** Creator handles are replaced by salted SHA-256 IDs in
  processed corpora and in all tables and figures. The salt stays in the
  ignored raw folder. Comments carry no author handle.
- **Storage.** All text-bearing files live in ignored folders on the
  researcher's machine. Credentials come from environment variables, the
  ignored `.env` file, or a prompt, and are never saved in notebooks.
- **Reporting.** The thesis names no individual accounts and paraphrases
  quotes, because verbatim text can be searched back to an account. Provider
  and institution accounts may be named as organizations.
- **Retention.** Check the deletion and refresh obligations of the TikTok
  Research API terms in force. Raw data is deleted at the end of the thesis
  unless those terms or the university's data policy require otherwise.
