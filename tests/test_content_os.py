"""Content OS safety tests. Fake Buffer only; no network."""
import datetime as dt, json, pathlib, sys, tempfile, unittest
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "scripts"))
from content_os import analytics, timing, brain, inventory, learn, episodes
from content_os.distribute import Distributor, DistStore, move, IllegalTransition
from content_os.client import norm_post
from daily.buffer import Outcome
from daily.redact import redact

NOW = dt.datetime(2026, 10, 4, 6, 0, tzinfo=dt.timezone.utc)
CFG = {"timezone": "Asia/Kolkata", "videos_per_day": 2, "platforms": ["instagram", "youtube"],
       "autonomy": {"weekly_plan_approval": True, "scheduler_enabled": False}, "coordination": "same_slot",
       "initial_test_slots": ["08:00", "21:00"], "min_lead_minutes": 45, "publish_grace_minutes": 30,
       "held_episodes": {"JR-0036": "held"}, "pinned_first": ["JR-0037"],
       "youtube": {"privacy": "public", "category_id": "22", "made_for_kids": False, "notify_subscribers": True},
       "metric_priority": [["reach", ["reach", "views"]], ["shares", ["shares"]], ["likes", ["reactions"]]],
       "checkpoints_hours": [24, 72, 168], "buffer": {"channels": {"instagram": "IG", "youtube": "YT"}}}
URL = "https://example.test/JR-0040.mp4"


class FakeBuffer:
    def __init__(self, mode="ok"):
        self.posts, self.mode, self.creates, self.edits, self.n = {}, mode, 0, 0, 0

    def add(self, platform, status="draft", text="cap", asset=URL, due="2026-12-31T00:00:00.000Z", **kw):
        self.n += 1
        pid = f"P{self.n}"
        self.posts[pid] = norm_post(dict(id=pid, status=status, text=text, dueAt=due, channelService=platform,
                                         assets=[{"source": asset}], **kw))
        self.posts[pid]["_platform"] = platform
        return pid

    def list_posts(self, platform):
        return [p for p in self.posts.values() if p["_platform"] == platform], "OK"

    def read(self, pid):
        return (self.posts[pid], "OK") if pid in self.posts else (None, "NOT_FOUND")

    def create_scheduled(self, platform, text, url, due_at, yt=None):
        self.creates += 1
        if self.mode == "reject":
            return Outcome("REJECTED", detail="bad")
        pid = self.add(platform, "scheduled", text, url, due_at)
        if self.mode == "unknown":
            return Outcome("UNKNOWN", detail="timeout")
        if self.mode == "unknown_lost":
            del self.posts[pid]
            return Outcome("UNKNOWN", detail="timeout")
        return Outcome("OK", post={"id": pid})

    def schedule_draft(self, pid, platform, text, url, due_at, yt=None):
        self.edits += 1
        self.posts[pid].update(status="scheduled", dueAt=due_at)
        return Outcome("OK", post={"id": pid})


def ctx(text="cap"):
    return {"asset_url": URL, "instagram_text": text, "youtube_text": text, "youtube_title": "T",
            "asset_check": lambda: (True, "ok")}


DUE = "2026-10-05T02:30:00.000Z"


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = pathlib.Path(self.tmp.name)
        self.buf = FakeBuffer()

    def tearDown(self):
        self.tmp.cleanup()

    def dist(self, dry=False, buf=None, now=NOW):
        return Distributor(self.root, buf or self.buf, CFG, lambda u: 200, "t", now, dry_run=dry)


class T01StateTransitions(Base):
    def test_draft_is_not_scheduled_and_published_not_verified(self):
        blk = DistStore(self.root, CFG["platforms"]).load("JR-0040")["platforms"]["instagram"]
        move(blk, "DRAFT", "x", "t", NOW)
        with self.assertRaises(IllegalTransition):
            move(blk, "NONE", "x", "t", NOW)
        move(blk, "SCHEDULED", "x", "t", NOW); move(blk, "PUBLISHED", "x", "t", NOW)
        with self.assertRaises(IllegalTransition):
            move(blk, "SCHEDULED", "x", "t", NOW)


