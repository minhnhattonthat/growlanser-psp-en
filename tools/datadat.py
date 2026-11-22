"""datadat.py: Growlanser PSP named archives (gr_data1/DATA.DAT, DATA_BOOT.DAT).

Layout (verified: offsets ascend and the last entry ends at EOF; first data offset = header end rounded):
  directory of 0x20-byte records: name (NUL-padded, 0x1C bytes) + u32 BIG-endian absolute offset; ends at the first
  record whose name is empty. Entry size = next offset - this offset (the last runs to EOF). Payloads are plain files
  (BMP, PNG, AT3, VAG, .ani, bind.dat).

    python -X utf8 tools/datadat.py list FILE
    python -X utf8 tools/datadat.py x FILE OUTDIR [GLOB]
"""
import fnmatch
import os
import struct
import sys


def entries(d):
    """[(name, offset, size)] in directory order."""
    out, i = [], 0
    while i + 0x20 <= len(d):
        name = d[i:i + 0x1C].split(b"\0")[0]
        if not name or not all(32 < c < 127 for c in name):
            break
        out.append([name.decode("ascii"), struct.unpack_from(">I", d, i + 0x1C)[0]])
        i += 0x20
    for k, e in enumerate(out):
        e.append((out[k + 1][1] if k + 1 < len(out) else len(d)) - e[1])
    return [tuple(e) for e in out]


def get(d, name):
    for n, o, s in entries(d):
        if n == name:
            return d[o:o + s]
    raise KeyError(name)


if __name__ == "__main__":
    cmd, f = sys.argv[1], sys.argv[2]
    d = open(f, "rb").read()
    if cmd == "list":
        for n, o, s in entries(d):
            print(f"{o:#010x} {s:9d} {n}")
    elif cmd == "x":
        out, pat = sys.argv[3], (sys.argv[4] if len(sys.argv) > 4 else "*")
        k = 0
        for n, o, s in entries(d):
            if fnmatch.fnmatch(n, pat):
                p = os.path.join(out, n)
                os.makedirs(os.path.dirname(p), exist_ok=True)
                open(p, "wb").write(d[o:o + s])
                k += 1
        print(f"{k} files -> {out}")
