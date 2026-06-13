from __future__ import annotations

from sqlalchemy import select

from valor_auto_agent.db.models import Evaluation, Listing, Rating, Search
from valor_auto_agent.db.session import session

STATUSES = ["shortlist", "maybe", "rejected"]


def list_evaluations(
    *,
    search: str | None = None,
    sources: list[str] | None = None,
    min_score: float | None = None,
    statuses: list[str] | None = None,
) -> list[dict]:
    # one row per car (source, external_id) carrying its latest rating + decision
    with session() as s:
        rows = s.execute(
            select(Listing, Rating, Search)
            .join(Rating, Rating.listing_id == Listing.id)
            .join(Search, Search.id == Listing.search_id)
            .order_by(Listing.id.desc())
        ).all()
        decisions = {(e.source, e.external_id): e for e in s.scalars(select(Evaluation)).all()}

        seen: set[tuple[str, str]] = set()
        out: list[dict] = []
        for li, rating, srch in rows:
            key = (li.source, li.external_id)
            if key in seen:  # id-desc order means the first hit is the most recent rating
                continue
            seen.add(key)
            dec = decisions.get(key)
            filters = srch.filters_json or {}
            out.append(
                {
                    "source": li.source,
                    "external_id": li.external_id,
                    "brand": filters.get("brand"),
                    "model": filters.get("model"),
                    "title": li.title,
                    "year": li.year,
                    "km": li.km,
                    "price_eur": li.price_eur,
                    "fuel": li.fuel,
                    "transmission": li.transmission,
                    "location": li.location,
                    "score": rating.score,
                    "rationale": rating.rationale,
                    "rated_by": rating.model,
                    "rated_at": rating.created_at.isoformat() if rating.created_at else None,
                    "status": dec.status if dec else None,
                    "notes": dec.notes if dec else "",
                    "url": li.url,
                }
            )

    def keep(r: dict) -> bool:
        if search:
            hay = " ".join(
                str(r.get(k) or "") for k in ("title", "brand", "model", "location")
            ).lower()
            if search.lower() not in hay:
                return False
        if sources and r["source"] not in sources:
            return False
        if min_score is not None and (r["score"] or 0) < min_score:
            return False
        return not (statuses and (r["status"] or "unset") not in statuses)

    kept = [r for r in out if keep(r)]
    kept.sort(key=lambda r: r["score"] or 0, reverse=True)
    return kept


def set_decision(source: str, external_id: str, status: str | None, notes: str) -> None:
    with session() as s:
        ev = s.scalars(
            select(Evaluation).where(
                Evaluation.source == source, Evaluation.external_id == external_id
            )
        ).first()
        if ev is None:
            ev = Evaluation(source=source, external_id=external_id)
            s.add(ev)
        ev.status = status or None
        ev.notes = notes or ""
