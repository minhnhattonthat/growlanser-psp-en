"""Translation batches (docs/translator-brief.md): split untranslated text, check translator output, merge it back.

    python -X utf8 tools/batches.py split [--size 3500] [--only PREFIX]   work/tl/bNNN.tsv + build/terms_bNNN.txt
    python -X utf8 tools/batches.py check [bNNN ...]      a batch's .out.tsv; with no batch, all shipped English (for check.py)
    python -X utf8 tools/batches.py merge bNNN ... [--overwrite]   check, then write the wrapped English into script/
    python -X utf8 tools/batches.py wrap ID "English"     show how the wrapper lays out one line (dry-run fitter)
    python -X utf8 tools/batches.py edges [--write]       copy the JP's edge blanks / {n} into English that lost them
    python -X utf8 tools/batches.py choices [--write]     drop a final period from '・' choice lines (the JP has none)

Copied from the skill's assets/batches.py; ADAPTER fitted to Growlanser (script/*.json, {code} tokens, VWF budgets
from tools/fit.py). Translators write paragraphs: the wrapper adds {n} (and {p} in dialogue) by pixel width, so the
English stored in script/ is the wrapped form. Batch TSV: id, speaker, form, limit, JP. Output: work/tl/bNNN.out.tsv.
"""
import json
import re
import sys
from collections import Counter
from functools import lru_cache
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import enfont  # noqa: E402
import fit  # noqa: E402
import prefill  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
TL = ROOT / "work/tl"
SCRIPT = ROOT / "script"
GLOSSARY = ROOT / "glossary.md"
MAX_ENTRIES = 150
_rx = lru_cache(maxsize=None)(re.compile)  # per-term patterns: re's own 512-entry cache thrashed (28 min full check)

# ---- ADAPTER: this game's text format ----
TOKEN = re.compile(r"\{[^}\n]*\}|\[[0-9A-F]{4}\]")  # control codes, placeholders, [XXXX] icon glyphs
FREE = {"{n}", "{p}"}  # layout codes the English may place freely (the wrapper adds them)
DICT = re.compile(r"\{F4([0-9A-F]{2})\}")  # dictionary words: shown expanded to translators, spelled out in English
VARIABLE = r"\{s:[0-9A-F]{4}\}"  # a name the game draws: no suffix glued on
GLYPH_VARS = {"{s:0127}", "{s:012A}"}  # 目 drawn from the names table (PS1 0127, PSP 012A), a kanji: English spells the word
GLYPH_VARS |= {"{s:012E}", "{s:0047}"}  # PSP: 爪 ("Claw") in 爪か髪の毛, 教授 in 学院教授会 (faculty council)
GLYPH_VARS |= {"{s:011B}"}  # "Nick" as the ニック of パニック (its only use, scen166.0013): English writes "panic"
GLYPH_VARS |= {"[028B]", "[028C]", "[028D]", "[028E]"}  # ペンダント squeezed into 4 font cells: English spells "Pendant"
GLYPH_VARS |= {"[0107]"}  # a second 柱 glyph in 携帯集魔[0107] (boot.items.0282, the improved model): "Portable Pillar II"
GLYPH_VARS |= {"[0793]"}  # blank glyph in ＤＡＴＡ[0793]ＢＡＮＫ: its cell holds asm/vwf.asm now, English writes a space
LF = "{lf}"  # a raw newline (boot.save) as translators see and write it; check_batch turns it back into "\n"
HONORIFICS = {"さん": "-san", "ちゃん": "-chan", "くん": "-kun", "君": "-kun"}  # D1: honorifics kept
from insert import KEEP_JP, needs_english  # noqa: E402,F401  the one keep-list, shared with the inserter
WRAPPED = ("scen", "boot.help", "msys")  # multi-line boxes the wrapper lays out; {p} only added in scen dialogue
TABLES = ("boot.names", "boot.places", "boot.classes", "boot.units", "boot.items", "boot.magic", "boot.skills")
_font, _codec, _dict = None, None, None
# Edge blanks are layout (blank first line, indent, grid padding): the English keeps the JP's leading and trailing
# run of blanks / {n} exactly (edges(); `edges --write` copies them over). Exempt ids, with the reason:
EDGE_FREE = {  # skill rank labels "　１".."　９Ｂ": the MSYS packer (msyspack.events) takes no raw word < 0x80, so
    # no full-width blank; the blank only right-aligned a 12 px digit
    **{"msys.skills.%04d" % i: "MSYS packer: no full-width blank" for i in range(123, 133)},
    "scen014.0185": "blanks centre the English line (vqa ev_battle001 f2640: 7 left it 17 px off centre)",
}
_SILENT = r"\{(?!F4[0-9A-F]{2}\}|s:|FFE[89AB]\})[^}\n]*\}"  # codes that draw nothing (not dictionary/name/item/number vars)
LEAD = re.compile(r"^(?:%s|[ 　])*" % _SILENT)
TRAIL = re.compile(r"(?:%s|[ 　])*$" % _SILENT)


