"""Translation lint (tools/batches.py problems): the rules check.py runs on all shipped English."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import batches  # noqa: E402

TERMS = [(["メルフィ"], ["Melfie"], ["Melfi"])]


def problems(jp, en):
    return batches.problems({"id": "scen000.0186", "jp": jp, "term": "end"}, en, TERMS)


class Problems(unittest.TestCase):
    def test_clean(self):
        self.assertEqual(problems("メルフィさん、こんにちは。", "Hello, Melfie-san."), [])

    def test_glossary_and_avoid(self):
        self.assertIn("glossary: メルフィ -> Melfie", problems("メルフィだ。", "It's her."))
        self.assertIn("glossary Avoid: Melfi", problems("メルフィだ。", "It's Melfie. No, Melfi."))

    def test_honorific(self):
        self.assertIn("honorific さん needs -san", problems("メルフィさん。", "Melfie."))
        self.assertTrue(any("no honorific" in p for p in problems("{s:0001}さん。", "{s:0001}-san.")))

    def test_control_codes(self):
        self.assertTrue(any("control codes differ" in p for p in problems("{s:0001}だ。", "It's him.")))

    def test_choice_period(self):
        self.assertTrue(any("choice line" in p for p in problems("・はい", "・Yes.")))


if __name__ == "__main__":
    unittest.main()
