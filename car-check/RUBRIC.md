# Car rating rubric — strict, deterministic, identical for every car

Score every car with this exact procedure. Never deviate, never round in the car's
favor, never adjust because the user (or the seller) likes the car. Two ads with the
same facts must get the same score, in the same session or a month apart.

## Bias firewall

- The seller's adjectives ("impecável", "único", "nacional", "como novo") are claims,
  not evidence. Only facts verified in photos, specs, or checkable text move the score.
- The user's enthusiasm, prior remarks, or ownership of the car change NOTHING. If the
  user says "rate my favorite", apply this rubric identically and report the result
  even if it's low.
- Never re-estimate market prices from feelings or memory of previous sessions. Use the
  `market_reference` block from a search file when rating a batch; for a single ad, use
  the comparables procedure below.

## Procedure

Start at **5.0**. Apply every adjustment whose data exists. Skip (do not guess) any
whose data is missing, and list what was missing. Clamp to [0, 10], one decimal.

### 1. Price vs market
Batch rating: compare against the search's fixed `market_reference` (never recompute
from a subset). Single ad: run `search_ads.py` for the same brand/model/year±2 and use
its market_reference; if that fails, skip this adjustment and say so.

- ≤ p25 → **+1.5** · between p25 and median → **+0.5**
- between median and p75 → **−0.5** · ≥ p75 → **−1.5**
- more than 40% below median with no explanation in the ad → **−2.0** (scam risk
  overrides the cheap-price bonus; flag it)

### 2. Mileage rate
km ÷ (current year − model year): < 12k/yr → **+0.5** · 12–20k → **0** ·
20–25k → **−0.5** · 25–35k → **−1.0** · > 35k → **−2.0**.
Odometer photo contradicting claimed km → **−3.0** and flag.

### 3. Age
\> 12 years old → **−0.5**, plus another **−0.5** per 5 further years, unless price
is ≤ p25 (then only the first −0.5).

### 4. Photos (hard caps)
- 0 photos → **cap the final score at 4.0**, note "sem fotos".
- 1–5 photos, or only blurry/dark/stock images → **−1.0**.
- ≥ 10 varied photos covering exterior, interior, engine bay, odometer → **+0.5**.
- Visible damage per photo evidence: light wear **−0.5**; dents/rust/curbed wheels/
  cracked glass **−1.0 each kind, max −3.0**; dashboard warning light lit → **−2.0**.

### 5. Provenance & honesty (the remarks that matter most)
- Import disclosed in the description → **−0.5** (paperwork/IUC risk, PT market).
- **Import visible in photos but NOT disclosed** (foreign dealer stamp/watermark/plate
  frame — e.g. a German "Autohaus …" stamp — foreign plates, TÜV/HU sticker, km/h-only
  or mph cluster, foreign inspection vignette) → **−1.5** and flag prominently: the
  omission is worse than the import.
- Any photo/description/spec contradiction (claimed trim vs badge, claimed year vs
  plate era, equipment listed but absent in photos) → **−1.0 each, max −3.0**.
- Description red flags: "acidente", "para peças", "vendido como está", "sem retoma",
  "importado sem documentos", engine/gearbox/clutch noises → **−2.0 each, max −4.0**.
- Verified positives: stamped service history, single owner, recent timing
  belt/clutch/tires with proof → **+0.5 each, max +1.5**.

### 6. Reliability prior (Portugal)
Toyota/Honda/Mazda/Lexus → **+0.5**. BMW 320d N47, Mercedes C-class, VW/Audi 1.6/2.0
TDI EA189 era without full service history → **−0.5**. Peugeot/Citroën/Renault older
than 10 years → **−0.5**.

## Output format (always)

```
score: X.X/10
verdict: one sentence
key remarks:
- (only findings that moved the score, each with its adjustment, e.g.
   "green 'Autohaus Genc' stamp on photos 3+7 — German import not disclosed: −1.5")
missing data: (what was skipped)
```
