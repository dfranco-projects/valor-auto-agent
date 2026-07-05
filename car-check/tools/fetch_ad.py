"""fetch ONE olx.pt or standvirtual.com car ad for local inspection by claude code.

usage (from the repo root):
    uv run python car-check/tools/fetch_ad.py <ad-url>

validates the url is a single ad on one of the two supported sites, scrapes that one
page (full description, structured specs when available, the page's visible text for
title/price/seller), downloads EVERY gallery photo, and writes it all under
car-check/ads/<ad-id>/ so the agent can Read the photos and text locally.
"""

from __future__ import annotations

import asyncio
import json
import re
import sys
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlparse

import httpx
from selectolax.parser import HTMLParser

from valor_auto_agent.tools.crawler import olx, standvirtual
from valor_auto_agent.tools.crawler.base import extract_apollo_images, fetch_html, with_browser
from valor_auto_agent.tools.crawler.schemas import Detail

ADS_DIR = Path(__file__).resolve().parents[1] / "ads"

_HOSTS = {
    "olx.pt": "olx",
    "www.olx.pt": "olx",
    "standvirtual.com": "standvirtual",
    "www.standvirtual.com": "standvirtual",
}


def validate(url: str) -> str:
    """return the source name, or exit with a clear refusal."""
    p = urlparse(url)
    source = _HOSTS.get(p.netloc.lower(), "")
    if p.scheme != "https" or not source:
        sys.exit(
            f"refused: {url!r} is not an olx.pt or standvirtual.com url — "
            "this tool only fetches single ads from those two sites"
        )
    if source == "olx" and not p.path.startswith("/d/anuncio/"):
        sys.exit("refused: olx url is not a single-ad page (expected /d/anuncio/...)")
    if source == "standvirtual" and not p.path.startswith("/carros/anuncio/"):
        sys.exit("refused: standvirtual url is not a single-ad page (expected /carros/anuncio/...)")
    return source


def ad_id(url: str) -> str:
    m = re.search(r"(ID\w+)\.html", urlparse(url).path)
    return m.group(1) if m else re.sub(r"\W+", "-", urlparse(url).path).strip("-")[-60:]


def parse_detail(source: str, html: str) -> Detail:
    if source == "standvirtual":
        d = standvirtual._parse_advert(html)
        if not d.images:
            d.images = extract_apollo_images(html, limit=100)
        return d
    return olx._parse_detail(html)  # gallery-scoped: excludes related-ads thumbnails


def page_text(html: str) -> str:
    # visible page text as a fallback source for title, price, seller card, params
    tree = HTMLParser(html)
    for n in tree.css("script, style, noscript, svg"):
        n.decompose()
    text = tree.body.text(separator="\n", strip=True) if tree.body else ""
    return re.sub(r"\n{3,}", "\n\n", text)


async def download_photos(urls: list[str], dest: Path) -> list[str]:
    dest.mkdir(parents=True, exist_ok=True)
    sem = asyncio.Semaphore(6)

    async def grab(http: httpx.AsyncClient, i: int, url: str) -> str | None:
        async with sem:
            try:
                r = await http.get(url)
                r.raise_for_status()
            except httpx.HTTPError as e:
                print(f"  photo {i:02d} failed: {e}", file=sys.stderr)
                return None
        name = f"{i:02d}.jpg"
        (dest / name).write_bytes(r.content)
        return name

    async with httpx.AsyncClient(timeout=30, follow_redirects=True) as http:
        results = await asyncio.gather(*(grab(http, i, u) for i, u in enumerate(urls, 1)))
    return [r for r in results if r]


async def main(url: str) -> None:
    source = validate(url)
    out = ADS_DIR / ad_id(url)
    out.mkdir(parents=True, exist_ok=True)

    async with with_browser() as ctx:
        html = await fetch_html(ctx, url, scroll=(source == "olx"))
    if not html:
        sys.exit("fetch failed: page returned no html after retries (blocked or timed out)")

    detail = parse_detail(source, html)
    photos = await download_photos(detail.images, out / "photos")

    (out / "description.txt").write_text(detail.description, encoding="utf-8")
    (out / "page.txt").write_text(page_text(html), encoding="utf-8")
    record = {
        "url": url,
        "source": source,
        "fetched_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "description": detail.description,
        "specs": detail.specs,
        "equipment": detail.equipment,
        "gallery_total": len(detail.images),
        "photos_downloaded": len(photos),
        "photo_files": [f"photos/{p}" for p in photos],
    }
    (out / "ad.json").write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"source: {source}")
    print(f"saved to: {out}")
    print(f"description: {len(detail.description)} chars -> description.txt")
    print(f"specs: {len(detail.specs)} fields, equipment: {len(detail.equipment)} items -> ad.json")
    print("full visible page text (title/price/seller) -> page.txt")
    print(f"photos: {len(photos)}/{len(detail.images)} downloaded -> photos/")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("usage: uv run python car-check/tools/fetch_ad.py <ad-url>")
    asyncio.run(main(sys.argv[1]))
