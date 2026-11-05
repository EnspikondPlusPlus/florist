"""MCP server: Florist as native tools for Claude Code, Codex, Cursor and other MCP clients.

Register with ``florist mcp install`` (runs ``claude mcp add florist -- florist mcp``).

Two ways for an agent to use the loop:

* ``florist_grow`` — Florist runs rounds with its configured model (API or subscription);
* ``florist_round_start`` / ``florist_round_next`` / ``florist_round_submit`` — the agent itself
  is the brain: it receives each step's skill, context and JSON Schema, does the thinking (and may
  use its own web tools), and submits validated JSON back.
"""

from __future__ import annotations

import json
from typing import Any

try:  # MCP Python SDK 2.x
    from mcp.server.mcpserver import MCPServer as _Server
except ImportError:  # SDK 1.x
    from mcp.server.fastmcp import FastMCP as _Server

from . import config, skills
from .agent import compost, greenhouse, loop, pack, preferences
from .ingest import feed
from .store import db

mcp = _Server("florist", instructions=(
    "Florist is the user's ideation suite: inspiration feed, compost pile, greenhouse of seeds, and an "
    "exploration loop that grows a seed into a flower (findings with evidence, directions, visuals) and "
    "picks it into a flower pack for OpenResearch / Co-Scientist / a build plan / a coding agent. "
    "Read the `florist://skill/overview` resource first. Never run smoke checks without asking the user."
))


def _j(obj: Any) -> str:
    return json.dumps(obj, indent=1, ensure_ascii=False, default=str)


@mcp.resource("florist://skill/overview")
def overview() -> str:
    """How to drive Florist (the CLI/agent skill)."""
    return skills.cli_overview()


@mcp.resource("florist://skill/{name}")
def skill(name: str) -> str:
    """A step skill (prompt + rubric), e.g. florist-check."""
    s = skills.get(name)
    return f"{skills.shared_preamble()}\n\n{s.body}"


@mcp.tool()
def florist_status() -> str:
    """Overview: configured models, seed counts by state, feed and compost sizes, spend."""
    from .server import status

    return _j(status())


@mcp.tool()
def florist_list_seeds(include_candidates: bool = False) -> str:
    """Seeds in the greenhouse with tier, state, priority, flower summary and current run."""
    from .server import list_seeds

    return _j(list_seeds(all=include_candidates))


@mcp.tool()
def florist_add_seed(prompt: str, tier: str = "personal", title: str = "", technologies: list[str] | None = None,
                     must_use: list[str] | None = None, must_avoid: list[str] | None = None, time: str = "",
                     compute: str = "", priority: int = 3) -> str:
    """Plant a seed. tier: exploration | personal | formal."""
    seed, _ = greenhouse.create_seed(prompt, tier=tier, title=title, technologies=technologies or [],
                                     constraints={"must_use": must_use or [], "must_avoid": must_avoid or [],
                                                  "time": time, "compute": compute}, priority=priority)
    return _j(seed.model_dump(mode="json"))


@mcp.tool()
def florist_get_seed(seed: str) -> str:
    """Seed details (id or slug) plus flower summary and runs."""
    from .server import get_seed

    return _j(get_seed(seed))


@mcp.tool()
def florist_grow(seed: str, rounds: int = 1) -> str:
    """Run exploration rounds with Florist's configured model. Blocks until done."""
    return _j(loop.grow(seed, rounds=rounds))


@mcp.tool()
def florist_round_start(seed: str, rounds: int = 1) -> str:
    """Start an agent-driven run: YOU are the model. Returns the first task (instructions, context, schema)."""
    ctx = loop.start(seed, rounds, "agent")
    return _j(loop.next_task(run_id=ctx.run_id))


@mcp.tool()
def florist_round_next(seed: str) -> str:
    """The pending task of an agent-driven run."""
    return _j(loop.next_task(seed))


@mcp.tool()
def florist_round_submit(seed: str, output: dict[str, Any]) -> str:
    """Submit your JSON output for the pending step. Returns accepted/error and the next task."""
    return _j(loop.submit(seed, output))


@mcp.tool()
def florist_get_flower(seed: str) -> str:
    """Current flower: findings with evidence refs, directions, novelty, risks, first steps."""
    from .server import flower

    return _j(flower(seed))


