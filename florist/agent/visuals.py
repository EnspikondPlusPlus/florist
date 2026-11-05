"""Visuals as code: SVG (always), Mermaid and Plotly specs (where they add value).

* concept   — how the core technique works (from the ``florist-visualize`` ConceptSpec)
* landscape — where existing work sits and where the gap is (2-D map of sources vs directions)
* scores    — novelty / feasibility / room / interest per direction
* smoke     — smoke-check metrics
* graph     — the exploration graph (Mermaid)

Files are written to ``~/.florist/visuals/<seed_id>/`` and linked from the flower.
"""

from __future__ import annotations

import html
import json
import math
from pathlib import Path
from typing import Any

from .. import paths, text
from ..schemas import ConceptSpec, ExplorationNode, NodeStatus, SmokeCheck, Visual
from ..store import db

GREEN = "#00a85a"
GREEN_DARK = "#00773a"
GREEN_LIGHT = "#c9eedb"
INK = "#171717"
SUB = "#6b6b6b"
MUTED = "#a1a1a1"
LINE = "#e5e5e5"
KIND_COLORS = {"paper": "#3a8dff", "repo": "#9c5cff", "post": "#da9100", "web": "#209a84"}
FONT = "-apple-system, 'Segoe UI', system-ui, Inter, Roboto, sans-serif"


def seed_dir(seed_id: str) -> Path:
    return paths.sub("visuals", seed_id)


def esc(s: str) -> str:
    return html.escape(s or "", quote=True)


def clip(s: str, n: int) -> str:
    s = s or ""
    return s if len(s) <= n else s[: n - 1].rstrip() + "…"


def wrap(s: str, width: int) -> list[str]:
    words, lines, cur = (s or "").split(), [], ""
    for w in words:
        if len(cur) + len(w) + 1 > width and cur:
            lines.append(cur)
            cur = w
        else:
            cur = f"{cur} {w}".strip()
    if cur:
        lines.append(cur)
    return lines


def _svg(w: int, h: int, body: str, title: str) -> str:
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}" '
        f'font-family="{FONT}" role="img" aria-label="{esc(title)}">\n'
        f'<rect width="{w}" height="{h}" rx="14" fill="#ffffff"/>\n'
        '<defs><marker id="arr" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" '
        f'orient="auto-start-reverse"><path d="M0 0L10 5L0 10z" fill="{SUB}"/></marker>'
        f'<radialGradient id="halo"><stop offset="0" stop-color="#3a8dff" stop-opacity="0.16"/>'
        f'<stop offset="1" stop-color="#3a8dff" stop-opacity="0"/></radialGradient></defs>\n'
        f"{body}\n</svg>\n"
    )


def _save(seed_id: str, name: str, content: str) -> str:
    (seed_dir(seed_id) / name).write_text(content, encoding="utf-8")
    return name


def _register(seed_id: str, kind: str, title: str, caption: str, files: dict[str, str], rnd: int) -> Visual:
    v = Visual(id=f"vis_{seed_id[-8:]}_{kind}", seed_id=seed_id, kind=kind, title=title,  # type: ignore[arg-type]
               caption=caption, files=files, round=rnd)
    return db.put_visual(v)


# ---------------------------------------------------------------------------
# Concept explainer
# ---------------------------------------------------------------------------


