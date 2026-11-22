"""extract.py: dump every text pool of the original disc to script/*.json (formats: docs/re/text.md "Script files").

    python -X utf8 tools/extract.py            write missing script files (never touches existing ones)
    python -X utf8 tools/extract.py --force    rewrite files that hold no English yet (refuses files with any `en`)
    python -X utf8 tools/extract.py --check    exit 1 unless script/ matches the disc and rebuilds byte-identical

Pools (adapted from the PS1 repo's tools/extract.py):
  scen/sNNN.json   SCEN.DAT scene text sections, N = entry - 380 = scene id         form "section"
  msys/*.json      MSYS.DAT description sections (items, magic, skills)              form "section"
  boot/<t>.json    BOOT.BIN module string tables (pool, then its u16 offset table)   form "table"
  boot/save.json   BOOT.BIN UTF-8 / Shift-JIS strings (save utility, save title)     form "cstr"
  boot/kbd.json    BOOT.BIN Shift-JIS name-entry keyboard rows                       form "cstr"
Entry fields: id, jp (terminator excluded), en, term (end = FFFE message, null = FFFF name/slot), unref (no pointer).
cstr entries: at (file offset), size (slot bytes: string + NUL fill up to the next string), enc.
"""
import json
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import dat  # noqa: E402
import gltext  # noqa: E402
import scen  # noqa: E402
import textsec  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
TREE = ROOT / "work" / "iso" / "PSP_GAME"
FILES = {"SCEN.DAT": "USRDIR/gr_data1/SCEN.DAT", "MSYS.DAT": "USRDIR/gr_data1/MSYS.DAT", "BOOT.BIN": "SYSDIR/BOOT.BIN"}
SCRIPT = ROOT / "script"
TERM = {0xFFFE: "end", 0xFFFF: "null"}
TERM_W = {v: k for k, v in TERM.items()}
SCEN_ENTRIES = range(380, 760)
MSYS_SECTIONS = [("items", 0x42800), ("magic", 0x48000), ("skills", 0x48DBC)]
# name, pool start, offset table (pool ends there), count; BOOT.BIN file offsets, getters in docs/re/text.md
BOOT_TABLES = [
    ("dict", 0x12C4A4, 0x12D640, 0x100),
    ("places", 0x12D840, 0x12D954, 0x14),
    ("help", 0x12D97C, 0x12E018, 0x24),
    ("items", 0x12E060, 0x12F2A0, 0x172),
    ("skills", 0x12F584, 0x12FA5C, 0x66),  # getter bound 0x64; the table holds 2 more words (into the pool)
    ("magic", 0x12FB28, 0x12FD6C, 0x40),
    ("classes", 0x12FDEC, 0x130310, 0x11D),
    ("units", 0x13054C, 0x131540, 0x167),
    ("names", 0x131810, 0x131EBC, 0x167),
    ("sys", 0x13218C, 0x133068, 0xC8),
]
BOOT_TABLES_RANGE = (0x12C4A4, 0x1331F8)
# cstr pools: (name, [(offset, slot size, encoding)]); slot = up to the next string in the file
CSTR = [
    ("save", [(0x117408, 0x28, "cp932"),   # save title format グローランサー［%s］　%s：%s：%s　%s
              (0x117A80, 0x18, "utf-8"), (0x117A98, 0x14, "utf-8"), (0x117AAC, 0x28, "utf-8"),
              (0x117AF4, 0x38, "utf-8"), (0x117B2C, 0x3C, "utf-8"), (0x117B68, 0x30, "utf-8"),
              (0x117B98, 0x30, "utf-8"), (0x117BC8, 0xBC, "utf-8"), (0x117C84, 0x88, "utf-8"),
              (0x117D0C, 0x54, "utf-8"), (0x119284, 0x20, "utf-8"), (0x1192A4, 0x44, "utf-8"),
              (0x1192E8, 0x44, "utf-8"), (0x11932C, 0x68, "utf-8"), (0x119394, 0x28, "utf-8"),
              (0x1193BC, 0x50, "utf-8")]),
    ("kbd", [(0x1137D0 + 21 * k, 21, "cp932") for k in range(30)]),  # 10 full-width cells + NUL per row
]


def _refs_str(refs):
    return " ".join(str(i) if d == 0 else "%d+%d" % (i, d) for i, d in refs)


def _refs_parse(s):
    out = []
    for t in s.split():
        i, _, d = t.partition("+")
        out.append((int(i), int(d or 0)))
    return out


def _entries(prefix, strings, refs, codec):
    used = {i for i, _ in refs}
    out = []
    for k, ws in enumerate(strings):
        e = {"id": "%s.%04d" % (prefix, k), "jp": codec.decode(ws[:-1]), "en": "", "term": TERM[ws[-1]]}
        if k not in used:
            e["unref"] = True
        out.append(e)
    return out


def read(name, tree=TREE):
    return (tree / FILES[name]).read_bytes()


def _pool_end(buf, base, table):
    """Pool end before its table, past any zero-word fill; -> (end, fill words)."""
    end = table
    while end > base and struct.unpack_from("<H", buf, end - 2)[0] == 0 and \
            struct.unpack_from("<H", buf, end - 4)[0] in TERM:
        end -= 2
    return end, (table - end) // 2