@mcp.tool()
def florist_graph(seed: str) -> str:
    """Exploration graph nodes (sources, directions, checks, smoke, findings) and edges."""
    from .server import graph

    g = graph(seed)
    for n in g["nodes"]:
        n["data"] = {k: v for k, v in n["data"].items() if k not in ("abstract",)}
    return _j(g)


@mcp.tool()
def florist_direction_action(node_id: str, action: str, note: str = "") -> str:
    """Steer a direction: boost | prune | deepen | restore (also teaches preferences)."""
    return _j(greenhouse.direction_action(node_id, action, note))


@mcp.tool()
def florist_steer(seed: str, note: str) -> str:
    """Leave a steering note for the seed's next round."""
    s = db.get_seed(seed)
    if not s:
        raise ValueError(f"no seed {seed}")
    greenhouse.steer(s.id, note)
    return "ok"


@mcp.tool()
def florist_idea(seed: str, idea: str) -> str:
    """Drop another idea into a seed mid-search; a running loop re-grounds around it."""
    return _j(greenhouse.inject_idea(seed, idea))


@mcp.tool()
def florist_pick(seed: str, adapters: list[str] | None = None, out_dir: str = "",
                 handoff: dict[str, Any] | None = None) -> str:
    """Pick the flower into a flower pack. Pass `handoff` (HandoffPlan JSON from florist_pick_task) to skip the model call."""
    dest = pack.pick(seed, out_dir or None, adapters, handoff=handoff)
    return _j({"path": str(dest), "files": sorted(str(p.relative_to(dest)) for p in dest.rglob("*") if p.is_file())})


@mcp.tool()
def florist_pick_task(seed: str) -> str:
    """The pick step as a task (instructions, context, HandoffPlan schema) for you to answer."""
    return _j(pack.pick_task(seed))


@mcp.tool()
def florist_feed(status: str = "kept", limit: int = 30) -> str:
    """Inspiration feed items (kept by default; or folded, composted, all)."""
    items = db.list_feed(None if status == "all" else status.split(","), limit)
    return _j([i.model_dump(mode="json", exclude={"content"}) for i in items])


@mcp.tool()
def florist_feed_action(item_id: str, action: str, seed: str = "", note: str = "") -> str:
    """compost | attach (with seed) | seed (new seed) | dismiss | keep. Teaches the feed filter."""
    sid = ""
    if seed:
        s = db.get_seed(seed)
        sid = s.id if s else ""
    return _j(feed.act(item_id, action, sid, note))


@mcp.tool()
def florist_save_link(url: str, note: str = "") -> str:
    """Save a link to Florist's feed (summarized, tagged, scored)."""
    return _j(feed.add_link(url, note).model_dump(mode="json"))


@mcp.tool()
def florist_compost(tag: str = "") -> str:
    """The compost pile (optionally filtered by tag)."""
    return _j([c.model_dump() for c in db.list_compost() if not tag or tag.lower() in c.tags])


@mcp.tool()
def florist_compost_add(title: str = "", link: str = "", note: str = "", tags: list[str] | None = None) -> str:
    """Add a link or note to compost."""
    return _j(compost.add(title, link, note, tags or []).model_dump())


@mcp.tool()
def florist_compost_mine() -> str:
    """Ask Florist for connections across the compost → candidate seeds."""
    return _j([s.model_dump(mode="json") for s in compost.mine()])


@mcp.tool()
def florist_profile() -> str:
    """The user's profile (interests, skills, compute, time, learned preferences)."""
    from . import profile

    return _j(profile.load().model_dump(mode="json"))


@mcp.tool()
def florist_record_preference(kind: str, target_kind: str, target_id: str, tags: list[str] | None = None,
                              technologies: list[str] | None = None) -> str:
    """Log a behavioural signal (e.g. kind=boost/dismiss/pick) when the user expresses taste in chat."""
    sig = preferences.record(kind, target_kind, target_id, {"tags": tags or [], "technologies": technologies or []})
    return _j({"signal": sig})


@mcp.tool()
def florist_research(query: str, kind: str = "paper", limit: int = 8) -> str:
    """Search papers / repos / posts through Florist's cached research layer."""
    from . import research

    return _j([h.model_dump() for h in research.search(query, kind=kind, limit=limit)])


def main() -> None:
    config.load()
    db.conn()
    mcp.run()
