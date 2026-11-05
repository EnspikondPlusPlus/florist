# Architecture

```
┌──────────── app/ (React) ────────────┐   ┌──── coding agents ─────┐   ┌── terminal ──┐
│ Feed · Compost · Greenhouse · Seed   │   │ MCP tools · skills ·   │   │ florist …    │
│ workspace · Settings                 │   │ florist agent          │   │ --json       │
└──────────────┬───── REST + /ws ──────┘   └───────────┬────────────┘   └──────┬───────┘
               │                                       │                       │
┌──────────────▼───────────────────────────────────────▼───────────────────────▼───────┐
│ florist/ (Python)                                                                     │
│  server.py (FastAPI)   cli.py (Typer)   mcp_server.py (FastMCP)   desktop.py         │
│  agent/loop.py ── steps ── skills/ (prompts+rubrics) ── schemas.py (validation)      │
│  gateway.py ── LiteLLM │ claude -p --json-schema │ codex exec │ mock   (+ cost log)  │
│  research.py ── alphaXiv → OpenAlex → arXiv → Semantic Scholar → agent web (cached)  │
│  ingest/ (feed fetchers + triage)  agent/compost.py  agent/preferences.py            │
│  agent/visuals.py (SVG/Mermaid/Plotly)  agent/smoke.py (approved subprocess)         │
│  agent/pack.py ── adapters/ (Jinja)  agent/scheduler.py (passive growth, tick)       │
│  store/db.py ── SQLite (WAL) document tables + activity log                          │
└───────────────────────────────────────────────────────────────────────────────────────┘
                     ~/.florist: florist.db · profile.yaml · about.md · settings.yaml
                                 visuals/ · smoke/ · packs/
```

## Principles (spec §11)

1. **Schemas first.** `florist/schemas.py` defines every record and step output; `schemas/` holds
   the exported JSON Schemas (a test keeps them in sync).
2. **One gateway, one research layer.** All LLM calls go through `gateway.complete` (validation,
   one repair retry, tokens/cost/latency logged per call in `llm_calls`). All lookups go through
   `research.search` (fallback chain + `research_cache`).
3. **Prompts are files.** `skills/<name>/SKILL.md`; adapters are templates in `adapters/`.
4. **Nothing executes without approval.** Smoke checks run in `python -I` subprocesses with a
   minimal environment and a hard timeout, only after an explicit approve.
5. **Traceability.** `apply_flower` drops findings whose evidence ids do not exist; `apply_check`
   keeps only closest-work refs that are real source nodes.

## The loop as a state machine

```
ground → search* → triage → explore → check_search* → check → smoke → exploit → visualize → render* → flower
```

`*` = code steps (retrieval, rendering). Every LLM step has `prepare(ctx) → {context, hints}` and
`apply(ctx, output)`. The run's cursor and scratch state live in `runs.state`, so:

- the **internal driver** (`loop.drive`) calls the gateway for each LLM step;
- the **agent driver** (`loop.next_task` / `loop.submit`) hands each step to an external coding
  agent and validates its submission — same prepare/apply, same guarantees;
- a run started from the CLI shows up live in the UI (the server tails the `activity` table and
  pushes rows over `/ws`).

**Stopping:** flower stability (similarity of directions, findings and idea between versions)
≥ 0.85 from round 2, the seed's dollar budget, the requested rounds, or a stop request.

**On-the-fly changes:** before each step the loop checks for new ideas the user dropped in
(`chat.role = 'idea'`). If one arrives after grounding, the round restarts at *ground* (once per
round) with the idea in `steering.new_ideas`; *explore* must develop it.

## Novelty and feasibility constraint

For each direction, `check_search` retrieves closest work with tier-dependent depth (1–3 queries:
papers, repos, recent papers) and, for personal/formal tiers, OpenAlex counts (all-time and last
18 months) for crowdedness. The `florist-check` rubric anchors novelty scores to what was retrieved
(“an existing repo does this nearly as stated → ≤ 0.2”). The overall score weights novelty,
feasibility, room (1 − crowdedness) and interest differently per tier.

## Preference adaptation

`events` (every gesture) → signed weights per tag / technology / source in
`profile.yaml → learned_preferences` (exponential move toward ±1, scaled by gesture strength;
locked entries never move) → `preferences.score()` used by feed ranking and blended 50/50 with the
critic's interest score → periodic `florist-taste` distillation into plain-language statements.
The user's own `about.md` is part of every prompt.

## Storage

SQLite in WAL mode; each table has indexed columns plus a validated JSON `doc`. Migrations live in
`florist/store/migrations/*.sql`. Files (visuals, smoke runs, packs) live under `~/.florist`.
