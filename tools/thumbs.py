"""thumbs.py: labelled contact sheets of many PNGs (graphics survey review sheets for codex/visual review).

    python -X utf8 tools/thumbs.py OUTDIR PNG.. [--cols 4] [--rows 4] [--scale 0.5]

Writes OUTDIR/0000.png.. and OUTDIR/index.tsv (sheet, slot, file). Each image is scaled by --scale (nearest) and
labelled with its file name.
"""
import argparse
import os

from PIL import Image, ImageDraw


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("pngs", nargs="+")
    ap.add_argument("--cols", type=int, default=4)
    ap.add_argument("--rows", type=int, default=4)
    ap.add_argument("--scale", type=float, default=0.5)
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    ims = []
    for f in a.pngs:
        im = Image.open(f).convert("RGB")
        ims.append((os.path.basename(f), im.resize((max(1, int(im.width * a.scale)), max(1, int(im.height * a.scale))),
                                                     Image.NEAREST)))
    per = a.cols * a.rows
    idx = []
    for k in range(0, len(ims), per):
        chunk = ims[k:k + per]
        cw = max(im.width for _, im in chunk) + 6
        ch = max(im.height for _, im in chunk) + 14
        sheet = Image.new("RGB", (cw * a.cols, ch * a.rows), (40, 40, 40))
        dr = ImageDraw.Draw(sheet)
        for j, (name, im) in enumerate(chunk):
            x, y = j % a.cols * cw, j // a.cols * ch
            sheet.paste(im, (x, y + 12))
            dr.text((x, y), name, fill=(255, 255, 0))
            idx.append((f"{k // per:04d}", str(j), name))
        sheet.save(os.path.join(a.out, f"{k // per:04d}.png"))
    with open(os.path.join(a.out, "index.tsv"), "w", encoding="utf-8") as f:
        f.write("sheet\tslot\tfile\n")
        f.writelines("\t".join(r) + "\n" for r in idx)
    print(len(ims), "images ->", (len(ims) + per - 1) // per, "sheets in", a.out)


if __name__ == "__main__":
    main()
