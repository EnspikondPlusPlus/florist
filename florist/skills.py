"""Skill files: prompts and rubrics per loop step live in ``skills/<name>/SKILL.md``.

The same files serve two drivers:

* the built-in loop renders ``system = shared preamble + skill body`` and calls the gateway;
* an external coding agent (Claude Code, Codex) reads them via ``florist skill <name>``
  or ``florist round next`` and submits the output with ``florist round submit``.

Skills marked ``agent: true`` in front matter are the ones installed into a coding
agent's skills folder by ``florist skills install``.
"""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path

import yaml

from . import paths


@dataclass
class Skill:
    name: str
    description: str
    body: str
    path: Path
    meta: dict

    @property
    def agent_facing(self) -> bool:
        return bool(self.meta.get("agent"))


def _parse(path: Path) -> Skill:
    text = path.read_text(encoding="utf-8")
    meta: dict = {}
    body = text
    if text.startswith("---"):
        _, fm, body = text.split("---", 2)
        meta = yaml.safe_load(fm) or {}
    return Skill(
        name=meta.get("name", path.parent.name),
        description=meta.get("description", ""),
        body=body.strip(),
        path=path,
        meta=meta,
    )


def all_skills() -> list[Skill]:
    root = paths.skills_dir()
    return [_parse(p) for p in sorted(root.glob("*/SKILL.md"))]


def get(name: str) -> Skill:
    root = paths.skills_dir()
    for cand in (name, f"florist-{name}", f"florist-{name.replace('_', '-')}"):
        p = root / cand / "SKILL.md"
        if p.exists():
            return _parse(p)
    raise KeyError(f"no skill named {name!r} in {root}")


def for_step(step: str) -> Skill:
    return get(f"florist-{step.replace('_', '-')}")


def shared_preamble() -> str:
    p = paths.skills_dir() / "_shared" / "SYSTEM.md"
    return p.read_text(encoding="utf-8").strip() if p.exists() else ""


def system_prompt(step: str) -> str:
    return f"{shared_preamble()}\n\n{for_step(step).body}"


def cli_overview() -> str:
    return (paths.RESOURCES / "SKILL.md").read_text(encoding="utf-8")


def install(target: str = "claude", project_dir: Path | None = None) -> list[Path]:
    """Copy agent-facing skills (plus the CLI overview) into a coding agent's skills folder.

    target: ``claude`` → ``~/.claude/skills``; ``codex`` → ``~/.codex/skills``;
    ``project`` → ``<project_dir>/.claude/skills``.
    """
    if target == "claude":
        dest_root = Path.home() / ".claude" / "skills"
    elif target == "codex":
        dest_root = Path.home() / ".codex" / "skills"
    elif target == "project":
        dest_root = (project_dir or Path.cwd()) / ".claude" / "skills"
    else:
        raise ValueError("target must be claude, codex or project")
    written = []
    overview = dest_root / "florist"
    overview.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(paths.RESOURCES / "SKILL.md", overview / "SKILL.md")
    written.append(overview / "SKILL.md")
    for s in all_skills():
        if not s.agent_facing:
            continue
        d = dest_root / s.name
        d.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(s.path, d / "SKILL.md")
        written.append(d / "SKILL.md")
    return written
