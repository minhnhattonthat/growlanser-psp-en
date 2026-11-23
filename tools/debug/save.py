"""save.py: build and check edited save data (docs/re/debug.md "Saves"). PSP saves are encrypted by sceSavedata, so
edits go into RAM and the game writes the save itself (its own checksum): no file editing.

    python -X utf8 tools/debug/save.py make OUT (--warp NAME | --sav DIR) [--set FIELD=VALUE ..]
        warp to a scenes.txt entry (ending in the field, menu closed) or load slot 1 of save folder DIR, apply the
        edits, save to slot 1 through the field menu; OUT/ULJM05423GR_DATA is the save (pass OUT to --sav)
    python -X utf8 tools/debug/save.py make work/saves/clear --clear work/qa/tour/credits/state.ppst
        clear-data save from the end of the `credits` warp (APPENDIX fixture: warp.py --scene title_appendix --sav)
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
# post-credits SAVE list (cursor on slot 1) -> "New save data will be created. Proceed?" -> OK (up)
CLEAR_ROUTE = "6 circle;200 -;6 up;60 -;6 circle;600 -"


# --stress (phase 8 stress saves, docs/re/debug.md "Inventory"): u16 id lists (-1 = empty) per field-menu category,
# list pointers u32 at 0x08958BF8; quantity byte at 0x08CE9ED0 + 2 * id (ids < 325, high byte 0x80 = owned flag);
# counts u16 x5 at 0x08CEA6EA. Category id ranges are read off the item names (script/boot/items.json), not game data.
LISTS = [(0x08CEA15A, 112, [range(0, 110)]), (0x08CEA23A, 52, [range(110, 153)]),
         (0x08CEA2A2, 48, [range(153, 179), range(277, 289)]), (0x08CEA302, 144, [range(179, 246)]),
         (0x08CEA422, 356, [range(246, 277)])]
QTY, COUNTS = 0x08CE9ED0, 0x08CEA6EA


def stress_sets(qty=99, money=999999):
    """(name, addr, size, value) writes: every list filled with its category's ids in order, max money, quantities."""
    out, counts, qb = [("money", *FIELDS["money"], money)], [], bytearray(650)
    for addr, cap, ranges in LISTS:
        ids = [i for r in ranges for i in r][:cap]
        blob = b"".join(i.to_bytes(2, "little") for i in ids) + b"\xff\xff" * (cap - len(ids))
        out.append((f"list {addr:08X}", addr, len(blob), int.from_bytes(blob, "little")))
        counts.append(len(ids))
        for i in ids:
            if i < 325:
                qb[2 * i:2 * i + 2] = bytes([qty, 0x80])
    blob = b"".join(c.to_bytes(2, "little") for c in counts)
    out.append(("counts", COUNTS, len(blob), int.from_bytes(blob, "little")))
    out.append(("qty", QTY, len(qb), int.from_bytes(qb, "little")))
    return out


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
        ok = read(w, a, n) == v
        print(f"set {k} {a:08X}" + (f" = {v}" if n <= 4 else f" ({n} bytes)"), "read back ok" if ok else "READ BACK DIFFERS")
    W.play(run, W.expand(SAVE_ROUTE))
    run.shot("saved.png")
    src = Path(run.ms) / "PSP" / "SAVEDATA" / SAVE_DIR
    if not (src / "DATA.DAT").exists():
        raise SystemExit(f"no save written ({src}); see {run.out}/saved.png")
    dst = Path(out) / SAVE_DIR
    shutil.rmtree(dst, ignore_errors=True)
    shutil.copytree(src, dst)
    print("save ->", dst)


def clear_save(state, out, qa):
    """From the post-credits SAVE screen: slot 1 -> "New save data will be created" -> OK; copy SAVEDATA to OUT."""
    ms = Path(qa) / "memstick"
    shutil.rmtree(ms, ignore_errors=True)
    run = psp.Run(psp.find_emu(None), str(W.ISO), str(qa), state=state, memstick=str(ms))
    try:
        run.run_to(30)
        W.play(run, W.expand(CLEAR_ROUTE))
        run.shot("saved.png")
    finally:
        run.close()
    src = ms / "PSP" / "SAVEDATA"
    dirs = [d for d in src.iterdir() if (d / "PARAM.SFO").exists()] if src.exists() else []
    if not dirs:
        return f"no save written; see {qa}/saved.png"
    shutil.rmtree(out, ignore_errors=True)
    shutil.copytree(src, out)
    print("clear save ->", out, [d.name for d in dirs])
    return 0


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
    ap.add_argument("--stress", action="store_true", help="make: fill every item list, max money and quantities")
    ap.add_argument("--clear", metavar="STATE", help="make: clear-data save from a state on the post-credits SAVE "
                    "screen (the `credits` warp's state.ppst)")
    ap.add_argument("--expect", action="append", help="check: FIELD=VALUE")
    ap.add_argument("--qa", default="work/qa/save", help="emulator output folder")
    a = ap.parse_args()
    qa = Path(a.qa) / Path(a.dir).name
    if a.cmd == "make":
        sets = (stress_sets() if a.stress else []) + parse_sets(a.set)
        if a.warp:
            spec = W.load_scenes()[a.warp]
            got = W.warp(spec, qa, after=lambda run, w: save_and_copy(run, w, sets, a.dir))
            sys.exit(0 if got is not None else 1)
        if a.clear:
            sys.exit(clear_save(a.clear, a.dir, qa))
        if not a.sav:
            ap.error("make needs --warp, --sav or --clear")
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
