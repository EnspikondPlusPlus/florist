"""The user profile.

Two files, one source of truth:

* ``profile.md`` — **the user's document.** Plain markdown you can paste into from a CV, a
  website or notes: about you, interests, skills, compute, time, how you work. One section,
  between ``<!-- florist:begin -->`` and ``<!-- florist:end -->``, is maintained by Florist
  (learned preferences); everything else is yours. This text is read into every prompt.
* ``profile.yaml`` — **Florist's structured copy**, derived from ``profile.md`` after every save
  (headings parsed deterministically, then refined by the ``florist-profile-sync`` skill when a
  model is available), plus machine knobs: greenhouse downtime, fold threshold, learned weights.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

from . import paths
from .schemas import Profile, ProfileSync

HEADER = """\
# Florist's structured profile — derived from profile.md (edit that file instead).
# Knobs below (downtime, thresholds, learned_preferences) are managed in the app.
"""

EXAMPLE = Profile(
    name="",
    interests=["efficient inference", "robotics", "data visualization"],
    proficient_in=["Python", "PyTorch", "React"],
    wants_to_learn=["Rust", "reinforcement learning"],
    work_preferences=["small steps", "prefers simple baselines", "likes visual explanations"],
)

BEGIN = "<!-- florist:begin -->"
END = "<!-- florist:end -->"


# ---------------------------------------------------------------------------
# profile.yaml
# ---------------------------------------------------------------------------


def load() -> Profile:
    p = paths.profile_path()
    if not p.exists():
        save(EXAMPLE)
        return EXAMPLE.model_copy(deep=True)
    data = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    prof = Profile.model_validate(data)
    if prof.downtime.enabled and prof.downtime.mode == "stop" and "mode" not in (data.get("downtime") or {}):
        prof.downtime.mode = "scheduled"  # migrate the old boolean
    return prof


def save(profile: Profile) -> None:
    text = yaml.safe_dump(profile.model_dump(mode="json"), sort_keys=False, allow_unicode=True, width=100)
    paths.profile_path().write_text(HEADER + text, encoding="utf-8")


def update(patch: dict[str, Any]) -> Profile:
    cur = load().model_dump(mode="json")
    for k, v in patch.items():
        if isinstance(v, dict) and isinstance(cur.get(k), dict):
            cur[k] = {**cur[k], **v}
        else:
            cur[k] = v
    prof = Profile.model_validate(cur)
    save(prof)
    return prof


def export_to(dest: Path) -> Path:
    dest = Path(dest)
    dest.write_text(load_doc(), encoding="utf-8")
    return dest


def import_from(src: Path) -> Profile:
    text = Path(src).read_text(encoding="utf-8")
    if Path(src).suffix in (".yaml", ".yml"):
        prof = Profile.model_validate(yaml.safe_load(text) or {})
        save(prof)
        return prof
    return save_doc(text)


def raw_yaml() -> str:
    load()
    return paths.profile_path().read_text(encoding="utf-8")


def save_raw_yaml(text: str) -> Profile:
    prof = Profile.model_validate(yaml.safe_load(text) or {})  # raises on invalid input; nothing written
    save(prof)
    return prof


# ---------------------------------------------------------------------------
# profile.md — the user's document
# ---------------------------------------------------------------------------


def doc_path() -> Path:
    return paths.home() / "profile.md"


def _bullets(items: list[str]) -> str:
    return "\n".join(f"- {x}" for x in items) or "- "


def _initial_doc(p: Profile) -> str:
    about = ""
    legacy = paths.home() / "about.md"
    if legacy.exists():
        about = re.sub(r"<!--.*?-->", "", legacy.read_text(encoding="utf-8"), flags=re.S)
        about = "\n".join(ln for ln in about.splitlines() if not ln.startswith("#")).strip()
    return f"""# My profile

## About me
{about or "Who you are, what you work on, what excites you. Paste a bio or CV snippet here."}

