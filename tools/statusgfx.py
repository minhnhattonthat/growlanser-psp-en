"""statusgfx.py: English G2 affinity labels and G3 element icons (status screen resistance grid, docs/re/graphics.md).

Texture: MSYS.DAT 0x9100, 4bpp, 128-byte rows (256 px), x 192-239. Labels 24x16 (2 per row, rows 0/16/32: 急所 半減 /
弱点 無効 / 普通 吸収), icons 16x16 (3 per row, rows 46/62/78: 炎 風 聖 / 冷 雷 闇 / 地 物 精). Each cell is redrawn
in its own indices: the background is the original's per-row background, strokes take the original's main stroke
index, a drop shadow (right/below) its edge index. Labels get English words, icons pictograms (16 px holds no word;
D15).

    python -X utf8 tools/statusgfx.py OUT.png     render the redrawn texture beside the original (grey ramp)
"""
import sys

BASE, ROW, X0 = 0x9100, 128, 192

FONT = {  # 7 rows, variable width
    "A": [".#.", "#.#", "#.#", "###", "#.#", "#.#", "#.#"],
    "D": ["##.", "#.#", "#.#", "#.#", "#.#", "#.#", "##."],
    "E": ["###", "#..", "#..", "##.", "#..", "#..", "###"],
    "F": ["###", "#..", "#..", "##.", "#..", "#..", "#.."],
    "H": ["#.#", "#.#", "#.#", "###", "#.#", "#.#", "#.#"],
    "I": ["#"] * 7,
    "K": ["#.#", "#.#", "##.", "#..", "##.", "#.#", "#.#"],
    "L": ["#..", "#..", "#..", "#..", "#..", "#..", "###"],
    "N": ["#..#", "##.#", "##.#", "#.##", "#.##", "#..#", "#..#"],
    "R": ["##.", "#.#", "#.#", "##.", "#.#", "#.#", "#.#"],
    "T": ["###", ".#.", ".#.", ".#.", ".#.", ".#.", ".#."],
    "U": ["#.#", "#.#", "#.#", "#.#", "#.#", "#.#", "###"],
    "V": ["#.#", "#.#", "#.#", "#.#", "#.#", ".#.", ".#."],
    "W": ["#...#", "#...#", "#...#", "#.#.#", "#.#.#", "##.##", "#...#"],
}
LABELS = ["VITAL", "HALF", "WEAK", "NULL", "EVEN", "DRAIN"]  # 急所 半減 弱点 無効 普通 吸収

ICONS = [  # 11x11: fire wind holy / cold thunder dark / earth physical spirit
    [".....#.....", "....##.....", "...###..#..", "...####.#..", "..#####.##.", ".##########",
     ".###.######", "###..#.####", "###.....###", ".###...###.", "..#######.."],
    ["..######...", "........#..", ".#######.#.", ".........#.", "#########..", "...........",
     "..#######..", ".........#.", "...###...#.", "..#...###..", "..#........"],
    [".....#.....", ".....#.....", "....###....", "....###....", "..#######..", "###########",
     "..#######..", "....###....", "....###....", ".....#.....", ".....#....."],
    [".....#.....", ".#..###..#.", "..#..#..#..", "...#.#.#...", "....###....", "###########",
     "....###....", "...#.#.#...", "..#..#..#..", ".#..###..#.", ".....#....."],
    ["......####.", ".....####..", "....####...", "...####....", "..########.", ".......###.",
     "......###..", ".....###...", "....##.....", "...##......", "..#........"],
    ["....#####..", "..#####....", ".####......", ".###.......", "####.......", "####.......",
     "####.......", ".###.......", ".####......", "..#####....", "....#####.."],
    [".....#.....", "....###....", "...#####...", "...######..", "..#######..", ".#########.",
     ".##########", "###########", "###########", "...........", "..........."],
    [".........##", "........###", ".......###.", "......###..", ".#...###...", ".##.###....",
     "..####.....", "...##......", "..####.....", ".##..##....", "##........."],
    ["...#####...", "..#.....#..", ".#..###..#.", "#..#...#..#", "#.#..#..#.#", "#.#.###.#.#",
     "#.#..#..#.#", "#..#...#..#", ".#..###..#.", "..#.....#..", "...#####..."],
]


