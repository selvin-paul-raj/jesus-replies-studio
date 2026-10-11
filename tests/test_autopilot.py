"""Autonomy, self-healing and feedback-loop tests (2026-10-11). No network, no real Buffer."""
import datetime as dt, json, pathlib, shutil, sys, tempfile, unittest
ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "tests"))
from daily import pipeline as pl                                # noqa: E402
from daily.store import Store                                   # noqa: E402
from content_os.autopilot import Autopilot                      # noqa: E402
from content_os.distribute import DistStore                     # noqa: E402
from content_os.brain import plan_sha                           # noqa: E402
from content_os import strategy                                 # noqa: E402
import test_daily as td                                         # noqa: E402

UTC = dt.timezone.utc
AUTH = {"given": "2026-10-11 20:48 IST, Selvin in chat", "quote": "complete automous running system"}


class AutoApprove(td.Base):
    def enable(self, require=False):
        r = json.loads((self.root / "config/publishing-rules.json").read_text())
        r["require_human_approval"] = require
        (self.root / "config/publishing-rules.json").write_text(json.dumps(r))
        (self.root / "config/content-os.json").write_text(json.dumps({"autonomy": {"full_autonomy": AUTH}}))
        self.ctx = self.make_ctx()

    def test_qa_passed_draft_is_auto_approved(self):
        self.enable(False)
        st = pl.advance(self.ctx, "JR-0002")
        self.assertEqual(st["state"], "APPROVED")
        self.assertEqual(st["approval"]["approved_by"], "standing authorization")
        self.assertEqual(self.buf.creates, 1)
        self.assertEqual(self.buf.schedules, 0)        # scheduling belongs to the distributor

    def test_human_gate_kept_when_rules_require_it(self):
        self.enable(True)
        self.assertEqual(pl.advance(self.ctx, "JR-0002")["state"], "WAITING_FOR_USER")

    def test_no_authorization_record_fails_closed(self):
        r = json.loads((self.root / "config/publishing-rules.json").read_text())
        r["require_human_approval"] = False
        (self.root / "config/publishing-rules.json").write_text(json.dumps(r))
        self.ctx = self.make_ctx()
        self.assertEqual(pl.advance(self.ctx, "JR-0002")["state"], "WAITING_FOR_USER")


class Heal(td.Base):
    def test_lord_small_caps_spacing_matches(self):
        self.assertEqual(pl.norm_text("for you alone, Lord , make me dwell"), pl.norm_text("for you alone, LORD, make me dwell").replace("LORD", "Lord"))

    def test_scripture_mismatch_is_repaired_and_revalidated(self):
        src = "The Lord is my shepherd, I lack nothing at all."
        self.ctx = self.make_ctx(fetch=lambda ref: src)
        st = pl.advance(self.ctx, "JR-0002")
        self.assertEqual(st["state"], "VALIDATION_FAILED")
        st = pl.autoadvance(self.ctx, "JR-0002")
        self.assertNotIn(st["state"], pl.states.FAILURES)
        self.assertEqual(json.loads((self.root / "generated/JR-0002.json").read_text())["bible"]["text"], src)
        self.assertEqual(st["heal"]["attempts"], 1)

    def test_originality_failure_is_not_auto_repaired(self):
        (self.root / "generated/JR-0002.json").write_text(json.dumps(
            td.ep("JR-0002", "When Fear Wins", "Jesus, I froze at school today.", ref=("John", 14, "27"))))
        st = pl.autoadvance(self.ctx, "JR-0002")
        self.assertEqual(st["state"], "VALIDATION_FAILED")
        self.assertTrue(st["heal"]["exhausted"])

    def test_package_qa_hashtags_trimmed(self):
        p = self.root / "generated/JR-0002.package.json"
        pk = json.loads(p.read_text()); pk["instagram_hashtags"] += ["#f", "#g"]; p.write_text(json.dumps(pk))
        st = pl.autoadvance(self.ctx, "JR-0002")
        self.assertNotIn(st["state"], pl.states.FAILURES, st["history"][-3:])
        self.assertEqual(len(json.loads(p.read_text())["instagram_hashtags"]), 5)

    def test_psalm_singular_accepted_for_psalms(self):
        e = json.loads((self.root / "generated/JR-0002.json").read_text())
        e["bible"]["book"] = "Psalms"
        (self.root / "generated/JR-0002.json").write_text(json.dumps(e))
        st = pl.advance(self.ctx, "JR-0002")
        self.assertNotEqual(st["state"], "PACKAGE_QA_FAILED", st["history"][-1])

    def test_heal_is_bounded(self):
        st = self.ctx.store.load("JR-0002")
        for to in ["GENERATED", "VALIDATED", "RENDER_FAILED"]:
            st = self.ctx.store.transition(st, to, "x")
        for _ in range(5):
            st, act = pl.heal(self.ctx, st, max_attempts=3)
            if act:
                st = self.ctx.store.transition(st, "RENDER_FAILED", "again")
        self.assertTrue(st["heal"]["exhausted"])
        self.assertEqual(st["heal"]["attempts"], 3)


def due(d, t):
    return dt.datetime.fromisoformat(f"{d}T{t}:00+05:30").astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%S.000Z")


