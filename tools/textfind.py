"""textfind.py: rank images / raw archive pages by "rows of glyph-sized blobs" (likely drawn text).

A screening aid for the graphics-text survey, not a verdict: view the top-ranked hits zoomed.
Masks: pixels != the image's most common value (sprite sheets, raw pages), plus bright and dark strokes
against a 15x15 local mean (text on a textured background). A hit is a run of >= --run components of
glyph size (4-24 px) sharing a baseline, similar height, gaps under 1.2x height.

    python -X utf8 tools/textfind.py png DIR_OR_PNG.. [--top 40]
    python -X utf8 tools/textfind.py dat ARCHIVE [--bpp 8 --stride 128] [--min 8] [--top 40]
"""
import argparse
import os
import sys

import numpy as np
from PIL import Image
from scipy import ndimage

sys.path.insert(0, os.path.dirname(__file__))
from dat import SECTOR, entries  # noqa: E402
from rawgfx import pixels  # noqa: E402


def runs(mask, minrun):
    """Best run of glyph-sized components on one baseline: (length, x, y)."""
    lab, n = ndimage.label(mask, structure=np.ones((3, 3)))
    if n == 0 or n > 20000:
        return (0, 0, 0)
    boxes = []
    for sl in ndimage.find_objects(lab):
        h, w = sl[0].stop - sl[0].start, sl[1].stop - sl[1].start
        if 4 <= h <= 24 and 2 <= w <= 24:
            boxes.append((sl[0].start, sl[0].stop, sl[1].start, sl[1].stop))
    boxes.sort(key=lambda b: (b[1], b[2]))
    best = (0, 0, 0)
    used = set()
    for i, (y0, y1, x0, x1) in enumerate(boxes):
        if i in used:
            continue
        h = y1 - y0
        row = sorted([j for j, b in enumerate(boxes) if abs(b[1] - y1) <= 2 and abs((b[1] - b[0]) - h) <= max(3, h // 2)],
                     key=lambda j: boxes[j][2])
        used.update(row)
        k, end = 0, None
        for j in row:
            b = boxes[j]
            if end is not None and 0 <= b[2] - end <= 1.2 * max(h, 6):
                k += 1
            else:
                k = 1
            end = max(b[3], end or 0) if k > 1 else b[3]
            if k > best[0]:
                best = (k, b[2], b[0])
    return best if best[0] >= minrun else (0, 0, 0)


def score(a, minrun):
    a = a.astype(np.int16)
    vals, cnt = np.unique(a, return_counts=True)
    res = [runs(a != vals[cnt.argmax()], minrun)]
    if a.shape[0] >= 16 and a.shape[1] >= 16:
        m = ndimage.uniform_filter(a.astype(np.float32), 15)
        res += [runs(a > m + 40, minrun), runs(a < m - 40, minrun)]
    return max(res)


def crops(a, hits, d):
    from PIL import ImageDraw
    cw, ch, per = 240, 48, 4
    sheet = Image.new("L", (per * (cw * 2 + 8), ((len(hits) + per - 1) // per) * (ch * 2 + 14)), 64)
    dr = ImageDraw.Draw(sheet)
    for i, (k, name, x, y) in enumerate(hits):
        if d is None:
            im = Image.open(name).convert("L")
        else:
            e, off = name.split(":")
            s, n = entries(d)[int(e)]
            buf = d[s * SECTOR + int(off, 16):s * SECTOR + min(int(off, 16) + a.stride * a.rows, n * SECTOR)]
            buf += bytes(-len(buf) % a.stride)
            im = Image.fromarray(pixels(buf, a.bpp).reshape(-1, a.stride * 8 // a.bpp))
        x0, y0 = max(0, x - 16), max(0, y - 12)
        c = im.crop((x0, y0, x0 + cw, y0 + ch)).resize((cw * 2, ch * 2), Image.NEAREST)
        px, py = (i % per) * (cw * 2 + 8), (i // per) * (ch * 2 + 14)
        sheet.paste(c, (px, py + 12))
        dr.text((px, py), f"{i} {os.path.basename(name)} {k}", fill=255)
    sheet.save(a.sheet)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["png", "dat"])
    ap.add_argument("paths", nargs="+")
    ap.add_argument("--bpp", type=int, default=8)
    ap.add_argument("--stride", type=int, default=128)
    ap.add_argument("--rows", type=int, default=256)
    ap.add_argument("--min", type=int, default=8)
    ap.add_argument("--run", type=int, default=5)
    ap.add_argument("--top", type=int, default=40)
    ap.add_argument("--sheet", help="write a PNG of 240x48 crops at each hit (2x), 4 per row")
    a = ap.parse_args()
    hits = []
    if a.mode == "png":
        files = []
        for p in a.paths:
            files += [os.path.join(p, f) for f in sorted(os.listdir(p)) if f.endswith(".png")] if os.path.isdir(p) else [p]
        for f in files:
            k, x, y = score(np.asarray(Image.open(f).convert("L")), a.run)
            hits.append((k, f, x, y))
    else:
        d = open(a.paths[0], "rb").read()
        page = a.stride * a.rows
        w = a.stride * 8 // a.bpp
        for e, (s, n) in enumerate(entries(d)):
            if n < a.min:
                continue
            for off in range(0, n * SECTOR, page):
                buf = d[s * SECTOR + off:s * SECTOR + min(off + page, n * SECTOR)]
                buf += bytes(-len(buf) % a.stride)
                k, x, y = score(pixels(buf, a.bpp).reshape(-1, w), a.run)
                hits.append((k, f"{e}:{off:X}", x, y))
    hits.sort(key=lambda h: -h[0])
    for k, name, x, y in hits[:a.top]:
        if k:
            print(f"{k}\t{name}\tx={x} y={y}")
    if a.sheet:
        crops(a, [h for h in hits[:a.top] if h[0]], d if a.mode == "dat" else None)
    print(f"{sum(1 for h in hits if h[0])} of {len(hits)} with a run >= {a.run}", file=sys.stderr)


if __name__ == "__main__":
    main()