## Interests
{_bullets(p.interests)}

## Proficient in
{_bullets(p.proficient_in)}

## Want to learn
{_bullets(p.wants_to_learn)}

## Compute and budget
- {p.resources.compute or "e.g. 1x RTX 4090, no cluster"}
- API budget: ${p.resources.budget_usd_month:g}/month

## Time and goals
- {p.time.hours_per_week:g} h/week
- Goal date: {p.time.goal_date or "—"}

## Conferences
{_bullets(p.conference_targets)}

## How I like to work
{_bullets(p.work_preferences)}

{BEGIN}
## Florist's notes
_Learned from what you save, dismiss, boost and pick. Florist rewrites this section; edit anything
above freely._
{END}
"""


def load_doc() -> str:
    p = doc_path()
    if not p.exists():
        p.write_text(_initial_doc(load()), encoding="utf-8")
    return p.read_text(encoding="utf-8")


_SECTIONS = [
    ("interests", ("interest",)),
    ("proficient_in", ("proficien", "skill", "good at", "know")),
    ("wants_to_learn", ("learn",)),
    ("conference_targets", ("conference", "venue")),
    ("work_preferences", ("how i like", "work style", "preference", "working")),
    ("_compute", ("compute", "budget", "hardware", "resources")),
    ("_time", ("time", "goal", "deadline", "schedule")),
]


def _user_part(text: str) -> str:
    return re.sub(re.escape(BEGIN) + r".*?" + re.escape(END), "", text, flags=re.S)


def parse_doc(text: str) -> dict[str, Any]:
    """Deterministic heading parser: '## Interests' + bullets/commas → fields."""
    sections: dict[str, list[str]] = {}
    current = None
    for line in _user_part(re.sub(r"<!--.*?-->", "", text, flags=re.S)).splitlines():
        h = re.match(r"^#{1,4}\s+(.*)", line)
        if h:
            title = h.group(1).strip().lower()
            current = next((key for key, keys in _SECTIONS if any(k in title for k in keys)), None)
            continue
        if current and line.strip():
            sections.setdefault(current, []).append(line.strip())

    def items(lines: list[str]) -> list[str]:
        out: list[str] = []
        for ln in lines:
            ln = re.sub(r"^([-*+]|\d+[.)])\s*", "", ln).strip()
            if not ln or ln.startswith("_") or ln in ("—", "-"):
                continue
            parts = [x.strip(" .;") for x in re.split(r",|;", ln)] if len(ln) < 160 else [ln]
            out += [x for x in parts if x and len(x) < 120]
        return list(dict.fromkeys(out))

    fields: dict[str, Any] = {k: items(v) for k, v in sections.items() if not k.startswith("_")}
    compute = " ".join(sections.get("_compute", []))
    if compute:
        lines = [re.sub(r"^[-*+]\s*", "", x) for x in sections["_compute"]]
        fields["compute"] = next((x for x in lines if not re.search(r"budget|\$", x, re.I)), lines[0])[:160]
        m = re.search(r"\$\s?(\d+(?:\.\d+)?)", compute)
        if m:
            fields["budget_usd_month"] = float(m.group(1))
    tim = " ".join(sections.get("_time", []))
    if tim:
        m = re.search(r"(\d+(?:\.\d+)?)\s*(?:h|hrs?|hours?)\b", tim, re.I)
        if m:
            fields["hours_per_week"] = float(m.group(1))
        m = re.search(r"(\d{4}-\d{2}-\d{2})", tim)
        if m:
            fields["goal_date"] = m.group(1)
    return fields


def _apply_fields(prof: Profile, f: dict[str, Any]) -> Profile:
    for k in ("interests", "proficient_in", "wants_to_learn", "conference_targets", "work_preferences"):
        if f.get(k):
            setattr(prof, k, f[k])
    if f.get("compute"):
        prof.resources.compute = f["compute"]
    if f.get("budget_usd_month") is not None:
        prof.resources.budget_usd_month = float(f["budget_usd_month"])
    if f.get("hours_per_week") is not None:
        prof.time.hours_per_week = float(f["hours_per_week"])
    if f.get("goal_date"):
        prof.time.goal_date = f["goal_date"]
    return prof


def save_doc(text: str) -> Profile:
    """Save the user's document and re-derive the structured profile from it."""
    if BEGIN not in text:  # keep Florist's section even if the user pasted over everything
        text = text.rstrip() + "\n\n" + _florist_section(load())
    doc_path().write_text(text, encoding="utf-8")
    prof = _apply_fields(load(), parse_doc(text))
    save(prof)
    return prof


