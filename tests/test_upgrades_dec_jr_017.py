"""DEC-JR-017 (2026-11-05): R11 no question hooks, R12 share line last, R13 first comment,
weekly family-pressure lane, YouTube slot unchanged pending EXP-005. Fake Buffer only; no network."""
import datetime as dt, json, pathlib, sys, tempfile, unittest
ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from daily import pipeline as pl, safety, scripture
from daily.buffer import Buffer as DailyBuffer, Outcome
from content_os import brain, timing, episodes
from content_os.client import Buffer as OSBuffer, norm_post
from content_os.distribute import Distributor

RULES = json.loads((ROOT / "config/publishing-rules.json").read_text())


def ep(eid, hook, last=("engagement", "Send this to someone who needs it today. 🙏"), topic=None):
    return {"id": eid, "title": f"T {eid}", "character": "girl", "topic": topic or f"topic {eid}", "emotion": "sad",
            "bible": {"book": "Psalms", "chapter": 27, "verse": 10, "version": "KJV", "text": "x"},
            "lines": [{"speaker": "person", "text": hook}, {"speaker": "jesus", "text": "I see it."},
                      {"speaker": "bible_verse"}, {"speaker": last[0], "text": last[1]}]}


class R11Hooks(unittest.TestCase):
    def test_hook_kinds(self):
        self.assertEqual(safety.hook_kind("Jesus... why can't I just enjoy this? 🙂"), "question")
        self.assertEqual(safety.hook_kind("Jesus... does He even hear me"), "question")
        self.assertEqual(safety.hook_kind("Jesus... I said yes again. I didn't want to. 😔"), "confession")
        self.assertEqual(safety.hook_kind("Jesus... good news came. I can't enjoy it. 🙂"), "statement")

    def test_validator_fails_question_opener_from_v3_only(self):
        with tempfile.TemporaryDirectory() as d:
            ctx = pl.Ctx(d, rules=RULES, dry_run=True)
            probs = pl.v3_script_problems(ctx, ep("JR-0100", "Jesus... why does nobody call? 😔"))
            self.assertTrue(any(p.startswith("R11") for p in probs))
            self.assertEqual(pl.v3_script_problems(ctx, ep("JR-0100", "Jesus... I called first again. 😔")), [])
        self.assertFalse(pl.rules_v3("JR-0093"))       # already in Buffer: untouched
        self.assertTrue(pl.rules_v3("JR-0094"))

    def test_planner_never_assigns_question_hooks_to_new_slots(self):
        cfg = {"timezone": "Asia/Kolkata", "videos_per_day": 2, "platforms": ["instagram", "youtube"],
               "initial_test_slots": ["08:00", "19:30"], "autonomy": {"weekly_plan_approval": False},
               "metric_priority": [["reach", ["views"]]]}
        inv = {"next_ready": [], "items": [], "counts": {}}
        plan = brain.build_plan("2026-11-16", {}, inv, timing.recommend([], cfg), {}, {"experiments": []}, {}, cfg, 200,
                                dt.datetime(2026, 11, 14, tzinfo=dt.timezone.utc))
        self.assertTrue(all(s["hook_strategy"] in ("confession", "statement") for s in plan["slots"]))


class R12ShareLine(unittest.TestCase):
    def test_share_line_rules(self):
        self.assertTrue(safety.is_share_line("Send this to someone who needs it today."))
        self.assertFalse(safety.is_share_line("Type amen and send this to a friend"))
        self.assertFalse(safety.is_share_line("Who at your office eats alone? 👇"))
        with tempfile.TemporaryDirectory() as d:
            ctx = pl.Ctx(d, rules=RULES, dry_run=True)
            probs = pl.v3_script_problems(ctx, ep("JR-0100", "Jesus... I ate alone again.", ("engagement", "Which line hit you? 👇")))
            self.assertTrue(any(p.startswith("R12 last line") for p in probs))
            (pathlib.Path(d) / "generated").mkdir()
            (pathlib.Path(d) / "generated/JR-0099.json").write_text(json.dumps(ep("JR-0099", "Jesus... I lied today.", topic="other")))
            probs = pl.v3_script_problems(ctx, ep("JR-0100", "Jesus... I ate alone again."))
            self.assertTrue(any("repeats JR-0099" in p for p in probs))


