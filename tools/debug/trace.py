"""trace.py: which code runs, with what registers: breakpoints over the PPSSPP debugger WebSocket (no Lua on PSP).

    python -X utf8 tools/debug/trace.py ISO --state S --bp 08868480,088748A0 [--regs ra,a0,a1] [--route "60 -;6 circle"]
        [--max 200] [--out DIR]

Runs the route (psp.py route syntax, frames from the state), stopping at each breakpoint to log pc + REGS, and prints a
hit count per (pc, first reg) at the end. Recon only (docs/re/text.md "Printer").
"""
import argparse
import collections
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
from skill import SCRIPTS  # noqa: E402

sys.path.insert(0, SCRIPTS)
import psp  # noqa: E402


def trace(run, bps, regs, steps, cap):
    ws = run.ws
    for a in bps:
        ws.call("cpu.breakpoint.add", address=a, enabled=True)
    hits, f = [], run.frame()
    for n, keys in steps:
        run.press(keys)
        f += n
        target = run.base + round(f * psp.FRAME_US)
        while ws.call("cpu.status")["us"] < target - 100:
            ws.call("cpu.runUntilTime", us=target)
            pc = ws.wait("cpu.stepping").get("pc")
            if pc in bps and len(hits) < cap:
                hits.append((run.frame(), pc, [ws.call("cpu.getReg", name=r)["uintValue"] for r in regs]))
                if len(hits) == cap:
                    for a in bps:
                        ws.call("cpu.breakpoint.remove", address=a)
    return hits


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("iso")
    ap.add_argument("--state")
    ap.add_argument("--bp", required=True)
    ap.add_argument("--regs", default="ra")
    ap.add_argument("--route", default="60 -")
    ap.add_argument("--max", type=int, default=300)
    ap.add_argument("--out", default="work/qa/trace")
    a = ap.parse_args()
    bps = [int(x, 16) for x in a.bp.split(",")]
    regs = a.regs.split(",")
    run = psp.Run(psp.find_emu(None), a.iso, a.out, state=a.state)
    try:
        hits = trace(run, bps, regs, psp.parse_route(a.route), a.max)
        run.shot("final.png")
    finally:
        run.close()
    for fr, pc, rv in hits:
        print(f"f{fr} {pc:08X} " + " ".join(f"{r}={v:08X}" for r, v in zip(regs, rv)))
    c = collections.Counter((pc, rv[0]) for _, pc, rv in hits)
    print("--- counts (pc, %s)" % regs[0])
    for (pc, r0), n in sorted(c.items()):
        print(f"{pc:08X} {r0:08X} x{n}")


if __name__ == "__main__":
    main()
