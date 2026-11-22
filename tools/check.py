"""check.py: the repo's one-command check (tests + text lint). The pre-commit hook runs it; exit != 0 blocks the commit.

    python -X utf8 tools/check.py [pytest args]
"""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    r = subprocess.run([sys.executable, "-X", "utf8", "-m", "pytest", "-q", str(ROOT / "tests"), *sys.argv[1:]], cwd=ROOT)
    if r.returncode not in (0, 5):  # 5 = no tests collected
        sys.exit(r.returncode)
    lint = subprocess.run([sys.executable, "-X", "utf8", str(ROOT / "tools/fit.py")], cwd=ROOT, capture_output=True,
                          text=True, encoding="utf-8")
    if lint.returncode:
        sys.exit("fit.py (width lint) failed:\n" + lint.stdout[-3000:])
    tl = subprocess.run([sys.executable, "-X", "utf8", str(ROOT / "tools/batches.py"), "check"], cwd=ROOT,
                        capture_output=True, text=True, encoding="utf-8")
    if tl.returncode:  # glossary/Avoid, honorifics, control codes, choice periods on all shipped English
        sys.exit("batches.py check (translation lint) failed:\n" + tl.stdout[-3000:])
    print("check ok")


if __name__ == "__main__":
    main()
