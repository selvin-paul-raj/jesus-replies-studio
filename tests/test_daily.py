"""Daily post system safety tests. No network, no real Buffer: every external effect is mocked.
Run: python3 -m unittest discover -s tests -v"""
import datetime as dt, json, os, pathlib, shutil, sys, tempfile, types, unittest
ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from daily import pipeline as pl, states                      # noqa: E402
from daily.store import Store                                  # noqa: E402
from daily.buffer import Outcome                               # noqa: E402
from daily.redact import redact                                # noqa: E402

VERSE = "The Lord is my shepherd, I lack nothing."
URL = "https://github.com/x/y/releases/download/jr-ep-JR-0002/JR-0002.mp4"
SIZE = 1000
UTC = dt.timezone.utc


def ep(eid, title, hook, ref=("Psalm", 23, "1"), topic="fear", character="boy", emotion="sad"):
    return {"id": eid, "title": title, "character": character, "topic": topic, "emotion": emotion,
            "bible": {"book": ref[0], "chapter": ref[1], "verse": ref[2], "version": "NIV", "text": VERSE},
            "lines": [{"speaker": "person", "text": hook}, {"speaker": "jesus", "text": "I am here."}]}


GOOD_PROBE = {"format": {"format_name": "mov,mp4,m4a", "duration": "77.4"},
              "streams": [{"codec_type": "video", "codec_name": "h264", "width": 1080, "height": 1920},
                          {"codec_type": "audio", "codec_name": "aac"}]}


class FakeBuffer:
    def __init__(self):
        self.creates, self.schedules = 0, 0
        self.create_out = None
        self.schedule_out = None
        self.posts = {}

    def read(self, pid):
        p = self.posts.get(pid)
        return (dict(p), "OK") if p else (None, "NOT_FOUND")

    def create_draft(self, text, url, due):
        self.creates += 1
        out = self.create_out or Outcome("OK", post={"id": "P1"})
        if out.kind == "OK":
            self.posts[out.post["id"]] = {"id": out.post["id"], "status": "draft", "dueAt": "2026-12-31T00:00:00.000Z",
                                         "text": text, "channelService": "instagram", "_asset_source": url,
                                         "_duration_ms": 77400, "sentAt": None, "_has_sent_at_field": True}
        return out

    def schedule(self, pid, text, url, due):
        self.schedules += 1
        out = self.schedule_out or Outcome("OK", post={"id": pid})
        if out.kind == "OK" and not getattr(self, "ignore_schedule", False):
            self.posts[pid].update({"status": "scheduled", "dueAt": due.replace("Z", ".000Z")})
        return out


class Base(unittest.TestCase):
    def setUp(self):
        self.root = pathlib.Path(tempfile.mkdtemp())
        (self.root / "config").mkdir()
        shutil.copy(ROOT / "config/publishing-rules.json", self.root / "config")
        g = self.root / "generated"; g.mkdir()
        (g / "JR-0001.json").write_text(json.dumps(ep("JR-0001", "When Fear Wins", "Jesus, I froze at school today.",
                                                      ref=("John", 14, "27"), topic="shame")))
        (g / "JR-0002.json").write_text(json.dumps(ep("JR-0002", "My Father Left", "Jesus, my dad packed his bags last night.")))
        (g / "JR-0002.package.json").write_text(json.dumps({
            "instagram_caption": "A boy asks Jesus why. Psalm 23:1", "instagram_hashtags": ["#a", "#b", "#c", "#d", "#e"],
            "youtube_title": "My Father Left", "youtube_description": "Psalm 23 reply", "thumbnail_text": "He Left."}))
        (g / "release-manifest.json").write_text(json.dumps([{"episode_id": "JR-0002", "public_url": URL,
                                                               "size_bytes": SIZE, "qa_status": "PASS"}]))
        (self.root / "output/videos").mkdir(parents=True)
        (self.root / "output/thumbnails").mkdir(parents=True)
        (self.root / "output/videos/JR-0002.mp4").write_bytes(b"\x00\x00\x00\x18ftypmp42" + b"\x00" * 200)
        (self.root / "output/thumbnails/JR-0002-thumb.png").write_bytes(b"png")
        self.buf = FakeBuffer()
        self.clock = dt.datetime(2026, 10, 2, 12, 0, tzinfo=UTC)
        self.calls = []
        self.ctx = self.make_ctx()

    def make_ctx(self, run_id="run-A", dry_run=False, **kw):
        def run(cmd, env=None):
            self.calls.append(cmd)
            return types.SimpleNamespace(returncode=kw.get("rc", 0), stdout="ok", stderr="")
        store = Store(self.root)
        return pl.Ctx(self.root, store=store, run_id=run_id, dry_run=dry_run, buffer=self.buf, run=run,
                      fetch_scripture=kw.get("fetch", lambda ref: VERSE), probe=kw.get("probe", lambda p: GOOD_PROBE),
                      http_get=kw.get("http", lambda u: (206, b"\x00\x00\x00\x18ftypmp42", SIZE)),
                      now=lambda: self.clock, log=lambda m: self.calls.append(("log", m)))

    def to_waiting(self):
        st = pl.advance(self.ctx, "JR-0002")
        self.assertEqual(st["state"], "WAITING_FOR_USER", st["history"][-1])
        return st


