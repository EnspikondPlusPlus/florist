---
name: florist-visualize
description: "Loop step 5 (visualize): describe the core technique as a small concept diagram that Florist renders to SVG and Mermaid. Returns ConceptSpec."
step: visualize
output: ConceptSpec
---

# Visualize — concept explainer

Florist draws the landscape map, score chart and exploration graph itself from data. Your job is
the **concept explainer**: how the core technique of the top direction works, as a diagram a smart
newcomer understands in 20 seconds.

Return a `ConceptSpec`:

- `title`: the technique's name.
- `key_insight`: one sentence — the "aha" of the technique.
- `steps`: 3–8 boxes. `id` is a short identifier (letters, digits, underscore; e.g. `draft`),
  `label` ≤ 5 words, `detail` ≤ 20 words saying what happens there.
  Optional `group` places boxes in lanes (e.g. `input`, `model`, `output`) — use 2–3 lanes at most.
- `edges`: arrows between step ids, in reading order, with an optional ≤ 3-word `label`
  ("accept", "reject", "feedback"). A loop back is allowed and often clarifying.
- `caption`: one or two sentences under the figure: what to notice.

Prefer the mechanism over the project plan: draw *how it works*, not *what to do next*.