def edges(text):
    """(leading, trailing) layout of a string: its edge runs of codes and blanks, with only blanks and {n} kept."""
    keep = lambda run: "".join(re.findall(r"\{n\}|[ 　]", run))  # noqa: E731
    lead = LEAD.match(text).group()
    trail = TRAIL.search(text[len(lead):]).group()
    return keep(lead), keep(trail)


def restore_edges(jp, en):
    """en with the JP's edge layout, when both edge runs carry the same other codes in the same order; else None."""
    other = lambda run: re.sub(r"\{n\}|[ 　]", "", run)  # noqa: E731
    jl, el = LEAD.match(jp).group(), LEAD.match(en).group()
    jt, et = TRAIL.search(jp[len(jl):]).group(), TRAIL.search(en[len(el):]).group()
    if other(jl) == other(el) and other(jt) == other(et):
        return jl + en[len(el):len(en) - len(et)] + jt
    if edges(en) == ("", ""):  # codes moved (colour inside the JP's indent): blanks go outside the English's codes
        return edges(jp)[0] + en + edges(jp)[1]
    return None


def docs():
    """(path, doc, entries) per script file."""
    for path in sorted(SCRIPT.rglob("*.json")):
        doc = json.loads(path.read_text(encoding="utf-8"))
        yield path, doc, doc["entries"]


def group_of(entry):
    return entry["id"]


def entry_key(entry):
    return entry["id"]


def budget(entry, en=None):
    return fit.budget(entry["id"], {**entry, "en": en if en is not None else entry["jp"]})


def form_of(entry):
    b = budget(entry)
    if b[0] == "scen.name" or entry["id"].startswith(("boot.names", "boot.units")):
        return "name"
    if b[0] == "scen.choice":
        return "choice"
    if b[0] == "scen":
        return "dlg"
    if entry["id"].startswith(("boot.help", "msys")):
        return "desc"
    return "menu"


def limit_label(entry):
    _, kind, size, lines, _ = budget(entry)
    if kind == "clip":
        return f"{size}px one line"
    if entry["id"].startswith(WRAPPED) and form_of(entry) == "dlg":
        return "auto-wrapped, 3 lines a page"
    if entry["id"].startswith(WRAPPED):
        return f"auto-wrapped, max {lines} lines (~{lines * 46} chars)"
    if lines > 1 and size <= 8:
        return f"{size} cells (~{size * 2} chars) per {{n}} line"
    return f"{size} cells (~{size * 2} chars), one line"


def tools():
    global _font, _codec
    if _font is None:
        _font, _codec = enfont.load(), enfont.EnCodec()
    return _font, _codec


def fits(line, b):
    """One line fits when the engine would not auto-wrap it (fit.lint is the oracle)."""
    font, codec = tools()
    probs = fit.lint(line, (b[0], b[1], b[2], 99, True), font, codec)
    return not any("auto-wraps" in m for _, m in probs)


