#!/usr/bin/env python3
"""
qa-report.py
============
Randomly samples towers from a sector JSON and validates them against
the live piskari.cz source.

Checks per tower:
  - GPS coordinates (tolerance ±0.0001°)
  - Route names     (fuzzy match, threshold 0.85)
  - Route grades    (fuzzy match after normalisation)
  - Comment counts  (exact; JSON is capped at 8 per route — noted in report)

Usage:
  python qa-report.py --sector "Himálaj"
  python qa-report.py --sector "Himálaj" --seed 42   # reproducible sample
  python qa-report.py --sector "Himálaj" --headless  # no browser window

Output:
  qa-himalaj.md  (Markdown report, same folder as JSON files)

Sample size: 5% of sector tower count, minimum 5 towers.

Requirements:
  source venv/bin/activate   (needs playwright)
"""

from __future__ import annotations
import argparse
import asyncio
import difflib
import json
import math
import random
import re
import sys
import unicodedata
from datetime import datetime
from pathlib import Path

from playwright.async_api import async_playwright, TimeoutError as PWTimeout

BASE_URL      = "https://www.piskari.cz"
GPS_TOLERANCE = 0.0001   # degrees
NAME_PASS     = 0.85     # SequenceMatcher ratio → PASS
NAME_WARN     = 0.70     # SequenceMatcher ratio → WARN (below → FAIL)
MAX_COMMENTS  = 8        # scraper cap — JSON comment lists are truncated here


# ── helpers ───────────────────────────────────────────────────────────────────

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


def normalize(text: str) -> str:
    """Lowercase + strip diacritics + collapse whitespace."""
    nfkd = unicodedata.normalize("NFKD", text or "")
    ascii_only = "".join(c for c in nfkd if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", ascii_only).strip().lower()


def fuzzy_ratio(a: str, b: str) -> float:
    return difflib.SequenceMatcher(None, normalize(a), normalize(b)).ratio()


def gps_status(delta: float) -> str:
    return "✅ PASS" if delta <= GPS_TOLERANCE else "❌ FAIL"


def name_status(ratio: float) -> str:
    if ratio >= NAME_PASS:  return "✅ PASS"
    if ratio >= NAME_WARN:  return "⚠️ WARN"
    return "❌ FAIL"


def count_status(json_n: int, live_n: int) -> str:
    if json_n == live_n:
        return "✅ PASS"
    if live_n > json_n and json_n >= MAX_COMMENTS:
        return "⚠️ WARN (JSON capped at 8)"
    if live_n > json_n:
        return "❌ FAIL (JSON missing comments)"
    return "❌ FAIL (live has fewer than JSON)"


# ── live data extraction ──────────────────────────────────────────────────────

async def fetch_tower_live(page, tower_url: str) -> dict:
    """
    Fetch tower page: returns {lat, lon, routes: [{name, grade}]}.
    lat/lon are None if GPS unavailable.
    """
    try:
        await page.goto(tower_url, wait_until="domcontentloaded", timeout=30000)
    except PWTimeout:
        print(f"  TIMEOUT: {tower_url}", file=sys.stderr)
        return {"lat": None, "lon": None, "routes": []}

    # routes
    routes = []
    try:
        route_links = await page.query_selector_all('a[href*="/cs/cesta/"]')
        for link in route_links:
            rname = (await link.inner_text()).strip()
            cell_text = await link.evaluate(
                'el => el.closest("td") ? el.closest("td").innerText : el.parentElement.innerText'
            )
            cell_text = re.sub(r'\s+', ' ', cell_text).strip()
            grade_match = re.search(
                r'\b(I{1,3}|IV|IX|X[abc]?|VI{1,3}[abc]?|V[abc]?|[IVX]+[abc])\b', cell_text
            )
            grade = grade_match.group(0) if grade_match else ""
            if rname:
                routes.append({"name": rname, "grade": grade})
    except Exception as e:
        print(f"  Route extract error: {e}", file=sys.stderr)

    # GPS
    lat, lon = None, None
    try:
        map_tab = await page.query_selector('a:has-text("mapa")')
        if map_tab:
            await map_tab.click()
            await page.wait_for_function("""
                () => {
                    try {
                        if (typeof window.map === 'undefined') return false;
                        var c = window.map.getCenter();
                        return c !== null && c !== undefined &&
                               typeof c.lat === 'function' && c.lat() !== 0;
                    } catch(e) { return false; }
                }
            """, timeout=20000)
            try:
                ok_btn = await page.wait_for_selector('button:has-text("OK")', timeout=2000)
                if ok_btn:
                    await ok_btn.click()
            except Exception:
                pass
            coords = await page.evaluate("""
                () => { var c = window.map.getCenter(); return {lat: c.lat(), lng: c.lng()}; }
            """)
            lat = coords["lat"]
            lon = coords["lng"]
    except Exception as e:
        print(f"  GPS error: {e}", file=sys.stderr)

    return {"lat": lat, "lon": lon, "routes": routes}


async def fetch_comment_count(page, route_path: str) -> int:
    """Fetch route detail page, return live comment count (excluding rating-only rows)."""
    url = BASE_URL + route_path if route_path.startswith("/") else route_path
    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=20000)
        rows = await page.query_selector_all("table.komentare tr")
        skip = {"uživatel cestu pouze hodnotil, nekomentoval."}
        count = 0
        i = 0
        while i < len(rows):
            i += 1  # skip header row
            if i < len(rows):
                body = re.sub(r'\s+', ' ', (await rows[i].inner_text()).strip())
                i += 1
                if body.lower() not in skip and body:
                    count += 1
        return count
    except Exception:
        return -1  # -1 = fetch failed


