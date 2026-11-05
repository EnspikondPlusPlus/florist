"""Picking: flower → flower pack (spec section 7).

::

    flower-<slug>/
      flower.md   flower.json   sources.json   pruned.json
      visuals/    smoke/        adapters/<destination>/...

Adapters are Jinja templates in ``adapters/<name>/`` described by ``adapter.yaml``, so adding a
destination is adding files, not code.
"""

from __future__ import annotations

import json
import re
import shutil
from pathlib import Path
from typing import Any

import yaml
from jinja2 import Environment, FileSystemLoader, StrictUndefined

from .. import __version__, gateway, paths, profile, skills
from ..schemas import (
    FlowerPack,
    HandoffPlan,
    NodeStatus,
    PackSource,
    PrunedBranch,
    Scores,
    SeedState,
    now_iso,
)
from ..store import db
from . import loop, preferences, visuals


def list_adapters() -> list[dict[str, Any]]:
    out = []
    for f in sorted(paths.adapters_dir().glob("*/adapter.yaml")):
        meta = yaml.safe_load(f.read_text(encoding="utf-8")) or {}
        meta["name"] = f.parent.name
        out.append(meta)
    return out


def pick_task(seed_ref: str) -> dict[str, Any]:
    seed = db.get_seed(seed_ref)
    if not seed:
        raise KeyError(f"no seed {seed_ref}")
    flower = db.latest_flower(seed.id)
    if not flower:
        raise ValueError("this seed has no flower yet — grow it first")
    tops = [d for d in db.list_nodes(seed.id, "direction") if d.id in {x.node_id for x in flower.directions}]
    context = {
        "seed": loop._seed_brief(seed), "profile": profile.brief(),
        "flower": flower.model_dump(exclude={"visuals", "schema_version"}),
        "directions": [loop._dir_brief(d, True) for d in tops],
        "sources": [loop._src_brief(s) for s in loop._kept_sources(seed.id, 14)],
        "smoke_results": [{"id": s.id, "assumption": s.assumption, "status": s.status, "metrics": s.metrics}
                          for s in db.list_smoke(seed.id) if s.status in ("passed", "failed")],
        "steering": loop._steering(seed.id),
    }
    return {"step": "pick", "skill": "florist-pick", "instructions": skills.system_prompt("pick"),
            "context": context, "schema": gateway.inline_schema(HandoffPlan)}


