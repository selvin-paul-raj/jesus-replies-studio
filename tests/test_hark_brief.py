import sys, pathlib, unittest
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "scripts"))
from content_os.hark_brief import build


class T(unittest.TestCase):
    def test_outlier_and_slot(self):
        mk = lambda e, v, age, t="08:00": {"platform": "youtube", "episode_id": e, "publication_time": t, "latest": {"views": v}, "latest_age_hours": age}
        s = build([mk("A", 100, 500), mk("B", 100, 500, "19:30"), mk("C", 500, 30)], "x")
        self.assertIn("C", s); self.assertIn("slot 19:30: median 100 n=1", s)


if __name__ == "__main__":
    unittest.main()
