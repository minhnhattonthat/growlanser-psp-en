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
import gltext  # noqa: E402
import prxrel  # noqa: E402
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
        self.mode, self.jp, self.en = mode, gltext.Codec(), enfont.EnCodec()
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
        return self.jp.encode(e["jp"]) if t is None else self.en.encode(t)

    def cstr(self, e):
        t = self.text(e)
        if t is None:
            return extract.cstr_bytes(e)
        if self.mode == "marker" and e["id"] not in self.overrides:
            t = t.replace("・", "")[:len(e["jp"].encode(e["enc"]))]  # ASCII, no longer than the Japanese bytes
        return extract.cstr_bytes({**e, "en": t}, "en")

    def pool(self, doc):
        """New bytes for a pool, in place: section bytes, (table, pool bytes) or [cstr slots]. A pool holding a --qa
        override gets short markers elsewhere, so the override has room."""
        self.squeeze = any(e["id"] in self.overrides for e in doc["entries"])
        if doc["form"] == "cstr":
            return [self.cstr(e) for e in doc["entries"]]
        strings = [self.words(e) + [extract.TERM_W[e["term"]]] for e in doc["entries"]]
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


def patched(mode="en", overrides=None, tree=extract.TREE):
    """{ISO path: bytes} for flat files and {ISO path: {entry: bytes}} for SCEN.DAT, plus EBOOT/BOOT (signed)."""
    enc = Encoder(mode, overrides)
    scen, boot, msys = extract.read("SCEN.DAT", tree), bytearray(extract.read("BOOT.BIN", tree)), \
        bytearray(extract.read("MSYS.DAT", tree))
    entries = {}
    for doc in docs():
        new = enc.pool(doc)
        if doc["file"] == "SCEN.DAT":
            ent = bytearray(entries.get(doc["entry"]) or dat.entry(scen, doc["entry"]))
            at = int(doc["at"], 16)
            put(ent, at, new, struct.unpack_from("<I", ent, at)[0], doc["entries"][0]["id"])
            entries[doc["entry"]] = bytes(ent)
        elif doc["file"] == "MSYS.DAT":
            at = int(doc["at"], 16)
            put(msys, at, new, struct.unpack_from("<I", msys, at)[0], doc["entries"][0]["id"])
        elif doc["form"] == "cstr":
            for e, b in zip(doc["entries"], new):
                put(boot, int(e["at"], 16), b, e["size"], e["id"])
        else:
            table, pool = new
            t, base = int(doc["table"], 16), int(doc["base"], 16)
            put(boot, t, table, len(table), doc["entries"][0]["id"] + " table")
            put(boot, base, pool, t - base, doc["entries"][0]["id"] + " pool")
    if mode != "jp":
        boot = armips(bytes(boot))
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
