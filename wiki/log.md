# Wiki Log

Append-only record of all wiki operations.

---

## 2026-06-04 — Added publishing.md wiki page and publish.sh script

**New script**: `publish.sh "message"` — rebuilds HTML from markdown, commits, and pushes to GitHub in one command. Claude runs this automatically after every wiki change.

**New wiki page**: `publishing.md` — documents the full publishing pipeline, infrastructure, folder roles, and custom domain setup.

**Pages updated**: `index.md`, `log.md`

---

## 2026-06-04 — All 11 Adršpach sectors complete

All sector JSON and GPX files confirmed present on disk. Agent table and Locus Map folder listing in `howto-generate-gpx.md` updated to reflect 11/11 ✅.

Sectors: Milenecká hora, Himálaj, Jezerka, Království, Město, Ostrov, Panoptikum, Podhradí, Rokle nad Spáleným mlýnem, Vstupní obvod, Za pískovnou.

---

## 2026-05-28 — Added qa-report.py and qa-report wiki page

**New script**: `qa-report.py` — randomly samples 5% of sector towers (min 5), fetches each from live piskari.cz via Playwright, and validates GPS (±0.0001°), route names (fuzzy ≥0.85), route grades (fuzzy), and comment counts (exact, noting 8-comment cap).

**CLI**: `python qa-report.py --sector "Himálaj" [--seed N] [--headless]`

**Output**: `qa-{slug}.md` — Markdown report with summary table and per-tower detail.

**New wiki page**: `qa-report.md` — documents checks, sample size logic, usage, and result interpretation.

**Pages updated**: `index.md`, `log.md`

---

## 2026-05-28 — Added climber-filter.py and climber-filter wiki page

**New script**: `climber-filter.py` — filters all `piskovce-*.json` files by climber username (matched from comment timestamps), produces a new JSON + GPX with all matching towers and their full route data.

**First run**: `--climber cervo` — 217 towers across 13 sectors, all with GPS.

**CLI**: `python climber-filter.py --climber NAME [--output PREFIX] [--source DIR] [--dry-run]`

**New wiki page**: `climber-filter.md` — documents the pattern, usage, comment format, and refresh workflow.

**Pages updated**: `index.md`, `log.md`

---

## 2026-05-25 — Added --rebuild-gpx flag to piskari-scraper.py

**Change**: New `--rebuild-gpx` flag reads an existing JSON and writes a fresh GPX with no browser, no web access, and no comments re-fetch. Used after manually editing GPS coordinates in the JSON — faster and cheaper than `--add-comments` which would re-fetch all comments from the web.

Accepts a sector name or JSON filename: `python piskari-scraper.py --rebuild-gpx "Himálaj"`

**Pages updated**:
- `howto-generate-gpx.md` — Step 6 (optional rebuild after manual GPS fix) added; agent template updated with step 7
- `krizovy-vrch.md` — step 4 updated to use `--rebuild-gpx` instead of `--retry`

---

## 2026-05-25 — Agent template now requires only SECTOR_NAME and YOUR_KEY

**Change**: Scripts can now derive the JSON filename from the sector name, eliminating the need to specify JSON_FILE separately in the agent workflow.

- `mapycz-gps.py` — added `--sector NAME` flag (alternative to `--json FILE`); added `slugify()` function matching `piskari-scraper.py`
- `piskari-scraper.py --add-comments` — now accepts either a JSON filename or a sector name; derives `piskovce-{slug}.json` automatically when given a sector name
- `howto-generate-gpx.md` — agent template simplified to two substitutions: `YOUR_KEY` and `SECTOR_NAME`

**Pages updated**: `howto-generate-gpx.md`, `log.md`

---

## 2026-05-25 — Fixed slugify() to handle ě→e

**Change**: Added `ě` to the slugify() substitution table in `piskari-scraper.py`. Previously `ě` had no rule and was replaced by `-`, producing wrong filenames: `piskovce-jizni-v-ze.json` and `piskovce-m-sto.json`.

