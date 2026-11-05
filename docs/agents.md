# Coding agents

You can drive Florist from Claude Code, Codex, Cursor or any agent that speaks MCP — and you can
let the agent do the thinking itself, using your subscription instead of an API key.

## Connect Claude Code

The quickest way is MCP. One command registers Florist's tools with Claude Code:

```bash
uv run florist mcp install
```

Now you can ask Claude things like *"what's in my Florist feed today?"*, *"grow my speculative
decoding seed one more round"* or *"pick it and show me the program.md"*.

To also give Claude the Florist playbook and skills:

```bash
uv run florist skills install --target claude
uv run florist agent --seed speculative       # a Claude Code session focused on one seed
```

## Let the agent be the brain

Normally Florist calls a model for every step of a round. Instead, the agent can answer each step
itself. Florist still does the searching, keeps the graph, renders the visuals, and checks every
answer — it rejects findings that cite sources it never retrieved.

```bash
uv run florist round start speculative       # prints the first task as JSON
# … the agent reads `instructions`, thinks over `context`, writes out.json matching `schema` …
uv run florist round submit speculative --file out.json
```

Each submit returns the next task until the round is done. The steps are: plan searches, judge
what was found, propose directions, check novelty and feasibility, propose smoke checks, rank and
prune, describe a concept diagram, and write the flower.

## Codex

```bash
uv run florist mcp install --harness codex    # prints the config block for ~/.codex/config.toml
uv run florist agent --harness codex
```

## Useful commands for scripts

Every command takes `--json`:

```bash
uv run florist status --json
uv run florist seed list --json
uv run florist feed list --status kept --json
uv run florist research "speculative decoding" --kind repo --json
uv run florist usage --json
```

Read the full command reference any time with:

```bash
uv run florist skill
```
