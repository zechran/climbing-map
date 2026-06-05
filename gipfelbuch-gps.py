#!/usr/bin/env python3
"""
gipfelbuch-gps.py
=================
Fetches GPS coordinates from db-sandsteinklettern.gipfelbuch.de for
Křížový vrch towers and patches an existing piskovce-*.json file produced
by piskari-scraper.py.

Why this exists:
  piskari.cz does not publish GPS for Křížový vrch towers (no Google Maps
  embed on the tower pages). The German sandstone DB carries Gipfelkoordinaten
  for the same towers. The matching key is the Czech tower name.

Usage:
  python gipfelbuch-gps.py --sektor "Jižní věže" --json piskovce-jizni-v-ze.json
  python gipfelbuch-gps.py --all-kv                  # all 3 Křížový vrch sektors

Requirements:
  pip install requests beautifulsoup4

After running, re-generate the GPX:
  python piskari-scraper.py --add-comments piskovce-jizni-v-ze.json
"""

from __future__ import annotations
import argparse
import json
import re
import sys
import time
import unicodedata
import xml.dom.minidom
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path

import requests
from bs4 import BeautifulSoup

BASE = "http://db-sandsteinklettern.gipfelbuch.de"
ENCODING = "cp1250"  # Windows-1250; gipfelbuch.de uses cp1250, not iso-8859-2

# sektorid values on gipfelbuch.de for Křížový vrch
KRIZOVY_VRCH_SEKTORS = {
    "Křížový hřeben":   70,
    "Jižní věže":       71,
    "Zdoňovský oblouk": 72,
}

# Maps sektor name → the auto-named JSON file piskari-scraper.py produces
SEKTOR_TO_JSON = {
    "Křížový hřeben":   "piskovce-krizovy-hreben.json",
    "Jižní věže":       "piskovce-jizni-v-ze.json",
    "Zdoňovský oblouk": "piskovce-zdonovsky-oblouk.json",
}


# ── helpers ──────────────────────────────────────────────────────────────────