# ── comparison ────────────────────────────────────────────────────────────────

def compare_tower(json_tower: dict, live: dict, live_comment_counts: list[int]) -> dict:
    """
    Returns a result dict:
      gps:      {status, json_lat, json_lon, live_lat, live_lon, delta_lat, delta_lon}
      routes:   list of {json_name, live_name, name_status, json_grade, live_grade, grade_status}
      comments: list of {route_name, json_count, live_count, status}
      counts:   {json_routes, live_routes}
      summary:  {pass, warn, fail}
    """
    result = {"gps": {}, "routes": [], "comments": [], "counts": {}, "summary": {}}
    pass_n, warn_n, fail_n = 0, 0, 0

    def tally(status: str):
        nonlocal pass_n, warn_n, fail_n
        if "PASS" in status:   pass_n += 1
        elif "WARN" in status: warn_n += 1
        else:                  fail_n += 1

    # ── GPS ──
    jlat, jlon = json_tower.get("lat"), json_tower.get("lon")
    llat, llon = live.get("lat"),       live.get("lon")
    if jlat is None:
        gps_s = "⚠️ WARN (no GPS in JSON)"
        warn_n += 1
    elif llat is None:
        gps_s = "⚠️ WARN (GPS not loaded from live)"
        warn_n += 1
    else:
        dlat = abs(jlat - llat)
        dlon = abs(jlon - llon)
        gps_s = gps_status(max(dlat, dlon))
        tally(gps_s)
        result["gps"] = {
            "status":   gps_s,
            "json_lat": jlat, "json_lon": jlon,
            "live_lat": llat, "live_lon": llon,
            "delta_lat": round(dlat, 6),
            "delta_lon": round(dlon, 6),
        }

    if not result["gps"]:
        result["gps"] = {"status": gps_s}

    # ── routes ──
    json_routes = json_tower.get("routes", [])
    live_routes = live.get("routes", [])
    result["counts"] = {"json_routes": len(json_routes), "live_routes": len(live_routes)}

    for i in range(max(len(json_routes), len(live_routes))):
        jr = json_routes[i] if i < len(json_routes) else None
        lr = live_routes[i] if i < len(live_routes) else None

        jname  = jr["name"]  if jr else "—"
        lname  = lr["name"]  if lr else "—"
        jgrade = jr.get("grade", "") if jr else "—"
        lgrade = lr.get("grade", "") if lr else "—"

        if jr is None or lr is None:
            ns = "❌ FAIL (missing)"
            gs = "❌ FAIL (missing)"
            fail_n += 2
        else:
            nr = fuzzy_ratio(jname, lname)
            ns = name_status(nr)
            tally(ns)
            # grade: exact after normalize, else fuzzy
            if normalize(jgrade) == normalize(lgrade):
                gs = "✅ PASS"
            else:
                gr = fuzzy_ratio(jgrade, lgrade)
                gs = name_status(gr)
            tally(gs)

        result["routes"].append({
            "json_name": jname, "live_name": lname, "name_status": ns,
            "json_grade": jgrade, "live_grade": lgrade, "grade_status": gs,
        })

    # ── comment counts ──
    for i, jr in enumerate(json_routes):
        json_n = len(jr.get("comments", []))
        live_n = live_comment_counts[i] if i < len(live_comment_counts) else -1
        if live_n == -1:
            cs = "⚠️ WARN (fetch failed)"
            warn_n += 1
        else:
            cs = count_status(json_n, live_n)
            tally(cs)
        result["comments"].append({
            "route_name": jr.get("name", ""),
            "json_count": json_n,
            "live_count": live_n,
            "status": cs,
        })

    result["summary"] = {"pass": pass_n, "warn": warn_n, "fail": fail_n}
    return result


