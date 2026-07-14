#!/usr/bin/env python3
"""Generate the neofetch-style README card as themed SVGs.

Emits readme-dark.svg (TokyoNight Storm) and readme-light.svg (TokyoNight Day).
Everything is self-contained: Fira Code subset embedded as a data-URI woff2,
no external fetches (GitHub camo-safe). Text sits on an exact character grid;
every segment gets an explicit x so columns stay aligned even if the embedded
font fails and a fallback monospace kicks in.
"""
import base64
import json
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).parent

# ---------------------------------------------------------------- palettes --
# TokyoNight Storm / Day, from folke/tokyonight.nvim kitty extras.
STORM = {
    "name": "storm",
    "bg": "#24283b", "bg_dark": "#1f2335", "fg": "#c0caf5", "fg_dim": "#a9b1d6",
    "muted": "#565f89", "border": "#1d202f",
    "red": "#f7768e", "green": "#9ece6a", "yellow": "#e0af68", "blue": "#7aa2f7",
    "magenta": "#bb9af7", "cyan": "#7dcfff", "orange": "#ff9e64",
    "ansi": ["#1d202f", "#f7768e", "#9ece6a", "#e0af68", "#7aa2f7", "#bb9af7",
             "#7dcfff", "#a9b1d6", "#414868", "#ff899d", "#9fe044", "#faba4a",
             "#8db0ff", "#c7a9ff", "#a4daff", "#c0caf5"],
    # silver ramp so hue-mapped clothing pops against neutral skin
    "art": ["#414868", "#a9b1d6", "#c0caf5"],
}
DAY = {
    "name": "day",
    "bg": "#e1e2e7", "bg_dark": "#d0d5e3", "fg": "#3760bf", "fg_dim": "#6172b0",
    "muted": "#848cb5", "border": "#b4b5b9",
    "red": "#f52a65", "green": "#587539", "yellow": "#8c6c3e", "blue": "#2e7de9",
    "magenta": "#9854f1", "cyan": "#007197", "orange": "#b15c00",
    "ansi": ["#b4b5b9", "#f52a65", "#587539", "#8c6c3e", "#2e7de9", "#9854f1",
             "#007197", "#6172b0", "#a1a6c5", "#ff4774", "#5c8524", "#a27629",
             "#358aff", "#a463ff", "#007ea8", "#3760bf"],
    # light bg: dense glyphs need DARK ink, sparse glyphs light
    "art": ["#a8aecb", "#6172b0", "#2e3c64"],
}

# ------------------------------------------------------------------ layout --
FS = 13                      # font size px
CW = FS * 0.6                # Fira Code advance = 0.6em exactly
LH = round(FS * 1.28)        # info line height px
LH_ART = 14                  # art line height px (tighter: keeps density)
ART_ASPECT = CW / LH_ART     # feed to ascii_portrait --aspect
PAD_X = 24                   # inner padding
PAD_TOP = 16                 # below title bar
PAD_BOT = 20
TITLE_H = 40
ART_COLS = 52
GAP_COLS = 4
INFO_COLS = 62
TOTAL_COLS = ART_COLS + GAP_COLS + INFO_COLS

RAMP = " .'`^\",:;Il!i><~+_-?][}{1)(|\\/tfjrxnuvczXYUJCLQ0OZmwqpdbkhao*#MW&8%B@$"


