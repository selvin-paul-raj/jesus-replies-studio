"""DEC-JR-018 (2026-11-05): Part 2 sequels, 'Jesus replies to your comment', Tamil/Hindi subtitle versions,
weekly YouTube compilation, weekly Instagram verse carousel. Fake Buffer only; no network."""
import copy, datetime as dt, json, pathlib, sys, tempfile, unittest
ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from daily import pipeline as pl, formats, scripture
from daily.buffer import Outcome
from content_os import brain, carousel, compilation, cli
from content_os.client import Buffer as OSBuffer

CFG = json.loads((ROOT / "config/content-os.json").read_text())
G = ROOT / "generated"


def load(eid):
    return json.loads((G / f"{eid}.json").read_text())


class IRVBundles(unittest.TestCase):
    def test_verse_counts_cover_every_kjv_verse(self):
        kjv = set(scripture.verses(ROOT / "data/bible/kjv.json"))
        for lang in ("ta", "hi"):
            d = json.loads((ROOT / f"data/bible/{lang}-irv.json").read_text(encoding="utf-8"))
            self.assertIn("CC BY-SA 4.0", d["license"])
            self.assertIn("Bridge Connectivity Solutions", d["copyright"])
            self.assertTrue(d["attribution_line"].startswith(("Tamil Scripture", "Hindi Scripture")))
            self.assertEqual(kjv - set(d["verses"]), set(), lang)            # nothing missing
            self.assertLessEqual(len(set(d["verses"]) - kjv), 2)             # versification splits only
            self.assertFalse([k for k, t in d["verses"].items() if not t.strip()])
        hi = json.loads((ROOT / "data/bible/hi-irv.json").read_text(encoding="utf-8"))["verses"]
        self.assertNotIn("(इब्रा.", hi["Genesis 1:1"])                         # cross-references stripped


class SubtitleVersions(unittest.TestCase):
    def test_authored_variants_pass(self):
        for eid in ("JR-0099", "JR-0100"):
            self.assertEqual(formats.script_problems(load(eid), ROOT), [], eid)

    def test_verse_must_be_bundled_text_verbatim(self):
        e = load("JR-0099")
        e["subtitles"]["verse_text"] = e["subtitles"]["verse_text"].replace("மறப்பதில்லை", "மறக்க மாட்டேன்")
        self.assertTrue(any("verbatim" in p for p in formats.subtitle_problems(e, ROOT)))

    def test_lines_align_and_attribution(self):
        e = load("JR-0100")
        e["subtitles"]["lines"] = e["subtitles"]["lines"][:-1]
        e["subtitles"]["attribution"] = "Hindi Bible"
        probs = formats.subtitle_problems(e, ROOT)
        self.assertTrue(any("entries" in p for p in probs) and any("attribution" in p for p in probs))
        pk = json.loads((G / "JR-0100.package.json").read_text())
        self.assertEqual(formats.package_problems(load("JR-0100"), pk, ROOT), [])
        pk["youtube_description"] = pk["youtube_description"].replace(load("JR-0100")["subtitles"]["attribution"], "")
        self.assertTrue(formats.package_problems(load("JR-0100"), pk, ROOT))

    def test_config_flag_turns_lanes_off(self):
        self.assertIn("subtitles-ta", cli.cfg_load()["series_lanes"])
        p = ROOT / "config/content-os.json"
        raw = p.read_text()
        try:
            d = json.loads(raw); d["subtitle_versions"]["enabled"] = False
            p.write_text(json.dumps(d))
            lanes = cli.cfg_load()["series_lanes"]
            self.assertNotIn("subtitles-ta", lanes); self.assertNotIn("subtitles-hi", lanes)
        finally:
            p.write_text(raw)

    def test_variant_not_compared_with_its_source(self):
        with tempfile.TemporaryDirectory() as d:
            ctx = pl.Ctx(ROOT, dry_run=True)
            ok, issues = pl.originality(ctx, load("JR-0099"))
            self.assertFalse(any("JR-0063" in i for i in issues), issues)


