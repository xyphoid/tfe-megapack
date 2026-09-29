#!/usr/bin/env python3
"""Render TFE noteboard files (cr-tfe/NOTES) as static HTML pages.

Usage: build_notes.py <path/to/NOTES> <output dir>

Noteboard file format (see SRC/NOTE.CC load_noteboard):
    #NOTES
    <title>~
    <from>~
    <message>~
    <unix timestamp>
    ...
    $~
"""
import html
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

# SRC/COLOR.CC color_key: n=default, e=mild emphasis, E=strong emphasis,
# K=black, lower-case = normal colour, upper-case = bright colour.
COLOR_CLASSES = {
    "e": "c-em", "E": "c-strong", "K": "c-K",
    "r": "c-r", "R": "c-R", "g": "c-g", "G": "c-G",
    "y": "c-y", "Y": "c-Y", "b": "c-b", "B": "c-B",
    "m": "c-m", "M": "c-M", "c": "c-c", "C": "c-C", "W": "c-W",
}

BOARD_BLURBS = {
    "announcements": "Official announcements from the immortals.",
    "AVATAR": "The avatar board.",
    "BUGS": "Bug reports from players.",
    "CHANGES": "Changes to the game.",
    "CODE": "Coding notes.",
    "FIXED": "Bugs that have been fixed.",
    "GENERAL": "General discussion.",
    "IDEAS": "Player ideas and suggestions.",
    "IMMORTAL": "The immortal board.",
    "information": "General game information.",
    "JOBS": "Jobs for the builders and coders.",
    "STORIES": "Stories and role play.",
    "submissions": "Player submissions.",
    "WANTED": "Wanted posters.",
}


def parse_noteboard(path):
    text = path.read_bytes().decode("latin-1")
    # Lines were stored MUD-style ("\n\r") and later CRLF-converted, so each
    # line ends up double-spaced: collapse pairs of newlines back to one.
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    if not text.startswith("#NOTES"):
        raise ValueError(f"{path}: missing #NOTES header")
    pos = len("#NOTES")
    notes = []

    def read_string():
        nonlocal pos
        while pos < len(text) and text[pos].isspace():
            pos += 1
        end = text.index("~", pos)
        s = text[pos:end]
        pos = end + 1
        return s

    def read_number():
        nonlocal pos
        m = re.compile(r"\s*(-?\d+)").match(text, pos)
        pos = m.end()
        return int(m.group(1))

    while True:
        title = read_string()
        if title.startswith("$"):
            break
        notes.append({
            "title": title.strip(),
            "from": read_string().strip(),
            "message": read_string(),
            "date": read_number(),
        })
    return notes


def undouble(s):
    return s.replace("\n\n", "\n").strip("\n")


def render_colors(s):
    """Escape text and convert @-codes into spans."""
    out, open_span = [], False
    i = 0
    while i < len(s):
        ch = s[i]
        if ch != "@" or i + 1 >= len(s):
            out.append(html.escape(ch))
            i += 1
            continue
        code = s[i + 1]
        i += 2
        if code == "@":
            out.append("@")
        elif code == "I":
            out.append("  ")
        elif code in COLOR_CLASSES:
            if open_span:
                out.append("</span>")
            out.append(f'<span class="{COLOR_CLASSES[code]}">')
            open_span = True
        elif code == "n":
            if open_span:
                out.append("</span>")
            open_span = False
        # unknown codes are dropped, as the MUD did
    if open_span:
        out.append("</span>")
    return "".join(out)


def strip_colors(s):
    return re.sub(r"@(.)", lambda m: "@" if m.group(1) == "@" else "", s)


def fmt_date(ts):
    d = datetime.fromtimestamp(ts, tz=timezone.utc)
    return d.strftime("%a %-d %B %Y, %H:%M UTC")


def iso_date(ts):
    return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


