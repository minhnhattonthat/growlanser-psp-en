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
