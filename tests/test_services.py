from __future__ import annotations

import importlib

import pytest

from valor_auto_agent.db import session as session_mod


@pytest.fixture
def db(tmp_path, monkeypatch):
    monkeypatch.setenv("VALOR_DB_URL", f"sqlite:///{tmp_path}/t.db")
    monkeypatch.setenv("VALOR_CHECKPOINT_DB", str(tmp_path / "c.db"))
    monkeypatch.setenv("VALOR_SNAPSHOTS_DIR", str(tmp_path / "snaps"))
    session_mod._engine = None
    session_mod._factory = None
    importlib.reload(session_mod)
    yield


def _seed_car(s, source, external_id, score, model, filters=None):
    from valor_auto_agent.db.models import Listing, Rating, Search

    search = Search(filters_json=filters or {"brand": "bmw"}, sources="olx", status="done")
    s.add(search)
    s.flush()
    li = Listing(
        search_id=search.id,
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
    s.add(Rating(listing_id=li.id, score=score, rationale="ok", model=model))
    s.flush()


def test_list_evaluations_dedups_to_latest_rating(db):
    from backend.services.evaluations import list_evaluations
    from valor_auto_agent.db.session import session

    with session() as s:
        _seed_car(s, "olx", "car1", 7.0, "claude-sonnet-4-6")  # earlier search
        _seed_car(s, "olx", "car1", 9.0, "gemini-2.5-flash")  # re-searched, newer

    rows = list_evaluations()
    assert len(rows) == 1
    assert rows[0]["score"] == 9.0
    assert rows[0]["rated_by"] == "gemini-2.5-flash"
    assert rows[0]["brand"] == "bmw"


def test_set_decision_upserts(db):
    from backend.services.evaluations import list_evaluations, set_decision
    from valor_auto_agent.db.session import session

    with session() as s:
        _seed_car(s, "olx", "car1", 8.0, "claude-sonnet-4-6")

    set_decision("olx", "car1", "shortlist", "call seller")
    set_decision("olx", "car1", "rejected", "too pricey")

    row = list_evaluations()[0]
    assert row["status"] == "rejected"
    assert row["notes"] == "too pricey"


def test_status_filter(db):
    from backend.services.evaluations import list_evaluations, set_decision
    from valor_auto_agent.db.session import session

    with session() as s:
        _seed_car(s, "olx", "car1", 8.0, "claude-sonnet-4-6")
        _seed_car(s, "standvirtual", "car2", 6.0, "claude-sonnet-4-6")

    set_decision("olx", "car1", "shortlist", "")

    assert [r["external_id"] for r in list_evaluations(statuses=["shortlist"])] == ["car1"]
    assert [r["external_id"] for r in list_evaluations(statuses=["unset"])] == ["car2"]


def test_pref_roundtrip(db):
    from backend.services.sessions import load_pref, new_thread, save_pref

    assert load_pref() == {"active_thread_id": None, "rater_model": None}

    save_pref(rater_model="gemini-2.5-flash")
    assert load_pref()["rater_model"] == "gemini-2.5-flash"

    tid = new_thread()
    pref = load_pref()
    assert pref["active_thread_id"] == tid
    assert pref["rater_model"] == "gemini-2.5-flash"  # new_thread keeps the model
