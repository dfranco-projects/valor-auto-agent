from __future__ import annotations

import asyncio
import logging
import re
from urllib.parse import quote_plus

from selectolax.parser import HTMLParser

from valor_auto_agent.config import load
from valor_auto_agent.tools.crawler.base import extract_apollo_images, fetch_html, with_browser
from valor_auto_agent.tools.crawler.schemas import Detail, Filters, Listing

BASE = "https://www.olx.pt"
_CARD_SEL = 'div[data-cy="l-card"], div[data-testid="l-card"]'
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
    # note: olx rejects the mileage filter param (it returns a zero-results page), and its
    # `filter_enum_modelo` wants a model enum slug (e.g. serie-3) not a version like "320d".
    # both km_max and model are therefore matched after the crawl instead (see pipeline.crawl).
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
# "120 000 km" / "244.000 km" / "5000 km" (\s also matches the nbsp thousands separator olx uses)
_KM_RX = re.compile(r"(\d{1,3}(?:[.\s]\d{3})+|\d{4,7})\s*km")
# the spec reads "2008 - 244.000 km" (or older "2018 120 000 km"): the year sits right before the
# km figure. anchoring on km avoids picking up a posted/inspection date elsewhere on the card.
_YEAR_RX = re.compile(r"((?:19|20)\d{2})\s*-?\s*\d[\d.\s]*km")


def _int(s: str | None) -> int | None:
    if not s:
        return None
    m = _NUM_RX.findall(s.replace(".", "").replace(",", ""))
    return int("".join(m)) if m else None


def parse_cards(html: str) -> list[Listing]:
    # selectors target stable data-cy attributes used by olx group; fall back to structural
    tree = HTMLParser(html)
    out: list[Listing] = []
    for card in tree.css(_CARD_SEL):
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

        # specs are matched from the card text to survive olx markup changes: older cards used a
        # <ul data-testid="ad-card-params"> with separate items, current cards render a single
        # secondary-text line like "2008 - 244.000 km".
        spec = card.text(separator=" ", strip=True)
        kmm = _KM_RX.search(spec)
        km = _int(kmm.group(1)) if kmm else None
        ym = _YEAR_RX.search(spec)
        year = int(ym.group(1)) if ym else None
        fuel = None
        low = spec.lower()
        for f in ("gasolina", "diesel", "hibrido", "eletrico", "gpl"):
            if f in low:
                fuel = f
                break

        loc_el = card.css_first('[data-testid="location-date"], p.location')
        location = loc_el.text(strip=True) if loc_el else None

        img = card.css_first("img")
        image_url = (img.attributes.get("src") if img else None) or None
        # skip placeholder/data-uri images so a real "no photo" listing isn't given a fake thumbnail
        if image_url and not image_url.startswith("http"):
            image_url = None

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
                image_url=image_url,
            )
        )
    return out


async def fetch_detail(ctx, url: str) -> Detail:
    """parse an olx ad page into a description + photo gallery (olx has few structured specs)."""
    html = await fetch_html(ctx, url, scroll=True)
    if not html:
        return Detail()
    el = HTMLParser(html).css_first('[data-cy="ad_description"]')
    desc = el.text(separator=" ", strip=True) if el else ""
    return Detail(description=desc, images=extract_apollo_images(html, limit=30))


async def search(filters: Filters, max_pages: int | None = None) -> list[Listing]:
    settings = load()
    max_pages = max_pages or settings.max_pages
    found: dict[str, Listing] = {}
    sem = asyncio.Semaphore(3)

    async def fetch_page(ctx, page: int) -> list[Listing]:
        url = build_url(filters, page=page)
        async with sem:
            log.info("olx fetch page %d %s", page, url)
            # scroll to trigger olx's lazy-loaded card images (real src is absent otherwise)
            html = await fetch_html(ctx, url, scroll=True, wait_selector=_CARD_SEL)
        if not html:
            log.warning("olx page %d returned no html (blocked or timed out)", page)
            return []
        cards = parse_cards(html)
        log.info("olx page %d -> %d cards", page, len(cards))
        return cards

    async with with_browser() as ctx:
        pages = await asyncio.gather(
            *(fetch_page(ctx, p) for p in range(1, max_pages + 1)), return_exceptions=True
        )
    # keep page order; an empty/failed page means the results ran out, discard anything after it
    for cards in pages:
        if isinstance(cards, BaseException):
            log.warning("olx page fetch failed: %s", cards)
            break
        if not cards:
            break
        for c in cards:
            found.setdefault(c.external_id, c)
    return list(found.values())
