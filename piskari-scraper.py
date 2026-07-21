#!/usr/bin/env python3
from __future__ import annotations
"""
piskari-scraper.py
==================
Scrapes piskari.cz to build a GPX file for use in Locus Map.

What it does:
  1. Crawls all pages of a sector (e.g. Milenecká hora) to collect tower URLs
  2. For each tower: opens the page, loads the Google Maps panel, reads GPS via
     window.map.getCenter(), and scrapes routes + recent comments
  3. Writes one GPX <wpt> per tower with routes and comments in <desc>

Requirements:
  pip install playwright
  python -m playwright install chromium

Usage:
  python3 piskari-scraper.py                    # Milenecká hora (default)
  python3 piskari-scraper.py --sector 1          # Himálaj
  python3 piskari-scraper.py --all-adrspach      # all 11 Adršpach sectors
  python3 piskari-scraper.py --tower /cs/skala/adam-a-eva-1378/  # single tower

Output:
  piskovce-milenecka-hora.gpx  (or named by sector/area)
"""

import asyncio
import argparse
import json
import re
import sys
import xml.etree.ElementTree as ET
import xml.dom.minidom
from datetime import datetime
from pathlib import Path

from playwright.async_api import async_playwright, TimeoutError as PWTimeout

BASE_URL = "https://www.piskari.cz"

# Adršpach sector index: name → URL path
ADRSPACH_SECTORS = {
    "Himálaj":                    "/cs/adrspach/himalaj-1/",
    "Jezerka":                    "/cs/adrspach/jezerka-4/",
    "Království":                 "/cs/adrspach/kralovstvi-5/",
    "Město":                      "/cs/adrspach/mesto-6/",
    "Milenecká hora":             "/cs/adrspach/milenecka-hora-7/",
    "Ostrov":                     "/cs/adrspach/ostrov-8/",
    "Panoptikum":                 "/cs/adrspach/panoptikum-9/",
    "Podhradí":                   "/cs/adrspach/podhrati-10/",
    "Rokle nad Spáleným mlýnem":  "/cs/adrspach/rokle-nad-spalenim-mlynem-12/",
    "Vstupní obvod":              "/cs/adrspach/vstupni-obvod-14/",
    "Za pískovnou":               "/cs/adrspach/za-piskovnou-15/",
}

# Křížový vrch obvod index: name → URL path
KRIZOVY_VRCH_SECTORS = {
    "Jižní věže":        "/cs/krizovy-vrch/jizni-veze-22/",
    "Křížový hřeben":    "/cs/krizovy-vrch/krizovy-hreben-23/",
    "Zdoňovský oblouk":  "/cs/krizovy-vrch/zdonovsky-oblouk-24/",
}


# ── helpers ──────────────────────────────────────────────────────────────────

