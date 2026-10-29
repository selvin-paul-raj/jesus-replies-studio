import unittest, sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
from daily import safety

class AIDisclosure(unittest.TestCase):
    def test_new_line_mentions_ai(self):
        self.assertIn("AI-made visuals", safety.HONESTY_LINE)

    def test_legacy_line_still_passes_and_is_not_duplicated(self):
        old = safety.LEGACY_HONESTY_LINES[0]
        pk = {"instagram_caption": "x\n\n" + old, "youtube_description": "y\n\n" + old, "youtube_title": "t"}
        self.assertEqual(safety.package_problems(pk), [])
        safety.fix_package(pk)
        self.assertNotIn(safety.HONESTY_LINE, pk["instagram_caption"])

    def test_missing_line_gets_new_ai_line(self):
        pk = {"instagram_caption": "x", "youtube_description": "y", "youtube_title": "t"}
        safety.fix_package(pk)
        self.assertIn(safety.HONESTY_LINE, pk["instagram_caption"])
        self.assertIn(safety.HONESTY_LINE, pk["youtube_description"])

if __name__ == "__main__":
    unittest.main()