def esc(s):
    return (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


# ------------------------------------------------------------- info content --
def fmt_uptime(created_at, now=None):
    start = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
    now = now or datetime.now(timezone.utc)
    years = now.year - start.year
    months = now.month - start.month
    days = now.day - start.day
    if days < 0:
        months -= 1
        prev_month_end = (now.replace(day=1) - __import__("datetime").timedelta(days=1))
        days += prev_month_end.day
    if months < 0:
        years -= 1
        months += 12
    return f"{years} years, {months} months, {days} days"


def n(v):
    return f"{v:,}"


def build_info(stats, P):
    """Return list of rows; each row is a list of (text, color) segments."""
    key, val, mut, dot = P["blue"], P["fg"], P["muted"], P["muted"]
    acc, grn, red = P["magenta"], P["green"], P["red"]
    cyn, yel = P["cyan"], P["yellow"]

    def kv(k, segments, indent=0):
        """Dotted-leader row: key .... value (value right-aligned)."""
        if isinstance(segments, str):
            segments = [(segments, val)]
        vlen = sum(len(t) for t, _ in segments)
        pre = " " * indent + k + " "
        ndots = INFO_COLS - len(pre) - vlen - 1
        if ndots < 2:  # too long: no leader, single space
            row = [(" " * indent, val), (k, key), (" ", val)] + segments
            return row
        return ([(" " * indent, val)] if indent else []) + [
            (k, key), (" ", val), ("·" * ndots, dot), (" ", val)] + segments

    def rule(label=None):
        if not label:
            return [("─" * INFO_COLS, mut)]
        pre = "─ "
        rest = INFO_COLS - len(pre) - len(label) - 1
        return [(pre, mut), (label, acc), (" ", val), ("─" * rest, mut)]

    rows = []
    rows.append([("illya", grn), ("@", mut), ("starikov", grn), (" ", val),
                 ("─" * (INFO_COLS - len("illya@starikov ")), mut)])
    rows.append(kv("OS:", [("macOS", val), (", ", mut), ("Linux", val)]))
    rows.append(kv("Uptime (github):", fmt_uptime(stats["created_at"])))
    rows.append(kv("Host:", "Google"))
    rows.append(kv("Kernel:", "Software Engineer"))
    rows.append(kv("Shell:", [("zsh", val), (", ", mut), ("tmux", val)]))
    rows.append(kv("IDE:", [("Neovim", val), (" (btw)", mut)]))
    rows.append(kv("Terminal:", "WezTerm"))
    rows.append(kv("Keyboard.1:", [("Keychron Q10 Max", val),
                                   (" (Alice, QMK)", mut), (", ", mut),
                                   ("Jupiter Browns", val)]))
    rows.append(kv("Keyboard.2:", [("CODE V3 87-Key", val), (", ", mut),
                                   ("Cherry MX Clears", val)]))
    rows.append(kv("Baud Rate:", "110 WPM"))
    rows.append(kv("First Boot:", "age 4"))
    rows.append([])
    rows.append(kv("Languages.Programming:", [("Python, C++, Shell", val)]))
    rows.append(kv("Languages.Markup:", "HTML, LaTeX, Markdown, Regex"))
    rows.append(kv("Languages.Human:", [("English", val), (", ", mut),
                                        ("Українська", val)]))
    rows.append([])
    rows.append(kv("Hobbies.Analog:", "tea, camping, reading, cats"))
    rows.append([])
    rows.append(rule("Contact"))
    rows.append(kv("Email:", [("illya", val), ("@", mut), ("starikov.co", val)]))
    rows.append(kv("Website:", [("https://starikov.co", cyn)]))
    rows.append(kv("LinkedIn:", "illyastarikov"))
    rows.append(kv("GitHub:", "IllyaStarikov"))
    rows.append([])
    rows.append(rule("GitHub Stats"))
    rows.append(kv("Repos:", [(n(stats["repos"]), val)]))
    rows.append(kv("Stars:", [("★ ", yel), (n(stats["stars"]), yel)]))
    rows.append(kv("Commits:", [(n(stats["commits_total"]), val)]))
    rows.append(kv("Followers:", [(n(stats["followers"]), val)]))
    rows.append(kv("Lines of Code:", [(n(stats["loc_net"]), val), (" (", mut),
                                      ("+" + n(stats["loc_add"]), grn),
                                      (" / ", mut),
                                      ("-" + n(stats["loc_del"]), red),
                                      (")", mut)]))
    return rows


# --------------------------------------------------------------- svg pieces --
def font_face():
    b64 = base64.b64encode((HERE / "art" / "fira_subset.woff2").read_bytes()).decode()
    return (f"@font-face{{font-family:'FiraCodeSub';"
            f"src:url(data:font/woff2;base64,{b64}) format('woff2');}}")


def text_el(x_px, y_px, segments):
    """One grid row as a <text> with explicit-x tspans per color segment."""
    parts = []
    col = 0
    for txt, color in segments:
        if txt:
            sx = x_px + col * CW
            parts.append(f'<tspan x="{sx:.1f}" fill="{color}">{esc(txt)}</tspan>')
        col += len(txt)
    if not parts:
        return ""
    return f'<text y="{y_px:.1f}" class="t">{"".join(parts)}</text>'


def art_rows(art_text, P, cmap_text=None):
    """ASCII art lines -> rows of (char-run, color) segments.

    With a colormap: cells labelled r,o,y,g,c,b,m take theme hues; 0/1/2 take
    neutral shades. Without: 3-shade mapping by glyph density.
    """
    shades = P["art"]
    label_color = {"r": P["red"], "o": P["orange"], "y": P["yellow"],
                   "g": P["green"], "c": P["cyan"], "b": P["blue"],
                   "m": P["magenta"], "0": shades[0], "1": shades[1],
                   "2": shades[2]}
    art_lines = art_text.rstrip("\n").split("\n")
    cmap_lines = cmap_text.rstrip("\n").split("\n") if cmap_text else None

    def cell_color(ch, y, x):
        if ch == " ":
            return None
        if cmap_lines:
            try:
                label = cmap_lines[y][x]
            except IndexError:
                label = "1"
            return label_color.get(label, shades[1])
        r = RAMP.index(ch) / (len(RAMP) - 1) if ch in RAMP else 0.5
        return shades[0] if r < 0.30 else shades[1] if r < 0.62 else shades[2]

    rows = []
    for y, line in enumerate(art_lines):
        segs = []
        cur_color, cur_run = None, []
        for x, ch in enumerate(line):
            color = cell_color(ch, y, x)
            use = color if color else (cur_color or shades[0])
            ch_out = ch if color else " "
            if use != cur_color and cur_run:
                segs.append(("".join(cur_run), cur_color))
                cur_run = []
            cur_color = use
            cur_run.append(ch_out)
        if cur_run:
            segs.append(("".join(cur_run), cur_color))
        rows.append(segs)
    return rows


def render(P, stats, art_text, cmap_text=None):
    info = build_info(stats, P)
    art = art_rows(art_text, P, cmap_text)

    # vertical structure: prompt row, blank, then max(art, info) rows,
    # blank, color strip (2 rows), blank, cursor prompt row
    body_rows = max(len(art), len(info) + 4)  # info + strip below info column
    info_col_x = PAD_X + (ART_COLS + GAP_COLS) * CW

    total_rows = 1 + 1 + body_rows + 1
    width = round(PAD_X * 2 + TOTAL_COLS * CW)
    height = round(TITLE_H + PAD_TOP + total_rows * LH + PAD_BOT)

    out = []
    out.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" role="img" '
        f'aria-label="neofetch-style profile card for Illya Starikov">')
    out.append(f"<style>{font_face()}"
               f".t{{font-family:'FiraCodeSub','Fira Code',Menlo,Consolas,'DejaVu Sans Mono',monospace;"
               f"font-size:{FS}px;white-space:pre;}}</style>")
    # window
    out.append(f'<rect x="1" y="1" width="{width-2}" height="{height-2}" rx="12" '
               f'fill="{P["bg"]}" stroke="{P["border"]}" stroke-width="1.5"/>')
    # title bar
    out.append(f'<clipPath id="win"><rect x="1" y="1" width="{width-2}" '
               f'height="{height-2}" rx="12"/></clipPath>')
    out.append(f'<g clip-path="url(#win)">'
               f'<rect x="0" y="0" width="{width}" height="{TITLE_H}" fill="{P["bg_dark"]}"/></g>')
    for i, c in enumerate(("#ff5f57", "#febc2e", "#28c840")):
        out.append(f'<circle cx="{26 + i * 22}" cy="{TITLE_H / 2}" r="6.5" fill="{c}"/>')
    title = "illya@starikov: ~"
    tx = width / 2 - len(title) * CW / 2
    out.append(f'<text y="{TITLE_H / 2 + FS * 0.36}" class="t">'
               f'<tspan x="{tx:.1f}" fill="{P["muted"]}">{esc(title)}</tspan></text>')

    y0 = TITLE_H + PAD_TOP + LH  # baseline of first row
    row_y = lambda r: y0 + r * LH

    # ❯ neofetch command line
    out.append(text_el(PAD_X, row_y(0),
                       [("❯ ", P["green"]), ("neofetch", P["fg"])]))

    # art (left column): own tighter line grid, vertically centered in body
    body_top = row_y(2) - FS
    body_h = (body_rows - 2) * LH
    art_h = len(art) * LH_ART
    art_y0 = body_top + max(0, (body_h - art_h) / 2) + FS
    for i, segs in enumerate(art):
        if segs:
            out.append(text_el(PAD_X, art_y0 + i * LH_ART, segs))

    # info (right column), starting row 2
    for i, segs in enumerate(info):
        if segs:
            out.append(text_el(info_col_x, row_y(2 + i), segs))

    # color strip below info
    strip_row = 2 + len(info) + 1
    sw, sh = CW * 3, LH * 0.9
    for j in range(16):
        r, c = divmod(j, 8)
        x = info_col_x + c * sw
        y = row_y(strip_row) - FS + r * sh
        out.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{sw:.1f}" '
                   f'height="{sh:.1f}" fill="{P["ansi"][j]}"/>')

    # final prompt with blinking cursor
    last = total_rows - 1
    out.append(text_el(PAD_X, row_y(last), [("❯ ", P["green"])]))
    cx = PAD_X + 2 * CW
    cy = row_y(last) - FS + 1
    out.append(f'<rect x="{cx:.1f}" y="{cy:.1f}" width="{CW:.1f}" height="{FS + 2}" '
               f'fill="{P["fg"]}"><animate attributeName="opacity" '
               f'values="1;1;0;0" keyTimes="0;0.5;0.5;1" dur="1.1s" '
               f'repeatCount="indefinite"/></rect>')

    out.append("</svg>")
    return "\n".join(out)


def main():
    stats = json.loads((HERE / "stats.json").read_text())
    art_text = (HERE / "art" / "portrait.txt").read_text()
    cmap_path = HERE / "art" / "portrait.colors"
    cmap_text = cmap_path.read_text() if cmap_path.exists() else None
    for P, name in ((STORM, "dark"), (DAY, "light")):
        svg = render(P, stats, art_text, cmap_text)
        (HERE.parent / "assets" / f"readme-{name}.svg").write_text(svg)
        print(f"readme-{name}.svg: {len(svg):,} bytes")


if __name__ == "__main__":
    main()
