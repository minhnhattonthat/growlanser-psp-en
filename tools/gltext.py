"""gltext.py: Growlanser 16-bit text codec (u16 little-endian words <-> editable text).

Words:
  < 0xF000  glyph index; tbl/jp.tbl gives the character, else it decodes as [XXXX]
  F600 a    {s:XXXX}   substitute a string (name) by index a          (1 argument word)
  F700 a    {f7:XXXX}  (1 argument word, skipped by the engine)
  F800 a    {v:XXXX}   voice clip a (VOICE.XA)                         (1 argument word)
  FFFC      {n}        new line
  FFFD      {p}        new page (wait for a button)
  FFFE      {end}      end of message
  FFFF      {null}     empty slot
  other >= F000: {XXXX}  (high byte = command, low byte = parameter; no argument words)
A character mapped by two codes (ー, 館) decodes as itself only for the first code; the other comes out as [XXXX]
so encode(decode(w)) == w always.
"""
import re
import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NAMED = {0xFFFC: "n", 0xFFFD: "p", 0xFFFE: "end", 0xFFFF: "null"}
NAMED_ENC = {v: k for k, v in NAMED.items()}
ARG1 = {0xF600: "s", 0xF700: "f7", 0xF800: "v"}
ARG1_ENC = {v: k for k, v in ARG1.items()}
TOKEN = re.compile(r"\{(\w+)(?::([0-9A-Fa-f]{4}))?\}|\[([0-9A-Fa-f]{4})\]")


class Codec:
    def __init__(self, tbl=ROOT / "tbl" / "jp.tbl"):
        self.dec, self.enc = {}, {}
        for line in Path(tbl).read_text(encoding="utf-8").splitlines():
            if not line or line.startswith("#"):
                continue
            k, _, v = line.partition("=")
            code = int(k, 16)
            v = " " if v == r"\s" else v
            self.dec[code] = v
            self.enc.setdefault(v, code)

    def decode(self, words):
        out, i = [], 0
        while i < len(words):
            w = words[i]
            if w in ARG1 and i + 1 < len(words):
                out.append("{%s:%04X}" % (ARG1[w], words[i + 1]))
                i += 2
                continue
            if w in NAMED:
                out.append("{%s}" % NAMED[w])
            elif w >= 0xF000:
                out.append("{%04X}" % w)
            elif w in self.dec and self.enc[self.dec[w]] == w:
                out.append(self.dec[w])
            else:
                out.append("[%04X]" % w)
            i += 1
        return "".join(out)

    def encode(self, text):
        words, i = [], 0
        while i < len(text):
            m = TOKEN.match(text, i)
            if m:
                name, arg, raw = m.groups()
                if raw:
                    words.append(int(raw, 16))
                elif name in ARG1_ENC:
                    words += [ARG1_ENC[name], int(arg, 16)]
                elif name in NAMED_ENC:
                    words.append(NAMED_ENC[name])
                elif re.fullmatch(r"[0-9A-Fa-f]{4}", name):
                    words.append(int(name, 16))
                else:
                    raise ValueError(f"unknown control {m.group(0)!r} in {text!r}")
                i = m.end()
                continue
            ch = text[i]
            if ch not in self.enc:
                raise ValueError(f"no code for {ch!r} in {text!r}")
            words.append(self.enc[ch])
            i += 1
        return words


def words_of(data, off, n):
    return list(struct.unpack_from("<%dH" % n, data, off))


def pack(words):
    return struct.pack("<%dH" % len(words), *words)
