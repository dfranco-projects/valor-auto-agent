from __future__ import annotations

import importlib

import pytest
from fastapi.testclient import TestClient

from valor_auto_agent.db import session as session_mod


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("VALOR_DB_URL", f"sqlite:///{tmp_path}/t.db")
    monkeypatch.setenv("VALOR_CHECKPOINT_DB", str(tmp_path / "c.db"))
    monkeypatch.setenv("VALOR_SNAPSHOTS_DIR", str(tmp_path / "snaps"))
    session_mod._engine = None
    session_mod._factory = None
    importlib.reload(session_mod)

    from backend.deps import get_graph

    get_graph.cache_clear()
    from backend.main import create_app

    with TestClient(create_app()) as c:
        yield c


def _seed_rated_car(source="olx", external_id="c1"):
    from valor_auto_agent.db.models import Listing, Rating, Search
    from valor_auto_agent.db.session import session

    with session() as s:
        srch = Search(filters_json={"brand": "bmw"}, sources="olx", status="done")
        s.add(srch)
        s.flush()
        li = Listing(
            search_id=srch.id,
            source=source,
            external_id=external_id,
            title="bmw 320d",
            price_eur=14500,
            year=2018,
            km=120000,
            url="https://olx.pt/x",
        )
        s.add(li)
        s.flush()
        s.add(Rating(listing_id=li.id, score=8.0, rationale="ok", model="claude-sonnet-4-6"))


def test_config_lists_models(client):
    body = client.get("/api/config").json()
    assert "gemini-2.5-flash" in body["models"]
    assert isinstance(body["anthropic_key"], bool)
    assert isinstance(body["gemini_key"], bool)


def test_config_patch_persists_default_model(client):
    client.patch("/api/config", json={"rater_model": "gemini-2.5-pro"})
    assert client.get("/api/config").json()["default_model"] == "gemini-2.5-pro"


def test_evaluations_get_and_decision(client):
    _seed_rated_car()
    assert len(client.get("/api/evaluations").json()) == 1

    r = client.patch(
        "/api/evaluations",
        json={"source": "olx", "external_id": "c1", "status": "shortlist", "notes": "nice"},
    )
    assert r.status_code == 200

    row = client.get("/api/evaluations").json()[0]
    assert row["status"] == "shortlist"
    assert row["notes"] == "nice"


def test_sessions_active_returns_thread(client):
    body = client.get("/api/sessions/active").json()
    assert body["thread_id"]
    assert body["history"] == []
