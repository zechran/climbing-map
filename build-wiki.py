#!/usr/bin/env python3
"""
build-wiki.py
=============
Converts wiki/*.md → wiki-html/*.html

Handles:
  - [[wiki-links]]  → working <a href> between pages
  - Markdown tables, code blocks, headings, lists, blockquotes
  - Sidebar built from index.md structure
  - Dark theme via shared style.css
  - log.md excluded

Usage:
    python3 build-wiki.py

Requirements:
    pip3 install markdown --break-system-packages
    (or: source venv/bin/activate && pip install markdown)
"""

from __future__ import annotations
import re
import sys
from pathlib import Path

try:
    import markdown
    from markdown.extensions.tables import TableExtension
    from markdown.extensions.fenced_code import FencedCodeExtension
except ImportError:
    print("❌  Missing dependency: pip3 install markdown --break-system-packages")
    sys.exit(1)

WIKI_DIR  = Path("wiki")
OUT_DIR   = Path("docs")
EXCLUDE   = {"log.md"}
SITE_NAME = "Pieskari Wiki"


# ── slug / display helpers ────────────────────────────────────────────────────

def slug_to_display(slug: str) -> str:
    """'krizovy-vrch' → 'Krizovy Vrch' (fallback when no H1 found)."""
    return slug.replace("-", " ").title()


def load_titles(wiki_dir: Path, exclude: set) -> dict[str, str]:
    """Map slug → H1 title for every included page."""
    titles = {}
    for f in wiki_dir.glob("*.md"):
        if f.name in exclude:
            continue
        slug = f.stem
        text = f.read_text(encoding="utf-8")
        m = re.search(r"^#\s+(.+)", text, re.MULTILINE)
        titles[slug] = m.group(1).strip() if m else slug_to_display(slug)
    return titles


# ── [[wiki-link]] preprocessing ───────────────────────────────────────────────

def preprocess_wiki_links(text: str, titles: dict[str, str]) -> str:
    """
    Replace [[slug]] with a standard markdown link before conversion.
    Uses the page's H1 title as display text if known.
    """
    def replace(m):
        slug = m.group(1).strip()
        label = titles.get(slug, slug_to_display(slug))
        return f"[{label}]({slug}.html)"

    return re.sub(r'\[\[([^\]]+)\]\]', replace, text)


# ── sidebar parsing ───────────────────────────────────────────────────────────

