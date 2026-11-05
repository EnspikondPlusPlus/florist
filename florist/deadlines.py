"""Conference deadlines, pulled live from the AI Deadlines public API (mlciv.com/ai-deadlines)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

import httpx

from . import profile
from .research import UA, Hit, cached

UPCOMING = "https://mlciv.com/ai-deadlines/api/upcoming.json"


def upcoming(subjects: list[str] | None = None) -> list[dict[str, Any]]:
    def fetch() -> list[Hit]:
        r = httpx.get(UPCOMING, headers={"User-Agent": UA}, timeout=20, follow_redirects=True)
        r.raise_for_status()
        return [Hit(tool="deadlines", title="all", abstract=json.dumps(r.json()))]

    data = json.loads(cached("deadlines", "upcoming", fetch, ttl_days=1)[0].abstract)
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    out = [c for c in data if (c.get("deadline") or "") >= now]
    if subjects:
        out = [c for c in out if set(c.get("sub") or []) & set(subjects)]
    return sorted(out, key=lambda c: c.get("deadline") or "")


def for_profile() -> list[dict[str, Any]]:
    targets = [t.lower() for t in profile.load().conference_targets]
    items = upcoming()
    if not targets:
        return items[:12]
    return [c for c in items if any(t in (c.get("id", "") + " " + c.get("title", "")).lower() for t in targets)]
