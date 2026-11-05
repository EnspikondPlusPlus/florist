import json

import pytest

from florist import gateway
from florist.agent import greenhouse, loop, pack
from florist.schemas import STEP_OUTPUTS, Evidence, Finding, FlowerDirection, FlowerDraft
from florist.store import db


def _seed(**kw):
    seed, _ = greenhouse.create_seed("On-device speculative decoding with a tiny draft model on one RTX 4090",
                                     tier=kw.pop("tier", "personal"), **kw)
    return seed


def test_full_loop_builds_graph_flower_and_pack(tmp_path):
    seed = _seed()
    res = loop.grow(seed.id, rounds=2)
    assert res["status"] == "done"
    flower = db.latest_flower(seed.id)
    assert flower and flower.version == 2 and 1 <= len(flower.findings) <= 7
    valid = {n.id for n in db.list_nodes(seed.id)} | {s.id for s in db.list_smoke(seed.id)}
    for f in flower.findings:  # every finding is traceable
        assert f.evidence and all(e.ref in valid for e in f.evidence)
    kinds = {n.kind.value for n in db.list_nodes(seed.id)}
    assert {"seed", "source", "direction", "check", "finding", "visual"} <= kinds
    assert any(d.status.value == "pruned" and d.reason for d in db.list_nodes(seed.id, "direction"))
    vis = {v.kind for v in db.list_visuals(seed.id)}
    assert {"concept", "landscape", "scores", "graph"} <= vis
    assert db.get_seed(seed.id).state.value == "flowering"

    dest = pack.pick(seed.id, tmp_path / "packs")
    for f in ("flower.md", "flower.json", "sources.json", "pruned.json", "visuals/landscape.svg",
              "visuals/concept.svg", "adapters/openresearch/program.md", "adapters/build_plan/BUILD_PLAN.md",
              "adapters/coscientist/research_goal.md", "adapters/coding_agent/CLAUDE.md"):
        assert (dest / f).exists(), f
    data = json.loads((dest / "flower.json").read_text(encoding="utf-8"))
    assert data["schema_version"] and data["handoff"]["objective"]
    assert "## What you must not change" in (dest / "adapters/openresearch/program.md").read_text(encoding="utf-8")
    assert db.get_seed(seed.id).state.value == "picked"


def test_cost_is_logged_per_call():
    seed = _seed(tier="exploration")
    loop.grow(seed.id, rounds=1)
    steps = {r["step"] for r in db.q("SELECT step FROM llm_calls WHERE seed_id=?", (seed.id,))}
    assert {"ground", "triage", "explore", "check", "exploit", "flower"} <= steps


def test_agent_driven_loop_validates_and_advances():
    seed = _seed()
    ctx = loop.start(seed.id, 1, "agent")
    task = loop.next_task(run_id=ctx.run_id)
    seen = []
    for _ in range(20):
        if "step" not in task or "instructions" not in task:
            break
        seen.append(task["step"])
        assert task["schema"]["type"] == "object"
        # A bad submission is rejected without advancing.
        if task["step"] != "smoke":  # zero smoke proposals is a valid answer
            bad = loop.submit(seed.id, {"nonsense": True})
            assert not bad["accepted"] and bad["error"]
        # The mock model plays the external agent.
        out = gateway._mock(task["schema"], gateway.Call(step=task["step"], hints=_hints_for(task)))
        res = loop.submit(seed.id, out.structured)
        assert res["accepted"], res
        task = res["next"]
    assert task["status"] == "done"
    assert seen[:3] == ["ground", "triage", "explore"] and "flower" in seen
    assert db.latest_flower(seed.id) is not None


def _hints_for(task):
    ctx = task["context"]
    refs, evidence = [], []
    if task["step"] == "triage":
        refs = [s["id"] for s in ctx["sources"]]
    if task["step"] in ("check", "exploit", "smoke"):
        refs = [d["id"] for d in ctx["directions"]]
        evidence = [c["id"] for d in ctx["directions"] for c in d.get("closest_candidates", [])]
    if task["step"] == "flower":
        refs = [d["id"] for d in ctx["top_directions"]]
        evidence = [s["id"] for s in ctx["sources"]]
    return {"refs": refs, "evidence": evidence, "topic": "decoding"}


def test_flower_without_evidence_is_rejected():
    seed = _seed()
    ctx = loop.start(seed.id, 1, "agent")
    draft = FlowerDraft(idea="x", findings=[Finding(text="made up", evidence=[Evidence(ref="src_doesnotexist")])],
                        directions=[FlowerDirection(title="t", pitch="p")])
    with pytest.raises(loop.StepRejected):
        loop.apply_flower(ctx, draft)


def test_user_prune_and_boost_steer_exploit():
    seed = _seed()
    loop.grow(seed.id, rounds=1)
    dirs = [d for d in db.list_nodes(seed.id, "direction") if d.status.value != "pruned"]
    target = dirs[0]
    greenhouse.direction_action(target.id, "prune", "not my thing")
    n = db.get_node(target.id)
    assert n.status.value == "pruned" and n.data["user_pruned"]
    steering = loop._steering(seed.id)
    assert steering["user_pruned"][0]["id"] == target.id


def test_stop_request_stops_agent_run():
    seed = _seed()
    loop.start(seed.id, 1, "agent")
    loop.next_task(seed.id)
    assert loop.request_stop(seed.id)
    assert loop.active_run(seed.id) is None


def test_step_outputs_have_skills():
    from florist import skills

    for step in STEP_OUTPUTS:
        assert skills.for_step(step).body
