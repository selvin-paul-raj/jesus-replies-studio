"""Tests for the 2026-10-16 deep-review fixes (DEC-JR-007): honesty line, crisis gate,
one duration setting, bundled BSB scripture, original audio rotation.
No network, no Buffer. Run: python3 -m unittest discover -s tests -v"""
import json, os, pathlib, re, shutil, subprocess, sys, unittest
ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from daily import pipeline as pl, bsb, safety                  # noqa: E402
from test_daily import Base, ep, GOOD_PROBE, VERSE             # noqa: E402

EID = "JR-0064"
GOOD_PKG = {"instagram_caption": "He asks Jesus why. Psalm 23:1 (BSB)\n\n" + safety.HONESTY_LINE,
            "instagram_hashtags": ["#a", "#b", "#c", "#d", "#e"], "youtube_title": "My Father Left",
            "youtube_description": "Psalm 23 reply (BSB)\n\n" + safety.HONESTY_LINE, "thumbnail_text": "He Left."}


class NewEpisode(Base):
    """A JR-0064 episode (new rules) at PACKAGED, ready for package QA."""
    def setUp(self):
        super().setUp()
        self.write(ep(EID, "Nobody Called Back", "Jesus, I sent the message and nobody replied.", ref=("Psalm", 23, "1")), GOOD_PKG)
        (self.root / f"output/videos/{EID}.mp4").write_bytes(b"\x00\x00\x00\x18ftypmp42" + b"\x00" * 200)
        (self.root / f"output/thumbnails/{EID}-thumb.png").write_bytes(b"png")
        s = self.ctx.store.load(EID)
        for to in ["GENERATED", "VALIDATED", "RENDERED", "RENDER_QA_PASSED", "PACKAGED"]:
            s = self.ctx.store.transition(s, to, "test")
        self.ctx.store.save(s)

    def write(self, episode, pkg):
        g = self.root / "generated"
        (g / f"{EID}.json").write_text(json.dumps(episode))
        (g / f"{EID}.package.json").write_text(json.dumps(pkg))

    def pkg(self, **kw):
        return {**GOOD_PKG, **kw}

    def qa(self):
        return pl.step_package_qa(self.ctx, self.ctx.store.load(EID))


class T20HonestyLine(NewEpisode):
    def test_line_present_passes(self):
        st = self.qa()
        self.assertEqual(st["state"], "PACKAGE_QA_PASSED", st["errors"][-1:] if st["errors"] else st["history"][-1])

    def test_missing_line_fails_both_fields(self):
        self.write(json.loads((self.root / f"generated/{EID}.json").read_text()),
                   self.pkg(instagram_caption="He asks Jesus why. Psalm 23:1", youtube_description="Psalm 23 reply"))
        st = self.qa()
        self.assertEqual(st["state"], "PACKAGE_QA_FAILED")
        self.assertIn("honesty line missing from instagram_caption", st["errors"][-1]["detail"])
        self.assertIn("honesty line missing from youtube_description", st["errors"][-1]["detail"])

    def test_banned_phrase_fails_and_heal_fixes(self):
        self.write(json.loads((self.root / f"generated/{EID}.json").read_text()),
                   self.pkg(youtube_description="Psalm 23. Real questions, answered in His words."))
        st = self.qa()
        self.assertEqual(st["state"], "PACKAGE_QA_FAILED")
        self.assertIn("banned phrase", st["errors"][-1]["detail"])
        st, action = pl.heal(self.ctx, st)
        self.assertTrue(action)
        pk = json.loads((self.root / f"generated/{EID}.package.json").read_text())
        self.assertIn("answered from Scripture", pk["youtube_description"])
        self.assertIn(safety.HONESTY_LINE, pk["youtube_description"])
        st = pl.advance(self.ctx, EID)          # back through the same gate
        self.assertEqual(st["package_qa"], "PASS", st["history"][-1])

    def test_legacy_queued_packages_not_failed_for_missing_line(self):
        # JR-0002 (already in Buffer era) keeps passing without the line
        s = self.ctx.store.load("JR-0002")
        for to in ["GENERATED", "VALIDATED", "RENDERED", "RENDER_QA_PASSED", "PACKAGED"]:
            s = self.ctx.store.transition(s, to, "test")
        st = pl.step_package_qa(self.ctx, s)
        self.assertEqual(st["state"], "PACKAGE_QA_PASSED")

    def test_brief_carries_line_and_writer_rules(self):
        b = pl.brief(self.ctx, "JR-0065")
        self.assertEqual(b["honesty_line"], safety.HONESTY_LINE)
        self.assertTrue(any("promise an outcome" in r for r in b["writer_rules"]))
        self.assertTrue(any("medical" in r for r in b["writer_rules"]))
        self.assertTrue(any("doctrine" in r for r in b["writer_rules"]))


