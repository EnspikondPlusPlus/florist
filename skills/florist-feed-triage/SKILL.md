---
name: florist-feed-triage
description: "Inspiration feed: summarize, tag and score incoming items against the user's seeds and interests, with a one-line 'why this matters to you'. Returns FeedTriage."
step: feed_triage
output: FeedTriage
agent: false
---

# Feed triage

The context has the user profile (with learned preferences), the active greenhouse seeds (id, title,
one-line prompt), recently composted and picked topics, and a batch of new feed items (id, source,
title, excerpt).

For **every** item return:

- `summary`: 1–2 plain sentences on what it actually is / claims. Newsletters and posts often bury
  the point; dig it out of the excerpt.
- `tags` (topics) and `technologies` (methods, libraries, models), short lowercase names.
- `relevance` 0–1 to *this user*:
  - 0.8–1.0 directly advances an active seed or is squarely a stated interest;
  - 0.5–0.7 adjacent: a technology they want to learn, or a likely compost-worthy idea;
  - 0.2–0.4 loosely related;
  - < 0.2 off-topic, promotional, or duplicate news.
- `why`: **one line**, specific, naming the seed or interest — "Relevant to *on-device speculative
  decoding* because it reports draft-model speedups on a 4090." Not "This could be interesting."
- `related_seed_ids`: seed ids it bears on.

Florist blends your relevance with its learned preference model; low scores are folded, not deleted.