def concept(seed_id: str, spec: ConceptSpec, rnd: int) -> Visual:
    steps = {s.id: s for s in spec.steps}
    edges = [e for e in spec.edges if e.source in steps and e.target in steps and e.source != e.target]
    if not edges:
        ids = list(steps)
        edges = [_edge(a, b) for a, b in zip(ids, ids[1:])]

    # depth = longest path from a root, ignoring back edges (DFS order)
    order = list(steps)
    depth = {sid: 0 for sid in order}
    forward = [(e.source, e.target) for e in edges if order.index(e.target) > order.index(e.source)]
    for _ in range(len(order)):
        for a, b in forward:
            depth[b] = max(depth[b], depth[a] + 1)
    lanes = list(dict.fromkeys(s.group or "" for s in spec.steps))
    use_lanes = len(lanes) > 1
    slot: dict[tuple[int, int], int] = {}
    raw: dict[str, tuple[int, int, int]] = {}
    max_col = max(depth.values()) if depth else 0
    wrap_cols = 4 if not use_lanes and max_col >= 5 else max_col + 1
    for sid in order:
        col = depth[sid]
        lane = lanes.index(steps[sid].group or "") if use_lanes else 0
        if not use_lanes and col >= wrap_cols:
            col, lane = col - wrap_cols, lane + 1
        k = (lane, col)
        sub = slot.get(k, 0)
        slot[k] = sub + 1
        raw[sid] = (col, lane, sub)
    # compact lanes: each lane is only as tall as its busiest column
    lane_height: dict[int, int] = {}
    for (lane, _), n in slot.items():
        lane_height[lane] = max(lane_height.get(lane, 1), n)
    lane_start, acc = {}, 0
    for lane in sorted(lane_height):
        lane_start[lane] = acc
        acc += lane_height[lane]
    pos: dict[str, tuple[int, int]] = {sid: (c, lane_start[lane] + s) for sid, (c, lane, s) in raw.items()}

    bw, bh, gx, gy = 196, 86, 50, 34
    left, top = 40 + (96 if use_lanes else 0), 118
    cols = max(c for c, _ in pos.values()) + 1
    rows = max(r for _, r in pos.values()) + 1
    w = max(720, left + cols * (bw + gx) + 10)
    h = top + rows * (bh + gy) + 100
    out = [
        f'<text x="40" y="44" font-size="20" font-weight="650" fill="{INK}">{esc(spec.title)}</text>',
        f'<rect x="40" y="60" width="{w - 80}" height="34" rx="8" fill="{GREEN_LIGHT}"/>',
        f'<text x="54" y="82" font-size="13.5" fill="{GREEN_DARK}" font-weight="600">Key insight: '
        f'<tspan font-weight="400" fill="{INK}">{esc(spec.key_insight[:150])}</tspan></text>',
    ]

    def box_xy(sid: str) -> tuple[float, float]:
        c, r = pos[sid]
        return left + c * (bw + gx), top + r * (bh + gy)

    if use_lanes:
        lane_rows: dict[str, list[int]] = {}
        for sid, (c, r) in pos.items():
            lane_rows.setdefault(steps[sid].group or "", []).append(r)
        for lane, rs in lane_rows.items():
            y0 = top + min(rs) * (bh + gy) - 10
            y1 = top + max(rs) * (bh + gy) + bh + 10
            out.append(f'<rect x="28" y="{y0}" width="{w - 56}" height="{y1 - y0}" rx="10" fill="#fafafa" stroke="{LINE}"/>')
            out.append(f'<text x="40" y="{(y0 + y1) / 2 + 4}" font-size="11" fill="{SUB}" font-weight="600" '
                       f'letter-spacing="0.06em">{esc(lane.upper()[:14])}</text>')

    for e in edges:
        ax, ay = box_xy(e.source)
        bx, by = box_xy(e.target)
        back = order.index(e.target) <= order.index(e.source)
        if back:
            sx, sy = ax + bw / 2, ay + bh
            tx, ty = bx + bw / 2, by + bh
            low = max(sy, ty) + 34
            d = f"M{sx},{sy} C{sx},{low} {tx},{low} {tx},{ty + 2}"
            lx, ly = (sx + tx) / 2, low - 4
        elif abs(ay - by) < 1:
            sx, sy, tx, ty = ax + bw, ay + bh / 2, bx - 2, by + bh / 2
            d = f"M{sx},{sy} L{tx},{ty}"
            lx, ly = (sx + tx) / 2, sy - 7
        else:
            sx, sy, tx, ty = ax + bw, ay + bh / 2, bx - 2, by + bh / 2
            mx = (sx + tx) / 2
            d = f"M{sx},{sy} C{mx},{sy} {mx},{ty} {tx},{ty}"
            lx, ly = mx, (sy + ty) / 2 - 6
        dash = ' stroke-dasharray="5 4"' if back else ""
        out.append(f'<path d="{d}" fill="none" stroke="{SUB}" stroke-width="1.4" marker-end="url(#arr)"{dash}/>')
        if e.label:
            out.append(f'<text x="{lx}" y="{ly}" font-size="11" fill="{SUB}" text-anchor="middle" '
                       f'paint-order="stroke" stroke="#fff" stroke-width="4">{esc(e.label)}</text>')

    for i, s in enumerate(spec.steps):
        x, y = box_xy(s.id)
        fill = GREEN if i == 0 else "#ffffff"
        stroke = GREEN if i == 0 else "#d4d4d4"
        tcol = "#ffffff" if i == 0 else INK
        dcol = "#eafff3" if i == 0 else SUB
        out.append(f'<rect x="{x}" y="{y}" width="{bw}" height="{bh}" rx="10" fill="{fill}" stroke="{stroke}" stroke-width="1.2"/>')
        out.append(f'<text x="{x + 12}" y="{y + 22}" font-size="13" font-weight="650" fill="{tcol}">{esc(clip(s.label, 25))}</text>')
        detail = wrap(s.detail, 32)
        if len(detail) > 4:
            detail = detail[:3] + [clip(" ".join(detail[3:]), 31)]
        for j, line in enumerate(detail):
            out.append(f'<text x="{x + 12}" y="{y + 40 + j * 14}" font-size="11" fill="{dcol}">{esc(line)}</text>')

    cy = h - 50
    cap = wrap(spec.caption, max(60, int((w - 80) / 6.6)))
    for j, line in enumerate(cap[:3]):
        out.append(f'<text x="40" y="{cy + j * 16}" font-size="12.5" fill="{SUB}">{esc(line)}</text>')
    svg = _svg(int(w), int(h), "\n".join(out), spec.title)

    mmd = ["flowchart LR"]
    for s in spec.steps:
        mmd.append(f'  {s.id}["<b>{_mm(s.label)}</b><br/><small>{_mm(s.detail)}</small>"]')
    for e in edges:
        arrow = "-.->" if order.index(e.target) <= order.index(e.source) else "-->"
        mmd.append(f"  {e.source} {arrow}{'|' + _mm(e.label) + '|' if e.label else ''} {e.target}")
    mmd.append(f"  style {spec.steps[0].id} fill:{GREEN},color:#fff,stroke:{GREEN}")
    files = {
        "svg": _save(seed_id, "concept.svg", svg),
        "mermaid": _save(seed_id, "concept.mmd", "\n".join(mmd) + "\n"),
        "json": _save(seed_id, "concept.json", spec.model_dump_json(indent=2)),
    }
    return _register(seed_id, "concept", f"How it works: {spec.title}", spec.caption or spec.key_insight, files, rnd)


