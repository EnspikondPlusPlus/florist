"""Chat context: items dragged into a conversation, and composer skills that add retrieval.

Context items are ``{"kind": "compost" | "feed" | "source" | "seed", "id": ...}``.
Composer skills (toggled per message in the UI):

* ``literature`` — search papers/repos for the message (research layer, cached)
* ``novelty``    — closest-work search for the idea being discussed, with crowdedness counts
* ``compost``    — recall the most similar compost items
* ``feed``       — recall the most similar recent feed items
"""

from __future__ import annotations

from typing import Any

from .. import research, text
from ..store import db

COMPOSER_SKILLS = {
    "literature": "Search papers and repos for what you ask",
    "novelty": "Check what already exists close to the idea",
    "compost": "Recall related items from your compost",
    "feed": "Recall related items from your feed",
}


def resolve(items: list[dict[str, str]]) -> list[dict[str, Any]]:
    """Turn context references into compact dicts for prompts (unknown refs are skipped)."""
    out = []
    for it in items:
        kind, ref = it.get("kind"), it.get("id", "")
        if kind == "compost" and (c := db.get_compost(ref)):
            out.append({"kind": "compost", "id": c.id, "title": c.title, "summary": c.summary or c.notes,
                        "takeaways": c.takeaways, "links": c.links, "tags": c.tags})
        elif kind == "feed" and (f := db.get_feed_item(ref)):
            out.append({"kind": "feed", "id": f.id, "title": f.title, "summary": f.summary or f.content[:500],
                        "url": f.url, "source": f.source_name or f.source_kind})
        elif kind == "source" and (n := db.get_node(ref)):
            out.append({"kind": "source", "id": n.id, "title": n.title, "summary": n.summary or
                        (n.data.get("abstract") or "")[:600], "url": n.url})
        elif kind == "seed" and (s := db.get_seed(ref)):
            out.append({"kind": "seed", "id": s.id, "title": s.title, "summary": s.prompt})
    return out


def label(item: dict[str, str]) -> dict[str, str]:
    r = resolve([item])
    return {**item, "title": r[0]["title"] if r else item.get("id", "")}


def run_skills(skills: list[str], message: str, topic: str = "") -> dict[str, Any]:
    """Retrieval for the toggled composer skills. Every result carries an id the reply may cite."""
    q = (message if len(message) < 200 else message[:200]) + (f" {topic}" if topic else "")
    found: dict[str, Any] = {}
    if "literature" in skills:
        hits = research.search(q, kind="paper", limit=6) + research.search(q, kind="repo", limit=3)
        found["literature"] = [{"title": h.title, "url": h.url, "year": h.year, "tool": h.tool,
                                "snippet": h.abstract[:300]} for h in hits]
    if "novelty" in skills:
        phrase = " ".join(text.tokens(q)[:6]) or q
        hits = research.search(phrase, kind="paper", limit=5) + research.search(phrase, kind="repo", limit=3)
        found["closest_existing_work"] = [{"title": h.title, "url": h.url, "year": h.year,
                                           "snippet": h.abstract[:250]} for h in hits]
        found["crowdedness"] = research.crowdedness(phrase)
    if "compost" in skills:
        items = db.list_compost()
        ranked = sorted(items, key=lambda c: -text.similarity(q, f"{c.title} {c.summary} {' '.join(c.tags)}"))[:5]
        found["related_compost"] = [{"id": c.id, "title": c.title, "summary": c.summary[:240]} for c in ranked]
    if "feed" in skills:
        items = db.list_feed(["kept", "attached", "composted", "seeded"], 300)
        ranked = sorted(items, key=lambda f: -text.similarity(q, f"{f.title} {f.summary}"))[:5]
        found["related_feed"] = [{"id": f.id, "title": f.title, "url": f.url, "summary": f.summary[:240]}
                                 for f in ranked]
    return found


def search_compost(query: str, limit: int = 12) -> list[dict[str, Any]]:
    items = db.list_compost()
    if not query.strip():
        return [{"id": c.id, "title": c.title, "tags": c.tags[:3]} for c in items[:limit]]
    scored = [(text.similarity(query, f"{c.title} {c.summary} {' '.join(c.tags)} {c.notes}"), c) for c in items]
    scored = [x for x in scored if x[0] > 0 or query.lower() in x[1].title.lower()]
    scored.sort(key=lambda x: -x[0])
    return [{"id": c.id, "title": c.title, "tags": c.tags[:3], "score": round(s, 3)} for s, c in scored[:limit]]
