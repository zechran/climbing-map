#!/usr/bin/env python3
"""
mapycz-gps.py
=============
Fetches GPS coordinates from the mapy.com REST API (geocoding, type=poi)
and patches an existing piskovce-*.json file produced by piskari-scraper.py.

Works for ANY area — Adršpach, Křížový vrch, Broumovské stěny, etc.
Useful as:
  - primary GPS source for areas where piskari.cz has no GPS
  - fallback to fill towers still missing after gipfelbuch-gps.py

API key is prompted at runtime (not stored here).
Get a free key at: https://developer.mapy.com/rest-api-mapy-cz/how-to-start/
Each geocoding call costs 4 credits. Free tier: 250,000 credits/month.

Usage:
  python mapycz-gps.py --json piskovce-jizni-v-ze.json
  python mapycz-gps.py --json piskovce-himalaj.json --all   # also retry already-set GPS
  python mapycz-gps.py --json piskovce-himalaj.json --dry-run

Requirements:
  pip install requests
"""

from __future__ import annotations
import argparse
import getpass
import json
import os
import sys
import time
import unicodedata
import xml.dom.minidom
import xml.etree.ElementTree as ET
import re
from datetime import datetime
from pathlib import Path

import requests

GEOCODE_URL = "https://api.mapy.cz/v1/geocode"

# Bounding boxes for each area: (min_lon, min_lat, max_lon, max_lat)
# Used to validate that the returned POI is actually in the right area,
# not a same-named feature somewhere else in CZ.
AREA_BBOX = {
    "adrspach":          (16.05, 50.57, 16.22, 50.67),
    "krizovy-vrch":      (16.08, 50.59, 16.20, 50.67),
    "broumovske-steny":  (16.27, 50.52, 16.50, 50.65),
    "ostas":             (16.10, 50.54, 16.25, 50.62),
    "teplice":           (16.05, 50.57, 16.22, 50.67),
    # broad fallback covering entire Polická pánev
    "default":           (15.80, 50.40, 16.60, 50.80),
}

# Map JSON filename prefixes → area bbox key
def bbox_for_json(json_path: Path) -> tuple:
    name = json_path.stem.lower()
    if "himalaj" in name or "jezerka" in name or "kralovstvi" in name \
            or "mesto" in name or "milenecka" in name or "ostrov" in name \
            or "panoptikum" in name or "podhrati" in name or "rokle" in name \
            or "vstupni" in name or "piskovnou" in name:
        return AREA_BBOX["adrspach"]
    if "jizni" in name or "krizovy" in name or "zdonovsky" in name:
        return AREA_BBOX["krizovy-vrch"]
    if "broumov" in name:
        return AREA_BBOX["broumovske-steny"]
    if "ostas" in name:
        return AREA_BBOX["ostas"]
    if "teplice" in name:
        return AREA_BBOX["teplice"]
    return AREA_BBOX["default"]


# ── helpers ──────────────────────────────────────────────────────────────────

def slugify(name: str) -> str:
    """Same slugify as piskari-scraper.py — derives JSON filename from sector name."""
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