class CommentReplies(unittest.TestCase):
    def test_authored_comment_episode_passes(self):
        self.assertEqual(formats.script_problems(load("JR-0098"), ROOT), [])

    def test_unlogged_crisis_and_handle(self):
        e = load("JR-0098")
        e["comment"]["text"] = "I don't want to live anymore"
        probs = formats.comment_problems(e, ROOT)
        self.assertTrue(any("not in content-os/community" in p for p in probs))
        self.assertTrue(any("crisis" in p for p in probs))
        e = load("JR-0098"); e["comment"]["show_handle"] = True; e["comment"]["handle"] = "@someone"
        self.assertTrue(any("show_handle" in p for p in formats.comment_problems(e, ROOT)))
        self.assertFalse(CFG["comment_reply"]["show_handle"])


class Sequels(unittest.TestCase):
    def test_part2_points_back(self):
        e, pk = load("JR-0097"), json.loads((G / "JR-0097.package.json").read_text())
        self.assertEqual(formats.package_problems(e, pk, ROOT), [])
        pk["instagram_caption"] = pk["instagram_caption"].replace("Part 1", "the first one")
        self.assertTrue(formats.package_problems(e, pk, ROOT))
        self.assertNotIn("JR-0060", json.dumps(json.loads((G / "JR-0097.package.json").read_text())))


class Lanes(unittest.TestCase):
    def test_week_of_nov_9(self):
        c = cli.cfg_load()
        got = {pos: (n, i["episode_id"]) for pos, (n, i) in brain.lane_slots("2026-11-09", c).items()}
        self.assertEqual(got[0], ("family-pressure", "JR-0096"))      # Monday 08:00 untouched
        self.assertEqual(got[2], ("sequels", "JR-0097"))              # Tuesday 08:00
        self.assertEqual(got[7], ("comment-replies", "JR-0098"))      # Thursday 19:30
        self.assertEqual(got[5][0], "subtitles-ta"); self.assertEqual(got[11][0], "subtitles-hi")

    def test_no_double_booking(self):
        c = copy.deepcopy(cli.cfg_load())
        c["series_lanes"]["sequels"]["backlog"][0]["weekday"] = 0       # try to take the family slot
        got = brain.lane_slots("2026-11-09", c)
        self.assertEqual(got[0][0], "family-pressure")
        self.assertNotIn("sequels", [n for n, _ in got.values()])


class FakeBuf:
    def __init__(self, posts=()):
        self.posts, self.created = list(posts), []

    def list_posts(self, platform):
        return self.posts, "OK"

    def create_carousel(self, platform, text, urls, due, first_comment=None):
        self.created.append((platform, text, urls, due, first_comment))
        return Outcome("OK", post={"id": "p1", "status": "scheduled", "dueAt": due})

    def read(self, pid):
        return {"id": pid, "status": "scheduled", "dueAt": "x", "_first_comment": "q?"}, "OK"


