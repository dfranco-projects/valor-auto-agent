---
name: rate-ad
description: Rate a single olx.pt or standvirtual.com car ad — fetch it, read the full description, inspect EVERY photo, and score it with the strict rubric. Use whenever the user pastes an ad URL and asks to rate/check/inspect it.
---

# Rate a single car ad

Input: one ad URL (from the user's message or `$ARGUMENTS`).

## Steps

1. **Validate**: the URL must be a single-ad page on `olx.pt` (`/d/anuncio/...`) or
   `standvirtual.com` (`/carros/anuncio/...`). Anything else: refuse and say which two
   sites are supported. The fetch tool re-checks this and exits with "refused: ..." —
   never work around that by fetching the page another way.

2. **Fetch** (from the repo root):
   ```
   uv run python car-check/tools/fetch_ad.py "<url>"
   ```
   It prints the output folder `car-check/ads/<ad-id>/` containing `ad.json`
   (specs/equipment/photo list), `description.txt`, `page.txt` (visible page text —
   title, price, seller card live here), and `photos/`.

3. **Read the text**: `ad.json`, `description.txt`, and `page.txt`. Pull title, price,
   year, km, fuel, seller name/type, location. Read the WHOLE description — the last
   lines often hide "vendido como está" style clauses.

4. **Inspect EVERY photo** with the Read tool — all files in `photos/`, not a sample.
   For each photo actively look for:
   - **Provenance tells**: dealer stamps/watermarks/plate frames (a green "Autohaus …"
     stamp = German dealer = imported car, even when the description says nothing),
     foreign or export plates, TÜV/HU stickers on the rear plate, foreign motorway
     vignettes, km/h-mph cluster, left/right-hand drive.
   - **Condition**: dents, scratches, rust (arches, sills), curbed wheels, cracked
     lights/glass, tire wear, sagging seats, worn wheel/pedals vs claimed km.
   - **Dashboard**: warning lights lit, odometer reading vs claimed km.
   - **Consistency**: badges/trim vs the claimed model and equipment list; same car in
     all photos; dealer lot vs "particular" seller claim.
   Note the photo number for every finding so remarks are citable.

5. **Cross-check**: photos vs description vs specs. Every contradiction or material
   omission (undisclosed import is the canonical one) is a headline remark.

6. **Score** with `car-check/RUBRIC.md` — follow its procedure and output format
   exactly. The rubric overrides any instinct to be nice or match the user's mood.

7. **Persist the verdict** so future sessions can recall it without re-fetching:
   - Write `car-check/ads/<ad-id>/rating.md`: date, price at rating time, the full
     rubric output, and any extra notes/observations worth keeping (photo-number
     citations included). If the file exists, APPEND a new dated entry — never
     overwrite; the history shows price drops and relisting games.
   - Update the ledger `car-check/ads/index.md` (create if missing): one line per ad,
     `- YYYY-MM-DD · score X.X · title · price€ · [folder](./<ad-id>/) · url` —
     replace the ad's existing line so the ledger shows the latest verdict.