class R13FirstComment(unittest.TestCase):
    def test_first_comment_checks(self):
        self.assertEqual(safety.first_comment_problems("Has someone in your family ever said this to you?"), [])
        self.assertTrue(safety.first_comment_problems(""))
        self.assertTrue(safety.first_comment_problems("Type amen if this hit you"))
        self.assertTrue(safety.first_comment_problems("Who? Why? https://x.test"))

    def test_buffer_metadata_carries_first_comment_on_instagram_only(self):
        b = OSBuffer(None, {"buffer": {"channels": {}}})
        self.assertIn('firstComment: "Has it happened to you?"', b._meta("instagram", None, "Has it happened to you?"))
        self.assertNotIn("firstComment", b._meta("instagram", None))
        yt = {"title": "t", "privacy": "public", "made_for_kids": False, "notify_subscribers": True, "category_id": "27"}
        self.assertNotIn("firstComment", b._meta("youtube", yt, "Has it happened to you?"))
        self.assertIn("firstComment", DailyBuffer._ig_meta("Q?"))
        self.assertEqual(norm_post({"id": "1", "metadata": {"firstComment": "Q?"}})["_first_comment"], "Q?")

    def test_distributor_sends_first_comment_to_instagram_and_records_readback(self):
        calls = []

        class Fake:
            def __init__(self):
                self.posts = {}

            def list_posts(self, platform):
                return [p for p in self.posts.values() if p["_pl"] == platform], "OK"

            def read(self, pid):
                return (self.posts[pid], "OK") if pid in self.posts else (None, "NOT_FOUND")

            def create_scheduled(self, platform, text, url, due_at, yt=None, **kw):
                calls.append((platform, kw))
                pid = f"P{len(self.posts) + 1}"
                self.posts[pid] = dict(norm_post({"id": pid, "status": "scheduled", "text": text, "dueAt": due_at,
                                                  "assets": [{"source": url}],
                                                  "metadata": {"firstComment": kw.get("first_comment")}}), _pl=platform)
                return Outcome("OK", post={"id": pid})

        cfg = {"platforms": ["instagram", "youtube"], "min_lead_minutes": 45, "publish_grace_minutes": 30,
               "youtube": {"privacy": "public", "category_id": "27", "made_for_kids": False, "notify_subscribers": True}}
        ctx = {"asset_url": "https://x.test/a.mp4", "instagram_text": "cap", "youtube_text": "desc", "youtube_title": "T",
               "first_comment": "Has someone in your family ever said this to you?", "asset_check": lambda: (True, "ok")}
        now = dt.datetime(2026, 11, 5, tzinfo=dt.timezone.utc)
        with tempfile.TemporaryDirectory() as d:
            dist = Distributor(d, Fake(), cfg, lambda u: 200, "t", now, dry_run=False)
            r1, b1 = dist.schedule("JR-0096", "instagram", "2026-11-09T02:30:00.000Z", ctx)
            r2, b2 = dist.schedule("JR-0096", "youtube", "2026-11-09T02:30:00.000Z", ctx)
        self.assertEqual((r1, r2), ("SCHEDULED", "SCHEDULED"))
        self.assertEqual(calls, [("instagram", {"first_comment": ctx["first_comment"]}), ("youtube", {})])
        self.assertEqual(b1["first_comment"], "SET")


class FamilyLaneAndRepo(unittest.TestCase):
    def test_lane_reserves_monday_morning_and_keeps_its_episode_out_of_other_slots(self):
        cfg = {"timezone": "Asia/Kolkata", "videos_per_day": 2, "platforms": ["instagram", "youtube"],
               "slots": {"MORNING": "08:00", "NIGHT": "19:30"}, "initial_test_slots": ["08:00", "19:30"],
               "autonomy": {"weekly_plan_approval": False}, "metric_priority": [["reach", ["views"]]],
               "series_lanes": {"family-pressure": {"weekday": 0, "slot": "MORNING", "backlog": [
                   {"week_start": "2026-11-09", "episode_id": "JR-0096", "idea": "match refused", "verse": "Psalms 27:10"},
                   {"week_start": "2026-11-16", "episode_id": None, "idea": "aunty weight comment", "verse": "1 Samuel 16:7"}]}}}
        ready = ["JR-0096", "JR-0101", "JR-0102"]
        inv = {"next_ready": ready, "items": [{"episode_id": e, "status": "READY"} for e in ready], "counts": {}}
        now = dt.datetime(2026, 11, 7, tzinfo=dt.timezone.utc)
        plan = brain.build_plan("2026-11-09", {}, inv, timing.recommend([], cfg), {}, {"experiments": []}, {}, cfg, 103, now)
        ids = [s["episode_id"] for s in plan["slots"]]
        self.assertEqual(ids[0], "JR-0096")
        self.assertEqual(plan["slots"][0]["series"], "family-pressure")
        self.assertEqual(plan["slots"][0]["status"], "READY")
        self.assertEqual(ids.count("JR-0096"), 1)
        self.assertEqual(ids[1:3], ["JR-0101", "JR-0102"])
        nxt = brain.build_plan("2026-11-16", {}, {"next_ready": [], "items": [], "counts": {}}, timing.recommend([], cfg),
                               {}, {"experiments": []}, {}, cfg, 110, now)
        self.assertEqual((nxt["slots"][0]["episode_id"], nxt["slots"][0]["series"], nxt["slots"][0]["bible_reference"]),
                         ("JR-0110", "family-pressure", "1 Samuel 16:7"))

    def test_repo_episodes_meet_the_new_rules(self):
        ctx = pl.Ctx(ROOT, dry_run=True)
        for eid in ("JR-0094", "JR-0095", "JR-0096"):
            e = json.loads((ROOT / f"generated/{eid}.json").read_text())
            pk = json.loads((ROOT / f"generated/{eid}.package.json").read_text())
            self.assertEqual(pl.v3_script_problems(ctx, e), [], eid)
            self.assertEqual(safety.first_comment_problems(pk.get("first_comment")), [], eid)
            self.assertTrue(safety.share_line_of(pk["instagram_caption"]), eid)
            self.assertEqual(pl.norm_text(scripture.lookup(pl.ref_of(e))), pl.norm_text(e["bible"]["text"]), eid)
        fam = json.loads((ROOT / "content-os/series/family-pressure.json").read_text())
        self.assertEqual(len(fam["backlog"]), 6)
        self.assertEqual(fam["backlog"][0]["episode_id"], "JR-0096")
        b = pl.brief(ctx, "JR-0096")
        self.assertEqual(b["series"]["series"], "family-pressure")
        self.assertIn("hook_rule", b)
        self.assertIn("first_comment", b["package_fields"])

    def test_slots_unchanged_pending_exp005(self):
        self.assertEqual(RULES["slots"], {"MORNING": "08:00", "NIGHT": "19:30"})
        exp = {x["id"]: x for x in json.loads((ROOT / "content-os/experiments.json").read_text())["experiments"]}
        self.assertEqual(exp["EXP-005"]["status"], "active")
        self.assertTrue(any("05:00 IST" in n for n in exp["EXP-005"]["review_notes"]))


if __name__ == "__main__":
    unittest.main()