**Correct filenames after fix**:
- `"Jižní věže"` → `piskovce-jizni-veze.json` / `.gpx`
- `"Město"` → `piskovce-mesto.json` / `.gpx`

**Action required**: Rename existing JSON/GPX files on disk to match the new names before running the scraper again, otherwise it will create duplicate files.

**Pages updated**:
- `krizovy-vrch.md` — updated all references from `piskovce-jizni-v-ze.json` to `piskovce-jizni-veze.json`
- `howto-generate-gpx.md` — updated Město entry in agent table and Locus Map folder listing

---

## 2026-05-25 — mapycz-gps.py and --retry added as standard steps in all sector workflows

**Change**: `mapycz-gps.py` is now a standard step for every sector (not just Křížový vrch). After the initial GPS scrape, it fills remaining gaps automatically. Manual GPS editing is followed by `--retry` to regenerate the GPX before running `--add-comments`.

**Pages updated**:
- `howto-generate-gpx.md` — Method 1 renumbered to 6 steps; Step 3 (mapycz-gps.py) and Step 4 (manual fix + --retry) added; agent template updated with same steps; troubleshooting note updated
- `krizovy-vrch.md` — Full workflow expanded to 5 steps; Step 3 (mapycz-gps.py) and Step 4 (manual fix + --retry) made explicit

---

## 2026-05-25 — Improved agent instruction template in howto-generate-gpx.md

**Change**: Agent instruction template now uses explicit `SECTOR_NAME` / `JSON_FILE` placeholders. Agent table expanded with a 4th column listing the pre-computed JSON filename for each sector, so the user knows exactly what to substitute in both step 3 and step 4 without having to derive the slug manually.

**Pages updated**:
- `howto-generate-gpx.md` — template rewritten, table extended with JSON_FILE column

---

## 2026-05-25 — Jezerka and Království sectors completed

**Status update**: User confirmed both Adršpach sectors fully scraped and commented.

**Pages updated**:
- `howto-generate-gpx.md` — Agent 3 (Jezerka) and Agent 4 (Království) marked ✅ Done in the agent table; both GPX files marked ✅ in the Locus Map folder listing

4 of 11 Adršpach sectors now complete: Milenecká hora ✅, Himálaj ✅, Jezerka ✅, Království ✅
Remaining: Město, Ostrov, Panoptikum, Podhradí, Rokle nad Spáleným mlýnem, Vstupní obvod, Za pískovnou

---

## 2026-05-20 — Initial ingest: piskari.cz homepage

**Source**: `lezení na českém písku, na pískovcových skálách (Adršpach (Ádr), Broumovské stěny (Broumovky), Křižový vrch (Křížák), Ostaš, Teplické skály (Teplice).md`

**Pages created**:
- `wiki/index.md` — table of contents
- `wiki/log.md` — this file
- `wiki/piskari-cz.md` — portal overview
- `wiki/policka-panev.md` — geographic region
- `wiki/ovk-broumovsko.md` — regional climbing committee
- `wiki/czech-sandstone-climbing.md` — ethics, style, gear
- `wiki/czech-climbing-grades.md` — grading system
- `wiki/adrspach.md` — Adršpach area
- `wiki/broumovske-steny.md` — Broumovské stěny area
- `wiki/ostas.md` — Ostaš area (Horní + Zadní)
- `wiki/teplicke-skaly.md` — Teplické skály area
- `wiki/krizovy-vrch.md` — Křižový vrch area
- `wiki/vez-bounty.md` — Bounty tower, Adršpach
- `wiki/vez-rybnik.md` — Rybník tower, Horní Ostaš
- `wiki/vez-zdarska-vyhlidka.md` — Žďárská vyhlídka, Ostaš
- `wiki/routes/bicovani-u-stezne.md`
- `wiki/routes/doutniky.md`
- `wiki/routes/jarnicka.md`
- `wiki/routes/nenazvuhodna-prasecina.md`
- `wiki/routes/gotes.md`
- `wiki/routes/ctyrdenni.md`
- `wiki/routes/stara-cesta-4351.md`
- `wiki/routes/stara-cesta-3418.md`
- `wiki/routes/komin.md`
- `wiki/routes/bahneni.md`
- `wiki/routes/zensen.md`
- `wiki/routes/dalsi-v-poradi.md`
- `wiki/routes/chapes-vis-jak.md`
- `wiki/routes/marsovsky-valcik.md`
- `wiki/routes/druhy-dech.md`
- `wiki/routes/cas-kvapi.md`
- `wiki/routes/sladka-tecka.md`
- `wiki/routes/chytte-ho.md`
- `wiki/routes/mordovani.md`
- `wiki/routes/dokoncena.md`
- `wiki/routes/pekelna.md`
- `wiki/routes/nebeska.md`
- `wiki/routes/kamizolka-zelena.md`
- `wiki/routes/nahorni.md`
- `wiki/routes/bud-a-nebo.md`
- `wiki/routes/udolni.md`

