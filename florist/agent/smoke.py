"""Smoke-check sandbox: a local Python subprocess with a hard timeout, run only after approval.

Isolation is deliberately simple (spec: "small and cheap only"): ``python -I`` in a fresh
per-check directory, a minimal environment without API keys, and a hard wall-clock limit.
It is not a security sandbox — the approval step is the safety mechanism.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys

from .. import paths
from ..schemas import ExplorationNode, NodeKind, SmokeCheck, now_iso
from ..store import db
from . import visuals

HARD_CAP_S = 300
_SAFE_ENV = ("PATH", "SYSTEMROOT", "TEMP", "TMP", "HOME", "USERPROFILE", "LANG", "PYTHONIOENCODING")


def run(smoke_id: str, approved: bool) -> SmokeCheck:
    check = db.get_smoke(smoke_id)
    if not check:
        raise KeyError(f"no smoke check {smoke_id}")
    if not approved:
        raise PermissionError("smoke checks run only with explicit user approval")
    if check.status in ("running",):
        return check
    workdir = paths.sub("smoke", check.seed_id, check.id)
    (workdir / "check.py").write_text(check.code, encoding="utf-8")
    check.status = "running"
    db.put_smoke(check)
    db.log_activity("smoke", f"Running smoke check: {check.assumption}", check.seed_id, {"id": check.id})
    env = {k: v for k, v in os.environ.items() if k.upper() in _SAFE_ENV}
    env["PYTHONIOENCODING"] = "utf-8"
    timeout = min(check.timeout_s, HARD_CAP_S)
    try:
        proc = subprocess.run(
            [sys.executable, "-I", "check.py"], cwd=workdir, env=env, capture_output=True,
            text=True, encoding="utf-8", errors="replace", timeout=timeout,
        )
        check.stdout, check.stderr = proc.stdout[-8000:], proc.stderr[-4000:]
        metrics = parse_result(proc.stdout)
        check.metrics = metrics
        if proc.returncode == 0 and metrics:
            check.status = "passed"
            check.verdict = "ran and reported " + ", ".join(f"{k}={v:g}" for k, v in list(metrics.items())[:4])
        elif proc.returncode == 0:
            check.status = "failed"
            check.verdict = "ran but printed no SMOKE_RESULT line"
        else:
            check.status = "failed"
            last = (proc.stderr.strip().splitlines() or ["non-zero exit"])[-1]
            check.verdict = f"exit {proc.returncode}: {last[:200]}"
    except subprocess.TimeoutExpired as e:
        check.status = "failed"
        check.stdout = (e.stdout or "")[-4000:] if isinstance(e.stdout, str) else ""
        check.verdict = f"timed out after {timeout}s"
    check.finished = now_iso()
    (workdir / "result.json").write_text(check.model_dump_json(indent=2), encoding="utf-8")
    db.put_smoke(check)
    node = db.get_node(check.id)
    if node:
        node.summary = f"{check.status}: {check.verdict}"
        node.data.update({"status": check.status, "metrics": check.metrics, "verdict": check.verdict})
        db.put_node(node)
    visuals.smoke(check.seed_id, db.list_smoke(check.seed_id))
    db.log_activity("smoke", f"Smoke check {check.status}: {check.verdict}", check.seed_id, {"id": check.id})
    return check


def reject(smoke_id: str) -> SmokeCheck:
    check = db.get_smoke(smoke_id)
    if not check:
        raise KeyError(smoke_id)
    check.status = "rejected"
    db.put_smoke(check)
    node = db.get_node(check.id)
    if node:
        node.summary = "rejected by user"
        db.put_node(node)
    return check


def parse_result(stdout: str) -> dict[str, float]:
    for line in reversed((stdout or "").splitlines()):
        if line.startswith("SMOKE_RESULT"):
            try:
                data = json.loads(line[len("SMOKE_RESULT"):].strip())
            except json.JSONDecodeError:
                return {}
            if not isinstance(data, dict):
                return {}
            return {str(k): float(v) for k, v in data.items() if isinstance(v, (int, float, bool))}
    return {}


def add(seed_id: str, direction_id: str, assumption: str, code: str, rationale: str = "", expected: str = "",
        timeout_s: int = 60, rnd: int = 0) -> SmokeCheck:
    check = SmokeCheck(
        id=db.new_id("smk"), seed_id=seed_id, direction_id=direction_id, assumption=assumption,
        rationale=rationale, code=code, expected=expected, timeout_s=min(timeout_s, HARD_CAP_S),
    )
    db.put_smoke(check)
    parent = direction_id if direction_id and db.get_node(direction_id) else seed_id
    db.put_node(ExplorationNode(
        id=check.id, seed_id=seed_id, round=rnd, kind=NodeKind.smoke, title=f"Smoke: {assumption[:60]}",
        summary="awaiting your approval", parents=[parent], data={"status": "pending", "expected": expected},
    ))
    db.log_activity("smoke", f"Smoke check proposed (needs approval): {assumption}", seed_id, {"id": check.id})
    return check
