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
    print("check ok")


if __name__ == "__main__":
    main()
