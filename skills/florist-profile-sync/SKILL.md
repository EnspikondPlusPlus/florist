---
name: florist-profile-sync
description: "Read the user's free-form profile.md (possibly pasted from a CV or website) and extract the structured fields Florist uses. Returns ProfileSync."
step: profile_sync
output: ProfileSync
---

# Profile sync

The context is the user's own profile document. It may follow Florist's headings or be pasted from
anywhere (a CV, a personal site, notes). Extract only what it actually says:

- `interests`, `proficient_in`, `wants_to_learn`, `work_preferences`, `conference_targets`:
  short items (1–5 words each), deduplicated, in the user's terms.
- `compute`: one line describing hardware ("1x RTX 4090, no cluster").
- `budget_usd_month`, `hours_per_week`: numbers if stated, otherwise null.
- `goal_date`: ISO date if a date is stated, otherwise empty.

Never invent. Leave a field empty rather than guessing.
