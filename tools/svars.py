"""svars.py: what each {s:XXXX} draws (boot.names table by ref index): `{s:XXXX}<TAB>JP<TAB>English`.

    python -X utf8 tools/svars.py > build/svars.txt
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

doc = json.loads((ROOT / "script/boot/names.json").read_text(encoding="utf-8"))
for i, r in enumerate(doc["refs"].split()):
    e = doc["entries"][int(r)]
    print("{s:%04X}\t%s\t%s" % (i, e["jp"], e.get("en", "")))
