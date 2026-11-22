"""elfrefs.py: data addresses built in code of the Growlanser PSP module (BOOT.BIN = decrypted EBOOT, a relocatable
PRX with base 0: .text vaddr 0x24 at file 0xC4, .rodata/.data vaddr = file - 0xA0 / - 0xC0).

Finds `lui rX, hi` followed (within 12 instructions, before rX is rewritten) by `addiu/ori/lw/lh/lhu/sw.. rY, lo(rX)`
and reports hi<<16 + lo. Recon only: relocation tables are the authority for repointing.

    python -X utf8 tools/elfrefs.py ELF [ADDR_HEX ..]     references to each ADDR (vaddr), or a histogram
"""
import struct
import sys

TEXT = (0xC4, 0x10E550)  # file offset, size
TEXT_VADDR = 0x24


def vaddr_of_file(off):
    if off < 0x10F170:
        return off - 0xA0
    return off - 0xC0


def file_of_vaddr(va):
    if va < 0x11D3C0:
        return va + 0xA0
    return va + 0xC0


def refs(d):
    """[(code vaddr of the lui, rX, target address, consumer op)]"""
    off, size = TEXT
    words = struct.unpack_from("<%dI" % (size // 4), d, off)
    out = []
    for i, w in enumerate(words):
        if w >> 26 != 0x0F:  # lui
            continue
        rt = (w >> 16) & 31
        hi = w & 0xFFFF
        for j in range(i + 1, min(i + 13, len(words))):
            x = words[j]
            op = x >> 26
            rs, rt2 = (x >> 21) & 31, (x >> 16) & 31
            if op in (0x09, 0x0D, 0x20, 0x21, 0x23, 0x24, 0x25, 0x28, 0x29, 0x2B) and rs == rt:
                lo = x & 0xFFFF
                if op != 0x0D and lo & 0x8000:
                    lo -= 0x10000
                out.append((TEXT_VADDR + 4 * i, rt, ((hi << 16) + lo) & 0xFFFFFFFF, op))
                if op in (0x09, 0x0D) and rt2 == rt:
                    break
            # rt overwritten by another instruction -> stop
            if op == 0 and ((x >> 11) & 31) == rt and x != 0:
                # addu rX, rX, rI (indexing: the lo offset still applies to hi + index) keeps the chain
                if (x & 0x3F) == 0x21 and (rs == rt or rt2 == rt):
                    continue
                break
            if op in (0x08, 0x09, 0x0A, 0x0B, 0x0C, 0x0D, 0x0E, 0x0F, 0x20, 0x21, 0x23, 0x24, 0x25) and rt2 == rt and rs != rt:
                break
    return out


if __name__ == "__main__":
    d = open(sys.argv[1], "rb").read()
    rs = refs(d)
    if len(sys.argv) > 2:
        for a in sys.argv[2:]:
            t = int(a, 16)
            print(a, [hex(c) for c, _, x, _ in rs if x == t])
    else:
        print(len(rs), "refs")
