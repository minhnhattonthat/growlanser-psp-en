"""Centring check by seed point: flood-fill the box background from a point inside it, take that region's
bounding box (shrunk by 1 px) and run the skill's inkbox.py on it. Saves measuring box edges by hand.

    python -X utf8 tools/inkcheck.py SHOT.png X,Y [X,Y ...] [--tol 2] [--fill 24] [-- inkbox args]

Seed on the box's plain background, not on a letter. --fill = colour distance still counted as background.
Exit = inkbox's exit code (1 off-centre, 2 no ink).
"""
import argparse
import subprocess
import sys
from collections import deque

from PIL import Image

from skill import SKILL


def region(img, seed, fill):
    w, h = img.size
    px = img.load()
    ref = px[seed]
    seen = {seed}
    q = deque([seed])
    x0 = x1 = seed[0]
    y0 = y1 = seed[1]
    while q:
        x, y = q.popleft()
        x0, x1, y0, y1 = min(x0, x), max(x1, x), min(y0, y), max(y1, y)
        for n in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if n in seen or not (0 <= n[0] < w and 0 <= n[1] < h):
                continue
            if max(abs(a - b) for a, b in zip(px[n], ref)) <= fill:
                seen.add(n)
                q.append(n)
    assert len(seen) < w * h // 4, f"seed {seed} leaked out of its box"
    return x0 + 1, y0 + 1, x1 - x0 - 1, y1 - y0 - 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("png")
    ap.add_argument("seeds", nargs="+")
    ap.add_argument("--fill", type=int, default=24)
    ap.add_argument("--tol", default="2")
    a, rest = ap.parse_known_args()
    img = Image.open(a.png).convert("RGB")
    rc = 0
    for s in a.seeds:
        x, y = map(int, s.split(","))
        rect = "%d,%d,%d,%d" % region(img, (x, y), a.fill)
        # gradient boxes: ink = far from the seed colour, so the shading near the border isn't text
        bg = ["--bg", "%d,%d,%d" % img.getpixel((x, y)), "--diff", "64"] if "--ink" not in rest else []
        cmd = [sys.executable, "-X", "utf8", f"{SKILL}/scripts/inkbox.py", a.png, rect, "--tol", a.tol, *bg, *rest]
        rc = max(rc, subprocess.call(cmd))
    return rc


if __name__ == "__main__":
    sys.exit(main())
