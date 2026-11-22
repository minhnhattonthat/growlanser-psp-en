"""credits.py: English staff roll (docs/re/graphics.md P5; D3 credits in English).

The PSP roll is DATA.DAT staff/stf01..07.bmp (512x512, 4bpp BMP, 16-colour palette): each image is
two 256 px strips, scrolled left strip then right strip, stf01 to stf07, as one 256 x 7168 strip (lines straddle the
strip edges, so every edit is made on that whole strip). Index 0 = black, 1-6 = a faint glow (black in stf0N, greys
in the stf0Nb twin, whose indices are otherwise the same), 7-15 = the text ramp. Everything is right-aligned at x 244.
Japanese in it:
  - cast lines "role／actor" (kanji/kana) over a romanized actor line: 11 PSP cast lines (stf01) and the 35 original
    ones (stf04-05). The Japanese line -> the English role (glossary names) in Liberation Sans, right-aligned.
  - song credits: 「Tomorrow」 「Crimson Star」 lose the corner brackets; "Vocal：<name>／<kanji name>" loses the
    kanji; 「リンクシンク」 -> "Link Sync". The kept Latin is shifted right to stay right-aligned.
The P13 MAP.DAT credits pages are the PS1 roll, not drawn on PSP (warp `credits` shows the BMP roll).

    python -X utf8 tools/credits.py OUT.png [Y0 Y1]   the English strip (rows Y0-Y1) beside the original
"""
import io
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage

ROOT = Path(__file__).resolve().parent.parent
FONT = ROOT / "fonts/LiberationSans-Regular.ttf"
RIGHT = 244
PSP_CAST = ["Justin", "Amelia", "Melfie", "Luise", "Wallace", "Richard", "Sandra", "Wenzel", "Soldier", "Featherian",
            "Shop Clerk"]
CAST = ["Tippi", "Luise", "Wallace", "Ariost", "Julian", "Karen", "Elliot", "Misha", "Xenos", "Sandra", "Lyell",
        "Reeves", "Ralph", "Princess Leticia", "King Alcadius", "General Bronson", "General Weber", "Irene", "Berger",
        "Headmaster Maxwell", "Headmaster's Secretary", "Vice Headmaster's Secretary", "Vice Headmaster Bradley",
        "Queen Mother Angela", "Lord Douglas", "Queen Stella", "King of Ranzak", "Bard", "Elliot's Foster Father",
        "Sierra", "Gevel (Monstrosity)", "Gamlan", "Grengal", "Oswald", "Wenzel"]
CAST_ROWS = [((60, 530), PSP_CAST), ((3540, 5010), CAST)]  # strip rows holding each cast list
# Song lines: (rows y0-y1 exclusive, erase x ranges, (x0, x1, dx) Latin moved right, new text or None)
SONGS = [
    ((1865, 1879), [(165, 172), (232, 241)], (172, 232, 13), None),  # 「Tomorrow」
    ((1936, 1950), [(167, 256)], (0, 167, 79), None),  # Vocal：Yukari Tamura／田村ゆかり
    ((2005, 2019), [(144, 151), (232, 241)], (151, 232, 13), None),  # 「Crimson Star」
    ((2062, 2076), [(180, 256)], (0, 180, 66), None),  # Vocal：Maho Tomita／富田麻帆
    ((2118, 2132), [(145, 256)], None, "Link Sync"),  # 「リンクシンク」
    ((2174, 2188), [(180, 256)], (0, 180, 66), None),  # Vocal：Maho Tomita／富田麻帆
]
NAMES = [f"staff/stf{k:02d}{b}.bmp" for k in range(1, 8) for b in ("", "b")]


