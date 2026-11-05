from fastapi.testclient import TestClient

from florist import profile
from florist.agent import greenhouse, loop
from florist.server import app
from florist.store import db


def test_new_idea_mid_run_regrounds_once_and_reaches_context():
    seed, _ = greenhouse.create_seed("Tiny draft models for speculative decoding", tier="personal")
    ctx = loop.start(seed.id, 1, "agent")
    task = loop.next_task(run_id=ctx.run_id)
    assert task["step"] == "ground"
    # advance past ground into triage
    from florist import gateway
    out = gateway._mock(task["schema"], gateway.Call(step="ground", hints={"topic": "x"}))
    res = loop.submit(seed.id, out.structured)
    assert res["next"]["step"] == "triage"
    assert greenhouse.inject_idea(seed.id, "what about early-exit heads instead of a draft model")["applied"] == "live"
    # the pending triage task is discarded on next poll only after submit; simulate the next step boundary
    ctx = loop.load_ctx(ctx.run_id)
    ctx.state.pop("pending", None)
    assert loop.check_new_ideas(ctx) is True
    assert ctx.state["step_idx"] == 0
    assert loop.check_new_ideas(ctx) is False  # same idea is not re-applied
    assert "early-exit" in loop._steering(seed.id)["new_ideas"][0]


def test_about_md_flows_into_prompts():
    profile.save_about("# About me\n\nI love tiny, visual demos and hate cluster jobs.")
    assert "tiny, visual demos" in profile.brief()


def test_profile_docs_and_share_api():
    with TestClient(app) as c:
        raw = c.get("/api/profile/raw").json()["text"]
        assert "interests" in raw
        bad = c.put("/api/profile/raw", json={"text": "interests: 5\ncompost_after_days: -3"})
        assert bad.status_code == 400
        assert c.put("/api/profile/raw", json={"text": raw.replace("robotics", "gardening")}).status_code == 200
        assert "gardening" in c.get("/api/profile").json()["interests"]
        docs = c.get("/api/docs").json()
        assert any(d["title"] == "Getting started" for d in docs)
        assert c.get(f"/api/docs/{docs[0]['name']}").json()["text"]
        assert c.get("/api/docs/..__secrets").status_code == 404


def test_local_folder_source(tmp_path):
    from florist.ingest import sources
    from florist.schemas import FeedSource

    (tmp_path / "clip.md").write_text("# Neat trick\nSee https://example.com/trick for details", encoding="utf-8")
    items = sources.fetch_folder(FeedSource(id="s", kind="folder", name="notes", config={"path": str(tmp_path)}))
    assert items[0].title == "Neat trick" and items[0].url == "https://example.com/trick"


def test_mcp_server_exposes_tools():
    import asyncio

    from florist import mcp_server

    tools = asyncio.run(mcp_server.mcp.list_tools())
    names = {t.name for t in tools}
    assert {"florist_round_start", "florist_round_submit", "florist_pick", "florist_idea", "florist_feed"} <= names
