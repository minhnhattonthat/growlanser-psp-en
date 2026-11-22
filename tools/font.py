"""font.py: Growlanser 12x12 1bpp font (18 bytes/glyph, rows packed MSB-first, no row padding).

    python -X utf8 tools/font.py render BIN OFFSET FIRST COUNT OUT.png [--cols 32] [--scale 2]
        render COUNT glyphs from BIN at OFFSET, labelling each with its code (FIRST + index)
"""
import sys

from PIL import Image, ImageDraw

GW = GH = 12
GB = GW * GH // 8


def glyph(data, off):
    bits = int.from_bytes(data[off:off + GB], "big")
    return [[(bits >> (GB * 8 - 1 - (y * GW + x))) & 1 for x in range(GW)] for y in range(GH)]


def render(data, off, first, count, out, cols=32, scale=2):
    cw, ch = (GW + 4) * scale, (GH + 12) * scale
    rows = (count + cols - 1) // cols
    im = Image.new("L", (cols * cw, rows * ch), 0)
    dr = ImageDraw.Draw(im)
    for i in range(count):
        g = glyph(data, off + i * GB)
        X, Y = (i % cols) * cw, (i // cols) * ch
        dr.text((X, Y), "%X" % (first + i), fill=110)
        for y in range(GH):
            for x in range(GW):
                if g[y][x]:
                    dr.rectangle([X + x * scale, Y + 10 * scale // 2 + 2 + y * scale,
                                  X + x * scale + scale - 1, Y + 10 * scale // 2 + 2 + y * scale + scale - 1], fill=255)
    im.save(out)


if __name__ == "__main__":
    a = sys.argv
    if a[1] == "render":
        kw = {}
        if "--cols" in a:
            kw["cols"] = int(a[a.index("--cols") + 1])
        if "--scale" in a:
            kw["scale"] = int(a[a.index("--scale") + 1])
        render(open(a[2], "rb").read(), int(a[3], 0), int(a[4], 0), int(a[5], 0), a[6], **kw)