def pick(seed_ref: str, out_dir: str | Path | None = None, adapters: list[str] | None = None,
         handoff: HandoffPlan | dict | None = None, model: str | None = None) -> Path:
    seed = db.get_seed(seed_ref)
    if not seed:
        raise KeyError(f"no seed {seed_ref}")
    flower = db.latest_flower(seed.id)
    if not flower:
        raise ValueError("this seed has no flower yet — grow it first")
    if handoff is None:
        task = pick_task(seed.id)
        handoff = gateway.complete(
            gateway.Call(step="pick", seed_id=seed.id, model=model, hints={"topic": seed.title[:40]}),
            task["instructions"], loop.render_context(task["context"]), HandoffPlan,
        )
    elif isinstance(handoff, dict):
        handoff = HandoffPlan.model_validate(handoff)

    nodes = db.list_nodes(seed.id)
    by_id = {n.id: n for n in nodes}
    cited = {e.ref for f in flower.findings for e in f.evidence} | {c.ref for c in flower.novelty.closest_work}
    sources = [n for n in nodes if n.kind.value == "source" and (n.status != NodeStatus.pruned or n.id in cited)]
    directions = [n for n in nodes if n.kind.value == "direction"]
    prof = profile.load()
    pack = FlowerPack(
        florist_version=__version__, slug=seed.slug, seed=seed,
        constraints_snapshot={"seed": seed.constraints.model_dump(), "compute": prof.resources.compute,
                              "budget_usd_month": prof.resources.budget_usd_month,
                              "hours_per_week": prof.time.hours_per_week, "goal_date": prof.time.goal_date,
                              "proficient_in": prof.proficient_in, "wants_to_learn": prof.wants_to_learn,
                              "work_preferences": prof.work_preferences},
        flower=flower, handoff=handoff, directions=directions,
        sources=[PackSource(id=s.id, title=s.title, url=s.url, kind=s.data.get("kind", ""), year=s.data.get("year"),
                            summary=s.summary or (s.data.get("abstract") or "")[:300], tool=s.data.get("tool", ""))
                 for s in sorted(sources, key=lambda s: (s.id not in cited, -(s.score or 0)))],
        pruned=[PrunedBranch(id=d.id, title=d.title, summary=d.data.get("description", d.summary), reason=d.reason,
                             round=d.round, scores=Scores(**{k: v for k, v in d.data["scores"].items()
                                                             if k in Scores.model_fields}) if d.data.get("scores") else None)
                for d in directions if d.status == NodeStatus.pruned],
        visuals=db.list_visuals(seed.id), smoke=db.list_smoke(seed.id),
        cost={"usd": round(gateway.spent(seed_id=seed.id), 4),
              "tokens": int((db.q1("SELECT COALESCE(SUM(input_tokens+output_tokens),0) t FROM llm_calls WHERE seed_id=?",
                                   (seed.id,)) or {"t": 0})["t"])},
    )
    root = Path(out_dir) if out_dir else paths.sub("packs")
    dest = root / f"flower-{seed.slug}"
    if dest.exists():
        shutil.rmtree(dest)
    (dest / "visuals").mkdir(parents=True)
    (dest / "smoke").mkdir()
    (dest / "adapters").mkdir()

    vdir = visuals.seed_dir(seed.id)
    (vdir / "graph.mmd").write_text(visuals.graph_mermaid(seed.id), encoding="utf-8")
    for f in vdir.iterdir():
        if f.is_file():
            shutil.copyfile(f, dest / "visuals" / f.name)
    for s in pack.smoke:
        sd = dest / "smoke" / s.id
        sd.mkdir()
        (sd / "check.py").write_text(s.code, encoding="utf-8")
        (sd / "result.json").write_text(s.model_dump_json(indent=2, exclude={"code"}), encoding="utf-8")

    ctx = template_context(pack, by_id)
    env = _env()
    titles = {n.id: n.title for n in nodes} | {s.id: f"smoke check: {s.assumption}" for s in pack.smoke}
    (dest / "flower.json").write_text(pack.model_dump_json(indent=2), encoding="utf-8")
    (dest / "sources.json").write_text(json.dumps([s.model_dump() for s in pack.sources], indent=2), encoding="utf-8")
    (dest / "pruned.json").write_text(json.dumps([p.model_dump() for p in pack.pruned], indent=2), encoding="utf-8")

    chosen = adapters or [a["name"] for a in list_adapters() if a.get("default", True)]
    for meta in list_adapters():
        if meta["name"] not in chosen:
            continue
        adir = dest / "adapters" / meta["name"]
        adir.mkdir()
        for out in meta.get("outputs", []):
            text = humanize(env.get_template(f"{meta['name']}/{out['template']}").render(**ctx), titles)
            (adir / out["path"]).write_text(text, encoding="utf-8")
        pack.adapters.append(meta["name"])
    (dest / "flower.json").write_text(pack.model_dump_json(indent=2), encoding="utf-8")
    (dest / "flower.md").write_text(humanize(env.get_template("_pack/flower.md.j2").render(**ctx), titles), encoding="utf-8")

    seed.state = SeedState.picked
    db.put_seed(seed)
    db.ex("INSERT OR REPLACE INTO packs(seed_id, path, created) VALUES (?,?,?)", (seed.id, str(dest), now_iso()))
    preferences.record("pick", "seed", seed.id, preferences.features_of(seed))
    db.log_activity("pick", f"Picked “{seed.title}” → {dest}", seed.id, {"path": str(dest)})
    return dest


_ID = re.compile(r"(?<![/\w`])((?:src|chk|smk|dir|fnd|tech)_[0-9a-f]{8})(?![\w/`])")


def humanize(text: str, titles: dict[str, str]) -> str:
    """Replace raw node ids in prose with short quoted titles (ids in paths / code spans are kept)."""
    def rep(m: re.Match) -> str:
        t = titles.get(m.group(1))
        if not t:
            return m.group(1)
        t = t if len(t) <= 60 else t[:59].rstrip() + "…"
        return f"“{t}”"
    return _ID.sub(rep, text)


def _env() -> Environment:
    env = Environment(loader=FileSystemLoader(str(paths.adapters_dir())), undefined=StrictUndefined,
                      trim_blocks=True, lstrip_blocks=True, keep_trailing_newline=True)
    env.filters["pct"] = lambda v: f"{float(v) * 100:.0f}%"
    env.filters["f2"] = lambda v: f"{float(v):.2f}"
    return env


def template_context(pack: FlowerPack, by_id: dict[str, Any]) -> dict[str, Any]:
    srcs = {s.id: s for s in pack.sources}

    def cite(ref: str) -> str:
        s = srcs.get(ref)
        if s:
            return f"[{s.title}]({s.url})" if s.url else s.title
        n = by_id.get(ref)
        if n is not None:
            return f"{n.title} ({ref})"
        sm = next((x for x in pack.smoke if x.id == ref), None)
        return f"smoke check: {sm.assumption} — {sm.status}" if sm else ref

    top_ids = [d.node_id for d in pack.flower.directions if d.node_id]
    top_nodes = [by_id[i] for i in top_ids if i in by_id]
    return {
        "pack": pack, "seed": pack.seed, "flower": pack.flower, "handoff": pack.handoff,
        "constraints": pack.constraints_snapshot, "sources": pack.sources, "pruned": pack.pruned,
        "visuals": pack.visuals, "smoke": pack.smoke, "cite": cite, "top_nodes": top_nodes,
        "primary": pack.flower.directions[0], "primary_node": top_nodes[0] if top_nodes else None,
        "generated": pack.generated_at[:10], "version": pack.florist_version,
    }
