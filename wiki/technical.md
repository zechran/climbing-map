# Technical Documentation

**Summary**: Implementation details of the piskari.cz scraping pipeline — site structure, data extraction, JSON model, GPX format, and how to extend to new areas.

**Sources**: piskari-scraper.py, direct inspection of piskari.cz via Claude in Chrome

**Last updated**: 2026-05-25 (mapycz-gps.py added)

---

## Architecture overview

```
piskari.cz  ──scrape──►  JSON  ──generate──►  GPX  ──import──►  Locus Map
              browser               file                         (offline)
```

The browser is required because GPS coordinates are only available inside a JavaScript-rendered Google Maps embed. Plain HTTP fetches return no coordinates. All scraping uses **Playwright** (Python) controlling a Chromium browser.

---

## piskari.cz site structure

### URL patterns

| Level | Pattern | Example |
|-------|---------|---------|
| Area | `/cs/[area]/` | `/cs/adrspach/` |
| Sector | `/cs/[area]/[sector-slug]-[ID]/` | `/cs/adrspach/milenecka-hora-7/` |
| Sector page 2+ | `/cs/[area]/[sector-slug]-[ID]/[N]/` | `/cs/adrspach/milenecka-hora-7/1/` |
| Tower | `/cs/skala/[name-slug]-[ID]/` | `/cs/skala/adam-a-eva-1378/` |
| Route | `/cs/cesta/[name-slug]-[ID]/` | `/cs/cesta/jizni-2389/` |
| Tower search | `/cs/vyhledani-skalni-veze/` | alphabetical, paginated |

Sector pages show 30 towers per page. Page 1 has no suffix; page 2 is `/1/`, page 3 is `/2/`, etc. (zero-indexed offset).

### Tower IDs

Tower IDs in the 1xxx–2xxx range are established towers with full data including GPS. IDs in the 3xxx range are newer additions that typically have no GPS map on piskari.cz yet (confirmed: Amorek 3614, Konipas 3662, Sokolík 3613, Tři sestry 3680 — all missing map tab in Milenecká hora).

### Tower page structure

A tower page at `/cs/skala/[name]-[ID]/` contains three tab sections (JavaScript-toggled):

- **cesty** — route table, visible on page load (no JS needed)
- **mapa, okolní věže** — Google Maps embed + list of nearby towers
- **hlášení pro skalní údržbu** — maintenance reporting form

The route table (`<table class="vypis vypisCest">`) lists all routes with links to `/cs/cesta/` pages. Each route link has the name as link text; grade and first-ascent date appear as plain text in the same `<td>`.

### GPS storage

GPS coordinates are **not in the raw HTML**. They are passed to the Google Maps API in inline JavaScript. The map container is `<div id="a-vypis-mapy">`. After clicking the "mapa, okolní věže" tab, Google Maps initialises as `window.map` (a `google.maps.Map` instance). The map is centred on the tower's location.

**Extraction method**: `window.map.getCenter()` returns a `google.maps.LatLng` object. Calling `.lat()` and `.lng()` on it gives the tower's coordinates.

**Wait condition**: The map object exists before it is fully ready. The safe wait condition is:
```javascript
() => {
    try {
        var c = window.map.getCenter();
        return c !== null && typeof c.lat === 'function' && c.lat() !== 0;
    } catch(e) { return false; }
}
```

### Route page structure

A route page at `/cs/cesta/[name]-[ID]/` contains:

- **Route metadata** — in a single `<td>` containing lines prefixed with `popis:`, `datum prvovýstupu:`, `autor:`, `charakter:`
- **Comments** — in `<table class="komentare">`. Rows alternate: odd rows = date + username, even rows = comment text. Rows containing `"Uživatel cestu pouze hodnotil, nekomentoval."` are rating-only entries with no text and should be skipped.

---

## Scraper: piskari-scraper.py

### Requirements

```bash
python3 -m venv venv
source venv/bin/activate
pip install playwright
python -m playwright install chromium
```

Tested with Python 3.8.2. The `from __future__ import annotations` import at the top enables modern type hint syntax on Python 3.8.

### Functions