**Notes**: First ingest. Wiki started from scratch. Most routes extracted from recent user comments on piskari.cz; tower/area attribution is unknown for the majority and marked as TBD. Only 3 towers explicitly named in source (Bounty, Rybník, Žďárská vyhlídka). Future sources should resolve route → tower → area hierarchy.

---

## 2026-05-20 — Schema update: Sector level added; first GPS-located tower

**Trigger**: User confirmed that mapy.cz already contains all tower names with GPS coordinates. This establishes the join key between piskari.cz (route content) and mapy.cz (spatial data).

**Hierarchy corrected to**: Area → Sector → Tower → Route → Comments

**Pages created**:
- `wiki/sektor-dolni-adrspach.md` — Dolní Adršpach sub-area
- `wiki/sektor-milenecka-hora.md` — Milenecká hora sector
- `wiki/vez-adam-a-eva.md` — first tower with confirmed GPS (50.6084167N, 16.1159444E, from mapy.cz)

**Pages updated**:
- `wiki/adrspach.md` — sector hierarchy added, Adam a Eva tower linked
- `wiki/index.md` — Sector section added, hierarchy and data sources documented

**Key insight logged**: Tower names are the join key between mapy.cz (GPS) and piskari.cz (routes/comments). No manual GPS collection needed — mapy.cz POIs already exist for all towers.

---

## 2026-05-20 — Wiki refocused on product; route pages removed

**Trigger**: Decision that individual route and comment pages are source data (piskari.cz content), not product knowledge. The wiki is a product knowledge base, not a mirror of piskari.cz.

**Pages created**:
- `wiki/product-spec.md` — draft product specification for Option A (GPX-based climbing map on mapy.com)

**Pages deleted**:
- `wiki/routes/` — entire folder (26 route pages) removed

**Index rewritten**: Now product-first. Spatial data model (area → sector → tower) is the core structure. Route-level data is described as embedded in GPX output at generation time, not catalogued in the wiki.

**Key decision logged**: Route descriptions and climber comments are embedded directly into GPX `<desc>` fields at export time, sourced live from piskari.cz. They do not need permanent wiki pages.

---

## 2026-05-20 — GPX test result: mapy.com blocked; platform pivoted to Locus Map

**Test**: Single waypoint GPX (`test-adam-a-eva.gpx`, tower Adam a Eva, GPS 50.6084167N 16.1159444E) imported into mapy.com. Tested on web (Safari) and iOS, free and Premium.

**Finding**: mapy.com does not render the GPX `<desc>` field in any mode. The only user-editable field on an imported waypoint is "Add note" (Premium only, manual, not GPX-importable).

**Decision**: mapy.com is not viable as the content host. The GPX data model is sound. Platform pivoted to **Locus Map** (Android + iOS).

---

## 2026-05-20 — Locus Map iOS confirmed; platform locked

**Test**: `test-adam-a-eva.gpx` imported into Locus Map Lite (iOS). Tapped the Adam a Eva waypoint pin.

