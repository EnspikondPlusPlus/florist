"""``florist`` — drive everything from a terminal or a coding agent.

Every command accepts ``--json`` for machine-readable output. See ``SKILL.md`` (``florist skill``)
for how a coding agent should use it.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import webbrowser
from pathlib import Path
from typing import Any, Optional

import typer
from rich.console import Console
from rich.table import Table

from . import __version__, config, gateway, paths, profile as profile_mod, skills

app = typer.Typer(help="Florist grows ideas: feed → compost → greenhouse → exploration loop → flower pack.",
                  no_args_is_help=True, add_completion=False, rich_markup_mode="markdown")
seed_app = typer.Typer(help="Greenhouse seeds.", no_args_is_help=True)
round_app = typer.Typer(help="Agent-driven loop: an external coding agent is the brain.", no_args_is_help=True)
feed_app = typer.Typer(help="Inspiration feed.", no_args_is_help=True)
sources_app = typer.Typer(help="Feed sources.", no_args_is_help=True)
compost_app = typer.Typer(help="Compost pile.", no_args_is_help=True)
profile_app = typer.Typer(help="Your profile (profile.yaml).", no_args_is_help=True)
models_app = typer.Typer(help="Model backends and keys.", no_args_is_help=True)
smoke_app = typer.Typer(help="Smoke checks (run only with your approval).", no_args_is_help=True)
skills_app = typer.Typer(help="Skill files.", no_args_is_help=True)
mcp_app = typer.Typer(help="MCP server for coding agents.", invoke_without_command=True)
for sub, name in ((seed_app, "seed"), (round_app, "round"), (feed_app, "feed"), (sources_app, "sources"),
                  (compost_app, "compost"), (profile_app, "profile"), (models_app, "models"),
                  (smoke_app, "smoke"), (skills_app, "skills"), (mcp_app, "mcp")):
    app.add_typer(sub, name=name)

console = Console(highlight=False)
JSON = typer.Option(False, "--json", help="Machine-readable JSON output.")


def out(obj: Any, as_json: bool, human: Any = None) -> None:
    if as_json or human is None:
        print(json.dumps(obj, indent=2, ensure_ascii=False, default=str))
    elif callable(human):
        human(obj)
    else:
        console.print(human)


def fail(msg: str, code: int = 1) -> None:
    console.print(f"[red]error:[/red] {msg}")
    raise typer.Exit(code)


def _seed(ref: str):
    from .store import db

    s = db.get_seed(ref)
    if not s:
        fail(f"no seed matching '{ref}' (try `florist seed list`)")
    return s


def _read_json(file: str) -> Any:
    raw = sys.stdin.read() if file == "-" else Path(file).read_text(encoding="utf-8")
    return json.loads(raw)


# ---------------------------------------------------------------------------
# Top level
# ---------------------------------------------------------------------------


@app.callback()
def _root(version: bool = typer.Option(False, "--version", help="Show version.")) -> None:
    if version:
        print(__version__)
        raise typer.Exit()
    config.load()


@app.command()
def init(model: str = typer.Option("", help="Default model, e.g. meta/muse-spark-1.3 or claude-code:sonnet"),
         as_json: bool = JSON) -> None:
    """Create ~/.florist (database, profile.yaml, settings.yaml) and starter feed sources."""
    from .ingest import feed
    from .store import db

    db.conn()
    profile_mod.load()
    if model:
        config.update({"models": {"default": model, "fast": model, "strong": model}})
    feed.ensure_starter_sources()
    info = {"home": str(paths.home()), "profile": str(paths.profile_path()), "settings": str(paths.settings_path()),
            "model": config.get().models.default}
    out(info, as_json, f"[green]Florist ready[/green] at {info['home']}\n  profile:  {info['profile']}\n"
                       f"  settings: {info['settings']}\n  model:    {info['model']}\n"
                       "Next: edit your profile (`florist profile edit`), then `florist seed add \"…\"`.")


@app.command()
def status(as_json: bool = JSON) -> None:
    """Overview: models, seeds, feed, compost, spend."""
    from .server import status as st

    s = st()

    def human(s: dict) -> None:
        console.print(f"[bold green]Florist {s['version']}[/bold green]  home: {s['home']}")
        for role, m in s["models"].items():
            mark = "[green]✓[/green]" if m["ready"] else "[red]✗[/red]"
            console.print(f"  {mark} {role:7} {m['model']}  ({m['backend']}: {m['detail']})")
        console.print(f"  seeds: {s['seeds'] or 0}   feed: {s['feed'] or 0}   compost: {s['compost']}"
                      f"   smoke awaiting approval: {s['pending_smoke']}")
        u = s["usage"]
        console.print(f"  usage: {u.get('n', 0)} calls, {u.get('tin', 0) + u.get('tout', 0)} tokens, ${u.get('usd', 0):.4f}")

    out(s, as_json, human)


@app.command()
def up(port: int = typer.Option(0, help="Port (default from settings, 4795)."), host: str = "127.0.0.1",
       open_browser: bool = typer.Option(True, "--open/--no-open")) -> None:
    """Start the local sidecar + dashboard (http://127.0.0.1:4795)."""
    import threading

    import uvicorn

    port = port or config.get().port
    url = f"http://{host}:{port}"
    console.print(f"[green]Florist[/green] dashboard at {url}  (Ctrl+C to stop)")
    if open_browser:
        threading.Timer(1.2, lambda: webbrowser.open(url)).start()
    uvicorn.run("florist.server:app", host=host, port=port, log_level="warning")


@app.command("app")
def desktop(port: int = typer.Option(0, help="Port for the sidecar.")) -> None:
    """Open Florist as a desktop window (pywebview; falls back to an Edge/Chrome app window)."""
    from .desktop import run

    run(port or config.get().port)


@app.command()
def agent(harness: str = typer.Option("claude", help="claude | codex"),
          seed: str = typer.Option("", help="Focus the session on this seed."),
          prompt: str = typer.Option("", help="Initial instruction.")) -> None:
    """Open an interactive Claude Code / Codex session that drives Florist (playbook + CLI skill)."""
    from .harness import launch

    raise typer.Exit(launch(harness, seed, prompt))


@app.command()
def usage(seed: str = typer.Option("", help="Limit to one seed."), as_json: bool = JSON) -> None:
    """Token and cost log per step/model."""
    sid = _seed(seed).id if seed else None
    u = gateway.usage_summary(sid)

    def human(u: dict) -> None:
        t = Table("step", "backend", "model", "calls", "tokens in", "tokens out", "USD", "failed")
        for r in u["by_step"]:
            t.add_row(r["step"], r["backend"], r["model"][:38], str(r["n"]), str(r["tin"]), str(r["tout"]),
                      f"{r['usd'] or 0:.4f}", str(r["failed"]))
        console.print(t)
        tot = u["total"]
        console.print(f"total: {tot.get('n', 0)} calls, ${tot.get('usd', 0):.4f}")

    out(u, as_json, human)


@app.command()
def tick(as_json: bool = JSON, no_feed: bool = typer.Option(False, "--no-feed")) -> None:
    """Do due background work once: fetch feeds, passive growth in downtime, auto-compost, mining."""
    from .agent import scheduler

    out(scheduler.tick(fetch_feed=False if no_feed else None), True)


@app.command()
def deadlines(subject: str = typer.Option("", help="ML, CV, NLP, RO, …"), as_json: bool = JSON) -> None:
    """Upcoming conference deadlines (AI Deadlines API), filtered by your profile targets."""
    from . import deadlines as dl

    items = dl.upcoming([subject]) if subject else dl.for_profile()

    def human(items: list) -> None:
        t = Table("conference", "deadline", "place", "subjects")
        for c in items[:25]:
            t.add_row(f"{c['title']} {c.get('year', '')}", c.get("deadline", ""), c.get("place", ""),
                      ",".join(c.get("sub") or []))
        console.print(t)

    out(items, as_json, human)


@app.command()
def research(query: str, kind: str = typer.Option("paper", help="paper | repo | post"),
             tool: str = typer.Option("", help="Force one tool: alphaxiv, openalex, arxiv, semantic_scholar, "
                                                "github, hackernews, agent_web"),
             since: str = typer.Option("", help="YYYY-MM-DD"), limit: int = 8, as_json: bool = JSON) -> None:
    """Search the research-tool layer (cached, with fallback)."""
    from . import research as r

    hits = r.search(query, kind=kind, limit=limit, since=since or None, tool=tool or None,
                    log=lambda m: console.print(f"[dim]{m}[/dim]"))

    def human(hits: list) -> None:
        for h in hits:
            console.print(f"[bold]{h['title']}[/bold] [dim]({h['tool']}, {h.get('year') or '—'})[/dim]\n  {h['url']}")

    out([h.model_dump() for h in hits], as_json, human)


@app.command()
def skill(name: str = typer.Argument("", help="Skill name; omit for the CLI overview.")) -> None:
    """Print a skill (prompt + rubric) — what a coding agent should read before acting."""
    if not name:
        print(skills.cli_overview())
        print("\n## Bundled skills\n")
        for s in skills.all_skills():
            print(f"- `{s.name}` — {s.description}")
        return
    try:
        s = skills.get(name)
    except KeyError as e:
        fail(str(e))
    print(f"# {s.name}\n\n{s.description}\n\n{skills.shared_preamble()}\n\n{s.body}")


@app.command("schemas")
def schemas_cmd(export: bool = typer.Option(True, "--export/--list")) -> None:
    """Export JSON Schemas for every record and step output into schemas/."""
    from .schemas import RECORDS, STEP_OUTPUTS

    d = paths.schemas_dir()
    d.mkdir(exist_ok=True)
    names = []
    for name, model in {**RECORDS, **{m.__name__: m for m in STEP_OUTPUTS.values()}}.items():
        if export:
            (d / f"{name}.schema.json").write_text(json.dumps(model.model_json_schema(), indent=2) + "\n",
                                                   encoding="utf-8")
        names.append(name)
    console.print(f"{'wrote' if export else 'schemas:'} {len(names)} schemas → {d}")


# ---------------------------------------------------------------------------
# Seeds
# ---------------------------------------------------------------------------


@seed_app.command("add")
def seed_add(prompt: str, tier: str = typer.Option("personal", help="exploration | personal | formal"),
             title: str = "", tech: list[str] = typer.Option([], "--tech", help="Related technology (repeatable)."),
             paper: list[str] = typer.Option([], "--paper", help="Related paper id/URL (repeatable)."),
             compost_id: list[str] = typer.Option([], "--compost", help="Link a compost item (repeatable)."),
             time: str = typer.Option("", help="Time constraint, e.g. '2 weekends'."),
             compute: str = typer.Option("", help="Compute constraint."),
             must_use: list[str] = typer.Option([], "--must-use"),
             must_avoid: list[str] = typer.Option([], "--must-avoid"),
             priority: int = typer.Option(3, min=1, max=5), passive: bool = typer.Option(False, "--passive"),
             ask: bool = typer.Option(False, "--ask", help="Let Florist ask up to two follow-up questions."),
             as_json: bool = JSON) -> None:
    """Plant a seed from a short prompt."""
    from .agent import greenhouse

    seed, questions = greenhouse.create_seed(
        prompt, tier=tier, title=title, technologies=tech, related_papers=paper, compost_ids=compost_id,
        constraints={"time": time, "compute": compute, "must_use": must_use, "must_avoid": must_avoid},
        priority=priority, ask_followups=ask, passive=passive)
    res = {"seed": seed.model_dump(mode="json"), "questions": questions}
    human = f"[green]planted[/green] {seed.slug} ({seed.id}, {seed.tier.value})"
    if questions:
        human += "\nFlorist asks:\n" + "\n".join(f"  {i + 1}. {q}" for i, q in enumerate(questions))
        human += f"\nAnswer with: florist seed answer {seed.slug} \"…\" \"…\""
    out(res, as_json, human)


@seed_app.command("list")
def seed_list(all: bool = typer.Option(False, "--all", help="Include candidates and composted."),
              as_json: bool = JSON) -> None:
    """Seeds by tier and state."""
    from .server import list_seeds

    seeds = list_seeds(all=all)

    def human(seeds: list) -> None:
        t = Table("slug", "tier", "state", "prio", "rounds", "flower", "$")
        for s in seeds:
            fl = f"v{s['flower']['version']} ({s['flower']['stability']:.2f})" if s["flower"] else "—"
            t.add_row(s["slug"], s["tier"], s["state"] + (" ⟳" if s["run"] else ""), str(s["priority"]),
                      str(s["rounds_done"]), fl, f"{s['usd']:.3f}")
        console.print(t)

    out(seeds, as_json, human)


@seed_app.command("show")
def seed_show(ref: str, as_json: bool = JSON) -> None:
    """Seed details, flower summary and current run."""
    from .server import get_seed

    s = get_seed(_seed(ref).id)

    def human(s: dict) -> None:
        console.print(f"[bold]{s['title']}[/bold]  [dim]{s['slug']} · {s['id']} · {s['tier']} · {s['state']}[/dim]")
        console.print(s["prompt"])
        if s["flower"]:
            console.print(f"\n[green]Flower v{s['flower']['version']}[/green] stability {s['flower']['stability']:.2f}")
            for d in s["flower"]["directions"]:
                console.print(f"  → {d}")
        if s["run"]:
            console.print(f"\nrun {s['run']['id']}: {s['run']['status']} at {s['run']['step']} (round {s['run']['round']})")

    out(s, as_json, human)


@seed_app.command("edit")
def seed_edit(ref: str, set_: list[str] = typer.Option([], "--set", help="field=value (e.g. tier=formal, "
                                                                          "constraints.compute='1x 4090')"),
              as_json: bool = JSON) -> None:
    """Edit seed fields."""
    from .agent import greenhouse

    patch: dict[str, Any] = {}
    for kv in set_:
        k, _, v = kv.partition("=")
        try:
            val: Any = json.loads(v)
        except json.JSONDecodeError:
            val = v
        if "." in k:
            a, b = k.split(".", 1)
            patch.setdefault(a, {})[b] = val
        else:
            patch[k] = val
    s = greenhouse.update_seed(_seed(ref).id, patch)
    out(s.model_dump(mode="json"), as_json, f"updated {s.slug}")


@seed_app.command("answer")
def seed_answer(ref: str, answers: list[str]) -> None:
    """Answer Florist's follow-up questions."""
    from .agent import greenhouse

    s = greenhouse.answer_followups(_seed(ref).id, answers)
    console.print(f"saved {len(answers)} answer(s) for {s.slug}")


@seed_app.command("state")
def seed_state(ref: str, state: str) -> None:
    """Set state: dormant | growing | flowering | picked."""
    from .agent import greenhouse

    s = greenhouse.set_state(_seed(ref).id, state)
    console.print(f"{s.slug} → {s.state.value}")


@seed_app.command("priority")
def seed_priority(ref: str, priority: int = typer.Argument(..., min=1, max=5)) -> None:
    """Set priority 1 (lowest) … 5. Seeds at 1 for too long fall into compost."""
    from .agent import greenhouse

    s = greenhouse.update_seed(_seed(ref).id, {"priority": priority})
    console.print(f"{s.slug} priority {s.priority}")


@seed_app.command("compost")
def seed_compost(ref: str, reason: str = "moved to compost by you") -> None:
    """Move a seed to compost (kept, not lost)."""
    from .agent import greenhouse

    c = greenhouse.compost_seed(_seed(ref).id, reason)
    console.print(f"composted as {c.id}")


@seed_app.command("delete")
def seed_delete(ref: str, yes: bool = typer.Option(False, "--yes")) -> None:
    """Delete a seed and its whole exploration graph."""
    from .store import db

    s = _seed(ref)
    if not yes and not typer.confirm(f"Delete {s.slug} and everything explored for it?"):
        raise typer.Exit(1)
    db.delete_seed(s.id)
    console.print(f"deleted {s.slug}")


# ---------------------------------------------------------------------------
# Loop
# ---------------------------------------------------------------------------


@app.command()
def grow(ref: str, rounds: int = typer.Option(1, min=1, max=10),
         model: str = typer.Option("", help="Override the model for this run."), as_json: bool = JSON) -> None:
    """Grow a seed with Florist's own loop (API model or Claude Code/Codex subscription)."""
    from .agent import loop
    from .store import db

    seed = _seed(ref)
    last = [0]

    def show_progress() -> None:
        for a in db.activity_since(last[0]):
            last[0] = a["id"]
            if a["seed_id"] == seed.id and not as_json:
                console.print(f"[dim]{a['created'][11:19]}[/dim] {a['message']}")

    import threading

    stop = threading.Event()

    def pump() -> None:
        while not stop.wait(0.5):
            show_progress()

    row = db.q1("SELECT COALESCE(MAX(id),0) m FROM activity")
    last[0] = row["m"] if row else 0
    t = threading.Thread(target=pump, daemon=True)
    t.start()
    try:
        res = loop.grow(seed.id, rounds=rounds, model=model or None)
    except loop.RunBusy as e:
        stop.set()
        fail(str(e))
    finally:
        stop.set()
        t.join(1)
        show_progress()
    out(res, as_json, f"[green]{res['status']}[/green]: {res['reason']} (round {res['round']}, ${res['usd']:.4f})")


@app.command()
def stop(ref: str) -> None:
    """Stop a seed's running loop after the current step."""
    from .agent import loop

    console.print("stop requested" if loop.request_stop(_seed(ref).id) else "nothing running")


@round_app.command("start")
def round_start(ref: str, rounds: int = typer.Option(1, min=1, max=10), as_json: bool = typer.Option(True, "--json/--text")) -> None:
    """Start an agent-driven run and print the first task (skill + context + schema)."""
    from .agent import loop

    ctx = loop.start(_seed(ref).id, rounds, "agent")
    _print_task(loop.next_task(run_id=ctx.run_id), as_json)


@round_app.command("next")
def round_next(ref: str, as_json: bool = typer.Option(True, "--json/--text")) -> None:
    """Print the pending task for an agent-driven run."""
    from .agent import loop

    try:
        _print_task(loop.next_task(_seed(ref).id), as_json)
    except KeyError as e:
        fail(str(e).strip("'\""))


@round_app.command("submit")
def round_submit(ref: str, file: str = typer.Option("-", "--file", "-f", help="JSON file with the step output, or - for stdin."),
                 as_json: bool = typer.Option(True, "--json/--text")) -> None:
    """Validate and apply the agent's output for the pending step; prints the next task."""
    from .agent import loop

    res = loop.submit(_seed(ref).id, _read_json(file))
    if as_json:
        print(json.dumps(res, indent=1, ensure_ascii=False, default=str))
    else:
        if not res["accepted"]:
            console.print(f"[red]rejected[/red] {res['step']}: {res['error']}")
        else:
            console.print(f"[green]accepted[/green] {res['step']}")
            _print_task(res["next"], False)


def _print_task(task: dict, as_json: bool) -> None:
    if as_json:
        print(json.dumps(task, indent=1, ensure_ascii=False, default=str))
        return
    if "step" not in task or "instructions" not in task:
        console.print(f"run {task.get('run_id')}: {task.get('status')} — {task.get('reason', '')}")
        return
    console.print(f"[bold]Round {task['round']} · step {task['step']}[/bold] (skill {task['skill']}, "
                  f"output {task['output_schema']})")
    console.print(task["instructions"])
    console.print("\n## Context\n" + json.dumps(task["context"], indent=1, ensure_ascii=False))
    console.print(f"\nSubmit with: {task['submit']}")


@round_app.command("status")
def round_status(ref: str, as_json: bool = JSON) -> None:
    """Runs for a seed."""
    from .agent import loop

    runs = loop.list_runs(_seed(ref).id, 10)
    for r in runs:
        r["state"] = {k: v for k, v in r["state"].items() if k != "pending"}
    out(runs, as_json, lambda rs: [console.print(
        f"{r['id']} {r['mode']:7} {r['status']:8} round {r['round']} step {r['step'] or '—'} {r['error'][:60]}")
        for r in rs])


@app.command()
def graph(ref: str, mermaid: bool = typer.Option(False, "--mermaid"), as_json: bool = JSON) -> None:
    """The exploration graph (nodes and edges, or Mermaid)."""
    from .server import graph as g

    data = g(_seed(ref).id)
    if mermaid:
        print(data["mermaid"])
        return

    def human(d: dict) -> None:
        for n in d["nodes"]:
            dim = "[dim]" if n["status"] == "pruned" else ""
            console.print(f"{dim}{n['kind']:10} {n['status']:7} {n['id']:14} {n['title'][:70]}"
                          + (f"  ({n['score']:.2f})" if n.get("score") is not None else ""))

    out(data, as_json, human)


@app.command()
def flower(ref: str, as_json: bool = JSON) -> None:
    """The current flower: findings with evidence, directions, risks, first steps."""
    from .server import flower as fl

    data = fl(_seed(ref).id)
    if not data["flower"]:
        fail("no flower yet — run `florist grow`")

    def human(d: dict) -> None:
        f, refs = d["flower"], d["refs"]
        console.print(f"[bold green]Flower v{f['version']}[/bold green] (round {f['round']}, stability {f['stability']:.2f})")
        console.print(f["idea"] + "\n")
        console.print("[bold]Findings[/bold]")
        for i, x in enumerate(f["findings"], 1):
            cites = "; ".join(refs.get(e["ref"], {}).get("title", e["ref"])[:60] for e in x["evidence"])
            console.print(f" {i}. {x['text']}\n    [dim]↳ {cites}[/dim]")
        console.print("[bold]Directions[/bold]")
        for d_ in f["directions"]:
            console.print(f" → [bold]{d_['title']}[/bold]: {d_['pitch']}")
        if f["novelty"]["gap"]:
            console.print(f"[bold]Gap[/bold] {f['novelty']['gap']}")
        for s in f["first_steps"]:
            console.print(f" □ {s}")

    out(data, as_json, human)


@app.command()
def direction(action: str = typer.Argument(..., help="boost | prune | deepen | restore"), node: str = typer.Argument(...),
              note: str = typer.Option("", help="Reason / what to dig into.")) -> None:
    """Steer a direction node (teaches your preferences too)."""
    from .agent import greenhouse

    n = greenhouse.direction_action(node, action, note)
    console.print(f"{action}: {n['title']} → {n['status']}")


@app.command()
def steer(ref: str, note: str) -> None:
    """Leave a steering note for the next round."""
    from .agent import greenhouse

    greenhouse.steer(_seed(ref).id, note)
    console.print("noted for the next round")


@app.command()
def idea(ref: str, text: str) -> None:
    """Drop another idea into a seed mid-search (a running loop re-grounds around it)."""
    from .agent import greenhouse

    res = greenhouse.inject_idea(_seed(ref).id, text)
    console.print("folded into the running exploration" if res["applied"] == "live" else "saved for the next round")


@app.command()
def chat(ref: str, message: str, as_json: bool = JSON) -> None:
    """Talk to Florist about a seed (live mode); steering becomes actions."""
    from .agent import greenhouse

    res = greenhouse.chat(_seed(ref).id, message)
    out(res, as_json, lambda r: (console.print(r["reply"]),
                                 [console.print(f"[dim]action: {a['type']} {a['target']} {a['note']}[/dim]")
                                  for a in r["actions"]]))


@app.command()
def pick(ref: str, out_dir: str = typer.Option("", "--out", help="Write the pack here (default ~/.florist/packs)."),
         adapter: list[str] = typer.Option([], "--adapter", help="openresearch | coscientist | build_plan | coding_agent"),
         prepare: bool = typer.Option(False, "--prepare", help="Print the pick task for a coding agent instead."),
         handoff: str = typer.Option("", "--handoff", help="Use this HandoffPlan JSON (from --prepare) instead of a model call."),
         as_json: bool = JSON) -> None:
    """Pick a flower: write the flower pack with adapters."""
    from .agent import pack as pk

    seed = _seed(ref)
    if prepare:
        print(json.dumps(pk.pick_task(seed.id), indent=1, ensure_ascii=False, default=str))
        return
    dest = pk.pick(seed.id, out_dir or None, adapter or None, handoff=_read_json(handoff) if handoff else None)
    files = sorted(str(p.relative_to(dest)).replace("\\", "/") for p in dest.rglob("*") if p.is_file())
    out({"path": str(dest), "files": files}, as_json,
        f"[green]picked[/green] → {dest}\n" + "\n".join(f"  {f}" for f in files))


# ---------------------------------------------------------------------------
# Smoke
# ---------------------------------------------------------------------------


@smoke_app.command("list")
def smoke_list(ref: str = typer.Argument("", help="Seed (optional)."), as_json: bool = JSON) -> None:
    from .store import db

    items = db.list_smoke(_seed(ref).id if ref else None)
    out([s.model_dump(exclude={"stdout", "stderr"}) for s in items], as_json,
        lambda xs: [console.print(f"{x['id']} {x['status']:9} {x['assumption'][:80]}") for x in xs])


@smoke_app.command("show")
def smoke_show(smoke_id: str) -> None:
    from .store import db

    s = db.get_smoke(smoke_id)
    if not s:
        fail("no such smoke check")
    console.print(f"[bold]{s.assumption}[/bold] — {s.status}\n{s.rationale}\nexpected: {s.expected}\n")
    print(s.code)
    if s.stdout:
        console.print(f"\n[dim]stdout:[/dim]\n{s.stdout[-2000:]}")


@smoke_app.command("run")
def smoke_run(smoke_id: str, yes: bool = typer.Option(False, "--yes", help="Approve without prompting.")) -> None:
    """Run a smoke check — shows the code and asks for approval first."""
    from .agent import smoke as sm
    from .store import db

    s = db.get_smoke(smoke_id)
    if not s:
        fail("no such smoke check")
    if not yes:
        console.print(f"[bold]{s.assumption}[/bold] (timeout {s.timeout_s}s)\n")
        print(s.code)
        if not typer.confirm("\nRun this code locally?"):
            raise typer.Exit(1)
    r = sm.run(smoke_id, approved=True)
    console.print(f"{r.status}: {r.verdict}")


@smoke_app.command("reject")
def smoke_reject(smoke_id: str) -> None:
    from .agent import smoke as sm

    console.print(sm.reject(smoke_id).status)


# ---------------------------------------------------------------------------
# Feed & sources
# ---------------------------------------------------------------------------


@feed_app.command("list")
def feed_list(status: str = typer.Option("kept", help="kept,folded,composted,… or all"), limit: int = 40,
              as_json: bool = JSON) -> None:
    from .store import db

    items = db.list_feed(None if status == "all" else status.split(","), limit)

    def human(items: list) -> None:
        for i in items:
            console.print(f"[bold]{i['title'][:90]}[/bold] [dim]{i['id']} · {i['source_name'] or i['source_kind']} · "
                          f"{i['score']:.2f}[/dim]\n  {i['summary'][:200]}\n  [green]{i['why']}[/green]")

    out([i.model_dump(mode="json") for i in items], as_json, human)


@feed_app.command("fetch")
def feed_fetch(source: str = typer.Option("", help="Only this source id."), as_json: bool = JSON) -> None:
    from .ingest import feed

    feed.ensure_starter_sources()
    out(feed.fetch(source or None, force=True), True)


@feed_app.command("add")
def feed_add(url: str, note: str = "", as_json: bool = JSON) -> None:
    """Save a link to Florist (summarized, tagged, scored)."""
    from .ingest import feed

    it = feed.add_link(url, note)
    out(it.model_dump(mode="json"), as_json, f"saved {it.id}: {it.title}\n  {it.why}")


@feed_app.command("act")
def feed_act(item_id: str, action: str = typer.Argument(..., help="compost | attach | seed | dismiss | keep | unfold"),
             seed: str = typer.Option("", help="Seed for attach."), note: str = "", as_json: bool = JSON) -> None:
    from .ingest import feed

    sid = _seed(seed).id if seed else ""
    out(feed.act(item_id, action, sid, note), as_json, f"{action} ✓")


@sources_app.command("list")
def sources_list(as_json: bool = JSON) -> None:
    from .ingest import feed
    from .store import db

    feed.ensure_starter_sources()
    out([s.model_dump() for s in db.list_sources()], as_json,
        lambda xs: [console.print(f"{'●' if x['enabled'] else '○'} {x['id']:22} {x['kind']:8} {x['name']}  "
                                  f"[dim]{json.dumps(x['config'])} {x['last_error'][:50]}[/dim]") for x in xs])


@sources_app.command("add")
def sources_add(kind: str = typer.Argument(..., help="rss | youtube | arxiv | alphaxiv | github | hn | email"),
                name: str = typer.Argument(...),
                cfg: list[str] = typer.Option([], "--set", help="key=value, e.g. url=https://… or channel_id=UC…"),
                interval: float = 6.0) -> None:
    from .schemas import FeedSource
    from .store import db

    s = FeedSource(id=db.new_id("src"), kind=kind, name=name,  # type: ignore[arg-type]
                   config=dict(kv.split("=", 1) for kv in cfg), interval_hours=interval)
    db.put_source(s)
    console.print(f"added {s.id}")


@sources_app.command("remove")
def sources_remove(source_id: str) -> None:
    from .store import db

    db.delete_source(source_id)
    console.print("removed")


# ---------------------------------------------------------------------------
# Compost
# ---------------------------------------------------------------------------


@compost_app.command("list")
def compost_list(tag: str = "", as_json: bool = JSON) -> None:
    from .store import db

    items = [c for c in db.list_compost() if not tag or tag.lower() in c.tags]
    out([c.model_dump() for c in items], as_json,
        lambda xs: [console.print(f"{x['id']} [bold]{x['title'][:70]}[/bold] [dim]{x['date']} · {', '.join(x['tags'][:4])}"
                                  f"{' · ' + x['cluster'] if x['cluster'] else ''}[/dim]") for x in xs])


@compost_app.command("add")
def compost_add(title: str = "", link: str = "", note: str = "", tag: list[str] = typer.Option([], "--tag"),
                as_json: bool = JSON) -> None:
    """Add a link or note by hand."""
    from .agent import compost

    c = compost.add(title, link, note, tag)
    out(c.model_dump(), as_json, f"composted {c.id}: {c.title}")


@compost_app.command("edit")
def compost_edit(item_id: str, set_: list[str] = typer.Option([], "--set", help="field=value (JSON for lists)")) -> None:
    from .agent import compost

    patch = {}
    for kv in set_:
        k, _, v = kv.partition("=")
        try:
            patch[k] = json.loads(v)
        except json.JSONDecodeError:
            patch[k] = v
    console.print(compost.update(item_id, patch).title)


@compost_app.command("clusters")
def compost_clusters(refresh: bool = typer.Option(True, "--refresh/--cached"), as_json: bool = JSON) -> None:
    from .agent import compost

    cl = compost.clusters() if refresh else compost.cached_clusters()
    out(cl, as_json, lambda cs: [console.print(f"[bold]{c['label']}[/bold] ({len(c['items'])}): "
                                               + "; ".join(t[:40] for t in c["titles"][:4])) for c in cs])


@compost_app.command("mine")
def compost_mine(prepare: bool = typer.Option(False, "--prepare", help="Print the mining task for a coding agent."),
                 submit: str = typer.Option("", "--submit", help="Apply a MiningOutput JSON file (or -)."),
                 as_json: bool = JSON) -> None:
    """Ask Florist for connections across the compost pile → candidate seeds."""
    from .agent import compost
    from .schemas import MiningOutput

    if prepare:
        print(json.dumps({"skill": "florist-mining", "instructions": skills.system_prompt("mining"),
                          "context": compost.mining_task(), "schema": gateway.inline_schema(MiningOutput)},
                         indent=1, ensure_ascii=False))
        return
    seeds = compost.apply_mining(MiningOutput.model_validate(_read_json(submit))) if submit else compost.mine()
    out([s.model_dump(mode="json") for s in seeds], as_json,
        lambda xs: [console.print(f"candidate {x['slug']}: {x['title']}") for x in xs] or console.print("no candidates"))


@compost_app.command("seed")
def compost_seed(ids: list[str], prompt: str = "", tier: str = "exploration", title: str = "") -> None:
    """Start a seed from these compost items."""
    from .agent import compost

    s = compost.seed_from(ids, prompt, tier, title)
    console.print(f"planted {s.slug}")


@compost_app.command("accept")
def compost_accept(ref: str) -> None:
    """Accept a mined candidate seed into the greenhouse."""
    from .agent import compost

    console.print(f"accepted {compost.accept_candidate(_seed(ref).id).slug}")


@compost_app.command("reject")
def compost_reject(ref: str) -> None:
    from .agent import compost

    compost.reject_candidate(_seed(ref).id)
    console.print("rejected")


# ---------------------------------------------------------------------------
# Profile
# ---------------------------------------------------------------------------


@profile_app.command("show")
def profile_show(as_json: bool = JSON) -> None:
    p = profile_mod.load()
    out(p.model_dump(mode="json"), as_json, lambda _: print(paths.profile_path().read_text(encoding="utf-8")))


@profile_app.command("path")
def profile_path() -> None:
    print(paths.profile_path())


@profile_app.command("edit")
def profile_edit() -> None:
    """Open profile.yaml in your editor."""
    profile_mod.load()
    p = str(paths.profile_path())
    editor = os.environ.get("EDITOR") or ("notepad" if os.name == "nt" else "nano")
    subprocess.call([editor, p])
    profile_mod.load()  # validate
    console.print("profile ok")


@profile_app.command("set")
def profile_set(key: str, value: str) -> None:
    """Set a knob: `florist profile set interests '["robotics","rust"]'` or `resources.compute "1x 4090"`."""
    try:
        val: Any = json.loads(value)
    except json.JSONDecodeError:
        val = value
    data = profile_mod.load().model_dump(mode="json")
    cur = data
    parts = key.split(".")
    for p in parts[:-1]:
        cur = cur[p]
    cur[parts[-1]] = val
    profile_mod.update(data)
    console.print(f"{key} = {json.dumps(val)}")


@profile_app.command("export")
def profile_export(dest: Path) -> None:
    console.print(f"exported → {profile_mod.export_to(dest)}")


@profile_app.command("import")
def profile_import(src: Path) -> None:
    profile_mod.import_from(src)
    console.print("imported")


@profile_app.command("learn")
def profile_learn(prepare: bool = typer.Option(False, "--prepare"), submit: str = typer.Option("", "--submit"),
                  as_json: bool = JSON) -> None:
    """Distill behaviour into learned preference statements (written to profile.yaml)."""
    from .agent import preferences
    from .schemas import PreferenceDistill

    if prepare:
        print(json.dumps({"skill": "florist-taste", "instructions": skills.system_prompt("taste"),
                          "context": preferences.distill_task(), "schema": gateway.inline_schema(PreferenceDistill)},
                         indent=1, ensure_ascii=False))
        return
    learned = (preferences.apply_distill(PreferenceDistill.model_validate(_read_json(submit))) if submit
               else preferences.distill())
    out([lp.model_dump() for lp in learned], as_json,
        lambda xs: [console.print(f"{x['weight']:+.2f} {x['key']}") for x in xs] or console.print("not enough behaviour yet"))


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------


@models_app.command("show")
def models_show(as_json: bool = JSON) -> None:
    s = config.get().models
    data = {r: gateway.check_backend(getattr(s, r)) for r in ("default", "fast", "strong")}
    out(data, as_json, lambda d: [console.print(f"{'✓' if v['ready'] else '✗'} {k:7} {v['model']} — {v['detail']}")
                                  for k, v in d.items()])


@models_app.command("set")
def models_set(model: str, role: str = typer.Option("all", help="all | default | fast | strong")) -> None:
    """Choose models: `meta/muse-spark-1.3`, `meta/muse-wonder-1.0`, `claude-code:sonnet`, `codex:gpt-5`, `anthropic/…`, `ollama/…`, `mock`."""
    roles = ["default", "fast", "strong"] if role == "all" else [role]
    config.update({"models": {r: model for r in roles}})
    console.print(f"{', '.join(roles)} → {model}")


@models_app.command("key")
def models_key(provider: str = typer.Argument(..., help="meta | anthropic | openai | github | imap | …"),
               key: str = typer.Argument(..., help="API key ('' to remove)")) -> None:
    """Store a BYOK key in settings.yaml (environment variables take precedence)."""
    keys = dict(config.get().keys)
    if key:
        keys[provider] = key
    else:
        keys.pop(provider, None)
    config.update({"keys": keys})
    console.print(f"{provider} key {'saved' if key else 'removed'}")


@models_app.command("test")
def models_test(model: str = typer.Option("", help="Model to test (default: settings default).")) -> None:
    """Make one tiny structured call to check the backend works."""
    from .schemas import Model

    class Ping(Model):
        ok: bool
        word: str

    m = model or config.get().models.default
    res = gateway.complete(gateway.Call(step="ping", model=m), "Reply in JSON.",
                           "Return ok=true and a single word describing flowers.", Ping)
    console.print(f"[green]✓[/green] {m}: {res.model_dump()}")


# ---------------------------------------------------------------------------
# Skills, MCP
# ---------------------------------------------------------------------------


@skills_app.command("list")
def skills_list(as_json: bool = JSON) -> None:
    data = [{"name": s.name, "description": s.description, "agent": s.agent_facing} for s in skills.all_skills()]
    out(data, as_json, lambda xs: [console.print(f"{'★' if x['agent'] else ' '} {x['name']:22} {x['description'][:90]}")
                                   for x in xs])


@skills_app.command("install")
def skills_install(target: str = typer.Option("claude", help="claude (~/.claude/skills) | codex | project"),
                   project: Path = typer.Option(None, help="Project dir for target=project.")) -> None:
    """Install Florist's agent-facing skills into a coding agent."""
    for p in skills.install(target, project):
        console.print(f"  {p}")


@mcp_app.callback()
def mcp(ctx: typer.Context) -> None:
    """Run the MCP server over stdio (for Claude Code, Codex, Cursor …)."""
    if ctx.invoked_subcommand is None:
        from .mcp_server import main as mcp_main

        mcp_main()


@mcp_app.command("install")
def mcp_install(scope: str = typer.Option("user", help="user | project | local"),
                harness: str = typer.Option("claude", help="claude | codex")) -> None:
    """Register `florist mcp` with Claude Code (`claude mcp add`) or print the Codex config."""
    exe = gateway.find_binary("florist") or sys.argv[0]
    if harness == "claude":
        claude = gateway.find_binary("claude")
        if not claude:
            fail("claude CLI not found")
        cmd = [claude, "mcp", "add", "--scope", scope, "florist", "--", exe, "mcp"]
        console.print(" ".join(cmd))
        raise typer.Exit(subprocess.call(cmd))
    console.print(f'Add to ~/.codex/config.toml:\n\n[mcp_servers.florist]\ncommand = "{exe}"\nargs = ["mcp"]\n')


def main() -> None:
    if os.name == "nt":
        try:
            sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
        except Exception:
            pass
    app()


if __name__ == "__main__":
    main()
