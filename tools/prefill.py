"""prefill.py: copy the PS1 translation (../growlanser-en) into script/ for every PSP string whose jp equals a translated
PS1 jp exactly (status.md phase 6 step 1). Marks those entries "src": "ps1".

    python -X utf8 tools/prefill.py [--write] [--ps1 ../growlanser-en]

Pick order for a jp with several PS1 English forms: the same id (when the scene isn't shifted), then the matching PS1
pool (scene_map; PS1 exe.X = PSP boot.X), then the most common form. Entries already holding English, keep-JP entries and empty jp are left alone.
"""
import difflib
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from extract import dump  # noqa: E402
from insert import keep_jp  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]


def pool(eid):
    p = eid.rpartition(".")[0]
    return "boot" + p[3:] if p.startswith("exe.") else p


def ps1_index(ps1):
    by_jp = defaultdict(list)  # jp -> [(id, pool, en)]
    for path in sorted((ps1 / "script").glob("*/*.json")):
        for e in json.loads(path.read_text(encoding="utf-8"))["entries"]:
            if e["jp"] and e.get("en"):
                by_jp[e["jp"]].append((e["id"], pool(e["id"]), e["en"]))
    return by_jp


def scene_map(by_jp):
    """PSP pool -> the PS1 pool sharing most of its long lines (scenes shift: PSP scen200 = PS1 scen159)."""
    votes = defaultdict(Counter)
    for path in sorted((ROOT / "script").glob("*/*.json")):
        for e in json.loads(path.read_text(encoding="utf-8"))["entries"]:
            if len(e["jp"]) > 12 and len({c[1] for c in by_jp.get(e["jp"], ())}) == 1:
                votes[pool(e["id"])][by_jp[e["jp"]][0][1]] += 1
    return {p: v.most_common(1)[0][0] for p, v in votes.items()}


def pick(e, cands, smap):
    p = smap.get(pool(e["id"]), pool(e["id"]))
    if p == pool(e["id"]):
        for c in cands:
            if c[0] == e["id"]:
                return c[2]
    same = [c[2] for c in cands if c[1] == p]
    return Counter(same or [c[2] for c in cands]).most_common(1)[0][0]


class Near:
    """The most similar translated PS1 line in the matching PS1 scene (reworded PSP lines), for translator batches."""

    def __init__(self, ps1=None):
        ps1 = ps1 or ROOT.parent / "growlanser-en"
        by_jp = ps1_index(ps1)
        self.smap = scene_map(by_jp)
        self.pools = defaultdict(list)
        for path in sorted((ps1 / "script").glob("*/*.json")):
            for e in json.loads(path.read_text(encoding="utf-8"))["entries"]:
                if e["jp"] and e.get("en"):
                    self.pools[pool(e["id"])].append(e)

    def __call__(self, e, floor=0.55):
        p = pool(e["id"])
        best, hit = floor, None
        for c in self.pools.get(self.smap.get(p, p), ()):
            sm = difflib.SequenceMatcher(None, e["jp"], c["jp"], autojunk=False)
            if sm.real_quick_ratio() > best and sm.quick_ratio() > best and sm.ratio() > best:
                best, hit = sm.ratio(), c
        return hit


def main(argv):
    ps1 = Path(argv[argv.index("--ps1") + 1]) if "--ps1" in argv else ROOT.parent / "growlanser-en"
    by_jp = ps1_index(ps1)
    smap = scene_map(by_jp)
    stats = Counter()
    for path in sorted((ROOT / "script").glob("*/*.json")):
        doc = json.loads(path.read_text(encoding="utf-8"))
        changed = False
        for e in doc["entries"]:
            if not e["jp"] or keep_jp(e) or e.get("en"):
                continue
            cands = by_jp.get(e["jp"])
            stats[(path.parent.name, "reused" if cands else "new")] += 1
            if cands:
                e["en"], e["src"], changed = pick(e, cands, smap), "ps1", True
        if changed and "--write" in argv:
            path.write_text(dump(doc), encoding="utf-8", newline="\n")
    for k, v in sorted(stats.items()):
        print(*k, v)
    print("reused", sum(v for k, v in stats.items() if k[1] == "reused"),
          "new", sum(v for k, v in stats.items() if k[1] == "new"))


if __name__ == "__main__":
    main(sys.argv[1:])