def _edge(a: str, b: str) -> Any:
    from ..schemas import ConceptEdge

    return ConceptEdge(source=a, target=b)


def _mm(s: str) -> str:
    return (s or "").replace('"', "'").replace("|", "/").replace("[", "(").replace("]", ")")


# ---------------------------------------------------------------------------
# Landscape map
# ---------------------------------------------------------------------------


def landscape(seed_id: str, sources: list[ExplorationNode], directions: list[ExplorationNode], rnd: int,
              title: str = "") -> Visual:
    items = [(n, f"{n.title} {n.summary} {n.data.get('abstract', '')[:600]}") for n in sources]
    items += [(n, f"{n.title} {n.summary} {n.data.get('description', '')} {' '.join(n.data.get('technologies', []))}")
              for n in directions]
    vecs = text.tfidf([t for _, t in items])
    pts = text.project_2d(vecs)
    w, h, pad_l, pad_t, pw, ph = 900, 640, 40, 88, 600, 500
    out = [
        f'<text x="40" y="44" font-size="20" font-weight="650" fill="{INK}">Landscape{": " + esc(title[:60]) if title else ""}</text>',
        f'<text x="40" y="66" font-size="12.5" fill="{SUB}">Existing work (dots) vs. directions (numbered). Nearby means similar; '
        f'halos show where work is dense.</text>',
        f'<rect x="{pad_l}" y="{pad_t}" width="{pw}" height="{ph}" rx="10" fill="#fcfcfc" stroke="{LINE}"/>',
    ]

    def xy(p: tuple[float, float]) -> tuple[float, float]:
        return pad_l + p[0] * pw, pad_t + p[1] * ph

    src_pts = [(n, xy(p)) for (n, _), p in zip(items, pts) if n.kind.value == "source"]
    dir_pts = [(n, xy(p)) for (n, _), p in zip(items, pts) if n.kind.value == "direction"]
    for _, (x, y) in src_pts:
        out.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="46" fill="url(#halo)"/>')
    for n, (x, y) in src_pts:
        kind = n.data.get("kind", "paper")
        col = KIND_COLORS.get(kind, "#3a8dff")
        out.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="5" fill="{col}" fill-opacity="0.85"><title>{esc(n.title)}</title></circle>')

    gap_id = ""
    active = [(n, p) for n, p in dir_pts if n.status != NodeStatus.pruned]
    if active and src_pts:
        def min_d(p: tuple[float, float]) -> float:
            return min(math.dist(p, q) for _, q in src_pts)
        gap_id = max(active, key=lambda t: min_d(t[1]))[0].id
    ranked = sorted(dir_pts, key=lambda t: ({"top": 0, "active": 1, "pruned": 2}[t[0].status.value], -(t[0].score or 0)))
    numbered = [(i + 1, n, p) for i, (n, p) in enumerate(ranked) if n.status != NodeStatus.pruned]
    for n, (x, y) in ranked[::-1]:
        if n.status == NodeStatus.pruned:
            out.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="6" fill="#fff" stroke="{MUTED}" stroke-width="1.4" '
                       f'stroke-dasharray="3 2"><title>{esc(n.title)} (pruned: {esc(n.reason)})</title></circle>')
    for num, n, (x, y) in numbered[::-1]:
        top_ = n.status == NodeStatus.top
        if n.id == gap_id:
            out.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="22" fill="none" stroke="{GREEN}" stroke-width="1.5" stroke-dasharray="4 3"/>')
            out.append(f'<text x="{x:.1f}" y="{y - 27:.1f}" font-size="10.5" font-weight="700" fill="{GREEN_DARK}" '
                       f'text-anchor="middle" letter-spacing="0.08em">GAP</text>')
        out.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="11" fill="{GREEN if top_ else "#7fd1a6"}" stroke="#fff" stroke-width="2">'
                   f'<title>{esc(n.title)}</title></circle>')
        out.append(f'<text x="{x:.1f}" y="{y + 4:.1f}" font-size="11" font-weight="700" fill="#fff" text-anchor="middle">{num}</text>')

    lx = pad_l + pw + 26
    out.append(f'<text x="{lx}" y="{pad_t + 14}" font-size="12" font-weight="650" fill="{INK}">Legend</text>')
    rows = [("circle", KIND_COLORS["paper"], "paper"), ("circle", KIND_COLORS["repo"], "repository"),
            ("circle", KIND_COLORS["post"], "post / discussion"), ("circle", KIND_COLORS["web"], "web"),
            ("dir", GREEN, "recommended direction"), ("dir", "#7fd1a6", "candidate direction"),
            ("pruned", MUTED, "pruned direction")]
    for i, (shape, col, label) in enumerate(rows):
        yy = pad_t + 38 + i * 22
        if shape == "circle":
            out.append(f'<circle cx="{lx + 6}" cy="{yy - 4}" r="5" fill="{col}"/>')
        elif shape == "dir":
            out.append(f'<circle cx="{lx + 6}" cy="{yy - 4}" r="7" fill="{col}" stroke="{GREEN_DARK}"/>')
        else:
            out.append(f'<circle cx="{lx + 6}" cy="{yy - 4}" r="7" fill="#fff" stroke="{col}" stroke-dasharray="3 2"/>')
        out.append(f'<text x="{lx + 20}" y="{yy}" font-size="11.5" fill="{SUB}">{label}</text>')
    dir_y = pad_t + 38 + len(rows) * 22 + 18
    out.append(f'<text x="{lx}" y="{dir_y}" font-size="12" font-weight="650" fill="{INK}">Directions</text>')
    yy = dir_y + 22
    for num, n, _ in numbered[:9]:
        top_ = n.status == NodeStatus.top
        out.append(f'<circle cx="{lx + 7}" cy="{yy - 4}" r="8" fill="{GREEN if top_ else "#7fd1a6"}"/>')
        out.append(f'<text x="{lx + 7}" y="{yy}" font-size="9.5" font-weight="700" fill="#fff" text-anchor="middle">{num}</text>')
        for j, line in enumerate(wrap(n.title, 26)[:2]):
            out.append(f'<text x="{lx + 21}" y="{yy + j * 14}" font-size="11.5" fill="{INK if top_ else SUB}" '
                       f'font-weight="{600 if top_ else 400}">{esc(line)}</text>')
        yy += 14 * min(2, len(wrap(n.title, 26))) + 10
    n_pruned = sum(1 for n, _ in dir_pts if n.status == NodeStatus.pruned)
    out.append(f'<text x="{lx}" y="{yy + 6}" font-size="11" fill="{MUTED}">{len(src_pts)} sources · {n_pruned} pruned (hover)</text>')
    svg = _svg(w, h, "\n".join(out), "Landscape map")

    traces = []
    for kind in sorted({n.data.get("kind", "paper") for n, _ in src_pts}):
        sel = [(n, p) for n, p in src_pts if n.data.get("kind", "paper") == kind]
        traces.append({
            "type": "scatter", "mode": "markers", "name": kind,
            "x": [round((p[0] - pad_l) / pw, 4) for _, p in sel], "y": [round(1 - (p[1] - pad_t) / ph, 4) for _, p in sel],
            "text": [n.title for n, _ in sel], "hovertemplate": "%{text}<extra>" + kind + "</extra>",
            "marker": {"size": 8, "color": KIND_COLORS.get(kind, "#3a8dff"), "opacity": 0.8},
        })
    for status, color, name in (("top", GREEN, "recommended"), ("active", "#7fd1a6", "candidate"), ("pruned", MUTED, "pruned")):
        sel = [(n, p) for n, p in dir_pts if n.status.value == status]
        if sel:
            traces.append({
                "type": "scatter", "mode": "markers+text", "name": name, "textposition": "bottom center",
                "x": [round((p[0] - pad_l) / pw, 4) for _, p in sel], "y": [round(1 - (p[1] - pad_t) / ph, 4) for _, p in sel],
                "text": [n.title for n, _ in sel],
                "marker": {"size": 16 if status == "top" else 12, "color": color, "line": {"color": GREEN_DARK, "width": 1},
                           "symbol": "circle-open" if status == "pruned" else "circle"},
            })
    plot = {"data": traces, "layout": {
        "title": {"text": "Landscape map"}, "showlegend": True, "hovermode": "closest",
        "xaxis": {"visible": False}, "yaxis": {"visible": False}, "margin": {"l": 10, "r": 10, "t": 40, "b": 10},
        "paper_bgcolor": "rgba(0,0,0,0)", "plot_bgcolor": "rgba(0,0,0,0)"}}
    files = {
        "svg": _save(seed_id, "landscape.svg", svg),
        "plotly": _save(seed_id, "landscape.plotly.json", json.dumps(plot)),
        "html": _save(seed_id, "landscape.html", _plotly_html("Landscape map", plot)),
    }
    caption = "Where existing work sits and where the gap is. Positions come from text similarity of titles and abstracts."
    return _register(seed_id, "landscape", "Landscape map", caption, files, rnd)


