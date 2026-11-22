"""save.py: build and check edited save data (docs/re/debug.md "Saves"). PSP saves are encrypted by sceSavedata, so
edits go into RAM and the game writes the save itself (its own checksum): no file editing.

    python -X utf8 tools/debug/save.py make OUT (--warp NAME | --sav DIR) [--set FIELD=VALUE ..]
        warp to a scenes.txt entry (ending in the field, menu closed) or load slot 1 of save folder DIR, apply the
        edits, save to slot 1 through the field menu; OUT/ULJM05423GR_DATA is the save (pass OUT to --sav)
    python -X utf8 tools/debug/save.py check DIR [--expect FIELD=VALUE ..]
        cold boot with DIR, LOAD slot 1, assert it reached the field (a scene loaded, no error screen) and every
        expected field reads back; exit 1 otherwise

FIELD: money, hero_lv, hero_hp, hero_maxhp, or ADDR:SIZE (hex RAM address, size 1/2/4), e.g. 08C5AD94:4.
"""
import argparse
import os
import shutil
import struct
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import warp as W  # noqa: E402

psp = W.psp
SAVE_DIR = "ULJM05423GR_DATA"
# money = ELM (0x08CDF410 is only the field menu's display copy)
FIELDS = {"money": (0x08C5AD94, 4), "hero_lv": (0x08C588A5, 1), "hero_hp": (W.HERO_HP, 2),
          "hero_maxhp": (W.HERO_HP + 2, 2)}
# field (menu closed) -> SYSTEM -> SAVE -> slot 1 -> OK (up)
SAVE_ROUTE = "6 triangle;150 -;pick 5;6 circle;300 -;6 circle;200 -;6 up;60 -;6 circle;600 -"
# title (cursor on LOAD when a save exists) -> slot 1 -> OK (up)
LOAD_ROUTE = "650 -;6 circle;300 -;6 circle;200 -;6 up;60 -;6 circle;60 -"
LOAD_FRAMES = 2400


def field(name):
    if name in FIELDS:
        return FIELDS[name]
    a, _, n = name.partition(":")
    return int(a, 16), int(n or 4)


def parse_sets(items):
    out = []
    for it in items or []:
        k, _, v = it.partition("=")
        out.append((k, *field(k), int(v, 0)))
    return out


def read(w, addr, size):
    return int.from_bytes(w.ws.mem(addr, size), "little")


def write(w, addr, size, v):
    import base64
    w.ws.call("memory.write", address=addr, base64=base64.b64encode(v.to_bytes(size, "little")).decode())


def save_and_copy(run, w, sets, out):
    for k, a, n, v in sets:
        write(w, a, n, v)
        print(f"set {k} {a:08X} = {v} (was read back {read(w, a, n)})")
    W.play(run, W.expand(SAVE_ROUTE))
    run.shot("saved.png")
    src = Path(run.ms) / "PSP" / "SAVEDATA" / SAVE_DIR
    if not (src / "DATA.DAT").exists():
        raise SystemExit(f"no save written ({src}); see {run.out}/saved.png")
    dst = Path(out) / SAVE_DIR
    shutil.rmtree(dst, ignore_errors=True)
    shutil.copytree(src, dst)
    print("save ->", dst)


def load(sav, out):
    """Boot with save folder SAV, load slot 1; returns (run, warp) in the field, or raises."""
    ms = Path(out) / "memstick"
    shutil.rmtree(ms, ignore_errors=True)
    psp.seed_saves(str(ms), str(sav))
    run = psp.Run(psp.find_emu(None), str(W.ISO), str(out), memstick=str(ms))
    w = W.Warp(run)
    run.run_to(1)
    W.play(run, W.expand(LOAD_ROUTE))
    f = run.frame()
    while f < LOAD_FRAMES and w.where()[0] == 0xFFFF:
        f += 30
        run.run_to(f)
    run.run_to(f + 120)
    run.shot("loaded.png")
    return run, w


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["make", "check"])
    ap.add_argument("dir", help="make: output folder; check: save folder (holds ULJM05423GR_DATA)")
    ap.add_argument("--warp", help="make: scenes.txt entry to start from")
    ap.add_argument("--sav", help="make: save folder to start from")
    ap.add_argument("--set", action="append", help="FIELD=VALUE")
    ap.add_argument("--expect", action="append", help="check: FIELD=VALUE")
    ap.add_argument("--qa", default="work/qa/save", help="emulator output folder")
    a = ap.parse_args()
    qa = Path(a.qa) / Path(a.dir).name
    if a.cmd == "make":
        sets = parse_sets(a.set)
        if a.warp:
            spec = W.load_scenes()[a.warp]
            got = W.warp(spec, qa, after=lambda run, w: save_and_copy(run, w, sets, a.dir))
            sys.exit(0 if got is not None else 1)
        if not a.sav:
            ap.error("make needs --warp or --sav")
        run, w = load(a.sav, qa)
        try:
            if w.where()[0] == 0xFFFF:
                sys.exit(f"could not load {a.sav}; see {qa}/loaded.png")
            save_and_copy(run, w, sets, a.dir)
        finally:
            run.close()
        return
    run, w = load(a.dir, qa)
    try:
        where, bad = w.where(), 0
        print("loaded scene/area/sub", where, "shot", qa / "loaded.png")
        if where[0] == 0xFFFF:
            print("FAIL: no scene loaded (corrupt or missing save?)")
            bad += 1
        for k, addr, n, v in parse_sets(a.expect):
            got = read(w, addr, n)
            print(f"{k} = {got} (want {v})", "ok" if got == v else "FAIL")
            bad += got != v
        W.play(run, W.expand("6 triangle;150 -"))   # field menu: LV, HP, ELM on screen
        run.shot("menu.png")
    finally:
        run.close()
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
