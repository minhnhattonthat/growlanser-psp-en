"""Phase 4 extract: script/ matches the disc, every pool rebuilds byte-identical from its jp text, the pools cover the
known text ranges, and the table maps every glyph except the known odd ones. Disc tests skip without the dump."""
import json
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))
import build  # noqa: E402
import extract  # noqa: E402
import gltext  # noqa: E402

disc = pytest.mark.skipif(not build.ISO.is_file(), reason="no dump in rom/")
# glyphs the table leaves out on purpose (tbl/jp.tbl header): icons, condensed "pendant", flourish, blanks, 啍
UNMAPPED = {0x01BE, 0x01C2, 0x0793, 0x0298, 0x02A4, *range(0x0107, 0x0118), *range(0x028B, 0x028F), 0x07ED}


@disc
def test_script_roundtrip():
    build.unpack()
    assert extract.check() == []


@disc
def test_ranges_covered():
    build.unpack()
    docs = dict(extract.pools())
    msys = sorted((int(d["at"], 16), len(extract.pool_bytes(d))) for r, d in docs.items() if r.startswith("msys/"))
    assert msys[0][0] == 0x42800 and msys[-1][0] + msys[-1][1] == 0x4A81C
    tabs = sorted((int(d["base"], 16), int(d["table"], 16) + 2 * len(d["refs"].split()))
                  for d in docs.values() if d["form"] == "table")
    assert tabs[0][0] == extract.BOOT_TABLES_RANGE[0] and tabs[-1][1] == extract.BOOT_TABLES_RANGE[1]
    boot = extract.read("BOOT.BIN")
    assert all(not any(boot[a[1]:b[0]]) for a, b in zip(tabs, tabs[1:]))  # gaps between tables are zero fill only
    assert sum(r.startswith("scen/") for r in docs) == 309


def test_table_complete():
    c = gltext.Codec()
    missing = {w for w in range(0x836) if w not in c.dec} - UNMAPPED
    assert not missing, ["%04X" % w for w in sorted(missing)]


def test_only_known_unmapped_in_script():
    raw = set()
    for p in (ROOT / "script").rglob("*.json"):
        for e in json.loads(p.read_text(encoding="utf-8"))["entries"]:
            raw.update(int(h, 16) for h in re.findall(r"\[([0-9A-F]{4})\]", e["jp"]))
    assert raw <= UNMAPPED, ["%04X" % w for w in sorted(raw - UNMAPPED)]


def test_cstr_slot_overflow():
    e = {"id": "t", "jp": "abc", "size": 4, "enc": "utf-8"}
    assert extract.cstr_bytes(e) == b"abc\0"
    with pytest.raises(ValueError):
        extract.cstr_bytes({**e, "jp": "abcd"})
