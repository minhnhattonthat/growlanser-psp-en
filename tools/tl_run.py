"""tl_run.py: run translation batches through `codex exec` (no subagents in an Orca worker; translation.md §Review).

    python -X utf8 tools/tl_run.py pipeline [bNNN ..|--all] [-j 6] [--lock NAME]   translate -> check -> review
                                                                      -> fix -> merge
    python -X utf8 tools/tl_run.py synopsis [-j 6]                    scene summaries -> docs/synopsis.md draft
    python -X utf8 tools/tl_run.py psp-scenes sNNN .. [-j 6]          PSP-only scene summaries -> synopsis section
    python -X utf8 tools/tl_run.py pairs bNNN ..                      reviewer pairs file work/tl/pairs/bNNN.txt
    python -X utf8 tools/tl_run.py status                             per-batch state

Per batch (work/tl/): bNNN.out.tsv (passing English), bNNN.report.txt (translator report), reviews/bNNN.md
(review; Minors -> docs/polish.md), bNNN.done (merged into script/). Codex runs read-only with the brief, terms and
batch in the prompt; its final message is parsed, so it never writes repo files. Logs: work/tl/log/.
"""
import json
import re
import shutil
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import batches  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
TL = ROOT / "work/tl"
LOG = TL / "log"
REV = TL / "reviews"
LOCK = threading.Lock()
ROW = re.compile(r"^((?:scen|boot|msys)[\w.]*\.\d{4})\t(.*)$")
ID = r"\b(?:scen|boot|msys)[\w.]*\.\d{4}"
FIX_ROUNDS = 3


def read(p):
    return (ROOT / p).read_text(encoding="utf-8")


def codex(prompt, tag):
    """One read-only codex run; returns its final message ('' on failure after retries)."""
    LOG.mkdir(parents=True, exist_ok=True)
    out = LOG / f"{tag}.out.md"
    for attempt in range(3):
        out.unlink(missing_ok=True)
        try:
            r = subprocess.run([shutil.which("codex"), "exec", "-s", "read-only", "--skip-git-repo-check", "-o",
                                str(out), "-"], input=prompt, text=True, encoding="utf-8", cwd=ROOT,
                               capture_output=True, timeout=3600)
            (LOG / f"{tag}.stderr.txt").write_text((r.stderr or "")[-4000:] + f"\n[rc {r.returncode}] stdout tail:\n"
                                                    + (r.stdout or "")[-2000:], encoding="utf-8")
        except subprocess.TimeoutExpired:
            pass
        if out.exists() and out.stat().st_size:
            return out.read_text(encoding="utf-8")
        time.sleep(60 * (attempt + 1))
    return ""


def rulings():
    g = read("glossary.md")
    return g[:g.index("## Characters")]


def tl_prompt(b, prev=None, errors=None, issues=None):
    head = (read("docs/translator-brief.md") + "\n\n# Glossary rulings\n" + rulings()
            + "\n\n# docs/style-reference.md\n" + read("docs/style-reference.md"))
    if (ROOT / "docs/synopsis.md").exists():
        head += "\n\n# docs/synopsis.md\n" + read("docs/synopsis.md")
    head += f"\n\n# build/terms_{b}.txt\n" + read(f"build/terms_{b}.txt")
    head += f"\n\n# work/tl/{b}.tsv\n" + read(f"work/tl/{b}.tsv")
    head += ("\n\n# How to answer\nYou cannot run the check tool or write files here: the controller runs "
             "`tools/batches.py check` on your answer. Reply with the complete output TSV (every id, same order, "
             "`id<TAB>English`, real tab characters) in one ```tsv fenced block, then the report lines after it.")
    if prev:
        head += f"\n\n# Your previous output\n```tsv\n{prev}\n```\n"
    if errors:
        head += "\n# The check tool reported these problems; fix them and return the complete corrected TSV\n" + errors
    if issues:
        head += ("\n# A reviewer reported these Critical/Important issues; fix each (judge the suggestion, keep "
                 "voice and control codes) and return the complete corrected TSV\n" + issues)
    return head


