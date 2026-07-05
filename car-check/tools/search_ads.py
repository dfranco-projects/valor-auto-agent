"""search olx.pt + standvirtual.com with the valor-auto-agent crawler.

usage (from the repo root):
    uv run python car-check/tools/search_ads.py --brand bmw --model 318 \
        --price-max 12000 --year-min 2008 [--km-max 200000] [--fuel diesel] \
        [--transmission automatica] [--max-pages 2]

crawls both sites concurrently, marks cross-site duplicates, and writes the full
listing set to car-check/searches/<timestamp>.json for the agent to rate.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import statistics
import sys
from datetime import UTC, datetime
from pathlib import Path

from valor_auto_agent.pipeline import crawl
from valor_auto_agent.tools.crawler.schemas import Filters
from valor_auto_agent.tools.dedupe import also_on

SEARCH_DIR = Path(__file__).resolve().parents[1] / "searches"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--brand")
    p.add_argument("--model")
    p.add_argument("--price-min", type=int)
    p.add_argument("--price-max", type=int)
    p.add_argument("--year-min", type=int)
    p.add_argument("--year-max", type=int)
    p.add_argument("--km-max", type=int)
    p.add_argument("--fuel", choices=["gasolina", "diesel", "hibrido", "eletrico", "gpl"])
    p.add_argument("--transmission", choices=["manual", "automatica"])
    p.add_argument("--max-pages", type=int, help="pages per site (default from settings)")
    return p.parse_args()


def market_reference(prices: list[int]) -> dict:
    # fixed benchmark computed once over the whole result set, so ratings don't drift
    prices = sorted(prices)

    def pct(p: float) -> int:
        return prices[min(len(prices) - 1, int(p * len(prices)))]

    return {
        "priced_listings": len(prices),
        "median_eur": int(statistics.median(prices)),
        "p25_eur": pct(0.25),
        "p75_eur": pct(0.75),
        "min_eur": prices[0],
        "max_eur": prices[-1],
    }


async def main() -> None:
    args = parse_args()
    filters = Filters(
        brand=args.brand,
        model=args.model,
        price_min=args.price_min,
        price_max=args.price_max,
        year_min=args.year_min,
        year_max=args.year_max,
        km_max=args.km_max,
        fuel=args.fuel,
        transmission=args.transmission,
    )
    if args.max_pages:
        from valor_auto_agent.config import load

        load().max_pages = args.max_pages

    listings = await crawl(filters)
    if not listings:
        sys.exit("no listings found (filters too narrow, or both sites blocked the crawl)")

    dupes = also_on(listings)
    rows = []
    for i, li in enumerate(listings):
        row = li.model_dump(mode="json", exclude={"raw"})
        row["also_on"] = dupes.get(i, [])
        rows.append(row)
    rows.sort(key=lambda r: (r["price_eur"] is None, r["price_eur"]))

    prices = [r["price_eur"] for r in rows if r["price_eur"]]
    out = {
        "fetched_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "filters": filters.model_dump(exclude_none=True),
        "market_reference": market_reference(prices) if prices else None,
        "listings": rows,
    }
    SEARCH_DIR.mkdir(parents=True, exist_ok=True)
    path = SEARCH_DIR / f"{datetime.now():%Y%m%d-%H%M%S}.json"
    path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"{len(rows)} listings -> {path}")
    if out["market_reference"]:
        m = out["market_reference"]
        print(f"market: median {m['median_eur']}€, p25 {m['p25_eur']}€, p75 {m['p75_eur']}€")


if __name__ == "__main__":
    asyncio.run(main())
