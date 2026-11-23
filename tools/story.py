"""Story-pass chapter files (skill translation.md §Review): every shown scene line, JP / EN, in chapter order.

    python -X utf8 tools/story.py [--max 90000]   -> work/qa/story/chapters/cNN[_P].txt (old files removed)
    python qa_gate.py init work/qa/story/manifest.tsv work/qa/story/chapters --glob "*.txt"

Port of the PS1 repo's story.py. docs/synopsis.md §2 lists chapters by PS1 scene id: a PSP scene joins the chapter of
the PS1 scene it shares most lines with (prefill.scene_map). The 43 PSP-only scenes (work/psp_scenes.txt, synopsis
§6) get their own chapters: c16 Darkfall arc (§6 plot order), c17 PSP extras. c18 = branches (synopsis §3), c19 = the
rest (optional, system, debug). Unreferenced entries ("unref") are never shown and are left out.
Each line is marked "=" when its JP and EN pair equals a PS1 pair (read in the PS1 repo's story pass) or "*" (new
or changed on PSP: the lines this pass must read closely).
"""
import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from prefill import ps1_index, scene_map  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "work/qa/story/chapters"
VOICE = re.compile(r"\{v:[0-9A-F]{4}\}")
BRANCH = "s013 s020 s093 s101 s147-s154 s237-s261 s033 s041 s047 s203-s204 s195 s248 s011".split()  # PS1 ids, §3
# PSP ids, synopsis §6 "Plot in scene order"; s185 is the developer jump menu (c19)
DARKFALL = ("s092 s279 s280 s156 s157 s158 s159 s160 s161 s162 s163 s165 s166 s167 s169 s170 s171 s172 s186 "
            "s174 s175 s176 s177 s179 s180 s183 s184 s284 s285 s286 s290 s291").split()
EXTRAS = "s187 s329 s330 s331 s332 s333 s325 s326 s327 s328".split()


def expand(spec):
    """'s021–s022, s089' -> ['s021', 's022', 's089']."""
    out = []
    for part in re.split(r"[,\s]+", spec.strip()):
        m = re.fullmatch(r"s(\d{3})(?:[–-]s(\d{3}))?", part)
        if m:
            a, b = int(m[1]), int(m[2] or m[1])
            out += ["s%03d" % i for i in range(a, b + 1)]
    return out


def chapters():
    rows = []
    for line in (ROOT / "docs/synopsis.md").read_text(encoding="utf-8").splitlines():
        m = re.match(r"\| (\d+)\. ([^|]+) \| ([^|]+) \|", line)
        if m:
            rows.append((int(m[1]), m[2].strip(), expand(m[3])))
    return rows


def show(text):
    return VOICE.sub("", text).replace("{n}", " ").replace("{p}", " ¶ ")


def scene_text(sid, ps1_pairs, ps1_of=None):
    doc = json.loads((ROOT / f"script/scen/{sid}.json").read_text(encoding="utf-8"))
    cast = [e["en"] or e["jp"] for e in doc["entries"] if e.get("term") == "null" and e["jp"]]
    rows, new = [], 0
    for e in doc["entries"]:
        if e["jp"] and e.get("term") != "null" and not e.get("unref"):
            mark = "=" if (e["jp"], e["en"]) in ps1_pairs else "*"
            new += mark == "*"
            rows += [f">> {e['id']} {mark} | {show(e['jp'])}", f"   {show(e['en'])}"]
    src = f", PS1 {ps1_of}" if ps1_of else ""
    head = f"## {sid} ({new} new of {len(rows) // 2}{src}; names in scene: {', '.join(cast) or '-'})"
    return "\n".join([head] + rows) + "\n", new


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--max", type=int, default=90000)
    a = ap.parse_args()
    by_jp = ps1_index(ROOT.parent / "growlanser-en")
    ps1_pairs = {(jp, c[2]) for jp, cands in by_jp.items() for c in cands}
    smap = {"s" + k[4:]: "s" + v[4:] for k, v in scene_map(by_jp).items() if k.startswith("scen")}
    every = sorted(p.stem for p in (ROOT / "script/scen").glob("s*.json"))
    psp_only = set(DARKFALL + EXTRAS + ["s185"])
    seen, plan = set(DARKFALL + EXTRAS), []
    for num, title, ps1_scenes in chapters():
        own = [s for s in every if s not in seen and smap.get(s) in ps1_scenes]
        own.sort(key=lambda s: (ps1_scenes.index(smap[s]), s))
        seen |= set(own)
        plan.append((num, title, own))
    plan.append((16, "The Darkfall arc (PSP only, synopsis §6)", DARKFALL))
    plan.append((17, "PSP extras: Fairy Café and companion events (synopsis §6)", EXTRAS))
    branch = expand(" ".join(BRANCH))
    own = [s for s in every if s not in seen and smap.get(s) in branch]
    seen |= set(own)
    plan.append((18, "Relationships, branches and endings (synopsis §3)", own))
    plan.append((19, "Optional, system and debug scenes (synopsis §3, §5)", [s for s in every if s not in seen]))
    assert not (psp_only - set(every)), psp_only - set(every)
    OUT.mkdir(parents=True, exist_ok=True)
    for old in OUT.glob("*.txt"):
        old.unlink()
    for num, title, scenes in plan:
        parts, cur, new = [], "", 0
        for s in scenes:
            t, n = scene_text(s, ps1_pairs, None if s in psp_only else smap.get(s))
            if cur and len(cur) + len(t) > a.max:
                parts.append((cur, new))
                cur, new = "", 0
            cur += t
            new += n
        parts.append((cur, new))
        for i, (body, n) in enumerate(parts, 1):
            name = f"c{num:02d}" + (f"_{i}" if len(parts) > 1 else "")
            head = f"# Chapter {num}. {title}" + (f" (part {i}/{len(parts)})" if len(parts) > 1 else "")
            head += ("\n# '¶' = page break; voice codes removed. '=' = JP/EN pair as in the PS1 translation (story-"
                     "reviewed there), '*' = new or changed on PSP.\n\n")
            (OUT / f"{name}.txt").write_text(head + body, encoding="utf-8", newline="\n")
            print(f"{name}.txt {len(body)} chars, {n} new lines")


if __name__ == "__main__":
    main()