def sync_with_model() -> Profile | None:
    """Refine profile.yaml from free text with the florist-profile-sync skill (best effort)."""
    from . import gateway, skills

    text = _user_part(load_doc())
    try:
        out = gateway.complete(gateway.Call(step="profile_sync", hints={"topic": "profile"}),
                               skills.system_prompt("profile_sync"), f"## profile.md\n\n{text[:8000]}", ProfileSync)
    except gateway.LLMError:
        return None
    prof = _apply_fields(load(), out.model_dump())
    save(prof)
    return prof


def _florist_section(prof: Profile) -> str:
    statements = [lp for lp in prof.learned_preferences if lp.kind == "statement"]
    weights = sorted([lp for lp in prof.learned_preferences if lp.kind != "statement" and lp.evidence >= 2],
                     key=lambda x: -abs(x.weight))[:10]
    seek = [lp.key for lp in weights if lp.weight > 0.15]
    avoid = [lp.key for lp in weights if lp.weight < -0.15]
    lines = [BEGIN, "## Florist's notes",
             "_Learned from what you save, dismiss, boost and pick. Florist rewrites this section; edit anything "
             "above freely._", ""]
    lines += [f"- {'Likes' if s.weight >= 0 else 'Avoids'}: {s.key}" for s in statements]
    if seek:
        lines.append(f"- Leans toward: {', '.join(seek)}")
    if avoid:
        lines.append(f"- Tends to skip: {', '.join(avoid)}")
    lines.append(END)
    return "\n".join(lines) + "\n"


def refresh_florist_section() -> None:
    text = load_doc()
    new = _florist_section(load())
    if BEGIN in text and END in text:
        text = re.sub(re.escape(BEGIN) + r".*?" + re.escape(END) + r"\n?", new, text, flags=re.S)
    else:
        text = text.rstrip() + "\n\n" + new
    doc_path().write_text(text, encoding="utf-8")


def outline(text: str | None = None) -> list[dict[str, Any]]:
    out = []
    for i, line in enumerate((text if text is not None else load_doc()).splitlines()):
        m = re.match(r"^(#{1,3})\s+(.*)", line)
        if m:
            out.append({"line": i, "level": len(m.group(1)), "title": m.group(2).strip()})
    return out


# Back-compat names used by earlier code paths
def load_about() -> str:
    return load_doc()


def save_about(text: str) -> None:
    save_doc(text)


def about_path() -> Path:
    return doc_path()


def brief(profile: Profile | None = None) -> str:
    """Profile rendering for prompts: the user's own document plus learned weights."""
    p = profile or load()
    doc = re.sub(r"<!--.*?-->", "", load_doc(), flags=re.S).strip()
    doc = re.sub(r"\n{3,}", "\n\n", doc)
    lines = [doc[:3500]]
    learned = sorted([lp for lp in p.learned_preferences if lp.kind != "statement"], key=lambda x: -abs(x.weight))[:10]
    if learned:
        lines.append("Learned weights (+ seek, - avoid): " +
                     "; ".join(f"{lp.kind}:{lp.key} {lp.weight:+.2f}" for lp in learned))
    return "\n".join(lines)
