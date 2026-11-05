---
name: florist-explore
description: "Loop step 2 (explore): propose distinct project directions for a seed, evolving the best previous ones. Returns ExploreOutput."
step: explore
output: ExploreOutput
---

# Explore — widen the space of directions

Propose directions for the seed. This is the *generate* (and in later rounds *evolve*) step of a
generate → critique → rank → evolve loop.

## Round 1

Propose 4–5 **genuinely different** directions. Vary at least two of:

- the core technology or method,
- the framing (tool vs. study vs. benchmark vs. visual explainer vs. application),
- the scope (weekend hack → multi-month investigation, as the tier allows).

## Round 2+

The context marks the current top directions and what to deepen. Propose:

- 1–2 **evolutions** of top directions (set `evolves` to that direction's id): narrow the scope,
  combine with another direction, or adapt to a finding from new sources;
- 1–2 **new** directions that address open questions or user steering.

Do not re-propose pruned directions (listed with their reasons) unless the user's steering
explicitly brings one back.

## Fit to the user

- Must-use tools must appear; must-avoid tools must not.
- Respect compute (no pretraining on a single GPU), time per week and the goal date.
- Lean toward the user's `wants_to_learn` when it costs little, and toward learned preferences.
- Tier shapes ambition: exploration → understand and demo; personal → buildable artifact;
  formal → a research question with a measurable claim and a baseline.

Each direction: a crisp `title` (≤ 8 words), a `description` of what is built or studied,
the `framing`, `technologies`, a first-version `scope`, and `inspired_by` source ids.

## New ideas from the user

`steering.new_ideas` holds ideas the user dropped in mid-search. Each new idea must be developed by at
least one direction this round — on its own, or combined with the seed if that is stronger. Say in the
`framing` which idea it develops.
