from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from typing import Any

from anthropic import AsyncAnthropic
from google.genai import types
from langchain_core.messages import AIMessage, HumanMessage
from langgraph.types import interrupt

from valor_auto_agent import pipeline
from valor_auto_agent.config import Settings, load
from valor_auto_agent.db.exports import snapshot_search
from valor_auto_agent.db.models import Evaluation as DbEvaluation
from valor_auto_agent.db.models import Listing as DbListing
from valor_auto_agent.db.models import Rating as DbRating
from valor_auto_agent.db.models import Search
from valor_auto_agent.db.session import session
from valor_auto_agent.memory import recall_defaults, remember
from valor_auto_agent.subagents.rater import _gemini_client, rate_batch
from valor_auto_agent.tools.crawler.schemas import Filters, Listing
from valor_auto_agent.tools.dedupe import also_on

log = logging.getLogger(__name__)

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


EXTRACT_SYS = (
    "extract used-car search filters from the user's message. return only a json object with "
    "the keys you can infer, omit the rest. keys: brand (lowercase slug e.g. bmw, audi, "
    "mercedes-benz, volkswagen), model (lowercase e.g. 320d, golf), year_min, year_max, "
    "price_min, price_max (eur ints), km_max (int), fuel (one of "
    "gasolina,diesel,hibrido,eletrico,gpl), transmission (one of manual,automatica), "
    "location (portuguese city). examples: 'under 10k'/'até 10000€' => price_max=10000; "
    "'from 2015'/'2015+' => year_min=2015; 'auto' => transmission=automatica. "
    "do not invent values that are not implied by the message."
)

_FILTER_KEYS = tuple(Filters.model_fields)


async def _extract_gemini(settings: Settings, text: str) -> str:
    client = _gemini_client(settings)
    resp = await client.aio.models.generate_content(
        model="gemini-2.5-flash",
        contents=text,
        config=types.GenerateContentConfig(
            system_instruction=EXTRACT_SYS,
            response_mime_type="application/json",
        ),
    )
    return resp.text or ""


async def _extract_anthropic(settings: Settings, text: str) -> str:
    client = AsyncAnthropic(api_key=settings.anthropic_api_key)
    resp = await client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=300,
        system=EXTRACT_SYS,
        messages=[
            {"role": "user", "content": text},
            {"role": "assistant", "content": "{"},
        ],
    )
    return "{" + "".join(b.text for b in resp.content if hasattr(b, "text"))


async def _extract(text: str, model: str | None) -> dict:
    settings = load()
    if not text.strip():
        return {}
    model = model or settings.rater_model
    gemini_ok = settings.gemini_api_key or settings.google_genai_use_vertexai
    try:
        if model.startswith("gemini") and gemini_ok:
            raw = await _extract_gemini(settings, text)
        elif settings.anthropic_api_key:
            raw = await _extract_anthropic(settings, text)
        elif gemini_ok:
            raw = await _extract_gemini(settings, text)
        else:
            return {}
        data = json.loads(raw) if raw.strip() else {}
        return data if isinstance(data, dict) else {}
    except Exception as e:
        log.warning("extract_filters failed: %r", e)
        return {}


def _coerce_filters(data: dict) -> dict:
    candidate = {k: data[k] for k in _FILTER_KEYS if data.get(k) not in (None, "")}
    try:
        Filters(**candidate)
        return candidate
    except Exception:
        # drop only the fields that fail validation, keep the rest
        clean: dict = {}
        for k, v in candidate.items():
            try:
                Filters(**{k: v})
                clean[k] = v
            except Exception:
                continue
        return clean


def _humanize(d: dict) -> str:
    return ", ".join(f"{k}={v}" for k, v in d.items())


def _prefill_note(extracted: dict, recalled: dict, prefill: dict) -> str:
    if not prefill:
        return "i couldn't read specific filters — fill the form to start the scrape."
    parts = []
    read = {k: v for k, v in prefill.items() if k in extracted}
    if read:
        parts.append("read: " + _humanize(read))
    from_mem = {k: v for k, v in prefill.items() if k not in extracted and k in recalled}
    if from_mem:
        parts.append("from your usual prefs: " + _humanize(from_mem))
    parts.append("confirm or adjust below.")
    return " · ".join(parts)


async def extract_filters(state: dict) -> dict:
    text = await _last_user_text(state)
    extracted = _coerce_filters(await _extract(text, state.get("rater_model")))
    recalled = recall_defaults()
    prefill = _coerce_filters({**recalled, **extracted})  # nl wins over remembered prefs
    return {"filters_prefill": prefill, "prefill_note": _prefill_note(extracted, recalled, prefill)}


async def collect_filters(state: dict) -> dict:
    raw = interrupt(
        {
            "need": "filters",
            "schema": Filters.model_json_schema(),
            "prefill": state.get("filters_prefill") or {},
            "note": state.get("prefill_note") or "",
        }
    )
    if isinstance(raw, dict):
        remember(raw)
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

    log.info("scrape start filters=%s", filters.model_dump(exclude_none=True))
    listings = await pipeline.crawl(filters)
    log.info("scrape total %d listings", len(listings))

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
    log.info("rate start: %d listings model=%s", len(listings), model)
    rated = await rate_batch(listings, model=model)
    log.info("rate done: %d ratings", len(rated))
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
    raw_listings = [Listing(**li) for li in state.get("listings", [])]
    dup_idx = also_on(raw_listings)
    dups = {
        (raw_listings[i].source, raw_listings[i].external_id): v for i, v in dup_idx.items()
    }
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
                "external_id": li.get("external_id"),
                "url": li.get("url"),
                "also_on": dups.get(key, []),
            }
        )
    enriched.sort(key=lambda x: x["score"], reverse=True)
    top = enriched[:10]
    # reflect any existing shortlist/decision so the ui can show already-saved cars
    if top:
        with session() as s:
            ev = {(e.source, e.external_id): e.status for e in s.query(DbEvaluation).all()}
        for t in top:
            t["status"] = ev.get((t["source"], t["external_id"]))
    log.info(
        "present: %d listings, %d ratings -> %d enriched, %d dup groups, top=%d",
        len(raw_listings),
        len(ratings),
        len(enriched),
        len(dup_idx),
        len(top),
    )
    # keep the chat reply short — the top picks render as cards in the ui, don't dump them as text
    summary = (
        f"found {len(enriched)} matches — here are the top {len(top)}:"
        if top
        else "no listings matched the filters"
    )
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


def _serialize_for_state(li: Listing) -> dict:
    d = li.model_dump(mode="json")
    return d


def route_decide(state: dict) -> str:
    return "extract_filters" if state.get("should_scrape") else "chat"
