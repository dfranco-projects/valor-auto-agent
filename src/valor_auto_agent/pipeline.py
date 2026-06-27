from __future__ import annotations

import asyncio
import logging
import re

from valor_auto_agent.tools.crawler import olx, standvirtual
from valor_auto_agent.tools.crawler.schemas import Filters, Listing

log = logging.getLogger(__name__)


def _model_match(title: str, model: str) -> bool:
    # neither site reliably filters by version (e.g. "320d"), so match it against the listing
    # title: by the model's number token when it has one (320d -> "320", excludes 116/318/i3),
    # otherwise by the model word.
    nums = re.findall(r"\d+", model)
    title_l = title.lower()
    if nums:
        title_nums = set(re.findall(r"\d+", title_l))
        return any(n in title_nums for n in nums)
    return model.lower() in title_l


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

    if filters.model:
        before = len(listings)
        listings = [li for li in listings if _model_match(li.title or "", filters.model)]
        log.info("model filter %r: %d -> %d listings", filters.model, before, len(listings))

    # olx can't filter mileage via url, so enforce km_max here for both sources (unknown km kept)
    if filters.km_max is not None:
        before = len(listings)
        listings = [li for li in listings if li.km is None or li.km <= filters.km_max]
        log.info("km_max filter %d: %d -> %d listings", filters.km_max, before, len(listings))
    return listings
