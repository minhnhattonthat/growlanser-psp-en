"""textsec.py: Growlanser string pools (docs/re/text.md), split into strings and rebuilt byte-exact.

Two forms:
  section (SCEN.DAT scene text, MSYS.DAT descriptions): u32 size, u16 byte offsets from the section start
      (count = (first offset - 4) / 2), then the strings back to back up to `size`.
  table (EXE): u16 word offsets at `table`, strings from `base`; string = base + 2 * value.
Strings end with FFFE (message) or FFFF (name / empty slot); F600/F700/F800 take one argument word, which is
skipped when looking for the terminator. Every pointer is kept as (string index, delta in bytes): a few SCEN offsets
point 2 bytes into a string (past a leading FD00).
"""
import struct

ARG1 = (0xF600, 0xF700, 0xF800)
TERMS = (0xFFFE, 0xFFFF)


def split(buf, start, end):
    """Terminated strings (terminator included) tiling buf[start:end]; returns (strings, starts)."""
    out, starts, p = [], [], start
    while p < end:
        starts.append(p)
        ws = []
        while True:
            if p + 2 > end:
                raise ValueError("unterminated string at %X" % starts[-1])
            w = struct.unpack_from("<H", buf, p)[0]
            p += 2
            ws.append(w)
            if w in ARG1:
                ws.append(struct.unpack_from("<H", buf, p)[0])
                p += 2
            elif w in TERMS:
                break
        out.append(ws)
    if p != end:
        raise ValueError("strings overrun %X by %d" % (end, p - end))
    return out, starts


def refs_of(ptrs, starts):
    """Map absolute pointers to (string index, delta)."""
    import bisect
    out = []
    for a in ptrs:
        i = bisect.bisect_right(starts, a) - 1
        if i < 0:
            raise ValueError("pointer %X before the pool" % a)
        out.append((i, a - starts[i]))
    return out


def trailing_pad(strings, refs):
    """Count trailing unreferenced [FFFF] strings (alignment padding)."""
    used = {i for i, _ in refs}
    n = 0
    while len(strings) - n - 1 >= 0 and strings[-n - 1] == [0xFFFF] and len(strings) - n - 1 not in used:
        n += 1
    return n


def read_section(buf, off):
    """-> (strings, refs, pad, size); strings exclude the pad."""
    size, first = struct.unpack_from("<IH", buf, off)
    n = (first - 4) // 2
    offs = struct.unpack_from("<%dH" % n, buf, off + 4)
    strings, starts = split(buf, off + 4 + 2 * n, off + size)
    refs = refs_of([off + o for o in offs], starts)
    pad = trailing_pad(strings, refs)
    return strings[:len(strings) - pad], refs, pad, size


def pad_for(strings, nrefs):
    """The game's padding rule (holds for every original section): at least one FFFF, then to a 4-byte size."""
    size = 4 + 2 * nrefs + 2 * sum(len(s) for s in strings)
    return 1 if size % 4 == 2 else 2


def build_section(strings, refs, pad):
    n = len(refs)
    pos, p = [], 4 + 2 * n
    for s in strings:
        pos.append(p)
        p += 2 * len(s)
    words = [w for s in strings for w in s] + [0xFFFF] * pad
    size = 4 + 2 * n + 2 * len(words)
    offs = [pos[i] + d for i, d in refs]
    if max(offs, default=0) > 0xFFFF:
        raise ValueError("section over 64 KB: u16 offsets overflow")
    return struct.pack("<I%dH%dH" % (n, len(words)), size, *offs, *words)


def read_table(buf, table, base, count, end):
    """-> (strings, refs); strings tile buf[base:end]."""
    vals = struct.unpack_from("<%dH" % count, buf, table)
    strings, starts = split(buf, base, end)
    return strings, refs_of([base + 2 * v for v in vals], starts)


def build_table(strings, refs):
    """-> (table bytes, pool bytes)."""
    pos, p = [], 0
    for s in strings:
        pos.append(p)
        p += len(s)
    vals = [pos[i] + d // 2 for i, d in refs]
    words = [w for s in strings for w in s]
    return struct.pack("<%dH" % len(vals), *vals), struct.pack("<%dH" % len(words), *words)
