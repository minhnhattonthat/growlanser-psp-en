"""textlog.py: text-coverage log for a PPSSPP run (no Lua on PSP): a breakpoint at the printer entry 0x088748A0,
where *t3 is the code pointer (docs/re/text.md "Printer"); each hit hashes the words up to FFFE/FFFF the way
tools/strings.py keys build/strings.tsv and appends "TEXT <hex> f<frame> p=<ptr>" to OUT/log.txt once per distinct
hash. A call that resumes after a wait code starts mid-string: its suffix hash matches no id (harmless).

    import textlog; textlog.attach(run, out)         # psp.Run: replaces run.run_to with a breakpoint-aware loop
    warp.py --scene X --out D --textlog                # what the tour and the coverage runs use

Report: python -X utf8 $SKILL/scripts/textcover.py work/qa/cov build/strings.tsv --waive docs/text_unshown.tsv
"""
import struct
import sys
import types
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from skill import SCRIPTS  # noqa: E402

sys.path.insert(0, SCRIPTS)
import psp  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from strings import key  # noqa: E402

PRINTER = 0x088748A0
MAX_WORDS = 0x1000


def read_words(ws, p):
    """Words from P up to and including the first FFFE/FFFF (at most MAX_WORDS)."""
    out = []
    while len(out) < MAX_WORDS:
        try:
            b = ws.mem(p + 2 * len(out), 256)
        except RuntimeError:   # ran off valid memory
            return out
        for (w,) in struct.iter_unpack("<H", b):
            out.append(w)
            if w in (0xFFFE, 0xFFFF):
                return out
    return out


def attach(run, out):
    ws, seen = run.ws, set()
    log = open(Path(out) / "log.txt", "a", encoding="utf-8")
    ws.call("cpu.breakpoint.add", address=PRINTER, enabled=True)

    def hit():
        t3 = ws.call("cpu.getReg", name="t3")["uintValue"]
        p = struct.unpack("<I", ws.mem(t3, 4))[0]
        h = key(read_words(ws, p))
        if h not in seen:
            seen.add(h)
            log.write(f"TEXT {h:X} f{run.frame()} p={p:08X}\n")
            log.flush()

    def run_to(self, f):
        target = self.base + round(f * psp.FRAME_US)
        while ws.call("cpu.status")["us"] < target - 100:
            ws.call("cpu.runUntilTime", us=target)
            if ws.wait("cpu.stepping").get("pc") == PRINTER:
                hit()
    run.run_to = types.MethodType(run_to, run)
    return seen
