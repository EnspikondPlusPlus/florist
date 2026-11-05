"""Per-seed spec sheet: one editable markdown file that both the user and the loop work from.

Lives at ``~/.florist/seeds/<seed_id>/spec.md``. Created from the seed's fields on first access;
after that it is the user's document — the loop reads it every round (``loop._seed_brief``).
"""

from __future__ import annotations

from pathlib import Path

from .. import paths
from ..schemas import Seed

TEMPLATE = """# {title}

## Idea
{prompt}

## Must have
-

## Out of scope
-

## Constraints
- Time: {time}
- Compute: {compute}
- Must use: {must_use}
- Must avoid: {must_avoid}

## Notes
<!-- Anything else Florist should know: links, prior attempts, who it is for, what "done" looks like. -->
"""


def path(seed: Seed) -> Path:
    return paths.sub("seeds", seed.id) / "spec.md"


def template(seed: Seed) -> str:
    c = seed.constraints
    return TEMPLATE.format(
        title=seed.title, prompt=seed.prompt.strip(), time=c.time or "from profile",
        compute=c.compute or "from profile", must_use=", ".join(c.must_use) or "—",
        must_avoid=", ".join(c.must_avoid) or "—",
    )


def read(seed: Seed) -> str:
    p = path(seed)
    if not p.exists():
        p.write_text(template(seed), encoding="utf-8")
    return p.read_text(encoding="utf-8")


def write(seed: Seed, text: str) -> None:
    path(seed).write_text(text, encoding="utf-8")


def is_customized(seed: Seed, text: str | None = None) -> bool:
    return (text if text is not None else read(seed)).strip() != template(seed).strip()
