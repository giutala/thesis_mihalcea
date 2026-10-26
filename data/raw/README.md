# Raw data

`tiktok/` is created by `notebooks/tiktok_collection.ipynb` and holds the raw
TikTok Research API records:

- `videos/<start>_<end>.jsonl`: one file per completed 7-day window;
- `users.jsonl`: creator profiles, including unavailable ones;
- `comments/<video_id>.jsonl`: one file per collected comment thread;
- `pilot/`: search-term pilot yields and samples;
- `query_config.json`, `collection_log.jsonl`: frozen query and fetch log;
- `pseudonym_salt.txt`: salt for creator pseudonyms.

The folder is ignored by Git because it contains usernames, video text, and
comments. Analysis code reads it without modifying it.
