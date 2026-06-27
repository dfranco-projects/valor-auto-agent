from __future__ import annotations

import asyncio
import logging
import re
from urllib.parse import quote_plus

from selectolax.parser import HTMLParser

from valor_auto_agent.config import load
from valor_auto_agent.tools.crawler.base import fetch_html, with_browser
from valor_auto_agent.tools.crawler.schemas import Filters, Listing

BASE = "https://www.olx.pt"
log = logging.getLogger(__name__)


def build_url(filters: Filters, page: int = 1) -> str:
    path = "/d/carros-motos-e-barcos/carros"
    if filters.brand:
        path += f"/{quote_plus(filters.brand.lower())}"
    qp: list[str] = []
    if filters.price_min is not None:
        qp.append(f"search%5Bfilter_float_price%3Afrom%5D={filters.price_min}")
    if filters.price_max is not None:
        qp.append(f"search%5Bfilter_float_price%3Ato%5D={filters.price_max}")
    if filters.year_min is not None:
        qp.append(f"search%5Bfilter_float_year%3Afrom%5D={filters.year_min}")
    if filters.year_max is not None:
        qp.append(f"search%5Bfilter_float_year%3Ato%5D={filters.year_max}")
    if filters.km_max is not None:
        qp.append(f"search%5Bfilter_float_mileage%3Ato%5D={filters.km_max}")
    if filters.model:
        qp.append(f"search%5Bfilter_enum_modelo%5D%5B0%5D={quote_plus(filters.model.lower())}")
    if filters.fuel:
        qp.append(f"search%5Bfilter_enum_combustivel%5D%5B0%5D={filters.fuel}")
    if filters.transmission:
        qp.append(f"search%5Bfilter_enum_transmissao%5D%5B0%5D={filters.transmission}")
    if page > 1:
        qp.append(f"page={page}")
    qs = "&".join(qp)
    return f"{BASE}{path}/{'?' + qs if qs else ''}"


_PRICE_RX = re.compile(r"(\d[\d\s.]*)\s*€")
_NUM_RX = re.compile(r"\d+")


def _int(s: str | None) -> int | None:
    if not s:
        return None
    m = _NUM_RX.findall(s.replace(".", "").replace(",", ""))
    return int("".join(m)) if m else None


def parse_cards(html: str) -> list[Listing]:
    # selectors target stable data-cy attributes used by olx group; fall back to structural
    tree = HTMLParser(html)
    out: list[Listing] = []
    for card in tree.css('div[data-cy="l-card"], div[data-testid="l-card"]'):
        a = card.css_first("a")
        if a is None:
            continue
        href = a.attributes.get("href") or ""
        url = href if href.startswith("http") else f"{BASE}{href}"
        title_el = card.css_first('h4, h6, [data-cy="ad-card-title"]')
        title = (title_el.text(strip=True) if title_el else "").strip()
        price_el = card.css_first('[data-testid="ad-price"], p.price')
        price = None
        if price_el:
            m = _PRICE_RX.search(price_el.text())
            price = _int(m.group(1)) if m else None
        params_el = card.css_first('[data-testid="ad-card-params"], ul')
        year = km = None
        fuel = None
        if params_el:
            text = params_el.text(separator=" ", strip=True).lower()
            ym = re.search(r"(19|20)\d{2}", text)
            year = int(ym.group(0)) if ym else None
            kmm = re.search(r"(\d{1,3}(?:[\s. ]\d{3})*|\d{4,7})\s*km", text)
            km = _int(kmm.group(1)) if kmm else None
            for f in ("gasolina", "diesel", "hibrido", "eletrico", "gpl"):
                if f in text:
                    fuel = f
                    break
        loc_el = card.css_first('[data-testid="location-date"], p.location')
        location = loc_el.text(strip=True) if loc_el else None

        external_id = ""
        for tok in href.split("/")[::-1]:
            if tok.startswith("ID") or tok.endswith(".html"):
                external_id = tok
                break
        if not external_id:
            external_id = href

        out.append(
            Listing(
                source="olx",
                external_id=external_id,
                title=title,
                price_eur=price,
                year=year,
                km=km,
                fuel=fuel,  # type: ignore[arg-type]
                location=location,
                url=url,
            )
        )
    return out


async def search(filters: Filters, max_pages: int | None = None) -> list[Listing]:
    settings = load()
    max_pages = max_pages or settings.max_pages
    found: dict[str, Listing] = {}
    async with with_browser() as ctx:
        for page in range(1, max_pages + 1):
            url = build_url(filters, page=page)
            log.info("olx fetch page %d %s", page, url)
            html = await fetch_html(ctx, url)
            if not html:
                log.warning("olx page %d returned no html (blocked or timed out)", page)
                break
            cards = parse_cards(html)
            log.info("olx page %d -> %d cards", page, len(cards))
            if not cards:
                break
            for c in cards:
                found.setdefault(c.external_id, c)
            await asyncio.sleep(1.0)
    return list(found.values())
