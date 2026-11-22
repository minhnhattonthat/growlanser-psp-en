"""cover_ids.py: which strings a cover.py run stalled on (the last forced string of each stalled run).

    python -X utf8 tools/debug/cover_ids.py [--out work/qa/cov] [--chunk 2000] [N..]    N = staged index (default:
        every stalled run's last string)
"""
import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "tools" / "debug"))
import cover  # noqa: E402
import insert  # noqa: E402
import strings  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default=str(ROOT / "work" / "qa" / "cov"))
    ap.add_argument("--chunk", type=int, default=2000)
    ap.add_argument("n", nargs="*", type=int)
    a = ap.parse_args()
    ss = cover.staged_strings()
    want = a.n
    if not want:
        log = (Path(a.out).parent / "cov.log").read_text(encoding="utf-8")
        for c, st, k in re.findall(r"c(\d+) r\d+: from (\d+), forced (\d+), stalled", log):
            if int(k):
                want.append(int(c) * a.chunk + int(st) + int(k) - 1)
    enc, first = insert.Encoder("en"), {}
    for d in insert.docs():
        if d["form"] == "cstr":
            continue
        for e in d["entries"]:
            first.setdefault(strings.key(enc.words(e)), (e["id"], e.get("en") or e["jp"]))
    for n in want:
        k, w = ss[n]
        i, t = first[k]
        print(f"{n}\t{i}\t{t[:100]!r}")


if __name__ == "__main__":
    main()