def normalize(text: str) -> str:
    """Lowercase + strip diacritics — for result name validation."""
    nfkd = unicodedata.normalize("NFKD", text)
    ascii_only = "".join(c for c in nfkd if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", ascii_only).strip().lower()


def in_bbox(lat: float, lon: float, bbox: tuple) -> bool:
    min_lon, min_lat, max_lon, max_lat = bbox
    return min_lat <= lat <= max_lat and min_lon <= lon <= max_lon


# ── API call ─────────────────────────────────────────────────────────────────

def geocode(name: str, api_key: str, bbox: tuple, limit: int = 5) -> dict | None:
    """
    Call mapy.com geocoding API for a tower name.
    Returns the best matching item dict, or None if nothing useful found.

    Response shape:
      {"items": [{"name": "...", "label": "...", "position": {"lon": .., "lat": ..}, ...}]}
    """
    params = {
        "query": name,
        "type":  "poi",
        "lang":  "cs",
        "limit": limit,
        "apikey": api_key,
    }
    try:
        r = requests.get(GEOCODE_URL, params=params, timeout=10)
        if r.status_code == 401:
            print("\n❌ API key rejected (HTTP 401). Check your key and try again.")
            sys.exit(1)
        if r.status_code == 429:
            print("\n⚠️  Rate limited (HTTP 429). Waiting 5 seconds...")
            time.sleep(5)
            r = requests.get(GEOCODE_URL, params=params, timeout=10)
        r.raise_for_status()
    except requests.RequestException as e:
        print(f"\n  HTTP error: {e}", file=sys.stderr)
        return None

    data = r.json()
    items = data.get("items", [])
    if not items:
        return None

    norm_query = normalize(name)

    # Prefer items inside the bounding box; among those, prefer name match
    candidates = []
    for item in items:
        pos = item.get("position", {})
        lat = pos.get("lat")
        lon = pos.get("lon")
        if lat is None or lon is None:
            continue
        inside = in_bbox(lat, lon, bbox)
        result_name = normalize(item.get("name", ""))
        name_match = (result_name == norm_query)
        candidates.append((inside, name_match, lat, lon, item))

    # Sort: bbox-inside first, name-match second
    candidates.sort(key=lambda x: (x[0], x[1]), reverse=True)

    if not candidates:
        return None

    best_inside, best_name_match, lat, lon, item = candidates[0]

    if not best_inside:
        # Result is outside the expected area — likely a false match
        return None

    return {"lat": lat, "lon": lon, "name": item.get("name", ""), "label": item.get("label", "")}


# ── GPX writer (mirrors piskari-scraper.py) ───────────────────────────────────

def build_desc(tower: dict) -> str:
    lines = []
    if tower.get("area") or tower.get("sector"):
        lines.append(f"OBLAST: {tower.get('area', '')} / {tower.get('sector', '')}")
    lines.append("ZDROJ: piskari.cz")
    lines.append(f"URL: {tower.get('url', '')}")
    lines.append("")
    if tower.get("routes"):
        lines.append("--- CESTY ---")
        for i, r in enumerate(tower["routes"], 1):
            grade = f" | {r['grade']}" if r.get("grade") else ""
            date  = f" ({r['date']})"  if r.get("date")  else ""
            lines.append(f"{i}. {r['name']}{grade}{date}")
            if r.get("charakter"):
                lines.append(f"   Charakter: {r['charakter']}")
            if r.get("popis"):
                lines.append(f"   Popis: {r['popis']}")
            if r.get("autor"):
                lines.append(f"   Autor: {r['autor']}")
            coms = r.get("comments", [])
            if coms:
                lines.append("   Komentáře:")
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
        if t.get("lat") is None or t.get("lon") is None:
            skipped += 1
            continue
        wpt = ET.SubElement(gpx, "wpt", {
            "lat": f"{t['lat']:.7f}",
            "lon": f"{t['lon']:.7f}",
        })
        ET.SubElement(wpt, "name").text = t["name"]
        ET.SubElement(wpt, "desc").text = build_desc(t)
        ET.SubElement(wpt, "sym").text = "Flag, Blue"

    rough = ET.tostring(gpx, encoding="unicode")
    pretty = xml.dom.minidom.parseString(rough).toprettyxml(indent="  ", encoding="utf-8")
    with open(output_path, "wb") as f:
        f.write(pretty)

    total = len(towers)
    with_gps = total - skipped
    print(f"\n✅ GPX written: {output_path}")
    print(f"   {with_gps}/{total} towers have GPS  ({skipped} skipped — no GPS found)")


# ── main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Patch piskovce-*.json with GPS from mapy.com geocoding API"
    )
    src = parser.add_mutually_exclusive_group(required=True)
    src.add_argument(
        "--json", metavar="FILE",
        help="Path to existing piskovce-*.json produced by piskari-scraper.py"
    )
    src.add_argument(
        "--sector", metavar="NAME",
        help='Sector name (e.g. "Himálaj") — JSON path is derived automatically'
    )
    parser.add_argument(
        "--all", action="store_true", dest="patch_all",
        help="Re-geocode ALL towers, not just those missing GPS (use to refresh/verify)"
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Print what would be patched without modifying any files"
    )
    parser.add_argument(
        "--no-gpx", action="store_true",
        help="Skip GPX regeneration (update JSON only)"
    )
    args = parser.parse_args()

    if args.sector:
        json_path = Path(f"piskovce-{slugify(args.sector)}.json")
    else:
        json_path = Path(args.json)
    if not json_path.exists():
        print(f"❌ File not found: {json_path}")
        sys.exit(1)

    # API key: use environment variable if set, otherwise prompt interactively
    api_key = os.environ.get("MAPYCZ_API_KEY", "").strip()
    if api_key:
        print("ℹ️  Using API key from MAPYCZ_API_KEY environment variable.")
    else:
        api_key = getpass.getpass("mapy.com API key: ")
    if not api_key.strip():
        print("❌ No API key entered.")
        sys.exit(1)

    towers = json.loads(json_path.read_text(encoding="utf-8"))
    bbox = bbox_for_json(json_path)
    label = json_path.stem.replace("piskovce-", "").replace("-", " ").title()

    to_process = [t for t in towers if args.patch_all or t.get("lat") is None]
    already_set = len(towers) - len(to_process)

    print(f"\n📍 {json_path.name}: {len(towers)} towers total")
    if already_set:
        print(f"   {already_set} already have GPS — skipping (use --all to re-geocode)")
    print(f"   {len(to_process)} to geocode via mapy.com API")
    if args.dry_run:
        print("   [DRY RUN — no files will be modified]")
    print()

    matched = 0
    not_found = []

    for i, tower in enumerate(to_process):
        name = tower["name"]
        result = geocode(name, api_key, bbox)
        time.sleep(0.1)  # stay well within rate limits

        if result:
            print(f"  [{i+1}/{len(to_process)}] {name!r:35s} → {result['lat']:.5f},{result['lon']:.5f}  ({result['label']})")
            if not args.dry_run:
                tower["lat"] = result["lat"]
                tower["lon"] = result["lon"]
            matched += 1
        else:
            print(f"  [{i+1}/{len(to_process)}] {name!r:35s} → NOT FOUND in bbox")
            not_found.append(name)

    print(f"\n   Geocoded: {matched}/{len(to_process)}")

    if not_found:
        print(f"\n   ⚠️  {len(not_found)} towers not found (outside bbox or no POI match):")
        for n in not_found:
            print(f"      {n!r}")
        print("   Tip: check spelling on mapy.cz or add GPS manually to the JSON.")

    if args.dry_run:
        print("\n   [DRY RUN complete — no files written]")
        return

    # Save updated JSON
    json_path.write_text(json.dumps(towers, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n   JSON saved: {json_path}")

    # Regenerate GPX
    if not args.no_gpx:
        gpx_path = json_path.with_suffix(".gpx")
        write_gpx(towers, gpx_path, label)


if __name__ == "__main__":
    main()
