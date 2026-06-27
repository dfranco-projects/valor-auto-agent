from __future__ import annotations

import asyncio
import json
import logging
import re
from urllib.parse import quote_plus

from selectolax.parser import HTMLParser

from valor_auto_agent.config import load
from valor_auto_agent.tools.crawler.base import fetch_html, with_browser
from valor_auto_agent.tools.crawler.schemas import Filters, Listing

BASE = "https://www.standvirtual.com"
log = logging.getLogger(__name__)

# standvirtual fuel/gearbox slugs -> our enum values
_FUEL_MAP = {
    "petrol": "gasolina",
    "gasoline": "gasolina",
    "diesel": "diesel",
    "hybrid": "hibrido",
    "plugin-hybrid": "hibrido",
    "hybrid-petrol": "hibrido",
    "hybrid-diesel": "hibrido",
    "electric": "eletrico",
    "lpg": "gpl",
    "petrol-lpg": "gpl",
}
_GEARBOX_MAP = {"automatic": "automatica", "manual": "manual"}
# our enum values -> standvirtual url slugs (for the search filters)
_URL_FUEL = {
    "gasolina": "petrol",
    "diesel": "diesel",
    "hibrido": "hybrid",
    "eletrico": "electric",
    "gpl": "lpg",
}
_URL_GEARBOX = {"automatica": "automatic", "manual": "manual"}


def build_url(filters: Filters, page: int = 1) -> str:
    path = "/carros"
    if filters.brand:
        path += f"/{quote_plus(filters.brand.lower())}"
        if filters.model:
            path += f"/{quote_plus(filters.model.lower())}"
    qp: list[str] = []
    if filters.price_min is not None:
        qp.append(f"search%5Bfilter_float_price%3Afrom%5D={filters.price_min}")
    if filters.price_max is not None:
        qp.append(f"search%5Bfilter_float_price%3Ato%5D={filters.price_max}")
    if filters.year_min is not None:
        qp.append(f"search%5Bfilter_float_first_registration_year%3Afrom%5D={filters.year_min}")
    if filters.year_max is not None:
        qp.append(f"search%5Bfilter_float_first_registration_year%3Ato%5D={filters.year_max}")
    if filters.km_max is not None:
        qp.append(f"search%5Bfilter_float_mileage%3Ato%5D={filters.km_max}")
    if filters.fuel:
        qp.append(
            f"search%5Bfilter_enum_fuel_type%5D%5B0%5D={_URL_FUEL.get(filters.fuel, filters.fuel)}"
        )
    if filters.transmission:
        gearbox = _URL_GEARBOX.get(filters.transmission, filters.transmission)
        qp.append(f"search%5Bfilter_enum_gearbox%5D%5B0%5D={gearbox}")
    if page > 1:
        qp.append(f"page={page}")
    qs = "&".join(qp)
    return f"{BASE}{path}/{'?' + qs if qs else ''}"


_NUM_RX = re.compile(r"\d+")


def _int(s: str | None) -> int | None:
    if not s:
        return None
    m = _NUM_RX.findall(s.replace(".", "").replace(",", "").replace("\xa0", " "))
    return int("".join(m)) if m else None


def _node_to_listing(node: dict) -> Listing | None:
    url = node.get("url")
    if not url:
        return None
    params = {p.get("key"): p.get("value") for p in node.get("parameters") or []}
    amount = ((node.get("price") or {}).get("amount")) or {}
    price = int(amount["units"]) if amount.get("units") is not None else None
    city = ((node.get("location") or {}).get("city") or {}).get("name")
    return Listing(
        source="standvirtual",
        external_id=str(node.get("id") or url),
        title=node.get("title") or "",
        price_eur=price,
        year=_int(params.get("first_registration_year")),
        km=_int(params.get("mileage")),
        fuel=_FUEL_MAP.get((params.get("fuel_type") or "").lower()),  # type: ignore[arg-type]
        transmission=_GEARBOX_MAP.get((params.get("gearbox") or "").lower()),  # type: ignore[arg-type]
        location=city,
        url=url,
    )


def parse_cards(html: str) -> list[Listing]:
    # standvirtual is a next.js app: ads are embedded as json (urql cache), not rendered
    # into the static html, so parse the __NEXT_DATA__ payload instead of the dom
    nd = HTMLParser(html).css_first("script#__NEXT_DATA__")
    if nd is None:
        return []
    try:
        urql = json.loads(nd.text())["props"]["pageProps"].get("urqlState") or {}
    except (json.JSONDecodeError, KeyError, TypeError):
        return []
    out: list[Listing] = []
    for entry in urql.values():
        data = entry.get("data") if isinstance(entry, dict) else None
        if not data or "advertSearch" not in data:
            continue
        try:
            edges = json.loads(data)["advertSearch"]["edges"]
        except (json.JSONDecodeError, KeyError, TypeError):
            continue
        for edge in edges:
            li = _node_to_listing(edge.get("node") or {})
            if li is not None:
                out.append(li)
    return out


async def search(filters: Filters, max_pages: int | None = None) -> list[Listing]:
    settings = load()
    max_pages = max_pages or settings.max_pages
    found: dict[str, Listing] = {}
    async with with_browser() as ctx:
        for page in range(1, max_pages + 1):
            url = build_url(filters, page=page)
            log.info("standvirtual fetch page %d %s", page, url)
            html = await fetch_html(ctx, url)
            if not html:
                log.warning("standvirtual page %d returned no html (blocked or timed out)", page)
                break
            cards = parse_cards(html)
            log.info("standvirtual page %d -> %d cards", page, len(cards))
            if not cards:
                break
            for c in cards:
                found.setdefault(c.external_id, c)
            await asyncio.sleep(1.0)
    return list(found.values())