class T02PlatformScheduling(Base):
    def test_instagram_and_youtube_created_and_read_back(self):
        d = self.dist()
        for p in ("instagram", "youtube"):
            r, blk = d.schedule("JR-0040", p, DUE, ctx())
            self.assertEqual((r, blk["state"]), ("SCHEDULED", "SCHEDULED"))
        self.assertEqual(self.buf.creates, 2)

    def test_existing_draft_is_edited_not_recreated(self):
        pid = self.buf.add("instagram")
        st = DistStore(self.root, CFG["platforms"]); d0 = st.load("JR-0040")
        d0["platforms"]["instagram"].update(state="DRAFT", post_id=pid); st.save(d0)
        r, blk = self.dist().schedule("JR-0040", "instagram", DUE, ctx())
        self.assertEqual((r, self.buf.creates, self.buf.edits), ("SCHEDULED", 0, 1))

    def test_draft_with_different_content_is_not_touched(self):
        pid = self.buf.add("instagram", text="other words")
        st = DistStore(self.root, CFG["platforms"]); d0 = st.load("JR-0040")
        d0["platforms"]["instagram"].update(state="DRAFT", post_id=pid); st.save(d0)
        r, _ = self.dist().schedule("JR-0040", "instagram", DUE, ctx())
        self.assertEqual((r, self.buf.edits), ("DRAFT_CONTENT_MISMATCH", 0))


class T03Idempotency(Base):
    def test_rerun_does_not_duplicate(self):
        d = self.dist()
        d.schedule("JR-0040", "instagram", DUE, ctx())
        r, _ = self.dist().schedule("JR-0040", "instagram", DUE, ctx())
        self.assertEqual((r, self.buf.creates), ("ALREADY_SCHEDULED", 1))

    def test_untracked_existing_post_is_adopted(self):
        self.buf.add("youtube", "scheduled", due=DUE)
        r, _ = self.dist().schedule("JR-0040", "youtube", DUE, ctx())
        self.assertEqual((r, self.buf.creates), ("ALREADY_SCHEDULED", 0))

    def test_duplicate_posts_block(self):
        self.buf.add("instagram"); self.buf.add("instagram")
        r, blk = self.dist().schedule("JR-0040", "instagram", DUE, ctx())
        self.assertEqual((r, blk["state"], self.buf.creates), ("STOP", "BLOCKED", 0))


class T04UnknownOutcome(Base):
    def test_unknown_reconciled_by_listing(self):
        b = FakeBuffer("unknown")
        r, blk = self.dist(buf=b).schedule("JR-0040", "instagram", DUE, ctx())
        self.assertTrue(r.startswith("RECONCILED"))
        self.assertEqual(b.creates, 1)

    def test_unknown_unresolved_stops_and_never_retries(self):
        b = FakeBuffer("unknown_lost")
        r, blk = self.dist(buf=b).schedule("JR-0040", "instagram", DUE, ctx())
        self.assertEqual((r, blk["state"]), ("STOP", "UNKNOWN"))
        r2, _ = self.dist(buf=b).schedule("JR-0040", "instagram", DUE, ctx())
        self.assertEqual((r2, b.creates), ("STOP", 1))


class T05Recovery(Base):
    def test_pending_mutation_with_post_is_adopted(self):
        st = DistStore(self.root, CFG["platforms"]); d0 = st.load("JR-0040")
        d0["platforms"]["instagram"]["pending_mutation"] = {"kind": "create_scheduled"}; st.save(d0)
        self.buf.add("instagram", "scheduled", due=DUE)
        r, _ = self.dist().schedule("JR-0040", "instagram", DUE, ctx())
        self.assertEqual((r, self.buf.creates), ("ALREADY_SCHEDULED", 0))

    def test_youtube_retry_only_when_instagram_published(self):
        self.buf.add("instagram", "sent", sentAt="2026-10-03T02:31:00Z", externalLink="https://ig/p/1", metricsUpdatedAt="x")
        d = self.dist()
        r_ig, b_ig = d.schedule("JR-0040", "instagram", DUE, ctx())
        r_yt, _ = d.schedule("JR-0040", "youtube", DUE, ctx())
        self.assertEqual((r_ig, b_ig["state"], r_yt, self.buf.creates), ("ALREADY_PUBLISHED", "PUBLISHED_VERIFIED", "SCHEDULED", 1))


class T06Safety(Base):
    def test_dry_run_never_mutates(self):
        r, _ = self.dist(dry=True).schedule("JR-0040", "instagram", DUE, ctx())
        self.assertEqual((r, self.buf.creates), ("WOULD_CREATE", 0))

    def test_held_episode_untouched(self):
        r, _ = self.dist().schedule("JR-0036", "instagram", DUE, ctx())
        self.assertEqual((r, self.buf.creates), ("HELD", 0))

    def test_unauthorized_week_waits(self):
        plan = {"plan_sha256": "abc", "slots": []}
        self.assertEqual(self.dist().schedule_week(plan, lambda e: ctx(), {"plan_sha256": "other"})["status"], "WAITING_FOR_USER")

    def test_past_slot_is_missed_not_published_now(self):
        r, _ = self.dist().schedule("JR-0040", "instagram", "2026-10-04T05:30:00.000Z", ctx())
        self.assertEqual((r, self.buf.creates), ("MISSED_SLOT", 0))

    def test_youtube_without_category_blocks(self):
        c = json.loads(json.dumps(CFG)); c["youtube"]["category_id"] = None
        d = Distributor(self.root, self.buf, c, lambda u: 200, "t", NOW, dry_run=False)
        r, _ = d.schedule("JR-0040", "youtube", DUE, ctx())
        self.assertEqual((r, self.buf.creates), ("BLOCKED_YOUTUBE_CATEGORY", 0))

    def test_secret_redaction(self):
        self.assertNotIn("pHwOlu-lAVSsvzSau8ambcgt1tFjisg8JK0C-mK80QI", redact("Bearer pHwOlu-lAVSsvzSau8ambcgt1tFjisg8JK0C-mK80QI"))


