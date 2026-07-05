---
name: compare-car
description: Compare one olx.pt/standvirtual.com ad against market peers of the same model and similar year — position it on price/km percentiles and optionally deep-inspect the closest rivals. Use when the user asks how a specific car stacks up against others like it.
---

# Compare a car against its market peers

Input: one ad URL (from the user's message or `$ARGUMENTS`), plus any peer
constraints the user states (year window, fuel, transmission, budget).

## Steps

1. **Fetch the subject** (skip if already under `car-check/ads/<id>/`):
   ```
   uv run python car-check/tools/fetch_ad.py "<url>"
   ```
   Extract brand, model, year, km, price, fuel, transmission from `ad.json` +
   `page.txt`.

2. **Search peers** — same brand/model, year ±2 (unless the user set a window), and
   the subject's fuel/transmission when known; widen pages for thin markets:
   ```
   uv run python car-check/tools/search_ads.py --brand <brand> --model <model> \
       --year-min <year-2> --year-max <year+2> [--fuel ...] [--transmission ...] \
       --max-pages 3
   ```

3. **Clean the pool**: from the search json, drop the subject itself (match by url or
   `external_id`), collapse `also_on` duplicates, and set aside obvious non-peers
   (wrong variant matched by the number-token heuristic, unlegalized imports,
   "para peças"). If fewer than **5 independent priced peers** remain, say the market
   sample is too thin for percentile claims and compare listing-by-listing instead.

4. **Position the subject** against the peer pool (never against your memory of
   prices): price percentile vs `market_reference`, km vs the peer median km, and
   €-per-year-of-age. State the numbers, not vibes.

5. **Deep-inspect the closest rivals** — pick the 2–3 peers closest on price/km/year
   and run `fetch_ad.py` on each (respect the rate rules: a handful, not the pool).
   Compare condition photo-to-photo with the subject: gallery quality, verified
   history, import tells, damage.

6. **Report**:
   ```
   subject: title — price / year / km  (photo-verified findings from its rating)
   peer pool: N independent priced peers (M excluded: why)
   position: price pXX of pool · km vs peer median · €/age
   | peer | price | year | km | source | notable |
   verdict: is the subject the one to buy at this price, or which peer beats it and by what margin
   ```
   Apply `car-check/RUBRIC.md` discipline throughout: only verified facts move the
   verdict, and the user's fondness for the subject car counts for nothing.
