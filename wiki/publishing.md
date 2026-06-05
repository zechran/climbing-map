# Publishing

**Summary**: How the wiki is built and published to GitHub Pages as a public website.

**Last updated**: 2026-06-04

---

## Overview

Wiki content is authored in Markdown (`wiki/`) and published as HTML (`docs/`). A single script handles the full pipeline — build, commit, and push.

```
wiki/*.md  →  build-wiki.py  →  docs/*.html  →  git push  →  GitHub Pages
```

The public site updates automatically within ~1 minute of every push.

---

## Publishing workflow

Claude runs this after every wiki change:

```bash
./publish.sh "descriptive commit message"
```

This does three things in sequence:
1. Runs `python3 build-wiki.py` — converts all `wiki/*.md` to `docs/*.html`
2. Runs `git add . && git commit -m "message"` — commits all changes
3. Runs `git push` — pushes to GitHub, triggering Pages deployment

---

## Manual run

If you need to publish manually from Terminal:

```bash
cd ~/Documents/LLM-pieskari/pieskari
./publish.sh "your commit message"
```

Or step by step:

```bash
python3 build-wiki.py
git add .
git commit -m "your message"
git push
```

---

## Infrastructure

| Component | Detail |
|-----------|--------|
| Repository | `github.com/YOUR_USERNAME/climbing-map` (public) |
| Hosting | GitHub Pages |
| Source folder | `docs/` (on `main` branch) |
| Public URL | `https://YOUR_USERNAME.github.io/climbing-map/` |
| Custom domain | TBD |

---

## Folder roles

| Folder | Role | Edited by |
|--------|------|-----------|
| `wiki/` | Authoring format (Markdown) | Claude |
| `docs/` | Published output (HTML) | `build-wiki.py` — never edit directly |

---

## Custom domain setup

When you're ready to point a domain at the wiki:

1. Go to **GitHub → Settings → Pages → Custom domain**
2. Enter your domain (e.g. `wiki.yourdomain.com`)
3. Add a `CNAME` DNS record at your domain registrar pointing to `YOUR_USERNAME.github.io`
4. Wait for DNS propagation (up to 24h)
5. Tick **Enforce HTTPS** once the certificate is issued

---

## Related pages

- [[howto-generate-gpx]] — workflow for generating GPX files
- [[qa-report]] — automated data quality validation