def bmp(data):
    """4bpp BMP (high nibble = left pixel) -> (top-down indices, pixel offset, height field)."""
    import struct
    off, = struct.unpack_from("<I", data, 10)
    w, h, _, bpp = struct.unpack_from("<iiHH", data, 18)
    assert bpp == 4 and w % 8 == 0, bpp
    p = np.frombuffer(data, np.uint8, abs(h) * w // 2, off).reshape(abs(h), w // 2)
    a = np.empty((abs(h), w), np.uint8)
    a[:, 0::2], a[:, 1::2] = p >> 4, p & 15
    return (a[::-1] if h > 0 else a).copy(), off, h


def pack4(a, h):
    a = a[::-1] if h > 0 else a
    return (a[:, 0::2] << 4 | a[:, 1::2]).astype(np.uint8).tobytes()


def strip(images):
    """[512x512 arrays] (stf01..07) -> the 256 x 7168 roll."""
    return np.vstack([p for a in images for p in (a[:, :256], a[:, 256:])])


def unstrip(g):
    return [np.hstack([g[1024 * k:1024 * k + 512], g[1024 * k + 512:1024 * k + 1024]]) for k in range(7)]


def runs(g, y0, y1):
    """(top, bottom exclusive) of each run of rows with text ink (>= 7) in g[y0:y1]."""
    ink = (g[y0:y1] >= 7).any(1)
    out, y = [], 0
    while y < len(ink):
        if ink[y]:
            s = y
            while y < len(ink) and ink[y]:
                y += 1
            out.append((y0 + s, y0 + y))
        y += 1
    return out


def cast_lines(g, y0, y1):
    """[(jp_top, roman_top)] per cast entry: a 14-row Japanese line (rows top..top+13) over an 11-14 row romanized
    line, either as two runs or merged into one (the romanized line then starts right under the 14 rows)."""
    rs, out, i = runs(g, y0, y1), [], 0
    while i < len(rs):
        s, e = rs[i]
        if e - s >= 22:
            out.append((s, s + 14))
            i += 1
        else:
            assert i + 1 < len(rs) and rs[i + 1][0] - e <= 3 and e - s <= 16, (s, e)
            out.append((s, rs[i + 1][0]))
            i += 2
    return out


def render(text):
    """Text coverage (0-1 floats), cropped to the ink, with the cap top at row 0 of the returned (array, cap_row)."""
    f = ImageFont.truetype(str(FONT), 15)
    w = int(f.getlength(text)) + 8
    im = Image.new("L", (w, 30))
    ImageDraw.Draw(im).text((2, 4), text, font=f, fill=255)
    a = np.asarray(im, float) / 255
    hb = f.getbbox("H")  # cap top relative to the draw origin
    cols = np.nonzero(a.max(0) > 0.05)[0]
    return a[:, cols[0]:cols[-1] + 1], 4 + hb[1]


def indices(cov):
    """Coverage -> the roll's ramp: 7 (48 grey) .. 15 (216); faint edges 4; a glow ring of 2 around the text."""
    v = cov * 216
    idx = np.where(v < 24, 0, np.where(v < 40, 4, np.clip(np.round((v - 48) / 21) + 7, 7, 15))).astype(np.uint8)
    ring = ndimage.binary_dilation(idx >= 7, np.ones((3, 3), bool)) & (idx == 0)
    idx[ring] = 2
    return idx


def put_text(gs, text, cap_top):
    """Draw text right-aligned at RIGHT with its cap top at row cap_top, into every roll in gs."""
    cov, cap = render(text)
    idx = indices(cov)
    y0 = cap_top - cap
    x0 = RIGHT + 1 - idx.shape[1]
    assert x0 >= 4, text
    for g in gs:
        t = g[y0:y0 + idx.shape[0], x0:x0 + idx.shape[1]]
        np.maximum(t, idx, out=t)


def patch_rolls(gs):
    """Edit the rolls (stf0N and stf0Nb, same layout) in place."""
    a = gs[0]
    for (y0, y1), roles in CAST_ROWS:
        lines = cast_lines(a, y0, y1)
        assert len(lines) == len(roles), (y0, len(lines), len(roles))
        for (top, roman), role in zip(lines, roles):
            for g in gs:
                g[top - 1:roman, :256] = 0  # the Japanese line and its glow
            put_text(gs, role, top + 1)
    for (y0, y1), erase, move, text in SONGS:
        # lines overlap by a row or two (descenders of the line above): work on this line's own glyphs only, i.e. the
        # connected components (ink >= 5) whose top row is inside y0..y1, plus their faint 1-px edge
        top = y0 - 4
        lab, n = ndimage.label(a[top:y1 + 2, :256] >= 9, np.ones((3, 3), bool))
        objs = ndimage.find_objects(lab)
        mine = np.zeros(lab.shape, bool)
        for k, sl in enumerate(objs, 1):
            if y0 - 1 <= sl[0].start + top < y1:
                mine |= lab == k
        k3 = np.ones((3, 3), bool)
        others = ndimage.binary_dilation((lab > 0) & ~mine, k3)  # the lines above and below, with their edges
        mine = ndimage.binary_dilation(mine, k3) & ~others & (a[top:y1 + 2, :256] > 0)
        rows = np.arange(lab.shape[0])[:, None] + top
        cols = np.arange(256)
        for g in gs:
            band = g[top:y1 + 2, :256]
            old = band.copy()
            for e0, e1 in erase:
                band[(cols >= e0) & (cols < e1) & (rows >= y0 - 1) & ~others] = 0
            if move:
                x0, x1, dx = move
                sel = mine & (cols >= x0) & (cols < x1)
                band[sel] = 0
                ys, xs = np.nonzero(sel)
                band[ys, xs + dx] = old[ys, xs]
        if text:
            put_text(gs, text, y0 + 1)


def patch(get):
    """get(name) -> original bytes; returns {name: new bytes} for staff/stf01..07(b).bmp."""
    src = {n: get(n) for n in NAMES}
    arrs = {n: bmp(d) for n, d in src.items()}
    gs = [strip([arrs[f"staff/stf{k:02d}{b}.bmp"][0] for k in range(1, 8)]) for b in ("", "b")]
    patch_rolls(gs)
    out = {}
    for b, g in zip(("", "b"), gs):
        for k, img in enumerate(unstrip(g), 1):
            n = f"staff/stf{k:02d}{b}.bmp"
            _, off, h = arrs[n]
            d = bytearray(src[n])
            d[off:off + img.size // 2] = pack4(img, h)
            if bytes(d) != src[n]:
                out[n] = bytes(d)
    return out


if __name__ == "__main__":
    sys.path.insert(0, str(ROOT / "tools"))
    import datadat
    d = (ROOT / "work/iso/PSP_GAME/USRDIR/gr_data1/DATA.DAT").read_bytes()
    old = strip([bmp(datadat.get(d, f"staff/stf{k:02d}.bmp"))[0] for k in range(1, 8)])
    new_files = patch(lambda n: datadat.get(d, n))
    new = strip([bmp(new_files.get(f"staff/stf{k:02d}.bmp") or datadat.get(d, f"staff/stf{k:02d}.bmp"))[0]
                 for k in range(1, 8)])
    y0, y1 = (int(sys.argv[2]), int(sys.argv[3])) if len(sys.argv) > 3 else (0, len(old))
    pal = np.array([0] * 7 + [48, 64, 88, 112, 128, 152, 176, 200, 216], np.uint8)
    Image.fromarray(np.hstack([pal[old[y0:y1]], np.full((y1 - y0, 4), 255, np.uint8), pal[new[y0:y1]]])).save(sys.argv[1])
