"""stress.py: write a --qa stress file of ruler lines for the width gate (build.py --mode marker --qa-file F --out X).

    python -X utf8 tools/stress.py OUT.tsv ids scen000.0186:4 boot.sys.0121:1:40 ...   rulers into these ids
                                                              (lines, chars per line, default 4 x 80)
    python -X utf8 tools/stress.py OUT.tsv tables [POOL ..]   rulers into every BOOT table entry (minus POOLs,
                                                              default sys dict) + the first 3 MSYS descriptions

Ruler: "A234567890B234567890...H234567890", every character 6 px (font/en12.txt), so character k ends at 6k px; the
engine wraps or the window clips at the budget, read it off a zoomed shot. Other strings of a pool holding a ruler
shrink to their id (insert.marker short), so the ruler fits in place. Port of ../growlanser-en/tools/stress.py.
"""
import glob
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
R = "".join(c + "234567890" for c in "ABCDEFGH")  # 80 chars = 480 px


def ruler(n=1, w=80):
    return "{n}".join([R[:w]] * n)


def tables(skip):
    for f in sorted(glob.glob(str(ROOT / "script/boot/*.json"))) + sorted(glob.glob(str(ROOT / "script/msys/*.json"))):
        doc = json.loads(Path(f).read_text(encoding="utf-8"))
        msys = doc["file"] == "MSYS.DAT"
        if doc["form"] == "cstr" or (not msys and Path(f).stem in skip):
            continue
        for k, e in enumerate(doc["entries"]):
            if e["jp"] and (not msys or k < 3):  # MSYS blocks only hold a few multi-line rulers
                yield e["id"], ruler(4 if msys else 1)


def main(a):
    out, mode, rest = a[0], a[1], a[2:]
    if mode == "ids":
        rows = [(i, ruler(int(n or 4), int(w or 80))) for i, n, w in ((s.split(":") + ["", ""])[:3] for s in rest)]
    else:
        rows = list(tables(set(rest) or {"sys", "dict"}))
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    Path(out).write_text("".join("%s\t%s\n" % r for r in rows), encoding="utf-8", newline="\n")
    print("%d lines -> %s" % (len(rows), out))


if __name__ == "__main__":
    main(sys.argv[1:])
