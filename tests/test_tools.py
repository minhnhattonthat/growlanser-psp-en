"""Fast tests for the repo's own tools (no ROM needed)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))


def test_skill_path_resolves():
    from skill import SKILL
    assert (Path(SKILL) / "SKILL.md").is_file()