def pools(tree=TREE):
    """Yield (relative path, doc) for every pool, generated from the disc files."""
    c = gltext.Codec()
    data = read("SCEN.DAT", tree)
    for n in SCEN_ENTRIES:
        e = dat.entry(data, n)
        ts = scen.text_section(e) if e else None
        if ts is None:
            continue
        sec = ts[0]
        strings, refs, pad, _ = textsec.read_section(e, sec)
        yield "scen/s%03d.json" % (n - 380), {
            "file": "SCEN.DAT", "form": "section", "entry": n, "at": "0x%X" % sec, "pad": pad,
            "refs": _refs_str(refs), "entries": _entries("scen%03d" % (n - 380), strings, refs, c)}
    data = read("MSYS.DAT", tree)
    for name, off in MSYS_SECTIONS:
        strings, refs, pad, _ = textsec.read_section(data, off)
        yield "msys/%s.json" % name, {
            "file": "MSYS.DAT", "form": "section", "at": "0x%X" % off, "pad": pad,
            "refs": _refs_str(refs), "entries": _entries("msys.%s" % name, strings, refs, c)}
    data = read("BOOT.BIN", tree)
    for name, base, table, count in BOOT_TABLES:
        end, fill = _pool_end(data, base, table)
        strings, refs = textsec.read_table(data, table, base, count, end)
        yield "boot/%s.json" % name, {
            "file": "BOOT.BIN", "form": "table", "table": "0x%X" % table, "base": "0x%X" % base, "fill": fill,
            "refs": _refs_str(refs), "entries": _entries("boot.%s" % name, strings, refs, c)}
    for name, slots in CSTR:
        ents = []
        for k, (at, size, enc) in enumerate(slots):
            raw = data[at:at + size]
            ents.append({"id": "boot.%s.%04d" % (name, k), "jp": raw.split(b"\0")[0].decode(enc), "en": "",
                         "at": "0x%X" % at, "size": size, "enc": enc})
        yield "boot/%s.json" % name, {"file": "BOOT.BIN", "form": "cstr", "entries": ents}


def cstr_bytes(e, field="jp"):
    b = e[field].encode(e["enc"])
    if len(b) >= e["size"]:
        raise ValueError("%s: %d bytes, slot holds %d with its NUL" % (e["id"], len(b), e["size"] - 1))
    return b + b"\0" * (e["size"] - len(b))


def pool_bytes(doc, field="jp", codec=None):
    """Rebuild a pool from a script doc: section bytes, (table bytes, pool bytes) for a table, [slot bytes] for cstr."""
    if doc["form"] == "cstr":
        return [cstr_bytes(e, field) for e in doc["entries"]]
    c = codec or gltext.Codec()
    strings = [c.encode(e[field]) + [TERM_W[e["term"]]] for e in doc["entries"]]
    refs = _refs_parse(doc["refs"])
    if doc["form"] == "section":
        return textsec.build_section(strings, refs, doc["pad"])
    table, pool = textsec.build_table(strings, refs)
    return table, pool + b"\0\0" * doc["fill"]


def original_bytes(doc, tree=TREE):
    data = read(doc["file"], tree)
    if doc["file"] == "SCEN.DAT":
        data = dat.entry(data, doc["entry"])
    if doc["form"] == "cstr":
        return [data[int(e["at"], 16):int(e["at"], 16) + e["size"]] for e in doc["entries"]]
    if doc["form"] == "section":
        at = int(doc["at"], 16)
        return data[at:at + struct.unpack_from("<I", data, at)[0]]
    table, base = int(doc["table"], 16), int(doc["base"], 16)
    return data[table:table + 2 * len(doc["refs"].split())], data[base:table]


def dump(doc):
    return json.dumps(doc, ensure_ascii=False, indent=1) + "\n"


def _skeleton(doc):
    """Everything the disc decides: pool fields and each entry's fields except en (and notes etc.)."""
    keys = ("id", "jp", "term", "unref", "at", "size", "enc")
    return ({k: v for k, v in doc.items() if k != "entries"},
            [tuple(e.get(k) for k in keys) for e in doc["entries"]])


def check():
    """Problems: script files missing / differing from the disc, or not rebuilding byte-identical."""
    bad, c = [], gltext.Codec()
    for rel, doc in pools():
        path = SCRIPT / rel
        if not path.exists():
            bad.append("%s missing" % rel)
            continue
        have = json.loads(path.read_text(encoding="utf-8"))
        if _skeleton(have) != _skeleton(doc):
            bad.append("%s differs from the disc" % rel)
            continue
        if pool_bytes(have, codec=c) != original_bytes(have):
            bad.append("%s does not rebuild byte-identical" % rel)
    return bad


def main(argv):
    if "--check" in argv:
        bad = check()
        print("\n".join(bad) or "script/ matches the disc and rebuilds byte-identical")
        return 1 if bad else 0
    force = "--force" in argv
    wrote = kept = 0
    for rel, doc in pools():
        path = SCRIPT / rel
        if path.exists():
            if not force:
                kept += 1
                continue
            old = json.loads(path.read_text(encoding="utf-8"))
            if any(e.get("en") for e in old["entries"]):
                print("refusing to overwrite %s: it holds English" % rel)
                kept += 1
                continue
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(dump(doc), encoding="utf-8", newline="\n")
        wrote += 1
    print("wrote %d, kept %d" % (wrote, kept))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
