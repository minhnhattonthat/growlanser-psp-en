"""gfx.py: graphics-text edits for the English build (docs/re/graphics.md P1-P13).

Every edit is computed from the original files at build time (no hand-painted binaries in git): build.py calls
apply(flat, edits) with insert.patched's output and adds the changed archives' entries and flat files.

    python -X utf8 tools/gfx.py preview OUTDIR   # PNGs of every edited image, original | English
"""
import io
import sys
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT))
import datadat  # noqa: E402
import glb  # noqa: E402
from skill import SKILL  # noqa: E402

sys.path.insert(0, str(Path(SKILL) / "scripts"))
import sfo  # noqa: E402

U = "/PSP_GAME/USRDIR/"
G = U + "gr_data1/"


def orig(path):
    import build
    return build.orig(path)


def subtitle_mask(rgb, box, k=4):
    """The red katakana subtitle グローランサー under the logo bar, with its cream outline, inside box (x0, y0, x1, y1)."""
    c = rgb[..., :3].astype(int)
    r, g, b = c[..., 0], c[..., 1], c[..., 2]
    inbox = np.zeros(r.shape, bool)
    x0, y0, x1, y1 = box
    inbox[y0:y1, x0:x1] = True
    red = (r > 0x70) & (g < r * 0.45) & inbox
    m = ndimage.binary_dilation(red, iterations=k) & inbox
    cream = (r > 0xA8) & (g > 0.8 * r) & (b > 0.55 * r)
    return ndimage.binary_dilation(m | (cream & ndimage.binary_dilation(m, iterations=4)), iterations=2) & inbox


def fill_down(a, m, dy):
    """Masked pixels <- the pixel dy rows below (clamped to the image)."""
    ys, xs = np.nonzero(m)
    a[ys, xs] = a[np.minimum(ys + dy, a.shape[0] - 1), xs]


def title(entry):
    """P8: GLB B99_02_A, the whole title screen. Subtitle -> marble from 28 rows below (as the PS1 G1 fill)."""
    pix, pal, _ = glb.decode(entry)
    pix = pix.copy()
    c = glb.rgb(pix, pal).astype(int)
    m = subtitle_mask(c, (33, 96, 198, 124))
    fill_down(pix, m, 28)
    for y in (94, 95):  # the bar's dark shadow rows: subtitle outline tips -> the shadow pixel to the left
        for x in range(33, 198):
            if c[y, x].sum() > 0xC0 or c[y, x, 0] > 0x58:
                pix[y, x] = pix[y, x - 1]
    for x in range(40, 198):  # the bar's cream bottom edge where the subtitle touched it
        if c[93, x, 1] < 0xB0:
            pix[93, x] = pix[93, x - 1]
    return glb.encode(pix, pal)


def lum(pal):
    p = pal.astype(int)
    return (p & 31) * 3 + (p >> 5 & 31) * 6 + (p >> 10 & 31)


TUT_ITEMS = ["boot.items.0022", "boot.items.0108", "boot.items.0160"]  # ウィザードロッド 厚手の服 ミラーピアス
# Grid cells, row-major as in the picture: 急所 半減 急所 / 弱点 普通 弱点 / 普通 吸収 無効 -> statusgfx.LABELS index
TUT_LABELS = [0, 1, 0, 2, 4, 2, 4, 5, 3]


def item_names():
    import json
    d = json.loads((ROOT / "script/boot/items.json").read_text(encoding="utf-8"))
    es = {e["id"]: e for e in (d["entries"] if isinstance(d, dict) else d)}
    return [es[i]["en"] for i in TUT_ITEMS]


