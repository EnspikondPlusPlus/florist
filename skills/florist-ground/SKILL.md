---
name: florist-ground
description: "Loop step 1a (ground): plan literature, repo and post searches for a seed. Returns GroundPlan."
step: ground
output: GroundPlan
---

# Ground — plan the searches

You are planning what Florist should read before proposing directions for a seed.

## Inputs (in the context)

- The seed: prompt, tier, technologies, constraints, follow-up answers.
- Linked compost items and feed items the user attached.
- The current flower and directions from earlier rounds (if any), plus user steering notes.
- Queries already run in earlier rounds (do not repeat them).

## What to produce

`queries`: distinct searches that together map the space. Mix kinds:

- `paper` — terminology a paper abstract would use (method names, task names, benchmarks).
- `repo` — what someone would name a GitHub project or library ("speculative decoding llama.cpp").
- `post` — practitioner discussion (blog/HN phrasing).

Depth by tier:

| Tier | Queries | Emphasis |
| --- | --- | --- |
| exploration | 3–4 | explainer-level papers, popular repos, what the concept *is* |
| personal | 4–6 | existing implementations to reuse, has-this-been-built, tooling |
| formal | 6–8 | recent (last ~18 months) papers, closest competitors, benchmarks, open problems |

Rules:

- In round 2+, target the *top directions* and *open questions* from the previous flower and the
  user's steering, not the seed in general.
- Each query 2–8 words. No boolean operators. One idea per query.
- `technologies`: the 3–8 key technologies / methods the seed touches (used to label the graph).

If `steering.new_ideas` is non-empty, the user just added an idea mid-search: at least half of the
queries must target the new idea and how it connects to the seed.