class T07Verification(Base):
    def test_overdue_scheduled_becomes_unknown(self):
        self.buf.add("instagram", "scheduled", due="2026-10-04T04:00:00.000Z")
        d = self.dist()
        _, blk = d.reconcile("JR-0040", "instagram", ctx())
        self.assertEqual(blk["state"], "UNKNOWN")

    def test_sent_without_permalink_is_published_not_verified(self):
        self.buf.add("youtube", "sent", sentAt="2026-10-04T02:31:00Z")
        _, blk = self.dist().reconcile("JR-0040", "youtube", ctx())
        self.assertEqual(blk["state"], "PUBLISHED")


def ep(eid, emotion, character, hook):
    return {"id": eid, "title": hook, "topic": f"t{eid}", "emotion": emotion, "character": character,
            "bible": {"book": "John", "chapter": 1, "verse": "1"},
            "lines": [{"speaker": "person", "text": hook}, {"speaker": "jesus", "text": "x"},
                      {"speaker": "person", "text": "but"}, {"speaker": "jesus", "text": "y"},
                      {"speaker": "engagement", "text": "What about you?"}]}


class T08PlanAndInventory(unittest.TestCase):
    def setUp(self):
        self.eps = {f"JR-00{n}": ep(f"JR-00{n}", ["sad", "worried"][n % 2], ["boy", "girl"][n % 2], f"Jesus, question {n}?")
                    for n in range(21, 38)}
        self.assets = {e: {"public_url": f"u/{e}", "qa_status": "PASS", "duration_seconds": 60} for e in self.eps}
        self.attrs = {e: episodes.derive_attributes(v, None, self.assets[e]) for e, v in self.eps.items()}

    def test_inventory_and_14_slot_plan(self):
        inv = inventory.build(self.eps, self.assets, {}, [], CFG)
        self.assertNotIn("JR-0036", inv["next_ready"])
        tm = timing.recommend([], CFG)
        plan = brain.build_plan("2026-10-05", self.attrs, inv, tm, {}, {"experiments": []}, {}, CFG, 38, NOW)
        self.assertEqual(len(plan["slots"]), 14)
        self.assertEqual(plan["slots"][0]["episode_id"], "JR-0037")
        ids = [s["episode_id"] for s in plan["slots"]]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(plan["slots"][0]["due_at"]["youtube"], "2026-10-05T02:30:00.000Z")
        self.assertTrue(all(s["platforms"] == ["instagram", "youtube"] for s in plan["slots"]))

    def test_published_episode_not_ready(self):
        rows = [{"episode_id": "JR-0021", "status": "sent", "platform": "instagram"}]
        inv = inventory.build(self.eps, self.assets, {}, rows, CFG)
        self.assertNotIn("JR-0021", inv["next_ready"])

    def test_timing_insufficient_data_is_experimental(self):
        tm = timing.recommend([], CFG)
        self.assertTrue(all(s["status"] == "experimental" for s in tm["slots"]))


class T09Analytics(unittest.TestCase):
    def test_ingestion_matching_availability_and_checkpoints(self):
        eps = {"JR-0040": ep("JR-0040", "sad", "boy", "Jesus... why does it still hurt so much?")}
        p = norm_post({"id": "A", "status": "sent", "text": "Jesus... why does it still hurt so much? more", "sentAt": "2026-09-30T02:30:00Z",
                       "metrics": [{"type": "reactions", "value": 5}, {"type": "views", "value": 100}]})
        d = norm_post({"id": "B", "status": "sent", "text": "\u2728 Today's blessing: x", "sentAt": "2026-09-30T02:30:00Z", "metrics": []})
        rows = analytics.snapshot({"instagram": [p, d]}, eps, {}, NOW)
        self.assertEqual(rows[0]["episode_id"], "JR-0040"); self.assertIsNone(rows[1]["episode_id"])
        av = analytics.availability(rows)["instagram"]
        self.assertIn("views", av["AVAILABLE"]); self.assertIn("saves", av["UNAVAILABLE_VIA_BUFFER"])
        h = {}
        analytics.update_history(h, rows)
        self.assertEqual(sorted(h["instagram:A"]["checkpoints"]), ["24h", "72h"])

    def test_experiment_tags_and_learning_needs_n3(self):
        attrs = {f"E{i}": {"hook_type": "question" if i % 2 else "statement", "emotion": "sad"} for i in range(4)}
        rows = [{"episode_id": f"E{i}", "status": "sent", "platform": "instagram", "sent_at": "2026-09-29T02:30:00Z",
                 "age_hours": 100, "metrics": {"views": 10 * i}} for i in range(4)]
        rep = learn.weekly_report("2026-09-28", rows, attrs, None, CFG, NOW)
        hk = [p for p in rep["patterns"] if p["dimension"] == "hook_type"][0]
        self.assertEqual(hk["finding"], "insufficient data")



