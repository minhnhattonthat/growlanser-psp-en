"""dat.py: Growlanser sector archives (SCEN.DAT, MAP.DAT, MAGD.BIN?).

Layout (verified by listing: entries tile the file exactly, see tests/test_dat.py):
  u32 count, then count x (u16 start_sector, u16 n_sectors), sector = 2048 bytes.

    python -X utf8 tools/dat.py FILE            list entries
    python -X utf8 tools/dat.py FILE N OUT      extract entry N
"""
import struct
import sys

SECTOR = 2048


def entries(data):
    count = struct.unpack_from("<I", data, 0)[0]
    return [struct.unpack_from("<HH", data, 4 + 4 * i) for i in range(count)]


def entry(data, i):
    start, n = entries(data)[i]
    return data[start * SECTOR:(start + n) * SECTOR]


def pack(orig, repl):
    """Rebuild orig with entry i replaced by repl[i] (bytes, zero-padded to whole sectors).

    Entries that sit in sequence are laid out again back to back; out-of-sequence empty ones (MAP.DAT's trailing
    (0, 0) records) keep their original record. The header area (up to the first sector in use) is kept as is,
    so pack(orig, {}) == orig."""
    es = entries(orig)
    head = min(s for s, n in es if n) * SECTOR
    out = bytearray(orig[:head])
    pos = opos = head // SECTOR
    for i, (s, n) in enumerate(es):
        if s != opos:
            assert n == 0 and i not in repl, f"entry {i} out of sequence"
            continue
        b = repl.get(i, orig[s * SECTOR:(s + n) * SECTOR])
        b = b + bytes(-len(b) % SECTOR)
        assert pos < 0x10000 and len(b) // SECTOR < 0x10000, "sector field overflow"
        struct.pack_into("<HH", out, 4 + 4 * i, pos, len(b) // SECTOR)
        out += b
        pos += len(b) // SECTOR
        opos = s + n
    return bytes(out)


if __name__ == "__main__":
    data = open(sys.argv[1], "rb").read()
    if len(sys.argv) > 3:
        open(sys.argv[3], "wb").write(entry(data, int(sys.argv[2])))
    else:
        es = entries(data)
        for i, (s, n) in enumerate(es):
            print(i, s, n)
        end = max(s + n for s, n in es)
        print(f"count {len(es)}, last sector end {end}, file sectors {len(data) // SECTOR}")
