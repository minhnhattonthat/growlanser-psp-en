"""appendixgfx.py: English G4 labels of AORI's APPENDIX ROOM (docs/re/graphics.md G4, decision D16).

Texture: MSYS.DAT 0x70000 on, 8bpp, 256-byte rows (texture row r = 0x70000 + r*256; VRAM x 896, y r+88 in the
room). Labels are hand-lettered: an inner fill (indices 1-0x5F) inside a 2-3 px ring (222 = black outline, then
antialias). The new labels are put together from the sheet's own Latin letters, so they keep the lettering:
  OMAKE/1  GLチップスカード入れ (非売品)  ->  "GL CARDS" + "(PROMO)"   (D = mirrored C closed by a stem)
  OMAKE/2  VISUALビューモード            ->  "VISUAL ROOM"             (ROOM from MUSIC ROOM, OMAKE/3)
A letter = the inner components in an x span of a source line plus every ring pixel nearest to them (BFS).

    python -X utf8 tools/appendixgfx.py OUT.png [SHOT.png]   old | new, 3x (palette voted from a room shot)
"""
import sys
from collections import Counter, deque

BASE, ROW = 0x71000, 256  # PSP: the PS1 sheet (0x70000 there) sits 0x1000 later in MSYS.DAT, byte-identical
INNER = 0x60  # indices 1..0x5F are fill, the rest ring/antialias
RING = {1: 222, 2: 222, 3: 108}  # value by distance from the fill, for drawn (not copied) parts: the sheet's modes

# source lines (y0, y1, x0, x1): texture rows/cols holding one line of lettering and nothing else
GL_LINE = (274, 302, 0, 142)
VISUAL_LINE = (325, 352, 0, 142)
MUSIC_LINE = (232, 256, 112, 248)
CV_LINE = (366, 392, 0, 142)  # CV MESSAGE
SMALL_LINE = (185, 197, 112, 240)  # AORI's APPENDIX ROOM
PAREN_LINE = (298, 313, 86, 142)  # (非売品)
# label rects to clear and refill (y0, y1, x0, x1)
LABEL1 = (274, 313, 0, 142)
LABEL2 = (324, 353, 0, 143)


def px(m, y, x):
    return m[BASE + y * ROW + x]


def letter(m, line, xa, xb):
    """{(y, x): (value, distance from fill)} of the letter whose fill lies in columns xa..xb of line."""
    y0, y1, x0, x1 = line
    seed = {(y, x): x for y in range(y0, y1) for x in range(x0, x1) if 0 < px(m, y, x) < INNER}
    own, dist = {}, {}
    q = deque()
    for p, x in seed.items():
        own[p], dist[p] = xa <= x <= xb, 0
        q.append(p)
    while q:  # nearest fill wins: ring pixels between two letters split down the middle
        y, x = q.popleft()
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                n = (y + dy, x + dx)
                if y0 <= n[0] < y1 and x0 <= n[1] < x1 and n not in dist and px(m, *n):
                    dist[n], own[n] = dist[(y, x)] + 1, own[(y, x)]
                    q.append(n)
    return {p: (px(m, *p), dist[p]) for p in dist if own[p]}


def box(g, fill=True):
    ps = [p for p, (v, d) in g.items() if d == 0 or not fill]
    return min(y for y, x in ps), max(y for y, x in ps), min(x for y, x in ps), max(x for y, x in ps)


def ring(fill):
    """Fill pixels {(y, x): value} -> glyph with a RING outline drawn around them."""
    g = {p: (v, 0) for p, v in fill.items()}
    q = deque(fill)
    while q:
        y, x = q.popleft()
        d = g[(y, x)][1] + 1
        if d not in RING:
            continue
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                n = (y + dy, x + dx)
                if n not in g:
                    g[n] = (RING[d], d)
                    q.append(n)
    return g


def scaled(g, h):
    """Glyph g's fill scaled (nearest) to h rows, the ring drawn anew."""
    t, b, l, r = box(g)
    f = h / (b - t + 1)
    fill = {(y - t, x - l): v for (y, x), (v, d) in g.items() if d == 0}
    out = {}
    for y in range(h):
        for x in range(round((r - l + 1) * f)):
            v = fill.get((int(y / f), int(x / f)))
            if v is not None:
                out[(y, x)] = v
    return ring(out)


def letter_d(m):
    """D: CV MESSAGE's C mirrored (bowl on the right), its open left side closed by a 2 px stem."""
    c = letter(m, CV_LINE, 8, 20)
    t, b, l, r = box(c)
    fill = {(y, l + r - x): v for (y, x), (v, d) in c.items() if d == 0}
    v = Counter(fill.values()).most_common(1)[0][0]
    for y in range(t + 1, b):
        for x in (l, l + 1):
            fill[(y, x)] = v
    return ring(fill)


def place(canvas, g, x, bottom):
    """Paste glyph g with its fill's left edge at x and its fill's bottom row at bottom (nearer fill wins)."""
    t, b, l, r = box(g)
    for (y, xx), (v, d) in g.items():
        p = (y - b + bottom, xx - l + x)
        if p not in canvas or d < canvas[p][1]:
            canvas[p] = (v, d)
    return x + r - l + 1


