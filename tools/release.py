"""release.py: build, gate and package the English patch (skill pipeline.md §Release). Stops at the first failure.
    python -X utf8 tools/release.py [--version 1.0] [--force] [--skip-build] [--skip-tests]
Steps: build.py -> tools/check.py -> smoke boot (tools/routes/boot.txt) -> no Japanese left in the script (see
leftover_jp) -> qa_gate.py check on every work/qa/**/manifest.tsv (verdicts in its folder's verdicts/) ->
textcover.py -> no unticked line in docs/polish.md -> no template placeholder in README.md -> debug tool off ->
xdelta3 patch (-B image size) -> re-apply to the clean original and compare sha1 -> zip
release/Growlanser_PSP_EN_v<version>.zip (patch + README.txt, ZIP_STORED). The playable ISO stays in build/.
--skip-build / --skip-tests reuse the current build/ or skip check.py (gates only: a real release runs everything).
Refuses to overwrite an existing version's files without --force. Adapted from the PS1 repo's tools/release.py.
"""
import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
import zipfile
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from skill import SKILL  # noqa: E402

SKILL = Path(SKILL)
PY = [sys.executable, "-X", "utf8"]
ORIG = ROOT / "rom/Growlanser (Japan).iso"
BUILT = ROOT / "build/growlanser_en.iso"
JP = re.compile(r"[぀-ヺー-ヿ一-鿿ｦ-ﾟ]")  # not ・ (U+30FB): the choice bullet
CODE = re.compile(r"\{[^}\n]*\}|\[[0-9A-F]{4}\]")
PLACEHOLDER = re.compile(r"<(?:Game title|platform|publisher|year|repo|file|size|sha1|game|ext)[^>]*>|<[A-Z][a-z]+ /")


def step(name, ok, detail=""):
    print(f"[{'ok' if ok else 'FAIL'}] {name}" + (f": {detail}" if detail else ""), flush=True)
    if not ok:
        sys.exit(1)


def run(cmd, **kw):
    return subprocess.run([str(c) for c in cmd], cwd=ROOT, **kw).returncode


def digest(path):
    h, c = hashlib.sha1(), 0
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
            c = zlib.crc32(chunk, c)
    return h.hexdigest(), "%08X" % c


def leftover_jp():
    """Japanese the release would still show. The build encodes exactly script/*.json, so check that: every string
    with Japanese has English with none (insert.KEEP_JP / KEEP_POOLS excepted). Runtime proof: textcover.py."""
    from insert import KEEP_JP, KEEP_POOLS
    bad = []
    for p in sorted((ROOT / "script").rglob("*.json")):
        for e in json.loads(p.read_text(encoding="utf-8"))["entries"]:
            if e["id"] in KEEP_JP or e["id"].startswith(KEEP_POOLS) or not JP.search(CODE.sub("", e["jp"])):
                continue
            if not e.get("en") or JP.search(CODE.sub("", e["en"])):
                bad.append(e["id"])
    return bad


def debug_in_build():
    """The debug tool pokes RAM over PPSSPP's WebSocket (tools/debug/); nothing of it may be assembled into the build."""
    return [p.name for p in (ROOT / "asm").glob("*.asm")
            if re.search(r"tools/debug|\bwarp|cheat", re.sub(r"(;|//|#).*", "", p.read_text(encoding="utf-8")), re.I)]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--version", default="1.0")
    ap.add_argument("--force", action="store_true", help="overwrite this version's existing release files")
    ap.add_argument("--skip-build", action="store_true", help="use the current build/ (not for a real release)")
    ap.add_argument("--skip-tests", action="store_true", help="skip tools/check.py (not for a real release)")
    a = ap.parse_args()
    out = ROOT / "release" / f"v{a.version}"
    zpath = ROOT / "release" / f"Growlanser_PSP_EN_v{a.version}.zip"
    if (out.exists() or zpath.exists()) and not a.force:
        step("release files", False, f"{out.name} exists; pass --force to overwrite")
    xdelta = shutil.which("xdelta3")
    step("xdelta3 on PATH", bool(xdelta))
    if not a.skip_build:
        step("build", run(PY + ["build.py"]) == 0)
    if not a.skip_tests:
        step("tools/check.py", run(PY + ["tools/check.py"]) == 0)
    rc = run(PY + [SKILL / "scripts/emu.py", BUILT, "--out", ROOT / "work/qa/release_smoke",
                   "--route", ROOT / "tools/routes/boot.txt", "--smoke"], stdout=subprocess.DEVNULL)
    step("smoke boot", rc == 0, f"exit {rc}")
    bad = leftover_jp()
    step("no Japanese left in the script", not bad, " ".join(bad[:20]))
    for m in sorted((ROOT / "work/qa").rglob("manifest.tsv")):
        rc = run(PY + [SKILL / "scripts/qa_gate.py", "check", m, m.parent / "verdicts"], stdout=subprocess.DEVNULL)
        step(f"qa_gate {m.relative_to(ROOT).as_posix()}", rc == 0, f"exit {rc}")
    rc = run(PY + [SKILL / "scripts/textcover.py", "work/qa/cov", "build/strings.tsv"], stdout=subprocess.DEVNULL)
    step("textcover", rc == 0, f"exit {rc}")
    open_polish = [ln for ln in (ROOT / "docs/polish.md").read_text(encoding="utf-8").splitlines()
                   if ln.startswith("- [ ]")]
    step("docs/polish.md all ticked", not open_polish, f"{len(open_polish)} open")
    ph = PLACEHOLDER.findall((ROOT / "README.md").read_text(encoding="utf-8"))
    step("README.md has no template placeholder", not ph, " ".join(ph[:5]))
    dbg = debug_in_build()
    step("debug tool off (none assembled)", not dbg, " ".join(dbg))
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    (o_sha, o_crc), (b_sha, b_crc) = digest(ORIG), digest(BUILT)
    patch = out / "Growlanser (Japan).xdelta"
    size = max(ORIG.stat().st_size, BUILT.stat().st_size)
    step("xdelta", run([xdelta, "-e", "-9", "-f", "-B", size, "-s", ORIG, BUILT, patch]) == 0)
    check = out / "reapply.tmp"
    rc = run([xdelta, "-d", "-f", "-s", ORIG, patch, check])
    same = rc == 0 and digest(check)[0] == b_sha
    check.unlink(missing_ok=True)
    step(f"re-apply {patch.name}", same, f"{patch.stat().st_size} bytes")
    files = (f"  Growlanser (Japan).iso (Redump, ULJM-05423)\n    {ORIG.stat().st_size} bytes, CRC32 {o_crc}, "
             f"SHA-1 {o_sha}\n    patch: {patch.name} -> patched CRC32 {b_crc}, SHA-1 {b_sha}\n")
    readme = (ROOT / "docs/release-readme.txt").read_text(encoding="utf-8")
    readme = readme.replace("{VERSION}", a.version).replace("{FILES}", files)
    (out / "README.txt").write_text(readme, encoding="utf-8", newline="\r\n")
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_STORED) as z:
        for f in sorted(out.iterdir()):
            z.write(f, f.name)
    step("zip", True, f"{zpath.relative_to(ROOT).as_posix()} ({zpath.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
