"""fit.py: width / line lint for the English script against the window budgets (docs/windows.md).

    python -X utf8 tools/fit.py [IDPREFIX ..]      lint every entry with `en` (or only ids starting with a prefix)
    python -X utf8 tools/fit.py --text POOL "line"  lint one string as if it were an entry of POOL (e.g. scen, exe.items)

Exit 1 on any error. Budgets marked "guess" (not measured in-game yet) only warn. Port of ../growlanser-en/tools/fit.py;
PSP budgets re-measured (docs/windows.md).

Engine rule (docs/re/text.md): before each code the printer wraps on its own when its column s6 = ceil(x / 12)
reaches the window width W. The VWF draws a letter pair as one code, so a line fits when every code starts at
x <= 12 * (W - 1). An auto-wrap splits words where the engine decides, so in "wrap" windows any auto-wrap is an
error (wrap by hand with {n}); "clip" fields (name tag) cut the text at a pixel limit instead.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import enfont  # noqa: E402
import gltext  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
WAITS = (0xFFF9, 0xFFFA, 0xFFFB)  # wait codes: the pen continues (vwf.asm CONT_RA1), the start rule still holds
SUB_PX = 96  # shortcut: a {s:XXXX} name counts 8 cells (the longest name we allow); measure names when translated

# (id prefix, kind, columns or px, lines per page, measured). First match wins; scen entries are split further below.
BUDGETS = [
    ("scen.name", "clip", 144, 1, True),     # speaker name tag (scen entries with term null)
    ("scen.choice", "wrap", 24, 6, True),    # choice / script menu line after the "・" bullet
    ("scen", "wrap", 24, 3, True),           # dialogue box (with or without portrait)
    ("boot.names", "clip", 144, 1, True),    # name tag
    # "lower bound" rows (True): the field shows the pool's longest JP string, so it is at least that wide
    ("boot.units", "clip", 144, 1, True),    # lower bound: JP max 12 cells (battle UI not reached yet)
    ("boot.items", "wrap", 8, 1, True),      # item list, equip / status slots
    ("boot.magic", "wrap", 8, 1, True),      # lower bound: JP max 8 cells (spell list, same list routine as items)
    ("boot.skills", "wrap", 8, 1, True),     # lower bound: JP max 8 cells (shares the spell list column on PS1)
    ("boot.classes", "wrap", 11, 1, True),   # lower bound: JP max 11 cells
    ("boot.places", "wrap", 12, 1, True),    # one-line popup, 12 cells (field-menu bubble ruler, same popup routine)
    ("boot.help", "wrap", 24, 3, True),      # help box under menus
    ("boot.sys.0062", "wrap", 12, 1, True),  # field-menu bubbles 0062-0067 (popup, 12 cells)
    ("boot.sys.0063", "wrap", 12, 1, True),
    ("boot.sys.0064", "wrap", 12, 1, True),
    ("boot.sys.0065", "wrap", 12, 1, True),
    ("boot.sys.0066", "wrap", 12, 1, True),
    ("boot.sys.0067", "wrap", 12, 1, True),
    ("boot.sys.0102", "wrap", 24, 3, True),  # growth graph caption: lower bound (JP line 3 is 23 cells, heading centred)
    ("boot.sys.0103", "wrap", 4, 7, True),   # growth graph legend, a label per line: lower bound (JP max 4 cells)
    ("boot.sys.0121", "wrap", 8, 9, True),   # config labels, one per line
    ("boot.sys.012", "wrap", 8, 1, True),    # config values 0122-0129
    ("boot.sys.013", "wrap", 8, 1, True),    # config values 0130-0133
    ("boot.sys", "wrap", 24, 3, False),
    ("boot.dict", "wrap", 24, 3, False),     # English writes dictionary words out; kept for completeness
    ("boot.save", "clip", 999, 9, False),    # save-utility messages (system dialog font, not our VWF): phase 8
    ("boot.kbd", "clip", 999, 9, False),     # name-entry key grids: stay Japanese (D10)
    ("msys", "wrap", 24, 3, True),           # item / spell / skill descriptions (help box)
]


def budget(eid, entry=None):
    key = eid
    if eid.startswith("scen") and entry is not None:
        if entry.get("term") == "null":
            key = "scen.name"
        elif entry.get("en", "").lstrip().startswith("・"):
            key = "scen.choice"
    for b in BUDGETS:
        if key.startswith(b[0]):
            return b
    raise KeyError(eid)


def lint(text, b, font=None, codec=None):
    """Problems ([(error?, message)]) for one string under budget b."""
    font, codec = font or enfont.load(), codec or enfont.EnCodec()
    _, kind, size, lines, measured = b
    probs = []
    if b[0] == "scen.choice":
        text = text.lstrip()[1:]  # the budget counts from after the bullet column
    try:
        words = codec.encode(text)
    except ValueError as e:
        return [(True, str(e))]
    x, line, page_lines, i = 0, 1, 1, 0
    limit = 12 * (size - 1)
    while i < len(words):
        w = words[i]
        i += 1
        if w in (0xFFFC, 0xFFFD):
            if kind == "clip":
                probs.append((True, "line break in a one-line field"))
            x, line = 0, line + 1
            page_lines = 1 if w == 0xFFFD else page_lines + 1
            if page_lines > lines:
                probs.append((measured, "line %d: more than %d lines on a page (add {p})" % (line, lines)))
            continue
        if w in gltext.ARG1:
            arg = words[i]
            i += 1
            if w != 0xF600:
                continue
            adv = SUB_PX
        elif 0xF400 <= w < 0xF500:
            probs.append((True, "dictionary code {%04X} (writes Japanese): spell the word out" % w))
            continue
        elif w in WAITS:
            continue  # the pen continues (vwf_newstr continuation flag); PSP keeps the start rule (work/qa/s3c/wait)
        elif w >= 0xF000:
            continue
        elif w >= enfont.PAIR:
            a, c = (w - enfont.PAIR) >> 7, w & 0x7F
            adv = font[codec.rev[a]][2] + (font[codec.rev[c]][2] if c else 0)
        else:
            adv = 12
        if kind == "wrap" and x > limit:
            probs.append((measured, "line %d: auto-wraps at %d px (budget %d cells = %d px)" % (line, x, size, 12 * size)))
            x = 0
        x += adv
        if kind == "clip" and x > size:
            probs.append((measured, "line %d: %d px > %d px field" % (line, x, size)))
            break
    return probs


def entries(prefixes):
    for f in sorted((ROOT / "script").glob("*/*.json")):
        for e in json.loads(f.read_text(encoding="utf-8"))["entries"]:
            if e.get("en") and not e["id"].startswith("boot.save") and (  # boot.save: system font, not the VWF
                    not prefixes or any(e["id"].startswith(p) for p in prefixes)):
                yield e


def main(argv):
    font, codec = enfont.load(), enfont.EnCodec()
    if argv[:1] == ["--text"]:
        items = [{"id": argv[1], "en": argv[2], "term": "end"}]
    else:
        items = entries(argv)
    errs = warns = 0
    for e in items:
        for err, msg in lint(e["en"], budget(e["id"], e), font, codec):
            errs += err
            warns += not err
            print("%s %s: %s" % ("ERROR" if err else "warn ", e["id"], msg))
    print("%d errors, %d warnings" % (errs, warns))
    return 1 if errs else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