class Fill(unittest.TestCase):
    def setUp(self):
        self.root = pathlib.Path(tempfile.mkdtemp())
        self.now = dt.datetime(2026, 10, 13, 0, 0, tzinfo=UTC)          # Tue 05:30 IST, both slots > 30h away
        slots = []
        for eid, d, t in [("JR-0050", "2026-10-15", "20:30"), ("JR-0051", "2026-10-16", "08:00"), ("JR-0052", "2026-10-20", "08:00")]:
            slots.append({"episode_id": eid, "date": d, "time": t, "slot": 1, "status": "NEEDS_GENERATION",
                          "platforms": ["instagram", "youtube"], "due_at": {"instagram": due(d, t), "youtube": due(d, t)}})
        self.plan = {"week_start": "2026-10-12", "slots": slots[:2]}
        self.plan["plan_sha256"] = plan_sha(self.plan["slots"])
        wd = self.root / "content-os/weeks/2026-10-12"; wd.mkdir(parents=True)
        (wd / "weekly-content-plan.json").write_text(json.dumps(self.plan))
        (wd / "authorization.json").write_text(json.dumps({"plan_sha256": self.plan["plan_sha256"]}))
        self.eps = {"JR-0040": {"id": "JR-0040"}, "JR-0051": {"id": "JR-0051"}}
        self.pkgs = {"JR-0040": {}, "JR-0051": {}}
        self.assets = {"JR-0040": {"qa_status": "PASS", "public_url": "u"}}
        self.cfg = {"platforms": ["instagram", "youtube"], "min_lead_minutes": 45, "held_episodes": {}}

    def ap(self):
        return Autopilot(self.root, self.cfg, self.eps, self.pkgs, self.assets, DistStore(self.root, ["instagram", "youtube"]),
                         Store(self.root), self.now, "t", log=lambda m: None)

    def test_unauthored_slot_gets_ready_spare_and_reauthorized(self):
        sw = self.ap().fill_slots(AUTH)
        self.assertEqual(sw, [{"slot": "2026-10-15 20:30", "from": "JR-0050", "from_status": "UNAUTHORED", "to": "JR-0040"}])
        wd = self.root / "content-os/weeks/2026-10-12"
        plan = json.loads((wd / "weekly-content-plan.json").read_text())
        auth = json.loads((wd / "authorization.json").read_text())
        self.assertEqual(plan["slots"][0]["episode_id"], "JR-0040")
        self.assertEqual(auth["plan_sha256"], plan["plan_sha256"])
        self.assertEqual(plan["plan_sha256"], plan_sha(plan["slots"]))
        self.assertTrue((wd / "authorization-history.json").exists())

    def test_in_pipeline_far_from_slot_is_not_swapped(self):
        self.eps["JR-0050"] = {"id": "JR-0050"}
        self.assertEqual(self.ap().fill_slots(AUTH), [])
        self.assertIn("JR-0050", self.ap().targets())

    def test_episode_with_buffer_object_never_swapped(self):
        ds = DistStore(self.root, ["instagram", "youtube"])
        d = ds.load("JR-0050"); d["platforms"]["youtube"]["state"] = "FAILED"; ds.save(d)
        self.assertEqual(self.ap().fill_slots(AUTH), [])

    def test_buffer_report_queues_authoring(self):
        rb = self.ap().buffer_report(53)
        self.assertIn("JR-0050", rb["authoring_needed"])
        self.assertGreaterEqual(len(rb["authoring_needed"]), 1 + 6 - 2)

    def test_sync_waiting_to_scheduled(self):
        st = Store(self.root)
        s = st.load("JR-0040")
        for to in ["GENERATED", "VALIDATED", "RENDERED", "RENDER_QA_PASSED", "PACKAGED", "PACKAGE_QA_PASSED",
                   "ASSET_HOSTED", "BUFFER_DRAFT", "WAITING_FOR_USER"]:
            s = st.transition(s, to, "x")
        ds = DistStore(self.root, ["instagram", "youtube"])
        d = ds.load("JR-0040"); d["platforms"]["instagram"].update(state="SCHEDULED", post_id="P", due_at="x"); ds.save(d)
        ch = self.ap().sync_states(AUTH)
        self.assertEqual(ch, [("JR-0040", "WAITING_FOR_USER", "SCHEDULED")])


class Learn(unittest.TestCase):
    def test_guidance_needs_n_and_feeds_brief(self):
        now = dt.datetime(2026, 10, 11, 12, 0, tzinfo=UTC)
        rows, attrs = [], {}
        for i in range(8):
            eid = f"JR-00{20 + i}"
            emo = "crying" if i < 4 else "happy"
            attrs[eid] = {"emotion": emo, "character": "girl", "hook_type": "question", "duration": 58, "hook": f"h{i}"}
            rows.append({"episode_id": eid, "platform": "instagram", "status": "sent",
                         "sent_at": (now - dt.timedelta(days=3 + i)).isoformat(),
                         "metrics": {"views": 2000 if emo == "crying" else 200, "reach": 1000, "saves": 10}})
        L = strategy.learnings(rows, attrs, now)
        g = L["authoring_guidance"]
        self.assertTrue(any("emotion=crying" in x for x in g["lean_towards"]))
        self.assertTrue(any("emotion=happy" in x for x in g["avoid"]))
        root = pathlib.Path(tempfile.mkdtemp())
        (root / "content-os").mkdir()
        strategy.write(root, L)
        self.assertIn("emotion=crying", (root / "content-os/STRATEGY.md").read_text())
        (root / "config").mkdir()
        shutil.copy(ROOT / "config/publishing-rules.json", root / "config")
        ctx = pl.Ctx(root, store=Store(root), dry_run=True, log=lambda m: None)
        self.assertIn("lean_towards", pl.brief(ctx, "JR-0099")["strategy"])


if __name__ == "__main__":
    unittest.main()