def parse_sidebar(index_text: str, titles: dict[str, str]) -> list[dict]:
    """
    Parse index.md into a flat list of sidebar items:
      {"type": "section"|"subsection"|"link", "label": str, "slug": str, "indent": int}
    """
    items = []
    current_h2_indent = 0  # base indent under current h2
    in_spatial = False      # h3 subsections only appear in spatial section

    for line in index_text.splitlines():
        # h2 section header
        if re.match(r'^## ', line):
            label = re.sub(r'^## ', '', line).strip()
            items.append({"type": "section", "label": label})
            in_spatial = "spatial" in label.lower() or "data model" in label.lower()
            current_h2_indent = 0
            continue

        # h3 subsection (only used in spatial section)
        if re.match(r'^### ', line):
            label = re.sub(r'^### ', '', line).strip()
            items.append({"type": "subsection", "label": label})
            current_h2_indent = 1
            continue

        # any bullet with [[slug]]
        m = re.match(r'^(\s*)-\s+\[\[([^\]]+)\]\]', line)
        if m:
            spaces = len(m.group(1))
            slug = m.group(2).strip()
            label = titles.get(slug, slug_to_display(slug))
            # indent: 0 = direct under section, 1 = under subsection, 2 = deeper
            if in_spatial:
                indent = min(current_h2_indent + spaces // 2, 2)
            else:
                indent = 0
            items.append({"type": "link", "slug": slug, "label": label, "indent": indent})

    return items


def build_sidebar_html(items: list[dict], active_slug: str) -> str:
    parts = []
    for item in items:
        if item["type"] == "section":
            parts.append(f'<div class="nav-section">{item["label"]}</div>')
        elif item["type"] == "subsection":
            parts.append(f'<div class="nav-subsection">{item["label"]}</div>')
        elif item["type"] == "link":
            slug   = item["slug"]
            label  = item["label"]
            indent = item.get("indent", 0)
            active = ' active' if slug == active_slug else ''
            ind_cls = f' indent-{indent}' if indent else ''
            parts.append(
                f'<a href="{slug}.html" class="nav-link{active}{ind_cls}">{label}</a>'
            )
    return "\n".join(parts)


# ── markdown → HTML ───────────────────────────────────────────────────────────

MD = markdown.Markdown(extensions=[
    TableExtension(),
    FencedCodeExtension(),
    "nl2br",
    "smarty",
])


def convert(text: str) -> str:
    MD.reset()
    return MD.convert(text)


# ── HTML template ─────────────────────────────────────────────────────────────

HTML_TEMPLATE = """\
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title} — {site}</title>
  <link rel="stylesheet" href="style.css">
</head>
<body>
  <div class="layout">
    <nav class="sidebar">
      <div class="sidebar-title">
        <a href="index.html">🧗 {site}</a>
      </div>
      {sidebar}
    </nav>
    <main class="content">
      <article>
        {content}
      </article>
    </main>
  </div>
</body>
</html>
"""


def build_page(title: str, content_html: str, sidebar_html: str) -> str:
    return HTML_TEMPLATE.format(
        title=title,
        site=SITE_NAME,
        sidebar=sidebar_html,
        content=content_html,
    )


# ── CSS ───────────────────────────────────────────────────────────────────────

CSS = """\
/* Pieskari Wiki — dark theme */
:root {
  --bg:           #0d1117;
  --surface:      #161b22;
  --border:       #30363d;
  --text:         #e6edf3;
  --text-muted:   #8b949e;
  --link:         #58a6ff;
  --link-hover:   #79c0ff;
  --code-bg:      #1f2428;
  --accent:       #388bfd;
  --sidebar-w:    270px;
}

*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

body {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", system-ui, sans-serif;
  background: var(--bg);
  color: var(--text);
  line-height: 1.65;
  font-size: 15px;
}

/* ── layout ── */
.layout { display: flex; min-height: 100vh; }

/* ── sidebar ── */
.sidebar {
  width: var(--sidebar-w);
  background: var(--bg);
  border-right: 1px solid var(--border);
  position: fixed;
  top: 0; bottom: 0;
  overflow-y: auto;
  padding-bottom: 2rem;
  flex-shrink: 0;
}

.sidebar-title {
  font-size: 0.95rem;
  font-weight: 600;
  padding: 1.25rem 1.25rem 1.1rem;
  border-bottom: 1px solid var(--border);
  margin-bottom: 0.5rem;
  position: sticky;
  top: 0;
  background: var(--bg);
  z-index: 1;
}

.sidebar-title a { color: var(--text); text-decoration: none; }

.nav-section {
  font-size: 0.68rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  color: var(--text-muted);
  padding: 1rem 1.25rem 0.3rem;
}

.nav-subsection {
  font-size: 0.78rem;
  color: var(--text-muted);
  padding: 0.5rem 1.25rem 0.15rem;
  font-style: italic;
}

.nav-link {
  display: block;
  padding: 0.28rem 1.25rem;
  color: var(--text-muted);
  text-decoration: none;
  font-size: 0.85rem;
  border-left: 2px solid transparent;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  transition: color 0.12s, background 0.12s;
}

.nav-link:hover {
  color: var(--text);
  background: rgba(255,255,255,0.04);
}

.nav-link.active {
  color: var(--link);
  border-left-color: var(--link);
  background: rgba(88,166,255,0.08);
}

.nav-link.indent-1 { padding-left: 2rem; }
.nav-link.indent-2 { padding-left: 2.75rem; }

/* ── content ── */
.content {
  margin-left: var(--sidebar-w);
  flex: 1;
  padding: 2.5rem 3.5rem;
  max-width: calc(var(--sidebar-w) + 820px);
}

/* ── typography ── */
article h1 {
  font-size: 1.7rem;
  font-weight: 700;
  margin-bottom: 0.75rem;
  padding-bottom: 0.6rem;
  border-bottom: 1px solid var(--border);
  line-height: 1.3;
}

article h2 {
  font-size: 1.2rem;
  font-weight: 600;
  margin: 2.25rem 0 0.75rem;
  padding-bottom: 0.35rem;
  border-bottom: 1px solid var(--border);
}

article h3 {
  font-size: 1rem;
  font-weight: 600;
  margin: 1.75rem 0 0.5rem;
  color: var(--text);
}

article h4 {
  font-size: 0.9rem;
  font-weight: 600;
  margin: 1.25rem 0 0.4rem;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

article p { margin-bottom: 0.875rem; }

article a { color: var(--link); text-decoration: none; }
article a:hover { color: var(--link-hover); text-decoration: underline; }

article ul, article ol {
  margin: 0.4rem 0 0.875rem 1.4rem;
}

article li { margin-bottom: 0.3rem; }
article li > ul { margin-top: 0.25rem; }

article strong { font-weight: 600; }
article em { font-style: italic; color: var(--text-muted); }

/* ── code ── */
article code {
  background: var(--code-bg);
  padding: 0.15em 0.4em;
  border-radius: 4px;
  font-size: 0.85em;
  font-family: "SF Mono", "Fira Code", Consolas, "Liberation Mono", monospace;
  color: #e6edf3;
  border: 1px solid var(--border);
}

article pre {
  background: var(--code-bg);
  border: 1px solid var(--border);
  border-radius: 6px;
  padding: 1rem 1.25rem;
  overflow-x: auto;
  margin: 1rem 0;
  line-height: 1.55;
}

article pre code {
  background: none;
  padding: 0;
  border: none;
  font-size: 0.83em;
}

/* ── tables ── */
article table {
  width: 100%;
  border-collapse: collapse;
  margin: 1rem 0;
  font-size: 0.875rem;
}

article th {
  background: var(--surface);
  padding: 0.55rem 0.875rem;
  text-align: left;
  border: 1px solid var(--border);
  font-weight: 600;
  color: var(--text);
}

article td {
  padding: 0.45rem 0.875rem;
  border: 1px solid var(--border);
  vertical-align: top;
}

article tr:nth-child(even) td {
  background: rgba(255,255,255,0.025);
}

/* ── misc ── */
article hr {
  border: none;
  border-top: 1px solid var(--border);
  margin: 2rem 0;
}

article blockquote {
  border-left: 3px solid var(--accent);
  padding: 0.6rem 1rem;
  margin: 1rem 0;
  color: var(--text-muted);
  background: rgba(56,139,253,0.06);
  border-radius: 0 4px 4px 0;
  font-size: 0.92rem;
}

article blockquote p { margin: 0; }
article blockquote p + p { margin-top: 0.4rem; }

/* ── responsive ── */
@media (max-width: 800px) {
  .sidebar { display: none; }
  .content { margin-left: 0; padding: 1.5rem; }
}
"""


# ── main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    if not WIKI_DIR.exists():
        print(f"❌  Wiki directory not found: {WIKI_DIR}")
        sys.exit(1)

    OUT_DIR.mkdir(exist_ok=True)

    # write CSS
    css_path = OUT_DIR / "style.css"
    css_path.write_text(CSS, encoding="utf-8")
    print(f"  CSS  → {css_path}")

    # load all page titles first (needed for link labels)
    titles = load_titles(WIKI_DIR, EXCLUDE)

    # build sidebar structure from index.md
    index_text = (WIKI_DIR / "index.md").read_text(encoding="utf-8")
    sidebar_items = parse_sidebar(index_text, titles)

    # convert each .md file
    md_files = sorted(
        f for f in WIKI_DIR.glob("*.md")
        if f.name not in EXCLUDE
    )

    print(f"\nConverting {len(md_files)} pages...\n")

    for md_file in md_files:
        slug = md_file.stem
        text = md_file.read_text(encoding="utf-8")

        # preprocess [[wiki-links]]
        text = preprocess_wiki_links(text, titles)

        # convert to HTML
        content_html = convert(text)

        # page title
        title = titles.get(slug, slug_to_display(slug))

        # sidebar with active page highlighted
        sidebar_html = build_sidebar_html(sidebar_items, slug)

        # full page
        page_html = build_page(title, content_html, sidebar_html)

        out_path = OUT_DIR / f"{slug}.html"
        out_path.write_text(page_html, encoding="utf-8")
        print(f"  {md_file.name:<40} → {out_path.name}")

    print(f"\n✅  Built {len(md_files)} pages in {OUT_DIR}/")
    print(f"   Open: {OUT_DIR}/index.html")


if __name__ == "__main__":
    main()
