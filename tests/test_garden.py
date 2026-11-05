import email
import email.policy
import json
from datetime import datetime, timedelta, timezone

from florist import profile
from florist.agent import compost, greenhouse, preferences, scheduler, smoke
from florist.ingest import feed, sources
from florist.schemas import Downtime, DowntimeWindow, FeedItem, FeedSource
from florist.store import db


def _feed_item(title, tags=None, source="alphaXiv trending"):
    it = FeedItem(id=db.new_id("fd"), title=title, url=f"https://ex.org/{title.replace(' ', '-')}",
                  content=f"{title} explained", source_name=source, tags=tags or [])
    db.insert_feed_item(it)
    return it


def test_preferences_learn_from_behaviour_and_change_ranking():
    a = _feed_item("Robot arm grasping", ["robotics"])
    b = _feed_item("Fast LLM inference kernels", ["efficient inference"])
    for _ in range(3):
        preferences.record("dismiss", "feed", a.id, {"tags": ["robotics"], "technologies": [], "source": ""})
        preferences.record("compost", "feed", b.id, {"tags": ["efficient inference"], "technologies": ["cuda"],
                                                     "source": ""})
    prof = profile.load()
    weights = {(lp.kind, lp.key): lp.weight for lp in prof.learned_preferences}
    assert weights[("tag", "robotics")] < 0 < weights[("tag", "efficient inference")]
    assert preferences.score({"tags": ["robotics"]}) < 0.5 < preferences.score({"tags": ["efficient inference"]})
    # locked entries are never changed by Florist
    prof.learned_preferences[0].locked = True
    locked = prof.learned_preferences[0]
    profile.save(prof)
    preferences.record("dismiss", "feed", a.id, {"tags": [locked.key], "technologies": [], "source": ""})
    again = {lp.id: lp for lp in profile.load().learned_preferences}[locked.id]
    assert again.weight == locked.weight


def test_distill_writes_statements_to_profile():
    for i in range(6):
        preferences.record("dismiss", "feed", f"x{i}", {"tags": ["theory"], "technologies": [], "source": ""})
    learned = preferences.distill()
    assert learned and all(lp.kind == "statement" for lp in learned)
    text = (profile.load().learned_preferences)
    assert any(lp.kind == "statement" for lp in text)


def test_feed_triage_ranks_and_folds_and_actions():
    seed, _ = greenhouse.create_seed("Speculative decoding on consumer GPUs", tier="personal")
    items = [_feed_item(f"Paper {i} on speculative decoding") for i in range(3)]
    assert feed.triage([i.id for i in items]) == 3
    got = db.get_feed_item(items[0].id)
    assert got.summary and got.why and got.status.value in ("kept", "folded")
    res = feed.act(items[0].id, "compost")
    assert db.get_compost(res["compost_id"]).feed_item_id == items[0].id
    res = feed.act(items[1].id, "attach", seed.id)
    assert items[1].id in db.get_seed(seed.id).feed_ids
    res = feed.act(items[2].id, "seed")
    assert db.get_seed(res["seed_id"]).origin == "feed"


def test_compost_clusters_mining_and_seed_from():
    for t in ["sparse attention kernels", "flash attention on 4090", "attention sinks", "robot grasping video",
              "imitation learning from video", "humanoid teleoperation"]:
        compost.add(title=t, note=f"notes on {t}")
    cl = compost.clusters()
    assert cl and sum(len(c["items"]) for c in cl) == 6
    cands = compost.mine()
    assert all(c.state.value == "candidate" and len(c.compost_ids) >= 2 for c in cands)
    if cands:
        assert compost.accept_candidate(cands[0].id).state.value == "dormant"
    ids = [c.id for c in db.list_compost()[:2]]
    s = compost.seed_from(ids)
    assert s.compost_ids == ids and s.origin == "compost"


def test_auto_compost_moves_stale_lowest_priority_seeds():
    seed, _ = greenhouse.create_seed("Old idea", tier="exploration", priority=1)
    s = db.get_seed(seed.id)
    s.priority_since = (datetime.now(timezone.utc) - timedelta(days=400)).isoformat()
    db.put_seed(s)
    moved = greenhouse.auto_compost()
    assert seed.id in moved
    assert db.get_seed(seed.id).state.value == "composted"
    assert any(c.seed_id == seed.id for c in db.list_compost())


def test_smoke_runs_only_with_approval_and_parses_result():
    seed, _ = greenhouse.create_seed("x", tier="personal")
    chk = smoke.add(seed.id, "", "python works", "import json\nprint('SMOKE_RESULT ' + json.dumps({'two': 2}))")
    try:
        smoke.run(chk.id, approved=False)
        raise AssertionError("ran without approval")
    except PermissionError:
        pass
    r = smoke.run(chk.id, approved=True)
    assert r.status == "passed" and r.metrics == {"two": 2.0}
    slow = smoke.add(seed.id, "", "times out", "import time\ntime.sleep(10)", timeout_s=1)
    assert smoke.run(slow.id, approved=True).status == "failed"


def test_newsletter_is_split_into_items():
    html = """<html><body><h2>This week</h2><p>Great post: <a href="https://blog.example.com/spec-decoding">
    Speculative decoding explained in depth</a> shows 3x speedups.</p>
    <p><a href="https://github.com/foo/bar">A new repo for fast tokenizers in Rust</a></p>
    <p><a href="https://news.example.com/unsubscribe?id=1">Unsubscribe from this list</a></p></body></html>"""
    msg = email.message.EmailMessage(policy=email.policy.default)
    msg["Subject"] = "Weekly ML"
    msg["From"] = "news@example.com"
    msg.set_content("plain")
    msg.add_alternative(html, subtype="html")
    src = FeedSource(id="src_mail", kind="email", name="newsletters")
    items = sources.split_newsletter(src, msg)
    urls = [i.url for i in items]
    assert "https://blog.example.com/spec-decoding" in urls and "https://github.com/foo/bar" in urls
    assert not any("unsubscribe" in u for u in urls)


def test_downtime_window_crossing_midnight():
    d = Downtime(enabled=True, windows=[DowntimeWindow(start="23:00", end="06:00")])
    inside = datetime(2026, 11, 4, 2, 30).astimezone()
    outside = datetime(2026, 11, 4, 12, 0).astimezone()
    assert scheduler.window_start(d, inside) is not None
    assert scheduler.window_start(d, outside) is None


def test_passive_growth_respects_queue():
    seed, _ = greenhouse.create_seed("Passive idea", tier="exploration", passive=True)
    res = scheduler.passive_growth(force=True, max_rounds=1)
    assert res and res[0]["seed_id"] == seed.id
    assert db.get_seed(seed.id).rounds_done == 1


def test_schemas_on_disk_are_in_sync():
    from florist import paths
    from florist.schemas import RECORDS, STEP_OUTPUTS

    d = paths.schemas_dir()
    for name, model in {**RECORDS, **{m.__name__: m for m in STEP_OUTPUTS.values()}}.items():
        f = d / f"{name}.schema.json"
        assert f.exists(), f"run `florist schemas` ({name} missing)"
        assert json.loads(f.read_text(encoding="utf-8")) == model.model_json_schema(), f"{name} out of date"
