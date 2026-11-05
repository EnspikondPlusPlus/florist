---
name: florist-flower
description: "Loop step 7 (update the flower): rewrite the living summary for a seed — findings with evidence, recommended directions, novelty evidence, risks, first steps. Returns FlowerDraft."
step: flower
output: FlowerDraft
---

# Flower — the living summary

Rewrite the seed's flower from everything in the context: kept directions and their checks, the
landscape, sources, smoke-check results, the previous flower and user steering.

- `idea`: the idea in one paragraph, as it now stands (not as first typed).
- `findings`: **3–7** major findings. Each has `evidence`: one or more `{ref, quote}` where `ref`
  is a source id (`src_…`), smoke check id (`smk_…`) or check id (`chk_…`) from the context and
  `quote` is the short fact from it that supports the finding. **A finding with no valid evidence
  is dropped by Florist.** Findings are facts about the world ("X already exists and does Y",
  "Z dataset has N examples", "method A beats B on C"), not advice.
- `directions`: **1–3** recommended project directions, each tied to its direction node id
  (`node_id`), with a 2–3 sentence `pitch` and `why_you` (fit to this user's skills, compute,
  interests, learning goals).
- `novelty`: the closest existing work (`ref`, `title`, `how_it_differs`) and the `gap`.
- `risks`, `open_questions`: short, concrete.
- `first_steps`: the first 3–5 actions, each doable in one sitting.
- `success_criteria`: how the user will know it worked (measurable where possible).

Keep stable what has not changed — a flower that churns every round is a bad flower. Change it
where new evidence or steering warrants.
