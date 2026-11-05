"""Usage statistics for the Statistics page and per-seed activity (GitHub-style heatmaps)."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from .store import db


def _days(n: int) -> list[str]:
    today = date.today()
    return [(today - timedelta(days=i)).isoformat() for i in range(n - 1, -1, -1)]


def global_stats(days: int = 60) -> dict[str, Any]:
    since = _days(days)[0]
    rows = db.q(
        """SELECT substr(created,1,10) d, COUNT(*) calls, SUM(input_tokens+output_tokens) tokens, SUM(cost_usd) usd,
                  SUM(1-ok) failed FROM llm_calls WHERE substr(created,1,10)>=? GROUP BY d""", (since,))
    by_day = {r["d"]: dict(r) for r in rows}
    series = [{"date": d, "calls": by_day.get(d, {}).get("calls", 0) or 0,
               "tokens": by_day.get(d, {}).get("tokens", 0) or 0,
               "usd": round(by_day.get(d, {}).get("usd", 0) or 0, 4),
               "failed": by_day.get(d, {}).get("failed", 0) or 0} for d in _days(days)]

    def group(col: str) -> list[dict[str, Any]]:
        return [dict(r) for r in db.q(
            f"""SELECT {col} key, COUNT(*) calls, SUM(input_tokens+output_tokens) tokens, SUM(cost_usd) usd,
                       AVG(latency_ms) ms, SUM(1-ok) failed FROM llm_calls GROUP BY {col} ORDER BY usd DESC, calls DESC""")]

    seeds = [dict(r) for r in db.q(
        """SELECT l.seed_id key, COALESCE(json_extract(s.doc,'$.title'), l.seed_id) title, COUNT(*) calls,
                  SUM(l.cost_usd) usd FROM llm_calls l LEFT JOIN seeds s ON s.id=l.seed_id
           WHERE l.seed_id!='' GROUP BY l.seed_id ORDER BY usd DESC LIMIT 10""")]
    tot = db.q1("SELECT COUNT(*) calls, COALESCE(SUM(input_tokens+output_tokens),0) tokens, COALESCE(SUM(cost_usd),0) usd, "
                "COALESCE(SUM(1-ok),0) failed FROM llm_calls")
    counts = {
        "seeds": (db.q1("SELECT COUNT(*) n FROM seeds WHERE state NOT IN ('candidate','composted')") or {"n": 0})["n"],
        "flowers": (db.q1("SELECT COUNT(DISTINCT seed_id) n FROM flowers") or {"n": 0})["n"],
        "packs": (db.q1("SELECT COUNT(*) n FROM packs") or {"n": 0})["n"],
        "compost": (db.q1("SELECT COUNT(*) n FROM compost") or {"n": 0})["n"],
        "feed": (db.q1("SELECT COUNT(*) n FROM feed_items") or {"n": 0})["n"],
        "sources_read": (db.q1("SELECT COUNT(*) n FROM nodes WHERE kind='source'") or {"n": 0})["n"],
    }
    return {"total": dict(tot) if tot else {}, "series": series, "by_model": group("model"), "by_step": group("step"),
            "by_backend": group("backend"), "by_seed": seeds, "counts": counts, "heatmap": heatmap()}


def heatmap(seed_id: str | None = None, weeks: int = 26) -> list[dict[str, Any]]:
    """Daily activity counts (activity log + model calls) for the last ``weeks`` weeks."""
    since = _days(weeks * 7)[0]
    where, params = ("AND seed_id=?", [seed_id]) if seed_id else ("", [])
    act = {r["d"]: r["n"] for r in db.q(
        f"SELECT substr(created,1,10) d, COUNT(*) n FROM activity WHERE substr(created,1,10)>=? {where} GROUP BY d",
        [since, *params])}
    calls = {r["d"]: r["n"] for r in db.q(
        f"SELECT substr(created,1,10) d, COUNT(*) n FROM llm_calls WHERE substr(created,1,10)>=? {where} GROUP BY d",
        [since, *params])}
    return [{"date": d, "count": act.get(d, 0) + calls.get(d, 0)} for d in _days(weeks * 7)]


def seed_stats(seed_id: str) -> dict[str, Any]:
    tot = db.q1("SELECT COUNT(*) calls, COALESCE(SUM(input_tokens+output_tokens),0) tokens, COALESCE(SUM(cost_usd),0) usd "
                "FROM llm_calls WHERE seed_id=?", (seed_id,))
    kinds = {r["kind"]: r["n"] for r in db.q("SELECT kind, COUNT(*) n FROM nodes WHERE seed_id=? GROUP BY kind", (seed_id,))}
    pruned = (db.q1("SELECT COUNT(*) n FROM nodes WHERE seed_id=? AND kind='direction' AND status='pruned'",
                    (seed_id,)) or {"n": 0})["n"]
    runs = (db.q1("SELECT COUNT(*) n FROM runs WHERE seed_id=?", (seed_id,)) or {"n": 0})["n"]
    return {"calls": tot["calls"] if tot else 0, "tokens": tot["tokens"] if tot else 0,
            "usd": round(tot["usd"], 4) if tot else 0, "runs": runs, "sources": kinds.get("source", 0),
            "directions": kinds.get("direction", 0), "pruned": pruned, "checks": kinds.get("check", 0),
            "smoke": kinds.get("smoke", 0), "heatmap": heatmap(seed_id)}
