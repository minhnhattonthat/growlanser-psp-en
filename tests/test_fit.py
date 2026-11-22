"""Fit lint (tools/fit.py) against the widths measured in-game on PSP (docs/windows.md), and the script passes it."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import fit  # noqa: E402

RULER = "".join(c + "234567890" for c in "ABCDEFGH")  # 6 px per character


def errors(eid, text, term="end"):
    return [m for err, m in fit.lint(text, fit.budget(eid, {"en": text, "term": term})) if err]


class Fit(unittest.TestCase):
    def test_measured_rulers(self):
        # work/qa/s2r: dialogue wrapped after 48 ruler chars, name tag showed 24; work/qa/s3: items, config 16
        self.assertEqual(errors("scen000.0186", RULER[:48]), [])
        self.assertTrue(errors("scen000.0186", RULER[:49]))
        self.assertEqual(errors("boot.items.0001", RULER[:16]), [])
        self.assertTrue(errors("boot.items.0001", RULER[:17]))
        self.assertEqual(errors("boot.sys.0122", RULER[:16]), [])
        self.assertTrue(errors("boot.sys.0122", RULER[:17]))
        self.assertEqual(errors("boot.sys.0062", RULER[:24]), [])
        self.assertTrue(errors("boot.sys.0062", RULER[:25]))
        self.assertEqual(errors("scen000.0003", RULER[:24], "null"), [])
        self.assertTrue(errors("scen000.0003", RULER[:25], "null"))

    def test_lines_per_page(self):
        self.assertEqual(errors("scen000.0186", "a{n}b{n}c{p}d{n}e{n}f"), [])
        self.assertTrue(errors("scen000.0186", "a{n}b{n}c{n}d"))
        self.assertTrue(errors("boot.items.0001", "{F401}"))  # dictionary codes write Japanese

    def test_wait_codes(self):
        # work/qa/s3c/wait: 25 chars, wait, then the pen continued and wrapped after 47 (pairs re-align after a wait)
        line = RULER[:25] + "{FFF9}{FFFB}" + RULER[25:47]
        self.assertEqual(errors("scen000.0186", line), [])
        self.assertTrue(errors("scen000.0186", line + RULER[47]))

    def test_script(self):
        font, codec = fit.enfont.load(), fit.enfont.EnCodec()
        bad = [(e["id"], m) for e in fit.entries([])
               for err, m in fit.lint(e["en"], fit.budget(e["id"], e), font, codec)]
        self.assertEqual(bad, [])  # warnings too: an unmeasured guess must still hold


if __name__ == "__main__":
    unittest.main()
