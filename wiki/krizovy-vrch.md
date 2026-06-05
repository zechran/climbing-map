# Křížový vrch (Křížák)

**Summary**: One of the five Czech sandstone climbing areas in the Polická pánev, colloquially known as "Křížák". All 3 obvods fully processed ✅ — routes, GPS, and comments complete.

**Sources**: `lezení na českém písku, na pískovcových skálách (...).md`, piskari.cz, db-sandsteinklettern.gipfelbuch.de, mapy.com API, `piskari-scraper.py`, `gipfelbuch-gps.py`, `mapycz-gps.py`

**Last updated**: 2026-05-25

---

Křížový vrch (colloquially "Křížák") is one of the five climbing areas in the [[policka-panev]], governed by [[ovk-broumovsko]]. It is a distinct area from [[adrspach]] — separate rock formations, separate URL namespace on piskari.cz (`/cs/krizovy-vrch/`).

**Key difference from Adršpach**: piskari.cz does not provide GPS coordinates for Křížový vrch towers (no Google Maps embed on tower pages). GPS is sourced from the German sandstone climbing database at `db-sandsteinklettern.gipfelbuch.de`, which covers the same towers under the name "Křížový_vrch/Kreuzberg (Holsterberg)".

## Obvods (sectors)

Křížový vrch is divided into 3 obvods. Both data sources cover all 3:

| Obvod            | piskari.cz URL                          | gipfelbuch.de sektorid | JSON file                        | Status |
| ---------------- | --------------------------------------- | ---------------------- | -------------------------------- | ------ |
| Jižní věže       | `/cs/krizovy-vrch/jizni-veze-22/`       | 71                     | `piskovce-jizni-veze.json`       | ✅ done |
| Křížový hřeben   | `/cs/krizovy-vrch/krizovy-hreben-23/`   | 70                     | `piskovce-krizovy-hreben.json`   | ✅ done |
| Zdoňovský oblouk | `/cs/krizovy-vrch/zdonovsky-oblouk-24/` | 72                     | `piskovce-zdonovsky-oblouk.json` | ✅ done |

## GPS data source: gipfelbuch.de

The German DB at `http://db-sandsteinklettern.gipfelbuch.de/gebiet.php?gebietid=10` carries `Gipfelkoordinaten` (GPS coordinates) per tower. These are matched to the piskari.cz JSON by Czech tower name.

**Important**: The site uses **cp1250** (Windows-1250) encoding, not iso-8859-2. This matters because cp1250 encodes `š` as `\x9a` and `ž` as `\x9e` — bytes that iso-8859-2 treats as invisible control characters, causing name-matching failures (e.g. `Tomášova věžička` appearing as `Tomá\x9aova vě\x9eička`). The `gipfelbuch-gps.py` script uses cp1250 correctly.

## Full workflow per obvod

```bash
cd ~/Documents/LLM-pieskari/pieskari && source venv/bin/activate

# Step 1: scrape routes from piskari.cz → JSON (no GPS yet)
python piskari-scraper.py --kv-sector "Jižní věže" --headless

# Step 2: patch GPS from gipfelbuch.de → updates JSON + writes GPX
python gipfelbuch-gps.py --sektor "Jižní věže" --json piskovce-jizni-veze.json

# Step 3: fill remaining GPS gaps via mapy.com API (fallback for towers missing from gipfelbuch.de)
python mapycz-gps.py --json piskovce-jizni-veze.json

# Step 4 (optional): manually fix any towers still missing GPS
#   - open piskovce-jizni-veze.json, search for "lat": null
#   - look up tower on mapy.cz, fill in coordinates
#   - then rebuild GPX from updated JSON (no web access):
python piskari-scraper.py --rebuild-gpx "Jižní věže"

# Step 5: enrich with route descriptions and comments
python piskari-scraper.py --add-comments piskovce-jizni-veze.json
```

For all 3 obvods at once (steps 3–5 still need to be run per-obvod):
```bash
python piskari-scraper.py --all-krizovy-vrch --headless
python gipfelbuch-gps.py --all-kv
```

## Known GPS gaps

Some towers are missing from gipfelbuch.de — `mapycz-gps.py` (Step 3) handles most of these automatically. It only touches towers still missing GPS, so it is safe to chain after `gipfelbuch-gps.py`.

Towers not found by either script must be resolved manually (look up on mapy.cz, edit the JSON, then run `--retry` to regenerate the GPX before proceeding to `--add-comments`).

Name mismatches between piskari.cz and gipfelbuch.de may also cause a tower to be skipped — check the mismatch report and add a manual name mapping if needed.

## Related pages

- [[policka-panev]]
- [[ovk-broumovsko]]
- [[czech-sandstone-climbing]]
- [[technical]]
- [[piskari-cz]]
