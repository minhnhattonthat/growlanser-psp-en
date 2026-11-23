"""tools/insert.py: the jp mode rebuilds every pool byte-identical, marker pools fit in place, vwf.asm assembles only
at its pinned hook sites (relocated words stay j/jal)."""
import struct
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import extract  # noqa: E402
import insert  # noqa: E402

pytestmark = pytest.mark.skipif(not (extract.TREE / "SYSDIR" / "BOOT.BIN").is_file(), reason="work/iso not unpacked")


@pytest.mark.parametrize("mode", ["jp", "marker"])
def test_pools_in_place(mode):
    enc = insert.Encoder(mode)
    for doc in insert.docs():
        new, old = enc.pool(doc), extract.original_bytes(doc)
        if doc["form"] == "cstr":
            assert all(len(n) == len(o) for n, o in zip(new, old)), doc["entries"][0]["id"]
        elif doc["form"] == "section":
            assert (new == old) if mode == "jp" else len(new) <= len(old), doc["entries"][0]["id"]
        else:
            assert (new[0] == old[0] and new[1] == old[1]) if mode == "jp" else \
                (len(new[0]) == len(old[0]) and len(new[1]) <= len(old[1])), doc["entries"][0]["id"]


def test_marker_word_count():
    e = {"id": "scen123.0456", "jp": "これは{n}テスト{FFEE}"}
    m = insert.marker(e)
    assert m == "123.45{n}The qu{FFEE}"
    assert insert.marker({"id": "boot.items.0002", "jp": "剣"}) == "it"
    # short (pool holds a --qa ruler): only the id, later runs empty, codes kept
    assert insert.marker({"id": "scen123.0456", "jp": "これはテストです{n}テスト{FFEE}"}, True) == "123.456{n}{FFEE}"


def test_qa_override_room():
    # a ruler longer than its own Japanese fits in place: the rest of its pool shrinks to ids
    enc = insert.Encoder("marker", {"boot.items.0030": "A234567890" * 8})
    doc = next(d for d in insert.docs() if d["entries"][0]["id"].startswith("boot.items."))
    table, pool = enc.pool(doc)
    old = extract.original_bytes(doc)
    assert len(table) == len(old[0]) and len(pool) <= len(old[1])
    assert not insert.Encoder("marker").squeeze  # pools without an override keep full markers


@pytest.mark.skipif(not insert.ARMIPS.is_file(), reason="armips not installed in tools/armips")
def test_vwf_asm_sites():
    boot = extract.read("BOOT.BIN")
    out = insert.armips(boot)  # raises on a stray write or a non-jump at an R_MIPS_26 site
    for a in (0x0887501C, 0x088750F8, 0x08874CE0):  # jal vwf_std / vwf_big, module-relative
        w = struct.unpack_from("<I", out, insert.ram_to_file(a))[0]
        sym = insert.symbols()["vwf_big" if a == 0x08874CE0 else "vwf_std"]
        assert w == 0x0C000000 | (sym - 0x08804000) >> 2


