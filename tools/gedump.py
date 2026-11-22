"""gedump.py: record one GE frame (PPSSPP `gpu.record.dump`) at a frame or savestate, and list the textures it draws.

    python -X utf8 tools/gedump.py ISO --out DIR [--frames N] [--state-in S]

Writes DIR/frame.ppdmp and prints each texture the frame binds (RAM address, format, size). Recon only: finds where
a screen's texture lives in RAM, so the RAM dump (pspdbg.py) can be matched against the archives.
"""
import argparse
import base64
import json
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(__file__))
from pspdbg import open_run, play  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("iso")
    ap.add_argument("--out", required=True)
    ap.add_argument("--frames", type=int, default=0)
    ap.add_argument("--state-in")
    a = ap.parse_args()
    run = open_run(a.iso, a.out, state=a.state_in)
    try:
        play(run, [], a.frames)
        # the dump completes on the next frame: send it, then let the CPU run until the reply comes
        ws = run.ws
        ws.ticket += 1
        t = ws.ticket
        ws._send(1, json.dumps(dict(event="gpu.record.dump", ticket=t)).encode())
        ws.call("cpu.runUntilTime", us=ws.call("cpu.status")["us"] + 200000)
        while True:
            r = ws.events.pop(0) if ws.events else ws.recv()
            if r.get("ticket") == t:
                break
        uri = r.get("uri", "")
        data = base64.b64decode(uri.split(",", 1)[1]) if "," in uri else b""
        path = os.path.join(a.out, "frame.ppdmp")
        open(path, "wb").write(data)
        print(path, len(data), "bytes")
        run.shot("final.png")
        ram = b"".join(ws.mem(0x08800000 + k, 0x100000) for k in range(0, 0x1800000, 0x100000))
    finally:
        run.close()
    for i, (state, tex) in enumerate(textures(data)):
        addr = ram.find(tex[:256]) if len(tex) >= 256 and tex[:256].count(tex[0]) < 256 else -1
        out = os.path.join(a.out, f"tex{i:02d}.bin")
        open(out, "wb").write(tex)
        print(f"tex{i:02d} {len(tex):7d} B  ram {hex(0x08800000 + addr) if addr >= 0 else '?':>10}  {state}")


GE_NAMES = {0xA0: "texaddr", 0xA8: "texbufw", 0xB8: "texsize", 0xC3: "texfmt", 0xC5: "clutfmt", 0xB0: "clutaddr",
            0xB1: "clutaddrhi", 0xC2: "texmode"}


def textures(data):
    """[(register summary, texture bytes)] for each texture upload in a version-6 .ppdmp (PPSSPP GPU/Debugger/Record)."""
    import zstandard
    assert data[:8] == b"PPSSPPGE" and struct.unpack_from("<I", data, 8)[0] >= 6, "need a zstd (v6+) dump"
    count, pushsz = struct.unpack_from("<II", data, 0x18)
    p = 0x20
    dz = zstandard.ZstdDecompressor()
    csz = struct.unpack_from("<I", data, p)[0]
    cmds = dz.decompress(data[p + 4:p + 4 + csz], max_output_size=count * 9)
    p += 4 + csz
    psz = struct.unpack_from("<I", data, p)[0]
    push = dz.decompress(data[p + 4:p + 4 + psz], max_output_size=pushsz)
    regs, out = {}, []
    for k in range(count):
        typ, sz, ptr = struct.unpack_from("<BII", cmds, k * 9)
        if typ == 1:  # REGISTERS: GE command words
            for w in struct.unpack_from(f"<{sz // 4}I", push, ptr):
                if w >> 24 in GE_NAMES:
                    regs[GE_NAMES[w >> 24]] = w & 0xFFFFFF
        elif 0x10 <= typ <= 0x17 and typ == 0x10:  # TEXTURE0 (level 0)
            r = dict(regs)
            r["texsize"] = f"{1 << (r.get('texsize', 0) & 15)}x{1 << (r.get('texsize', 0) >> 8 & 15)}"
            out.append(({k2: (v if isinstance(v, str) else hex(v)) for k2, v in r.items()}, push[ptr:ptr + sz]))
    return out


if __name__ == "__main__":
    main()
