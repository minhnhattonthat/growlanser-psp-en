"""warp.py: cold boot -> New Game -> straight into any scene, by name from tools/debug/scenes.txt (docs/re/debug.md).

    python -X utf8 tools/debug/warp.py --scene dbgmenu --out work/qa/warp            one entry, shots + sheet
    python -X utf8 tools/debug/warp.py --scene "scene 42 area 3 sub 0" --out DIR       a raw scene id 0-379
    python -X utf8 tools/debug/warp.py --all --out work/qa/warp [--only a,b]          every entry: DIR/<name>/,
        state work/states/<name>.ppst (DIR/<name>/state.ppst with --iso), asserted landed first, DIR/summary.tsv;
        exit 1 if any entry failed

How (PPSSPP has no Lua; RAM pokes over the debugger WebSocket, debug only, never in a build): the New Game branch at
0x088062E4 stores area 2 / sub 5 into the save block and zeroes the two scene-request halfwords, then the field
loader loads the requested scene. We patch the area/sub immediates in RAM, NOP the two zeroing stores, and hold the
request at the wanted scene until the save block says that scene and map are loaded. Circle picks START on the title.
After landing, ROUTE runs: "FRAMES KEYS" steps split by ";", "6 circle*20" (press, 30 idle, x20), "6 circle*20/60"
(60 idle), "pick N" (cursor down N, then Circle).
"""
import argparse
import base64
import os
import re
import struct
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
from skill import SCRIPTS  # noqa: E402

sys.path.insert(0, SCRIPTS)
import psp  # noqa: E402

ISO = ROOT / "rom" / "Growlanser (Japan).iso"
SCENES = Path(__file__).with_name("scenes.txt")

SAVE = 0x08C8EAB4                    # save block (PS1 0x80196A70)
LOADED = SAVE + 0x30E                # u16 scene now loaded, 0xFFFF none (PS1 +0x2B4)
AREA, SUB = SAVE + 0x314, SAVE + 0x315   # map area / sub (PS1 +0x2BA / +0x2BB)
REQ = (0x08C8D244, 0x08C8F2E8)       # scene request halfwords the field loader reads (PS1 0x80113D62 / 66)
VM_PTR = 0x08C8EE6C                  # event VM script pointer, loaded into s1 before the op read
VM_DISPATCH = 0x08833B2C             # lbu t0, (s1): the VM reads its next op byte
SCENE_PTR = 0x08C8E4A0               # u32 -> loaded SCEN entry N+380 (script + text); moves with entry N's size
JUMP_AFTER = 300                     # frames after landing before a "jump"
HERO_HP = 0x08C588C4                 # u16 hero HP (max HP +2; unit record 0x08C5888C: +0x19 LV, +0x1A AT, +0x1C DF)
HERO_AT = 0x08C5888C + 0x1A
KILL_STEP = 10                       # with "kill F": HP 1 and AT 0 held every this many frames from frame F
TITLE_F = 600                        # the title menu takes input by here (tools/routes/boot.txt)
STEP = 4                             # frames between pokes / landing checks


def new_game_patch(area, sub):
    """[(address, u32)] rewriting the New Game branch (0x088062E4..) for map AREA/SUB, request zeroing NOPed."""
    return [
        (0x088062EC, 0x24020000 + sub),    # addiu v0, zero, SUB  (sb v0, 0x315(a2))
        (0x08806300, 0x24020000 + area),   # addiu v0, zero, AREA (sb v0, 0x314(a2))
        (0x0880630C, 0x24040000 + area),   # addiu a0, zero, AREA (map lookup 0x0882BF70 args)
        (0x08806314, 0x24050000 + sub),    # addiu a1, zero, SUB
        (0x08806320, 0),                   # nop: sh zero, -0x2DBC(v0)  (REQ[0])
        (0x08806328, 0),                   # nop: sh zero, -0xD18(v1)   (REQ[1], jal delay slot)
    ]


def parse_spec(body):
    """'title|scene N [area A sub S] [frames F] [then ROUTE]' -> dict."""
    m = re.match(r"^(.*?)\s+then\s+(.+)$", body)
    head, route = (m.group(1), m.group(2)) if m else (body, None)
    num = lambda k: (lambda x: int(x.group(1)) if x else None)(re.search(k + r"\s+(\d+)", head))
    jump = re.search(r"jump\s+0x([0-9A-Fa-f]+)", head)
    spec = dict(kind=head.split()[0], scene=num("scene"), area=num("area"), sub=num("sub"), frames=num("frames"),
                route=route, jump=int(jump.group(1), 16) if jump else None, kill=num("kill"))
    if spec["kind"] not in ("title", "scene"):
        raise ValueError(f"bad scene spec: {body}")
    spec["area"] = 2 if spec["area"] is None else spec["area"]   # New Game's own map (the moonlit cliff)
    spec["sub"] = 5 if spec["sub"] is None else spec["sub"]
    return spec