def write(m, rect, canvas, log=None):
    """Clear rect and draw canvas in it, centred horizontally on the old label's ink."""
    y0, y1, x0, x1 = rect
    old = [p for p in ((y, x) for y in range(y0, y1) for x in range(x0, x1)) if px(m, *p)]
    shift = (min(x for y, x in old) + max(x for y, x in old)) // 2 - \
        (min(x for y, x in canvas) + max(x for y, x in canvas)) // 2
    rows = {y: bytes(m[BASE + y * ROW + x0:BASE + y * ROW + x1]) for y in range(y0, y1)}
    for y in range(y0, y1):
        m[BASE + y * ROW + x0:BASE + y * ROW + x1] = bytes(x1 - x0)
    for (y, x), (v, d) in canvas.items():
        x += shift
        assert y0 <= y < y1 and x0 <= x < x1, (rect, y, x)
        m[BASE + y * ROW + x] = v
    if log is not None:
        for y, o in rows.items():
            off = BASE + y * ROW + x0
            if bytes(m[off:off + x1 - x0]) != o:
                log.append(("MSYS.DAT", off, o, bytes(m[off:off + x1 - x0]), "appendixgfx.patch"))


def label1(m):
    """GL CARDS (PROMO): G and L kept where they are, CARDS in CV MESSAGE's letters (R: MUSIC ROOM's, scaled to
    their height), (PROMO) in the small font."""
    src = bytes(m)
    gl = {**letter(src, GL_LINE, 6, 20), **letter(src, GL_LINE, 23, 36)}
    canvas = {p: vd for p, vd in gl.items()}
    t, bottom, l, x = box(gl)
    bottom -= 1  # CV letters sit on GL's baseline (GL's fill dips a row lower)
    x += 10
    c, a, s = letter(src, CV_LINE, 8, 20), letter(src, CV_LINE, 96, 105), letter(src, CV_LINE, 76, 84)
    r = scaled(letter(src, MUSIC_LINE, 187, 198), box(a)[1] - box(a)[0] + 1)
    for i, g in enumerate([c, a, r, letter_d(src), s]):
        x = place(canvas, g, x + (4 if i else 0), bottom)
    left, right = box(gl)[3] + 10, x
    small = [letter(src, PAREN_LINE, 86, 97), letter(src, SMALL_LINE, 159, 162), letter(src, SMALL_LINE, 132, 135),
             letter(src, SMALL_LINE, 123, 129), letter(src, SMALL_LINE, 228, 235),
             letter(src, SMALL_LINE, 123, 129), letter(src, PAREN_LINE, 131, 135)]
    width = sum(box(g)[3] - box(g)[2] + 1 for g in small) + 2 * (len(small) - 1)
    x = (left + right - width) // 2  # centred under CARDS (right-aligned, ")" ran into the S)
    for g in small:
        bottom_g = 308 if g is small[0] or g is small[-1] else 307  # parens hang a row below the letters
        x = place(canvas, g, x, bottom_g) + 2
    return canvas


def label2(m):
    """VISUAL ROOM: VISUAL kept, ROOM from MUSIC ROOM on VISUAL's baseline."""
    src = bytes(m)
    vis = letter(src, VISUAL_LINE, 12, 75)
    canvas = dict(vis)
    t, b, l, r = box(vis)
    place(canvas, letter(src, MUSIC_LINE, 187, 236), r + 10, b - 1)
    return canvas


def patch(msys, log=None):
    """Redraw both labels in msys (bytearray, in place); log as insert.log_put (one write per changed row)."""
    c1, c2 = label1(msys), label2(msys)
    write(msys, LABEL1, c1, log)
    write(msys, LABEL2, c2, log)


if __name__ == "__main__":
    import json
    from pathlib import Path

    from PIL import Image
    root = Path(__file__).resolve().parent.parent
    m0 = (root / "work/iso/PSP_GAME/USRDIR/gr_data1/MSYS.DAT").read_bytes()
    m = bytearray(m0)
    patch(m)
    pal = {i: (255 - i, 255 - i, 255 - i) for i in range(256)}
    if len(sys.argv) > 2:  # vote each index's colour from a room screenshot showing OMAKE/1 at 1:1
        sc = Image.open(sys.argv[2]).convert("RGB")
        bg = Counter(sc.getdata()).most_common(1)[0][0]
        y0, y1, x1 = 262, 312, 142
        best = max(((sum((px(m0, y0 + y, x) == 0) == (sc.getpixel((dx + x, dy + y)) == bg)
                         for y in range(0, y1 - y0, 2) for x in range(0, x1, 2)), dx, dy)
                    for dy in range(sc.size[1] - (y1 - y0)) for dx in range(sc.size[0] - x1)))
        votes = {}
        for y in range(y1 - y0):
            for x in range(x1):
                votes.setdefault(px(m0, y0 + y, x), Counter())[sc.getpixel((best[1] + x, best[2] + y))] += 1
        pal.update({i: c.most_common(1)[0][0] for i, c in votes.items()})
        pal[0] = bg
    h = 360 - 255
    img = Image.new("RGB", (2 * 144, h))
    for k, mm in enumerate((m0, m)):
        for y in range(h):
            for x in range(143):
                img.putpixel((k * 144 + x, y), pal.get(px(mm, 255 + y, x), (255, 0, 255)))
    img.resize((img.width * 3, h * 3), Image.NEAREST).save(sys.argv[1])
