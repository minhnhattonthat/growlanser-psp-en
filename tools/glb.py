"""glb.py: Growlanser PSP GLB.DAT (map, battle, event and title backgrounds).

Directory (verified: 1119 named records; offsets ascend, the first equals the directory size 0x41A0):
  14-byte records: name (8 bytes, NUL-padded) + u16 0 + u32 BIG-endian absolute offset. Entry size = next offset -
  this offset. The table has 1200 slots; slots after the last real one hold 0xCD filler.
Image: u8 0x82, u8 tiles across, u8 tiles down, then one byte-RLE stream to the end of the entry
  (c < 0x80: c copies of the next byte; c >= 0x80: c-0x80 literal bytes). Decoded: 0xFE zero bytes, 256 x u16
  palette (ABGR1555, entry 0 = colour key) at 0xFE, then 8bpp 128x128 tiles at 0x2FE, each already in the PSP GE
  swizzled layout, tiles row-major. Verified: decoded B99_02_A (the title screen) = the 12 title textures in RAM
  byte for byte, and its palette = the title CLUT in RAM (work/qa/ge_title, tools/gedump.py).

    python -X utf8 tools/glb.py list GLB.DAT
    python -X utf8 tools/glb.py png GLB.DAT OUTDIR [NAME_GLOB]
"""
import fnmatch
import os
import struct
import sys

import numpy as np

TILE = 128


def entries(d):
    """[(name, offset, size)] for the real records."""
    out, i = [], 0
    first = struct.unpack_from(">I", d, 10)[0]
    while i < first:
        name = d[i:i + 8].split(b"\0")[0]
        off = struct.unpack_from(">I", d, i + 10)[0]
        if not name or not name.isascii() or off >= len(d):
            break
        out.append([name.decode("ascii"), off])
        i += 14
    for k, e in enumerate(out):
        e.append((out[k + 1][1] if k + 1 < len(out) else len(d)) - e[1])
    return [tuple(e) for e in out]


def pack(d, repl):
    """Rebuild d with {name: bytes} swapped in: directory block kept, offsets rewritten, payloads back to back."""
    es = entries(d)
    out = bytearray(d[:es[0][1]])
    for k, (n, o, s) in enumerate(es):
        struct.pack_into(">I", out, k * 14 + 10, len(out))
        out += repl.get(n, d[o:o + s])
    assert not set(repl) - {n for n, _, _ in es}, "unknown names"
    return bytes(out)


def unrle(b):
    out, p = bytearray(), 3
    while p < len(b):
        c = b[p]
        if c < 0x80:
            out += bytes([b[p + 1]]) * c
            p += 2
        else:
            out += b[p + 1:p + c - 0x7F]
            p += c - 0x7F
    return bytes(out)


PAL, PIX = 0xFE, 0x2FE


def unswizzle(t):
    """PSP GE swizzle (16-byte x 8-row blocks) -> row-major, for one TILE x TILE 8bpp tile."""
    return np.frombuffer(t, np.uint8).reshape(TILE // 8, TILE // 16, 8, 16).transpose(0, 2, 1, 3).reshape(TILE, TILE)


def decode(b):
    """-> (indices uint8 HxW, palette uint16[256], decoded stream)."""
    assert b[0] == 0x82, f"not a GLB image (0x{b[0]:02X})"
    tw, th = b[1], b[2]
    u = unrle(b)
    n = tw * th * TILE * TILE
    assert len(u) == PIX + n, (len(u), PIX + n)
    pal = np.frombuffer(u, "<u2", 256, PAL)
    tiles = [unswizzle(u[PIX + k * TILE * TILE:PIX + (k + 1) * TILE * TILE]) for k in range(tw * th)]
    return np.vstack([np.hstack(tiles[r * tw:(r + 1) * tw]) for r in range(th)]), pal, u


def rgb(pix, pal):
    p = pal.astype(np.uint32)
    lut = np.stack([(p & 31) << 3, (p >> 5 & 31) << 3, (p >> 10 & 31) << 3], -1).astype(np.uint8)
    return lut[pix]


if __name__ == "__main__":
    cmd, f = sys.argv[1], sys.argv[2]
    d = open(f, "rb").read()
    if cmd == "list":
        for n, o, s in entries(d):
            print(f"0x{o:08x} {s:8d} {n}  {d[o + 1]}x{d[o + 2]} tiles")
    elif cmd == "png":
        from PIL import Image
        os.makedirs(sys.argv[3], exist_ok=True)
        pat = sys.argv[4] if len(sys.argv) > 4 else "*"
        for n, o, s in entries(d):
            if fnmatch.fnmatch(n, pat):
                pix, pal, u = decode(d[o:o + s])
                Image.fromarray(rgb(pix, pal)).save(os.path.join(sys.argv[3], n + ".png"))
