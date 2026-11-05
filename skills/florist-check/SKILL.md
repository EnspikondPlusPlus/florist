---
name: florist-check
description: "Loop step 3 (check): constrain novelty and feasibility. Score each direction against closest existing work, the user's constraints, crowdedness and the user's taste. Returns CheckOutput."
step: check
output: CheckOutput
---

# Check — novelty, feasibility, crowdedness, interest

For each direction in the context, Florist has already retrieved its **closest existing work**
(targeted searches per direction) and a **crowdedness count** (how many works match the direction's
key phrase overall and in the recent window). Score every direction; return one `checks` entry per
direction id.

## Novelty (0–1): grounded, never vibes

1. Read the closest-work candidates listed under that direction.
2. Pick the 1–3 that overlap most. For each: `closest_work` entry with `ref` (source id), `title`
   and `how_it_differs` — the concrete difference (setting, method, scale, data, audience).
3. Write `gap`: what remains genuinely undone. If you cannot name a gap, novelty ≤ 0.3.

Anchors:

| Score | Meaning |
| --- | --- |
| 0.0–0.2 | Already done; an existing repo/paper does this nearly as stated |
| 0.3–0.5 | Done in a nearby setting; the twist is small but real (port, scale, new data) |
| 0.6–0.8 | Clear gap with a named closest work that does not cover it |
| 0.9–1.0 | No close work found **and** retrieval was thorough — rare; justify it |

Tier sets how hard to look and how much novelty matters:

- **exploration** — light check. Novelty barely matters; reuse is good. Do not penalise "already
  exists" if building it teaches the concept.
- **personal** — moderate. "Has this been built? What can be reused?" A known idea re-built with
  a new angle, data or UX is fine; say what to reuse.
- **formal** — deep and current. Only works from the recent window count as "the field". A direction
  with a near-identical paper in the last 18 months scores ≤ 0.3 unless the gap is explicit.

## Feasibility (0–1) under *this user's* constraints

Check compute, hours per week × weeks to the goal date, proficiency vs. required skills,
data availability, must-use / must-avoid. Write the binding constraint in `feasibility_notes`.
0.8+ means a first result is reachable within ~2 weeks of the user's time.

## Crowdedness (0–1)

Use the counts given: high recent counts or many active repos → crowded. A crowded area can still
be worth it for a personal project; for formal investigations it lowers the chance of a clean
contribution.

## Interest (0–1): the user's taste

Score how much *this user* would care, using interests, wants-to-learn, work preferences and
**learned preferences** (behavioural, signed weights). Florist blends your score with its own
preference model, so judge from the profile, not from general hype.

## Also

- `risks`: the 1–3 things most likely to sink it.
- `smoke_worthy`: one key assumption a tiny, cheap test could confirm (a library does X, a dataset
  is downloadable, a toy example runs). Leave empty if none.
