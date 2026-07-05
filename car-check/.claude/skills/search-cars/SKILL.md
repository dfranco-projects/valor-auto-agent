---
name: search-cars
description: Search olx.pt + standvirtual.com for cars matching the user's filters and rate every result with the strict rubric — the full valor-auto-agent flow. Use when the user asks to find/search/compare cars rather than rate one URL.
---

# Search and rate cars (full agent flow)

Input: the user's criteria (brand, model, budget, year, km, fuel, transmission).

## Steps

1. **Search** (from the repo root), mapping the user's words to flags — fuel is one of
   `gasolina|diesel|hibrido|eletrico|gpl`, transmission `manual|automatica`:
   ```
   uv run python car-check/tools/search_ads.py --brand bmw --model 318 \
       --price-max 12000 --year-min 2008 --max-pages 2
   ```
   It writes `car-check/searches/<timestamp>.json`: all listings (price-sorted,
   cross-site duplicates marked in `also_on`) plus a fixed `market_reference`.

2. **Rate every listing** with `car-check/RUBRIC.md`, using that file's
   `market_reference` as the price benchmark — never re-estimate it from a subset.
   Same rules for every car; a duplicate pair gets one rating (cite both URLs).

3. **Report**: a table of the top ~10 by score — score, title, price, year, km,
   source, URL — each with a one-line rationale, plus anything you filtered out as a
   likely scam and why.

4. **Deep-inspect on request** (or offer it for the top 2–3): run the `rate-ad` skill
   on those URLs — it fetches the full gallery and description and re-scores from the
   photos. Photo-verified findings override the text-only rating.

Rate limits: the crawler already sleeps between pages; don't run several searches
back-to-back, and deep-inspect a handful of ads, not the whole result set.
