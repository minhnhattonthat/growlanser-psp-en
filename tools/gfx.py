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


def png_bytes(im):
    f = io.BytesIO()
    im.save(f, "PNG", optimize=True)
    return f.getvalue()


def icon0(data):
    """P10: ICON0 / GR_SAVE_ICON0 (144x80, parchment): subtitle rows -> parchment 8 rows below."""
    a = np.array(Image.open(io.BytesIO(data)).convert("RGB"))
    a[62:69, 28:73] = a[70:77, 28:73]
    return png_bytes(Image.fromarray(a))


def pic0(data):
    """P10: PIC0 (310x180 RGBA over the XMB): subtitle -> transparent."""
    a = np.array(Image.open(io.BytesIO(data)).convert("RGBA"))
    a[101:116, 72:160] = 0
    return png_bytes(Image.fromarray(a))


def pic1(data):
    """P10: GR_SAVE_PIC1 (480x272 save-screen background): subtitle -> the dark clothes below it."""
    a = np.array(Image.open(io.BytesIO(data)).convert("RGB"))
    m = subtitle_mask(a, (266, 253, 350, 272), k=2)
    fill_down(a, m, 11)
    a[251:254, 268:353] = a[251:254, 365:366]  # the bar's white bottom outline + dark row under it, as right of it
    return png_bytes(Image.fromarray(a))


def sfo_title(data):
    return sfo.set_str(data, "TITLE", "Growlanser")


def apply(flat, edits):
    """Add the graphics edits to build.py's {path: bytes} / {archive path: {entry: bytes}}."""
    g = orig(G + "GLB.DAT")
    ge = {n: g[o:o + s] for n, o, s in glb.entries(g)}
    edits.setdefault(G + "GLB.DAT", {}).update({
        "B99_02_A": title(ge["B99_02_A"]),
        "V49": ge["V41"],  # P12: the 仮 (placeholder) stamp copy of V41
    })
    for arc in (G + "DATA.DAT", U + "DATA_BOOT.DAT"):
        d = orig(arc)
        edits.setdefault(arc, {}).update({
            "GR_SAVE_ICON0.PNG": icon0(datadat.get(d, "GR_SAVE_ICON0.PNG")),
            "GR_SAVE_PIC1.PNG": pic1(datadat.get(d, "GR_SAVE_PIC1.PNG")),
        })
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