def _plotly_html(title: str, plot: dict) -> str:
    return (
        f"<!doctype html><html><head><meta charset='utf-8'><title>{esc(title)}</title>"
        "<script src='https://cdn.jsdelivr.net/npm/plotly.js-basic-dist-min@2.35.2/plotly-basic.min.js'></script>"
        f"</head><body style='margin:0;font-family:{FONT}'><div id='p' style='width:100vw;height:100vh'></div>"
        f"<script>Plotly.newPlot('p', {json.dumps(plot['data'])}, {json.dumps(plot['layout'])}, {{responsive:true}});</script>"
        "<noscript>Open landscape.svg for the static version.</noscript></body></html>"
    )


# ---------------------------------------------------------------------------
# Score chart
# ---------------------------------------------------------------------------


def scores(seed_id: str, directions: list[ExplorationNode], rnd: int) -> Visual | None:
    rows = [d for d in directions if d.data.get("scores")]
    if not rows:
        return None
    rows.sort(key=lambda d: (d.status == NodeStatus.pruned, -(d.score or 0)))
    metrics = [("novelty", "Novelty", "#3a8dff"), ("feasibility", "Feasibility", GREEN),
               ("room", "Room (1 − crowded)", "#da9100"), ("interest", "Interest", "#9c5cff")]
    label_w, bar_w, row_h = 280, 112, 54
    w = 40 + label_w + len(metrics) * (bar_w + 18) + 90
    h = 120 + len(rows) * row_h + 30
    out = [
        f'<text x="40" y="44" font-size="20" font-weight="650" fill="{INK}">Direction scores</text>',
        f'<text x="40" y="66" font-size="12.5" fill="{SUB}">Grounded checks per direction. Overall blends them by tier and your learned preferences.</text>',
    ]
    x0 = 40 + label_w
    for i, (_, name, col) in enumerate(metrics):
        x = x0 + i * (bar_w + 18)
        out.append(f'<text x="{x}" y="100" font-size="11.5" font-weight="600" fill="{col}">{name}</text>')
    out.append(f'<text x="{x0 + len(metrics) * (bar_w + 18)}" y="100" font-size="11.5" font-weight="600" fill="{INK}">Overall</text>')
    for r, d in enumerate(rows):
        y = 116 + r * row_h
        sc = d.data["scores"]
        pruned = d.status == NodeStatus.pruned
        if r % 2 == 0:
            out.append(f'<rect x="28" y="{y - 6}" width="{w - 56}" height="{row_h - 4}" rx="8" fill="#fafafa"/>')
        tag = "★ " if d.status == NodeStatus.top else ""
        out.append(f'<text x="40" y="{y + 16}" font-size="13" font-weight="600" fill="{MUTED if pruned else INK}">'
                   f'{esc(clip(tag + d.title, 36))}<title>{esc(d.title)}</title></text>')
        sub_ = "pruned — " + clip(d.reason, 36) if pruned else f"round {d.round}"
        out.append(f'<text x="40" y="{y + 33}" font-size="11" fill="{MUTED}">{esc(sub_)}<title>{esc(d.reason)}</title></text>')
        for i, (key, _, col) in enumerate(metrics):
            val = (1 - sc.get("crowdedness", 0.5)) if key == "room" else sc.get(key, 0)
            x = x0 + i * (bar_w + 18)
            out.append(f'<rect x="{x}" y="{y + 8}" width="{bar_w}" height="14" rx="7" fill="#eeeeee"/>')
            out.append(f'<rect x="{x}" y="{y + 8}" width="{max(4, bar_w * val):.1f}" height="14" rx="7" fill="{MUTED if pruned else col}"/>')
            out.append(f'<text x="{x}" y="{y + 38}" font-size="10.5" fill="{SUB}">{val:.2f}</text>')
        ov = sc.get("overall", d.score or 0)
        ox = x0 + len(metrics) * (bar_w + 18) + 22
        out.append(f'<circle cx="{ox}" cy="{y + 15}" r="17" fill="{MUTED if pruned else GREEN}" fill-opacity="{0.25 + 0.75 * ov:.2f}"/>')
        out.append(f'<text x="{ox}" y="{y + 19}" font-size="11" font-weight="700" fill="#fff" text-anchor="middle">{ov:.2f}</text>')
    svg = _svg(int(w), int(h), "\n".join(out), "Direction scores")
    files = {"svg": _save(seed_id, "scores.svg", svg)}
    return _register(seed_id, "scores", "Direction scores", "Novelty, feasibility, room and interest per direction.", files, rnd)


