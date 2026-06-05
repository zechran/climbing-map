# Climber Filter

**Summary**: How to generate a personal GPX map showing only towers a specific climber has visited, identified by their comments in the route data.

**Last updated**: 2026-05-28

---

## What it does

`climber-filter.py` scans all `piskovce-*.json` files in the project folder and collects every tower where a given climber has left at least one comment on any route. It then produces a new JSON + GPX containing those towers — with all their routes intact, not just the commented ones.

The result is a personal climbing map: import it into Locus Map and see exactly which towers a climber has been to.

## Usage

No virtual environment needed — the script uses Python standard library only.

```bash
cd ~/Documents/LLM-pieskari/pieskari

# Basic — produces adrspach-cervo.json + adrspach-cervo.gpx
python3 climber-filter.py --climber cervo

# Custom output filename prefix
python3 climber-filter.py --climber cervo --output my-cervo-map

# Preview matches without writing files
python3 climber-filter.py --climber cervo --dry-run

# Different source directory
python3 climber-filter.py --climber cervo --source /path/to/jsons
```

## How climbers are identified

Comments in the JSON follow the format:

```
[25.7.2013 14:49:05 cervo] Krásna dvojspára, ale občas trochu široká...
```

The script matches `[date time USERNAME]` at the start of each comment. The match is exact — `cervo` will not match `cervo2` or `supercervo`.

## Output

| File | Contents |
|------|----------|
| `adrspach-{climber}.json` | All matching towers in standard piskovce format |
| `adrspach-{climber}.gpx` | GPX ready to import into Locus Map |

The JSON uses the same structure as all other sector JSON files, so it can be used with `piskari-scraper.py --rebuild-gpx` if you need to regenerate the GPX later.

## Refreshing

Run the script again any time sector JSONs are updated with new comments:

```bash
python3 climber-filter.py --climber cervo
```

It always rebuilds from scratch, so the output stays in sync with the source data.

## Related pages

- [[howto-generate-gpx]] — how sector JSON files are produced
- [[technical]] — JSON data model and comment format
