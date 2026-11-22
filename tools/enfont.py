"""enfont.py: English VWF font (font/en12.txt) and the pair codec for English text.

    python -X utf8 tools/enfont.py render OUT.png [TEXT]   glyph sheet, or TEXT laid out as the VWF draws it
    python -X utf8 tools/enfont.py --selftest

English text is stored two letters per 16-bit word: PAIR + (i << 7) + j, where i, j are charset indices (ASCII for
U+0020-U+007E, EXTRA below for the rest; j = 0 means no second letter). Words below PAIR stay glyph codes of the
game's font (icons, buttons), words >= 0xDFFF stay control codes. asm/vwf.asm draws a pair as two proportional
glyphs; the engine counts it as one 12 px cell, so its own line checks stay roughly right.
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import gltext  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
FONT = ROOT / "font" / "en12.txt"
PAIR = 0x0800
EXTRA = {0x01: "é", 0x02: "…", 0x03: "—", 0x04: "♪", 0x05: "♥"}  # index -> char
# Blank spacers U+E001-U+E00B, advance 1-11 px: only the encoder adds them (insert.Encoder.centre / slots); decode drops them.
SPACERS = {chr(0xE001 + k): k + 1 for k in range(11)}
EXTRA.update({0x10 + k: ch for k, ch in enumerate(SPACERS)})
LEGACY = {"・": 0x00D1, "　": 0x0000}  # game glyphs kept (12 px): choice bullet, full-width blank (layout)
GH, GW = 12, 12


def load(path=FONT):
    """{char: (top, rows, advance)}"""
    out = {}
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        ch = chr(int(parts[0][2:], 16)) if parts[0].startswith("U+") else parts[0]
        top = int(parts[1])
        adv = None
        if parts[2].startswith("w="):
            adv = int(parts[2][2:])
            parts.pop(2)
        rows = parts[2].split("/")
        w = len(rows[0])
        assert all(len(r) == w for r in rows), ch
        assert top + len(rows) <= GH and w <= GW - 1, ch
        out[ch] = (top, rows, adv if adv is not None else w + 1)
    return out


def charset():
    """{char: index} for every index 1-127 the font defines."""
    cs = {chr(c): c for c in range(0x20, 0x7F)}
    cs.update({ch: i for i, ch in EXTRA.items()})
    return cs


def tables(path=FONT):
    """(glyph bytes 128 x 18, widths 128) for asm/vwf.asm; undefined indices are blank, width 0."""
    font, glyphs, widths = load(path), bytearray(128 * 18), bytearray(128)
    for ch, i in charset().items():
        if ch not in font:
            continue
        top, rows, adv = font[ch]
        bits = 0
        for y in range(GH):
            r = rows[y - top] if 0 <= y - top < len(rows) else ""
            for x in range(GW):
                bits = bits << 1 | (x < len(r) and r[x] == "#")
        glyphs[i * 18:i * 18 + 18] = bits.to_bytes(18, "big")
        widths[i] = adv
    return bytes(glyphs), bytes(widths)


class EnCodec(gltext.Codec):
    """Encode English: letters in pairs, {controls} and [XXXX] raw words as in gltext.Codec."""

    def __init__(self):
        super().__init__()
        font = load()
        self.cs = {ch: i for ch, i in charset().items() if ch in font}
        self.rev = {i: ch for ch, i in self.cs.items()}

    def encode(self, text):
        words, run, i = [], [], 0

        def flush():
            for k in range(0, len(run), 2):
                words.append(PAIR + (run[k] << 7) + (run[k + 1] if k + 1 < len(run) else 0))
            run.clear()
        while i < len(text):
            m = gltext.TOKEN.match(text, i)
            if m:
                flush()
                words.extend(super().encode(m.group(0)))
                i = m.end()
                continue
            if text[i] in LEGACY:
                flush()
                words.append(LEGACY[text[i]])
                i += 1
                continue
            if text[i] not in self.cs:
                raise ValueError(f"no glyph for {text[i]!r} in {text!r}")
            run.append(self.cs[text[i]])
            i += 1
        flush()
        return words

    def decode(self, words):
        out, rest = [], []
        for w in words:
            if w == PAIR:  # zero-width filler (insert.Encoder.tag_pad)
                continue
            if PAIR <= w < PAIR + 0x4000:
                if rest:
                    out.append(super().decode(rest))
                    rest = []
                out.append(self.rev.get(w - PAIR >> 7, "?") + self.rev.get(w & 0x7F, "") if w & 0x7F else
                           self.rev.get(w - PAIR >> 7, "?"))
            else:
                rest.append(w)
        if rest:
            out.append(super().decode(rest))
        return "".join(ch for ch in "".join(out) if ch not in SPACERS)


def width(text, font=None):
    """Pixel advance of plain text (controls skipped, [XXXX] game glyphs 12 px)."""
    font = font or load()
    text = re.sub(r"\[[0-9A-Fa-f]{4}\]", "\0", text)
    text = gltext.TOKEN.sub("", text)
    return sum(12 if ch == "\0" else font[ch][2] for ch in text)


def render(out, text=None, scale=3):
    from PIL import Image
    font = load()
    chars = list(text) if text else [ch for ch in charset() if ch in font]
    W = sum(font[c][2] for c in chars) if text else 16 * 13
    H = GH + 1 if text else ((len(chars) + 15) // 16) * 14
    im = Image.new("RGB", (W + 2, H + 2), (24, 32, 72))
    x = y = 0
    for n, ch in enumerate(chars):
        if not text:
            x, y = (n % 16) * 13, (n // 16) * 14
        top, rows, adv = font[ch]
        sh = set()
        for ry, r in enumerate(rows):
            for rx, c in enumerate(r):
                if c == "#":
                    sh |= {(x + rx, y + top + ry + 1), (x + rx + 1, y + top + ry + 1)}
        for px, py in sh:
            im.putpixel((px, py), (40, 40, 40))
        for ry, r in enumerate(rows):
            for rx, c in enumerate(r):
                if c == "#":
                    im.putpixel((x + rx, y + top + ry), (240, 240, 240))
        x += adv
    im.resize((im.width * scale, im.height * scale), Image.NEAREST).save(out)


def selftest():
    c = EnCodec()
    s = "Carmaine, it's {n}me… {s:0001}Riviera!{end}"
    w = c.encode(s.replace("{end}", ""))
    assert c.decode(w) == s.replace("{end}", ""), c.decode(w)
    assert all(x < PAIR + 0x4000 or x >= 0xDFFF for x in w)
    assert c.encode("abc") == [PAIR + (0x61 << 7) + 0x62, PAIR + (0x63 << 7)]
    g, wd = tables()
    assert len(g) == 128 * 18 and wd[ord("A")] == 6 and wd[ord(" ")] == 4 and wd[0] == 0
    font = load()
    assert all(ch in font for ch in EXTRA.values()) and all(chr(c) in font for c in range(0x41, 0x5B))
    print("enfont selftest ok")


if __name__ == "__main__":
    a = sys.argv[1:]
    if a and a[0] == "render":
        render(a[1], a[2] if len(a) > 2 else None)
    else:
        selftest()