CSS = """
:root {
  --bg: #fbfaf7; --fg: #1f1d1a; --muted: #6b665e; --line: #e2ddd3;
  --card: #ffffff; --accent: #8a3b12; --side: #f3f0ea;
  --r: #a31515; --R: #d7263d; --g: #1d7a2e; --G: #2fa84f; --y: #8a6d00; --Y: #b58900;
  --b: #1f4fa3; --B: #3a78e0; --m: #7d2a8a; --M: #b04ac2; --c: #0f7680; --C: #1597a3;
  --W: #000000; --K: #555555;
}
@media (prefers-color-scheme: dark) {
  :root {
    --bg: #15171a; --fg: #e6e3dc; --muted: #9a958b; --line: #2c3036;
    --card: #1c1f23; --accent: #f0a36b; --side: #191b1f;
    --r: #d05050; --R: #ff6b6b; --g: #4caf50; --G: #7ee081; --y: #c9a227; --Y: #ffe066;
    --b: #5b8def; --B: #8ab4ff; --m: #b86bc6; --M: #e29bf0; --c: #3fb5bf; --C: #7fe3ea;
    --W: #ffffff; --K: #888888;
  }
}
* { box-sizing: border-box; }
html { scroll-behavior: smooth; }
body { margin: 0; background: var(--bg); color: var(--fg);
  font: 16px/1.5 system-ui, -apple-system, "Segoe UI", sans-serif; }
a { color: var(--accent); }
.layout { display: grid; grid-template-columns: 19rem 1fr; min-height: 100vh; }
nav.side { position: sticky; top: 0; height: 100vh; overflow-y: auto;
  background: var(--side); border-right: 1px solid var(--line); padding: 1rem; font-size: 0.9rem; }
nav.side h2 { font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.08em;
  color: var(--muted); margin: 1.2rem 0 0.4rem; }
nav.side ul { list-style: none; margin: 0; padding: 0; }
nav.side li { margin: 0; }
nav.side a { display: block; padding: 0.2rem 0.4rem; border-radius: 4px; text-decoration: none; color: var(--fg); }
nav.side a:hover { background: var(--line); }
nav.side a.current { font-weight: 600; color: var(--accent); }
nav.side .meta { display: block; font-size: 0.75rem; color: var(--muted); }
nav.side .boards a { display: inline-block; }
nav.side .boards li { display: inline; }
main { padding: 1.5rem 2rem 4rem; max-width: 60rem; }
header.page h1 { margin: 0 0 0.25rem; }
header.page p { margin: 0 0 1.5rem; color: var(--muted); }
article { background: var(--card); border: 1px solid var(--line); border-radius: 8px;
  padding: 1rem 1.25rem; margin: 0 0 1.25rem; scroll-margin-top: 1rem; }
article:target { outline: 2px solid var(--accent); }
article h2 { margin: 0 0 0.25rem; font-size: 1.15rem; }
article .byline { color: var(--muted); font-size: 0.85rem; margin-bottom: 0.75rem; }
article .byline a { color: var(--muted); }
article .num { color: var(--muted); font-weight: normal; font-size: 0.85rem; margin-right: 0.35rem; }
.body { white-space: pre-wrap; overflow-wrap: anywhere; margin: 0;
  font: 0.9rem/1.45 ui-monospace, "SFMono-Regular", Menlo, Consolas, monospace; }
.c-em { font-weight: bold; } .c-strong { font-weight: bold; text-decoration: underline; }
.c-K { color: var(--K); } .c-W { color: var(--W); font-weight: bold; }
.c-r { color: var(--r); } .c-R { color: var(--R); font-weight: bold; }
.c-g { color: var(--g); } .c-G { color: var(--G); font-weight: bold; }
.c-y { color: var(--y); } .c-Y { color: var(--Y); font-weight: bold; }
.c-b { color: var(--b); } .c-B { color: var(--B); font-weight: bold; }
.c-m { color: var(--m); } .c-M { color: var(--M); font-weight: bold; }
.c-c { color: var(--c); } .c-C { color: var(--C); font-weight: bold; }
table.index { border-collapse: collapse; width: 100%; }
table.index th, table.index td { text-align: left; padding: 0.4rem 0.6rem; border-bottom: 1px solid var(--line); }
table.index th { font-size: 0.8rem; color: var(--muted); text-transform: uppercase; letter-spacing: 0.05em; }
@media (max-width: 800px) {
  .layout { display: block; }
  nav.side { position: static; height: auto; max-height: 50vh; border-right: 0; border-bottom: 1px solid var(--line); }
  main { padding: 1rem; }
}
"""


def page(title, sidebar, content, root):
    return f"""<!doctype html>
<html lang="en-GB">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)}</title>
<link rel="stylesheet" href="{root}style.css">
</head>
<body>
<div class="layout">
<nav class="side">
{sidebar}
</nav>
<main>
{content}
</main>
</div>
</body>
</html>
"""


def boards_nav(boards, current, root):
    items = []
    for b in boards:
        cls = ' class="current"' if b["slug"] == current else ""
        items.append(f'<li><a href="{root}{b["href"]}"{cls}>{html.escape(b["name"])}</a></li>')
    return "\n".join(items)