def load_scenes(path=SCENES):
    out = {}
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        line = line.split("#")[0].strip()
        if line:
            name, rest = line.split(None, 1)
            out[name] = parse_spec(rest)
    return out


def expand(route):
    """Route text -> [(frames, keys)]."""
    steps = []
    for st in route.split(";"):
        st = st.strip()
        if not st:
            continue
        m = re.match(r"^pick\s+(\d+)$", st)
        if m:
            steps += [(6, {"down"}), (24, set())] * int(m.group(1)) + [(6, {"circle"}), (120, set())]
            continue
        m = re.match(r"^(\d+)\s+([\w+-]+?)(?:\*(\d+)(?:/(\d+))?)?$", st)
        if not m:
            raise ValueError(f"bad route step: {st}")
        n, k = int(m.group(1)), m.group(2)
        keys = set() if k == "-" else set(k.split("+"))
        if keys - psp.BUTTONS:
            raise ValueError(f"unknown button(s) in {st}")
        if m.group(3):
            steps += [(n, keys), (int(m.group(4) or 30), set())] * int(m.group(3))
        else:
            steps.append((n, keys))
    return steps


class Warp:
    def __init__(self, run):
        self.run, self.ws = run, run.ws

    def w32(self, a, v):
        self.ws.call("memory.write", address=a, base64=base64.b64encode(struct.pack("<I", v)).decode())

    def w16(self, a, v):
        self.ws.call("memory.write", address=a, base64=base64.b64encode(struct.pack("<H", v)).decode())

    def u16(self, a):
        return struct.unpack("<H", self.ws.mem(a, 2))[0]

    def u8(self, a):
        return self.ws.mem(a, 1)[0]

    def vm_jump(self, addr, tries=60):
        """Break where the VM reads its next op (s1 = script pointer) and point it at ADDR. Returns the old pointer.
        The VM only runs while a script does (a message waiting for Circle does not), so Circle is tapped meanwhile."""
        ws, run = self.ws, self.run
        ws.call("cpu.breakpoint.add", address=VM_DISPATCH, enabled=True)
        try:
            for i in range(tries):   # 10 frames per try
                run.press({"circle"} if i % 2 else set())
                target = ws.call("cpu.status")["us"] + round(10 * psp.FRAME_US)
                ws.call("cpu.runUntilTime", us=target)
                if ws.wait("cpu.stepping").get("pc") == VM_DISPATCH:
                    break
            else:
                raise RuntimeError("VM dispatcher never reached")
            run.press(set())
            old = ws.call("cpu.getReg", name="s1")["uintValue"]
            ws.call("cpu.setReg", name="s1", value=addr)
            return f"s1 {old:#010x} -> {addr:#010x} at f{self.run.frame()}"
        finally:
            ws.call("cpu.breakpoint.remove", address=VM_DISPATCH)

    def where(self):
        return self.u16(LOADED), self.u8(AREA), self.u8(SUB)


def play(run, steps):
    """Run [(frames, keys)] from the current frame, then release."""
    f = run.frame()
    for n, keys in steps:
        run.press(keys)
        f += n
        run.run_to(f)
    run.press(set())


