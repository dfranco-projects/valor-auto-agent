from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from typing import Any

from anthropic import AsyncAnthropic
from langchain_core.messages import AIMessage, HumanMessage
from langgraph.types import interrupt

from valor_auto_agent.config import load
from valor_auto_agent.db.exports import snapshot_search
from valor_auto_agent.db.models import Listing as DbListing
from valor_auto_agent.db.models import Rating as DbRating
from valor_auto_agent.db.models import Search
from valor_auto_agent.db.session import session
from valor_auto_agent.subagents.rater import rate_batch
from valor_auto_agent.tools.crawler import olx, standvirtual
from valor_auto_agent.tools.crawler.schemas import Filters, Listing

CLASSIFY_SYS = (
    "you classify the latest user message. reply with exactly one word: scrape or chat. "
    "scrape = user wants car listings searched on olx/standvirtual. chat = anything else"
)


async def _last_user_text(state: dict) -> str:
    for m in reversed(state.get("messages", [])):
        if isinstance(m, HumanMessage):
            return m.content if isinstance(m.content, str) else str(m.content)
        if isinstance(m, dict) and m.get("type") == "human":
            return str(m.get("content", ""))
    return ""


async def decide(state: dict) -> dict:
    settings = load()
    if not settings.anthropic_api_key:
        # offline default: treat any non-empty user message as a scrape intent
        return {"should_scrape": bool(await _last_user_text(state))}
    client = AsyncAnthropic(api_key=settings.anthropic_api_key)
    text = await _last_user_text(state)
    resp = await client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=10,
        system=CLASSIFY_SYS,
        messages=[{"role": "user", "content": text or "(empty)"}],
    )
    reply = "".join(b.text for b in resp.content if hasattr(b, "text")).strip().lower()
    return {"should_scrape": reply.startswith("scrape")}


async def collect_filters(state: dict) -> dict:
    raw = interrupt({"need": "filters", "schema": Filters.model_json_schema()})
    if isinstance(raw, dict):
        return {"filters": raw}
    return {"filters": {}}


async def scrape(state: dict) -> dict:
    filters = Filters(**(state.get("filters") or {}))
    with session() as s:
        search = Search(
            filters_json=filters.model_dump(exclude_none=True),
            sources="olx,standvirtual",
            scrape_started_at=datetime.now(UTC),
            status="running",
        )
        s.add(search)
        s.flush()
        search_id = search.id

    olx_task = olx.search(filters)
    sv_task = standvirtual.search(filters)
    results = await asyncio.gather(olx_task, sv_task, return_exceptions=True)
    listings: list[Listing] = []
    for r in results:
        if isinstance(r, Exception):
            continue
        listings.extend(r)

    with session() as s:
        for li in listings:
            s.add(
                DbListing(
                    search_id=search_id,
                    source=li.source,
                    external_id=li.external_id,
                    title=li.title,
                    price_eur=li.price_eur,
                    year=li.year,
                    km=li.km,
                    fuel=li.fuel,
                    transmission=li.transmission,
                    location=li.location,
                    url=li.url,
                    image_url=li.image_url,
                    posted_at=li.posted_at,
                    raw_json=li.raw,
                )
            )
        search = s.get(Search, search_id)
        if search is not None:
            search.scrape_ended_at = datetime.now(UTC)
            search.status = "scraped"
        snapshot_search(search_id, s)

    return {
        "search_id": search_id,
        "listings": [li.model_dump(mode="json") for li in listings],
    }


async def rate(state: dict) -> dict:
    raw = state.get("listings") or []
    listings = [Listing(**li) for li in raw]
    if not listings:
        return {"ratings": []}
    model = state.get("rater_model") or load().rater_model
    rated = await rate_batch(listings, model=model)
    search_id = state.get("search_id")
    if search_id:
        with session() as s:
            by_ext = {(r["source"], r["external_id"]): r for r in rated}
            db_listings = s.query(DbListing).filter(DbListing.search_id == search_id).all()
            for dbl in db_listings:
                key = (dbl.source, dbl.external_id)
                r = by_ext.get(key)
                if not r:
                    continue
                s.add(
                    DbRating(
                        listing_id=dbl.id,
                        score=float(r["score"]),
                        rationale=str(r.get("rationale", "")),
                        model=model,
                    )
                )
            search = s.get(Search, search_id)
            if search is not None:
                search.status = "rated"
            snapshot_search(search_id, s)
    return {"ratings": rated}


async def present(state: dict) -> dict:
    listings = {(li["source"], li["external_id"]): li for li in state.get("listings", [])}
    ratings = state.get("ratings") or []
    enriched: list[dict[str, Any]] = []
    for r in ratings:
        key = (r["source"], r["external_id"])
        li = listings.get(key)
        if not li:
            continue
        enriched.append(
            {
                "score": float(r["score"]),
                "rationale": r.get("rationale", ""),
                "title": li.get("title"),
                "price_eur": li.get("price_eur"),
                "year": li.get("year"),
                "km": li.get("km"),
                "source": li.get("source"),
                "url": li.get("url"),
            }
        )
    enriched.sort(key=lambda x: x["score"], reverse=True)
    top = enriched[:10]
    summary = _format_top(top)
    return {"top": top, "reply": summary, "messages": [AIMessage(content=summary)]}


async def chat(state: dict) -> dict:
    settings = load()
    text = await _last_user_text(state)
    if not settings.anthropic_api_key:
        msg = "anthropic api key not set — i can only scrape when configured"
        return {"reply": msg, "messages": [AIMessage(content=msg)]}
    client = AsyncAnthropic(api_key=settings.anthropic_api_key)
    resp = await client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=400,
        system="you are a helpful assistant for a portuguese used-car shopper",
        messages=[{"role": "user", "content": text or "(empty)"}],
    )
    out = "".join(b.text for b in resp.content if hasattr(b, "text")).strip()
    return {"reply": out, "messages": [AIMessage(content=out)]}


def _format_top(top: list[dict]) -> str:
    if not top:
        return "no listings matched the filters"
    lines = ["here are the top picks:"]
    for i, t in enumerate(top, 1):
        price = f"{t['price_eur']}€" if t.get("price_eur") else "n/a"
        lines.append(
            f"{i}. [{t['score']:.1f}] {t['title']} — {price} · {t.get('year') or ''} · "
            f"{t.get('km') or ''}km · {t['source']} — {t['url']}"
        )
    return "\n".join(lines)


def _serialize_for_state(li: Listing) -> dict:
    d = li.model_dump(mode="json")
    return d


def route_decide(state: dict) -> str:
    return "collect_filters" if state.get("should_scrape") else "chat"
