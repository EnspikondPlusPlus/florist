"""Preference adaptation loop.

Behaviour → events → learned weights → ranking and critique → behaviour.

1. Every user gesture (compost, dismiss, attach, start a seed, pick, boost, prune, …) is logged
   to ``events`` with the target's features (tags, technologies, source, tier).
2. ``record`` updates signed weights per feature in ``profile.yaml → learned_preferences``
   (an exponential move toward ±1 scaled by the gesture's signal). Locked entries never move.
3. ``score`` turns a feature set into a 0..1 preference score used by the feed ranker, the
   direction critic (blended with the model's ``interest``) and compost mining.
4. ``distill`` (skill ``florist-taste``) periodically turns the event log into plain-language
   statements ("prefers hands-on repos over surveys"), also written to the profile.

Nothing is hidden: the profile file is the model.
"""

from __future__ import annotations

import json
import math
from collections import Counter
from typing import Any

from .. import gateway, profile, skills
from ..schemas import LearnedPreference, PreferenceDistill, now_iso
from ..store import db

# Signal per gesture: sign = seek/avoid, magnitude = how much it says about taste.
SIGNALS: dict[str, float] = {
    "pick": 1.0,
    "seed_from": 1.0,
    "promote": 0.9,
    "attach": 0.8,
    "boost": 0.7,
    "compost": 0.6,
    "accept_candidate": 0.8,
    "keep": 0.3,
    "open": 0.15,
    "unfold": 0.2,
    "dismiss": -0.7,
    "prune": -0.6,
    "reject_candidate": -0.5,
    "auto_compost": -0.3,
}
LEARNING_RATE = 0.18
MAX_ENTRIES = 80


def features_of(obj: Any) -> dict[str, Any]:
    """Extract preference features from a FeedItem / CompostItem / Seed / node-like object."""
    get = (lambda k, d=None: obj.get(k, d)) if isinstance(obj, dict) else (lambda k, d=None: getattr(obj, k, d))
    data = get("data", {}) or {}
    tier = get("tier")
    return {
        "tags": [t.lower() for t in (get("tags") or [])][:8],
        "technologies": [t.lower() for t in (get("technologies") or data.get("technologies") or [])][:8],
        "source": (get("source_name") or get("source_kind") or get("source") or data.get("tool") or "").lower(),
        "tier": getattr(tier, "value", tier) or "",
        "title": get("title") or "",
    }


def record(kind: str, target_kind: str, target_id: str, features: dict[str, Any]) -> float:
    """Log a behavioural event and update learned weights. Returns the signal used."""
    signal = SIGNALS.get(kind, 0.0)
    db.ex(
        "INSERT INTO events(kind, target_kind, target_id, signal, features, created) VALUES (?,?,?,?,?,?)",
        (kind, target_kind, target_id, signal, json.dumps(features), now_iso()),
    )
    if signal:
        _update_weights(signal, features)
    return signal


def _key(kind: str, key: str) -> str:
    return f"lp_{kind}_{db.slugify(key, 40)}"


def _update_weights(signal: float, features: dict[str, Any]) -> None:
    prof = profile.load()
    entries = {lp.id: lp for lp in prof.learned_preferences}
    keys: list[tuple[str, str]] = [("tag", t) for t in features.get("tags", [])]
    keys += [("technology", t) for t in features.get("technologies", [])]
    if features.get("source"):
        keys.append(("source", features["source"]))
    direction = 1.0 if signal > 0 else -1.0
    for kind, key in keys:
        if not key:
            continue
        lid = _key(kind, key)
        lp = entries.get(lid) or LearnedPreference(id=lid, kind=kind, key=key)  # type: ignore[arg-type]
        if lp.locked:
            continue
        lp.weight = round(max(-1.0, min(1.0, lp.weight + LEARNING_RATE * abs(signal) * (direction - lp.weight))), 3)
        lp.evidence += 1
        lp.updated = now_iso()
        entries[lid] = lp
    ranked = sorted(
        entries.values(),
        key=lambda e: (e.locked or e.kind == "statement", abs(e.weight) * math.log(2 + e.evidence)),
        reverse=True,
    )
    prof.learned_preferences = ranked[:MAX_ENTRIES]
    profile.save(prof)


def score(features: dict[str, Any]) -> float:
    """0..1 preference score; 0.5 means 'no learned opinion'."""
    prof = profile.load()
    weights = {(lp.kind, lp.key.lower()): lp.weight for lp in prof.learned_preferences if lp.kind != "statement"}
    for interest in prof.interests:  # stated interests count as a mild prior
        weights.setdefault(("tag", interest.lower()), 0.4)
    matched: list[float] = []
    for t in features.get("tags", []):
        if ("tag", t.lower()) in weights:
            matched.append(weights[("tag", t.lower())])
    for t in features.get("technologies", []):
        w = weights.get(("technology", t.lower()), weights.get(("tag", t.lower())))
        if w is not None:
            matched.append(w)
    if features.get("source") and ("source", features["source"]) in weights:
        matched.append(0.5 * weights[("source", features["source"])])
    title = (features.get("title") or "").lower()
    for interest in prof.interests + prof.wants_to_learn:
        if interest and interest.lower() in title:
            matched.append(0.5)
    if not matched:
        return 0.5
    x = sum(matched) / math.sqrt(len(matched))  # more agreeing evidence → more confident
    return round(0.5 + 0.5 * math.tanh(x), 3)


def event_summary(limit: int = 300) -> dict[str, Any]:
    rows = db.q("SELECT kind, target_kind, features, created FROM events ORDER BY id DESC LIMIT ?", (limit,))
    by_kind = Counter(r["kind"] for r in rows)
    samples = [
        {"kind": r["kind"], "target": r["target_kind"], **json.loads(r["features"]), "at": r["created"][:10]}
        for r in rows[:120]
    ]
    return {"counts": dict(by_kind), "events": samples}


def distill_task() -> dict[str, Any]:
    prof = profile.load()
    return {
        "events": event_summary(),
        "current_statements": [lp.model_dump() for lp in prof.learned_preferences if lp.kind == "statement"],
        "profile": profile.brief(prof),
    }


def apply_distill(out: PreferenceDistill) -> list[LearnedPreference]:
    prof = profile.load()
    kept = [lp for lp in prof.learned_preferences if lp.kind != "statement" or lp.locked]
    locked_text = {lp.key.lower() for lp in kept if lp.kind == "statement"}
    new = [
        LearnedPreference(
            id=_key("statement", s.statement), kind="statement", key=s.statement,
            weight=s.weight, evidence=s.evidence, note="distilled from behaviour",
        )
        for s in out.statements
        if s.statement.lower() not in locked_text
    ]
    prof.learned_preferences = new + kept
    profile.save(prof)
    profile.refresh_florist_section()
    db.log_activity("taste", f"Learned {len(new)} preference statements from behaviour")
    return new


def distill() -> list[LearnedPreference]:
    """Run the taste skill over recent behaviour (needs ≥ 5 events)."""
    task = distill_task()
    if sum(task["events"]["counts"].values()) < 5:
        return []
    out = gateway.complete(
        gateway.Call(step="taste", hints={"topic": "your preferences"}),
        skills.system_prompt("taste"),
        "## Context\n" + json.dumps(task, indent=1, ensure_ascii=False),
        PreferenceDistill,
    )
    return apply_distill(out)
