import time

from fastapi.testclient import TestClient

from florist import gateway
from florist.server import app


def test_api_seed_lifecycle():
    with TestClient(app) as c:
        r = c.post("/api/seeds", json={"prompt": "A visual explainer of diffusion models", "tier": "exploration",
                                       "ask_followups": True})
        assert r.status_code == 200
        seed = r.json()["seed"]
        assert len(r.json()["questions"]) <= 2
        assert c.post(f"/api/seeds/{seed['id']}/grow", json={"rounds": 1}).status_code == 200
        for _ in range(100):
            s = c.get(f"/api/seeds/{seed['id']}").json()
            if not s["run"]:
                break
            time.sleep(0.1)
        assert s["flower"] is not None
        g = c.get(f"/api/seeds/{seed['id']}/graph").json()
        assert g["nodes"] and g["edges"] and g["mermaid"].startswith("flowchart")
        fl = c.get(f"/api/seeds/{seed['id']}/flower").json()
        assert fl["flower"]["findings"] and fl["refs"]
        vis = c.get(f"/api/seeds/{seed['id']}/visuals").json()
        svg = next(v for v in vis if v["kind"] == "landscape")["files"]["svg"]
        assert c.get(f"/api/visuals/{seed['id']}/{svg}").text.startswith("<svg")
        assert c.get(f"/api/visuals/{seed['id']}/..%2F..%2Fflorist.db").status_code == 404
        chat = c.post(f"/api/seeds/{seed['id']}/chat", json={"message": "focus on the simplest version"}).json()
        assert chat["reply"]
        picked = c.post(f"/api/seeds/{seed['id']}/pick", json={}).json()
        assert "adapters/openresearch/program.md" in picked["files"]
        assert c.get("/api/status").json()["usage"]["n"] > 0
        assert c.get("/api/usage").json()["by_step"]


def test_extract_json_handles_fenced_and_noisy_output():
    assert gateway.extract_json('Here you go:\n```json\n{"a": 1}\n```') == {"a": 1}
    assert gateway.extract_json('noise {"a": {"b": "}"}} trailing') == {"a": {"b": "}"}}
