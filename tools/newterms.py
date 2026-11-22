"""NEW TERM lines from translator reports (work/tl/bNNN.report.txt), grouped by JP, minus terms already in glossary.md.

    python -X utf8 tools/newterms.py            conflicts first (one JP, several EN), then the rest
    python -X utf8 tools/newterms.py --table    the agreed ones as glossary rows: | JP | EN | | first batch | |

Read-only: add the rows to glossary.md with the file-edit tool, and fix the losing spellings in script/ by hand.
"""
import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def known():
    """JP cells of every glossary table row."""
    jp = set()
    for line in (ROOT / "glossary.md").read_text(encoding="utf-8").splitlines():
        if line.startswith("| ") and not line.startswith("| JP"):
            jp.update(x.strip() for x in line.split("|")[1].split("/"))
    return jp


def collect():
    terms = defaultdict(lambda: defaultdict(list))  # jp -> en -> [batch]
    for rep in sorted((ROOT / "work/tl").glob("b*.report.txt")):
        for line in rep.read_text(encoding="utf-8").splitlines():
            m = re.match(r"NEW TERM:\s*(.+?)\s*->\s*(.+?)\s*$", line)
            if m:
                for jp in m.group(1).split(" / "):
                    terms[jp.strip()][m.group(2)].append(rep.name[:4])
    return terms


def main():
    have, terms = known(), collect()
    new = {jp: ens for jp, ens in terms.items() if jp not in have}
    conflicts = {jp: ens for jp, ens in new.items() if len(ens) > 1}
    if "--table" in sys.argv:
        for jp, ens in sorted(new.items()):
            if jp not in conflicts:
                en, bs = next(iter(ens.items()))
                print(f"| {jp} | {en} | | {bs[0]} | |")
        return
    print(f"{len(new)} new JP terms, {len(conflicts)} with conflicting English")
    for jp, ens in sorted(conflicts.items()):
        print(jp, " | ".join(f"{en} ({','.join(bs)})" for en, bs in ens.items()))
    print("--- agreed")
    for jp, ens in sorted(new.items()):
        if jp not in conflicts:
            en, bs = next(iter(ens.items()))
            print(jp, "->", en, f"({','.join(bs)})")


if __name__ == "__main__":
    main()
