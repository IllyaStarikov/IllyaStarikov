#!/usr/bin/env python3
"""Self-hosted bilingual typing greeting SVG (replaces readme-typing-svg embed).

Per-character opacity reveal via SMIL: type -> hold -> backspace -> next
phrase, looping. Characters live in normal text flow, so the wave emoji and
Cyrillic shape natively. Fira Code subset embedded like the card.
"""
import base64
from pathlib import Path

HERE = Path(__file__).parent

PHRASES = ["Hello. 👋 I'm Illya.", "Привіт. 👋 Я Ілля."]
TYPE_S, DEL_S, HOLD_S, GAP_S = 0.075, 0.04, 1.4, 0.25
FS = 24
WIDTH, HEIGHT, BASELINE = 480, 44, 31

COLORS = {"dark": "#c0caf5", "light": "#3760bf"}  # TokyoNight storm/day fg


def font_face():
    b64 = base64.b64encode((HERE / "art" / "fira_subset.woff2").read_bytes()).decode()
    return (f"@font-face{{font-family:'FiraCodeSub';"
            f"src:url(data:font/woff2;base64,{b64}) format('woff2');}}")


def esc(ch):
    return ch.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def build(color):
    # timeline
    spans = []   # (char, t_on, t_off) absolute seconds
    t = 0.3
    for phrase in PHRASES:
        chars = list(phrase)
        n = len(chars)
        on = [t + j * TYPE_S for j in range(n)]
        t_hold_end = t + n * TYPE_S + HOLD_S
        off = [t_hold_end + (n - 1 - j) * DEL_S for j in range(n)]
        t = t_hold_end + n * DEL_S + GAP_S
        spans.append(list(zip(chars, on, off)))
    total = t + 0.2

    def keyframes(on, off):
        k_on, k_off = on / total, off / total
        return (f'values="0;1;0" keyTimes="0;{k_on:.4f};{k_off:.4f}" '
                f'calcMode="discrete" dur="{total:.2f}s" '
                f'repeatCount="indefinite"')

    texts = []
    for idx, phrase_spans in enumerate(spans):
        # Base opacity 1 for the first phrase: if a renderer ever ignores
        # SMIL, the README still shows "Hello. 👋 I'm Illya." statically.
        base = 1 if idx == 0 else 0
        tspans = []
        for ch, on, off in phrase_spans:
            tspans.append(
                f'<tspan opacity="{base}">{esc(ch)}'
                f'<animate attributeName="opacity" {keyframes(on, off)}/>'
                f'</tspan>')
        texts.append(
            f'<text x="0" y="{BASELINE}" class="g">{"".join(tspans)}</text>')

    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" '
        f'height="{HEIGHT}" viewBox="0 0 {WIDTH} {HEIGHT}" role="img" '
        f'aria-label="Hello, I\'m Illya. Привіт, я Ілля.">'
        f"<style>{font_face()}"
        f".g{{font-family:'FiraCodeSub','Fira Code',Menlo,Consolas,monospace;"
        f"font-size:{FS}px;fill:{color};white-space:pre;}}</style>"
        f'{"".join(texts)}</svg>')


for mode, color in COLORS.items():
    p = HERE.parent / "assets" / f"greeting-{mode}.svg"
    p.write_text(build(color))
    print(f"{p.name}: {p.stat().st_size:,} bytes")
