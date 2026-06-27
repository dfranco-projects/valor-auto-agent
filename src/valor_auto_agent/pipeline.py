from __future__ import annotations

import asyncio
import logging

from valor_auto_agent.tools.crawler import olx, standvirtual
from valor_auto_agent.tools.crawler.schemas import Filters, Listing

log = logging.getLogger(__name__)


async def crawl(filters: Filters) -> list[Listing]:
    """crawl olx + standvirtual concurrently, tolerating a single-source failure."""
    results = await asyncio.gather(
        olx.search(filters), standvirtual.search(filters), return_exceptions=True
    )
    listings: list[Listing] = []
    for name, r in zip(("olx", "standvirtual"), results, strict=True):
        if isinstance(r, Exception):
            log.warning("crawl %s failed: %r", name, r)
            continue
        log.info("crawl %s -> %d listings", name, len(r))
        listings.extend(r)
    return listings