# ── report rendering ──────────────────────────────────────────────────────────

def overall_badge(results: list[dict]) -> str:
    total_fail = sum(r["summary"]["fail"] for r in results)
    total_warn = sum(r["summary"]["warn"] for r in results)
    if total_fail:   return "❌ FAIL"
    if total_warn:   return "⚠️ WARNINGS"
    return "✅ PASS"


def render_report(
    sector_name: str,
    json_path: Path,
    towers: list[dict],
    sample: list[dict],
    results: list[dict],
    seed: int | None,
) -> str:
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    pct = round(len(sample) / len(towers) * 100, 1)
    seed_note = str(seed) if seed is not None else "random (no seed)"

    lines = [
        f"# QA Report — {sector_name}",
        "",
        f"**Generated**: {now}  ",
        f"**Sector JSON**: {json_path.name}  ",
        f"**Towers in sector**: {len(towers)}  ",
        f"**Sample**: {len(sample)} towers ({pct}%)  ",
        f"**Seed**: {seed_note}  ",
        "",
        "---",
        "",
        "## Summary",
        "",
    ]

    # summary table
    total_pass = sum(r["summary"]["pass"] for r in results)
    total_warn = sum(r["summary"]["warn"] for r in results)
    total_fail = sum(r["summary"]["fail"] for r in results)

    gps_pass  = sum(1 for r in results if "PASS" in r["gps"].get("status", ""))
    gps_warn  = sum(1 for r in results if "WARN" in r["gps"].get("status", ""))
    gps_fail  = sum(1 for r in results if "FAIL" in r["gps"].get("status", ""))

    name_p = sum(1 for r in results for ro in r["routes"] if "PASS" in ro["name_status"])
    name_w = sum(1 for r in results for ro in r["routes"] if "WARN" in ro["name_status"])
    name_f = sum(1 for r in results for ro in r["routes"] if "FAIL" in ro["name_status"])

    grade_p = sum(1 for r in results for ro in r["routes"] if "PASS" in ro["grade_status"])
    grade_w = sum(1 for r in results for ro in r["routes"] if "WARN" in ro["grade_status"])
    grade_f = sum(1 for r in results for ro in r["routes"] if "FAIL" in ro["grade_status"])

    com_p = sum(1 for r in results for c in r["comments"] if "PASS" in c["status"])
    com_w = sum(1 for r in results for c in r["comments"] if "WARN" in c["status"])
    com_f = sum(1 for r in results for c in r["comments"] if "FAIL" in c["status"])

    lines += [
        "| Check | ✅ Pass | ⚠️ Warn | ❌ Fail |",
        "|-------|--------|--------|--------|",
        f"| GPS coordinates | {gps_pass} | {gps_warn} | {gps_fail} |",
        f"| Route names | {name_p} | {name_w} | {name_f} |",
        f"| Route grades | {grade_p} | {grade_w} | {grade_f} |",
        f"| Comment counts | {com_p} | {com_w} | {com_f} |",
        f"| **Total** | **{total_pass}** | **{total_warn}** | **{total_fail}** |",
        "",
        f"**Overall: {overall_badge(results)}**",
        "",
        "---",
        "",
        "## Tower results",
        "",
    ]

    for tower, result in zip(sample, results):
        s = result["summary"]
        badge = "❌" if s["fail"] else ("⚠️" if s["warn"] else "✅")
        lines += [
            f"### {badge} {tower['name']}",
            "",
            f"**URL**: {tower.get('url', '—')}  ",
            f"**JSON routes**: {result['counts']['json_routes']} | "
            f"**Live routes**: {result['counts']['live_routes']}",
            "",
        ]

        # GPS
        g = result["gps"]
        lines.append("#### GPS")
        lines.append("")
        if "json_lat" in g:
            lines += [
                "| | Lat | Lon |",
                "|-|-----|-----|",
                f"| JSON | {g['json_lat']} | {g['json_lon']} |",
                f"| Live | {g['live_lat']} | {g['live_lon']} |",
                f"| Δ | {g['delta_lat']} | {g['delta_lon']} |",
                f"| Result | {g['status']} | |",
            ]
        else:
            lines.append(g.get("status", "—"))
        lines.append("")

        # Routes
        if result["routes"]:
            lines.append("#### Routes")
            lines.append("")
            lines += [
                "| # | JSON name | Live name | Name | JSON grade | Live grade | Grade |",
                "|---|-----------|-----------|------|-----------|-----------|-------|",
            ]
            for i, ro in enumerate(result["routes"], 1):
                lines.append(
                    f"| {i} | {ro['json_name']} | {ro['live_name']} | {ro['name_status']} "
                    f"| {ro['json_grade']} | {ro['live_grade']} | {ro['grade_status']} |"
                )
            lines.append("")

        # Comment counts
        if result["comments"]:
            lines.append("#### Comment counts")
            lines.append("")
            lines += [
                "| Route | JSON | Live | Result |",
                "|-------|------|------|--------|",
            ]
            for c in result["comments"]:
                live_disp = str(c["live_count"]) if c["live_count"] >= 0 else "err"
                lines.append(
                    f"| {c['route_name']} | {c['json_count']} | {live_disp} | {c['status']} |"
                )
            lines.append("")

        lines.append("---")
        lines.append("")

    lines += [
        "## Notes",
        "",
        f"- GPS tolerance: ±{GPS_TOLERANCE}°",
        f"- Name/grade fuzzy match: PASS ≥ {NAME_PASS}, WARN ≥ {NAME_WARN}, FAIL < {NAME_WARN}",
        f"- Comment counts in JSON are capped at {MAX_COMMENTS} per route by the scraper. "
          f"A live count higher than {MAX_COMMENTS} with JSON count = {MAX_COMMENTS} is expected → ⚠️ WARN.",
    ]

    return "\n".join(lines) + "\n"


