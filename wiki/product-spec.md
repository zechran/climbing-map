# Product Specification — Climbing Map

**Summary**: A mobile-first climbing map delivering GPS-located towers with route descriptions and climber comments, all sourced from piskari.cz, delivered as a GPX file and viewed in Locus Map.

**Status**: ✅ Pipeline built and validated — Adršpach (Himálaj ✅, Milenecká hora ✅) and Křížový vrch ✅ complete

**Last updated**: 2026-05-25

---

## Problem

Climbing information in the [[policka-panev]] region is all on piskari.cz, but piskari.cz is a web portal with no map. A climber in the field has to juggle a phone browser to look up a tower, with no offline capability, no GPS location, no navigation to the crag.

A climber standing in front of a sandstone tower needs to answer: *"What do I climb here, and how do I protect it?"* — without cell signal.

## Goal

Tap a tower on an offline map → see its routes, grades, protection character, and recent climber comments. No cell signal required.

---

## Users

**MVP phase** — 1–2 people (friends). Solution does not need to be polished or idiot-proof. Working is enough.

**Next phase** — broader climbing community. Smooth, shareable, maintainable.

---

## Hard requirements

- **Offline** — the full map and all route/comment content must be available without cell signal. Climbers frequently go off-grid in the mountains.
- **Both platforms** — Android and iOS must be covered.

---

## Data architecture

### Data sources

The map draws on three data sources depending on the area:

| Source | What it provides | Areas |
|--------|-----------------|-------|
| piskari.cz | Tower list, routes, grades, route detail, comments, GPS (via JS map) | All areas for routes; Adršpach for GPS |
| db-sandsteinklettern.gipfelbuch.de | GPS coordinates per tower | Křížový vrch (primary GPS) |
| mapy.com REST API (geocoding, `type=poi`) | GPS coordinates per tower name | All areas (fallback / gap-filler) |

piskari.cz is the primary source for climbing content (routes, comments). GPS sourcing varies by area because piskari.cz only embeds a Google Maps panel for Adršpach towers — other areas have no GPS on piskari.cz.

### GPS by area

| Area | GPS source |
|------|-----------|
| Adršpach | piskari.cz JS map (`window.map.getCenter()` after clicking the "mapa" tab) |
| Křížový vrch | gipfelbuch.de (primary) → mapy.com API (fallback) |
| Broumovské stěny, Ostaš, Teplické skály | mapy.com API (to be confirmed when scraped) |

### Hierarchy

```
Area  (e.g. Adršpach)
  └── Sector  (e.g. Milenecká hora)
        └── Tower  (e.g. Adam a Eva)         ← GPS from piskari.cz JS map
              └── Route  (e.g. Jižní, V)     ← from piskari.cz
                    └── Comments  (beta)      ← from piskari.cz
```

### URL patterns

| Level | Pattern | Example |
|-------|---------|---------|
| Area | `/cs/[area]/` | `/cs/adrspach/` |
| Sector | `/cs/[area]/[sector]-[ID]/` | `/cs/adrspach/milenecka-hora-7/` |
| Tower | `/cs/skala/[name]-[ID]/` | `/cs/skala/adam-a-eva-1378/` |
| Route | `/cs/cesta/[name]-[ID]/` | `/cs/cesta/jizni-2389/` |
| Tower search | `/cs/vyhledani-skalni-veze/` | alphabetical, paginated |

---

## Delivery format — GPX file

Each tower is one `<wpt>` waypoint. The `<name>` field is shown on the map; the `<desc>` field contains the full route sheet.

```xml
<wpt lat="50.6084167" lon="16.1159444">
  <name>Adam a Eva</name>
  <desc>
OBLAST: Adršpach / Milenecká hora
ZDROJ: piskari.cz

CESTY:
1. Jižní | V | (21.6.1961)
2. Senzační prázdniny | VIIc | (28.6.1971)
3. Severní | VIIIb | (28.6.1961)

KOMENTÁŘE:
[2026-05-10] Jižní: ...
[2026-04-28] Severní: ...
  </desc>
</wpt>
```

---

## Platform — Locus Map

### Why Locus Map

- **Czech-made app** (Asamm, Brno) — well known and trusted in the Czech/Slovak outdoor community
- **Android + iOS** — both platforms covered
- **GPX import with `<desc>`** — confirmed on both Android and iOS (see Test history)
- **Offline LoMaps** — downloadable offline maps covering Czech Republic including Adršpach/Broumov region
- **Sync across devices** — one person imports the GPX, both users sync via Locus Account (Premium Gold)
- **Guidance to waypoint** — tap a tower pin → navigate there

