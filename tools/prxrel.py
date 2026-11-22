"""prxrel.py: relocation entries of the PSP module (BOOT.BIN, a PRX with SHT 0x700000A0 relocation sections).

    python -X utf8 tools/prxrel.py BOOT.BIN [RAM_ADDR ..]    count by type, or the relocation at each address

The loader adds the load base (0x08804000) at each entry: R_MIPS_26 (type 4) adds base >> 2 to a j/jal's target
field, so a patched word at such a site must stay a j/jal whose target is module-relative (RAM - BASE). Any other
word written there is corrupted at load. asm/vwf.asm and tools/insert.py rely on this (docs/re/build.md "Code hooks").
"""
import collections
import struct
import sys

BASE = 0x08804000


def segments(d):
    phoff, phnum = struct.unpack_from("<I", d, 0x1C)[0], struct.unpack_from("<H", d, 0x2C)[0]
    return [struct.unpack_from("<8I", d, phoff + 32 * i) for i in range(phnum)]  # type, off, vaddr, paddr, filesz..


def relocs(d):
    """{RAM address: type} for every relocation entry."""
    shoff, shnum = struct.unpack_from("<I", d, 0x20)[0], struct.unpack_from("<H", d, 0x30)[0]
    segs = segments(d)
    out = {}
    for i in range(shnum):
        sh = struct.unpack_from("<10I", d, shoff + 40 * i)
        if sh[1] != 0x700000A0:
            continue
        for k in range(sh[5] // 8):
            off, info = struct.unpack_from("<2I", d, sh[4] + 8 * k)
            out[BASE + segs[(info >> 8) & 0xFF][2] + off] = info & 0xFF
    return out


def main():
    d = open(sys.argv[1], "rb").read()
    r = relocs(d)
    if len(sys.argv) == 2:
        print(len(r), "entries:", dict(collections.Counter(r.values())))
    for a in sys.argv[2:]:
        a = int(a, 16)
        print(f"{a:08X}: type {r.get(a, '-')}")


if __name__ == "__main__":
    main()