# ---------------------------------------------------------------------------
# Smoke results
# ---------------------------------------------------------------------------


def smoke(seed_id: str, checks: list[SmokeCheck]) -> Visual | None:
    done = [c for c in checks if c.status in ("passed", "failed") and c.metrics]
    if not done:
        return None
    rows = [(c, k, v) for c in done for k, v in list(c.metrics.items())[:6]]
    w, row_h = 820, 34
    h = 100 + len(rows) * row_h + 20
    vmax = max(abs(v) for _, _, v in rows) or 1.0
    out = [f'<text x="40" y="44" font-size="20" font-weight="650" fill="{INK}">Smoke checks</text>',
           f'<text x="40" y="66" font-size="12.5" fill="{SUB}">Small tests of key assumptions, run locally with your approval.</text>']
    for i, (c, k, v) in enumerate(rows):
        y = 92 + i * row_h
        col = GREEN if c.status == "passed" else "#d94654"
        out.append(f'<text x="40" y="{y + 14}" font-size="12" fill="{INK}">{esc(c.assumption[:44])}</text>')
        out.append(f'<text x="40" y="{y + 28}" font-size="10.5" fill="{SUB}">{esc(k)}</text>')
        out.append(f'<rect x="420" y="{y + 4}" width="300" height="14" rx="7" fill="#eeeeee"/>')
        out.append(f'<rect x="420" y="{y + 4}" width="{max(4, 300 * abs(v) / vmax):.1f}" height="14" rx="7" fill="{col}"/>')
        out.append(f'<text x="730" y="{y + 16}" font-size="11.5" fill="{INK}">{v:g}</text>')
    svg = _svg(w, h, "\n".join(out), "Smoke checks")
    files = {"svg": _save(seed_id, "smoke.svg", svg)}
    return _register(seed_id, "smoke", "Smoke-check results", "Metrics reported by approved smoke checks.", files, 0)