### Platform status (confirmed 2026-05-20)

| Feature | Android (Locus Map 4) | iOS (Locus Map Lite) |
|---------|----------------------|----------------------|
| GPX import — points | ✅ | ✅ confirmed |
| GPX `<desc>` rendering | ✅ | ✅ confirmed |
| Offline LoMaps | ✅ | ✅ confirmed |
| Sync Android ↔ iOS | ✅ | ✅ (Premium Gold) |
| Turn-by-turn navigation | ✅ | ❌ not yet |
| Guidance to waypoint | ✅ | ✅ |
| App maturity | Full | Early stage (started 2023) |

---

## Test history

### mapy.com — GPX `<desc>` — ❌ FAILED (2026-05-20)

Tested `test-adam-a-eva.gpx` (single waypoint, Adam a Eva) on mapy.com web (Safari) and iOS mobile, free and Premium.

- `<name>` displayed correctly ✅
- `<desc>` completely ignored — not shown anywhere ❌
- "Add note" exists but is Premium-only, manual, and not importable via GPX ⚠️

**Conclusion:** mapy.com is not viable. Dropped from the project entirely.

### Locus Map — GPX `<desc>` — ✅ CONFIRMED (2026-05-20)

Same file (`test-adam-a-eva.gpx`) imported into Locus Map Lite (iOS).

- `<desc>` content fully displayed when tapping the tower pin ✅
- Full description visible (no truncation observed) ✅
- Platform confirmed for iOS; Android known to work ✅

**Waypoint limit**: No hard limit on import. Display performance consideration at ~10,000 simultaneous points — well above the expected tower count for the full [[policka-panev]].

---

## MVP user journey

1. **One-time setup** — import `piskovce-adrspach.gpx` into Locus Map. File saved to My Library. (Optional: sync to second user via Locus Account.)
2. **Before the trip** — download offline LoMap for Czech Republic / Adršpach area in Locus Map.
3. **At the crag** — open Locus Map offline. Tower pins visible on map. Tap a tower → see routes and recent comments. No cell signal needed.
4. **Keeping current** — when piskari.cz has significant new comments, regenerate GPX and re-import (or sync via shared Locus account).

---

## Data pipeline

To generate the GPX, the following steps are needed:

1. **Crawl tower list** — fetch piskari.cz sector pages for each area to collect all tower names and URLs (e.g. all towers in Milenecká hora)
2. **Extract GPS per tower** — render each tower page (`/cs/skala/[name]-[ID]/`) in a JavaScript-capable browser; extract lat/lon from the map initialization code
3. **Extract routes per tower** — from the same page, collect route list (name, grade, date)
4. **Extract route detail** — optionally fetch `/cs/cesta/[name]-[ID]/` for protection notes and full description
5. **Extract comments** — collect recent comments from route pages
6. **Assemble GPX** — one `<wpt>` per tower, `<desc>` containing formatted route sheet + recent comments
7. **Test import** — import GPX into Locus Map and verify display

**Tooling options**: Claude in Chrome (interactive, one-off), Puppeteer/Playwright (automated, repeatable), Python + requests-html (for GPS extraction phase).

---

## Open questions

1. **Description length limit?** — How much text fits in `<desc>` before Locus Map truncates? Not yet hit a limit in practice.
2. **Update distribution** — How does a user get an updated GPX? Email, shared URL, Locus sync?
3. **GPS coverage for remaining areas** — mapy.com API assumed as GPS source for Broumovské stěny, Ostaš, Teplické skály — to be confirmed when those areas are scraped.

---

## Next steps

1. ✅ Platform confirmed — Locus Map (Android + iOS); `<desc>` renders fully on both
2. ✅ GPS extraction confirmed — `window.map.getCenter()` on piskari.cz tower pages (Adršpach)
3. ✅ Pipeline built — `piskari-scraper.py` (routes + GPS), `gipfelbuch-gps.py` (KV GPS), `mapycz-gps.py` (fallback GPS)
4. ✅ Milenecká hora — 125/129 towers, end-to-end validated in Locus Map
5. ✅ Himálaj — complete
6. ✅ Křížový vrch — all 3 obvods complete (routes + GPS + comments)
7. ⏳ Remaining 9 Adršpach sectors
8. ⏳ Broumovské stěny, Ostaš, Teplické skály — sector URLs to be collected, then scraped

---

## Related pages

- [[policka-panev]]
- [[adrspach]]
- [[czech-sandstone-climbing]]
- [[piskari-cz]]
- [[vez-adam-a-eva]]
- [[sektor-milenecka-hora]]
