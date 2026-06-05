#!/usr/bin/env python3
"""
cervo-filter.py
===============
Filters towers from piskovce-*.json files by climber username and produces
a new JSON + GPX containing only towers where that climber has left at least
one comment on any route.

All routes of a matching tower are included (not just the commented ones),
so the GPX shows the full tower profile in Locus Map.

Usage:
  python cervo-filter.py --climber cervo
  python cervo-filter.py --climber cervo --output my-cervo
  python cervo-filter.py --climber cervo --source /path/to/jsons
  python cervo-filter.py --climber cervo --dry-run

Output (default, with --climber cervo):
  adrspach-cervo.json
  adrspach-cervo.gpx

Comment format expected in JSON:
  "[25.7.2013 14:49:05 cervo] Krásna dvojspára..."

Requirements:
  No external dependencies — stdlib only.
"""

from __future__ import annotations
import argparse
import json
import re
import sys
import xml.dom.minidom
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path


# ── GPX helpers ───────────────────────────────────────────────────────────────

def gpx_escape(text: str) -> str:
    return (text or "") \
        .replace("&", "&amp;") \
        .replace("<", "&lt;") \
        .replace(">", "&gt;") \
        .replace('"', "&quot;")


def write_gpx(towers: list[dict], output_path: Path, label: str) -> None:
    gpx = ET.Element("gpx", {
        "version": "1.1",
        "creator": "cervo-filter",
        "xmlns": "http://www.topografix.com/GPX/1/1",
    })
    meta = ET.SubElement(gpx, "metadata")
    ET.SubElement(meta, "name").text = label
    ET.SubElement(meta, "time").text = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")

    skipped = 0
    for tower in towers:
        lat, lon = tower.get("lat"), tower.get("lon")
        if lat is None or lon is None:
            skipped += 1
            continue
        wpt = ET.SubElement(gpx, "wpt", {"lat": str(lat), "lon": str(lon)})
        ET.SubElement(wpt, "name").text = tower["name"]

        lines = []
        for r in tower.get("routes", []):
            grade = r.get("grade", "")
            name  = r.get("name", "")
            lines.append(f"{name} ({grade})" if grade else name)
            if r.get("popis"):
                lines.append(r["popis"])
            if r.get("charakter"):
                lines.append(f"Charakter: {r['charakter']}")
            for c in r.get("comments", []):
                lines.append(f"  {c}")
            lines.append("")
        ET.SubElement(wpt, "desc").text = gpx_escape("\n".join(lines).strip())

    rough = ET.tostring(gpx, encoding="unicode")
    pretty = xml.dom.minidom.parseString(rough).toprettyxml(indent="  ")
    pretty = "\n".join(pretty.split("\n")[1:])  # strip XML declaration line
    with open(output_path, "wb") as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n'.encode("utf-8"))
        f.write(pretty.encode("utf-8"))

    total = len(towers)
    with_gps = total - skipped
    print(f"✅ GPX written: {output_path}")
    print(f"   {with_gps}/{total} towers have GPS  ({skipped} skipped — no coordinates)")


# ── main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Filter piskovce-*.json files by climber username → JSON + GPX"
    )
    parser.add_argument(
        "--climber", metavar="NAME", required=True,
        help='Climber username to filter by (e.g. "cervo")'
    )
    parser.add_argument(
        "--output", metavar="PREFIX",
        help='Output file prefix (default: adrspach-{climber}). '
             'Produces {prefix}.json and {prefix}.gpx'
    )
    parser.add_argument(
        "--source", metavar="DIR", default=".",
        help="Directory containing piskovce-*.json files (default: current directory)"
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Print matching towers without writing any files"
    )
    args = parser.parse_args()

    source_dir = Path(args.source)
    source_files = sorted(source_dir.glob("piskovce-*.json"))
    if not source_files:
        print(f"❌ No piskovce-*.json files found in: {source_dir}")
        sys.exit(1)

    climber = args.climber.strip()
    pattern = re.compile(r'\[[\d.:\s]+' + re.escape(climber) + r'\]')

    # ── scan all source files ─────────────────────────────────────────────────
    matched: list[dict] = []
    stats: dict[str, int] = {}

    for fpath in source_files:
        data = json.loads(fpath.read_text(encoding="utf-8"))
        sector_matches = 0
        for tower in data:
            for route in tower.get("routes", []):
                if any(pattern.search(c) for c in route.get("comments", [])):
                    matched.append(tower)
                    sector_matches += 1
                    break
        if sector_matches:
            stats[fpath.name] = sector_matches

    print(f"\nClimber '{climber}' found in {len(matched)} towers across {len(stats)} sectors:\n")
    for fname, count in stats.items():
        sector_label = fname.replace("piskovce-", "").replace(".json", "").replace("-", " ").title()
        print(f"  {sector_label:<30} {count} tower(s)")
    print(f"\n  Total: {len(matched)} towers\n")

    if args.dry_run:
        print("Dry run — no files written.")
        return

    if not matched:
        print("No matching towers found. No files written.")
        return

    # ── write output ──────────────────────────────────────────────────────────
    prefix = args.output or f"adrspach-{climber}"
    json_out = Path(prefix + ".json")
    gpx_out  = Path(prefix + ".gpx")

    json_out.write_text(json.dumps(matched, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"✅ JSON written: {json_out}  ({len(matched)} towers)")

    label = f"{climber} — Adršpach & Křížový vrch"
    write_gpx(matched, gpx_out, label)


if __name__ == "__main__":
    main()
