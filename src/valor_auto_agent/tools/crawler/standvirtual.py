from __future__ import annotations

import asyncio
import re
from urllib.parse import quote_plus

from selectolax.parser import HTMLParser

from valor_auto_agent.config import load
from valor_auto_agent.tools.crawler.base import fetch_html, with_browser
from valor_auto_agent.tools.crawler.schemas import Filters, Listing

BASE = "https://www.standvirtual.com"


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
        qp.append(f"search%5Bfilter_enum_fuel_type%5D%5B0%5D={filters.fuel}")
    if filters.transmission:
        qp.append(f"search%5Bfilter_enum_gearbox%5D%5B0%5D={filters.transmission}")
    if page > 1:
        qp.append(f"page={page}")
    qs = "&".join(qp)
    return f"{BASE}{path}/{'?' + qs if qs else ''}"


_PRICE_RX = re.compile(r"(\d[\d\s.]*)\s*€")
_NUM_RX = re.compile(r"\d+")


def _int(s: str | None) -> int | None:
    if not s:
        return None
    m = _NUM_RX.findall(s.replace(".", "").replace(",", "").replace("\xa0", " "))
    return int("".join(m)) if m else None


def parse_cards(html: str) -> list[Listing]:
    tree = HTMLParser(html)
    out: list[Listing] = []
    for art in tree.css('article[data-testid="listing-ad"], article.ooa-1yux8sr'):
        a = art.css_first('h1 a, h2 a, a[data-testid="listing-link"]')
        if a is None:
            continue
        href = a.attributes.get("href") or ""
        url = href if href.startswith("http") else f"{BASE}{href}"
        title = a.text(strip=True)
        price_el = art.css_first('[data-testid="ad-price"], h3[class*="price"]')
        price = None
        if price_el:
            m = _PRICE_RX.search(price_el.text())
            price = _int(m.group(1)) if m else None
        params = art.css('dd, [data-testid="ad-params"] li')
        year = km = None
        fuel = None
        transmission = None
        for p in params:
            txt = p.text(strip=True).lower()
            if not year:
                ym = re.search(r"(19|20)\d{2}", txt)
                if ym:
                    year = int(ym.group(0))
            if not km:
                kmm = re.search(r"(\d{1,3}(?:[\s. ]\d{3})*|\d{4,7})\s*km", txt)
                if kmm:
                    km = _int(kmm.group(1))
            for f in ("gasolina", "diesel", "hibrido", "eletrico", "gpl"):
                if f in txt:
                    fuel = f
            # "automat" doesn't match accented "automática" via substring — use shorter prefix
            if "autom" in txt:
                transmission = "automatica"
            elif "manual" in txt:
                transmission = "manual"
        loc_el = art.css_first('[data-testid="location-date"], p[class*="location"]')
        location = loc_el.text(strip=True) if loc_el else None
        external_id = art.attributes.get("data-id") or art.attributes.get("id") or href

        out.append(
            Listing(
                source="standvirtual",
                external_id=external_id,
                title=title,
                price_eur=price,
                year=year,
                km=km,
                fuel=fuel,  # type: ignore[arg-type]
                transmission=transmission,  # type: ignore[arg-type]
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
            html = await fetch_html(ctx, url)
            if not html:
                break
            cards = parse_cards(html)
            if not cards:
                break
            for c in cards:
                found.setdefault(c.external_id, c)
            await asyncio.sleep(1.0)
    return list(found.values())
