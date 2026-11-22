"""show.py: print strings by id as translators see them (JP with dictionary words expanded, English unwrapped).

    python -X utf8 tools/show.py scen061.0236 scen073.0222 ... [--ctx N]   N neighbours each side (default 0)
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import batches  # noqa: E402


def unwrap(en):
    """Paragraph form, as translators write it; keeps U+3000 (layout), which str.split() would eat."""
    return re.sub(r" *\{[np]\} *", " ", en or "").strip(" ")


def main(argv):
    ctx = int(argv[argv.index("--ctx") + 1]) if "--ctx" in argv else 0
    ids = [a for a in argv if "." in a and not a.startswith("--")]
    for _, _, entries in batches.docs():
        pos = {e["id"]: i for i, e in enumerate(entries)}
        for eid in ids:
            if eid in pos:
                for e in entries[max(0, pos[eid] - ctx):pos[eid] + ctx + 1]:
                    mark = ">" if e["id"] == eid else " "
                    print(f"{mark}{e['id']}\t{batches.show_jp(e)}\n \t{unwrap(e.get('en'))}")
                print()


if __name__ == "__main__":
    main(sys.argv[1:])