def tutorial(entry):
    """P11: GLB B08_01B, the front layer of the magic-class tutorial's status-screen picture (index 0 = colour key,
    B08_01A shows through). Equipment names -> English in the VWF font (ink 242, opaque black shadow 5 right/below,
    as the JP); the resistance grid -> the statusgfx words and pictograms (D15), in each cell's own colours."""
    import enfont
    import statusgfx as sg
    pix, pal, _ = glb.decode(entry)
    pix = pix.copy()
    L = lum(pal)
    font = enfont.load()
    for k, name in enumerate(item_names()):
        top = 193 + 16 * k
        assert (pix[top:top + 13, 128:239] != 0).sum() and not (pix[top:top + 13, 239] == 242).any()
        pix[top:top + 13, 128:239] = 0
        x = 129
        for ch in name:
            t, rows, adv = font[ch]
            for i, row in enumerate(rows):
                for j, v in enumerate(row):
                    if v == "#":
                        y = top + t + i
                        pix[y, x + j] = 242
                        for dy, dx in ((0, 1), (1, 0), (1, 1)):
                            if pix[y + dy, x + j + dx] != 242:
                                pix[y + dy, x + j + dx] = 5
            x += adv
        assert x < 238, name
    # icon plates: rows Y+2..Y+12, cols X+3..X+13; bg per row = the commonest index of that row over the 9 plates,
    # stroke = the darkest index in them (the engraved kanji)
    plates = np.stack([pix[196 + 16 * r + 2:196 + 16 * r + 13, 263 + 56 * c:274 + 56 * c]
                       for r in range(3) for c in range(3)])
    plate_bg = [np.bincount(plates[:, i].ravel(), minlength=256).argmax() for i in range(11)]
    stroke = min(np.unique(plates), key=lambda v: L[v])
    for r in range(3):
        for c in range(3):
            X, Y = 260 + 56 * c, 196 + 16 * r
            # label: dark text box rows Y+2..Y+12, cols X+26..X+45
            a = pix[Y + 2:Y + 13, X + 26:X + 46]
            vals, n = np.unique(a, return_counts=True)
            order = vals[np.argsort(-n)]
            bg, ink = order[0], order[1]  # the box, then the label's main stroke colour
            a[:] = bg
            art = sg.word(sg.LABELS[TUT_LABELS[3 * r + c]])
            h, w = len(art), len(art[0])
            top, left = (a.shape[0] - h) // 2, (a.shape[1] - w) // 2
            for i in range(h):
                for j in range(w):
                    if art[i][j] == "#":
                        a[top + i, left + j] = ink
            art = sg.ICONS[3 * r + c]
            for i in range(11):
                pix[Y + 2 + i, X + 3:X + 14] = plate_bg[i]
                for j in range(11):
                    if art[i][j] == "#":
                        pix[Y + 2 + i, X + 3 + j] = stroke
    return glb.encode(pix, pal)


def bmp_edit(data, fn):
    """Run fn(indices) on an 8bpp BMP's pixels (top-down H x W array, edited in place) and return the BMP bytes with
    only the pixel bytes changed (header, palette and row order kept)."""
    import struct
    b = bytearray(data)
    off, = struct.unpack_from("<I", b, 10)
    w, h, _, bpp = struct.unpack_from("<iiHH", b, 18)
    assert bpp == 8 and w % 4 == 0, (w, bpp)
    a = np.frombuffer(data, np.uint8, abs(h) * w, off).reshape(abs(h), w).copy()
    a = a[::-1].copy() if h > 0 else a
    fn(a)
    b[off:off + a.size] = (a[::-1] if h > 0 else a).tobytes()
    return bytes(b)


def outline_word(a, text, ink, edge):
    """Draw a statusgfx 7-row word centred in a, ink with an 8-neighbour edge outline."""
    import statusgfx as sg
    art = sg.word(text)
    h, w = len(art), len(art[0])
    top, left = (a.shape[0] - h) // 2, (a.shape[1] - w) // 2
    assert top >= 1 and left >= 1, text
    on = np.zeros(a.shape, bool)
    for i in range(h):
        for j in range(w):
            on[top + i, left + j] = art[i][j] == "#"
    a[ndimage.binary_dilation(on, np.ones((3, 3), bool)) & ~on] = edge
    a[on] = ink


def labels_bmp(data):
    """P3: DATA.DAT MESWDA3E.bmp, the status screen's affinity label plates (40x16 each from (0,120): 急所 半減 弱点
    無効 普通 吸収). The text area (rows 122-131, cols 9-31 of each plate) -> the plate's own background, then the D15
    word in the plate's main stroke index with the dark outline index 8, as the JP."""
    import statusgfx as sg

    def fn(a):
        for k, text in enumerate(sg.LABELS):
            t = a[122:132, 40 * k + 9:40 * k + 32]
            vals, n = np.unique(t, return_counts=True)
            ink = next(v for v in vals[np.argsort(-n)] if v not in (2, 8))
            t[:] = 2
            a[132, 40 * k + 9:40 * k + 32] = 4  # the JP glyphs' outline ran into the plate's lower bevel row
            outline_word(t, text, ink, 8)
    return bmp_edit(data, fn)


