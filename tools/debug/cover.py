"""cover.py: text coverage: every printer string of the build through the real printer (port of the PS1 repo's
cover.py + msgforce.lua; PPSSPP has no Lua, so breakpoints over the debugger WebSocket).

    python -X utf8 tools/debug/cover.py [--iso build/growlanser_en.iso] [--out work/qa/cov] [--chunk 2000] [--jobs 3]
        [--only K,K]   (chunk numbers, to rerun)
    then: python -X utf8 $SKILL/scripts/textcover.py work/qa/cov build/strings.tsv --waive docs/text_unshown.tsv

Strings = one per distinct key of tools/strings.py (same words the build writes), split into chunks. Per chunk: warp
`newgame` (scene 0, the host: its first line "This is..." at ~f1800), stage the chunk's strings (each words + FFFE)
in free RAM at STAGE (docs/re/text.md "Free RAM"), then mash Circle with two breakpoints:
- printer entry 0x088748A0: if the code pointer *t3 is outside the stage (a new host message or tag, not a
  continuation of a staged one), point it at the next staged string and log "TEXT <key>" (key hashed from RAM).
- VM dispatcher 0x08833B2C (s1 = next op): the first printer hit fixes LOOP = the op dispatched before it; after
  that every dispatch is sent back to LOOP, so the host's message op repeats for as long as strings remain.
Voice codes are left out of the staged copies (no voice bank in the host: the message never closes); the log gives
the build string's key. A string that never closes (stall: no printer call for STALL frames) ends the run; the next
run of the chunk starts after it (up to --reruns). OUT/c<NN>_r<K>/log.txt per run, OUT/results.tsv per chunk.
"""
import argparse
import base64
import struct
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "tools" / "debug"))
import strings  # noqa: E402
import insert  # noqa: E402
import warp as W  # noqa: E402
import textlog  # noqa: E402
import psp  # noqa: E402  (on sys.path via textlog)

STAGE = 0x09A00000          # free RAM 0x0994E0C0-0x09D40000 (all zero in every dump)
STAGE_END = 0x09D40000
STALL = 900                 # frames with no new staged string = stalled
TAP = (4, 8)                # Circle on, off (frames)
VOICE = 0xF800              # {v:XXXX}


def unvoiced(w):
    """W without voice codes (F800 + id): the host scene has no voice bank loaded and the message waits forever.
    shortcut: the staged copy lacks the voice codes the key was hashed with; the text the printer draws is the same."""
    out, i = [], 0
    while i < len(w):
        if w[i] == VOICE:
            i += 2
            continue
        out.append(w[i])
        i += 1
    return out


def staged_strings():
    """[(key, words incl. FFFE)] one per distinct key, in id order."""
    enc, seen, out = insert.Encoder("en"), set(), []
    for doc in insert.docs():
        if doc["form"] == "cstr":
            continue
        for e in doc["entries"]:
            if e.get("unref") or not (e["jp"] or e.get("en")):
                continue
            w = enc.words(e)
            k = strings.key(w)
            if k not in seen:
                seen.add(k)
                out.append((k, unvoiced([x for x in w if x not in (0xFFFE, 0xFFFF)]) + [0xFFFE]))
    return out