def test_fitting():
    """PS1 fitting ports: name tags padded so every code's column is inside the code-count frame; name-entry slices."""
    enc = insert.Encoder("en")
    w = enc.tag_pad(enc.en.encode("Alviss's Staff"))
    x = 0
    for c in w:
        assert -(-x // 12) < len(w)
        x += enc.advance(c)
    s = enc.slots("boot.sys.0069", "Enter Name　Hira Kata ABC Del OK")
    assert sum(map(enc.advance, s)) == sum(insert.SLOTS["boot.sys.0069"])
    e = next(e for d in insert.docs() for e in d["entries"] if e["id"] == "boot.sys.0069")
    assert enc.words(e) == s
    cap = {"id": "scen011.0027", "jp": "一ヶ月後‥‥", "en": "One month later...", "term": "end"}
    assert insert.is_title(cap) and not insert.is_title({**cap, "id": "scen034.0035"})


def test_move_buffers():
    """Scene and MSYS buffers move to the grown BSS: every builder of an old buffer address is rewritten."""
    boot = bytearray(extract.read("BOOT.BIN"))
    assert len(insert.stale_refs(boot)) == 14  # the scan finds the pinned sites (incl. the 0x08B7EF38 + 0x16000 read)
    insert.move_buffers(boot)
    assert insert.stale_refs(boot) == []
    for pairs, new in ((insert.SCEN_PAIRS, insert.SCEN_BUF), (insert.MSYS_PAIRS, insert.MSYS_BUF)):
        assert {insert._pair_ram(boot, *p) & ~0x1F for p in pairs} == {new}
    assert insert._pair_ram(boot, 0x088080E8, 0x088080F0) == insert.SCEN_BUF
    assert struct.unpack_from("<I", boot, 0x34 + 32 + 20)[0] == insert.BSS_END - insert.DATA_SEG
    # heap starts at the (0x1000-aligned) BSS end and must end where the original's did (issue #1)
    assert insert.BSS_END + insert._word(boot, insert.HEAP_KB) * 1024 == insert.HEAP_END


def test_msys_groups():
    """English MSYS: each group is its sections back to back (the loader finds section 1 at word 0 of section 0);
    a group that outgrows its sectors moves to the end of MSYS.DAT and the BOOT sector tables follow."""
    boot, msys, enc = bytearray(extract.read("BOOT.BIN")), extract.read("MSYS.DAT"), insert.Encoder("en")
    secs = {int(d["at"], 16): enc.pool(d) for d in insert.docs() if d["file"] == "MSYS.DAT"}
    out = insert.msys_groups(boot, msys, secs)
    st, sz = (insert.ram_to_file(t) for t in insert.MSYS_TABLES)
    for g, ats in ((6, [0x42800]), (7, [0x48000, 0x48DBC])):
        start = struct.unpack_from("<H", boot, st + 2 * g)[0] * 0x800
        want = b"".join(secs[a] for a in ats)
        assert out[start:start + len(want)] == want
        assert struct.unpack_from("<H", boot, sz + 2 * g)[0] * 0x800 >= len(want)
    assert out[:0x42800] == msys[:0x42800] and out[0x4B000:len(msys)] == msys[0x4B000:]


@pytest.mark.skipif(not insert.ARMIPS.is_file(), reason="armips not installed in tools/armips")
def test_en_build():
    """The full English build's gates (BOOT write log + romdiff, stale_refs, scene/MSYS fit, armips, MSYS outside the
    grown groups) pass, and the repacked SCEN.DAT keeps every non-text entry byte-identical."""
    sys.path.insert(0, str(ROOT))
    import build
    import dat
    flat, edits = insert.patched("en")
    assert set(flat) == {"/PSP_GAME/USRDIR/gr_data1/MSYS.DAT", "/PSP_GAME/SYSDIR/BOOT.BIN", "/PSP_GAME/SYSDIR/EBOOT.BIN"}
    scen = build.G + "SCEN.DAT"
    old, new = build.orig(scen), build.patches(edits)[scen]
    assert len(dat.entries(new)) == len(dat.entries(old))
    for n in [n for n in range(len(dat.entries(old))) if not 380 <= n < 760]:
        assert dat.entry(new, n) == dat.entry(old, n), n


def test_log_writes():
    log = insert.log_writes([], b"abcdef", b"aXcdYY", [(1, 2), (4, 6)], "t")
    assert log == [(1, b"b", b"X", "t"), (4, b"ef", b"YY", "t")]
    with pytest.raises(ValueError):
        insert.log_writes([], b"abcdef", b"aXcdYY", [(1, 2)], "t")


def test_boot_heap():
    """English BOOT tables: each id read back the getter's way (repointed base + 2 * u16) gives its encoded string."""
    boot, enc = bytearray(extract.read("BOOT.BIN")), insert.Encoder("en")
    docs = [d for d in insert.docs() if d["file"] == "BOOT.BIN" and d["form"] == "table"
            and not d["entries"][0]["id"].startswith(insert.KEEP_POOLS)]
    insert.heap_tables(boot, enc, docs)
    base = insert.ram_to_file(insert.HEAP_RAM)
    for d in docs:
        t, want = int(d["table"], 16), enc.strings(d)
        for k, (i, delta) in enumerate(extract._refs_parse(d["refs"])):
            at = base + 2 * struct.unpack_from("<H", boot, t + 2 * k)[0]
            s = want[i][delta // 2:]
            assert list(struct.unpack_from("<%dH" % len(s), boot, at)) == s, d["entries"][i]["id"]
    # the classes getter's pool base now builds HEAP_RAM: lui 0x0001 kept, addiu lo16 = HEAP_RAM - .data RAM
    w = struct.unpack_from("<I", boot, insert.ram_to_file(0x08876668))[0]
    assert w & 0xFFFF == (insert.HEAP_RAM - insert.DATA_SEG) & 0xFFFF
