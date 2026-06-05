# Wiki Index

**Summary**: Knowledge base for a climbing map product combining GPS tower data from mapy.com with route descriptions and comments from piskari.cz.

**Hierarchy**: Area → Sector → Tower → Route → Comments

**Last updated**: 2026-05-28

---

## Product

- [[product-spec]] — Product specification: problem, data architecture, GPX delivery format, user journey, next steps
- [[technical]] — Technical documentation: piskari.cz site structure, scraper architecture, JSON data model, GPX format, GPS extraction method, known limitations, extending to new areas
- [[howto-generate-gpx]] — Step-by-step guide: how to generate a GPX for a sector, manually via terminal or via parallel agents
- [[publishing]] — How the wiki is built and published to GitHub Pages
- [[climber-filter]] — How to generate a personal GPX map for a specific climber using `climber-filter.py`
- [[qa-report]] — How to validate sector JSON data quality against live piskari.cz using random sampling

## Domain knowledge

- [[czech-sandstone-climbing]] — Ethics, style, and gear of traditional Czech sandstone climbing
- [[czech-climbing-grades]] — Czech sandstone grading system (Roman numeral + letter scale)

## Data sources

- [[piskari-cz]] — piskari.cz: **single data source** — areas, sectors, towers, GPS (JS map), routes, grades, protection notes, and climber comments
- [[policka-panev]] — Polická pánev (Police Basin): the five-area region this project covers
- [[ovk-broumovsko]] — Regional climbing committee; governs access, first ascents, closures

## Spatial data model
*(Tower pages are the core unit: GPS + routes both from piskari.cz)*

### Adršpach (Ádr)
- [[adrspach]] — Area overview
  - [[sektor-dolni-adrspach]] — Dolní Adršpach (sub-area)
    - [[sektor-milenecka-hora]] — Milenecká hora (sector)
      - [[vez-adam-a-eva]] — Skalní věž Adam a Eva · GPS 50.6084167N, 16.1159444E ✓

### Broumovské stěny (Broumovky)
- [[broumovske-steny]] — Area overview *(sectors and towers TBD)*

### Ostaš
- [[ostas]] — Area overview
  - [[vez-rybnik]] — Rybník tower, Horní Ostaš *(GPS TBD)*
  - [[vez-zdarska-vyhlidka]] — Žďárská vyhlídka *(GPS TBD)*

### Teplické skály (Teplice)
- [[teplicke-skaly]] — Area overview *(sectors and towers TBD)*

### Křížový vrch (Křížák)
- [[krizovy-vrch]] — Area overview; all 3 obvods fully processed ✅ (routes + GPS + comments)

---

*Route-level data (individual routes and comments) lives in piskari.cz and is embedded in tower GPX descriptions at generation time — it is not separately catalogued in this wiki.*