**Result**: Full `<desc>` content displayed correctly. No truncation. ✅

**Waypoint limit**: No hard import limit in Locus Map. Display performance consideration at ~10,000 simultaneous points — well above the expected tower count for all five [[policka-panev]] areas.

**Decision**: Platform locked. Locus Map (Android + iOS) is the delivery target. Next step: collect tower list for Adršpach from mapy.com and generate the first real area GPX.

**Rationale for Locus Map**: Czech-made, well known in CZ/SK outdoor community, confirmed GPX import on both platforms, offline LoMaps, device sync. iOS version is early stage — `<desc>` rendering needs a test.

---

## 2026-05-22 — Architecture: piskari.cz confirmed as sole data source; GPS extraction approach identified

**Decision**: mapy.com is fully removed from the project. piskari.cz is the single source for everything: area/sector/tower hierarchy, route descriptions, climber comments, and GPS coordinates.

**GPS finding**: Tower GPS coordinates are NOT in the raw HTML of piskari.cz tower pages. They are embedded in the JavaScript that renders the "MAPA" section (e.g. `/cs/skala/adam-a-eva-1378/`). A JavaScript-capable browser (Claude in Chrome, Puppeteer, Playwright) is required to extract them. Plain HTML fetch returns no coordinates.

**Alternative GPS path**: Each piskari.cz tower page links to the Czech Mountaineering Association database (`horosvaz.cz`) — that may carry GPS independently and is a fallback extraction target.

**Pages updated**:
- `wiki/product-spec.md` — fully rewritten: mapy.com removed; piskari.cz documented as sole source with URL patterns; GPS extraction approach documented; data pipeline steps outlined; next steps updated
- `wiki/index.md` — data sources section updated to reflect piskari.cz as single source
- `wiki/vez-adam-a-eva.md` — mapy.cz GPS source replaced with piskari.cz; routes table added from piskari.cz page; route URLs added; nearby towers listed

**Next step**: Render `https://www.piskari.cz/cs/skala/adam-a-eva-1378/` in a browser and inspect the JavaScript map initialization to confirm GPS extraction is viable. Then build crawl pipeline for Milenecká hora sector.

---

## 2026-05-23 — GPS extraction confirmed; full tower list collected; scraper script written

**GPS extraction confirmed**: Navigated to `https://www.piskari.cz/cs/skala/adam-a-eva-1378/` in Claude in Chrome. Clicked "mapa, okolní věže" tab. Map uses Google Maps API. `window.map.getCenter()` returns `{lat: 50.608439, lng: 16.115956}` — matches expected coordinates for Adam a Eva. ✅

**Map structure**: Google Maps is initialized in a `<div id="a-vypis-mapy">` container. The map center IS the tower position. Markers for surrounding towers are visible on map but not easily extractable in bulk (no named global marker array). GPS must be extracted per-tower via `window.map.getCenter()`.

**Tower list — Milenecká hora**: All 5 pages scraped via Claude in Chrome. **129 towers** collected with piskari.cz URLs. Pagination pattern: `/cs/adrspach/milenecka-hora-7/`, `/1/`, `/2/`, `/3/`, `/4/`.

**Scraper script created**: `piskari-scraper.py` — Python Playwright script saved to workspace. Capabilities:
- Crawls sector pages to collect all tower URLs
- For each tower: loads map tab, reads `window.map.getCenter()` for GPS
- Scrapes routes (name, grade, date) from tower page
- Optionally fetches comments per route (`--comments` flag)
- Writes GPX file (one `<wpt>` per tower) and raw JSON
- Supports: single sector, all Adršpach sectors, single tower

**Usage**:
```bash
pip install playwright
python -m playwright install chromium
python3 piskari-scraper.py                         # Milenecká hora (default)
python3 piskari-scraper.py --all-adrspach          # all 11 Adršpach sectors
python3 piskari-scraper.py --comments              # include route comments
```