GLUE = {  # 3x5 letters for the card binder's tiny label
    "G": [".##", "#..", "#.#", "#.#", ".##"], "L": ["#..", "#..", "#..", "#..", "###"],
    "U": ["#.#", "#.#", "#.#", "#.#", "###"], "E": ["###", "#..", "##.", "#..", "###"],
}


def binder(data):
    """P6: DATA.DAT chips/chips01.bmp, the card binder page: the two tiny "のりしろ" (glue margin) labels (4 kana, 5 rows
    high, ~11 px pitch) -> "GLUE" one letter per kana slot, in the labels' own ink, over binder texture from 10 rows
    below."""
    pal = np.array(Image.open(io.BytesIO(data)).getpalette()).reshape(-1, 3).sum(1)

    def fn(a):
        dark = pal[a] < 330
        for x0, x1 in ((70, 140), (168, 238)):
            ys, xs = np.nonzero(dark[84:95, x0:x1])
            assert len(xs) and ys.min() + 84 == 87 and ys.max() + 84 == 91, (x0, len(xs))
            vals, n = np.unique(a[84:95, x0:x1][dark[84:95, x0:x1]], return_counts=True)
            ink = vals[n.argmax()]
            left = x0 + xs.min()
            a[85:94, left - 2:left + 42] = a[95:104, left - 2:left + 42]
            for k, ch in enumerate("GLUE"):
                for i, row in enumerate(GLUE[ch]):
                    for j, v in enumerate(row):
                        if v == "#":
                            a[87 + i, left + 1 + 11 * k + j] = ink
    return bmp_edit(data, fn)


def png_bytes(im, size=None):
    """PNG bytes; with size, padded to exactly size bytes by a tEXt chunk before IEND. DATA.DAT and DATA_BOOT.DAT
    must keep their entry sizes: with a shorter save icon in DATA.DAT the ending's staff roll stayed black (the game
    reaches some entries by fixed offsets, not only through the directory)."""
    import struct
    import zlib
    f = io.BytesIO()
    im.save(f, "PNG", optimize=True)
    b = f.getvalue()
    if size is None:
        return b
    pad = size - len(b) - 12 - len(b"Comment\0")
    assert pad >= 0, (len(b), size)
    body = b"tEXt" + b"Comment\0" + b" " * pad
    chunk = struct.pack(">I", len(body) - 4) + body + struct.pack(">I", zlib.crc32(body))
    out = b[:-12] + chunk + b[-12:]
    assert len(out) == size
    return out


def icon0(data):
    """P10: ICON0 / GR_SAVE_ICON0 (144x80, parchment): subtitle rows -> parchment 8 rows below."""
    a = np.array(Image.open(io.BytesIO(data)).convert("RGB"))
    a[62:69, 28:73] = a[70:77, 28:73]
    return png_bytes(Image.fromarray(a), len(data))


def pic0(data):
    """P10: PIC0 (310x180 RGBA over the XMB): subtitle -> transparent."""
    a = np.array(Image.open(io.BytesIO(data)).convert("RGBA"))
    a[101:116, 72:160] = 0
    return png_bytes(Image.fromarray(a), len(data))


def pic1(data):
    """P10: GR_SAVE_PIC1 (480x272 save-screen background): subtitle -> the dark clothes below it."""
    a = np.array(Image.open(io.BytesIO(data)).convert("RGB"))
    m = subtitle_mask(a, (266, 253, 350, 272), k=2)
    fill_down(a, m, 11)
    a[251:254, 268:353] = a[251:254, 365:366]  # the bar's white bottom outline + dark row under it, as right of it
    return png_bytes(Image.fromarray(a), len(data))


def sfo_title(data):
    return sfo.set_str(data, "TITLE", "Growlanser")