def warp(spec, out, iso=ISO, frames=None, shot_every=300, state_out=None, log=print, after=None, text=False):
    """Run one warp; returns the landing frame (None if it never landed). Shots f<frame>.png in OUT.
    AFTER(run, warp) runs at the end of a landed run, before the emulator closes (tools/debug/save.py).
    TEXT: log every printed string's hash to OUT/log.txt (tools/debug/textlog.py)."""
    frames = frames or spec["frames"] or 4500
    run = psp.Run(psp.find_emu(None), str(iso), str(out))
    if text:
        import textlog
        textlog.attach(run, out)
    w = Warp(run)
    landed, f = None, 0
    queue = []
    try:
        run.run_to(1)
        if spec["kind"] == "scene":
            for a, v in new_game_patch(spec["area"], spec["sub"]):
                w.w32(a, v)
        target = (spec["scene"], spec["area"], spec["sub"])
        route_queued = booted = False
        while f < frames:
            if not queue:
                if landed is not None and (spec["route"] or spec.get("jump") is not None) and not route_queued:
                    queue, route_queued = expand(spec["route"] or ""), True
                    if spec.get("jump") is not None:   # one handler of the scene's script, without walking there
                        queue = [(JUMP_AFTER, set()), ("jump", None)] + queue
                elif landed is None and f >= TITLE_F and spec["kind"] == "scene":
                    if not booted:   # the cursor starts on LOAD: down, up, up = START (tools/routes/boot.txt)
                        queue, booted = expand("6 down;60 -;6 up;60 -;6 up;60 -"), True
                    queue += [(4, {"circle"}), (26, set())]   # START, then through New Game's lines
                else:
                    queue = [(STEP if landed is None else frames - f, set())]
            n, keys = queue.pop(0)
            if n == "jump":
                base = struct.unpack("<I", w.ws.mem(SCENE_PTR, 4))[0]
                log(f"jump to entry {spec['scene'] + 380}:{spec['jump']:#x}: {w.vm_jump(base + spec['jump'])}")
                f = run.frame()
                continue
            run.press(keys)
            end = min(f + n, frames)
            while f < end:
                nf = min(end, (f // STEP + 1) * STEP) if landed is None else end
                kill = spec.get("kill")
                if kill is not None and landed is not None:
                    if f >= kill:
                        w.w16(HERO_HP, 1)   # the next hit loses the battle
                        w.w16(HERO_AT, 0)   # and the hero can't kill the enemy first
                        nf = min(nf, f + KILL_STEP)
                    else:
                        nf = min(nf, kill)
                if shot_every and nf // shot_every > f // shot_every:
                    nf = nf // shot_every * shot_every
                run.run_to(nf)
                f = nf
                if landed is None:
                    if spec["kind"] == "scene":
                        for a in REQ:
                            w.w16(a, spec["scene"])
                        if w.where() == target:
                            landed = f
                    elif f >= TITLE_F:
                        landed = f
                    if landed is not None:
                        log(f"landed {spec['kind']} {target if spec['kind'] == 'scene' else ''} at f{f}")
                        run.shot(f"land_f{f:06d}.png")
                if shot_every and f % shot_every == 0:
                    run.shot(f"f{f:06d}.png")
        run.press(set())
        run.shot("final.png")
        if state_out and landed is not None:
            run.save_state(str(state_out))
        spec["end_where"] = w.where()
        log(f"end f{f} where={spec['end_where']}")
        if after and landed is not None:
            after(run, w)
    finally:
        run.close()
    return landed


def sheet(out):
    import subprocess
    subprocess.run([sys.executable, "-X", "utf8", os.path.join(SCRIPTS, "sheet.py"), str(out)], check=False,
                   stdout=subprocess.DEVNULL)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--scene", help="name in scenes.txt, or a raw spec 'scene N [area A sub S] [then ROUTE]'")
    ap.add_argument("--all", action="store_true", help="every entry in scenes.txt")
    ap.add_argument("--only", help="with --all: comma-separated names")
    ap.add_argument("--out", required=True)
    ap.add_argument("--iso", default=str(ISO))
    ap.add_argument("--frames", type=int)
    ap.add_argument("--then", help="route after landing (overrides the entry's)")
    ap.add_argument("--shot-every", type=int, default=300)
    ap.add_argument("--state-out")
    ap.add_argument("--no-sheet", action="store_true")
    ap.add_argument("--textlog", action="store_true", help="log printed strings to OUT/<name>/log.txt (textcover)")
    a = ap.parse_args()
    scenes = load_scenes()
    if a.all:
        names = a.only.split(",") if a.only else list(scenes)
        rows, bad = [], 0
        for name in names:
            t0 = time.time()
            out = Path(a.out) / name
            # work/states holds original-ISO states only; a run on another image keeps its states in its out dir
            st = ROOT / "work" / "states" / f"{name}.ppst" if Path(a.iso).resolve() == Path(ISO).resolve() else out / "state.ppst"
            try:
                got = warp(scenes[name], out, a.iso, a.frames, a.shot_every, st, log=lambda s: print(name, s, flush=True),
                           text=a.textlog)
            except (RuntimeError, OSError, EOFError) as e:   # one emulator failure must not stop the batch
                print(name, "error", e, flush=True)
                got = None
            if not a.no_sheet:
                sheet(out)
            bad += got is None
            where = " ".join(map(str, scenes[name].get("end_where", ())))
            rows.append(f"{name}\t{'ok' if got is not None else 'FAIL'}\t{got}\t{where}\t{time.time() - t0:.0f}s")
        summ = Path(a.out, "summary.tsv")   # merged: an --only rerun updates its rows, keeps the others
        old = {r.split("\t")[0]: r for r in summ.read_text(encoding="utf-8").splitlines()[1:]} if summ.exists() else {}
        old.update({r.split("\t")[0]: r for r in rows})
        summ.write_text("name\tresult\tlanded_f\tend scene area sub\ttime\n" + "\n".join(old.values()) + "\n",
                        encoding="utf-8")
        print("\n".join(rows))
        sys.exit(1 if bad else 0)
    if not a.scene:
        ap.error("--scene or --all")
    spec = scenes[a.scene] if a.scene in scenes else parse_spec(a.scene)
    if a.then:
        spec["route"] = a.then
    got = warp(spec, a.out, a.iso, a.frames, a.shot_every, a.state_out, text=a.textlog)
    if not a.no_sheet:
        sheet(a.out)
    sys.exit(0 if got is not None else 1)


if __name__ == "__main__":
    main()
