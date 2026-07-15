"""Tests for the SVG card generator (deterministic logic + a smoke render)."""

import json
from datetime import datetime, timezone

import generate_svg as gs

SAMPLE_STATS = {
    "created_at": "2014-08-25T17:45:39Z",
    "repos": 12,
    "stars": 211,
    "commits_total": 6816,
    "followers": 28,
    "loc_net": 3669391,
    "loc_add": 5865246,
    "loc_del": 2195855,
}
SAMPLE_ART = "  .^,.\n .QCcj.\n  }C0U\n"


def test_fmt_uptime_no_borrow():
    up = gs.fmt_uptime(
        "2020-01-01T00:00:00Z",
        now=datetime(2023, 6, 15, tzinfo=timezone.utc),
    )
    assert up == "3 years, 5 months, 14 days"


def test_fmt_uptime_month_borrow():
    # now.month < start.month -> borrow a year
    up = gs.fmt_uptime(
        "2020-06-01T00:00:00Z",
        now=datetime(2021, 3, 1, tzinfo=timezone.utc),
    )
    assert up == "0 years, 9 months, 0 days"


def test_fmt_uptime_day_borrow():
    # now.day < start.day -> borrow a month (Feb 2020 has 29 days)
    up = gs.fmt_uptime(
        "2020-01-15T00:00:00Z",
        now=datetime(2020, 3, 10, tzinfo=timezone.utc),
    )
    assert up == "0 years, 1 months, 24 days"


def test_n_formats_thousands():
    assert gs.n(1234567) == "1,234,567"
    assert gs.n(0) == "0"


def test_esc_escapes_markup():
    assert gs.esc("a<b>&c") == "a&lt;b&gt;&amp;c"


def test_palettes_well_formed():
    for P in (gs.STORM, gs.DAY):
        assert len(P["ansi"]) == 16
        assert len(P["art"]) == 3
        assert all(
            c.startswith("#") and len(c) == 7 for c in P["ansi"] + P["art"]
        )


def test_render_produces_valid_svg():
    svg = gs.render(gs.STORM, SAMPLE_STATS, SAMPLE_ART)
    assert svg.startswith("<svg")
    assert svg.rstrip().endswith("</svg>")
    assert 'xmlns="http://www.w3.org/2000/svg"' in svg
    for field in ("OS:", "Host:", "Google", "GitHub Stats", "Repos:"):
        assert field in svg
    assert gs.n(SAMPLE_STATS["stars"]) in svg  # 211 rendered


def test_render_themes_use_their_palettes():
    dark = gs.render(gs.STORM, SAMPLE_STATS, SAMPLE_ART)
    light = gs.render(gs.DAY, SAMPLE_STATS, SAMPLE_ART)
    assert gs.STORM["bg"] in dark
    assert gs.DAY["bg"] in light
    assert dark != light


def test_render_real_data_smoke():
    stats = json.loads((gs.HERE / "stats.json").read_text())
    art = (gs.HERE / "art" / "portrait.txt").read_text()
    cmap_path = gs.HERE / "art" / "portrait.colors"
    cmap = cmap_path.read_text() if cmap_path.exists() else None
    for P in (gs.STORM, gs.DAY):
        svg = gs.render(P, stats, art, cmap)
        assert svg.startswith("<svg") and svg.rstrip().endswith("</svg>")
        assert svg.count("<text") > 10
