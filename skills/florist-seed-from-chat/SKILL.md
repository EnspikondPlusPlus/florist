---
name: florist-seed-from-chat
description: "Turn an Ideate conversation into a seed: title, prompt, tier, technologies and hard constraints. Returns SeedFromChat."
step: seed_from_chat
output: SeedFromChat
---

# Seed from chat

Distill the conversation into the seed the user converged on — not the first message, the idea as
it stands at the end.

- `title`: ≤ 8 words, specific ("Tiny-draft speculative decoding on a 4090").
- `prompt`: 2–5 sentences in the user's voice: what it is, why it matters to them, the first version.
- `tier`: `exploration` (understand a concept), `personal` (build something), or `formal`
  (a publishable research question) — whatever the conversation implies.
- `technologies`: the tools and methods discussed.
- `must_use` / `must_avoid`: only constraints the user actually stated.
