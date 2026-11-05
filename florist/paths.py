"""Filesystem layout.

Two roots:

* ``RESOURCES`` — the repository (or installed tree) holding versioned files that
  are part of the product: ``skills/``, ``schemas/``, ``adapters/``, ``app/dist``.
* ``home()`` — the user's local-first data directory (default ``~/.florist``,
  override with ``FLORIST_HOME``): SQLite database, ``profile.yaml``,
  ``settings.yaml``, caches, visuals, smoke checks and picked packs.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# In a PyInstaller build the data files live next to the bundled modules (sys._MEIPASS).
_BUNDLE = Path(getattr(sys, "_MEIPASS", "")) if getattr(sys, "frozen", False) else None
RESOURCES = Path(os.environ.get("FLORIST_RESOURCES") or _BUNDLE or Path(__file__).resolve().parent.parent)


def home() -> Path:
    root = Path(os.environ.get("FLORIST_HOME") or Path.home() / ".florist")
    root.mkdir(parents=True, exist_ok=True)
    return root


def db_path() -> Path:
    return home() / "florist.db"


def profile_path() -> Path:
    return home() / "profile.yaml"


def settings_path() -> Path:
    return home() / "settings.yaml"


def sub(*parts: str) -> Path:
    p = home().joinpath(*parts)
    p.mkdir(parents=True, exist_ok=True)
    return p


def skills_dir() -> Path:
    return RESOURCES / "skills"


def schemas_dir() -> Path:
    return RESOURCES / "schemas"


def adapters_dir() -> Path:
    return RESOURCES / "adapters"


def ui_dist() -> Path:
    return RESOURCES / "app" / "dist"


def migrations_dir() -> Path:
    return Path(__file__).resolve().parent / "store" / "migrations"
