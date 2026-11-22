"""termscan.py: recurring katakana runs / 『』 terms in untranslated dialogue that neither glossary.md nor the game tables
cover (translation.md: terms pass before wave 1). Prints `count<TAB>run<TAB>example id`.

    python -X utf8 tools/termscan.py [--min 3]
"""
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import batches  # noqa: E402

RUN = re.compile(r"[ァ-ヺー・]{3,}|『[^』]{2,12}』")


def main(argv):
    least = int(argv[argv.index("--min") + 1]) if "--min" in argv else 3
    known = {j for jps, _, _ in batches.glossary() for j in jps} | set(batches.table_terms())
    count, first = Counter(), {}
    for _, _, entries in batches.docs():
        for e in entries:
            if not batches.needs_english(e) or not e["id"].startswith("scen"):
                continue
            for run in set(RUN.findall(batches.TOKEN.sub("", batches.show_jp(e)))):
                run = run.strip("・")
                if run and not any(k in run for k in known):
                    count[run] += 1
                    first.setdefault(run, e["id"])
    for run, n in count.most_common():
        if n >= least:
            print(f"{n}\t{run}\t{first[run]}")


if __name__ == "__main__":
    main(sys.argv[1:])