class T21CrisisGate(NewEpisode):
    def crisis_episode(self):
        e = ep(EID, "The Sleeves", "Jesus, I've been cutting myself again and nobody knows.", ref=("Psalm", 23, "1"))
        return e

    def test_classifier(self):
        self.assertTrue(safety.crisis_check(self.crisis_episode())[0])
        self.assertTrue(safety.crisis_check(ep(EID, "t", "Jesus, sometimes I think everyone is better off without me."))[0])
        self.assertTrue(safety.crisis_check(ep(EID, "t", "Jesus, my stepdad hit my mom again last night."))[0])
        self.assertFalse(safety.crisis_check(ep(EID, "t", "Jesus, my friend got engaged and I smiled in every photo."))[0])
        # the required crisis line itself never triggers the gate
        benign = ep(EID, "t", "Jesus, I failed my exam.")
        self.assertFalse(safety.crisis_check(benign, {"instagram_caption": safety.CRISIS_LINE})[0])

    def test_crisis_line_required(self):
        self.write(self.crisis_episode(), GOOD_PKG)
        st = self.qa()
        self.assertEqual(st["state"], "PACKAGE_QA_FAILED")
        self.assertIn("crisis line missing", st["errors"][-1]["detail"])

    def test_held_episode_is_never_sent_to_buffer_or_approved(self):
        cap = GOOD_PKG["instagram_caption"] + "\n" + safety.CRISIS_LINE
        desc = GOOD_PKG["youtube_description"] + "\n" + safety.CRISIS_LINE
        self.write(self.crisis_episode(), self.pkg(instagram_caption=cap, youtube_description=desc))
        s = self.ctx.store.load(EID)
        s["state"] = "PACKAGED"; self.ctx.store.save(s)
        st = pl.advance(self.ctx, EID)
        self.assertEqual(st["state"], "PACKAGE_QA_PASSED")
        self.assertEqual(st["review"]["status"], "HELD_FOR_REVIEW")
        self.assertIn("self_harm", st["review"]["crisis"])
        self.assertEqual(self.buf.creates, 0)
        st = pl.advance(self.ctx, EID)               # stays held on every later run
        self.assertEqual(st["state"], "PACKAGE_QA_PASSED")
        self.assertEqual(self.buf.creates, 0)
        st["state"] = "WAITING_FOR_USER"
        self.ctx.rules["require_human_approval"] = False
        self.assertEqual(pl.auto_approve(self.ctx, st)["state"], "WAITING_FOR_USER")

    def test_held_episode_is_in_content_os_held_list(self):
        from content_os import cli as cocli
        s = self.ctx.store.load(EID)
        s["review"] = {"status": "HELD_FOR_REVIEW"}; self.ctx.store.save(s)
        self.assertIn(EID, cocli.review_holds(self.root))

    def test_jesus_line_lint(self):
        e = ep(EID, "t", "Jesus, will I get the job?")
        e["lines"].append({"speaker": "jesus", "text": "You will get the job, I promise it will happen."})
        e["lines"].append({"speaker": "jesus", "text": "You don't need a doctor, just pray."})
        e["lines"].append({"speaker": "jesus", "text": "Invest in gold this week."})
        lint = safety.jesus_lint(e)
        self.assertEqual(set(lint), {"promised_outcome", "medical_advice", "financial_advice"})
        self.assertEqual(safety.jesus_lint(ep(EID, "t", "Jesus, I'm tired.")), {})