**Next step**: Run `piskari-scraper.py` locally to generate `piskovce-milenecka-hora.gpx`. Import into Locus Map. Validate tower pins and route descriptions.

---

## 2026-05-23 — MVP validated: Milenecká hora fully working in Locus Map ✅

**Result**: `piskovce-milenecka-hora.gpx` generated and imported into Locus Map. Tested on device. Confirmed working.

**Final stats — Milenecká hora**:
- 129 towers in sector
- 125/129 with GPS (4 skipped — Amorek, Konipas, Sokolík, Tři sestry have no map on piskari.cz; newer additions with IDs in 3xxx range)
- Routes (name, grade, date) extracted for all towers
- `--add-comments` enrichment added: popis, charakter, autor, climber comments per route
- GPX imported into Locus Map in a dedicated sector folder — sector visibility toggled with one tap ✅

**Folder-based organisation confirmed as the right UX pattern**: climbers navigate by sector, not individual tower. Locus Map folder = sector. One import per sector. User can show/hide entire sector at once.

**Script capabilities at this point** (`piskari-scraper.py`):
- `python piskari-scraper.py` — scrape a sector (GPS + routes) → JSON + GPX
- `python piskari-scraper.py --add-comments FILE.json` — enrich with popis/charakter/autor/comments → updated JSON + GPX
- `python piskari-scraper.py --retry FILE.json` — retry towers with missing GPS
- `python piskari-scraper.py --all-adrspach` — all 11 Adršpach sectors in one run

**Next**: Run remaining 10 Adršpach sectors. Then consider Broumovské stěny, Ostaš, Teplice, Křižový vrch.

---

## 2026-05-23 — Sector-by-sector workflow defined; script command reference

**Decision**: Each sector is processed independently, producing a separate GPX file. One GPX = one Locus Map folder = one sector. This gives the climber single-tap show/hide per sector.

**Workflow per sector** (3 steps, repeatable):
```
1. python piskari-scraper.py --sector "Name"        → piskovce-[name].gpx + .json
2. python piskari-scraper.py --add-comments piskovce-[name].json  → enriched GPX
3. Import GPX into Locus Map in a folder named after the sector
```

**Remember**: activate the virtual environment before each session:
```
cd ~/Documents/LLM-pieskari/pieskari
source venv/bin/activate
```

**Remaining Adršpach sectors** (10 of 11 — Milenecká hora done ✅):

| Sector | Command | Status |
|--------|---------|--------|
| Himálaj | `--sector "Himálaj"` | ⏳ |
| Jezerka | `--sector "Jezerka"` | ⏳ |
| Království | `--sector "Království"` | ⏳ |
| Město | `--sector "Město"` | ⏳ |
| Milenecká hora | `--sector "Milenecká hora"` | ✅ done |
| Ostrov | `--sector "Ostrov"` | ⏳ |
| Panoptikum | `--sector "Panoptikum"` | ⏳ |
| Podhradí | `--sector "Podhradí"` | ⏳ |
| Rokle nad Spáleným mlýnem | `--sector "Rokle nad Spáleným mlýnem"` | ⏳ |
| Vstupní obvod | `--sector "Vstupní obvod"` | ⏳ |
| Za pískovnou | `--sector "Za pískovnou"` | ⏳ |

**After Adršpach**: Add sector URLs for Broumovské stěny, Ostaš, Teplice, Křižový vrch to `ADRSPACH_SECTORS` dict in `piskari-scraper.py`.

**MVP scope clarified**: 1–2 users (friends). Does not need to be polished. Hard requirement: full offline capability (map + route content). `product-spec.md` fully rewritten to reflect this.

---

## 2026-05-24 — Himálaj done; Křížový vrch scraper support added

**Himálaj sector completed**: `piskovce-himalaj.gpx` generated and tested with positive result. ✅

**Křížový vrch added to scraper**: User confirmed that Křížový vrch is a distinct area (not an Adršpach sub-area) with 3 obvods on piskari.cz. It has its own URL namespace (`/cs/krizovy-vrch/`). The scraper was extended to support it:

