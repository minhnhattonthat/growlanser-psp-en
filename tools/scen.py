"""scen.py: text section of a Growlanser SCEN.DAT scene entry (recon; see docs/re/text.md).

Scene entry header: 25 x u32; word 0 = 0x64 (header size), word 22 = offset of the text section.
Text section: u32 size, then u16 offsets (relative to the section start; not sorted, may repeat), then
messages of u16 codes, each ended by 0xFFFE (0xFFFF = empty slot). Returned strings include the terminator. The section is the last thing in the entry; zero padding to the sector follows.

    python -X utf8 tools/scen.py SCEN.DAT      survey every entry, print stats
"""
import struct
import sys

sys.path.insert(0, __import__("os").path.dirname(__file__))
import dat  # noqa: E402


def text_section(e):
    """Return (sec_off, size, offsets) or None when the entry has no text section in this form."""
    if len(e) < 0x64 or struct.unpack_from("<I", e, 0)[0] != 0x64:
        return None
    sec = struct.unpack_from("<I", e, 22 * 4)[0]
    if sec + 4 > len(e):
        return None
    size = struct.unpack_from("<I", e, sec)[0]
    if sec + size > len(e):
        return None
    first = struct.unpack_from("<H", e, sec + 4)[0]
    n = (first - 4) // 2
    offs = list(struct.unpack_from("<%dH" % n, e, sec + 4))
    return sec, size, offs


def strings(e):
    sec, size, offs = text_section(e)
    out = []
    for o in offs:
        p = sec + o
        ws = []
        while True:
            w = struct.unpack_from("<H", e, p)[0]
            p += 2
            ws.append(w)
            if w in (0xFFFE, 0xFFFF):  # FFFE ends a message, FFFF an empty slot
                break
        out.append(ws)
    return out


if __name__ == "__main__":
    data = open(sys.argv[1], "rb").read()
    es = dat.entries(data)
    total = 0
    for i in range(len(es)):
        e = dat.entry(data, i)
        if not e:
            continue
        ts = text_section(e)
        if ts is None:
            print(i, "no text section", e[:8].hex())
            continue
        sec, size, offs = ts
        tail = e[sec + size:]
        print(i, hex(sec), hex(size), len(offs), "tail nonzero" if tail.strip(b"\0") else "")
        total += len(offs)
    print("total strings", total)
