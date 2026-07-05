from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from valor_auto_agent import pipeline
from valor_auto_agent.config import load
from valor_auto_agent.db.models import Alert, SavedSearch
from valor_auto_agent.db.session import run_db, session
from valor_auto_agent.subagents.rater import rate_batch
from valor_auto_agent.tools.crawler.schemas import Filters

log = logging.getLogger(__name__)
DEFAULT_USER = "default"


def _key(source: str, external_id: str) -> str:
    return f"{source}:{external_id}"


def _saved_dict(ss: SavedSearch, new_count: int) -> dict:
    return {
        "id": ss.id,
        "name": ss.name,
        "filters": ss.filters_json,
        "cadence_minutes": ss.cadence_minutes,
        "active": ss.active,
        "last_run_at": ss.last_run_at.isoformat() if ss.last_run_at else None,
        "new_count": new_count,
    }


def _alert_dict(a: Alert) -> dict:
    return {
        "id": a.id,
        "saved_search_id": a.saved_search_id,
        "source": a.source,
        "external_id": a.external_id,
        "title": a.title,
        "price_eur": a.price_eur,
        "year": a.year,
        "km": a.km,
        "url": a.url,
        "score": a.score,
        "rationale": a.rationale,
        "read": a.read,
        "created_at": a.created_at.isoformat() if a.created_at else None,
    }


def create_saved(
    name: str, filters: dict, cadence_minutes: int = 360, user_id: str = DEFAULT_USER
) -> dict:
    with session() as s:
        ss = SavedSearch(
            user_id=user_id,
            name=name,
            filters_json=filters or {},
            cadence_minutes=cadence_minutes,
            seen_ids_json=[],
        )
        s.add(ss)
        s.flush()
        return _saved_dict(ss, 0)


def list_saved(user_id: str = DEFAULT_USER) -> list[dict]:
    with session() as s:
        rows = (
            s.query(SavedSearch)
            .filter(SavedSearch.user_id == user_id)
            .order_by(SavedSearch.created_at.desc())
            .all()
        )
        out = []
        for ss in rows:
            unread = (
                s.query(Alert).filter(Alert.saved_search_id == ss.id, Alert.read.is_(False)).count()
            )
            out.append(_saved_dict(ss, unread))
        return out


def delete_saved(saved_id: int) -> None:
    with session() as s:
        ss = s.get(SavedSearch, saved_id)
        if ss is not None:
            s.delete(ss)


def due_saved(now: datetime | None = None) -> list[int]:
    now = now or datetime.now(UTC)
    with session() as s:
        ids: list[int] = []
        for ss in s.query(SavedSearch).filter(SavedSearch.active.is_(True)).all():
            if ss.last_run_at is None:
                ids.append(ss.id)
                continue
            last = ss.last_run_at
            if last.tzinfo is None:
                last = last.replace(tzinfo=UTC)
            if now - last >= timedelta(minutes=ss.cadence_minutes):
                ids.append(ss.id)
        return ids


async def run_saved(saved_id: int, rater_model: str | None = None) -> list[dict]:
    """crawl a saved search, alert on listings not seen before, return the new alerts."""

    def _load(s: Session) -> tuple[Filters, set[str], bool] | None:
        ss = s.get(SavedSearch, saved_id)
        if ss is None:
            return None
        return (
            Filters(**(ss.filters_json or {})),
            set(ss.seen_ids_json or []),
            ss.last_run_at is None,
        )

    loaded = await run_db(_load)
    if loaded is None:
        return []
    filters, seen, first_run = loaded

    listings = await pipeline.crawl(filters)

    if first_run:
        # baseline run: remember what's already listed without alerting, so future runs
        # only flag listings that appear after the search was created
        keys = {_key(li.source, li.external_id) for li in listings}

        def _baseline(s: Session) -> None:
            ss = s.get(SavedSearch, saved_id)
            if ss is not None:
                ss.seen_ids_json = sorted(seen | keys)
                ss.last_run_at = datetime.now(UTC)

        await run_db(_baseline)
        return []

    new = [li for li in listings if _key(li.source, li.external_id) not in seen]
    if not new:

        def _touch(s: Session) -> None:
            ss = s.get(SavedSearch, saved_id)
            if ss is not None:
                ss.last_run_at = datetime.now(UTC)

        await run_db(_touch)
        return []

    model = rater_model or load().rater_model
    try:
        rated = await rate_batch(new, model=model)
    except Exception as e:
        log.warning("saved search %s rating failed: %r", saved_id, e)
        rated = []
    by_ext = {(r["source"], r["external_id"]): r for r in rated}

    def _store(s: Session) -> list[dict]:
        ss = s.get(SavedSearch, saved_id)
        if ss is None:
            return []
        created: list[dict] = []
        for li in new:
            r = by_ext.get((li.source, li.external_id)) or {}
            a = Alert(
                saved_search_id=saved_id,
                source=li.source,
                external_id=li.external_id,
                title=li.title,
                price_eur=li.price_eur,
                year=li.year,
                km=li.km,
                url=li.url,
                score=float(r["score"]) if r.get("score") is not None else None,
                rationale=str(r.get("rationale", "")),
            )
            s.add(a)
            s.flush()
            created.append(_alert_dict(a))
        ss.seen_ids_json = sorted(seen | {_key(li.source, li.external_id) for li in new})
        ss.last_run_at = datetime.now(UTC)
        return created

    return await run_db(_store)


def list_alerts(user_id: str = DEFAULT_USER, unread_only: bool = False) -> list[dict]:
    with session() as s:
        q = (
            s.query(Alert)
            .join(SavedSearch, Alert.saved_search_id == SavedSearch.id)
            .filter(SavedSearch.user_id == user_id)
        )
        if unread_only:
            q = q.filter(Alert.read.is_(False))
        return [_alert_dict(a) for a in q.order_by(Alert.created_at.desc()).all()]


def mark_alert_read(alert_id: int) -> None:
    with session() as s:
        a = s.get(Alert, alert_id)
        if a is not None:
            a.read = True
