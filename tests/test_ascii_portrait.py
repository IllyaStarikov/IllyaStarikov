"""Tests for the photo -> ASCII + color-map pipeline."""

from PIL import Image

import ascii_portrait as ap
import generate_svg as gs

# classic has no double-quote or backslash, so it is safe to inline verbatim;
# medium is cross-checked against generate_svg.RAMP (the same ramp).
CLASSIC = (
    "`.-':_,^=;><+!rc*/z?sLTv)J7(|Fi{C}fI31tlu[neoZ5Yxjya]"
    "2ESwqkP6h9d4VpOGbUAKXHm8RD#$Bg0MNWQ%&@"
)


def test_ramps_preserved_after_wrapping():
    # The medium ramp is split across lines in the source; it must be byte-
    # identical to the copy in generate_svg (which the SVG output pins down).
    assert ap.RAMPS["medium"] == gs.RAMP
    assert len(ap.RAMPS["medium"]) == 70
    assert ap.RAMPS["classic"] == CLASSIC
    assert len(ap.RAMPS["classic"]) == 91
    assert ap.RAMPS["short"] == " .:-=+*#%@"
    assert ap.RAMPS["blocky"] == " .:;+=xX$&@"


def test_to_ascii_dimensions(tmp_path):
    img = Image.new("L", (100, 100), 128)
    p = tmp_path / "flat.png"
    img.save(p)
    art = ap.to_ascii(str(p), cols=20, char_aspect=0.5)
    lines = art.split("\n")
    assert len(lines) == 10  # round(20 * 100/100 * 0.5)
    assert all(len(line) <= 20 for line in lines)


def test_to_ascii_maps_dark_to_light(tmp_path):
    w = 70
    img = Image.new("L", (w, 1))
    for x in range(w):
        img.putpixel((x, 0), round(x / (w - 1) * 255))
    p = tmp_path / "grad.png"
    img.save(p)
    line = ap.to_ascii(str(p), cols=w, char_aspect=1.0, ramp="medium")
    assert line[0] == " "  # darkest -> ramp[0]
    assert line[-1] in ap.RAMPS["medium"][-5:]  # brightest -> densest glyph


def _label(tmp_path, rgb):
    img = Image.new("RGB", (1, 1), rgb)
    p = tmp_path / "px.png"
    img.save(p)
    return ap.color_labels(str(p), 1, 1)


def test_color_labels_blue_shirt(tmp_path):
    assert _label(tmp_path, (120, 150, 230)) == "b"  # pastel blue stays blue


def test_color_labels_dark_is_empty(tmp_path):
    assert _label(tmp_path, (5, 5, 5)) == "."  # near-black -> empty


def test_color_labels_skin_is_neutral(tmp_path):
    # warm skin tone -> a neutral shade (0/1/2), not a theme hue
    assert _label(tmp_path, (200, 160, 140)) in "012"