- Added `KRIZOVY_VRCH_SECTORS` dict with all 3 obvods:
  - `"Jižní věže"` → `/cs/krizovy-vrch/jizni-veze-22/`
  - `"Křížový hřeben"` → `/cs/krizovy-vrch/krizovy-hreben-23/`
  - `"Zdoňovský oblouk"` → `/cs/krizovy-vrch/zdonovsky-oblouk-24/`
- Added `--kv-sector "Name"` flag (single obvod)
- Added `--all-krizovy-vrch` flag (all 3 obvods → `piskovce-krizovy-vrch.gpx`)
- All existing flags (`--add-comments`, `--retry`, `--tower`, etc.) work unchanged

**Script architecture decision**: Each area gets its own named dict rather than merging everything into `ADRSPACH_SECTORS`. Future areas (Broumovské stěny, Ostaš, Teplické skály) follow the same pattern.

**Pages updated**:
- `wiki/krizovy-vrch.md` — fully rewritten: obvod table, piskari.cz URLs, scraper commands, GPX workflow
- `wiki/technical.md` — CLI flags table updated with `--kv-sector` / `--all-krizovy-vrch`; "Extending to other areas" section rewritten to document the per-area dict pattern
- `wiki/index.md` — Křížový vrch entry updated to reflect scraper support

**Křížový vrch towers**: Not yet scraped. Ready to run whenever needed.

---

## 2026-05-24 — Křížový vrch GPS pipeline: gipfelbuch.de + cp1250 encoding fix

**Problem**: piskari.cz has no GPS for Křížový vrch towers (no Google Maps embed on tower pages). Running `--kv-sector "Jižní věže"` produced a JSON with 30 towers, all `lat=None`.

**Solution**: GPS sourced from `db-sandsteinklettern.gipfelbuch.de` (German sandstone DB), which covers the same towers under "Křížový_vrch/Kreuzberg (Holsterberg)". The matching key is the Czech tower name published on both sites.

**New script**: `gipfelbuch-gps.py` — patches an existing piskovce-*.json with GPS from gipfelbuch.de. Uses `requests` + `beautifulsoup4` (no Playwright needed — static HTML). Supports `--sektor "Name"` and `--all-kv`.

**Encoding bug found and fixed**: The script initially used `iso-8859-2`. gipfelbuch.de actually uses **cp1250** (Windows-1250). In cp1250, `\x9a` = `š` and `\x9e` = `ž`; in iso-8859-2 those bytes are invisible control characters. This caused `Tomášova věžička` to appear as `Tomá\x9aova vě\x9eička` — name normalization failed and the tower got no GPS. Fixed by changing `ENCODING = "cp1250"`.

**Jižní věže result**: Data merged. Some towers still missing GPS (not present on gipfelbuch.de) or had residual name mismatches — these were verified manually by the user.

**Workflow for Křížový vrch** (3 steps, differs from Adršpach):
```
1. python piskari-scraper.py --kv-sector "Name" --headless   → JSON (no GPS)
2. python gipfelbuch-gps.py --sektor "Name" --json FILE.json → GPS patched, GPX written
3. python piskari-scraper.py --add-comments FILE.json        → route details + comments
```

**Pages updated**:
- `wiki/krizovy-vrch.md` — full rewrite: gipfelbuch GPS source documented, workflow updated with 3-step pipeline, encoding note added, GPS gaps explained
- `wiki/technical.md` — new section "Script: gipfelbuch-gps.py" with requirements, encoding table, CLI flags, sektorid map

---

## 2026-05-25 — mapycz-gps.py: GPS from mapy.com REST API

**New script**: `mapycz-gps.py` — geocodes tower names via the official mapy.com REST API (`type=poi`) and patches existing piskovce-*.json files.

**Motivation**: gipfelbuch.de only covers Křížový vrch and has partial coverage. mapy.com API works for all 5 areas and is a stable, versioned REST endpoint (no scraping).

