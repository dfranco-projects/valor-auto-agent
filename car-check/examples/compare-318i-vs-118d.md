# compare-car example run — BMW 318i (OLX) vs BMW 118d (Standvirtual)

Verbatim output of a headless test session (2026-07-05, `claude -p` in this folder
with the `compare-car` skill), prompted with the two ad URLs and "which is the
better buy?". Both ads were live at the time; scraped data (galleries, page dumps)
stays local under `ads/` and is not committed.

---

## BMW 318i 2009 LCI (OLX) — €6.900 · 183.000 km · auto · petrol

```
score: 1.5/10
verdict: at-market-priced 17-year-old car whose photos reveal a German import the
description never mentions — the omission kills it.
key remarks:
- "Autohaus Genc" German dealer plate frames front AND rear (photos 2, 4), and the
  plate BZ26NF is Portugal's post-March-2020 format on a 2009 car → imported and
  legalized ~2021, not disclosed anywhere in the ad: −1.5
- description says "com 180.000 km" while the ad's spec field says 183.000 km —
  internal km contradiction: −1.0
- 17 years old: −1.0
- hazed/yellowed headlight lenses (photo 2) + seller-admitted paintwork scratches —
  light wear: −0.5
- 10.8k km/yr (183k ÷ 17): +0.5
- disclosed fault, right rear indicator intermittent (no score — noted, matches the
  iDrive "Set time and date" warning in photo 8 suggesting recent battery disconnect)
missing data: price-vs-market skipped — the search returned only 3 comparables, one
being this very ad and another an unlegalized Dutch-plate car, so the market
reference is degenerate; no engine bay or odometer photo (12 photos, so no bonus).
```

## BMW 118d Sport Line 2015 (Standvirtual) — €9.490 · 250.000 km · manual · diesel

```
score: 5.0/10
verdict: honestly presented high-mileage car priced well below its market — the km
is the price, but the odometer photo backs the claim.
key remarks:
- €9.490 vs market median €14.990 / p25 €12.990 (43 comparables) — below p25: +1.5
  (36.7% below median, under the 40% scam threshold, and the 250k km explains it)
- 22.7k km/yr (250k ÷ 11): −0.5
- plate 42-XI-63 is a ~2019-issue series on an April-2015 car → almost certainly
  imported and legalized ~2019, not disclosed — year-vs-plate-era contradiction: −1.0
- odometer photo 8 reads 250.758 km, matching the claimed 250.000: verified, no flag
missing data: no engine bay photo (17 photos otherwise varied, so no photo bonus);
"REVISÃO COMPLETA COM COMPROVATIVO" is a claim — the comprovativo isn't photographed;
VIN hidden behind a click.
```

---

## Which is the better buy: the 118d, clearly (5.0 vs 1.5)

Both cars appear to be undisclosed imports — that's the common sin. What separates them:

- **The 318i's ad contradicts itself and its photos.** German dealer frames on both plates while the seller lists "pintura original, nunca teve acidentes" and stays silent on provenance, plus two different km figures in the same ad. At €6.900 it's also priced at the top of what little 318i-petrol market exists.
- **The 118d's claims check out where they can be checked.** The odometer photo matches the claimed 250.000 km, and at €9.490 it sits below the 25th percentile of 43 real comparables (median €14.990). You're paying roughly €3.500 under p25 in exchange for the high mileage — a transparent trade.

Caveats before you act on the 118d: it's a diesel at 250k km, so demand the "comprovativo" of the full service (timing chain / injectors / clutch history on the B47), confirm the import origin and IUC implications from the documents, and note the near-empty tank + handbrake light in photo 8 are benign. Neither car is a great buy — the 118d is merely the defensible one; the 318i I'd walk away from on the provenance omission alone.
