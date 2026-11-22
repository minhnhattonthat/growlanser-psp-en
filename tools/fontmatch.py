"""fontmatch.py: first-guess character for every glyph of the game font, by pixel match against MS Gothic 12px.

A first guess only (skill: system-font matching fails on look-alikes); tbl/jp.tbl is reviewed by eye and by
decoded-script context after this. Writes CODE<TAB>CHAR<TAB>SCORE<TAB>SECOND<TAB>SCORE2 per glyph.

    python -X utf8 tools/fontmatch.py EXE OUT.tsv [FIRST LAST [FONT_OFF]]
PSP: python -X utf8 tools/fontmatch.py work/iso/PSP_GAME/SYSDIR/BOOT.BIN work/fontmatch.tsv 0x7CB 0x835 0x1230D8
"""
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, __import__("os").path.dirname(__file__))
import font  # noqa: E402

FONT_OFF = 0xE85C8  # SLPS_023.80 file offset of glyph 0 (RAM 0x800F7DC8)


def candidates():
    out = []
    for hi in list(range(0x81, 0xA0)) + list(range(0xE0, 0xEB)):
        for lo in range(0x40, 0xFD):
            if lo == 0x7F:
                continue
            try:
                ch = bytes([hi, lo]).decode("cp932")
            except UnicodeDecodeError:
                continue
            if ch.isprintable() and ch != "\u3000":
                out.append(ch)
    return out


def render(ch, f):
    im = Image.new("L", (16, 16), 0)
    ImageDraw.Draw(im).text((0, 0), ch, font=f, fill=255)
    return (np.array(im)[:12, :12] > 127).astype(np.int8)


def shifts(a):
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            yield np.roll(np.roll(a, dy, 0), dx, 1)


def main():
    exe = open(sys.argv[1], "rb").read()
    first, last = (int(sys.argv[3], 0), int(sys.argv[4], 0)) if len(sys.argv) > 4 else (0, 0x7CA)
    font_off = int(sys.argv[5], 0) if len(sys.argv) > 5 else FONT_OFF
    f = ImageFont.truetype("C:/Windows/Fonts/msgothic.ttc", 12)
    cands = candidates()
    ref = np.stack([render(c, f) for c in cands]).reshape(len(cands), -1)
    rows = []
    for code in range(first, last + 1):
        g = np.array(font.glyph(exe, font_off + code * font.GB), dtype=np.int8)
        if not g.any():
            rows.append((code, "", 0, "", 0))
            continue
        best = None
        for s in shifts(g):
            d = (ref != s.reshape(1, -1)).sum(1)
            best = d if best is None else np.minimum(best, d)
        order = np.argsort(best)
        rows.append((code, cands[order[0]], int(best[order[0]]), cands[order[1]], int(best[order[1]])))
    with open(sys.argv[2], "w", encoding="utf-8", newline="\n") as o:
        for r in rows:
            o.write("%04X\t%s\t%d\t%s\t%d\n" % r)


if __name__ == "__main__":
    main()