# ---------------------------------------------------------------------------
# Exploration graph export
# ---------------------------------------------------------------------------


def graph_mermaid(seed_id: str) -> str:
    nodes = db.list_nodes(seed_id)
    edges = db.list_edges(seed_id)
    keep = {n.id for n in nodes if n.kind.value != "source" or n.status != NodeStatus.pruned}
    lines = ["flowchart LR"]
    for n in nodes:
        if n.id not in keep:
            continue
        shape = {"seed": ('(["', '"])'), "direction": ('["', '"]'), "source": ('[/"', '"/]'),
                 "check": ('{{"', '"}}'), "smoke": ('[["', '"]]')}.get(n.kind.value, ('("', '")'))
        lines.append(f"  {n.id}{shape[0]}{_mm(n.title[:48])}{shape[1]}")
    for e in edges:
        if e["src"] in keep and e["dst"] in keep:
            lines.append(f"  {e['src']} --> {e['dst']}")
    for n in nodes:
        if n.id in keep:
            if n.status == NodeStatus.pruned:
                lines.append(f"  style {n.id} fill:#f5f5f5,color:#a1a1a1,stroke:#d4d4d4,stroke-dasharray:3")
            elif n.status == NodeStatus.top:
                lines.append(f"  style {n.id} fill:{GREEN},color:#fff,stroke:{GREEN_DARK}")
    return "\n".join(lines) + "\n"


def graph(seed_id: str, rnd: int) -> Visual:
    files = {"mermaid": _save(seed_id, "graph.mmd", graph_mermaid(seed_id))}
    return _register(seed_id, "graph", "Exploration graph", "Everything explored for this seed; pruned branches dimmed.", files, rnd)
