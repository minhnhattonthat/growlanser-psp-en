"""insert.py: script/*.json -> patched game files, and asm/vwf.asm into BOOT.BIN (armips), for build.py.

    python -X utf8 tools/insert.py --check       hook sites, free space, relocations, marker sizes (no build)

Modes: "jp" (original text through our encoder: must give the original bytes), "marker" (every Japanese string
becomes "[id] The quick brown fox..." in English pairs, same word count as the Japanese, so every pool is written in
place), "en" (English where script has it, Japanese elsewhere; phase 7 adds fitting and relocation).
Pair codes: tools/enfont.py (PAIR 0x800 + i << 7 + j), drawn by asm/vwf.asm.
"""
import json
import re
import shutil
import struct
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import dat  # noqa: E402
import enfont  # noqa: E402
import extract  # noqa: E402
import fit  # noqa: E402
import gltext  # noqa: E402
import prxrel  # noqa: E402
import romdiff  # noqa: E402
import textsec  # noqa: E402

ARMIPS = ROOT / "tools" / "armips" / "armips.exe"
TEXT_HS, DATA_HS = 0x08803F60, 0x08803F40  # RAM - BOOT.BIN offset for .text/.rodata and .data (docs/re/text.md)
DATA_FILE = 0x11D480  # first .data byte in BOOT.BIN

# asm/vwf.asm fixed sites: RAM address -> the original bytes its .org overwrites (pinned from the rom.sha1 BOOT.BIN).
HOOKS = {
    0x0887501C: "05cb010c", 0x08875030: "0100d626",  # glyph call (row s5) + s6 step
    0x088750F8: "05cb010c", 0x0887510C: "0100d626",  # glyph call (row s5 + 1) + s6 step
    0x08874CE0: "17cc010c", 0x08874CF0: "0200d626",  # double-size glyph call + s6 step
    0x08869BCC: "3c034412", 0x08869DCC: "db024412",  # typewriter tests
    0x088677F4: "01003126758d0108", 0x08867A58: "02003126758d0108",  # pre-parser column step + loop jump
    0x088748A0: "80ffbd275000b0af",  # printer entry: new-string flag
    0x08871BFC: "23206500c21704002110440043a80200", 0x08871C98: "23184300",  # popup frame = pixel width
}
_ASM = (ROOT / "asm" / "vwf.asm").read_text(encoding="utf-8")
FREE_ASM = tuple(int(re.search(r"^%s\s+equ\s+(0x[0-9A-Fa-f]+)" % k, _ASM, re.M).group(1), 16) - DATA_HS
                 for k in ("FREE_START", "FREE_END"))  # BOOT.BIN offsets of vwf.asm's code + font tables
# Page-path callers of the print wrapper (return addresses): a print from there continues a message (vwf_newstr).
# 0x0886AAB4: the message display's only wrapper call (trace.py on a wait-code ruler, work/qa/s3/wait: without it the
# pen restarted at ceil(x/12) after a wait, a 6 px gap)
GEN_DEFAULT = {"CONT_RA1": 0x0886AAB4, "CONT_RA2": 0}

KEEP_JP = {"boot.sys.%04d" % i for i in range(5)}  # single punctuation / blanks (PS1 exe.sys 0-4: kinsoku data)
# Name-entry key grids, one code per key (the key's code is what the name gets): D10 (= PS1 D14)
KEEP_JP |= {"boot.sys.%04d" % i for i in range(70, 100)}
# Default names ＰＬＡＹＥＲ / ＭＹ ＣＩＴＹ: the name field takes one code per cell (D10 = PS1 D17/D18)
KEEP_JP |= {"boot.names.0000", "boot.units.0000", "boot.names.0014", "boot.units.0014"}
KEEP_POOLS = ("boot.kbd.", "boot.dict.")  # name-entry key grids (one code per key, PS1 D14); dictionary (English
# spells words out, the F4xx codes are dropped)
# Fitting (PS1 insert.py; docs/windows.md): fit.BUDGETS rows whose frame is 12 px x code count
TAG_POOLS = ("scen.name", "boot.names", "boot.places", "boot.items")  # items: the description's name tag
# Scene captions ("　The next day　"): code-count frame; text starts 15 px in (blank incl.), ink ends 4 px before
# the last advance (PS1 measure; PSP caption not reached yet: docs/windows.md)
CAPTION_BIAS = 11
# boot.sys.0069 (name-entry title + labels) is one line cut into pixel slices: title 60, blank 12, 5 labels x 24
# (measured, work/qa/s4/name_entry). English: "Title　Label Label ..", each field centred in its slice.
SLOTS = {"boot.sys.0069": (60, 12, 24, 24, 24, 24, 24)}