class T01DuplicateEpisode(Base):
    def test_originality_flags_repeat(self):
        (self.root / "generated/JR-0002.json").write_text(json.dumps(
            ep("JR-0002", "When Fear Wins", "Jesus, I froze at school today.", ref=("John", 14, "27"))))
        ok, issues = pl.originality(self.ctx, json.loads((self.root / "generated/JR-0002.json").read_text()))
        self.assertFalse(ok)
        self.assertTrue(any("title" in i for i in issues) and any("hook" in i for i in issues))

    def test_next_id_and_slot_allocation_are_deterministic(self):
        self.assertEqual(pl.next_episode_id(self.ctx), "JR-0003")
        a = pl.allocate(self.ctx, "2026-10-05", "MORNING")
        self.assertEqual(pl.allocate(self.ctx, "2026-10-05", "MORNING"), a)
        self.assertNotEqual(pl.allocate(self.ctx, "2026-10-05", "NIGHT"), a)


class T02DuplicateBuffer(Base):
    def test_existing_post_id_is_reconciled_not_recreated(self):
        st = self.to_waiting()
        self.assertEqual(self.buf.creates, 1)
        s = self.ctx.store.load("JR-0002"); s["state"] = "ASSET_HOSTED"; self.ctx.store.save(s)
        st = pl.advance(self.ctx, "JR-0002")
        self.assertEqual(self.buf.creates, 1)
        self.assertEqual(st["state"], "WAITING_FOR_USER")

    def test_legacy_posts_are_never_mutated(self):
        self.ctx.legacy = {"JR-0002": "LEGACY"}
        s = self.ctx.store.load("JR-0002")
        for to in ["GENERATED", "VALIDATED", "RENDERED", "RENDER_QA_PASSED", "PACKAGED", "PACKAGE_QA_PASSED", "ASSET_HOSTED"]:
            s = self.ctx.store.transition(s, to, "test")
        s["asset_url"] = URL; self.ctx.store.save(s)
        pl.advance(self.ctx, "JR-0002")
        self.assertEqual(self.buf.creates, 0)
        with self.assertRaises(ValueError):
            pl.approve(self.ctx, "JR-0002", "2026-10-05", "08:00", "Asia/Kolkata", "S", "yes")


class T03Transitions(Base):
    def test_illegal_transitions_raise(self):
        s = self.ctx.store.load("JR-0002")
        with self.assertRaises(states.TransitionError):
            self.ctx.store.transition(s, "SCHEDULED", "skip")
        for frm, to in [("GENERATED", "RENDERED"), ("BUFFER_DRAFT", "SCHEDULED"), ("WAITING_FOR_USER", "SCHEDULED"),
                        ("SCHEDULED", "PUBLISHED_VERIFIED"), ("RENDER_QA_FAILED", "PACKAGED")]:
            with self.assertRaises(states.TransitionError):
                states.check(frm, to)

    def test_history_records_every_step(self):
        st = self.to_waiting()
        self.assertEqual([h["to"] for h in st["history"]], states.ORDER[:9])

    def test_unverifiable_scripture_blocks(self):
        self.ctx = self.make_ctx(fetch=lambda ref: None)
        st = pl.advance(self.ctx, "JR-0002")
        self.assertEqual(st["state"], "BLOCKED")
        self.ctx = self.make_ctx(fetch=lambda ref: "Something else entirely.")
        s = self.ctx.store.load("JR-0002"); s["state"] = "GENERATED"; self.ctx.store.save(s)
        self.assertEqual(pl.advance(self.ctx, "JR-0002")["state"], "VALIDATION_FAILED")


class T04FailedRender(Base):
    def test_render_failure_after_validation(self):
        (self.root / "output/videos/JR-0002.mp4").unlink()
        st = self.ctx.store.load("JR-0002")
        for to in ["GENERATED", "VALIDATED"]:
            st = self.ctx.store.transition(st, to, "t")
        self.ctx = self.make_ctx(rc=1)
        st = pl.advance(self.ctx, "JR-0002")
        self.assertEqual(st["state"], "RENDER_FAILED")
        self.assertEqual(self.buf.creates, 0)