def gpx_escape(text: str) -> str:
    """Escape special XML characters."""
    return (text
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;"))


def slugify(name: str) -> str:
    name = name.lower()
    name = re.sub(r"[áa]", "a", name)
    name = re.sub(r"[čc]", "c", name)
    name = re.sub(r"[ďd]", "d", name)
    name = re.sub(r"[ěée]", "e", name)
    name = re.sub(r"[íi]", "i", name)
    name = re.sub(r"[ňn]", "n", name)
    name = re.sub(r"[óo]", "o", name)
    name = re.sub(r"[řr]", "r", name)
    name = re.sub(r"[šs]", "s", name)
    name = re.sub(r"[ťt]", "t", name)
    name = re.sub(r"[úůu]", "u", name)
    name = re.sub(r"[ýy]", "y", name)
    name = re.sub(r"[žz]", "z", name)
    name = re.sub(r"[^a-z0-9]+", "-", name)
    return name.strip("-")


# ── scraping ─────────────────────────────────────────────────────────────────

async def collect_tower_urls(page, sector_path: str) -> list[dict]:
    """Return list of {name, url} for all towers in a sector (all pages)."""
    towers = []
    page_num = 0
    while True:
        path = sector_path if page_num == 0 else f"{sector_path}{page_num}/"
        url = BASE_URL + path
        await page.goto(url, wait_until="domcontentloaded")
        links = await page.eval_on_selector_all(
            'a[href*="/cs/skala/"]',
            "els => els.map(e => ({name: e.textContent.trim(), url: e.pathname}))"
        )
        if not links:
            break
        towers.extend(links)
        page_num += 1
        # Check if there's a next page link
        has_next = await page.query_selector(f'a[href*="{sector_path}{page_num}/"]')
        if not has_next:
            break
    # Deduplicate (same tower can appear in "okolní věže" sections)
    seen = set()
    unique = []
    for t in towers:
        if t["url"] not in seen:
            seen.add(t["url"])
            unique.append(t)
    return unique


async def get_tower_data(page, tower_url: str) -> dict | None:
    """
    Visit a tower page, extract GPS + routes + comments.
    Returns dict with keys: name, area, sector, lat, lon, routes
    or None if extraction fails.
    """
    full_url = BASE_URL + tower_url
    try:
        await page.goto(full_url, wait_until="domcontentloaded", timeout=30000)
    except PWTimeout:
        print(f"  TIMEOUT loading {full_url}", file=sys.stderr)
        return None

    # ── tower name and breadcrumb ──
    try:
        heading = await page.inner_text("h1")
    except Exception:
        heading = ""
    # h1 format: "Adam a Eva (Adršpach — Milenecká hora)"
    name_match = re.match(r"^(.+?)\s*\((.+?)\s*[–—]\s*(.+?)\)\s*$", heading)
    tower_name = name_match.group(1).strip() if name_match else heading.strip()
    area_name  = name_match.group(2).strip() if name_match else ""
    sector_name = name_match.group(3).strip() if name_match else ""

    # ── routes: find all /cs/cesta/ links on the page ──
    routes = []
    try:
        route_links = await page.query_selector_all('a[href*="/cs/cesta/"]')
        for link in route_links:
            rname = (await link.inner_text()).strip()
            rhref = await link.get_attribute("href") or ""
            # Get grade and date from the surrounding table cell
            cell_text = await link.evaluate(
                'el => el.closest("td") ? el.closest("td").innerText : el.parentElement.innerText'
            )
            cell_text = re.sub(r'\s+', ' ', cell_text).strip()
            grade_match = re.search(r'\b(I{1,3}|IV|IX|X[abc]?|VI{1,3}[abc]?|V[abc]?|[IVX]+[abc])\b', cell_text)
            grade = grade_match.group(0) if grade_match else ""
            date_match = re.search(r'\((\d{1,2}\.\d{1,2}\.\d{4})\)', cell_text)
            date_str = date_match.group(1) if date_match else ""
            if rname:
                routes.append({"name": rname, "grade": grade, "date": date_str, "url": rhref})
    except Exception as e:
        print(f"  Route scrape error for {tower_name}: {e}", file=sys.stderr)

    # ── GPS: not extracted here ──
    # mapy.com is the single GPS source of truth.
    # Run mapycz-gps.py after this script to populate lat/lon via the mapy.com API.
    lat, lon = None, None

    return {
        "name": tower_name,
        "area": area_name,
        "sector": sector_name,
        "lat": lat,
        "lon": lon,
        "url": full_url,
        "routes": routes,
    }


async def get_route_details(page, route_url: str, max_comments: int = 8) -> dict:
    """
    Fetch full route detail page: description, character, author, and comments.
    Returns dict with keys: popis, charakter, autor, comments (list of strings).
    """
    result = {"popis": "", "charakter": "", "autor": "", "comments": []}
    if not route_url:
        return result
    try:
        url = BASE_URL + route_url if route_url.startswith("/") else route_url
        await page.goto(url, wait_until="domcontentloaded", timeout=20000)

        # ── route metadata: popis, charakter, autor ──
        # Appear on the page as: <strong>popis</strong>: value<br>
        # NOT inside a <td> — use JS to walk <strong> siblings.
        meta = await page.evaluate("""
            () => {
                const out = {popis: '', charakter: '', autor: ''};
                for (const s of document.querySelectorAll('strong')) {
                    const key = s.textContent.trim().toLowerCase();
                    if (key in out) {
                        const node = s.nextSibling;
                        if (node && node.nodeType === 3) {
                            out[key] = node.textContent.replace(/^[:\\s]+/, '').trim();
                        }
                    }
                }
                return out;
            }
        """)
        result["popis"]     = meta.get("popis", "")
        result["charakter"] = meta.get("charakter", "")
        result["autor"]     = meta.get("autor", "")

        # ── comments from table.komentare ──
        # Rows alternate: [date + username] [comment text] [date + username] [comment text] ...
        rows = await page.query_selector_all("table.komentare tr")
        skip_phrases = {"uživatel cestu pouze hodnotil, nekomentoval."}
        i = 0
        while i < len(rows) and len(result["comments"]) < max_comments:
            header_text = re.sub(r'\s+', ' ', (await rows[i].inner_text()).strip())
            i += 1
            if i < len(rows):
                body_text = re.sub(r'\s+', ' ', (await rows[i].inner_text()).strip())
                i += 1
            else:
                body_text = ""
            if body_text.lower() in skip_phrases or not body_text:
                continue
            # Format: "[date user] comment"
            result["comments"].append(f"[{header_text}] {body_text}")

    except Exception as e:
        pass
    return result


# ── GPX assembly ─────────────────────────────────────────────────────────────

def build_desc(tower: dict) -> str:
    lines = []
    if tower["area"] or tower["sector"]:
        lines.append(f"OBLAST: {tower['area']} / {tower['sector']}")
    lines.append(f"ZDROJ: piskari.cz")
    lines.append(f"URL: {tower['url']}")
    lines.append("")

    if tower["routes"]:
        lines.append("--- CESTY ---")
        for i, r in enumerate(tower["routes"], 1):
            grade = f" | {r['grade']}" if r["grade"] else ""
            date  = f" ({r['date']})" if r["date"] else ""
            lines.append(f"{i}. {r['name']}{grade}{date}")
            if r.get("charakter"):
                lines.append(f"   Charakter: {r['charakter']}")
            if r.get("popis"):
                lines.append(f"   Popis: {r['popis']}")
            if r.get("autor"):
                lines.append(f"   Autor: {r['autor']}")
            coms = r.get("comments", [])
            if coms:
                lines.append(f"   Komentáře:")
                for c in coms:
                    lines.append(f"   > {c}")
        lines.append("")

    return "\n".join(lines)


def write_gpx(towers: list[dict], output_path: Path, label: str):
    gpx = ET.Element("gpx", {
        "version": "1.1",
        "creator": "piskari-scraper.py + mapycz-gps.py",
        "xmlns": "http://www.topografix.com/GPX/1/1",
    })
    meta = ET.SubElement(gpx, "metadata")
    ET.SubElement(meta, "name").text = f"Piskovce — {label}"
    ET.SubElement(meta, "desc").text = (
        f"Climbing towers from piskari.cz — {label}. "
        f"GPS from mapy.com API. Generated {datetime.now().strftime('%Y-%m-%d')}."
    )

    skipped = 0
    for t in towers:
        if t["lat"] is None or t["lon"] is None:
            skipped += 1
            continue
        wpt = ET.SubElement(gpx, "wpt", {
            "lat": f"{t['lat']:.7f}",
            "lon": f"{t['lon']:.7f}",
        })
        ET.SubElement(wpt, "name").text = t["name"]
        ET.SubElement(wpt, "desc").text = build_desc(t)
        ET.SubElement(wpt, "sym").text = "Flag, Blue"

    # ET.indent is Python 3.9+ — use minidom for pretty-printing on 3.8
    rough = ET.tostring(gpx, encoding="unicode")
    pretty = xml.dom.minidom.parseString(rough).toprettyxml(indent="  ", encoding="utf-8")
    with open(output_path, "wb") as f:
        f.write(pretty)

    total = len(towers)
    with_gps = total - skipped
    print(f"\n✅ GPX written: {output_path}")
    print(f"   {with_gps}/{total} towers have GPS  ({skipped} skipped — map failed to load)")


# ── main ─────────────────────────────────────────────────────────────────────

async def main():
    parser = argparse.ArgumentParser(description="Scrape piskari.cz → GPX for Locus Map")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--sector", metavar="NAME",
                       default="Milenecká hora",
                       help="Adršpach sector name from ADRSPACH_SECTORS (default: Milenecká hora)")
    group.add_argument("--all-adrspach", action="store_true",
                       help="Scrape all 11 Adršpach sectors")
    group.add_argument("--kv-sector", metavar="NAME",
                       help="Křížový vrch obvod name from KRIZOVY_VRCH_SECTORS")
    group.add_argument("--all-krizovy-vrch", action="store_true",
                       help="Scrape all 3 Křížový vrch obvods")
    group.add_argument("--tower", metavar="PATH",
                       help="Single tower path, e.g. /cs/skala/adam-a-eva-1378/")
    group.add_argument("--add-comments", metavar="JSON_FILE_OR_SECTOR",
                       help="Enrich an existing JSON with route descriptions and comments, then regenerate GPX. "
                            "Accepts either a JSON filename or a sector name (e.g. \"Himálaj\") — "
                            "if a sector name is given, the JSON path is derived automatically.")
    group.add_argument("--rebuild-gpx", metavar="JSON_FILE_OR_SECTOR",
                       help="Rebuild GPX from an existing JSON without any web access. "
                            "Use after manually editing GPS coordinates in the JSON. "
                            "Accepts either a JSON filename or a sector name.")
    parser.add_argument("--output", metavar="FILE",
                       help="Output GPX path (default: auto-named)")
    parser.add_argument("--headless", action="store_true", default=False,
                       help="Run browser in headless mode (default: visible)")
    args = parser.parse_args()

    # --rebuild-gpx: no browser needed — read JSON, write GPX, done
    if args.rebuild_gpx:
        raw = args.rebuild_gpx
        json_file = Path(raw) if raw.endswith(".json") else Path(f"piskovce-{slugify(raw)}.json")
        if not json_file.exists():
            print(f"❌ File not found: {json_file}")
            sys.exit(1)
        towers = json.loads(json_file.read_text(encoding="utf-8"))
        label = json_file.stem.replace("piskovce-", "").replace("-", " ").title()
        out = Path(args.output) if args.output else json_file.with_suffix(".gpx")
        write_gpx(towers, out, label)
        return

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=args.headless)
        context = await browser.new_context(locale="cs-CZ")
        page = await context.new_page()

        # Disable images and CSS to speed up loading
        await page.route("**/*.{png,jpg,jpeg,gif,svg,css,woff,woff2}", lambda r: r.abort())

        towers = []
        label = ""

        if args.add_comments:
            # Enrich existing JSON with popis, charakter, autor, comments per route
            # Accept either a JSON filename or a sector name
            raw = args.add_comments
            if raw.endswith(".json"):
                json_file = Path(raw)
            else:
                json_file = Path(f"piskovce-{slugify(raw)}.json")
            towers = json.loads(json_file.read_text(encoding="utf-8"))
            # Count total routes to visit
            route_urls = [(t, r) for t in towers for r in t.get("routes", []) if r.get("url")]
            print(f"Fetching details for {len(route_urls)} routes across {len(towers)} towers...")
            for idx, (t, r) in enumerate(route_urls):
                already_done = bool(r.get("popis"))  # re-scrape if popis is still empty
                if already_done:
                    continue
                print(f"  [{idx+1}/{len(route_urls)}] {t['name']} — {r['name']}", end="  ", flush=True)
                details = await get_route_details(page, r["url"])
                r["popis"]     = details["popis"]
                r["charakter"] = details["charakter"]
                r["autor"]     = details["autor"]
                r["comments"]  = details["comments"]
                n = len(details["comments"])
                print(f"({n} comment{'s' if n != 1 else ''})")
            # Save enriched JSON
            json_file.write_text(json.dumps(towers, ensure_ascii=False, indent=2), encoding="utf-8")
            print(f"\n   JSON enriched: {json_file}")
            label = json_file.stem.replace("piskovce-", "").replace("-", " ").title()
            out = Path(args.output) if args.output else json_file.with_suffix(".gpx")
            await browser.close()
            write_gpx(towers, out, label)
            return

        elif args.tower:
            print(f"Scraping single tower: {args.tower}")
            data = await get_tower_data(page, args.tower)
            if data:
                towers = [data]
            label = data["name"] if data else "tower"

        elif args.all_adrspach:
            label = "Adršpach"
            for sector_name, sector_path in ADRSPACH_SECTORS.items():
                print(f"\n📍 Sector: {sector_name}")
                urls = await collect_tower_urls(page, sector_path)
                print(f"   Found {len(urls)} towers")
                for i, t in enumerate(urls):
                    print(f"   [{i+1}/{len(urls)}] {t['name']}", end=" ", flush=True)
                    data = await get_tower_data(page, t["url"])
                    if data:
                        towers.append(data)
                        print(f"→ OK (GPS via mapycz-gps.py)")
                    else:
                        print("→ FAILED")

        elif args.all_krizovy_vrch:
            label = "Křížový vrch"
            for sector_name, sector_path in KRIZOVY_VRCH_SECTORS.items():
                print(f"\n📍 Obvod: {sector_name}")
                urls = await collect_tower_urls(page, sector_path)
                print(f"   Found {len(urls)} towers")
                for i, t in enumerate(urls):
                    print(f"   [{i+1}/{len(urls)}] {t['name']}", end=" ", flush=True)
                    data = await get_tower_data(page, t["url"])
                    if data:
                        towers.append(data)
                        print(f"→ OK (GPS via mapycz-gps.py)")
                    else:
                        print("→ FAILED")

        elif args.kv_sector:
            sector_name = args.kv_sector
            sector_path = KRIZOVY_VRCH_SECTORS.get(sector_name)
            if not sector_path:
                print(f"Unknown Křížový vrch obvod: {sector_name}")
                print("Available:", ", ".join(KRIZOVY_VRCH_SECTORS.keys()))
                sys.exit(1)
            label = sector_name
            print(f"\n📍 Collecting towers in: {sector_name}")
            urls = await collect_tower_urls(page, sector_path)
            print(f"   Found {len(urls)} towers")
            for i, t in enumerate(urls):
                print(f"[{i+1}/{len(urls)}] {t['name']}", end=" ", flush=True)
                data = await get_tower_data(page, t["url"])
                if data:
                    towers.append(data)
                    print("→ OK (GPS via mapycz-gps.py)")
                else:
                    print("→ FAILED")

        else:
            sector_name = args.sector
            sector_path = ADRSPACH_SECTORS.get(sector_name)
            if not sector_path:
                print(f"Unknown sector: {sector_name}")
                print("Available:", ", ".join(ADRSPACH_SECTORS.keys()))
                sys.exit(1)
            label = sector_name
            print(f"\n📍 Collecting towers in: {sector_name}")
            urls = await collect_tower_urls(page, sector_path)
            print(f"   Found {len(urls)} towers")
            for i, t in enumerate(urls):
                print(f"[{i+1}/{len(urls)}] {t['name']}", end=" ", flush=True)
                data = await get_tower_data(page, t["url"])
                if data:
                    towers.append(data)
                    print("→ OK (GPS via mapycz-gps.py)")
                else:
                    print("→ FAILED")

        await browser.close()

        # Output path
        if args.output:
            out = Path(args.output)
        else:
            out = Path(f"piskovce-{slugify(label)}.gpx")

        write_gpx(towers, out, label)

        # Also save raw JSON for debugging
        json_out = out.with_suffix(".json")
        json_out.write_text(json.dumps(towers, ensure_ascii=False, indent=2))
        print(f"   Raw data: {json_out}")


if __name__ == "__main__":
    asyncio.run(main())
