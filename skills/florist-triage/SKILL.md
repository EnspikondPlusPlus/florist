---
name: florist-triage
description: "Loop step 1b (ground): judge retrieved sources for relevance to the seed and summarize the landscape. Returns GroundTriage."
step: triage
output: GroundTriage
---

# Triage — read what was found

The context lists sources retrieved for this seed, each with an id (`src_…`), title, year, venue
and abstract.

For **every** source return a note:

- `ref`: the source id.
- `keep`: false for off-topic or duplicate results (they stay in the cache, not the graph).
- `relevance` 0–1: how directly it bears on the seed *as this user would pursue it*.
- `summary`: one or two sentences in terms of the seed ("Shows X works for Y; uses Z").
  Use only what the abstract says.
- `technologies`: methods / tools it uses (short names).

Then `landscape`: 3–5 sentences. What already exists, which parts look crowded, where the
gaps might be, and what is reusable. Name sources by id in parentheses, e.g. "(src_1a2b)".
