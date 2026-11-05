"""Background work: one ``tick`` does whatever is due.

* fetch due feed sources (and triage new items)
* passive growth: during the user's downtime windows, grow queued seeds one round at a time
  while the window's spend (Florist's own token log) stays under ``max_usd_per_window``
* auto-compost seeds left at lowest priority past the profile threshold
* compost mining and preference distillation on their cadence

``florist up`` runs ``tick`` every few minutes; without the app, schedule ``florist tick``
(cron / Windows Task Scheduler).
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from .. import config, gateway, profile
from ..schemas import Downtime, SeedState
from ..store import db
from . import compost, greenhouse, loop, preferences

DAYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]


def window_start(downtime: Downtime, now: datetime | None = None) -> datetime | None:
    """Start of the downtime window containing ``now`` (local time), or None if outside all windows."""
    now = now or datetime.now().astimezone()
    for w in downtime.windows:
        sh, sm = map(int, w.start.split(":"))
        eh, em = map(int, w.end.split(":"))
        for back in (0, 1):  # windows may cross midnight
            day = now - timedelta(days=back)
            if DAYS[day.weekday()] not in w.days:
                continue
            start = day.replace(hour=sh, minute=sm, second=0, microsecond=0)
            end = day.replace(hour=eh, minute=em, second=0, microsecond=0)
            if end <= start:
                end += timedelta(days=1)
            if start <= now < end:
                return start
    return None


def passive_queue() -> list:
    seeds = [s for s in db.list_seeds() if s.passive and s.state in
             (SeedState.dormant, SeedState.growing, SeedState.flowering)]
    seeds = [s for s in seeds if s.rounds_done < s.budget.max_rounds and not loop.active_run(s.id)]
    flowers = {s.id: db.latest_flower(s.id) for s in seeds}
    seeds = [s for s in seeds if not (flowers[s.id] and flowers[s.id].stability >= loop.STABLE_AT)]
    return sorted(seeds, key=lambda s: (-s.priority, s.rounds_done))


def passive_growth(now: datetime | None = None, max_rounds: int = 3, force: bool = False) -> list[dict[str, Any]]:
    prof = profile.load()
    mode = prof.downtime.mode
    if mode == "stop" and not force:
        return []
    start = window_start(prof.downtime, now)
    if mode == "scheduled" and start is None and not force:
        return []
    since = (start or datetime.now().astimezone()).astimezone(timezone.utc).replace(microsecond=0).isoformat()
    results = []
    for seed in passive_queue()[:max_rounds]:
        if gateway.spent(since=since) >= prof.downtime.max_usd_per_window:
            db.log_activity("passive", "Downtime budget reached; passive growth paused")
            break
        try:
            results.append(loop.grow(seed.id, rounds=1, mode="passive"))
        except (loop.RunBusy, gateway.LLMError) as e:
            results.append({"seed_id": seed.id, "status": "failed", "reason": str(e)})
    return results


def tick(now: datetime | None = None, fetch_feed: bool | None = None) -> dict[str, Any]:
    from ..ingest import feed

    report: dict[str, Any] = {"at": datetime.now(timezone.utc).isoformat()}
    s = config.get()
    if fetch_feed if fetch_feed is not None else s.auto_fetch_feed:
        try:
            report["feed"] = feed.fetch()
        except Exception as e:
            report["feed_error"] = str(e)
    report["auto_composted"] = greenhouse.auto_compost()
    report["passive"] = passive_growth(now)
    last = db.kv_get("last_mining")
    if len(db.list_compost()) >= 6 and (not last or datetime.fromisoformat(last) <
                                        datetime.now(timezone.utc) - timedelta(days=s.mining_every_days)):
        try:
            report["mined"] = [x.id for x in compost.mine()]
        except gateway.LLMError as e:
            report["mining_error"] = str(e)
    last_taste = db.kv_get("last_taste")
    n_events = (db.q1("SELECT COUNT(*) n FROM events") or {"n": 0})["n"]
    if n_events >= 10 and (not last_taste or datetime.fromisoformat(last_taste) <
                           datetime.now(timezone.utc) - timedelta(days=3)):
        try:
            report["learned"] = len(preferences.distill())
            db.kv_set("last_taste", datetime.now(timezone.utc).isoformat())
        except gateway.LLMError as e:
            report["taste_error"] = str(e)
    return report