def get(m, r, x):
    b = m[BASE + r * ROW + x // 2]
    return b >> 4 if x & 1 else b & 15


def put(m, r, x, v):
    o = BASE + r * ROW + x // 2
    m[o] = (m[o] & 0x0F) | v << 4 if x & 1 else (m[o] & 0xF0) | v


def word(text):
    cols = [[] for _ in range(7)]
    for i, ch in enumerate(text):
        for r in range(7):
            cols[r] += list(FONT[ch][r]) + ([] if i == len(text) - 1 else ["."])
    return ["".join(c) for c in cols]


# Label CLUT, read from VRAM (288, 505) on the status screen (work/qa/g2v): index -> luminance, to pick the brightest
# ink of each label (the labels' cyan 無効 matched the screen with this CLUT).
LABEL_LUM = {1: 153, 2: 121, 3: 106, 4: 98, 5: 82, 6: 72, 7: 45, 8: 9, 9: 124, 10: 114, 11: 60, 12: 125, 13: 103,
             14: 128, 15: 96}


def roles(m, rows, cols, label):
    """(background per row, stroke index) of the original cell's text area: a label's brightest ink, an icon's
    darkest (the engraved kanji)."""
    if label:  # plain background 8 (080810); ink = every other index in the area
        ink = {get(m, r, x) for r in rows for x in cols} - {8}
        return {r: 8 for r in rows}, max(ink, key=LABEL_LUM.get)
    # icon CLUT (256, 505): the plate's vertical gradient, the same in all 9 (rows 2-12 of the cell: 3 3 4 4 5 5 6 6 6
    # 6 7; 7-11 are also kanji stroke shades, so it can't be voted per row); 11 = 303030, the darkest stroke
    return {r: GRADIENT[i] for i, r in enumerate(rows)}, 11


GRADIENT = [3, 3, 4, 4, 5, 5, 6, 6, 6, 6, 7]


def draw(m, rows, cols, art, label):
    bg, main = roles(m, rows, cols, label)
    h, w = len(art), len(art[0])
    top = rows[0] + (len(rows) - h) // 2
    left = cols[0] + (len(cols) - w) // 2
    on = {(top + i, left + j) for i in range(h) for j in range(w) if art[i][j] == "#"}
    for r in rows:
        for x in cols:
            put(m, r, x, main if (r, x) in on else bg[r])


def patch(msys, log=None):
    """Redraw the labels and icons in msys (bytearray, in place); log as insert.log_put (one write per row)."""
    old = {r: bytes(msys[BASE + r * ROW + 96:BASE + r * ROW + 120]) for r in range(96)}
    for k, text in enumerate(LABELS):
        r0, x = (k // 2) * 16, X0 + (k % 2) * 24
        draw(msys, list(range(r0 + 1, r0 + 10)), list(range(x + 2, x + 21)), word(text), True)
    for k, art in enumerate(ICONS):
        r0, x = 46 + (k // 3) * 16, X0 + (k % 3) * 16
        draw(msys, list(range(r0 + 2, r0 + 13)), list(range(x + 3, x + 14)), art, False)  # col 2 is frame
    if log is not None:
        for r, o in old.items():
            off = BASE + r * ROW + 96
            new = bytes(msys[off:off + 24])
            if new != o:
                log.append(("MSYS.DAT", off, o, new, "statusgfx.patch"))


if __name__ == "__main__":
    from pathlib import Path

    from PIL import Image
    root = Path(__file__).resolve().parent.parent
    m0 = (root / "work/iso/PSP_GAME/USRDIR/gr_data1/MSYS.DAT").read_bytes()
    m = bytearray(m0)
    patch(m)
    img = Image.new("L", (100, 96))
    for r in range(96):
        for x in range(48):
            img.putpixel((x, r), get(m0, r, X0 + x) * 17)
            img.putpixel((52 + x, r), get(m, r, X0 + x) * 17)
    img.resize((600, 576), Image.NEAREST).save(sys.argv[1])
