# How to Generate a GPX File

**Summary**: Step-by-step guide for generating climbing map GPX files from piskari.cz. Two methods: manual terminal and agent-based (parallel sectors).

**Last updated**: 2026-05-25

---

## Before you start — one-time setup

You only need to do this once. If you've done it before, skip to Method 1 or Method 2.

**Requirements**:
- Python 3.8+ installed on your Mac
- The `pieskari` project folder at `~/Documents/LLM-pieskari/pieskari/`

**Setup**:
```bash
cd ~/Documents/LLM-pieskari/pieskari
python3 -m venv venv
source venv/bin/activate
pip install playwright
python -m playwright install chromium
```

You should see `(venv)` appear in your terminal prompt. That means you're ready.

---

## What the process produces

For each sector you run, you get two files in the project folder:

| File | Purpose |
|------|---------|
| `piskovce-[sector].gpx` | Import this into Locus Map |
| `piskovce-[sector].json` | Intermediate data store — keep this, never delete it |

The JSON is the source of truth. The GPX is always regenerated from it.

---

## Method 1 — Manual (terminal, one sector at a time)

Best for: running a single sector, troubleshooting, or when you want full control.

### Step 1 — Activate the environment

Open Terminal, then:

```bash
cd ~/Documents/LLM-pieskari/pieskari
source venv/bin/activate
```

You'll see `(venv)` in the prompt. Do this every time you open a new terminal.

### Step 2 — Scrape GPS and routes

Replace `"Himálaj"` with the sector you want. A browser window will open automatically — don't close it.

```bash
python piskari-scraper.py --sector "Himálaj"
```

You'll see progress printed in the terminal:
```
📍 Collecting towers in: Himálaj
   Found 47 towers
[1/47] Abakus → 50.61823, 16.09541
[2/47] Adamec → 50.61901, 16.09483
...
✅ GPX written: piskovce-himalaj.gpx
```

This takes roughly 5–15 minutes depending on sector size.

### Step 3 — Fill GPS gaps via mapy.com API

Some towers won't have GPS after Step 2. This script queries the mapy.com API and fills in coordinates for towers where it finds a confident match. It only touches towers still missing GPS, so it is safe to always run.

```bash
python mapycz-gps.py --json piskovce-himalaj.json
```

The script reads your API key from the `MAPYCZ_API_KEY` environment variable if set, otherwise it prompts you interactively. To avoid the prompt (especially useful when running multiple sectors), set the variable once at the start of your terminal session:

```bash
export MAPYCZ_API_KEY="your-key-here"
```

The key lives only in the shell session's memory — it is never written to any file and disappears when you close the terminal.

### Step 4 (optional) — Handle towers still missing GPS

After Step 3, check if any towers are still missing GPS. If so, add them manually:

1. Open `piskovce-himalaj.json` in any text editor
2. Search for `"lat": null`
3. Look up the tower on mapy.cz, copy the coordinates
4. Replace `"lat": null, "lon": null` with `"lat": 50.12345, "lon": 16.12345`

### Step 5 — Enrich with route descriptions and comments

This visits every individual route page to add the full description, climbing character, and climber comments. Takes longer (~30–60 min for a large sector).

```bash
python piskari-scraper.py --add-comments piskovce-himalaj.json
```

Progress:
```
Fetching details for 142 routes across 47 towers...
  [1/142] Abakus — Stará cesta   (2 comments)
  [2/142] Abakus — Nová cesta    (0 comments)
  ...
✅ GPX written: piskovce-himalaj.gpx
```

### Step 6 (optional) — Rebuild GPX after manual GPS edits

After Step 5 completes, you may find some towers still have no GPS when you check the GPX in Locus Map. Open the JSON, fix the coordinates manually, then rebuild the GPX without re-fetching comments from the web:

```bash
python piskari-scraper.py --rebuild-gpx "Himálaj"
```

This reads the JSON as-is and writes a fresh GPX — no browser, no web access, no comments re-fetch.

### Step 7 — Import into Locus Map

1. Transfer `piskovce-himalaj.gpx` to your phone (AirDrop, cable, or shared folder)
2. Open Locus Map → My Library → Import
3. Select the GPX file
4. When prompted for a folder, create one named after the sector (e.g. "Himálaj")
5. Done — tap any pin on the map to see routes and comments

**Note**: If you did Step 6 (manual GPS fix), re-import the updated GPX to replace the previous one.

---

## Method 2 — Agent-based (parallel sectors)

Best for: generating multiple sectors at once without sitting at the terminal. Each Cowork agent handles one sector independently.

### How it works

Open a new Cowork chat for each sector. Give each agent a single instruction. They run in parallel — while one scrapes Himálaj, another scrapes Jezerka, etc.

### Agent instruction template

Paste this into a new Cowork chat. You need to substitute **two things**:
- `YOUR_KEY` → your mapy.com API key
- `SECTOR_NAME` → the sector name from column 3 of the table below

