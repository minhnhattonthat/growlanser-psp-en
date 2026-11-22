"""gfxsweep.py: static graphics sweep of a sector archive (MAP.DAT) into numbered review sheets (docs/re/graphics.md).

    python -X utf8 tools/gfxsweep.py ARCHIVE OUTDIR [--bpp 8] [--stride 128] [--rows 256] [--per 16] [--min 8]

Every entry of >= --min sectors is cut into pages of --rows rows; byte-identical pages are rendered once.
OUTDIR/index.tsv: sheet, column, entry, offset in entry (or the duplicate it repeats). Skipped entries are printed.
"""
import argparse
import hashlib
import os
import sys

from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(__file__))
from dat import entries, SECTOR  # noqa: E402
from rawgfx import pixels  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("archive")
    ap.add_argument("out")
    ap.add_argument("--bpp", type=int, default=8)
    ap.add_argument("--stride", type=int, default=128)
    ap.add_argument("--rows", type=int, default=256)
    ap.add_argument("--per", type=int, default=16)
    ap.add_argument("--min", type=int, default=8)
    a = ap.parse_args()
    d = open(a.archive, "rb").read()
    os.makedirs(a.out, exist_ok=True)
    page = a.stride * a.rows
    w = a.stride * 8 // a.bpp
    seen, pages, idx, skipped = {}, [], [], 0
    for e, (s, n) in enumerate(entries(d)):
        if n < a.min:
            skipped += 1
            continue
        for off in range(0, n * SECTOR, page):
            buf = d[s * SECTOR + off:s * SECTOR + min(off + page, n * SECTOR)]
            if buf.count(0) == len(buf):
                idx.append(("-", "-", e, f"{off:X}", "zero"))
                continue
            h = hashlib.sha1(buf).digest()
            if h in seen:
                idx.append(("-", "-", e, f"{off:X}", "dup of " + seen[h]))
                continue
            seen[h] = f"{e}:{off:X}"
            pages.append((e, off, buf))
    for k in range(0, len(pages), a.per):
        sheet = Image.new("L", ((w + 8) * a.per, a.rows + 12), 64)
        dr = ImageDraw.Draw(sheet)
        for j, (e, off, buf) in enumerate(pages[k:k + a.per]):
            buf += bytes(-len(buf) % a.stride)
            sheet.paste(Image.fromarray(pixels(buf, a.bpp).reshape(-1, w)), (j * (w + 8), 12))
            dr.text((j * (w + 8), 0), f"{e}:{off:X}", fill=255)
            idx.append((f"{k // a.per:04d}", str(j), e, f"{off:X}", ""))
        sheet.save(os.path.join(a.out, f"{k // a.per:04d}.png"))
    with open(os.path.join(a.out, "index.tsv"), "w", encoding="utf-8") as f:
        f.write("sheet\tcol\tentry\toffset\tnote\n")
        for r in idx:
            f.write("\t".join(map(str, r)) + "\n")
    print(f"{len(pages)} pages -> {(len(pages) + a.per - 1) // a.per} sheets; {skipped} entries under --min skipped "
          f"(listed by dat.py); dup/zero pages in index.tsv")


if __name__ == "__main__":
    main()
