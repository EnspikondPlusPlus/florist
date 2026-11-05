---
name: florist-followups
description: "Seed intake: ask at most two follow-up questions about a new seed, and suggest a title, technologies and tier. Returns FollowUpQuestions."
step: followups
output: FollowUpQuestions
---

# Follow-ups — the minimum needed to start

The user just planted a seed with a short prompt. Florist fills the rest from the profile.
Ask **at most two** questions, and only ones whose answer would change which directions are worth
exploring (e.g. "Is the goal a demo you can show, or a measurable speedup?", "Must it run on your
4090, or is cloud OK?"). Do not ask about anything the profile or seed already answers.
Zero questions is a good answer for clear seeds.

Also return a short `title` (≤ 8 words) if the seed has none, the `technologies` it names or
implies, and a `tier_suggestion` if the stated tier looks off.
