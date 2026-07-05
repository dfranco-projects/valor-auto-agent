from __future__ import annotations

import asyncio
import contextlib
import logging
import re
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from patchright.async_api import Browser, BrowserContext, async_playwright

from valor_auto_agent.config import load

log = logging.getLogger(__name__)

# both olx and standvirtual host photos on the same apollo cdn (...;s=WxH sizing suffix)
_APOLLO_RX = re.compile(r"https://ireland\.apollo\.olxcdn\.com[^\s\"'\\<>]+?image;s=\d+x\d+")


def extract_apollo_images(html: str, limit: int = 4) -> list[str]:
    """distinct gallery photo urls from a detail page (dedup a photo's size variants)."""
    out: list[str] = []
    seen: set[str] = set()
    for u in _APOLLO_RX.findall(html):
        base = u.split(";s=")[0]
        if base in seen:
            continue
        seen.add(base)
        out.append(u)
        if len(out) >= limit:
            break
    return out


_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_5) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"
)


@asynccontextmanager
async def with_browser() -> AsyncIterator[BrowserContext]:
    settings = load()
    async with async_playwright() as p:
        browser: Browser = await p.chromium.launch(headless=settings.headless)
        ctx = await browser.new_context(
            user_agent=_UA,
            locale="pt-PT",
            timezone_id="Europe/Lisbon",
            viewport={"width": 1366, "height": 900},
        )
        try:
            yield ctx
        finally:
            await ctx.close()
            await browser.close()


async def _autoscroll(page, max_steps: int = 15, pause: int = 200) -> None:
    # nudge the page down so lazy-loaded images (e.g. olx) fetch their real src before we
    # snapshot; stop as soon as the viewport hits the bottom or the scroll stops advancing
    last_y = -1.0
    for _ in range(max_steps):
        await page.evaluate("window.scrollBy(0, window.innerHeight * 0.9)")
        await page.wait_for_timeout(pause)
        y, at_bottom = await page.evaluate(
            "[window.scrollY,"
            " (window.scrollY + window.innerHeight) >= (document.body.scrollHeight - 50)]"
        )
        if at_bottom or y <= last_y:
            break
        last_y = y
    # wait until the lazy images have swapped in their real src (count stabilises), max ~2s
    last_n = -1
    for _ in range(8):
        n = await page.evaluate("document.querySelectorAll('img[src^=\"http\"]').length")
        if n == last_n:
            break
        last_n = n
        await page.wait_for_timeout(250)


async def fetch_html(
    ctx: BrowserContext,
    url: str,
    *,
    attempts: int = 3,
    scroll: bool = False,
    wait_selector: str | None = None,
) -> str | None:
    delay = 1.5
    for i in range(attempts):
        page = await ctx.new_page()
        try:
            resp = await page.goto(url, wait_until="domcontentloaded", timeout=30_000)
            if resp and resp.status in (403, 429, 503):
                log.warning("blocked %s on %s (try %d)", resp.status, url, i + 1)
                await asyncio.sleep(delay)
                delay *= 2
                continue
            do_scroll = scroll
            if wait_selector:
                # much faster than a fixed wait when content is already there; on timeout
                # still snapshot whatever rendered and let the parser decide
                target = None
                with contextlib.suppress(Exception):
                    target = await page.wait_for_selector(wait_selector, timeout=8_000)
                # no target -> nothing lazy worth scrolling for (e.g. an empty results page)
                do_scroll = scroll and target is not None
                if do_scroll:
                    # brief settle so lazy-load observers attach before we start scrolling
                    await page.wait_for_timeout(300)
            else:
                await page.wait_for_timeout(800)
            if do_scroll:
                await _autoscroll(page)
            return await page.content()
        except Exception as e:
            log.warning("fetch error %s: %s (try %d)", url, e, i + 1)
            await asyncio.sleep(delay)
            delay *= 2
        finally:
            await page.close()
    return None
