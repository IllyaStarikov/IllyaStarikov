#!/usr/bin/env python3
"""Convert a photo to ASCII art tuned for a dark-background SVG README.

TODO (adopt): use YOUR OWN photo -- this step is hand-work, there is no
one-size recipe. Remove the background and matte the subject onto black
first (see src/README.md), then tune --contrast/--gamma/--sharpen until
the face reads. Emits portrait.txt (glyphs) + portrait.colors (hues).
"""

from PIL import Image, ImageEnhance, ImageFilter, ImageOps

RESAMPLE = Image.Resampling.LANCZOS

# Character ramps, dark -> light (on a dark background, the brightest
# pixels get the densest glyphs).
RAMPS = {
    "short": " .:-=+*#%@",
    "medium": (
        " .'`^\",:;Il!i><~+_-?][}{1)(|\\/tfjrx"
        "nuvczXYUJCLQ0OZmwqpdbkhao*#MW&8%B@$"
    ),
    "classic": (
        "`.-':_,^=;><+!rc*/z?sLTv)J7(|Fi{C}fI31tlu[neo"
        "Z5Yxjya]2ESwqkP6h9d4VpOGbUAKXHm8RD#$Bg0MNWQ%&@"
    ),
    "blocky": " .:;+=xX$&@",
}


def to_ascii(
    img_path,
    cols=52,
    char_aspect=0.5,
    ramp="medium",
    contrast=1.0,
    brightness=1.0,
    gamma=1.0,
    sharpen=False,
    invert=False,
    autocontrast_cutoff=None,
):
    """Map pixel brightness to a glyph ramp -> ASCII lines (on a dark
    card, bright pixels get the densest glyphs)."""
    img = Image.open(img_path).convert("L")
    if autocontrast_cutoff is not None:
        img = ImageOps.autocontrast(img, cutoff=autocontrast_cutoff)
    if sharpen:
        img = img.filter(
            ImageFilter.UnsharpMask(radius=2, percent=120, threshold=2)
        )
    if contrast != 1.0:
        img = ImageEnhance.Contrast(img).enhance(contrast)
    if brightness != 1.0:
        img = ImageEnhance.Brightness(img).enhance(brightness)

    w, h = img.size
    rows = max(1, round(cols * (h / w) * char_aspect))
    img = img.resize((cols, rows), RESAMPLE)

    chars = RAMPS[ramp]
    if invert:
        chars = chars[::-1]
    n = len(chars)
    px = img.load()
    lines = []
    for y in range(rows):
        line = []
        for x in range(cols):
            v = px[x, y] / 255.0
            if gamma != 1.0:
                v = v**gamma
            line.append(chars[min(n - 1, int(v * n))])
        lines.append("".join(line).rstrip())
    return "\n".join(lines)


def color_labels(img_path, cols, rows, sat_floor=0.18, dark_floor=0.16):
    """Per-cell color class: r,o,y,g,c,b,m hues, 0/1/2 neutral shades,
    or '.' for empty."""
    import colorsys

    img = Image.open(img_path).convert("RGB").resize((cols, rows), RESAMPLE)
    px = img.load()
    grid = []
    for y in range(rows):
        row = []
        for x in range(cols):
            r, g, b = (v / 255.0 for v in px[x, y])
            h, s, v = colorsys.rgb_to_hsv(r, g, b)
            h *= 360
            if v < 0.06:
                row.append(".")
            elif 190 <= h < 262 and s >= 0.10 and v >= dark_floor:
                row.append("b")  # pastel blues (shirt) stay blue
            elif s < sat_floor or v < dark_floor:
                row.append("0" if v < 0.35 else "1" if v < 0.65 else "2")
            elif (0 <= h < 60 or h >= 340) and s < 0.82:
                # skin, lips, hair warm tones -> neutral shades, not theme hues
                row.append("0" if v < 0.35 else "1" if v < 0.7 else "2")
            elif h < 25 or h >= 330:
                row.append("r")
            elif h < 52:
                row.append("o")
            elif h < 70:
                row.append("y")
            elif h < 170:
                row.append("g")
            elif h < 210:
                row.append("c")
            elif h < 270:
                row.append("b")
            else:
                row.append("m")
        grid.append(row)
    # 3x3 mode filter to kill speckle (empties stay empty)
    from collections import Counter

    out = [row[:] for row in grid]
    for y in range(rows):
        for x in range(cols):
            if grid[y][x] == ".":
                continue
            neigh = [
                grid[ny][nx]
                for ny in range(max(0, y - 1), min(rows, y + 2))
                for nx in range(max(0, x - 1), min(cols, x + 2))
                if grid[ny][nx] != "."
            ]
            out[y][x] = Counter(neigh).most_common(1)[0][0]
    return "\n".join("".join(row) for row in out)


if __name__ == "__main__":
    import argparse

    p = argparse.ArgumentParser()
    p.add_argument("image")
    p.add_argument("--cols", type=int, default=52)
    p.add_argument("--aspect", type=float, default=0.5)
    p.add_argument("--ramp", default="medium", choices=RAMPS)
    p.add_argument("--contrast", type=float, default=1.0)
    p.add_argument("--brightness", type=float, default=1.0)
    p.add_argument("--gamma", type=float, default=1.0)
    p.add_argument("--sharpen", action="store_true")
    p.add_argument("--invert", action="store_true")
    p.add_argument("--autocontrast", type=float, default=None)
    p.add_argument("--out", default=None)
    p.add_argument(
        "--colors-out", default=None, help="also write per-cell color-class map"
    )
    a = p.parse_args()
    art = to_ascii(
        a.image,
        a.cols,
        a.aspect,
        a.ramp,
        a.contrast,
        a.brightness,
        a.gamma,
        a.sharpen,
        a.invert,
        a.autocontrast,
    )
    if a.out:
        with open(a.out, "w") as f:
            f.write(art + "\n")
    if a.colors_out:
        rows = len(art.split("\n"))
        cmap = color_labels(a.image, a.cols, rows)
        # blank cells in art must be blank in colormap
        cmap = "\n".join(
            "".join(
                "." if (x >= len(al) or al[x] == " ") else cl[x]
                for x in range(len(cl))
            )
            for al, cl in zip(art.split("\n"), cmap.split("\n"))
        )
        with open(a.colors_out, "w") as f:
            f.write(cmap + "\n")
    print(art)
