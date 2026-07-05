from __future__ import annotations

import asyncio
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from pathlib import Path

from sqlalchemy import Engine, StaticPool, create_engine
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
    kwargs: dict = {}
    if url.startswith("sqlite:///") and ":memory:" not in url:
        Path(url.removeprefix("sqlite:///")).parent.mkdir(parents=True, exist_ok=True)
    if url.startswith("sqlite"):
        # run_db hands session work to worker threads; the pool never gives one
        # connection to two threads at once, so the same-thread check can go
        kwargs["connect_args"] = {"check_same_thread": False}
        if url in ("sqlite://", "sqlite:///:memory:"):
            # in-memory dbs exist per connection: share the single connection
            kwargs["poolclass"] = StaticPool
    _engine = create_engine(url, future=True, **kwargs)
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


async def run_db[T](fn: Callable[[Session], T]) -> T:
    """run session work in a thread so async callers don't block the event loop."""

    def _work() -> T:
        with session() as s:
            return fn(s)

    return await asyncio.to_thread(_work)
