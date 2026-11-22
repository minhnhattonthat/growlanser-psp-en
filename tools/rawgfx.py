"""rawgfx.py: render raw PS1 pixel data (no TIM header) as grey sheets for the graphics-text survey.

    python -X utf8 tools/rawgfx.py FILE OUTDIR [--bpp 4] [--stride 128] [--at 0] [--len N] [--rows 512] [--per 4]

PS1 4bpp = low nibble first. --stride = bytes per image row (VRAM rectangles: 128 B = 256 px at 4bpp).
Writes OUTDIR/<offset hex>.png sheets, --per strips of --rows rows side by side, each labelled by file offset.
"""
import argparse
import os

import numpy as np
from PIL import Image, ImageDraw


def pixels(buf, bpp):
    a = np.frombuffer(buf, np.uint8)
    if bpp == 4:
        p = np.empty(a.size * 2, np.uint8)
        p[0::2] = a & 15
        p[1::2] = a >> 4
        return p * 17
    if bpp == 8:
        return a
    w = a[:a.size // 2 * 2].view("<u2").astype(np.int32)  # 16bpp BGR555 -> grey; int32 so *255 can't overflow
    r, g, b = w & 31, (w >> 5) & 31, (w >> 10) & 31
    return ((r * 3 + g * 6 + b) * 255 // 310).astype(np.uint8)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("file")
    ap.add_argument("out")
    ap.add_argument("--bpp", type=int, default=4, choices=(4, 8, 16))
    ap.add_argument("--stride", type=int, default=128)
    ap.add_argument("--at", type=lambda s: int(s, 0), default=0)
    ap.add_argument("--len", type=lambda s: int(s, 0), default=0)
    ap.add_argument("--rows", type=int, default=512)
    ap.add_argument("--per", type=int, default=4)
    a = ap.parse_args()
    d = open(a.file, "rb").read()
    end = a.at + a.len if a.len else len(d)
    os.makedirs(a.out, exist_ok=True)
    strip = a.stride * a.rows
    w = a.stride * 8 // a.bpp
    offs = list(range(a.at, end, strip))
    for k in range(0, len(offs), a.per):
        sheet = Image.new("L", ((w + 8) * a.per, a.rows + 12), 64)
        dr = ImageDraw.Draw(sheet)
        for j, o in enumerate(offs[k:k + a.per]):
            buf = d[o:min(o + strip, end)]
            buf += bytes(-len(buf) % a.stride)
            img = Image.fromarray(pixels(buf, a.bpp).reshape(-1, w))
            sheet.paste(img, (j * (w + 8), 12))
            dr.text((j * (w + 8), 0), f"{o:06X}", fill=255)
        sheet.save(os.path.join(a.out, f"{offs[k]:06X}.png"))
    print(f"{len(offs)} strips -> {(len(offs) + a.per - 1) // a.per} sheets in {a.out}")


if __name__ == "__main__":
    main()
