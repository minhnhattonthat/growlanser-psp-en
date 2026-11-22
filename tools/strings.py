"""strings.py: write build/strings.tsv for $SKILL/scripts/textcover.py (phase 8 text coverage).

    python -X utf8 tools/strings.py [--out build/strings.tsv]

One "id<TAB>hex key" per reachable string. Text moves in RAM with every scene load, so the key is not an address but
a hash of the string's words as the printer reads them: h = (h * 31 + word) mod 2^32 over the words before the first
FFFE/FFFF (port of the PS1 repo's tools/strings.py). tools/debug/textlog.py logs the same hash ("TEXT <hex>") at the
printer entry 0x088748A0 (code pointer = *t3, docs/re/text.md "Printer"). Left out: empty entries, `unref` entries
(no pointer reaches them) and the cstr pools (save.json / kbd.json: the system save dialog and the name-entry grid,
not the printer). Duplicate strings share a key and count together.
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import insert  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent


def key(words):
    h = 0
    for w in words:
        if w in (0xFFFE, 0xFFFF):
            break
        h = (h * 31 + w) % 0x100000000
    return h


def rows(mode="en"):
    enc = insert.Encoder(mode)
    for doc in insert.docs():
        if doc["form"] == "cstr":
            continue
        for e in doc["entries"]:
            if e.get("unref") or not (e["jp"] or e.get("en")):
                continue
            yield e["id"], key(enc.words(e))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default=str(ROOT / "build" / "strings.tsv"))
    ap.add_argument("--mode", default="en", choices=("en", "jp", "marker"))
    a = ap.parse_args()
    assert key([1, 2, 0xFFFE, 9]) == 33 and key([0xFFFF]) == 0
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with open(out, "w", encoding="utf-8", newline="\n") as f:
        for i, k in rows(a.mode):
            f.write(f"{i}\t{k:X}\n")
            n += 1
    print(f"{n} strings -> {out}")


if __name__ == "__main__":
    main()