def wrap(entry, en):
    """Lay out translator English: hard {n}/{p} kept, words flowed by pixel width, pages of 3 lines in dialogue."""
    b = budget(entry, en)
    if b[1] != "wrap" or b[0] in ("scen.choice",) or not entry["id"].startswith(WRAPPED):
        return en
    pages = []
    for page in en.split("{p}"):
        if b[0] == "scen" and "{n}" not in page and "　" not in page and not page.startswith(" "):
            pages += page_flow(page.split(), b, b[3])
            continue
        lines = []
        for hard in page.split("{n}"):
            body = hard.lstrip(" ")
            lead = hard[:len(hard) - len(body)]
            body = body.rstrip(" ")
            trail = hard[len(lead) + len(body):]  # edge blanks are layout: kept as they are
            cur = ""
            for w in body.split(" "):
                if w == "":
                    continue
                cand = f"{cur} {w}" if cur else lead + w
                if cur and not fits(cand, b):
                    lines.append(cur)
                    cand = w
                cur = cand
            lines.append((cur or lead) + trail)
        if b[0] == "scen":
            pages += ["{n}".join(lines[i:i + b[3]]) for i in range(0, len(lines), b[3])]
        else:
            pages.append("{n}".join(lines))
    return widows(entry, "{p}".join(pages))


SENT_END = re.compile(r"[.!?…♪][\"')]*$")
NOT_END = {"Mr.", "Mrs.", "Ms.", "Dr.", "St."}


def sentence_end(word):
    return bool(SENT_END.search(word)) and word not in NOT_END


def page_flow(words, b, per_page):
    """Greedy lines, per_page a page; a page that would end mid-sentence ends at its last sentence end instead
    ("...overrun us in no{p}time." -> the whole sentence on the next page). A sentence longer than a page still
    breaks where the page fills."""
    pages, i = [], 0
    while i < len(words):
        lines, cur, j, cut = [], "", i, None
        while j < len(words):
            cand = f"{cur} {words[j]}" if cur else words[j]
            if cur and not fits(cand, b):
                lines.append(cur)
                cur = ""
                if len(lines) == per_page:
                    break
                continue
            cur = cand
            if sentence_end(words[j]) and j + 1 < len(words):
                cut = (j, len(lines), cur)
            j += 1
        else:
            lines.append(cur)
        if cur == "" and j < len(words) and cut and not sentence_end(words[j - 1]):
            j, n, cur = cut
            lines, j = lines[:n] + [cur], j + 1
        pages.append("{n}".join(lines))
        i = j
    return pages


def widows(entry, en):
    """A page's one-word last line takes the line above's last word, when that line doesn't end a sentence."""
    b = budget(entry, en)
    pages = en.split("{p}")
    for i, page in enumerate(pages):
        lines = page.split("{n}")
        if len(lines) < 2 or " " in lines[-1].strip() or "{" in lines[-1] or not lines[-1].strip():
            continue
        head, _, word = lines[-2].rstrip(" ").rpartition(" ")
        if not head.strip() or "{" in word or head.rstrip()[-1] in ".!?…:;" or not fits(f"{word} {lines[-1]}", b):
            continue
        lines[-2:] = [head, f"{word} {lines[-1]}"]
        pages[i] = "{n}".join(lines)
    return "{p}".join(pages)