class T22Duration(Base):
    def test_one_setting(self):
        d = json.loads((ROOT / "config/publishing-rules.json").read_text())["duration"]
        self.assertEqual(d["target_seconds"], [50, 62])
        self.assertEqual(d["ceiling_seconds"], 75)
        cos = json.loads((ROOT / "config/content-os.json").read_text())
        self.assertNotIn("duration_ceiling_seconds", cos)
        for f in ("scripts/content_os/strategy.py", "scripts/daily/pipeline.py"):
            src = (ROOT / f).read_text()
            self.assertNotRegex(src, r"\b(?:65|78|70|80|90)\s*s?\b\s*(?:if|else|<=|>=)", f)

    def test_brief_and_strategy_read_it(self):
        from content_os import strategy
        b = pl.brief(self.ctx, "JR-0003")
        self.assertEqual(b["duration_target_seconds"], [50, 62])
        self.assertEqual(b["duration_ceiling_seconds"], 75)
        rules = strategy.duration_rules(ROOT)
        self.assertEqual([strategy.dur_bucket(x, rules) for x in (58, 70, 80)], ["<=62s", "63-75s", ">75s"])

    def test_prerender_estimate_over_ceiling_rejected(self):
        def run(cmd, env=None):
            import types
            return types.SimpleNamespace(returncode=0, stdout="[validate] PASS JR-0002 lines=9 estimated_seconds=81.40", stderr="")
        self.ctx.run = run
        s = self.ctx.store.load("JR-0002")
        s = self.ctx.store.transition(s, "GENERATED", "t")
        st = pl.step_validated(self.ctx, s)
        self.assertEqual(st["state"], "VALIDATION_FAILED")
        self.assertIn("over the 75s ceiling", st["errors"][-1]["detail"])

    def test_render_qa_rejects_80s(self):
        bad = json.loads(json.dumps(GOOD_PROBE)); bad["format"]["duration"] = "80.0"
        self.ctx.probe = lambda p: bad
        s = self.ctx.store.load("JR-0002")
        for to in ["GENERATED", "VALIDATED", "RENDERED"]:
            s = self.ctx.store.transition(s, to, "t")
        st = pl.step_render_qa(self.ctx, s)
        self.assertEqual(st["state"], "RENDER_QA_FAILED")


class T23BSB(unittest.TestCase):
    def test_lookup(self):
        self.assertTrue(bsb.lookup("John 3:16").startswith("For God so loved the world"))
        self.assertEqual(bsb.lookup("Psalms 23:1"), bsb.lookup("Psalm 23:1"))
        self.assertIn("The LORD is my shepherd", bsb.lookup("Psalms 23:1"))
        two = bsb.lookup("Romans 8:28-29")
        self.assertTrue(two.startswith(bsb.lookup("Romans 8:28")) and two.endswith(bsb.lookup("Romans 8:29")))
        self.assertIsNone(bsb.lookup("Hezekiah 1:1"))
        self.assertIsNone(bsb.lookup("John 3:999"))
        self.assertIsNone(bsb.lookup("John three"))

    def test_bundle_is_complete_and_public_domain(self):
        d = json.loads((ROOT / "data/bible/bsb.json").read_text())
        self.assertGreater(len(d["verses"]), 31000)
        self.assertIn("public domain", d["license"].lower())

    def test_daily_cards_are_bsb(self):
        d = json.loads((ROOT / "scripts/bible.json").read_text())
        self.assertEqual(d["translation"], "BSB")
        for e in d["promises"]:
            self.assertEqual(e["text"], bsb.lookup(e["reference"]), e["reference"])

    def test_no_niv_or_scraper_left_in_the_pipeline(self):
        self.assertFalse((ROOT / "scripts/fetch-passage.py").exists())
        for f in ("scripts/daily/pipeline.py", "scripts/daily/jr_daily.py", "scripts/get-bible-verse.ts",
                  "scripts/build-all-bible-posts.ts", "scripts/daily-bible-post.ts", "scripts/render_gate.py",
                  ".github/workflows/daily-bible-post.yml"):
            src = (ROOT / f).read_text()
            self.assertNotIn("biblegateway", src.lower(), f)
            self.assertNotIn('"NIV"', src, f)


class T23BSBValidation(Base):
    def test_default_lookup_verifies_and_rejects_niv_wording(self):
        g = self.root / "generated"
        e = ep("JR-0002", "My Father Left", "Jesus, my dad packed his bags last night.")
        e["bible"].update(book="Psalms", chapter=23, verse="1", version="BSB", text=bsb.lookup("Psalm 23:1"))
        (g / "JR-0002.json").write_text(json.dumps(e))
        self.ctx.fetch_scripture = bsb.lookup
        s = self.ctx.store.transition(self.ctx.store.load("JR-0002"), "GENERATED", "t")
        self.assertEqual(pl.step_validated(self.ctx, s)["state"], "VALIDATED")
        e["bible"]["text"] = "The LORD is my shepherd, I lack nothing."          # NIV wording
        (g / "JR-0002.json").write_text(json.dumps(e))
        s = self.ctx.store.load("JR-0002"); s["state"] = "GENERATED"; self.ctx.store.save(s)
        st = pl.step_validated(self.ctx, s)
        self.assertEqual(st["state"], "VALIDATION_FAILED")
        self.assertIn("does not match BSB source", st["errors"][-1]["detail"])
        e["bible"]["version"] = "NIV"
        (g / "JR-0002.json").write_text(json.dumps(e))
        s = self.ctx.store.load("JR-0002"); s["state"] = "GENERATED"; self.ctx.store.save(s)
        self.assertIn("not BSB", pl.step_validated(self.ctx, s)["errors"][-1]["detail"])