def apply(flat, edits):
    """Add the graphics edits to build.py's {path: bytes} / {archive path: {entry: bytes}}."""
    if G + "MSYS.DAT" in flat:  # P1/P2 status grid: same texture as the PS1 G2/G3, same offset (D15)
        import appendixgfx
        import statusgfx
        m = bytearray(flat[G + "MSYS.DAT"])
        statusgfx.patch(m)
        appendixgfx.patch(m)  # P4: appendix room labels, the PS1 G4 sheet 0x1000 later (D16)
        flat[G + "MSYS.DAT"] = bytes(m)
    g = orig(G + "GLB.DAT")
    ge = {n: g[o:o + s] for n, o, s in glb.entries(g)}
    edits.setdefault(G + "GLB.DAT", {}).update({
        "B99_02_A": title(ge["B99_02_A"]),
        "V49": ge["V41"],  # P12: the 仮 (placeholder) stamp copy of V41
        "B08_01B": tutorial(ge["B08_01B"]),
    })
    for arc in (G + "DATA.DAT", U + "DATA_BOOT.DAT"):
        d = orig(arc)
        edits.setdefault(arc, {}).update({
            "GR_SAVE_ICON0.PNG": icon0(datadat.get(d, "GR_SAVE_ICON0.PNG")),
            "GR_SAVE_PIC1.PNG": pic1(datadat.get(d, "GR_SAVE_PIC1.PNG")),
            "MESWDA3E.bmp": labels_bmp(datadat.get(d, "MESWDA3E.bmp")),
        })
    import credits  # P5: the staff roll
    d = orig(G + "DATA.DAT")
    edits[G + "DATA.DAT"].update(credits.patch(lambda n: datadat.get(d, n)))
    edits[G + "DATA.DAT"]["chips/chips01.bmp"] = binder(datadat.get(d, "chips/chips01.bmp"))
    for arc in (G + "DATA.DAT", U + "DATA_BOOT.DAT"):  # entry sizes must not change (png_bytes)
        d = orig(arc)
        bad = [n for n, b in edits[arc].items() if len(b) != len(datadat.get(d, n))]
        assert not bad, f"{arc}: size changed for {bad}"
    flat.update({
        "/PSP_GAME/ICON0.PNG": icon0(orig("/PSP_GAME/ICON0.PNG")),
        "/PSP_GAME/PIC0.PNG": pic0(orig("/PSP_GAME/PIC0.PNG")),
        U + "GR_SAVE_ICON0.PNG": icon0(orig(U + "GR_SAVE_ICON0.PNG")),
        U + "GR_SAVE_PIC1.PNG": pic1(orig(U + "GR_SAVE_PIC1.PNG")),
        "/PSP_GAME/PARAM.SFO": sfo_title(orig("/PSP_GAME/PARAM.SFO")),
    })
    return flat, edits


def preview(out):
    """original | English side by side for every edited image."""
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    flat, edits = apply({}, {})
    g = orig(G + "GLB.DAT")
    ge = {n: g[o:o + s] for n, o, s in glb.entries(g)}
    pairs = {}
    for n, b in edits[G + "GLB.DAT"].items():
        pairs["glb_" + n] = [Image.fromarray(glb.rgb(*glb.decode(x)[:2])) for x in (ge[n], b)]
    dd = orig(G + "DATA.DAT")
    for n, b in edits[G + "DATA.DAT"].items():
        if n.lower().endswith(".bmp"):
            pairs[Path(n).stem] = [Image.open(io.BytesIO(x)).convert("RGBA") for x in (datadat.get(dd, n), b)]
    for p, b in flat.items():
        if p.endswith(".PNG"):
            pairs[Path(p).stem] = [Image.open(io.BytesIO(x)).convert("RGBA") for x in (orig(p), b)]
    for n, (a, b) in pairs.items():
        im = Image.new("RGBA", (a.width * 2 + 4, a.height), (255, 0, 255, 255))
        im.paste(a, (0, 0))
        im.paste(b, (a.width + 4, 0))
        im.save(out / f"{n}.png")
    print(f"{len(pairs)} previews in {out}")


if __name__ == "__main__":
    if sys.argv[1:2] == ["preview"]:
        preview(sys.argv[2])
    else:
        sys.exit(__doc__)
