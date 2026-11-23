"""stressrun.py: phase 8 stress routes (references/emulator-qa.md "Stress saves"): cold boot with a stress save, LOAD
slot 1, run one menu route per case, shot every N frames, contact sheet per case.

    python -X utf8 tools/debug/save.py make work/saves/stress_full --warp st_vac07 --stress --set hero_lv=99 ...
    python -X utf8 tools/debug/stressrun.py --sav work/saves/stress_full --out work/qa/stress [--iso X] [--case items]

Cases (field menu: SPELL ITEM EQUIP STATUS TACTICS SYSTEM):
"""
import argparse
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import save as S  # noqa: E402
import warp as W  # noqa: E402

MENU = "300 -;6 triangle;150 -;"  # the field ignores Triangle for a while after LOAD
CASES = {
    "items": MENU + "pick 1;60 -;6 down*420/6",                                      # every list, every row
    "status": MENU + "pick 3;60 -;6 right*6/60;6 circle;60 -;6 down*100/8",           # each unit, spell/skill list
    "spell": MENU + "pick 0;60 -;6 circle;120 -;6 down*40/8;6 cross;60 -;6 down;6 circle;120 -;6 down*40/8",
    "equip": MENU + "pick 2;60 -;6 circle;120 -;6 circle;120 -;6 down*120/6",
    "save": MENU + "pick 5;6 circle;300 -;6 down*15/20",                              # slot names, place, time
}
__doc__ += "".join(f"  {k:7} {v[len(MENU):]}\n" for k, v in CASES.items())


def run_case(sav, out, name, every):
    run, w = S.load(sav, out)
    try:
        if w.where()[0] == 0xFFFF:
            raise SystemExit(f"{name}: save did not load; see {out}/loaded.png")
        f = run.frame()
        for n, keys in W.expand(CASES[name]):
            run.press(keys)
            for g in range(f + 1, f + n + 1):
                if g % every == 0:
                    run.run_to(g)
                    run.shot(f"f{g:06d}.png")
            f += n
            run.run_to(f)
        run.press(set())
        run.shot("final.png")
    finally:
        run.close()


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sav", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--iso", help="default: build/growlanser_en.iso (tour from a copy)")
    ap.add_argument("--case", action="append", choices=list(CASES))
    ap.add_argument("--every", type=int, default=24)
    a = ap.parse_args()
    if a.iso:
        W.ISO = Path(a.iso)
    skill = subprocess.run([sys.executable, "tools/skill.py"], capture_output=True, text=True).stdout.strip()
    for name in a.case or CASES:
        out = Path(a.out) / f"{Path(a.sav).name}_{name}"
        run_case(a.sav, out, name, a.every)
        subprocess.run([sys.executable, "-X", "utf8", f"{skill}/scripts/sheet.py", str(out), "--changed", "0.02",
                        "--out", str(out / "sheet.png")], check=True)
        print(name, "->", out / "sheet.png")


if __name__ == "__main__":
    main()
