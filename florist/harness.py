"""`florist agent`: open an interactive coding-agent session that drives Florist.

Mirrors OpenResearch's harness pattern: the agent gets a playbook appended to its system prompt
(``PLAYBOOK.md`` rendered with live state) and drives Florist through the ``florist`` CLI.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from . import gateway, paths, profile
from .store import db


def playbook(seed_ref: str = "") -> Path:
    tpl = (paths.RESOURCES / "PLAYBOOK.md").read_text(encoding="utf-8")
    seeds = db.list_seeds()
    lines = [f"- `{s.slug}` — {s.title} ({s.tier.value}, {s.state.value}, priority {s.priority})" for s in seeds[:20]]
    focus = ""
    if seed_ref:
        s = db.get_seed(seed_ref)
        if s:
            focus = f"\n\n**Focus seed:** `{s.slug}` — {s.title}\n\n{s.prompt}\n"
    text = (tpl.replace("{profile}", profile.brief())
               .replace("{seeds}", "\n".join(lines) or "- (no seeds yet)")
               .replace("{focus}", focus)
               .replace("{home}", str(paths.home())))
    out = paths.home() / "playbook.rendered.md"
    out.write_text(text, encoding="utf-8")
    return out


def launch(harness: str = "claude", seed_ref: str = "", prompt: str = "") -> int:
    pb = playbook(seed_ref)
    if harness == "claude":
        exe = gateway.find_binary("claude")
        if not exe:
            raise SystemExit("claude CLI not found — install Claude Code first")
        cmd = [exe, "--append-system-prompt-file", str(pb), "--add-dir", str(paths.home()),
               "--allowedTools", "Bash(florist:*)", "Bash(uv run florist:*)"]
        if prompt:
            cmd.append(prompt)
        return subprocess.call(cmd, cwd=paths.RESOURCES)
    if harness == "codex":
        exe = gateway.find_binary("codex")
        if not exe:
            raise SystemExit("codex CLI not found")
        instr = pb.read_text(encoding="utf-8")
        return subprocess.call([exe, "-c", f"developer_instructions={instr!r}", *([prompt] if prompt else [])],
                               cwd=paths.RESOURCES)
    raise SystemExit("harness must be claude or codex")