class T05FailedQA(Base):
    def test_over_ceiling_fails_and_is_not_trimmed(self):
        bad = json.loads(json.dumps(GOOD_PROBE)); bad["format"]["duration"] = "120.0"
        self.ctx = self.make_ctx(probe=lambda p: bad)
        st = pl.advance(self.ctx, "JR-0002")
        self.assertEqual(st["state"], "RENDER_QA_FAILED")
        self.assertIn("auto-trim disabled", st["errors"][-1]["detail"])

    def test_landscape_or_silent_fails(self):
        bad = {"format": {"format_name": "mp4", "duration": "70"}, "streams": [{"codec_type": "video", "width": 1920, "height": 1080}]}
        self.ctx = self.make_ctx(probe=lambda p: bad)
        st = pl.advance(self.ctx, "JR-0002")
        self.assertEqual(st["state"], "RENDER_QA_FAILED")
        self.assertIn("no audio stream", st["errors"][-1]["detail"])


class T06MissingAsset(Base):
    def test_unreachable_asset_fails_hosting(self):
        def boom(u): raise OSError("404")
        self.ctx = self.make_ctx(http=boom)
        st = pl.advance(self.ctx, "JR-0002")
        self.assertEqual(st["state"], "HOSTING_FAILED")
        self.assertEqual(self.buf.creates, 0)

    def test_size_mismatch_fails_hosting(self):
        self.ctx = self.make_ctx(http=lambda u: (200, b"\x00\x00\x00\x18ftyp", SIZE - 1))
        self.assertEqual(pl.advance(self.ctx, "JR-0002")["state"], "HOSTING_FAILED")


class T07BufferFailure(Base):
    def test_rejected_create_is_buffer_failed_without_pending(self):
        self.buf.create_out = Outcome("REJECTED", detail="Invalid post")
        st = pl.advance(self.ctx, "JR-0002")
        self.assertEqual(st["state"], "BUFFER_FAILED")
        self.assertIsNone(st["buffer"]["pending_mutation"])
        self.assertEqual(st["buffer"]["create_attempts"], 1)


class T08NoPostId(Base):
    def test_no_post_id_blocks_and_keeps_journal(self):
        self.buf.create_out = Outcome("NO_POST_ID")
        st = pl.advance(self.ctx, "JR-0002")
        self.assertEqual(st["state"], "BLOCKED")
        self.assertIsNotNone(st["buffer"]["pending_mutation"])


class T09RetryPrevention(Base):
    def test_unknown_outcome_never_retried(self):
        self.buf.create_out = Outcome("UNKNOWN")
        pl.advance(self.ctx, "JR-0002")
        s = self.ctx.store.load("JR-0002"); s["state"] = "ASSET_HOSTED"; self.ctx.store.save(s)   # simulate a crash-restart
        st = pl.advance(self.ctx, "JR-0002")
        self.assertEqual(self.buf.creates, 1)
        self.assertEqual(st["state"], "BLOCKED")

    def test_rejected_retried_at_most_once(self):
        self.buf.create_out = Outcome("REJECTED", detail="x")
        for _ in range(3):
            st = self.ctx.store.load("JR-0002")
            if st["state"] == "BUFFER_FAILED":
                self.ctx.store.reopen(st, "fixed")
            pl.advance(self.ctx, "JR-0002")
        self.assertEqual(self.buf.creates, 2)
        self.assertEqual(self.ctx.store.load("JR-0002")["state"], "BLOCKED")


class T10Approval(Base):
    def test_schedule_requires_approval(self):
        self.to_waiting()
        with self.assertRaises(ValueError):
            pl.schedule(self.ctx, "JR-0002")
        self.assertEqual(self.buf.schedules, 0)

    def test_ambiguous_or_bad_approvals_refused(self):
        self.to_waiting()
        for args in [("2026-10-05", "08:00", "UTC", "S", "yes"), ("2026-10-05", "8am", "Asia/Kolkata", "S", "yes"),
                     ("2026-10-05", "10:15", "Asia/Kolkata", "S", "yes"), ("2026-10-01", "08:00", "Asia/Kolkata", "S", "yes"),
                     ("2026-10-05", "08:00", "Asia/Kolkata", "S", "")]:
            with self.assertRaises(ValueError):
                pl.approve(self.ctx, "JR-0002", *args)
        st = pl.approve(self.ctx, "JR-0002", "2026-10-05", "08:00", "Asia/Kolkata", "Selvin", "Approve JR-0002 Mon 08:00 IST")
        self.assertEqual(st["approval"]["due_at"], "2026-10-05T02:30:00Z")


