"""Centring check for every centred box in warp shots (phase 8 inkbox gate; ported from the PS1 repo).

    python -X utf8 tools/inkqa.py DIR [DIR ..]      (warp.py output folders, --shot-every 20 recommended)

Boxes it finds by colour (within TOL per channel: PSP expands 5-bit colour a step off the PS1 values), one
measurement per distinct box per folder:
  bubble  field-menu bubbles (cream 0xEEDEC5 inside), text = dark ink: inkcheck.py seed flood
  popup   place popup / scene caption (border 0x836252, dark inside), text = 0xC5A473
Animation frames (popup open/close scale) are skipped: a box counts only once it is the same in two frames
in a row. Exit 1 if any box is off-centre by more than 2 px.
"""
import glob
import os
import subprocess
import sys

import numpy as np
from PIL import Image

from skill import SKILL

HERE = os.path.dirname(os.path.abspath(__file__))
CREAM, BORDER, INK = (0xEE, 0xDE, 0xC5), (131, 98, 82), (197, 164, 115)
TOL = 3
# folders whose one-line boxes are not centred text (warp scene name: why)
SKIP = {"tut_status": "P11 tutorial picture of a status screen: left-aligned equipment rows"}


def near(a, c):
    return (np.abs(a.astype(int) - c) <= TOL).all(-1)


def boxes(im):
    W, H = im.size
    a = np.asarray(im)
    px = im.load()
    out = []
    ys, xs = np.nonzero(near(a[:, W // 3:], CREAM))
    if len(xs) > 50:
        out.append(("bubble", (int(xs.min()) + W // 3 + 1, int(ys.min()) + 1)))
    ys, xs = np.nonzero(near(a, INK))
    border = near(a, BORDER)
    if len(xs) > 40:
        y = (int(ys.min()) + int(ys.max())) // 2
        row = xs[ys == y]
        l, r = (int(row.min()), int(row.max())) if len(row) else (int(xs[0]), int(xs[0]))
        while l > 0 and not border[y, l]:
            l -= 1
        while r < W - 1 and not border[y, r]:
            r += 1
        top, bot = y, y
        while top > 0 and not border[top, l + 1] and px[l + 1, top][0] < 120:
            top -= 1
        while bot < H - 1 and not border[bot, l + 1] and px[l + 1, bot][0] < 120:
            bot += 1
        # one-line boxes only: PSP status / item / config windows use the same ink and border but are left-aligned
        if 0 < l and r < W - 1 and r - l < 400 and bot - top < 32:
            out.append(("popup", (l + 1, top + 1, r - l - 1, bot - top - 1)))
    return out


def todo(d):
    """[(kind, frame, geometry)]: bubbles once stable for two frames; popups at the widest frame of each run
    (the open/close animation scales the box, and a popup may be fully open in one 20-frame shot only)."""
    out, seen, prev, run = [], set(), {}, None
    for f in sorted(glob.glob(os.path.join(d, "f*.png"))):
        im = Image.open(f).convert("RGB")
        if im.width < 300:
            continue
        cur = dict(boxes(im))
        g = cur.get("bubble")
        if g and prev.get("bubble") == g and g not in seen:
            seen.add(g)
            out.append(("bubble", f, g))
        g = cur.get("popup")
        if g and (run is None or g[2] > run[2][2]):
            run = ("popup", f, g)
        if not g and run:
            out.append(run)
            run = None
        prev = cur
    return out + ([run] if run else [])


def main(dirs):
    bad = 0
    for d in dirs:
        if os.path.basename(os.path.normpath(d)) in SKIP:
            continue
        for kind, f, geo in todo(d):
            if kind == "bubble":
                cmd = [sys.executable, "-X", "utf8", os.path.join(HERE, "inkcheck.py"), f, "%d,%d" % geo]
            else:
                cmd = [sys.executable, "-X", "utf8", f"{SKILL}/scripts/inkbox.py", f, "%d,%d,%d,%d" % geo,
                       "--ink", "%d,%d,%d" % INK, "--diff", "30"]
            r = subprocess.run(cmd, capture_output=True, text=True)
            bad |= r.returncode == 1
            print(kind, os.path.relpath(f), r.stdout.strip())
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