def parse_rows(msg):
    m = re.search(r"```(?:tsv)?\n(.*?)```", msg, re.S)
    body = m.group(1) if m else msg
    rows = [ROW.match(line.rstrip("\r")) for line in body.splitlines()]
    return [f"{r[1]}\t{r[2].strip()}" for r in rows if r]


def check(b):
    with LOCK:
        entries, terms = batches.index(), batches.glossary()
    bad, _ = batches.check_batch(b, entries, terms)
    return bad


def translate(b, issues=None):
    out = TL / f"{b}.out.tsv"
    prev = out.read_text(encoding="utf-8").strip() if issues and out.exists() else None
    errors = None
    for rnd in range(FIX_ROUNDS + 1):
        msg = codex(tl_prompt(b, prev, errors, issues if rnd == 0 else None), f"{b}.{'fix' if issues else 'tl'}{rnd}")
        rows = parse_rows(msg)
        if not rows:
            errors = "Your answer had no parsable TSV rows."
            continue
        out.write_text("\n".join(rows) + "\n", encoding="utf-8", newline="\n")
        report = msg[msg.rfind("```") + 3:].strip() if "```" in msg else ""
        with open(TL / f"{b}.report.txt", "a", encoding="utf-8") as f:
            f.write(report + "\n")
        bad = check(b)
        if not bad:
            return True
        prev, errors = "\n".join(rows), "\n".join(bad[:80])
    return False


def pairs(b):
    jp = {r[0]: r for r in batches.read_tsv(TL / f"{b}.tsv")}
    en = {r[0]: "\t".join(r[1:]) for r in batches.read_tsv(TL / f"{b}.out.tsv")}
    return "\n".join(f">> {i} | {r[2]} | {r[3]} | {r[4]}\n   {en.get(i, '')}" for i, r in jp.items())


def review(b, rnd):
    prompt = (read("docs/reviewer-brief.md") + "\n\n# Glossary rulings\n" + rulings()
              + "\n\n# docs/style-reference.md\n" + read("docs/style-reference.md")
              + f"\n\n# Terms for this batch\n" + read(f"build/terms_{b}.txt")
              + f"\n\n# Pairs\n" + pairs(b))
    msg = codex(prompt, f"{b}.rev{rnd}")
    REV.mkdir(parents=True, exist_ok=True)
    (REV / f"{b}.r{rnd}.md").write_text(msg, encoding="utf-8")
    sect = lambda name: re.search(rf"#### {name}.*?\n(.*?)(?=\n####|\n### |\Z)", msg, re.S)  # noqa: E731
    lines = lambda m: [x.strip() for x in m.group(1).splitlines() if x.strip().startswith("-")] if m else []  # noqa
    serious = lines(sect("Critical")) + lines(sect("Important"))
    serious = [x for x in serious if re.search(ID, x)]
    minors = [x for x in lines(sect("Minor")) if re.search(ID, x)]
    return msg != "", serious, minors


def merge(b):
    with LOCK:
        entries, terms = batches.index(), batches.glossary()
        bad, rows = batches.check_batch(b, entries, terms)
        if bad:
            return False
        batches.merge(rows, overwrite=True)
        (TL / f"{b}.done").write_text(time.strftime("%Y-%m-%d %H:%M") + "\n", encoding="utf-8")
    return True


def pipeline(b):
    if (TL / f"{b}.done").exists():
        return f"{b} already merged"
    out = TL / f"{b}.out.tsv"
    if not (out.exists() and not check(b)) and not translate(b):
        return f"{b} FAILED check"
    minors = []
    for rnd in range(3):
        ok, serious, mins = review(b, rnd)
        if not ok:
            return f"{b} FAILED review (codex gave no answer)"
        minors += mins
        if not serious:
            break
        if not translate(b, "\n".join(serious)):
            return f"{b} FAILED check after review fixes"
    else:
        return f"{b} FAILED: Critical/Important left after 3 review rounds (work/tl/reviews/{b}.r2.md)"
    with LOCK:
        with open(ROOT / "docs/polish.md", "a", encoding="utf-8", newline="\n") as f:
            f.writelines(f"- [ ] {b} {m.lstrip('- ')}\n" for m in minors)
    return f"{b} merged" if merge(b) else f"{b} FAILED merge check"