| Function | Purpose |
|----------|---------|
| `collect_tower_urls(page, sector_path)` | Crawls all pages of a sector, returns list of `{name, url}` |
| `get_tower_data(page, tower_url)` | Visits one tower page: extracts name, area, sector, GPS, routes |
| `get_route_details(page, route_url)` | Visits one route page: extracts popis, charakter, autor, comments |
| `build_desc(tower, comments_by_route)` | Assembles the `<desc>` string for a GPX waypoint |
| `write_gpx(towers, comments, output, label)` | Writes GPX file from tower list |

### CLI flags

| Flag | Effect |
|------|--------|
| `--sector "Name"` | Scrape one Adršpach sector by name (default: Milenecká hora) |
| `--all-adrspach` | Scrape all 11 Adršpach sectors in sequence |
| `--kv-sector "Name"` | Scrape one Křížový vrch obvod by name |
| `--all-krizovy-vrch` | Scrape all 3 Křížový vrch obvods in sequence |
| `--tower /cs/skala/[name]-[ID]/` | Scrape a single tower |
| `--add-comments FILE.json` | Enrich existing JSON with route details and comments, regenerate GPX |
| `--retry FILE.json` | Re-scrape only towers with missing GPS in an existing JSON |
| `--comments` | Fetch comments during the initial scrape (slower; prefer `--add-comments`) |
| `--output FILE` | Override output file name |
| `--headless` | Run browser without visible window |

### Performance notes

- Images, CSS and fonts are blocked via Playwright route interception to speed up page loads
- GPS extraction requires waiting for Google Maps to initialise (~2–5s per tower)
- Typical throughput: ~10–15 towers/minute for the GPS+routes pass
- The `--add-comments` pass visits ~3–4 route pages per tower; budget ~1 hour per 100 towers

---

## JSON data model

Each tower is one object. The JSON file is a list of tower objects.

```json
{
  "name": "Adam a Eva",
  "area": "Adršpach",
  "sector": "Milenecká hora",
  "lat": 50.608439,
  "lon": 16.115956,
  "url": "https://www.piskari.cz/cs/skala/adam-a-eva-1378/",
  "routes": [
    {
      "name": "Jižní",
      "grade": "V",
      "date": "21.6.1961",
      "url": "/cs/cesta/jizni-2389/",
      "popis": "Od JZ komínem do vnitřního prostoru. Vpravo spárou a komínem na vrchol.",
      "charakter": "širočina | komín",
      "autor": "Fritz Flötgen a Herbert Richter",
      "comments": [
        "[19.8.2015 14:00:09 Standa] Dole zajistit jde...",
        "[22.9.2016 20:04:12 half] Kdo se rád plazí...",
        "[28.6.2017 13:05:44 cervo] Zrejme najľahšia cesta..."
      ]
    }
  ]
}
```

`lat`/`lon` are `null` for towers where GPS extraction failed (no map tab on piskari.cz). `popis`, `charakter`, `autor`, `comments` are empty/absent until `--add-comments` is run.

The JSON file is the canonical intermediate store. The GPX is always regenerated from it — never edit the GPX directly.

---

## GPX format

One `<wpt>` per tower. Towers without GPS (`lat`/`lon` = null) are silently skipped.

```xml
<?xml version="1.0" encoding="utf-8"?>
<gpx version="1.1" creator="piskari-scraper.py"
     xmlns="http://www.topografix.com/GPX/1/1">
  <metadata>
    <name>Piskovce — Milenecká hora</name>
    <desc>Climbing towers from piskari.cz — Milenecká hora. Generated 2026-05-23.</desc>
  </metadata>
  <wpt lat="50.6084390" lon="16.1159560">
    <name>Adam a Eva</name>
    <desc>
OBLAST: Adršpach / Milenecká hora
ZDROJ: piskari.cz
URL: https://www.piskari.cz/cs/skala/adam-a-eva-1378/

--- CESTY ---
1. Jižní | V | (21.6.1961)
   Charakter: širočina | komín
   Popis: Od JZ komínem do vnitřního prostoru...
   Autor: Fritz Flötgen a Herbert Richter
   Komentáře:
   > [19.8.2015 14:00:09 Standa] Dole zajistit jde...
    </desc>
    <sym>Flag, Blue</sym>
  </wpt>
</gpx>
```

The `<desc>` field is plain text — Locus Map renders it as-is with line breaks. No HTML or markdown is used because Locus Map does not render markup in waypoint descriptions.

---

## Locus Map import