# ── main ──────────────────────────────────────────────────────────────────────

async def main() -> None:
    parser = argparse.ArgumentParser(
        description="QA report: validate sector JSON against live piskari.cz"
    )
    parser.add_argument("--sector", metavar="NAME", required=True,
                        help='Sector name, e.g. "Himálaj"')
    parser.add_argument("--seed", metavar="N", type=int, default=None,
                        help="Random seed for reproducible sample (omit for random)")
    parser.add_argument("--headless", action="store_true", default=False,
                        help="Run browser in headless mode")
    args = parser.parse_args()

    # resolve JSON
    slug = slugify(args.sector)
    json_path = Path(f"piskovce-{slug}.json")
    if not json_path.exists():
        print(f"❌ File not found: {json_path}")
        sys.exit(1)

    towers = json.loads(json_path.read_text(encoding="utf-8"))
    total = len(towers)
    sample_size = max(math.ceil(total * 0.05), 5)
    sample_size = min(sample_size, total)  # can't sample more than we have

    rng = random.Random(args.seed)
    sample = rng.sample(towers, sample_size)

    seed_note = f"seed={args.seed}" if args.seed is not None else "random"
    print(f"\n🔍 QA — {args.sector}")
    print(f"   JSON:   {json_path.name}  ({total} towers)")
    print(f"   Sample: {sample_size} towers ({seed_note})")
    print()

    results = []

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=args.headless)
        context = await browser.new_context(locale="cs-CZ")
        page = await context.new_page()
        await page.route("**/*.{png,jpg,jpeg,gif,svg,css,woff,woff2}", lambda r: r.abort())

        for idx, tower in enumerate(sample, 1):
            print(f"[{idx}/{sample_size}] {tower['name']}")

            # fetch tower page
            print(f"  → tower page ...", end=" ", flush=True)
            live = await fetch_tower_live(page, tower["url"])
            print(f"routes={len(live['routes'])}  GPS={'ok' if live['lat'] else 'n/a'}")

            # fetch comment counts per route
            live_comment_counts = []
            routes = tower.get("routes", [])
            for i, route in enumerate(routes):
                rurl = route.get("url", "")
                if rurl:
                    print(f"  → comments [{i+1}/{len(routes)}] {route['name'][:40]} ...",
                          end=" ", flush=True)
                    count = await fetch_comment_count(page, rurl)
                    live_comment_counts.append(count)
                    print(count)
                else:
                    live_comment_counts.append(-1)

            results.append(compare_tower(tower, live, live_comment_counts))

        await browser.close()

    # write report
    report_md = render_report(args.sector, json_path, towers, sample, results, args.seed)
    out_path = Path(f"qa-{slug}.md")
    out_path.write_text(report_md, encoding="utf-8")
    print(f"\n✅ Report written: {out_path}")

    # print summary
    total_fail = sum(r["summary"]["fail"] for r in results)
    total_warn = sum(r["summary"]["warn"] for r in results)
    print(f"   {overall_badge(results)}  —  "
          f"{total_fail} fail(s), {total_warn} warning(s)")


if __name__ == "__main__":
    asyncio.run(main())