**Key design decisions**:
- API key prompted at runtime via `getpass` — never stored in the script or on disk
- Bounding box auto-detected from the JSON filename — filters out false POI matches from other parts of CZ
- Only patches towers with `lat=None` by default; `--all` flag re-geocodes everything
- `--dry-run` mode for safe testing before committing changes
- Chains cleanly after `gipfelbuch-gps.py` — safe to run both in sequence

**Pricing**: 4 credits per call, 250,000 free credits/month on Basic tariff. The entire five-area project is ~1,000–2,000 towers — well inside the free tier.

**Test result**: Dry-run on `piskovce-jizni-v-ze.json` (Jižní věže). Partial coverage — works for towers mapy.cz indexes as POIs, misses some. Results manually verified against map. Accepted as a useful second-pass fallback after gipfelbuch-gps.py.

**Recommended GPS strategy** (documented in technical.md):
- Adršpach: `piskari-scraper.py` → `mapycz-gps.py` (fallback for 3xxx IDs)
- Křížový vrch: `piskari-scraper.py` → `gipfelbuch-gps.py` → `mapycz-gps.py` → manual
- Future areas: `piskari-scraper.py` → `mapycz-gps.py` → manual

**Pages updated**:
- `wiki/technical.md` — new section "Script: mapycz-gps.py" with CLI flags, bbox table, GPS source comparison table, recommended strategy per area
- `wiki/krizovy-vrch.md` — GPS gaps section updated to include mapycz-gps.py as second automated pass

---

## 2026-05-25 — Křížový vrch complete ✅

All 3 Křížový vrch obvods fully processed (routes + GPS + comments): Jižní věže, Křížový hřeben, Zdoňovský oblouk. GPX files ready for Locus Map import.

**Pages updated**:
- `wiki/krizovy-vrch.md` — all 3 obvods marked ✅, summary updated
- `wiki/index.md` — Křížový vrch marked complete

---

## 2026-05-25 — Raw source removed; wiki linted; product refocus

**Trigger**: User removed the sole raw source file (`lezení na českém písku...md`) and requested a lint + product refocus. piskari.cz is now explicitly one of several data sources, not "the single source".

**Dead links removed** (routes/ folder was deleted 2026-05-20 but links persisted):
- `adrspach.md` — `[[routes/bicovani-u-stezne]]` → plain text
- `vez-bounty.md` — same
- `ostas.md` — `[[routes/doutniky]]`, `[[routes/nenazvuhodna-prasecina]]`, `[[routes/jarnicka]]` → plain text
- `vez-rybnik.md` — `[[routes/doutniky]]` → plain text
- `vez-zdarska-vyhlidka.md` — `[[routes/jarnicka]]` → plain text
- `ovk-broumovsko.md` — same two route links → plain text
- `czech-climbing-grades.md` — `[[routes/zensen]]` → removed

**Stale source references removed** — 13 pages had `Sources: lezení na českém písku...md` pointing to a deleted file. Updated to reflect actual living sources (piskari.cz, ovkbroumovsko.cz).

**Stale facts fixed**:
- `adrspach.md` — GPS source corrected from mapy.cz → piskari.cz
- `sektor-milenecka-hora.md` — GPS source corrected; "TBD" status replaced with actual stats (125/129 towers, GPX complete ✅)
- `sektor-dolni-adrspach.md` — mapy.cz reference removed
- `vez-adam-a-eva.md` — "pending confirmation" language removed; GPS confirmed
- `howto-generate-gpx.md` — Himálaj marked ✅ done; KV workflow note added

**Product refocus** — `product-spec.md` significantly updated:
- "Single source: piskari.cz" section replaced with "Data sources" table (piskari.cz + gipfelbuch.de + mapy.com API)
- GPS-by-area table added (different sources per area)
- Open questions pruned (GPS confirmed, mapy.com dropped)
- Next steps updated to reflect actual pipeline status (Milenecká hora ✅, Himálaj ✅, Křížový vrch ✅)
