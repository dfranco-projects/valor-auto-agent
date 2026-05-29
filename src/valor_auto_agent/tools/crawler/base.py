from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from patchright.async_api import Browser, BrowserContext, async_playwright

from valor_auto_agent.config import load

log = logging.getLogger(__name__)

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


async def fetch_html(ctx: BrowserContext, url: str, *, attempts: int = 3) -> str | None:
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
            await page.wait_for_timeout(800)
            return await page.content()
        except Exception as e:
            log.warning("fetch error %s: %s (try %d)", url, e, i + 1)
            await asyncio.sleep(delay)
            delay *= 2
        finally:
            await page.close()
    return None
