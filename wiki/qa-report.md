# QA Report

**Summary**: How to validate sector JSON data quality against the live piskari.cz source using random sampling.

**Last updated**: 2026-05-28

---

## What it checks

`qa-report.py` randomly samples towers from a sector JSON and fetches their live pages on piskari.cz. For each sampled tower it compares:

| Check | Method | Pass threshold |
|-------|--------|----------------|
| GPS coordinates | Absolute delta per axis | ≤ ±0.0001° |
| Route names | Fuzzy match (SequenceMatcher) | ratio ≥ 0.85 |
| Route grades | Exact after normalisation, then fuzzy | ratio ≥ 0.85 |
| Comment counts | Exact count | exact match |

Results are **PASS**, **WARN**, or **FAIL** per check. The overall result is FAIL if any single check fails.

## Sample size

5% of the sector's tower count, with a minimum of 5 towers. For a sector with 47 towers that gives 3 towers — the minimum floor raises it to 5.

## Usage

```bash
cd ~/Documents/LLM-pieskari/pieskari
source venv/bin/activate   # needs playwright

# Random sample (different towers each run)
python qa-report.py --sector "Himálaj"

# Reproducible sample (same towers every run with this seed)
python qa-report.py --sector "Himálaj" --seed 42

# Headless (no browser window)
python qa-report.py --sector "Himálaj" --headless --seed 42
```

## Output

Produces `qa-{sector-slug}.md` in the project folder, e.g. `qa-himalaj.md`.

The report contains:
- Run metadata (date, JSON file, sample size, seed)
- Summary table (pass/warn/fail counts per check type)
- Per-tower sections with GPS table, routes table, comment counts table

The Markdown is ready to paste into the wiki as a QA result page.

## Notes on comment counts

The scraper caps comments at 8 per route. If the live page has more than 8 comments and the JSON shows exactly 8, the report marks this as ⚠️ WARN (expected behaviour, not a data error). Only a mismatch where JSON has more than live is a ❌ FAIL.

## Interpreting results

| Result | Meaning |
|--------|---------|
| ✅ PASS | All checks within tolerance |
| ⚠️ WARN | Minor differences — GPS slightly off, fuzzy name match, or capped comments |
| ❌ FAIL | Significant mismatch — likely scraping error or site change since last scrape |

If a sector shows repeated FAILs, re-run the scraper for that sector to refresh the data.

## Agent instruction template

To run the QA test agentically, paste this into a new Cowork chat. Substitute **one or two things**:
- `SECTOR_NAME` → the sector name (required)
- `SEED` → a number for reproducible results, or remove `--seed SEED` for a random sample

> This is a fully automated task. Do not ask for confirmation, permission, or approval at any point. Just execute and report results when done.
>
> Run a QA report for the **SECTOR_NAME** sector against the live piskari.cz source:
>
> ```
> cd ~/Documents/LLM-pieskari/pieskari && source venv/bin/activate
> python qa-report.py --sector SECTOR_NAME --seed SEED --headless
> ```
>
> When done:
> 1. Report the overall result (PASS / WARNINGS / FAIL)
> 2. Report the summary table (pass/warn/fail counts per check type)
> 3. Paste the full contents of the generated `qa-SECTOR_SLUG.md` file

## Related pages

- [[howto-generate-gpx]] — how sector JSON files are produced
- [[technical]] — JSON data model