def build(notes_dir, out_dir):
    notes_dir, out_dir = Path(notes_dir), Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "clans").mkdir(exist_ok=True)
    (out_dir / "style.css").write_text(CSS.lstrip())
    (out_dir / ".nojekyll").write_text("")

    boards = []
    for f in sorted(p for p in notes_dir.iterdir() if p.is_file()):
        boards.append({"name": f.name, "slug": f.name.lower(), "href": f"{f.name.lower()}.html",
                       "path": f, "clan": False})
    clan_dir = notes_dir / "CLANS"
    clans = []
    if clan_dir.is_dir():
        for f in sorted(p for p in clan_dir.iterdir() if p.is_file()):
            clans.append({"name": f.name, "slug": "clan-" + f.name.lower(),
                          "href": f"clans/{f.name.lower()}.html", "path": f, "clan": True})
    for b in boards + clans:
        b["notes"] = parse_noteboard(b["path"])

    def sidebar(current, root, posts_html=""):
        cur = ' class="current"' if current == "index" else ""
        s = f'<a href="{root}index.html"{cur}><strong>TFE noteboards</strong></a>\n'
        s += f'<h2>Boards</h2>\n<ul class="boards">\n{boards_nav(boards, current, root)}\n</ul>\n'
        s += f'<h2>Clan boards</h2>\n<ul class="boards">\n{boards_nav(clans, current, root)}\n</ul>\n'
        return s + posts_html

    for b in boards + clans:
        root = "../" if b["clan"] else ""
        seen, posts, links = {}, [], []
        for n, note in enumerate(b["notes"], 1):
            anchor = f"t{note['date']}"
            seen[anchor] = seen.get(anchor, 0) + 1
            if seen[anchor] > 1:
                anchor += f"-{seen[anchor]}"
            title = strip_colors(note["title"]) or "(no subject)"
            author = strip_colors(note["from"])
            date = fmt_date(note["date"])
            links.append(
                f'<li><a href="#{anchor}">{html.escape(title)}'
                f'<span class="meta">{html.escape(author)} &middot; {html.escape(date[4:-4])}</span></a></li>')
            posts.append(f"""<article id="{anchor}">
<h2><span class="num">#{n}</span>{render_colors(note["title"]) or "(no subject)"}</h2>
<div class="byline">by <strong>{html.escape(author)}</strong> &middot; <a href="#{anchor}"><time datetime="{iso_date(note["date"])}">{date}</time></a></div>
<pre class="body">{render_colors(undouble(note["message"]))}</pre>
</article>""")
        label = f"{b['name']} clan board" if b["clan"] else f"{b['name']} board"
        posts_html = f"<h2>Posts ({len(posts)})</h2>\n<ul>\n" + "\n".join(links) + "\n</ul>" if posts else ""
        blurb = BOARD_BLURBS.get(b["name"], "")
        content = (f'<header class="page"><h1>{html.escape(label)}</h1>'
                   f'<p>{html.escape(blurb)} {len(posts)} post{"s" if len(posts) != 1 else ""}.</p></header>\n'
                   + ("\n".join(posts) if posts else "<p>No posts on this board.</p>"))
        (out_dir / b["href"]).write_text(page(f"{label} · TFE", sidebar(b["slug"], root, posts_html), content, root))

    rows = []
    for b in boards + clans:
        dates = [n["date"] for n in b["notes"]]
        span = (f"{fmt_date(min(dates))[4:-11]} – {fmt_date(max(dates))[4:-11]}" if dates else "–")
        kind = "Clan" if b["clan"] else "Board"
        rows.append(f'<tr><td><a href="{b["href"]}">{html.escape(b["name"])}</a></td><td>{kind}</td>'
                    f'<td>{len(b["notes"])}</td><td>{span}</td></tr>')
    content = ('<header class="page"><h1>The Forest\'s Edge noteboards</h1>'
               '<p>An archive of the in-game noteboards from the cr-tfe snapshot. Dates are shown in UTC.</p></header>\n'
               '<table class="index"><thead><tr><th>Board</th><th>Type</th><th>Posts</th><th>Date range</th></tr></thead>\n<tbody>\n'
               + "\n".join(rows) + "\n</tbody></table>")
    (out_dir / "index.html").write_text(page("TFE noteboards", sidebar("index", ""), content, ""))


if __name__ == "__main__":
    build(sys.argv[1], sys.argv[2])