> This is a fully automated task. Do not ask for confirmation, permission, or approval at any point — not before running commands, not between steps, not at the end. Just execute everything and report results only when fully done or on error.
>
> Generate a GPX file for the **SECTOR_NAME** sector of Adršpach by running these commands in order in the terminal:
>
> ```
> cd ~/Documents/LLM-pieskari/pieskari && source venv/bin/activate && export MAPYCZ_API_KEY="YOUR_KEY"
> python piskari-scraper.py --sector SECTOR_NAME
> python mapycz-gps.py --sector SECTOR_NAME
> python piskari-scraper.py --add-comments SECTOR_NAME
> ```
>
> When done, report: how many towers total, how many have GPS, and the name of the GPX file created.
>
> If I later tell you I updated the JSON manually, run without asking: `python piskari-scraper.py --rebuild-gpx SECTOR_NAME`

### All 11 Adršpach sectors — one instruction per agent

Copy the template above, substitute `YOUR_KEY` and `SECTOR_NAME`, and start a separate chat for each. The JSON filename is derived automatically by the scripts — listed here for reference only:

| Agent    | Sector                    | SECTOR_NAME                   | JSON_FILE                                 |
| -------- | ------------------------- | ----------------------------- | ----------------------------------------- |
| Agent 1  | ✅ Done                    | `"Milenecká hora"`            | `piskovce-milenecka-hora.json`            |
| Agent 2  | ✅ Done                    | `"Himálaj"`                   | `piskovce-himalaj.json`                   |
| Agent 3  | ✅ Done                    | `"Jezerka"`                   | `piskovce-jezerka.json`                   |
| Agent 4  | ✅ Done                    | `"Království"`                | `piskovce-kralovstvi.json`                |
| Agent 5  | ✅ Done                    | `"Město"`                     | `piskovce-mesto.json`                     |
| Agent 6  | ✅ Done                    | `"Ostrov"`                    | `piskovce-ostrov.json`                    |
| Agent 7  | ✅ Done                    | `"Panoptikum"`                | `piskovce-panoptikum.json`                |
| Agent 8  | ✅ Done                    | `"Podhradí"`                  | `piskovce-podhrati.json`                  |
| Agent 9  | ✅ Done                    | `"Rokle nad Spáleným mlýnem"` | `piskovce-rokle-nad-spalenym-mlynem.json` |
| Agent 10 | ✅ Done                    | `"Vstupní obvod"`             | `piskovce-vstupni-obvod.json`             |
| Agent 11 | ✅ Done                    | `"Za pískovnou"`              | `piskovce-za-piskovnou.json`              |

### After all agents finish

Each agent produces a GPX file. Import each one into Locus Map into its own folder:

```
Locus Map / My Library /
  ├── Himálaj/          ← piskovce-himalaj.gpx  ✅
  ├── Jezerka/          ← piskovce-jezerka.gpx  ✅
  ├── Království/       ← piskovce-kralovstvi.gpx  ✅
  ├── Město/            ← piskovce-mesto.gpx  ✅
  ├── Milenecká hora/   ← piskovce-milenecka-hora.gpx  ✅
  ├── Ostrov/           ← piskovce-ostrov.gpx  ✅
  ├── Panoptikum/       ← piskovce-panoptikum.gpx  ✅
  ├── Podhradí/         ← piskovce-podhrati.gpx  ✅
  ├── Rokle/            ← piskovce-rokle-nad-spalenim-mlynem.gpx  ✅
  ├── Vstupní obvod/    ← piskovce-vstupni-obvod.gpx  ✅
  └── Za pískovnou/     ← piskovce-za-piskovnou.gpx  ✅
```

---

## Refreshing an existing sector

When piskari.cz has significant new comments (every few months):

```bash
cd ~/Documents/LLM-pieskari/pieskari
source venv/bin/activate

# Option A — refresh comments only (fast, keeps existing GPS)
python piskari-scraper.py --add-comments piskovce-himalaj.json

# Option B — full re-scrape from scratch (slower, picks up new towers too)
python piskari-scraper.py --sector "Himálaj"
python piskari-scraper.py --add-comments piskovce-himalaj.json
```

Then re-import the updated GPX into Locus Map (replace the existing file in the folder).

---

## Troubleshooting

**`(venv)` not showing in prompt**
Run `source venv/bin/activate` again. You need to do this every time you open a new terminal.

**`python: command not found`**
Use `python3` instead of `python` if you get this error.

**Tower shows → NO GPS**
The tower has no map tab on piskari.cz (usually a newer tower with a 3xxx ID). First run `mapycz-gps.py` (Step 3) — it may find a match. If still missing, add coordinates manually — see Step 4 above.

**Browser window opens but nothing happens**
piskari.cz may be slow or temporarily down. Wait 30 seconds and try again. If it keeps failing, run with `--headless` removed (it's off by default) and watch what the browser does.

**GPX imports into Locus Map but no pins appear**
Check that the GPX has at least one valid `<wpt>` element with lat/lon. Open the file in a text editor and look for `<wpt lat=`. If it's empty, check the terminal output for errors during scraping.

---

---

## Note: Křížový vrch workflow differs

Křížový vrch requires an extra GPS step because piskari.cz provides no GPS for that area. Instead of Step 2 above, GPS is sourced from `gipfelbuch-gps.py` first, then `mapycz-gps.py` as fallback. See [[krizovy-vrch]] for the full workflow.

---

## Related pages

- [[technical]] — Full technical reference: data model, selectors, GPS extraction method
- [[product-spec]] — Why this product exists and what it's trying to do
- [[krizovy-vrch]] — Křížový vrch workflow (different GPS pipeline)
- [[adrspach]] — Adršpach area and its 11 sectors