class Carousel(unittest.TestCase):
    def c(self):
        return carousel.load(ROOT, "CAR-2026-11-07")

    def test_first_carousel_passes_gates(self):
        self.assertEqual(carousel.problems(self.c(), CFG), [])

    def test_gates(self):
        c = self.c(); c["slides"][1]["text"] = c["slides"][1]["text"].replace("Honour", "Honor")
        self.assertTrue(any("verbatim" in p for p in carousel.problems(c, CFG)))
        c = self.c(); c["slides"][2]["r10_context"] = ""
        self.assertTrue(any("r10_context" in p for p in carousel.problems(c, CFG)))
        c = self.c(); c["slot"]["time"] = "19:30"
        self.assertTrue(any("collides" in p for p in carousel.problems(c, CFG)))
        c = self.c(); c["slides"] = c["slides"][:3]
        self.assertTrue(carousel.problems(c, CFG))

    def test_schedule_once_and_adopt(self):
        c = self.c(); c.pop("buffer", None)
        now = dt.datetime(2026, 11, 5, 12, 0, tzinfo=dt.timezone.utc)
        b = FakeBuf()
        res, rec = carousel.schedule(ROOT, c, b, now, lambda u: 200, dry_run=False, sha="0" * 40)
        self.assertEqual(res, "SCHEDULED"); self.assertEqual(len(b.created), 1)
        self.assertEqual(len(b.created[0][2]), 7)
        self.assertTrue(all(u.startswith("https://raw.githubusercontent.com/") for u in b.created[0][2]))
        res2, _ = carousel.schedule(ROOT, c, b, now, lambda u: 200, dry_run=False, sha="0" * 40)
        self.assertEqual(res2, "ALREADY_SCHEDULED"); self.assertEqual(len(b.created), 1)
        c2 = self.c(); c2.pop("buffer", None)
        b2 = FakeBuf([{"id": "old", "status": "scheduled", "text": carousel.caption(c2)}])
        self.assertEqual(carousel.schedule(ROOT, c2, b2, now, lambda u: 200, dry_run=False, sha="0" * 40)[0], "ADOPTED")
        self.assertEqual(b2.created, [])

    def test_mutation_shape(self):
        sent = []
        b = OSBuffer(lambda q: (sent.append(q) or (200, {"data": {"createPost": {"post": {"id": "x", "status": "scheduled"}}}})),
                     {"buffer": {"channels": {"instagram": "ig"}}})
        out = b.create_carousel("instagram", "t", ["https://a/1.png", "https://a/2.png"], "2026-11-07T12:30:00+05:30", first_comment="q?")
        self.assertEqual(out.kind, "OK")
        self.assertIn("type: post", sent[0]); self.assertEqual(sent[0].count("image: { url:"), 2)
        self.assertNotIn("firstComment", sent[0])          # paid Buffer feature; off on this plan
        b.cfg["buffer"]["instagram_first_comment"] = True
        b.create_carousel("instagram", "t", ["https://a/1.png"], "2026-11-07T12:30:00+05:30", first_comment="q?")
        self.assertIn('firstComment: "q?"', sent[1])


class FirstCommentPaidPlan(unittest.TestCase):
    def test_flag_off_on_this_plan(self):
        rules = json.loads((ROOT / "config/publishing-rules.json").read_text())
        self.assertFalse(rules["buffer"]["instagram_first_comment"])   # "First comment requires a paid plan" (2026-11-05)


class Compilation(unittest.TestCase):
    def test_select_fits_6_to_8_minutes_and_chapters(self):
        cands = [{"episode_id": f"JR-{i:04d}", "date": f"2026-11-0{2 + i % 6}", "time": "08:00", "views": 100 * i} for i in range(1, 15)]
        dur = {c["episode_id"]: 52.0 for c in cands}
        clips, total, ok = compilation.select(cands, dur, 360, 480)
        self.assertTrue(ok); self.assertLessEqual(total, 480); self.assertGreaterEqual(total, 360)
        self.assertEqual([c["date"] for c in clips], sorted(c["date"] for c in clips))
        eps = {c["episode_id"]: {"title": "Jesus... X", "bible": {"book": "Psalms", "chapter": 1, "verse": 1, "version": "KJV"}} for c in cands}
        ch = compilation.chapters(clips, dur, eps)
        self.assertEqual(ch[0][0], "0:00"); self.assertGreaterEqual(len(ch), 3)
        self.assertIn("Psalm 1:1 (KJV)", ch[0][1])
        meta = compilation.metadata("2026-11-02", clips, dur, eps)
        self.assertLessEqual(len(meta["title"]), 100); self.assertIn("Chapters", meta["description"])
        self.assertIn("King James Version", meta["description"])

    def test_buffer_longform_flag_off_and_pulled_excluded(self):
        self.assertFalse(CFG["weekly_compilation"]["buffer_youtube_longform_supported"])
        self.assertFalse(compilation.eligible("JR-0076", {"JR-0076": {}}, {}, set(CFG["held_episodes"])))
        wf = (ROOT / ".github/workflows/jr-weekly-compilation.yml").read_text()
        self.assertIn("30 15 * * 0", wf); self.assertNotIn("BUFFER_API_KEY", wf)


if __name__ == "__main__":
    unittest.main()