def normalize(text: str) -> str:
    """Lowercase, strip diacritics, collapse whitespace — used for name matching."""
    nfkd = unicodedata.normalize("NFKD", text)
    ascii_only = "".join(c for c in nfkd if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", ascii_only).strip().lower()


def get(url: str) -> BeautifulSoup:
    r = requests.get(url, timeout=20)
    r.encoding = ENCODING
    return BeautifulSoup(r.text, "html.parser")


# ── scraping ─────────────────────────────────────────────────────────────────

def fetch_gipfel_ids(sektorid: int) -> list[int]:
    """Return list of gipfelids listed on the sektor page."""
    soup = get(f"{BASE}/gipfel.php?sektorid={sektorid}")
    ids = []
    for a in soup.find_all("a", href=re.compile(r"weg\.php\?gipfelid=\d+")):
        m = re.search(r"gipfelid=(\d+)", a["href"])
        if m:
            ids.append(int(m.group(1)))
    # deduplicate, preserve order
    seen = set()
    unique = []
    for gid in ids:
        if gid not in seen:
            seen.add(gid)
            unique.append(gid)
    return unique


def fetch_tower(gipfelid: int) -> dict | None:
    """
    Fetch one tower page and return {czech_name, lat, lon}.
    Returns None if GPS is missing.
    """
    soup = get(f"{BASE}/weg.php?gipfelid={gipfelid}")

    # ── Czech name ──
    # h2 text is like "1 [whitespace] Erster Turm / První"
    # or just "Erster Turm" when there's no Czech equivalent
    h2 = soup.find("h2")
    if not h2:
        return None
    heading = h2.get_text(" ", strip=True)
    # strip leading number + whitespace (e.g. "1 16 Erster Turm / První 397")
    # userids appear as plain numbers inside the h2 — remove them
    heading = re.sub(r"\b\d+\b", "", heading).strip()
    if "/" in heading:
        czech_raw = heading.split("/", 1)[1].strip()
    else:
        czech_raw = heading.strip()
    # trim trailing junk numbers that sneak in
    czech_name = re.sub(r"\s+\d+\s*$", "", czech_raw).strip()

    # ── GPS ──
    text = soup.get_text(" ")
    m = re.search(
        r"Gipfelkoordinaten:\s*([\d.]+)\s*Grad\s*n[öo]rdlicher\s*Breite\s*und\s*([\d.]+)\s*Grad\s*[öo]stlicher\s*L[äa]nge",
        text,
    )
    if not m:
        return None

    return {
        "czech_name": czech_name,
        "lat": float(m.group(1)),
        "lon": float(m.group(2)),
    }


# ── GPX writer (mirrors piskari-scraper.py) ───────────────────────────────────

def gpx_escape(text: str) -> str:
    return (text
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;"))


def build_desc(tower: dict) -> str:
    lines = []
    if tower.get("area") or tower.get("sector"):
        lines.append(f"OBLAST: {tower.get('area', '')} / {tower.get('sector', '')}")
    lines.append("ZDROJ: piskari.cz + gipfelbuch.de")
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
        "creator": "piskari-scraper.py + gipfelbuch-gps.py",
        "xmlns": "http://www.topografix.com/GPX/1/1",
    })
    meta = ET.SubElement(gpx, "metadata")
    ET.SubElement(meta, "name").text = f"Piskovce — {label}"
    ET.SubElement(meta, "desc").text = (
        f"Climbing towers from piskari.cz — {label}. "
        f"GPS from gipfelbuch.de. Generated {datetime.now().strftime('%Y-%m-%d')}."
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


# ── patch logic ───────────────────────────────────────────────────────────────

def patch_json(sektor_name: str, sektorid: int, json_path: Path):
    print(f"\n📍 Sektor: {sektor_name} (gipfelbuch sektorid={sektorid})")
    towers = json.loads(json_path.read_text(encoding="utf-8"))
    norm_index = {normalize(t["name"]): t for t in towers}

    print(f"   Collecting tower list from gipfelbuch.de...")
    gipfel_ids = fetch_gipfel_ids(sektorid)
    print(f"   Found {len(gipfel_ids)} towers on gipfelbuch.de")

    matched = 0
    no_gps = 0
    no_match = []

    for i, gid in enumerate(gipfel_ids):
        time.sleep(0.3)  # be polite
        result = fetch_tower(gid)
        if result is None:
            no_gps += 1
            continue

        cz = result["czech_name"]
        key = normalize(cz)
        tower = norm_index.get(key)

        if tower is None:
            no_match.append((gid, cz))
            continue

        if tower["lat"] is None:
            tower["lat"] = result["lat"]
            tower["lon"] = result["lon"]
            matched += 1
            print(f"   [{i+1}/{len(gipfel_ids)}] {cz!r} → {result['lat']:.5f},{result['lon']:.5f}")
        else:
            print(f"   [{i+1}/{len(gipfel_ids)}] {cz!r} already has GPS, skipping")

    # save updated JSON
    json_path.write_text(json.dumps(towers, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n   JSON updated: {json_path}")
    print(f"   Matched & patched: {matched}")
    print(f"   No GPS on gipfelbuch: {no_gps}")

    if no_match:
        print(f"\n   ⚠️  {len(no_match)} towers from gipfelbuch had no name match in JSON:")
        for gid, cz in no_match:
            print(f"      gipfelid={gid}  czech_name={cz!r}")
        print("   (Check spelling differences between piskari.cz and gipfelbuch.de)")

    still_missing = sum(1 for t in towers if t["lat"] is None)
    if still_missing:
        print(f"\n   ⚠️  {still_missing} towers still have no GPS after patching:")
        for t in towers:
            if t["lat"] is None:
                print(f"      {t['name']!r}")

    # regenerate GPX
    from pathlib import Path as _P
    import re as _re
    label = sektor_name
    gpx_path = json_path.with_suffix(".gpx")
    write_gpx(towers, gpx_path, label)


# ── main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Patch Křížový vrch JSON with GPS from gipfelbuch.de"
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--sektor", metavar="NAME",
        help=f"One of: {', '.join(repr(k) for k in KRIZOVY_VRCH_SEKTORS)}"
    )
    group.add_argument(
        "--all-kv", action="store_true",
        help="Process all 3 Křížový vrch sektors"
    )
    parser.add_argument(
        "--json", metavar="FILE",
        help="Path to existing piskovce-*.json (required for --sektor; auto-detected for --all-kv)"
    )
    args = parser.parse_args()

    if args.all_kv:
        for sektor_name, sektorid in KRIZOVY_VRCH_SEKTORS.items():
            json_path = Path(SEKTOR_TO_JSON[sektor_name])
            if not json_path.exists():
                print(f"⚠️  Skipping {sektor_name}: {json_path} not found")
                continue
            patch_json(sektor_name, sektorid, json_path)
    else:
        sektor_name = args.sektor
        sektorid = KRIZOVY_VRCH_SEKTORS.get(sektor_name)
        if sektorid is None:
            print(f"Unknown sektor: {sektor_name!r}")
            print("Available:", ", ".join(KRIZOVY_VRCH_SEKTORS.keys()))
            sys.exit(1)
        if args.json:
            json_path = Path(args.json)
        else:
            json_path = Path(SEKTOR_TO_JSON[sektor_name])
        if not json_path.exists():
            print(f"JSON file not found: {json_path}")
            sys.exit(1)
        patch_json(sektor_name, sektorid, json_path)


if __name__ == "__main__":
    main()
