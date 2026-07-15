# devfetch

A neofetch-style GitHub profile card -- an ASCII portrait beside a column of
`key: value` rows, theme-aware (TokyoNight Storm in dark, Day in light),
redrawn every night by a GitHub Action with live stats. This directory is the
source for the card shown in the repository's root `README.md`.

Modeled on the original profile card by Andrew6rant (github.com/Andrew6rant),
reimplemented from scratch (that project carries no license).

## Files

| File | Does |
|------|------|
| `generate_svg.py` | Draws the two self-contained SVGs (`assets/readme-{dark,light}.svg`) |
| `fetch_stats.py` | Pulls live GitHub stats via `gh api graphql` into `stats.json` |
| `ascii_portrait.py` | Turns a photo into `art/portrait.txt` + `art/portrait.colors` |
| `art/` | The portrait text, its color map, and the embedded Fira Code subset |
| `../.github/workflows/update-readme.yml` | The nightly refresh + failure alert |

## Make it yours

Everything you need to change is marked `TODO` in the code -- grep for it:

```bash
grep -rn TODO src/
```

| Change | Where |
|--------|-------|
| Your GitHub username | `fetch_stats.py` -> `USER` |
| Every card row (labels + values) | `generate_svg.py` -> `build_info()` |
| The terminal title (`user@host`) | `generate_svg.py` -> `title` |
| Theme colors | `generate_svg.py` -> `STORM` / `DAY` |
| The portrait | your own photo -- see below |

## Requirements

- Python 3.11+ with Pillow -- `pip install Pillow`
- GitHub CLI (`gh`), authenticated -- `gh auth login` (the Action uses `GH_TOKEN`)
- rembg, for background removal -- run on demand with `uvx` (below)
- ImageMagick (`magick`), to matte the cutout onto black

## The portrait is hand-work

There is no one-size recipe: you pick your own photo and tune it by eye. A
head-and-shoulders shot with good contrast and a plain-ish background works best.

```bash
# 1. cut the background out
uvx --python 3.11 --from "rembg[cpu,cli]" rembg i you.jpg you_nobg.png

# 2. matte the subject onto black (so it reads on the dark card)
magick you_nobg.png -background black -flatten you_black.png

# 3. render ASCII glyphs + a per-cell color map
python3 ascii_portrait.py you_black.png \
  --cols 52 --aspect 0.557 --ramp medium --contrast 1.15 --sharpen \
  --out art/portrait.txt --colors-out art/portrait.colors
```

Re-run step 3 with different `--contrast` / `--gamma` / `--sharpen` until the
face reads. The color map snaps each cell to a theme hue; if your clothing or
skin lands on the wrong color, tune the thresholds in `color_labels()`.

## Build

```bash
python3 fetch_stats.py    # writes stats.json + loc_cache.json
python3 generate_svg.py   # writes ../assets/readme-{dark,light}.svg
```

Commit the two SVGs; the root `README.md` embeds them with a `<picture>` that
swaps by `prefers-color-scheme`.

## Nightly refresh

`update-readme.yml` runs the two scripts on a cron (`23 9 * * *`) and commits the
redrawn SVGs only when something changed. With no setup it counts public data;
add a classic PAT as the `README_TOKEN` secret (scopes: `repo`, `read:user`) to
include private-repo counts. If a run fails it opens an issue, so the card can't
silently freeze.

## Why the SVGs are self-contained

GitHub serves README images through its camo proxy, which blocks every external
fetch -- so the font is a 28 KB Fira Code subset (ASCII + Cyrillic + box-drawing
+ the star glyph) embedded as a base64 data-URI, and there are no network calls
or working links inside the card. To resubset for other glyphs, use `pyftsubset`
(fonttools).
