---
name: florist
description: Use the `florist` CLI (or the Florist MCP tools) to manage the user's ideation garden — inspiration feed, compost, greenhouse seeds — and to grow a seed into a flower and a flower pack, either letting Florist's loop run or acting as the loop's brain yourself. Read this before driving Florist programmatically.
---

# Florist CLI (`florist`)

Florist grows ideas: **feed** (inspiration from papers, newsletters, repos, videos) → **compost**
(everything interesting the user can't commit to yet) → **greenhouse** (seeds they want to pursue)
→ **exploration loop** (ground → explore → check → smoke → exploit → visualize → flower) →
**flower pack** (handoff for OpenResearch, Co-Scientist, a build plan, or a coding agent).

All state is local (`~/.florist`: SQLite, `profile.yaml`, visuals, packs). Every command takes
`--json`. Seeds are addressed by slug, id, or a unique prefix of either.

## Cardinal rules

1. **Never invent evidence.** Every finding you submit must cite ids that exist in the context you
   were given (`src_…` sources, `chk_…` checks, `smk_…` smoke checks). Florist drops findings whose
   refs don't exist and rejects outputs with unknown ids.
2. **Never run code without the user.** Smoke checks run only after the user approves:
   show them `florist smoke show <id>` and ask before `florist smoke run <id> --yes`.
3. **Constraints are hard limits.** The profile (compute, hours/week, skills, deadline) and each
   seed's must-use / must-avoid are not suggestions.
4. **Taste is the user's.** When the user reacts to something (likes a direction, dismisses an
   item), record it — `florist direction boost|prune <node>`, `florist feed act <id> dismiss` — so
   Florist's preference model learns. Learned preferences are visible in `profile.yaml`.
5. **Keep what you reject.** Prune with a specific reason; pruned branches are kept forever.

## Two ways to grow a seed

**A. Florist runs the loop** with its configured model (API key or a coding subscription):

```sh
florist grow <seed> --rounds 2          # streams progress; stops when the flower is stable or the budget is used
florist flower <seed>                   # findings with evidence, directions, gap, first steps
```

**B. You are the loop's brain** (no Florist model needed; use your own reasoning and web tools):

```sh
florist round start <seed> --rounds 1   # → JSON task: {step, skill, instructions, context, schema, submit}
# read `instructions`, think over `context`, write JSON matching `schema` to out.json
florist round submit <seed> --file out.json   # → {accepted, error?, next: <next task or run result>}
florist round next <seed>               # re-print the pending task at any time
```

Steps arrive in order: `ground` (plan searches) → `triage` (judge retrieved sources) → `explore`
(propose directions) → `check` (novelty / feasibility / crowdedness / interest, grounded in the
closest-work candidates Florist retrieved) → `smoke` (optional tiny tests) → `exploit` (rank, keep,
prune with reasons) → `visualize` (concept diagram spec) → `flower` (the living summary).
Florist does the searching, graph-building and rendering between steps. If a submission is
rejected, fix exactly what the error says and resubmit. Load a step's full rubric with
`florist skill <name>` (e.g. `florist skill florist-check`).

## Command quick reference

### Garden
| Command | What it does |
|---|---|
| `florist status` | Models, seeds by state, feed/compost sizes, spend |
| `florist seed add "<prompt>" --tier personal [--tech X] [--must-use X] [--compute "…"] [--ask]` | Plant a seed (`--ask`: Florist asks ≤ 2 follow-ups) |
| `florist seed list [--all]` / `seed show <seed>` | Greenhouse by tier and state |
| `florist seed edit <seed> --set tier=formal --set constraints.compute="1x 4090"` | Edit fields |
| `florist seed priority <seed> 1..5` / `seed compost <seed>` / `seed state <seed> dormant` | Lifecycle |

### Loop and steering
| Command | What it does |
|---|---|
| `florist grow <seed> [--rounds N] [--model M]` | Florist's own loop |
| `florist round start/next/submit <seed>` | Agent-driven loop (you are the model) |
| `florist graph <seed> [--mermaid]` / `florist flower <seed>` | Exploration graph / flower |
| `florist direction boost\|prune\|deepen\|restore <node> [--note "…"]` | Steer a direction |
| `florist steer <seed> "<note>"` / `florist chat <seed> "<msg>"` | Steering for the next round |
| `florist smoke list [seed]` / `smoke show <id>` / `smoke run <id>` | Smoke checks (approval first!) |
| `florist pick <seed> [--adapter openresearch] [--out DIR]` | Write the flower pack |
| `florist pick <seed> --prepare` then `pick <seed> --handoff plan.json` | Write the handoff yourself |

### Feed and compost
| Command | What it does |
|---|---|
| `florist feed fetch` / `feed list [--status kept,folded]` | Pull sources / read the ranked stream |
| `florist feed add <url> [--note]` | Save a link to Florist |
| `florist feed act <item> compost\|attach --seed S\|seed\|dismiss\|keep` | One-gesture actions (teach the filter) |
| `florist sources list/add/remove` | rss, youtube, arxiv, alphaxiv, github, hn, email |
| `florist compost list/add/clusters` | The pile and its themes |
| `florist compost mine [--prepare / --submit out.json]` | Connections → candidate seeds |
| `florist compost seed <id> <id> …` / `compost accept <seed>` | Start a seed from items / accept a candidate |

### Profile, models, research
| Command | What it does |
|---|---|
| `florist profile show/edit/set <key> <json>` | Knobs: interests, skills, compute, time, downtime |
| `florist profile learn [--prepare / --submit]` | Distill behaviour → learned preference statements |
| `florist models show/set <model>/key <provider> <key>/test` | `claude-code:sonnet`, `codex:gpt-5`, `meta_llama/…`, `mock` |
| `florist research "<query>" [--kind repo] [--tool openalex]` | Cached papers/repos/posts search with fallback |
| `florist deadlines` | Upcoming conference deadlines for the profile's targets |
| `florist usage [--seed S]` | Tokens and cost per step/model |
| `florist up` / `florist app` | Dashboard in the browser / desktop window |
| `florist mcp install` | Register Florist's MCP tools with Claude Code |

## Picking: what the pack contains

`flower-<slug>/flower.md` (brief), `flower.json` (schema-versioned), `sources.json`, `pruned.json`,
`visuals/` (concept, landscape, scores, smoke, graph), `smoke/`, and `adapters/`:
`openresearch/program.md`, `coscientist/research_goal.md`, `build_plan/BUILD_PLAN.md`,
`coding_agent/AGENTS.md`.
