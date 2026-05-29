from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from valor_auto_agent.config import load
from valor_auto_agent.db.models import Base

_engine: Engine | None = None
_factory: sessionmaker[Session] | None = None


def engine() -> Engine:
    global _engine, _factory
    if _engine is not None:
        return _engine
    url = load().db_url
    if url.startswith("sqlite:///"):
        Path(url.removeprefix("sqlite:///")).parent.mkdir(parents=True, exist_ok=True)
    _engine = create_engine(url, future=True)
    Base.metadata.create_all(_engine)
    _factory = sessionmaker(_engine, expire_on_commit=False)
    return _engine


@contextmanager
def session() -> Iterator[Session]:
    engine()
    assert _factory is not None
    s = _factory()
    try:
        yield s
        s.commit()
    except Exception:
        s.rollback()
        raise
    finally:
        s.close()