def force(run, chunk, log, frames):
    """Stage CHUNK and force it through the printer; returns (forced count, 'done'|'stalled'|'timeout')."""
    ws = run.ws
    addrs, blob = [], bytearray()
    for _, w in chunk:
        addrs.append(STAGE + len(blob))
        blob += struct.pack(f"<{len(w)}H", *w)
    assert STAGE + len(blob) <= STAGE_END, "chunk too big for the stage"
    for i in range(0, len(blob), 0x8000):
        ws.call("memory.write", address=STAGE + i, base64=base64.b64encode(bytes(blob[i:i + 0x8000])).decode())
    end = STAGE + len(blob)
    ws.call("cpu.breakpoint.add", address=textlog.PRINTER, enabled=True)
    ws.call("cpu.breakpoint.add", address=W.VM_DISPATCH, enabled=True)
    k, loop, last_op, f0 = 0, None, None, run.frame()
    last_new, f = f0, f0
    status = "timeout"
    while f < f0 + frames:
        on, off = TAP
        for n, keys in ((on, {"circle"}), (off, set())):
            run.press(keys)
            target = run.base + round((f + n) * psp.FRAME_US)
            while ws.call("cpu.status")["us"] < target - 100:
                ws.call("cpu.runUntilTime", us=target)
                pc = ws.wait("cpu.stepping").get("pc")
                if pc == W.VM_DISPATCH:
                    s1 = ws.call("cpu.getReg", name="s1")["uintValue"]
                    if loop is not None and s1 != loop:
                        ws.call("cpu.setReg", name="s1", value=loop)
                    last_op = s1
                elif pc == textlog.PRINTER:
                    t3 = ws.call("cpu.getReg", name="t3")["uintValue"]
                    p = struct.unpack("<I", ws.mem(t3, 4))[0]
                    if STAGE <= p < end or k >= len(chunk):
                        continue
                    if loop is None:
                        loop = last_op
                    ws.call("memory.write", address=t3, base64=base64.b64encode(struct.pack("<I", addrs[k])).decode())
                    log.write(f"TEXT {chunk[k][0]:X} f{run.frame()} k={k}\n")
                    log.flush()
                    k, last_new = k + 1, run.frame()
            f += n
        if k >= len(chunk):
            status = "done"
            break
        if f - last_new > STALL:
            status = "stalled"
            break
    for a in (textlog.PRINTER, W.VM_DISPATCH):
        ws.call("cpu.breakpoint.remove", address=a)
    return k, status


def run_chunk(n, chunk, a):
    """All runs of chunk N; returns a results row."""
    start, runs, status = 0, 0, ""
    while start < len(chunk) and runs <= a.reruns:
        out = Path(a.out) / f"c{n:02d}_r{runs}"
        out.mkdir(parents=True, exist_ok=True)
        res = {}

        def after(run, w, start=start, out=out):
            with open(out / "log.txt", "w", encoding="utf-8") as log:
                res["k"], res["status"] = force(run, chunk[start:], log, a.frames)
            run.shot("force_end.png")
        spec = dict(W.load_scenes()["newgame"], route="", frames=a.host_frames)
        try:
            W.warp(spec, out, a.iso, shot_every=0, log=lambda s: None, after=after)
        except (RuntimeError, OSError, EOFError) as e:
            res.setdefault("status", f"error {e}")
        k, status = res.get("k", 0), res.get("status", "nohost")
        print(f"c{n:02d} r{runs}: from {start}, forced {k}, {status}", flush=True)
        runs += 1
        start += k                  # the last forced string is the one that never closed (stall): drawn, skip it
        if status == "done" or k == 0:
            break
    return f"{n}\t{len(chunk)}\t{min(start, len(chunk))}\t{status}\t{runs}"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--iso", default=str(ROOT / "build" / "growlanser_en.iso"))
    ap.add_argument("--out", default=str(ROOT / "work" / "qa" / "cov"))
    ap.add_argument("--chunk", type=int, default=2000)
    ap.add_argument("--jobs", type=int, default=3)
    ap.add_argument("--reruns", type=int, default=10)
    ap.add_argument("--frames", type=int, default=120000, help="forcing frames per run")
    ap.add_argument("--host-frames", type=int, default=1700, help="frames to run the newgame warp before forcing")
    ap.add_argument("--only", help="chunk numbers, comma-separated")
    a = ap.parse_args()
    ss = staged_strings()
    chunks = [ss[i:i + a.chunk] for i in range(0, len(ss), a.chunk)]
    todo = [int(x) for x in a.only.split(",")] if a.only else range(len(chunks))
    print(f"{len(ss)} strings, {len(chunks)} chunks", flush=True)
    t0 = time.time()
    with ThreadPoolExecutor(a.jobs) as ex:
        rows = list(ex.map(lambda n: run_chunk(n, chunks[n], a), todo))
    res = Path(a.out) / "results.tsv"
    old = {r.split("\t")[0]: r for r in res.read_text(encoding="utf-8").splitlines()[1:]} if res.exists() else {}
    old.update({r.split("\t")[0]: r for r in rows})
    res.write_text("chunk\tstrings\treached\tlast status\truns\n" + "\n".join(old.values()) + "\n", encoding="utf-8")
    print("\n".join(rows), f"\n{time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