- **Import path**: My Library → Import → select GPX file
- **Folder**: create one folder per sector; import each sector's GPX into its own folder
- **Visibility**: entire sector shown/hidden with one tap on the folder
- **Offline**: works fully without cell signal once LoMaps are downloaded for the region
- **Waypoint limit**: no hard limit; display performance consideration at ~10,000 simultaneous points (well above the total tower count for all five [[policka-panev]] areas)

---

## Known limitations

| Limitation | Detail |
|-----------|--------|
| Towers with no GPS | IDs in 3xxx range on piskari.cz have no map tab; lat/lon remain null and tower is excluded from GPX. Fix manually in JSON if coordinates are found elsewhere. |
| Google Maps API error dialog | "This page can't load Google Maps correctly" appears on some tower pages (invalid API key). Does not affect GPS extraction — `window.map.getCenter()` works regardless. Playwright dismisses it automatically. |
| Comment count | Up to 8 comments per route are fetched (configurable via `max_comments` param in `get_route_details`). Older comments are not retrieved. |
| Grade regex | Grade extraction uses a regex that covers most Czech sandstone grades (I–Xa). Edge cases like "VIId RP: VIIc" may parse incorrectly. |
| Session state | Each scraper run opens a fresh browser. piskari.cz does not require login to read tower/route data. |

---

## Script: gipfelbuch-gps.py

A second script handles GPS for areas where piskari.cz provides no coordinates (currently: Křížový vrch). It fetches `Gipfelkoordinaten` from `db-sandsteinklettern.gipfelbuch.de` and patches an existing piskovce-*.json in place.

### Requirements

```bash
pip install requests beautifulsoup4
```

No Playwright or browser needed — gipfelbuch.de is static HTML.

### How it works

1. Fetches the sector page (`gipfel.php?sektorid=N`) to collect all gipfelids
2. For each tower, fetches `weg.php?gipfelid=N` and extracts:
   - Czech name from the `<h2>` heading (format: `NR GERMAN_NAME / CZECH_NAME`)
   - GPS from the line `Gipfelkoordinaten: LAT Grad nördlicher Breite und LON Grad östlicher Länge`
3. Normalizes both names (strip diacritics, lowercase) and matches to the existing JSON
4. Writes updated JSON and regenerates GPX

### Encoding: cp1250 (critical)

gipfelbuch.de uses **Windows-1250 (cp1250)** encoding, **not** iso-8859-2. The difference matters in the 0x80–0x9F byte range:

| Byte | cp1250 | iso-8859-2 |
|------|--------|------------|
| `\x9a` | `š` | control char (invisible) |
| `\x9e` | `ž` | control char (invisible) |

Reading the page as iso-8859-2 causes names like `Tomášova věžička` to appear as `Tomá\x9aova vě\x9eička`, breaking name matching. The script explicitly sets `r.encoding = "cp1250"`.

### CLI flags

| Flag | Effect |
|------|--------|
| `--sektor "Name"` | One Křížový vrch obvod (looks up sektorid automatically) |
| `--all-kv` | All 3 Křížový vrch obvods (auto-detects JSON filenames) |
| `--json FILE` | Override JSON path (for `--sektor` only) |

### Known gaps

- Some towers exist on piskari.cz but not on gipfelbuch.de → no GPS available automatically; must be added manually to the JSON
- Name mismatches between the two sources → reported by the script after each run; add a manual mapping dict in the script if needed

### sektorid map for Křížový vrch

| Obvod | piskari.cz URL | gipfelbuch sektorid |
|-------|---------------|---------------------|
| Křížový hřeben | `/cs/krizovy-vrch/krizovy-hreben-23/` | 70 |
| Jižní věže | `/cs/krizovy-vrch/jizni-veze-22/` | 71 |
| Zdoňovský oblouk | `/cs/krizovy-vrch/zdonovsky-oblouk-24/` | 72 |

---

## Script: mapycz-gps.py

A third GPS script using the official **mapy.com REST API** (geocoding, `type=poi`). Works for any area — unlike `gipfelbuch-gps.py` which is Křížový vrch only. Also useful as a fallback for towers that piskari.cz itself cannot geocode (e.g. the 3xxx ID towers in Adršpach).

### Requirements

```bash
pip install requests   # already installed if you have the other scripts
```

No API key stored in the script. Key is prompted at runtime via `getpass` (hidden input, not echoed).