def synopsis(jobs):
    """Scene groups -> summaries (work/tl/syn/gNN.md), then one draft docs/synopsis.md."""
    syn = TL / "syn"
    syn.mkdir(parents=True, exist_ok=True)
    groups, cur, size = [], [], 0
    for path in sorted((ROOT / "script/scen").glob("s*.json")):
        lines = [f"{e['id']} {e['jp']}" for e in json.loads(path.read_text(encoding="utf-8"))["entries"] if e["jp"]]
        text = "\n".join(lines)
        if cur and size + len(text) > 45000:
            groups.append(cur)
            cur, size = [], 0
        cur.append((path.stem, text))
        size += len(text)
    groups.append(cur)

    def one(i):
        p = syn / f"g{i:02d}.md"
        if p.exists() and p.stat().st_size:
            return
        g = groups[i]
        prompt = ("Below is the raw Japanese script of the PS1 RPG Growlanser (1999), scenes "
                  f"{g[0][0]}..{g[-1][0]} in file order ({{v:..}} voice, {{s:0000}} the player-named hero, {{n}}/{{p}} "
                  "breaks). For EACH scene write in English: `## sNNN - short title`, then 3-8 bullets: where it is, "
                  "who speaks (names as written, romanised), what happens, relationships and reveals, tone. Note "
                  "whether it looks like main story, side event, debug/system text, or battle text. Be factual; no "
                  "speculation beyond the text.\n\n" + "\n\n".join(f"### {n}\n{t}" for n, t in g))
        p.write_text(codex(prompt, f"syn{i:02d}"), encoding="utf-8", newline="\n")

    with ThreadPoolExecutor(jobs) as ex:
        list(ex.map(one, range(len(groups))))
    summaries = "\n\n".join((syn / f"g{i:02d}.md").read_text(encoding="utf-8") for i in range(len(groups)))
    prompt = ("From these per-scene summaries of Growlanser (PS1), write docs/synopsis.md for translators: "
              "1) Characters: who is who (romanised names as in the glossary below where present), relationships, "
              "speech style. 2) Plot by chapter in story order, with scene ids per chapter (a table: chapter | "
              "scene ids | summary). 3) Branches, endings, optional events. 4) Late reveals and twists, with the "
              "scene where each is revealed, so translators don't give them away early. 5) Non-story scenes "
              "(debug, system, battle-only). Markdown, under 12000 characters. Reply with the file content only."
              "\n\n# Glossary\n" + read("glossary.md") + "\n\n# Scene summaries\n" + summaries)
    (TL / "synopsis_draft.md").write_text(codex(prompt, "synopsis"), encoding="utf-8", newline="\n")
    print("draft:", TL / "synopsis_draft.md")


def psp_scenes(names, jobs):
    """Summaries of the PSP scenes the PS1 synopsis doesn't cover -> work/tl/syn_psp/<scene>.md, then one draft
    section for docs/synopsis.md (work/tl/synopsis_psp.md). Lines already translated show their English."""
    syn = TL / "syn_psp"
    syn.mkdir(parents=True, exist_ok=True)

    def one(name):
        p = syn / f"{name}.md"
        if p.exists() and p.stat().st_size:
            return
        es = json.loads((ROOT / f"script/scen/{name}.json").read_text(encoding="utf-8"))["entries"]
        text = "\n".join(f"{e['id']} {e['jp']}" + (f"  => {e['en']}" if e.get("en") else "") for e in es if e["jp"])
        prompt = ("Below is the Japanese script of one scene file of Growlanser (PSP remake, 2009, of the 1999 PS1 RPG). "
                  "This scene is new or reworked on PSP. Lines with `=>` carry the PS1 English translation of the same "
                  "line. ({v:..} voice, {s:0000} the player-named hero, {n}/{p} breaks.) Write in English: "
                  f"`## {name} - short title`, then 4-10 bullets: where it is, who speaks (names as in the glossary), "
                  "what happens, relationships and reveals, tone, and where it seems to fit in the PS1 story. Be "
                  "factual.\n\n# Glossary\n" + read("glossary.md") + f"\n\n# {name}\n" + text)
        p.write_text(codex(prompt, f"synpsp_{name}"), encoding="utf-8", newline="\n")

    with ThreadPoolExecutor(jobs) as ex:
        list(ex.map(one, names))
    body = "\n\n".join((syn / f"{n}.md").read_text(encoding="utf-8").strip() for n in names)
    (TL / "synopsis_psp.md").write_text("## 6. PSP-only and reworked scenes\n\n" + body + "\n", encoding="utf-8",
                                        newline="\n")
    print("draft:", TL / "synopsis_psp.md")


