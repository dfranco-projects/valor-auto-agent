from __future__ import annotations

import importlib

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from valor_auto_agent.db import session as session_mod
from valor_auto_agent.db.exports import snapshot_search
from valor_auto_agent.db.models import Base, Listing, Rating, Search


@pytest.fixture
def sess(tmp_path, monkeypatch):
    monkeypatch.setenv("VALOR_DB_URL", f"sqlite:///{tmp_path}/t.db")
    monkeypatch.setenv("VALOR_SNAPSHOTS_DIR", str(tmp_path / "snapshots"))
    # reset singletons
    session_mod._engine = None
    session_mod._factory = None
    importlib.reload(session_mod)

    eng = create_engine(f"sqlite:///{tmp_path}/t.db", future=True)
    Base.metadata.create_all(eng)
    Factory = sessionmaker(eng, expire_on_commit=False)
    with Factory() as s:
        yield s


def test_listing_roundtrip(sess):
    search = Search(filters_json={"brand": "bmw"}, sources="olx,standvirtual", status="done")
    sess.add(search)
    sess.flush()

    li = Listing(
        search_id=search.id,
        source="olx",
        external_id="abc",
        title="bmw 320d",
        price_eur=14500,
        year=2018,
        km=120000,
        url="https://olx.pt/x",
    )
    sess.add(li)
    sess.flush()
    sess.add(
        Rating(listing_id=li.id, score=8.5, rationale="solid price", model="claude-sonnet-4-6")
    )
    sess.commit()

    fetched = sess.get(Listing, li.id)
    assert fetched is not None
    assert fetched.rating is not None
    assert fetched.rating.score == 8.5


def test_snapshot_search(tmp_path, sess, monkeypatch):
    monkeypatch.setenv("VALOR_SNAPSHOTS_DIR", str(tmp_path / "snapshots"))

    search = Search(filters_json={"brand": "bmw", "price_max": 15000}, sources="olx", status="done")
    sess.add(search)
    sess.flush()
    sess.add(
        Listing(
            search_id=search.id,
            source="olx",
            external_id="1",
            title="bmw 320d",
            price_eur=14500,
            year=2018,
            km=120000,
            url="https://olx.pt/x",
        )
    )
    sess.commit()

    path = snapshot_search(search.id, sess)
    text = path.read_text()
    assert "# search" in text
    assert "bmw 320d" in text
    assert "filters" in text
