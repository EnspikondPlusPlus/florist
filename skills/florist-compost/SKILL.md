---
name: florist-compost
description: "Compost processing: turn a saved link, note or feed item into a compost row — summary, key takeaways, tags, technologies, related seeds, why it was interesting. Returns CompostProcessed."
step: compost
output: CompostProcessed
---

# Compost — process a saved item

Turn the item in the context into a row of the user's "everything interesting" spreadsheet.

- `summary`: 2–3 sentences, what it is and what it shows.
- `takeaways`: up to 5 key takeaways a person would want to remember in six months.
- `tags` (topics) and `technologies` (methods, tools, models, datasets) — short, lowercase, reuse the
  tag vocabulary already in the compost when it fits (listed in the context).
- `why_interesting`: one sentence on why *this user* kept it, tied to their interests or seeds.
- `related_seed_ids`: ids of greenhouse seeds it bears on.

Only use what the item says. If the text is thin (just a title), keep the summary short and say so.
