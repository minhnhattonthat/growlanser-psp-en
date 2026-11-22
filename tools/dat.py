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
