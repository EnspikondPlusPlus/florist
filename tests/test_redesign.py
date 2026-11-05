from fastapi.testclient import TestClient

from florist import profile, stats
from florist.agent import greenhouse, ideate, seedspec
from florist.schemas import FeedItem
from florist.server import app, research_pdf_url
from florist.store import db


def test_ideate_chat_context_and_convert_to_seed():
    c = db.new_id("fd")
    item = FeedItem(id=c, title="Tiny draft models", url="https://ex.org/t", summary="drafts")
    db.insert_feed_item(item)
    chat = ideate.create()
    chat = ideate.add_context(chat["id"], {"kind": "feed", "id": item.id})
    assert chat["context"][0]["title"] == "Tiny draft models"
    res = ideate.message(chat["id"], "Could I speed up a 7B model on my GPU?", ["compost", "feed"])
    assert res["reply"]
    assert len(ideate.get(chat["id"])["messages"]) == 2
    seed = ideate.to_seed(chat["id"])["seed"]
    assert seed["origin"] == "ideate" and item.id in seed["feed_ids"]
    assert ideate.get(chat["id"])["seed_id"] == seed["id"]


def test_feeling_lucky_opens_a_chat():
    db.insert_feed_item(FeedItem(id="fd_lucky", title="Lucky item", url="https://ex.org/l", status="kept", score=0.8))
    res = ideate.feeling_lucky()
    assert res["chat"]["context"][0]["id"] == "fd_lucky"


def test_seed_spec_sheet_feeds_the_loop():
    from florist.agent import loop

    seed, _ = greenhouse.create_seed("A tiny draft model demo", tier="personal")
    text = seedspec.read(seed)
    assert seed.title in text and not seedspec.is_customized(seed, text)
    assert loop._seed_brief(seed)["spec_sheet"] == ""
    seedspec.write(seed, text + "\n- Must run in the browser\n")
    assert "Must run in the browser" in loop._seed_brief(seed)["spec_sheet"]


def test_profile_doc_is_the_source_of_truth():
    doc = profile.load_doc()
    assert profile.BEGIN in doc and "## Interests" in doc
    new = doc.replace("- robotics", "- gardening robots").replace("API budget: $0/month", "API budget: $40/month")
    new = new.replace("- 5 h/week", "- 12 h/week")
    prof = profile.save_doc(new)
    assert "gardening robots" in prof.interests
    assert prof.resources.budget_usd_month == 40 and prof.time.hours_per_week == 12
    pasted = "I am a PhD student. Interests: graphics, compilers."  # free text, no headings
    profile.save_doc(pasted)
    assert profile.BEGIN in profile.load_doc()  # Florist's section is always kept
    assert "PhD student" in profile.brief()


def test_stage_stats_and_reader_links():
    from florist.agent import loop

    seed, _ = greenhouse.create_seed("Stage test", tier="exploration")
    assert greenhouse.stage(seed)["stage"] == "seed"
    loop.grow(seed.id, rounds=1)
    assert greenhouse.stage(db.get_seed(seed.id))["stage"] in ("growing", "flower")
    st = stats.seed_stats(seed.id)
    assert st["calls"] > 0 and st["sources"] > 0 and len(st["heatmap"]) == 26 * 7
    assert stats.global_stats()["total"]["calls"] > 0
    assert research_pdf_url("https://www.alphaxiv.org/abs/2607.27735") == "https://arxiv.org/pdf/2607.27735"
    assert research_pdf_url("https://github.com/foo/bar") == ""


def test_new_endpoints():
    with TestClient(app) as c:
        seed = c.post("/api/seeds", json={"prompt": "endpoint test seed", "tier": "personal", "ask_followups": False}).json()["seed"]
        assert c.get(f"/api/seeds/{seed['id']}").json()["stage"]["stage"] == "seed"
        assert c.put(f"/api/seeds/{seed['id']}/spec", json={"text": "# hi"}).json()["ok"]
        assert c.get(f"/api/seeds/{seed['id']}/spec").json()["text"] == "# hi"
        assert "experiments" in c.get(f"/api/seeds/{seed['id']}/files").json()
        provs = c.get("/api/providers").json()
        assert any(p["id"] == "mock" and p["configured"] for p in provs)
        assert "mock" in c.get("/api/models/configured").json()
        assert c.get("/api/profile/doc").json()["outline"]
        assert c.get("/api/reader", params={"url": "https://github.com/x/y"}).status_code == 415
        chat = c.post("/api/ideate", json={}).json()
        assert c.post(f"/api/ideate/{chat['id']}/message", json={"message": "hello"}).json()["reply"]
        assert c.get("/api/stats").json()["series"]


def test_character_animations_setting_defaults_off_and_persists():
    from florist import config

    assert config.get().ui.character_animations is False
    with TestClient(app) as c:
        assert c.get("/api/settings").json()["ui"]["character_animations"] is False
        assert c.put("/api/settings", json={"ui": {"character_animations": True}}).json()["ui"]["character_animations"] is True
    config._cache = None
    assert config.load().ui.character_animations is True


def test_meta_model_api_migration_and_routing(monkeypatch):
    import yaml

    from florist import config, gateway, paths, providers

    paths.settings_path().write_text(yaml.safe_dump({"keys": {"meta_llama": "LLM_test"},
                                                     "models": {"strong": "meta_llama/Llama-4-Maverick-17B-128E-Instruct-FP8"}}), encoding="utf-8")
    config._cache = None
    s = config.load()
    assert s.keys == {"meta": "LLM_test"} and s.models.strong == "meta/muse-spark-1.3"
    assert gateway.backend_of("meta/muse-spark-1.3") == "meta"
    assert gateway.check_backend("meta/muse-spark-1.3")["ready"]
    seen = {}

    class R:
        status_code = 200
        text = ""
        def json(self):
            return {"choices": [{"message": {"content": '{"text": "hi"}'}}],
                    "usage": {"prompt_tokens": 1000, "completion_tokens": 1000, "prompt_tokens_details": {"cached_tokens": 0}}}

    class C:
        def __init__(self, *a, **k): pass
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def post(self, url, headers=None, json=None):
            seen.update(url=url, body=json, auth=headers["Authorization"]); return R()

    import httpx
    monkeypatch.setattr(httpx, "Client", C)
    out = gateway.complete_text(gateway.Call(step="ideate", model="meta/muse-spark-1.3", effort="high"), "sys", "hi")
    assert out == "hi"
    assert seen["url"] == "https://api.meta.ai/v1/chat/completions" and seen["auth"] == "Bearer LLM_test"
    assert seen["body"]["reasoning_effort"] == "high" and seen["body"]["response_format"]["json_schema"]["strict"] is True
    assert abs(gateway.spent() - (1.25 + 4.25) / 1000) < 1e-9
    meta = next(g for g in providers.catalog() if g["id"] == "meta")
    assert "max" in next(m for m in meta["models"] if m["id"] == "meta/muse-spark-1.3")["efforts"]
