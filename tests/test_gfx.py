"""Graphics edits (tools/gfx.py): GLB re-encode round trip, archive entry sizes kept, PNG padding."""
import io
import sys
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import glb  # noqa: E402
import gfx  # noqa: E402

GLB = ROOT / "work/iso/PSP_GAME/USRDIR/gr_data1/GLB.DAT"


def test_rle_roundtrip():
    for u in (b"", b"a", b"aaaa", bytes(range(200)) + b"\0" * 300 + b"xyz" * 50):
        assert glb.unrle(b"\x82\0\0" + glb.rle(u)) == u


@pytest.mark.skipif(not GLB.is_file(), reason="work/iso not unpacked")
def test_glb_encode_title():
    d = GLB.read_bytes()
    e = {n: d[o:o + s] for n, o, s in glb.entries(d)}["B99_02_A"]
    pix, pal, u = glb.decode(e)
    enc = glb.encode(pix, pal)
    assert glb.decode(enc)[0].tobytes() == pix.tobytes() and len(enc) <= len(e)


def test_png_padding():
    im = Image.fromarray(np.zeros((8, 8, 3), np.uint8))
    b = gfx.png_bytes(im, 500)
    assert len(b) == 500 and np.asarray(Image.open(io.BytesIO(b))).shape == (8, 8, 3)


@pytest.mark.skipif(not GLB.is_file(), reason="work/iso not unpacked")
def test_apply_keeps_entry_sizes():
    flat, edits = gfx.apply({}, {})  # asserts DATA.DAT / DATA_BOOT.DAT entry sizes itself
    assert "staff/stf05.bmp" in edits[gfx.G + "DATA.DAT"] and "B99_02_A" in edits[gfx.G + "GLB.DAT"]
