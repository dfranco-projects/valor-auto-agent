from __future__ import annotations

import importlib

import pytest

from valor_auto_agent.db import session as session_mod


@pytest.fixture
def db(tmp_path, monkeypatch):
    monkeypatch.setenv("VALOR_DB_URL", f"sqlite:///{tmp_path}/t.db")
    monkeypatch.setenv("VALOR_SNAPSHOTS_DIR", str(tmp_path / "snaps"))
    session_mod._engine = None
    session_mod._factory = None
    importlib.reload(session_mod)
    yield


def test_recall_empty(db):
    from valor_auto_agent import memory

    assert memory.recall_defaults() == {}


def test_remember_and_recall(db):
    from valor_auto_agent import memory

    memory.remember({"brand": "bmw", "price_max": 10000, "model": "320d"})
    got = memory.recall_defaults()
    assert got["brand"] == "bmw"
    assert got["price_max"] == 10000
    # model is intentionally not remembered (too query-specific)
    assert "model" not in got


def test_remember_last_wins_and_retains(db):
    from valor_auto_agent import memory

    memory.remember({"brand": "bmw", "price_max": 10000})
    memory.remember({"brand": "audi"})
    got = memory.recall_defaults()
    assert got["brand"] == "audi"  # last value wins
    assert got["price_max"] == 10000  # prior pref retained


def test_remember_ignores_empty(db):
    from valor_auto_agent import memory

    memory.remember({})
    memory.remember({"brand": "", "price_max": None})
    assert memory.recall_defaults() == {}