class T11SchedulingVerification(Base):
    def approved(self):
        self.to_waiting()
        pl.approve(self.ctx, "JR-0002", "2026-10-05", "08:00", "Asia/Kolkata", "Selvin", "Approve JR-0002 Mon 08:00 IST")

    def test_success_needs_read_back(self):
        self.approved()
        st = pl.schedule(self.ctx, "JR-0002")
        self.assertEqual(st["state"], "SCHEDULED")
        self.assertEqual(st["buffer"]["due_at"], "2026-10-05T02:30:00.000Z")

    def test_ok_response_but_still_draft_is_not_scheduled(self):
        self.approved()
        self.buf.ignore_schedule = True
        st = pl.schedule(self.ctx, "JR-0002")
        self.assertEqual(st["state"], "BLOCKED")

    def test_already_scheduled_is_reconciled_without_mutation(self):
        self.approved()
        self.buf.posts["P1"].update({"status": "scheduled", "dueAt": "2026-10-05T02:30:00.000Z"})
        st = pl.schedule(self.ctx, "JR-0002")
        self.assertEqual((st["state"], self.buf.schedules), ("SCHEDULED", 0))


class T12PublishVerification(Base):
    def scheduled(self):
        self.to_waiting()
        pl.approve(self.ctx, "JR-0002", "2026-10-05", "08:00", "Asia/Kolkata", "Selvin", "ok")
        pl.schedule(self.ctx, "JR-0002")

    def test_before_due_is_not_failure(self):
        self.scheduled()
        self.assertEqual(pl.verify_published(self.ctx, "JR-0002")["state"], "SCHEDULED")

    def test_sent_is_verified(self):
        self.scheduled()
        self.clock = dt.datetime(2026, 10, 5, 3, 0, tzinfo=UTC)
        self.buf.posts["P1"].update({"status": "sent", "sentAt": "2026-10-05T02:30:05Z"})
        st = pl.verify_published(self.ctx, "JR-0002")
        self.assertEqual(st["state"], "PUBLISHED_VERIFIED")
        self.assertEqual([h["to"] for h in st["history"]][-2:], ["PUBLISHED", "PUBLISHED_VERIFIED"])

    def test_past_grace_unsent_fails(self):
        self.scheduled()
        self.clock = dt.datetime(2026, 10, 5, 4, 0, tzinfo=UTC)
        self.assertEqual(pl.verify_published(self.ctx, "JR-0002")["state"], "PUBLISH_VERIFICATION_FAILED")


class T13Concurrency(Base):
    def test_second_run_is_refused_while_locked(self):
        self.assertTrue(self.ctx.store.acquire("JR-0002", "run-A"))
        other = self.make_ctx(run_id="run-B")
        self.assertIsNone(pl.advance(other, "JR-0002"))
        self.assertEqual(self.buf.creates, 0)
        self.ctx.store.release("JR-0002", "run-A")
        self.assertEqual(pl.advance(other, "JR-0002")["state"], "WAITING_FOR_USER")
        self.assertFalse((self.root / "episodes/JR-0002/.lock").exists())


class T14Redaction(Base):
    def test_secret_never_reaches_state_or_logs(self):
        secret = "pk_live_SUPERSECRETVALUE123"
        os.environ["BUFFER_API_KEY"] = secret
        try:
            self.buf.create_out = Outcome("REJECTED", detail=f"bad key {secret} Bearer {secret}")
            pl.advance(self.ctx, "JR-0002")
            blob = (self.root / "episodes/JR-0002/state.json").read_text() + json.dumps(self.calls)
            self.assertNotIn(secret, blob)
            self.assertNotIn(secret, redact(f"Authorization: Bearer {secret}"))
        finally:
            del os.environ["BUFFER_API_KEY"]


class T16GenerationBlockReopen(Base):
    def test_unauthored_blocks_then_resumes_once_authored(self):
        f = self.root / "generated/JR-0002.json"; body = f.read_text(); f.unlink()
        st = pl.advance(self.ctx, "JR-0002")
        self.assertEqual((st["state"], st["generation"]), ("BLOCKED", "BLOCKED"))
        f.write_text(body)
        self.assertEqual(pl.advance(self.ctx, "JR-0002")["state"], "WAITING_FOR_USER")

    def test_other_blocks_do_not_reopen(self):
        self.ctx = self.make_ctx(fetch=lambda ref: None)
        pl.advance(self.ctx, "JR-0002")
        self.ctx = self.make_ctx()
        self.assertEqual(pl.advance(self.ctx, "JR-0002")["state"], "BLOCKED")
        self.assertEqual(self.buf.creates, 0)


class T15DryRun(Base):
    def test_dry_run_never_mutates(self):
        dry = self.make_ctx(dry_run=True)
        st = pl.advance(dry, "JR-0002")
        self.assertEqual(st["state"], "ASSET_HOSTED")
        self.assertEqual((self.buf.creates, self.buf.schedules), (0, 0))


if __name__ == "__main__":
    unittest.main()