def is_caption(e):
    j = e["jp"]
    return len(j) > 2 and j[0] == j[-1] == "　" and "{" not in j and "{" not in e.get("en", "")


def is_title(e):
    """A scene string shown alone in a popup: place or event name (one line, no codes, no sentence punctuation,
    not a choice); its box is sized to the text in whole columns (Encoder.title_lead)."""
    return bool(e["jp"]) and "{" not in e["jp"] + e.get("en", "") and not e["jp"].startswith("　") \
        and not re.search("[。！？‥、「」…・]", e["jp"]) and not is_caption(e)


FILLER = "The quick brown fox jumps over the lazy dog. "
TEXT_RUN = re.compile(r"(\{\w+(?::[0-9A-Fa-f]{4})?\}|\[[0-9A-Fa-f]{4}\])")


def ram_to_file(a):
    return a - (DATA_HS if a - DATA_HS >= DATA_FILE else TEXT_HS)


def short_id(eid):
    pool, _, n = eid.rpartition(".")
    m = re.fullmatch(r"scen(\d+)", pool)
    return "%d.%d" % (int(m.group(1)), int(n)) if m else "%s%d" % (pool.split(".")[-1][:2], int(n))


def marker(e, short=False):
    """Same word count as the jp: each text run becomes exactly 2 letters per Japanese character; a leading ・ stays.
    Dictionary codes {F4xx} are dropped (English spells words out), so a pool never grows. short: only the id (and
    empty runs after it), to free pool room for a --qa ruler."""
    out, first = [], True
    for part in TEXT_RUN.split(re.sub(r"\{F4[0-9A-F]{2}\}", "", e["jp"])):
        if not part or TEXT_RUN.fullmatch(part):
            out.append(part)
            continue
        lead = "・" if part.startswith("・") else ""
        n = 2 * (len(part) - len(lead))
        txt = (short_id(e["id"]) + " ") if first else ""
        n = min(n, max(0, len(txt) - 1)) if short else n
        first = False
        txt += (FILLER * (n // len(FILLER) + 1))[:max(0, n - len(txt))]
        out.append(lead + txt[:n])  # a short string keeps only the id's head
    return "".join(out)


def keep_jp(e):
    return e["id"] in KEEP_JP or e["id"].startswith(KEEP_POOLS)


def needs_english(e):
    """Nonempty JP with no English and no keep-JP exemption (batches.py)."""
    return bool(e.get("jp")) and not e.get("en") and not keep_jp(e)


class Encoder:
    def __init__(self, mode, overrides=None):
        assert mode in ("jp", "marker", "en")
        self.mode, self.jp, self.en, self.font = mode, gltext.Codec(), enfont.EnCodec(), enfont.load()
        self.overrides, self.squeeze = overrides or {}, False

    def text(self, e):
        """The string to write, or None to keep the Japanese."""
        if e["id"] in self.overrides:
            return self.overrides[e["id"]]
        if self.mode == "jp" or not e["jp"] or keep_jp(e):
            return None
        if self.mode == "marker":
            return marker(e, self.squeeze)
        return e.get("en") or None

    def words(self, e):
        t = self.text(e)
        if t is None:
            return self.jp.encode(e["jp"])
        if self.mode != "en" or e["id"] in self.overrides:
            return self.en.encode(t)
        pool = fit.budget(e["id"], e)[0]
        if pool == "scen" and is_caption(e):
            return self.centre(t, CAPTION_BIAS)
        if e["id"] in SLOTS:
            return self.slots(e["id"], t)
        w = self.en.encode(t)
        if pool in TAG_POOLS:
            return self.tag_pad(w)
        return self.title_lead(w) if pool == "scen" and is_title(e) else w

    # Fitting, ported from the PS1 insert.Encoder (same engine; docs/windows.md)
    def advance(self, w):
        if enfont.PAIR <= w < enfont.PAIR + 0x4000:
            return sum(self.font[self.en.rev[k]][2] for k in (w - enfont.PAIR >> 7, w & 0x7F) if k)
        return 12 if w < 0xE000 else 0

    def tag_pad(self, words):
        """Name tags are as many columns wide as their codes, and the printer draws a code only if its column
        ceil(x / 12) is inside: append zero-width codes (pair 0x0800 draws nothing) up to last column + 1."""
        x, need = 0, len(words)
        for w in words:
            need = max(need, -(-x // 12) + 1)
            x += self.advance(w)
        return words + [enfont.PAIR] * (need - len(words))

    def slots(self, eid, text):
        title, rest = text.split("　")
        fields, widths = [title, ""] + rest.split(" "), SLOTS[eid]
        if len(fields) != len(widths):
            raise ValueError(f"{eid}: {len(fields)} fields, the screen has {len(widths)} slices")

        def blank(n):
            sp = {v: k for k, v in enfont.SPACERS.items()}
            return sp[11] * (n // 11) + (sp[n % 11] if n % 11 else "")
        out = ""
        for f, w in zip(fields, widths):
            free = w - enfont.width(f, self.font)
            if free < 0:
                raise ValueError(f"{eid}: {f!r} is {-free} px wider than its {w} px slice")
            out += blank(free // 2) + f + blank(free - free // 2)
        return self.en.encode(out)

    def centre(self, text, bias):
        """The frame is 12 px x code count and the text starts near its left edge: lead with spacer glyphs (after
        any leading full-width blank) so the blank on the left matches the one on the right; bias = how much more
        blank the left side has than the model's. Never more codes than max(plain, 12)."""
        sp = list(enfont.SPACERS)
        leads = [""] + sp + [sp[-1] + s for s in sp]
        head = text[:len(text) - len(text.lstrip("　"))]
        cap = max(len(self.en.encode(text)), 12)
        best = None
        for lead in leads:
            w = self.en.encode(head + lead + text[len(head):])
            left = sum(enfont.SPACERS[c] for c in lead) + bias
            right = 12 * len(w) - sum(map(self.advance, w))
            key = (abs(left - right), len(w))
            if len(w) <= cap and (best is None or key < best[0]):
                best = key, w
        return best[1]

    def title_lead(self, w):
        """Title popups (place / event names) are sized to whole 12 px columns, ceil(width / 12), with the text at
        the left: lead with a spacer of half the slack so it sits centred."""
        width = sum(map(self.advance, w))
        lead = (-(-width // 12) * 12 - width) // 2
        return self.en.encode(chr(0xE000 + lead)) + w if lead else w

    def cstr(self, e):
        t = self.text(e)
        if t is None:
            return extract.cstr_bytes(e)
        if self.mode == "marker" and e["id"] not in self.overrides:
            t = t.replace("・", "")[:len(e["jp"].encode(e["enc"]))]  # ASCII, no longer than the Japanese bytes
        return extract.cstr_bytes({**e, "en": t}, "en")

    def strings(self, doc):
        return [self.words(e) + [extract.TERM_W[e["term"]]] for e in doc["entries"]]

    def pool(self, doc):
        """New bytes for a pool, in place: section bytes, (table, pool bytes) or [cstr slots]. A pool holding a --qa
        override gets short markers elsewhere, so the override has room."""
        self.squeeze = any(e["id"] in self.overrides for e in doc["entries"])
        if doc["form"] == "cstr":
            return [self.cstr(e) for e in doc["entries"]]
        strings = self.strings(doc)
        refs = extract._refs_parse(doc["refs"])
        if doc["form"] == "section":
            pad = doc["pad"] if self.mode == "jp" else textsec.pad_for(strings, len(refs))
            return textsec.build_section(strings, refs, pad)
        table, pool = textsec.build_table(strings, refs)
        return table, pool + b"\0\0" * doc["fill"]


def docs():
    for path in sorted((ROOT / "script").glob("*/*.json")):
        yield json.loads(path.read_text(encoding="utf-8"))


def put(buf, at, new, old_len, what):
    if len(new) > old_len:
        raise ValueError(f"{what}: {len(new)} bytes > {old_len} in place (relocation is phase 7)")
    buf[at:at + old_len] = new + bytes(old_len - len(new))


FONT = 0x1230D8  # BOOT.BIN game font, 18 bytes per glyph cell
# BOOT string tables outside jp mode (PS1 insert.Heap): every string goes to a heap made of the tables' original pools
# plus free kanji cells; each table keeps its u16 array, and its getters' pool base (an addiu lo16) moves to HEAP_RAM,
# so a string may sit anywhere in [HEAP_RAM, HEAP_RAM + 128 KB). HEAP_RAM keeps the lui half (0x0893) of every
# original base, so only addiu immediates change (no HI16 carry change for the PRX loader).
HEAP_RAM = 0x0892C000
# Kanji cells from HEAP_RAM up to vwf.asm (0x6A0), minus icon cells (PS1 list: 0530 heart, 0571 0643 0644 buttons).
# Cells English still draws (raw codes / kept JP: 01BE 01C2 0298 02A4) are all below 0x471.
FONT_FREE = [(0x471, 0x530), (0x531, 0x571), (0x572, 0x643), (0x645, 0x6A0)]
DATA_SEG = DATA_FILE + DATA_HS  # RAM of .data: lui/addiu immediates of .data addresses hold RAM - DATA_SEG


def file_to_ram(o):
    return o + (DATA_HS if o >= DATA_FILE else TEXT_HS)


class Heap:
    """First-fit string space; identical strings are stored once."""

    def __init__(self, pools):
        self.ranges = sorted(pools + [(FONT + 18 * a, FONT + 18 * b) for a, b in FONT_FREE])
        assert self.ranges[0][0] >= ram_to_file(HEAP_RAM)
        self.free, self.placed = list(self.ranges), {}

    def put(self, blob):
        if blob in self.placed:
            return self.placed[blob]
        for k, (s, e) in enumerate(self.free):
            if e - s >= len(blob):
                self.free[k] = (s + len(blob), e)
                self.placed[blob] = s
                return s
        raise ValueError("BOOT string heap full (%d bytes)" % len(blob))


def repoint(boot, old_ram, new_ram):
    """Rewrite every `lui r, hi` .. `addiu r', r, lo` in .text that builds old_ram (a .data address, stored
    segment-relative) to build new_ram; the lui half must stay the same. Returns the sites (file offsets)."""
    old, new = old_ram - DATA_SEG, new_ram - DATA_SEG
    lui, n = {}, []
    for o in range(0xC4, DATA_FILE, 4):
        w = struct.unpack_from("<I", boot, o)[0]
        op, rs, rt, imm = w >> 26, (w >> 21) & 31, (w >> 16) & 31, w & 0xFFFF
        if op == 0x0F:  # lui
            lui[rt] = imm
        elif op == 0x09 and rs in lui and (lui[rs] << 16) + imm - (imm & 0x8000) * 2 == old:
            if (new + 0x8000) >> 16 != lui[rs]:
                raise ValueError("0x%08X: new base 0x%08X needs another lui half" % (file_to_ram(o), new_ram))
            struct.pack_into("<I", boot, o, (w & 0xFFFF0000) | (new & 0xFFFF))
            n.append(o)
    return n


def heap_tables(boot, enc, docs):
    """Write the BOOT table docs' strings into one Heap, rebuild their u16 arrays in place, repoint the getters."""
    heap = Heap([(int(d["base"], 16), int(d["table"], 16)) for d in docs])
    rel = prxrel.relocs(boot)
    for s, e in heap.ranges:
        if any(file_to_ram(s) - 4 < a < file_to_ram(e) for a in rel):
            raise ValueError("PRX relocation inside heap range 0x%X-0x%X" % (s, e))
        boot[s:e] = bytes(e - s)
    base = ram_to_file(HEAP_RAM)
    heap.spans = list(heap.ranges)  # every byte heap_tables may write, for the romdiff gate
    for doc in docs:
        enc.squeeze = any(e["id"] in enc.overrides for e in doc["entries"])
        addr = []
        for s in enc.strings(doc):
            blob = struct.pack("<%dH" % len(s), *s)
            addr.append(heap.put(blob))
            boot[addr[-1]:addr[-1] + len(blob)] = blob
        vals = [(addr[i] - base + d) // 2 for i, d in extract._refs_parse(doc["refs"])]
        table = struct.pack("<%dH" % len(vals), *vals)  # struct fails past 0xFFFF words (128 KB)
        t = int(doc["table"], 16)
        put(boot, t, table, len(table), doc["entries"][0]["id"] + " table")
        sites = repoint(boot, file_to_ram(int(doc["base"], 16)), HEAP_RAM)
        if not sites:
            raise ValueError("%s: no getter builds pool base %s" % (doc["entries"][0]["id"], doc["base"]))
        heap.spans += [(t, t + len(table))] + [(o, o + 4) for o in sites]
    return heap


# Load buffers moved to a new BSS tail (docs/re/text.md "Phase 7"): .data memsz grows so the module owns the space.
# Every site that builds a buffer address is pinned (lui, lo user); work/p7-style scans of a RAM dump found no others.
# Addresses keep RAM and segment-relative low halves in 0x0000-0x7FFF, so the loader's HI16/LO16 carry stays simple.
BSS_END = 0x08DD2000
SCEN_BUF, SCEN_OLD, SCEN_SIZE = 0x08DB2000, 0x08B94F38, 0xF800  # size: the bound check is an ori (max 0xFFFF)
MSYS_BUF, MSYS_OLD, MSYS_SIZE = 0x08DC2000, 0x08BB5A98, 0x10000
SCEN_PAIRS = [(0x08807498, 0x088074A0), (0x08808020, 0x08808024), (0x08808104, 0x08808108),
              (0x0880A148, 0x0880A14C), (0x0881BFC0, 0x0881BFC4), (0x0881DB88, 0x0881DB8C),
              (0x0881DB9C, 0x0881DBA0)]
MSYS_PAIRS = [(0x08853B68, 0x08853B6C), (0x08853C7C, 0x08853C80), (0x088543C0, 0x088543C4)]
SCEN_BOUND = 0x0880802C  # ori a0, zero, 0xB000: buffer end in the scene-state copy
# 0x088080E8..F8 reads the buffer's first word (text entry offset) as 0x08B7EF38 + 0x10000 + 0x6000:
# lui v0 / lui v1, 1 / addiu v0 / addu v0, v0, v1 / lw t0, 0x6000(v0) -> pair builds SCEN_BUF, addu -> nop, lw 0(v0)
SCEN_WORD0 = {0x088080E8: "2600023c", 0x088080EC: "0100033c", 0x088080F0: "78db4224", 0x088080F4: "21104300",
              0x088080F8: "0060488c"}
MSYS_TABLES = (0x0891716C, 0x08917204)  # u16 start sector / sector count of each MSYS.DAT group (BOOT .rodata)
MSYS_GROUPS = (6, 7)  # items descriptions; magic + skills (loaded one at a time into the MSYS buffer)


def _word(boot, ram):
    return struct.unpack_from("<I", boot, ram_to_file(ram))[0]


def _set_pair(boot, lui, lo, ram):
    """Rewrite a lui + I-type pair to build `ram` (a .data/.bss address, stored segment-relative)."""
    v = ram - DATA_SEG
    assert _word(boot, lui) >> 26 == 0x0F and 0 <= v & 0xFFFF < 0x8000
    for a, imm in ((lui, (v + 0x8000) >> 16), (lo, v & 0xFFFF)):
        struct.pack_into("<I", boot, ram_to_file(a), (_word(boot, a) & 0xFFFF0000) | imm)


def _pair_ram(boot, lui, lo):
    imm = _word(boot, lo) & 0xFFFF
    return ((_word(boot, lui) & 0xFFFF) << 16) + imm - (imm & 0x8000) * 2 + DATA_SEG


def move_buffers(boot):
    """Grow .data memsz to BSS_END and point every pinned site at the new scene and MSYS buffers."""
    ph = struct.unpack_from("<I", boot, 0x1C)[0] + 32  # phdr[1] = .data
    assert ph == 0x34 + 32, "e_phoff moved (move_spans pins it)"
    vaddr, memsz = struct.unpack_from("<I", boot, ph + 8)[0], struct.unpack_from("<I", boot, ph + 20)[0]
    assert prxrel.BASE + vaddr == DATA_SEG and DATA_SEG + memsz <= SCEN_BUF
    struct.pack_into("<I", boot, ph + 20, BSS_END - DATA_SEG)
    for pairs, old, new in ((SCEN_PAIRS, SCEN_OLD, SCEN_BUF), (MSYS_PAIRS, MSYS_OLD, MSYS_BUF)):
        for lui, lo in pairs:
            cur = _pair_ram(boot, lui, lo)
            if not old <= cur < old + 0x20:
                raise ValueError("0x%08X: builds 0x%08X, not the buffer 0x%08X" % (lo, cur, old))
            _set_pair(boot, lui, lo, cur - old + new)
    for a, h in SCEN_WORD0.items():
        if boot[ram_to_file(a):ram_to_file(a) + 4].hex() != h:
            raise ValueError("0x%08X: BOOT.BIN is not the original scene word-0 read" % a)
    _set_pair(boot, 0x088080E8, 0x088080F0, SCEN_BUF)
    struct.pack_into("<I", boot, ram_to_file(0x088080F4), 0)  # nop
    struct.pack_into("<I", boot, ram_to_file(0x088080F8), _word(boot, 0x088080F8) & 0xFFFF0000)
    if _word(boot, SCEN_BOUND) != 0x3404B000:
        raise ValueError("scene bound site moved")
    struct.pack_into("<I", boot, ram_to_file(SCEN_BOUND), 0x34040000 | SCEN_SIZE)


def move_spans():
    """BOOT.BIN file ranges move_buffers and msys_groups write."""
    ph = 0x34 + 32 + 20  # phdr[1] p_memsz (e_phoff = 0x34, asserted in move_buffers' read)
    out = [(ph, ph + 4), (ram_to_file(0x088080E8), ram_to_file(0x088080FC)),
           (ram_to_file(SCEN_BOUND), ram_to_file(SCEN_BOUND) + 4)]
    out += [(ram_to_file(a), ram_to_file(a) + 4) for p in SCEN_PAIRS + MSYS_PAIRS for a in p]
    out += [(ram_to_file(t) + 2 * g, ram_to_file(t) + 2 * g + 2) for t in MSYS_TABLES for g in MSYS_GROUPS]
    return out


def stale_refs(boot):
    """.text sites that still build an address inside an old buffer (lui + addiu/load/store/addu, followed forward
    while the registers hold constants), and relocated .data words pointing there. The scan that found SCEN_WORD0."""
    old = [(SCEN_OLD, SCEN_OLD + 0xB000), (MSYS_OLD, MSYS_OLD + 0x5800)]
    hit = lambda v: any(lo <= (v + DATA_SEG) & 0xFFFFFFFF < hi for lo, hi in old)  # noqa: E731
    s16 = lambda x: x - ((x & 0x8000) << 1)  # noqa: E731
    word = lambda o: struct.unpack_from("<I", boot, o)[0]  # noqa: E731
    out = []
    for o in range(0xC4, DATA_FILE - 4, 4):
        if word(o) >> 26 != 0x0F:
            continue
        regs = {(word(o) >> 16) & 31: (word(o) & 0xFFFF) << 16}
        for b in range(o + 4, min(o + 160, DATA_FILE), 4):
            y = word(b)
            op, rs, rt, rd = y >> 26, (y >> 21) & 31, (y >> 16) & 31, (y >> 11) & 31
            if op == 0x0F:
                regs[rt] = (y & 0xFFFF) << 16
            elif op == 0x09 and rs in regs:
                regs[rt] = regs[rs] + s16(y & 0xFFFF)
                if hit(regs[rt]):
                    out.append(file_to_ram(b))
            elif op == 0 and y & 0x3F == 0x21 and rs in regs and rt in regs:
                regs[rd] = regs[rs] + regs[rt]
                if hit(regs[rd]):
                    out.append(file_to_ram(b))
            elif op in (0x20, 0x21, 0x22, 0x23, 0x24, 0x25, 0x26, 0x28, 0x29, 0x2A, 0x2B, 0x2E) and rs in regs:
                if hit(regs[rs] + s16(y & 0xFFFF)):
                    out.append(file_to_ram(b))
                if op < 0x28:
                    regs.pop(rt, None)
            elif op == 0:
                regs.pop(rd, None)
            elif op not in (0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x14, 0x15):
                regs.pop(rt, None)
    rel = prxrel.relocs(boot)
    out += [a for a, t in rel.items() if t == 2 and a >= DATA_SEG and hit(word(ram_to_file(a)))]
    return sorted(set(out))


def check_scen_fit(scen, entries):
    """Entry N loads at the buffer, entry N + 380 (text) at buffer + word 0 of entry N, in whole sectors."""
    def get(n):
        return entries.get(n) or dat.entry(scen, n)
    for n in range(380):
        a, b = get(n), get(n + 380)
        if not a:
            continue
        end = max(len(a), struct.unpack_from("<I", a, 0)[0] + -(-len(b) // 0x800) * 0x800)
        if end > SCEN_SIZE:
            raise ValueError("scene pair %d/%d: 0x%X bytes > scene buffer 0x%X" % (n, n + 380, end, SCEN_SIZE))


def msys_groups(boot, msys, sections):
    """sections: {file offset: new section bytes}. Rebuild each MSYS group from its sections back to back; a group
    that outgrows its sectors moves to the end of MSYS.DAT (the BOOT sector tables follow). Returns the new file."""
    st_at, sz_at = (ram_to_file(t) for t in MSYS_TABLES)
    out, olds = bytearray(msys), []
    for g in MSYS_GROUPS:
        st, sz = (struct.unpack_from("<H", boot, t + 2 * g)[0] for t in (st_at, sz_at))
        lo, hi = st * 0x800, (st + sz) * 0x800
        olds.append((lo, hi))
        ats = sorted(a for a in sections if lo <= a < hi)
        assert ats and ats[0] == lo, "MSYS group %d: no section at its start" % g
        p = lo
        for a in ats:  # original sections tile the group from its start
            assert a == p, "MSYS group %d: gap at 0x%X" % (g, p)
            p += struct.unpack_from("<I", msys, a)[0]
        assert not any(msys[p:hi]), "MSYS group %d: data after its sections" % g
        blob = b"".join(sections[a] for a in ats)
        n = -(-len(blob) // 0x800)
        if n * 0x800 > MSYS_SIZE:
            raise ValueError("MSYS group %d: 0x%X bytes > MSYS buffer 0x%X" % (g, len(blob), MSYS_SIZE))
        if n > sz:
            st, sz = len(out) // 0x800, n
            out += bytes(n * 0x800)
            struct.pack_into("<H", boot, st_at + 2 * g, st)
            struct.pack_into("<H", boot, sz_at + 2 * g, sz)
        out[st * 0x800:(st + sz) * 0x800] = blob + bytes(sz * 0x800 - len(blob))
    assert len(msys) % 0x800 == 0
    a, b = bytearray(msys), out[:len(msys)]
    for lo, hi in olds:
        a[lo:hi] = b[lo:hi] = bytes(hi - lo)
    if a != b:
        raise ValueError("MSYS.DAT changed outside groups %s" % (MSYS_GROUPS,))
    return bytes(out)


def log_writes(log, before, after, spans, by):
    """Append each changed run of `after` vs `before` to `log` as a romdiff write (offset, old, new, writer); a run
    outside the writer's declared `spans` raises. romdiff then checks old == the original file (no stage writes over
    another's bytes), new == the final file (nothing overwrites it later) and no overlaps."""
    merged = []
    for s, e in sorted(spans):
        if merged and s <= merged[-1][1]:
            merged[-1][1] = max(e, merged[-1][1])
        else:
            merged.append([s, e])
    i, n = 0, len(after)
    while i < n:
        if before[i:i + 4096] == after[i:i + 4096]:
            i += 4096
            continue
        if before[i] == after[i]:
            i += 1
            continue
        j = i
        while j < n and before[j] != after[j]:
            j += 1
        if not any(s <= i and j <= e for s, e in merged):
            raise ValueError("%s wrote BOOT.BIN 0x%X-0x%X outside its declared ranges" % (by, i, j))
        log.append((i, bytes(before[i:j]), bytes(after[i:j]), by))
        i = j
    return log


def patched(mode="en", overrides=None, tree=extract.TREE):
    """{ISO path: bytes} for flat files and {ISO path: {entry: bytes}} for SCEN.DAT, plus EBOOT/BOOT (signed)."""
    enc = Encoder(mode, overrides)
    scen, boot, msys = extract.read("SCEN.DAT", tree), bytearray(extract.read("BOOT.BIN", tree)), \
        bytearray(extract.read("MSYS.DAT", tree))
    entries, tables, sections, spans = {}, [], {}, []  # spans: BOOT.BIN file ranges the build may change
    for doc in docs():
        if mode != "jp" and doc["file"] == "BOOT.BIN" and doc["form"] == "table" and \
                not doc["entries"][0]["id"].startswith(KEEP_POOLS):
            tables.append(doc)
            continue
        new = enc.pool(doc)
        if doc["file"] == "SCEN.DAT":
            ent = bytearray(entries.get(doc["entry"]) or dat.entry(scen, doc["entry"]))
            at = int(doc["at"], 16)
            old = struct.unpack_from("<I", ent, at)[0]
            if mode == "jp" or len(new) <= old:
                put(ent, at, new, old, doc["entries"][0]["id"])
            else:  # the text section ends its entry (zero tail only): grow the entry, dat.pack moves it
                assert not any(ent[at + old:]), doc["entries"][0]["id"]
                ent = ent[:at] + new
            entries[doc["entry"]] = bytes(ent)
        elif doc["file"] == "MSYS.DAT":
            at = int(doc["at"], 16)
            if mode == "jp":
                put(msys, at, new, struct.unpack_from("<I", msys, at)[0], doc["entries"][0]["id"])
            sections[at] = new
        elif doc["form"] == "cstr":
            for e, b in zip(doc["entries"], new):
                put(boot, int(e["at"], 16), b, e["size"], e["id"])
                spans.append((int(e["at"], 16), int(e["at"], 16) + e["size"]))
        else:
            table, pool = new
            t, base = int(doc["table"], 16), int(doc["base"], 16)
            put(boot, t, table, len(table), doc["entries"][0]["id"] + " table")
            put(boot, base, pool, t - base, doc["entries"][0]["id"] + " pool")
            spans.append((base, t + len(table)))
    orig_boot = extract.read("BOOT.BIN", tree)
    log = log_writes([], orig_boot, boot, spans, "pools")  # each stage's writes, for romdiff --writes
    if tables:
        b = bytes(boot)
        log_writes(log, b, boot, heap_tables(boot, enc, tables).spans, "heap_tables")
    if mode != "jp":
        b = bytes(boot)
        move_buffers(boot)
        log_writes(log, b, boot, move_spans(), "move_buffers")
        stale = stale_refs(boot)
        if stale:
            raise ValueError("code still builds an old buffer address: " + ", ".join("%08X" % a for a in stale))
        assert set(entries) <= set(range(380, 760)), "SCEN.DAT edit outside the text entries"
        check_scen_fit(scen, entries)
        b = bytes(boot)
        msys = msys_groups(boot, msys, sections)
        log_writes(log, b, boot, move_spans(), "msys_groups")
        b = bytes(boot)
        boot = armips(b)
        log_writes(log, b, boot, [(ram_to_file(a), ram_to_file(a) + len(h) // 2) for a, h in HOOKS.items()] +
                   [FREE_ASM], "armips")
    errs, _ = romdiff.check(orig_boot, boot, [], log)
    if errs:
        raise ValueError("BOOT.BIN write log check failed:\n" + "\n".join(errs[:10]))
    sysdir = "/PSP_GAME/SYSDIR/"
    out = {"/PSP_GAME/USRDIR/gr_data1/MSYS.DAT": bytes(msys), sysdir + "BOOT.BIN": bytes(boot)}
    if mode != "jp":
        import sign
        out[sysdir + "EBOOT.BIN"] = sign.sign(bytes(boot))
    return out, {"/PSP_GAME/USRDIR/gr_data1/SCEN.DAT": entries}


def check_sites(boot):
    """Each hook site holds its original bytes; no relocation inside the free space; relocated hook words are
    j/jal sites (vwf.asm writes JALR/JR there) or untouched."""
    for a, h in HOOKS.items():
        o = ram_to_file(a)
        if boot[o:o + len(h) // 2].hex() != h:
            raise ValueError("vwf.asm hook 0x%08X: BOOT.BIN holds %s, not %s" % (a, boot[o:o + len(h) // 2].hex(), h))
    rel = prxrel.relocs(boot)
    lo, hi = FREE_ASM[0] + DATA_HS, FREE_ASM[1] + DATA_HS
    bad = [a for a in rel if lo - 4 < a < hi]
    if bad:
        raise ValueError("relocation inside the vwf.asm free space: 0x%08X" % bad[0])
    return rel


def armips(boot, gen=None):
    """Assemble asm/vwf.asm into BOOT.BIN; armips may change bytes only at HOOKS and in FREE_ASM, and every changed
    word with an R_MIPS_26 relocation must be a j/jal."""
    rel = check_sites(boot)
    work = ROOT / "work" / "asm"
    shutil.rmtree(work, ignore_errors=True)
    work.mkdir(parents=True, exist_ok=True)
    glyphs, widths = enfont.tables()
    (work / "en_glyphs.bin").write_bytes(glyphs)
    (work / "en_widths.bin").write_bytes(widths)
    (work / "gen.inc").write_text("".join("%s equ 0x%X\n" % kv for kv in {**GEN_DEFAULT, **(gen or {})}.items()))
    shutil.copy(ROOT / "asm" / "vwf.asm", work / "vwf.asm")
    (work / "BOOT.BIN").write_bytes(boot)
    r = subprocess.run([str(ARMIPS), "vwf.asm", "-sym", "vwf.sym"], cwd=work, capture_output=True, text=True)
    if r.returncode or "rror" in r.stdout:
        raise RuntimeError("armips failed:\n" + r.stdout + r.stderr)
    out = (work / "BOOT.BIN").read_bytes()
    if len(out) != len(boot):
        raise ValueError("armips changed the BOOT.BIN size")
    spans = [(ram_to_file(a), ram_to_file(a) + len(h) // 2) for a, h in HOOKS.items()] + [FREE_ASM]
    for i in range(0, len(boot), 4):
        if boot[i:i + 4] == out[i:i + 4]:
            continue
        if not any(s <= i < e for s, e in spans):
            raise ValueError("armips wrote outside the hook sites and free space: file 0x%X" % i)
        a = i + (DATA_HS if i >= DATA_FILE else TEXT_HS)
        if rel.get(a) == 4 and struct.unpack_from("<I", out, i)[0] >> 26 not in (2, 3):
            raise ValueError("0x%08X has an R_MIPS_26 relocation: only j/jal may go there" % a)
        if a in rel and rel[a] != 4:
            raise ValueError("0x%08X has a type %d relocation: leave it alone" % (a, rel[a]))
    return out


def symbols():
    out = {}
    for line in (ROOT / "work" / "asm" / "vwf.sym").read_text(encoding="utf-8").splitlines():
        a, _, name = line.partition(" ")
        if name and not name.startswith(".") and re.fullmatch(r"[0-9A-Fa-f]{8}", a):
            out[name.strip()] = int(a, 16)
    return out


if __name__ == "__main__":
    if "--check" in sys.argv:
        b = armips(extract.read("BOOT.BIN"))
        s = symbols()
        print("vwf.asm ok: code + font end 0x%08X (limit 0x%08X)" % (s["vwf_end"], FREE_ASM[1] + DATA_HS))