def terms():
    """work/tl/termscan.tsv (tools/termscan.py) -> work/tl/terms_proposed.tsv: codex picks the proper nouns and terms."""
    entries = batches.index()
    rows = [r for r in batches.read_tsv(TL / "termscan.tsv")]
    lines = "\n".join(f"{n}\t{run}\t{batches.show_jp(entries[i])}" for n, run, i in rows)
    prompt = ("Terms pass for the English fan translation of Growlanser (PS1). Below: katakana runs / quoted terms that "
              "recur in the untranslated script (count, run, one example line). Decide which are proper nouns or "
              "game terms that must be translated the same way everywhere (people, places, organisations, spells, "
              "items, monsters, titles, invented words) and which are ordinary loanwords or speech (アタシ, ホント, "
              "ゲット, パーティー). Reply with one ```tsv block: `run<TAB>English<TAB>term|word<TAB>note`, every run "
              "once. English names follow the glossary's romanisation rules.\n\n# Glossary\n" + read("glossary.md")
              + "\n\n# docs/synopsis.md\n" + read("docs/synopsis.md") + "\n\n# Runs\n" + lines)
    msg = codex(prompt, "terms")
    m = re.search(r"```(?:tsv)?\n(.*?)```", msg, re.S)
    (TL / "terms_proposed.tsv").write_text(m.group(1) if m else msg, encoding="utf-8", newline="\n")
    print(TL / "terms_proposed.tsv")


def main(argv):
    jobs = int(argv[argv.index("-j") + 1]) if "-j" in argv else 6
    if argv[:1] == ["terms"]:
        return terms()
    names = [a for a in argv[1:] if re.fullmatch(r"b\d{3}", a)]
    if "--all" in argv:
        names = [p.stem for p in batches.existing()]
    if argv[:1] == ["synopsis"]:
        return synopsis(jobs)
    if argv[:1] == ["pairs"]:  # reviewer input for subagent review (D13): work/tl/pairs/bNNN.txt
        (TL / "pairs").mkdir(exist_ok=True)
        for b in names:
            (TL / f"pairs/{b}.txt").write_text(pairs(b) + "\n", encoding="utf-8", newline="\n")
        return 0
    if argv[:1] == ["psp-scenes"]:
        return psp_scenes([a for a in argv[1:] if re.fullmatch(r"s\d{3}", a)], jobs)
    if argv[:1] == ["status"]:
        for p in batches.existing():
            b = p.stem
            st = "done" if (TL / f"{b}.done").exists() else "out" if (TL / f"{b}.out.tsv").exists() else "-"
            print(b, st)
        return 0
    if argv[:1] != ["pipeline"] or not names:
        sys.exit(__doc__)
    # one runner at a time: two would translate and merge the same batches. `--lock NAME` = a second runner, only
    # when the first can no longer write (e.g. its codex calls fail) or the batch sets are disjoint
    lock = TL / (argv[argv.index("--lock") + 1] if "--lock" in argv else "run.lock")
    if lock.exists():
        pid = lock.read_text().strip()
        alive = subprocess.run(["tasklist", "/FI", f"PID eq {pid}"], capture_output=True, text=True).stdout
        if pid in alive:
            sys.exit(f"another tl_run pipeline is running (pid {pid}, {lock})")
    lock.write_text(str(__import__("os").getpid()))
    try:
        return run(names, jobs)
    finally:
        lock.unlink(missing_ok=True)


def run(names, jobs):
    failed = 0
    with ThreadPoolExecutor(jobs) as ex:
        for res in ex.map(pipeline, names):
            print(res, flush=True)
            failed += "FAILED" in res
    print(f"{len(names) - failed}/{len(names)} batches merged or already merged")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