class T10Quota(Base):
    def test_quota_precheck_defers_without_mutation(self):
        c = json.loads(json.dumps(CFG)); c["scheduled_limit"] = {"instagram": 1}
        self.buf.add("instagram", "scheduled", text="other", asset="x")
        d = Distributor(self.root, self.buf, c, lambda u: 200, "t", NOW, dry_run=False)
        r, blk = d.schedule("JR-0040", "instagram", DUE, ctx())
        self.assertEqual((r, blk["state"], self.buf.creates), ("QUOTA_DEFERRED", "NONE", 0))

    def test_quota_failure_resets_for_topup(self):
        st = DistStore(self.root, CFG["platforms"]); d0 = st.load("JR-0040")
        d0["platforms"]["youtube"].update(state="FAILED", attempts=1, error='{"message": "Scheduled posts limit reached. You have 10"}'); st.save(d0)
        r, blk = self.dist().schedule("JR-0040", "youtube", DUE, ctx())
        self.assertEqual((r, self.buf.creates), ("SCHEDULED", 1))


    def test_draft_to_scheduled_counts_toward_quota(self):
        # Regression 2026-10-05: schedule_draft was not counted, so a second post
        # was scheduled past the limit and the Bible post hit Buffer 10/10.
        c = json.loads(json.dumps(CFG)); c["scheduled_limit"] = {"instagram": 2}

        class SnapshotBuffer(FakeBuffer):  # real Buffer listings are snapshots, not live objects
            def list_posts(self, platform):
                posts, d = FakeBuffer.list_posts(self, platform)
                return json.loads(json.dumps(posts)), d
        self.buf = SnapshotBuffer()
        self.buf.add("instagram", "scheduled", text="other", asset="x")
        pid = self.buf.add("instagram", "draft", text="cap", asset=URL)
        st = DistStore(self.root, CFG["platforms"]); d0 = st.load("JR-0040")
        d0["platforms"]["instagram"].update(state="DRAFT", post_id=pid); st.save(d0)
        d = Distributor(self.root, self.buf, c, lambda u: 200, "t", NOW, dry_run=False)
        r1, _ = d.schedule("JR-0040", "instagram", DUE, ctx())
        c2 = dict(ctx("second episode"), asset_url="https://example.com/JR-0041.mp4")
        r2, blk = d.schedule("JR-0041", "instagram", DUE, c2)
        self.assertEqual((r1, r2, self.buf.creates), ("SCHEDULED", "QUOTA_DEFERRED", 0))



class T11Ledger(unittest.TestCase):
    def test_ledger_fields_slot_labels_and_unavailable(self):
        from content_os import ledger
        rows = [{"episode_id": "E1", "status": "sent", "sent_at": "2026-10-05T15:01:00Z", "platform": "youtube",
                 "post_id": "Y1", "age_hours": 30, "metrics": {"views": 9, "reactions": 1}, "external_link": "l"}]
        hist = {"youtube:Y1": {"checkpoints": {"24h": {"metrics": {"views": 7}, "observed_age_hours": 25}}}}
        c = dict(CFG, initial_test_slots=["08:00", "20:30"])
        led = ledger.build(rows, hist, {"E1": {"theme": "t", "hook_type": "question", "emotion": "sad", "bible_theme": "John 1:1"}}, c)
        l = led[0]
        self.assertEqual((l["slot"], l["publication_time"], l["latest"]["reach"], l["checkpoints"]["24h"]["views"],
                          l["checkpoints"]["72h"]), ("20:30", "20:31", "UNAVAILABLE", 7, "NOT_YET"))
        st = ledger.slot_test(led, c)
        self.assertEqual(st["platforms"]["youtube"]["verdict"], "insufficient data")


if __name__ == "__main__":
    unittest.main()