class T25VerseStory(unittest.TestCase):
    def test_story_switch_and_payload(self):
        d = json.loads((ROOT / "config/publishing-rules.json").read_text())["daily_verse"]
        self.assertIn(d["instagram_post_type"], ("story", "post"))
        self.assertEqual(d["instagram_post_type"], "story")
        pub = (ROOT / "scripts/publish-buffer.ts").read_text()
        self.assertIn("type: story, shouldShareToFeed: false", pub)
        self.assertIn("instagramType", (ROOT / "scripts/daily-bible-post.ts").read_text())
        self.assertIn('id="BibleVerseStory"', (ROOT / "src/Root.tsx").read_text())


class T26Slots(unittest.TestCase):
    def test_one_slot_table(self):
        rules = json.loads((ROOT / "config/publishing-rules.json").read_text())
        self.assertEqual(rules["slots"], {"MORNING": "08:00", "NIGHT": "20:30"})
        cos = json.loads((ROOT / "config/content-os.json").read_text())
        self.assertNotIn("initial_test_slots", cos)
        from content_os import cli as cocli
        c = cocli.cfg_load()
        self.assertEqual(c["initial_test_slots"], ["08:00", "20:30"])

    def test_no_top_of_hour_crons(self):
        for wf in (ROOT / ".github/workflows").glob("*.yml"):
            for line in wf.read_text().splitlines():
                m = re.match(r"\s*-\s*cron:\s*['\"](\S+)\s", line)
                if m:
                    self.assertNotEqual(m.group(1), "0", f"{wf.name}: {line.strip()}")

    def test_every_workflow_that_pushes_has_concurrency(self):
        for wf in (ROOT / ".github/workflows").glob("*.yml"):
            src = wf.read_text()
            if "git push" in src or "contents: write" in src:
                self.assertIn("concurrency:", src, wf.name)


def fnv1a(text):
    h = 0x811c9dc5
    for b in text.encode():
        h ^= b
        h = (h * 0x01000193) & 0xFFFFFFFF
    return h


class T24AudioRotation(unittest.TestCase):
    def tracks(self):
        src = (ROOT / "src/assetResolver.ts").read_text()
        block = src.split("BGM_TRACKS", 1)[1].split("];", 1)[0]
        return re.findall(r'"(audio/[^"]+)"', block)

    def test_tracks_exist_and_are_licensed(self):
        t = self.tracks()
        self.assertGreaterEqual(len(t), 4)
        lic = (ROOT / "public/audio/LICENSES.md").read_text()
        for x in t:
            self.assertTrue((ROOT / "public" / x).is_file(), x)
            self.assertIn(pathlib.Path(x).name, lic)
        self.assertIn("original", lic.lower())

    def test_third_party_track_gone(self):
        self.assertFalse((ROOT / "public/audio/hallelujah.mp3").exists())
        for d in ("src", "scripts"):
            for p in (ROOT / d).rglob("*"):
                if p.suffix in (".ts", ".tsx", ".json", ".py") and p.is_file():
                    self.assertNotIn("hallelujah", p.read_text(errors="ignore").lower(), str(p))

    def test_rotation_is_deterministic_and_uses_every_track(self):
        t = self.tracks()
        picks = [t[fnv1a(f"JR-{n:04d}") % len(t)] for n in range(1, 121)]
        self.assertEqual(set(picks), set(t))
        self.assertEqual(picks, [t[fnv1a(f"JR-{n:04d}") % len(t)] for n in range(1, 121)])

    def test_typescript_rotation_check(self):
        if not (ROOT / "node_modules/.bin/tsx").exists():
            self.skipTest("node_modules not installed (CI runs Python tests before npm ci)")
        r = subprocess.run(["npx", "tsx", "scripts/check-audio-rotation.ts"], cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        # Python mirror and TS agree on one id
        r2 = subprocess.run(["npx", "tsx", "-e", "import {pickBgmTrack} from './src/assetResolver'; console.log(pickBgmTrack('JR-0064'))"],
                            cwd=ROOT, capture_output=True, text=True)
        t = self.tracks()
        self.assertEqual(r2.stdout.strip(), t[fnv1a("JR-0064") % len(t)])


if __name__ == "__main__":
    unittest.main()
