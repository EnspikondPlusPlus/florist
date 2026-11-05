import itertools

import pytest

from florist import config, research
from florist.store import db

_counter = itertools.count()


def fake_search(query, kind="paper", limit=6, since=None, tool=None, log=None):
    n = next(_counter)
    k = "repo" if kind == "repo" else kind
    return [
        research.Hit(tool="fake", kind=k, external_id=f"{n}-{i}", title=f"{query.title()} study {n}-{i}",
                     url=f"https://example.org/{n}/{i}", abstract=f"We study {query} with method {i}. "
                     f"Results show speedups on benchmark {i}.", year=2025 - i)
        for i in range(min(limit, 3))
    ]


@pytest.fixture(autouse=True)
def florist_home(tmp_path, monkeypatch):
    monkeypatch.setenv("FLORIST_HOME", str(tmp_path / "home"))
    db.reset_connection()
    config._cache = None
    config.update({"models": {"default": "mock", "fast": "mock", "strong": "mock"}, "auto_fetch_feed": False})
    monkeypatch.setattr(research, "search", fake_search)
    monkeypatch.setattr(research, "crowdedness", lambda q, months=18: {"total": 120, "recent": 30, "since": "2025-01-01"})
    yield tmp_path / "home"
    db.reset_connection()
