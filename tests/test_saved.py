from __future__ import annotations

import importlib
from datetime import UTC, datetime, timedelta

import pytest

from valor_auto_agent.db import session as session_mod
from valor_auto_agent.tools.crawler.schemas import Listing


@pytest.fixture
def db(tmp_path, monkeypatch):
    monkeypatch.setenv("VALOR_DB_URL", f"sqlite:///{tmp_path}/t.db")
    monkeypatch.setenv("VALOR_SNAPSHOTS_DIR", str(tmp_path / "snaps"))
    session_mod._engine = None
    session_mod._factory = None
    importlib.reload(session_mod)
    yield


def _li(ext: str, source: str = "olx", price: int = 9000) -> Listing:
    return Listing(
        source=source,  # type: ignore[arg-type]
        external_id=ext,
        title="bmw 320d",
        price_eur=price,
        url=f"https://example.pt/{ext}",
    )


def test_create_list_delete(db):
    from valor_auto_agent import saved

    a = saved.create_saved("bmws", {"brand": "bmw"})
    saved.create_saved("audis", {"brand": "audi"})
    rows = saved.list_saved()
    assert {r["name"] for r in rows} == {"bmws", "audis"}
    assert all(r["new_count"] == 0 for r in rows)

    saved.delete_saved(a["id"])
    assert {r["name"] for r in saved.list_saved()} == {"audis"}


def test_due_saved_cadence(db):
    from valor_auto_agent import saved
    from valor_auto_agent.db.models import SavedSearch

    ss = saved.create_saved("x", {"brand": "bmw"}, cadence_minutes=60)
    assert ss["id"] in saved.due_saved()  # never run -> due

    with session_mod.session() as s:
        s.get(SavedSearch, ss["id"]).last_run_at = datetime.now(UTC)
    assert ss["id"] not in saved.due_saved()  # just ran -> not due

    with session_mod.session() as s:
        s.get(SavedSearch, ss["id"]).last_run_at = datetime.now(UTC) - timedelta(hours=2)
    assert ss["id"] in saved.due_saved()  # cadence elapsed -> due


async def test_run_saved_alerts_on_new_only(db, monkeypatch):
    from valor_auto_agent import saved

    listings = [_li("1"), _li("2", source="standvirtual")]

    async def fake_crawl(_filters):
        return listings

    async def fake_rate(ls, model=None):
        return [
            {"source": li.source, "external_id": li.external_id, "score": 7.5, "rationale": "ok"}
            for li in ls
        ]

    monkeypatch.setattr("valor_auto_agent.pipeline.crawl", fake_crawl)
    monkeypatch.setattr("valor_auto_agent.saved.rate_batch", fake_rate)

    ss = saved.create_saved("bmws", {"brand": "bmw"}, cadence_minutes=60)

    # first run is a baseline: existing listings are remembered, not alerted on
    assert await saved.run_saved(ss["id"]) == []
    assert await saved.run_saved(ss["id"]) == []  # still nothing new

    # a fresh listing appears -> exactly one new alert, scored
    listings.append(_li("3"))
    new = await saved.run_saved(ss["id"])
    assert [a["external_id"] for a in new] == ["3"]
    assert new[0]["score"] == 7.5

    assert saved.list_saved()[0]["new_count"] == 1
    alerts = saved.list_alerts()
    assert len(alerts) == 1
    saved.mark_alert_read(alerts[0]["id"])
    assert saved.list_alerts(unread_only=True) == []
