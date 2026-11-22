"""Fast tests for the repo's own tools (no ROM needed)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))


def test_skill_path_resolves():
    from skill import SKILL
    assert (Path(SKILL) / "SKILL.md").is_file()


def test_glb_rle_and_unswizzle():
    import numpy as np
    import glb
    # 1x1 tile: runs of c copies, literals of c-0x80 bytes; 0xFE zeros, palette, then one swizzled tile
    body = bytearray([0x7F, 0, 0x7F, 0])  # 254 zeros
    pal = bytes(range(256)) * 2
    for k in range(0, 512, 127):
        chunk = pal[k:k + 127]
        body += bytes([0x80 + len(chunk)]) + chunk
    tile = np.arange(128 * 128, dtype=np.uint32).astype(np.uint8).reshape(128, 128)
    sw = tile.reshape(16, 8, 8, 16).transpose(0, 2, 1, 3).tobytes()  # row-major -> GE swizzle
    for k in range(0, len(sw), 127):
        chunk = sw[k:k + 127]
        body += bytes([0x80 + len(chunk)]) + chunk
    pix, p, u = glb.decode(bytes([0x82, 1, 1]) + bytes(body))
    assert (pix == tile).all() and len(u) == glb.PIX + 128 * 128 and p[1] == 0x0302


def test_textfind_row_of_glyphs():
    import numpy as np
    from textfind import score
    a = np.zeros((64, 200), np.uint8)
    assert score(a, 5)[0] == 0
    for i in range(7):  # 7 glyph-sized blobs, 10 px tall, 3 px gaps, one baseline
        a[20:30, 10 + i * 13:20 + i * 13:2] = 255
        a[24, 10 + i * 13:20 + i * 13] = 255
    assert score(a, 5)[0] >= 5