Get a free key at: [developer.mapy.com](https://developer.mapy.com/rest-api-mapy-cz/how-to-start/)
Cost: 4 credits per geocoding call. Free tier: 250,000 credits/month → ~62,500 lookups free.

### How it works

1. Prompts for API key (hidden input)
2. For each tower with missing GPS, calls `GET https://api.mapy.cz/v1/geocode?query=NAME&type=poi&lang=cs&limit=5&apikey=KEY`
3. Validates each result is within the area's **bounding box** (auto-detected from the JSON filename) — filters out false matches from other parts of CZ
4. Takes the best result (inside bbox + name match preferred)
5. Patches JSON and regenerates GPX

### CLI flags

| Flag | Effect |
|------|--------|
| `--json FILE` | JSON file to patch (required) |
| `--all` | Re-geocode all towers, not just those with missing GPS |
| `--dry-run` | Print what would be found without writing any files |
| `--no-gpx` | Update JSON only, skip GPX regeneration |

### Bounding boxes

The script auto-detects the area bounding box from the JSON filename. Defined in `AREA_BBOX` dict:

| Area | Bbox (min_lon, min_lat, max_lon, max_lat) |
|------|------------------------------------------|
| Adršpach | 16.05, 50.57, 16.22, 50.67 |
| Křížový vrch | 16.08, 50.59, 16.20, 50.67 |
| Broumovské stěny | 16.27, 50.52, 16.50, 50.65 |
| Ostaš | 16.10, 50.54, 16.25, 50.62 |
| Teplické skály | 16.05, 50.57, 16.22, 50.67 |
| default (fallback) | 15.80, 50.40, 16.60, 50.80 |

### Coverage and limitations

- **Works well** for towers with standard Czech names that mapy.cz indexes as POIs
- **Partial coverage** — mapy.cz may not have every tower, especially newer or smaller ones
- **Not found** results are listed after each run; fix manually in the JSON or try a spelling variant
- Tested with dry-run against Jižní věže: partial match, results verified against map

### GPS source comparison

| | piskari.cz (Playwright) | gipfelbuch.de (scraping) | mapy.com API |
|--|------------------------|--------------------------|-------------|
| Areas covered | Adršpach only (GPS) | Křížový vrch only | All areas |
| Auth needed | None | None | API key (free) |
| Encoding issues | None | cp1250 bug (fixed) | None (UTF-8) |
| Coverage | ~97% of known towers | Partial | Partial |
| Fragility | Depends on JS map loading | HTML scraping | Stable REST API |

**Recommended GPS strategy per area:**
- Adršpach: `piskari-scraper.py` (primary) → `mapycz-gps.py` (fallback for 3xxx IDs)
- Křížový vrch: `piskari-scraper.py` (routes) → `gipfelbuch-gps.py` (GPS) → `mapycz-gps.py` (remaining gaps)
- Other areas (future): `piskari-scraper.py` (routes) → `mapycz-gps.py` (GPS)

---

## Extending to other areas

### Area dictionaries in the script

The script maintains a separate sector dictionary per area. As of 2026-05-24:

| Dict | Area | Sectors | CLI flag |
|------|------|---------|----------|
| `ADRSPACH_SECTORS` | [[adrspach]] | 11 | `--sector / --all-adrspach` |
| `KRIZOVY_VRCH_SECTORS` | [[krizovy-vrch]] | 3 | `--kv-sector / --all-krizovy-vrch` |

### Adding a new area

1. Find sector URLs on piskari.cz (navigate the area's index page, e.g. `/cs/broumovske-steny/`)
2. Add a new dict (e.g. `BROUMOVSKE_STENY_SECTORS = { ... }`) in `piskari-scraper.py`
3. Add corresponding `--bs-sector` / `--all-broumovske-steny` args and execution branches in `main()` — follow the Křížový vrch pattern added 2026-05-24

The remaining three [[policka-panev]] areas to be added:

| Area | Base URL | Status |
|------|----------|--------|
| Broumovské stěny | `/cs/broumovske-steny/` | ⏳ sector URLs not yet collected |
| Ostaš | `/cs/ostas/` | ⏳ sector URLs not yet collected |
| Teplické skály | `/cs/teplice/` | ⏳ sector URLs not yet collected |

---

## Related pages

- [[product-spec]]
- [[piskari-cz]]
- [[adrspach]]
- [[sektor-milenecka-hora]]
- [[czech-sandstone-climbing]]
