---
name: florist-pick
description: "Picking: turn a flower into the handoff block of a flower pack — objective, metric, what may and may not change, milestones, first session. Returns HandoffPlan."
step: pick
output: HandoffPlan
---

# Pick — write the handoff

The user picked this flower. Florist will render one pack for several destinations (OpenResearch /
autoresearch `program.md`, a Co-Scientist research goal, a personal build plan, a coding agent's
`CLAUDE.md`). You write the shared handoff content once, for the **first recommended direction**
unless the user's steering says otherwise.

- `objective`: one or two sentences — what the downstream agent or person should achieve.
- `metric` + `metric_direction`: the single number that says it worked (e.g. "tokens/s at equal
  perplexity on WikiText-2, maximize"). For exploration tiers a `qualitative` metric is fine.
- `baseline`: what to compare against first (simplest credible baseline; reuse existing code).
- `may_change` / `must_not_change`: for an autonomous experiment agent — which files or knobs it may
  edit, and what is frozen (eval script, dataset split, metric code, compute budget).
- `constraints`: compute, time, budget, must-use / must-avoid, deadline — concrete numbers.
- `background`: 3–6 sentences of context a downstream agent needs, citing sources by title.
- `preferences`: the user's working style that should shape execution.
- `milestones`: 3–6 milestones, each with a `goal`, 2–5 `tasks` and `est_hours` that fit the
  user's hours per week and goal date.
- `first_session`: the to-do list for the very first sitting (3–6 items, each ≤ 1 hour).
- `tools`: libraries, datasets, repos to use (prefer ones found in sources).
- `conventions`: coding and experiment conventions for a coding agent (small steps, one fixed run
  command, log results to a table, keep a baseline, etc.).
- `first_experiments`: 2–4 first experiments for an autoresearch-style agent, in order.
