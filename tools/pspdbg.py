"""pspdbg.py: PPSSPPHeadless helpers on top of the skill's psp.py (boot, route, RAM dump, module list, breakpoints).

    python -X utf8 tools/pspdbg.py dump ISO --out DIR [--route FILE] [--frames N] [--state-in S] [--state-out S]
        runs the route (or N frames), then writes DIR/ram.bin (0x08800000.., 24 MB), DIR/modules.json, DIR/final.png
Library: open_run(iso, out, state=None) -> psp.Run; play(run, steps, frames); dump_ram(run, path); modules(run).
User RAM starts at 0x08800000; the game module (BOOT.BIN/EBOOT, a PRX) loads at the base modules() reports.
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from skill import SCRIPTS  # noqa: E402

sys.path.insert(0, SCRIPTS)
import psp  # noqa: E402

RAM = 0x08800000
RAM_SIZE = 0x01800000


def open_run(iso, out, state=None, memstick=None):
    return psp.Run(psp.find_emu(None), iso, out, state=state, memstick=memstick)


def play(run, steps, frames=0):
    """steps: [(frames, keys)] as psp.parse_route returns; runs them, then idles to `frames` if later."""
    f = run.frame()
    for n, keys in steps:
        run.press(keys)
        f += n
        run.run_to(f)
    run.press(set())
    if frames > f:
        run.run_to(frames)


def dump_ram(run, path, start=RAM, size=RAM_SIZE, chunk=0x100000):
    with open(path, "wb") as fh:
        for a in range(start, start + size, chunk):
            fh.write(run.ws.mem(a, chunk))


def modules(run):
    return run.ws.call("hle.module.list").get("modules", [])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["dump"])
    ap.add_argument("iso")
    ap.add_argument("--out", required=True)
    ap.add_argument("--route")
    ap.add_argument("--frames", type=int, default=0)
    ap.add_argument("--state-in")
    ap.add_argument("--state-out")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    run = open_run(a.iso, a.out, state=a.state_in)
    try:
        steps = psp.parse_route(open(a.route, encoding="utf-8").read()) if a.route else []
        play(run, steps, a.frames)
        run.shot("final.png")
        json.dump(modules(run), open(os.path.join(a.out, "modules.json"), "w"), indent=1)
        dump_ram(run, os.path.join(a.out, "ram.bin"))
        if a.state_out:
            run.save_state(a.state_out)
        print("frame", run.frame(), "->", a.out)
    finally:
        run.close()


if __name__ == "__main__":
    main()