def fix_widows(write):
    fixed = 0
    for path, doc, entries in docs():
        touched = False
        for e in entries:
            b = budget(e, e["en"]) if e.get("en") else None
            if not b or e["id"] in KEEP_JP or b[1] != "wrap" or b[0] == "scen.choice" \
                    or not e["id"].startswith(WRAPPED):
                continue
            new = widows(e, e["en"])
            if new != e["en"]:
                fixed += 1
                e["en"], touched = new, True
        if touched and write:
            path.write_text(json.dumps(doc, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
    print(f"widows: {fixed} fixed{'' if write else ' (dry run: --write)'}")
    return 0


CHOICE_END = re.compile(r"^([ 　]*・.*[^.])\.$")


def choice_period(entry, en):
    """en with the final period dropped from each '・' choice line whose JP line has no 。 (lines paired by {n}/{p})."""
    jp, parts = re.split(r"\{[np]\}", entry["jp"]), re.split(r"(\{[np]\})", en)
    if len(jp) * 2 - 1 != len(parts):
        return en
    for i, line in enumerate(parts[::2]):
        if not jp[i].rstrip().endswith("。"):
            parts[2 * i] = CHOICE_END.sub(r"\1", line)
    return "".join(parts)


def fix_choice_periods(write):
    fixed = 0
    for path, doc, entries in docs():
        touched = False
        for e in entries:
            if not e.get("en") or e["id"] in KEEP_JP:
                continue
            new = choice_period(e, e["en"])
            if new != e["en"]:
                fixed += 1
                e["en"], touched = new, True
        if touched and write:
            path.write_text(json.dumps(doc, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
    print(f"choice periods: {fixed} fixed{'' if write else ' (dry run: --write)'}")
    return 0


def width_problems(entry, en):
    if entry["id"].startswith("boot.save"):  # utf-8 system dialog (PSP OS font), not our VWF: measured in phase 8
        return []
    font, codec = tools()
    return [m for err, m in fit.lint(wrap(entry, en), budget(entry, en), font, codec) if err]


def encodable(char):
    """Letters the English font has (font/en12.txt) plus the choice bullet."""
    try:
        tools()[1].encode(char)
        return True
    except ValueError:
        return False


def show_jp(entry):
    """JP as translators see it: dictionary codes expanded, JP line breaks as ' / '."""
    global _dict
    if _dict is None:
        d = json.loads((SCRIPT / "boot/dict.json").read_text(encoding="utf-8"))["entries"]
        _dict = {int(e["id"][-4:]): e["jp"] for e in d}
    jp = DICT.sub(lambda m: _dict.get(int(m[1], 16), ""), entry["jp"])
    jp = jp.replace("\n", LF)  # boot.save system-dialog strings hold raw newlines: one TSV row each
    return jp.replace("{n}", " / ") if entry["id"].startswith(WRAPPED) else jp  # menus keep their {n} rows
# ---- end of ADAPTER ----


def kind(char):
    if "぀" <= char <= "ゟ":
        return "hiragana"
    if "゠" <= char <= "ヿ":
        return "katakana"
    if "一" <= char <= "鿿" or char == "々":
        return "kanji"
    return "other"


def has_term(jp, term):
    """term occurs as a whole kana or kanji run: ミン isn't in タイミング, くも isn't in ぼくも."""
    jp = jp.replace(" / ", "")
    if term not in jp:
        return False
    for m in _rx(re.escape(term)).finditer(jp):
        a, b = m.start(), m.end()
        if (a == 0 or kind(jp[a - 1]) != kind(term[0])) and (b == len(jp) or kind(jp[b]) != kind(term[-1])):
            return True
    return False


def glossary():
    """[(JP forms, EN forms, avoid forms)] from glossary.md's | JP | EN | max | notes | Avoid | tables."""
    rows = []
    if not GLOSSARY.exists():
        return rows
    for line in GLOSSARY.read_text(encoding="utf-8").splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if line.startswith("|") and len(cells) >= 2 and cells[0] not in ("JP", "") and not set(cells[0]) <= set("-: "):
            avoid = [x.strip() for x in cells[4].split("/") if x.strip()] if len(cells) > 4 else []
            rows.append(([x.strip() for x in cells[0].split("/")], [x.strip() for x in cells[1].split("/")], avoid))
    return rows


def problems(entry, en, terms):
    """Every rule, on one line of English."""
    jp = entry["jp"]
    if not en.strip():
        return ["empty English"]
    out = []
    plain = TOKEN.sub("", en).replace("\n", "")
    if choice_period(entry, en) != en:
        out.append("choice line ends with a period (the JP's has none): drop it")
    if bad := sorted({c for c in plain if not encodable(c)}):
        out.append(f"unencodable characters {bad} (font has ASCII letters/punctuation and é … — ♪ ♥ only)")
    if re.search(r"\\u[0-9a-fA-F]{4}", en) or "\t" in en or "\\n" in en:
        out.append("escape sequence or tab in the English (write {n} for a forced line break)")
    free = FREE if entry["id"].startswith(WRAPPED) else set()  # menu/list strings keep one {n} per row
    want = Counter(t for t in TOKEN.findall(jp) if t not in free | GLYPH_VARS and not DICT.fullmatch(t))
    have = Counter(t for t in TOKEN.findall(en) if t not in free)
    if want != have:
        out.append(f"control codes differ: JP {dict(want)} EN {dict(have)}")
    if entry["id"] not in EDGE_FREE and edges(en) != edges(jp):
        out.append("edge blanks are layout: keep the JP's leading/trailing blanks and {n} %r (EN %r)"
                   % (edges(jp), edges(en)))
    if jp.lstrip().startswith("・") != en.lstrip().startswith("・"):
        out.append("choice lines start with the bullet ・ exactly when the JP does")
    if re.search(VARIABLE + r"(st|nd|rd|th|s)\b", en):
        out.append("suffix glued to a name variable (only a possessive 's may follow it)")
    if re.search(VARIABLE + r"-(san|chan|kun|sama)\b", en):
        out.append("no honorific after a name variable: drop it (PS1 rule, 90 of 90 lines)")
    jp_plain = TOKEN.sub("", show_jp(entry))
    en_terms = " ".join(TOKEN.sub(" ", en).split()).lower()
    for jps, ens, avoid in terms:
        if any(has_term(jp_plain, j) for j in jps) and not any(" ".join(e.split()).lower() in en_terms for e in ens):
            out.append(f"glossary: {jps[0]} -> {ens[0]}")
        out += [f"glossary Avoid: {a}" for a in avoid if _rx(rf"\b{re.escape(a)}\b").search(en)]
    names = [j for jps, _, _ in terms if re.fullmatch(r"[ァ-ヺー・]+", jps[0]) for j in jps]  # katakana names
    for jp_form, en_form in HONORIFICS.items():  # after a name only: メイドさん is "maid", not "maid-san"
        if jp_form in jp_plain and any(_rx(rf"(?<![ァ-ヺー]){n}{jp_form}").search(jp_plain) for n in names) and en_form.lower() not in en.lower():
            out.append(f"honorific {jp_form} needs {en_form}")
    return out + width_problems(entry, en)


def index():
    result = {}
    for _, _, entries in docs():
        for e in entries:
            key = entry_key(e)
            if key in result:
                raise ValueError(f"duplicate batch key {key!r}")
            result[key] = e
    return result


def read_tsv(path):
    return [line.split("\t") for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def existing():
    return sorted(TL.glob("b[0-9][0-9][0-9].tsv"))


def table_terms():
    """Translated name / item / spell table rows (JP of 2+ characters) as reference terms for dialogue batches."""
    out = {}
    for _, _, entries in docs():
        for e in entries:
            if e["id"].startswith(TABLES) and e.get("en") and len(TOKEN.sub("", e["jp"])) >= 2:
                out.setdefault(TOKEN.sub("", e["jp"]), e["en"])
    return out


def cast(path):
    """A scene's speaker names (its term-null strings), to tell translators who can talk in it."""
    doc = json.loads(path.read_text(encoding="utf-8"))
    return [e["jp"] for e in doc["entries"] if e.get("term") == "null" and e["jp"]]


def ps1_reference(batch, near, order):
    """`near id | PS1 JP => EN` for reworded lines, `ctx id | JP => EN` for the translated lines around each run."""
    out, ids = [], {e["id"] for e in batch}
    for e in batch:
        if e["id"].startswith(("scen", "msys", "boot.help")) and (c := near(e)):
            out.append(f"near {e['id']} | {c['jp']} => {c['en']}\n")
        entries, i = order[e["id"]]
        if i == 0 or entries[i - 1]["id"] not in ids:  # start of a run: up to 2 translated lines before
            out += [f"ctx {x['id']} | {x['jp']} => {x['en']}\n" for x in entries[max(0, i - 2):i] if x.get("en")]
        if i + 1 < len(entries) and entries[i + 1]["id"] not in ids and entries[i + 1].get("en"):
            x = entries[i + 1]
            out.append(f"ctx {x['id']} | {x['jp']} => {x['en']}\n")
    return out


def split(size, only):
    """Numbers on from the last batch and leaves out ids already batched, so a repeat run can't duplicate work."""
    index()
    TL.mkdir(parents=True, exist_ok=True)
    (ROOT / "build").mkdir(exist_ok=True)
    taken = {r[0] for p in existing() for r in read_tsv(p)}
    n = max((int(p.stem[1:]) for p in existing()), default=0)
    groups, scene_of = {}, {}
    for path, _, entries in docs():
        for e in entries:
            if needs_english(e) and entry_key(e) not in taken and e["id"].startswith(only):
                groups.setdefault(group_of(e), []).append(e)
                scene_of[e["id"]] = path
    batches, cur, chars = [], [], 0
    for group in groups.values():
        c = sum(len(TOKEN.sub("", show_jp(e))) for e in group)
        if cur and (chars + c > size or len(cur) + len(group) > MAX_ENTRIES):
            batches.append(cur)
            cur, chars = [], 0
        cur += group
        chars += c
    if cur:
        batches.append(cur)
    terms, tterms = glossary(), table_terms()
    near, order = prefill.Near(), {}
    for _, _, entries in docs():
        order.update({e["id"]: (entries, i) for i, e in enumerate(entries)})
    for batch in batches:
        n += 1
        name = f"b{n:03d}"
        path = TL / f"{name}.tsv"
        if path.exists():
            sys.exit(f"{path} already exists")
        rows = [f"{entry_key(e)}\t\t{form_of(e)}\t{limit_label(e)}\t{show_jp(e)}" for e in batch]
        path.write_text("\n".join(rows) + "\n", encoding="utf-8", newline="\n")
        jps = " ".join(TOKEN.sub("", show_jp(e)) for e in batch)
        used = [f"{j}\t{ens[0]}\n" for jpl, ens, _ in terms for j in jpl if has_term(jps, j)]
        ref = [f"{j}\t{en}\t(game table, reference)\n" for j, en in tterms.items() if has_term(jps, j)]
        scenes = sorted({scene_of[e["id"]] for e in batch if e["id"].startswith("scen")})
        casts = [f"cast of {p.stem}: {' / '.join(cast(p))}\n" for p in scenes]
        refs = ["## PS1 reference\n"] + ps1_reference(batch, near, order)
        (ROOT / f"build/terms_{name}.txt").write_text("".join(used + ref + casts + refs), encoding="utf-8",
                                                      newline="\n")
    print(f"{len(batches)} new batches in {TL}, {len(taken)} ids already batched")


def check_batch(batch, entries, terms):
    want = [r[0] for r in read_tsv(TL / f"{batch}.tsv")]
    rows = [(r[0], "\t".join(r[1:]).strip(" \r\n").replace(LF, "\n"))  # keeps U+3000 edges
            for r in read_tsv(TL / f"{batch}.out.tsv")]
    bad = []
    if [r[0] for r in rows] != want:
        got = [r[0] for r in rows]
        dup = sorted(i for i, c in Counter(got).items() if c > 1)
        bad.append(f"ids differ: missing {sorted(set(want) - set(got))[:8]} extra {sorted(set(got) - set(want))[:8]} "
                   f"duplicate {dup[:8]} (order must match too)")
    for eid, en in rows:
        if eid in entries:
            bad += [f"{eid}: {p}: {en!r}" for p in problems(entries[eid], en, terms)]
    return bad, {eid: wrap(entries[eid], en) for eid, en in rows if eid in entries}


def merge(new, overwrite):
    """Refuses to replace different English unless told to, before anything is written."""
    if not overwrite:
        for _, _, entries in docs():
            for e in entries:
                if entry_key(e) in new and e.get("en") and e["en"] != new[entry_key(e)]:
                    sys.exit(f"{e['id']} would lose {e['en']!r}: pass --overwrite if that is meant")
    changed = 0
    for path, doc, entries in docs():
        touched = False
        for e in entries:
            if entry_key(e) in new and e.get("en") != new[entry_key(e)]:
                e["en"] = new[entry_key(e)]
                touched = True
                changed += 1
        if touched:
            path.write_text(json.dumps(doc, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
    print(f"merged: {changed} entries changed")


def fix_edges(write):
    """Copy the JP's edge layout into every English that lost it; print what can't be done mechanically."""
    fixed = manual = 0
    for path, doc, entries in docs():
        touched = False
        for e in entries:
            if not e.get("en") or e["id"] in KEEP_JP or e["id"] in EDGE_FREE:
                continue
            new = e["en"]
            if edges(new) != edges(e["jp"]):
                new = restore_edges(e["jp"], new)
                if new is None:
                    manual += 1
                    print(f"manual {e['id']}: JP {e['jp'][:60]!r} EN {e['en'][:60]!r}")
                    continue
            font, codec = tools()
            if any(err for err, _ in fit.lint(new, budget(e, new), font, codec)):
                new = wrap(e, new)  # an indent pushed a line over: flow the words again
                if bad := width_problems(e, new):
                    print(f"width  {e['id']}: {new[:70]!r}: {bad[0]}")
            if new != e["en"]:
                fixed += 1
                e["en"], touched = new, True
        if touched and write:
            path.write_text(json.dumps(doc, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
    print(f"edges: {fixed} restored{'' if write else ' (dry run: --write)'}, {manual} need a hand")
    return 0


def main(argv):
    if not argv:
        sys.exit(__doc__)
    cmd, args = argv[0], argv[1:]
    if cmd == "split":
        size = int(args[args.index("--size") + 1]) if "--size" in args else 3500
        return split(size, args[args.index("--only") + 1] if "--only" in args else "")
    if cmd == "wrap":
        e = index()[args[0]]
        out = wrap(e, args[1])
        print(out.replace("{p}", "\n--- page ---\n").replace("{n}", "\n"))
        print("\n".join(problems(e, args[1], glossary())) or "OK")
        return 0
    if cmd == "edges":
        return fix_edges("--write" in args)
    if cmd == "widows":
        return fix_widows("--write" in args)
    if cmd == "choices":
        return fix_choice_periods("--write" in args)
    overwrite = "--overwrite" in args
    names = [a for a in args if a != "--overwrite"]
    entries, terms = index(), glossary()
    if cmd == "check" and not names:
        bad = [f"{i}: missing English" for i, e in entries.items() if needs_english(e)]
        bad += [f"{i}: {p}: {e['en']!r}" for i, e in entries.items() if e.get("en") and i not in KEEP_JP
                for p in problems(e, e["en"], terms)]
        print(f"{len(entries)} entries, {len(bad)} problems")
        print("\n".join(bad[:200]))
        return 1 if bad else 0
    if cmd not in ("check", "merge") or not names:
        sys.exit(__doc__)
    failed = 0
    for batch in names:
        bad, rows = check_batch(batch, entries, terms)
        failed += bool(bad)
        print(f"{batch}: " + ("OK" if not bad else f"{len(bad)} problems"))
        for line in bad:
            print("  " + line)
        if cmd == "merge" and not bad:
            merge(rows, overwrite)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
