"""Steps of the daily post system. Every step reads state first, moves it along one
legal edge, records evidence, and stops at the first failure. External effects
(subprocess, scripture lookup, ffprobe, HTTP, Buffer) are injectable for tests.
Scripture is the public-domain translation named by config/content-os.json scripture_version
(KJV since 2026-11-05, DEC-JR-016), bundled at data/bible/ and read by scripts/daily/scripture.py;
there is no network scripture source (DEC-JR-007)."""
import datetime as dt, json, pathlib, re, subprocess, urllib.request
from zoneinfo import ZoneInfo
from . import states, scripture, safety, formats
from .redact import redact
from .store import Store, now_iso, ID_RE

IST = ZoneInfo("Asia/Kolkata")


# ---------------------------------------------------------------- helpers
def _jr_num(name):
    m = re.search(r"JR-(\d{4})", name)
    return int(m.group(1)) if m else None


def norm_text(s):
    s = (s or "").replace("\u201c", '"').replace("\u201d", '"').replace("\u2018", "'").replace("\u2019", "'")
    s = re.sub(r"\s+", " ", s).strip()
    # Whitespace before punctuation is never wording (older scraped sources rendered small-caps
    # LORD as "Lord ,"; JR-0048 Psalm 4:8, 2026-10-11).
    return re.sub(r"\s+([,.;:!?\u2019'\")])", r"\1", s)


def words(s):
    return set(re.findall(r"[a-z']+", (s or "").lower()))


def jaccard(a, b):
    A, B = words(a), words(b)
    return len(A & B) / len(A | B) if A and B else 0.0


def ref_of(ep):
    b = ep.get("bible") or {}
    return f"{b.get('book')} {b.get('chapter')}:{b.get('verse')}" if b.get("book") else None


def caption_text(pkg):
    tags = pkg["instagram_hashtags"]
    tags = " ".join(tags) if isinstance(tags, list) else tags
    cap = pkg["instagram_caption"].rstrip()
    # Audit 2026-10-16: 11 packages already ended with their hashtag block, so the post went out
    # with the same 5 tags twice (10 total). Instagram allows 5 per post; never append a second block.
    if re.search(r"(?:^|\s)#\w", cap.splitlines()[-1] if cap else ""):
        return cap
    return cap + "\n\n" + tags


BAIT_PATTERNS = (r"\bcomment (?:yes|amen|below)\b", r"\bin the comments\b", r"\btype (?:a|amen|yes)\b",
                 r"\bdouble tap\b", r"\btag (?:a|the|someone|your)\b")


RULES_V2_FROM = 64   # audit + deep-review rules (2026-10-16) apply to episodes written from JR-0064 on


def new_rules(eid):
    m = re.search(r"JR-(\d{4})", eid or "")
    return bool(m) and int(m.group(1)) >= RULES_V2_FROM


RULES_V3_FROM = 94  # 2026-11-05 (DEC-JR-017): R11 no question hook, R12 share line last, R13 first_comment.
# JR-0094 is the first episode not yet in Buffer when these rules landed (JR-0089..JR-0093 were
# already scheduled and are left exactly as they are).


def rules_v3(eid):
    m = re.search(r"JR-(\d{4})", eid or "")
    return bool(m) and int(m.group(1)) >= RULES_V3_FROM


def hook_line(ep):
    """The opener: the first person line (what the viewer reads in the first second)."""
    return next((l.get("text", "") for l in ep.get("lines") or [] if l.get("speaker") == "person" and l.get("text")), "")


def closing_line(ep):
    """Last spoken line of the script (the verse block has no text)."""
    spoken = [l for l in ep.get("lines") or [] if l.get("text") and l.get("speaker") not in ("bible_verse", "verse", "reference")]
    return spoken[-1] if spoken else {}


def v3_script_problems(ctx, ep):
    """R11 hook + R12 share line on the script itself (validator stage, before rendering)."""
    probs = []
    hook = hook_line(ep)
    if safety.hook_kind(hook) == "question":
        probs.append(f"R11 question hook {hook!r}: open with a confession or a statement (YouTube question hooks: median 382 views "
                     "vs 1,270 statement / 1,440 confession; one script feeds both platforms)")
    last = closing_line(ep)
    if last.get("speaker") != "engagement" or not safety.is_share_line(last.get("text")):
        probs.append(f"R12 last line must be a share line (speaker 'engagement', e.g. 'Send this to someone who needs it today.'), "
                     f"got {last.get('speaker')}: {last.get('text')!r}")
    else:
        src = formats.source_of(ep)
        recent = sorted([o for o in corpus(ctx, exclude=ep.get("id")) if not src or o.get("id") != src],
                        key=lambda e: _jr_num(e.get("id", "")) or 0)[-7:]
        mine = norm_text(last["text"]).lower()
        for o in recent:
            ol = closing_line(o)
            if ol.get("speaker") == "engagement" and norm_text(ol.get("text")).lower() == mine:
                probs.append(f"R12 share line repeats {o.get('id')} word for word; vary it")
    return probs


def held_for_review(st):
    return (st.get("review") or {}).get("status") == "HELD_FOR_REVIEW"


class Ctx:
    def __init__(self, root=".", rules=None, store=None, run_id="local", dry_run=False,
                 buffer=None, run=None, fetch_scripture=None, probe=None, http_get=None,
                 now=None, repo="selvin-paul-raj/jesus-replies-studio", log=print):
        self.root = pathlib.Path(root)
        self.rules = rules or json.loads((self.root / "config/publishing-rules.json").read_text())
        self.store = store or Store(root)
        self.run_id, self.dry_run, self.buffer, self.repo = run_id, dry_run, buffer, repo
        self.run = run or (lambda cmd, env=None: subprocess.run(cmd, capture_output=True, text=True, env=env))
        self.fetch_scripture = fetch_scripture or scripture.lookup
        self.probe, self.http_get = probe, http_get
        self.now = now or (lambda: dt.datetime.now(dt.timezone.utc))
        self.log = lambda m: log(redact(m))
        lp = self.root / "config/legacy-buffer-posts.json"
        self.legacy = {k: v for k, v in (json.loads(lp.read_text()) if lp.exists() else {}).items()
                       if ID_RE.match(k)}

    def ep_path(self, eid):
        return self.root / "generated" / f"{eid}.json"

    def pkg_path(self, eid):
        return self.root / "generated" / f"{eid}.package.json"


# ---------------------------------------------------------------- ids, slots, originality
def next_episode_id(ctx):
    nums = set()
    for d in ("generated", "Input"):
        for p in (ctx.root / d).glob("JR-*.json"):
            n = _jr_num(p.name)
            if n: nums.add(n)
    mp = ctx.root / "generated/release-manifest.json"
    for r in (json.loads(mp.read_text()) if mp.exists() else []):
        n = _jr_num(r.get("episode_id", ""))
        if n: nums.add(n)
    for r in ctx.store.load_manifest():
        nums.add(_jr_num(r["episode_id"]))
    if ctx.store.state_dir.exists():
        for p in ctx.store.state_dir.iterdir():
            n = _jr_num(p.name)
            if n: nums.add(n)
    nums |= {_jr_num(k) for k in ctx.legacy}
    return f"JR-{(max(nums) if nums else 0) + 1:04d}"


def allocate(ctx, date, slot):
    """Deterministic: one (date, slot) maps to exactly one episode id."""
    if slot not in ctx.rules["slots"]:
        raise ValueError(f"unknown slot {slot}")
    dt.date.fromisoformat(date)
    owner = ctx.store.slot_owner(date, slot)
    if owner:
        ctx.log(f"[allocate] {date} {slot} -> {owner} (existing)")
        return owner
    eid = next_episode_id(ctx)
    st = ctx.store.load(eid)
    st["slot"], st["target_date"] = slot, date
    ctx.store.save(st)
    ctx.store.upsert_manifest(st)
    ctx.log(f"[allocate] {date} {slot} -> {eid} (new)")
    return eid


def corpus(ctx, exclude=None):
    out = []
    for d in ("Input", "generated"):
        for p in sorted((ctx.root / d).glob("JR-*.json")):
            if ".package" in p.name or p.stem == exclude:
                continue
            try:
                out.append(json.loads(p.read_text()))
            except Exception:
                pass
    return out


def originality(ctx, ep):
    # DEC-JR-018: a subtitle version re-cuts its source, so it is not compared with that one episode
    src = formats.source_of(ep)
    issues, recent = [], [o for o in corpus(ctx, exclude=ep.get("id")) if not src or o.get("id") != src]
    last14 = sorted(recent, key=lambda e: _jr_num(e.get("id", "")) or 0)[-14:]
    hook = (ep.get("lines") or [{}])[0].get("text", "")
    for o in recent:
        oid = o.get("id", "?")
        if norm_text(o.get("title")).lower() == norm_text(ep.get("title")).lower() or jaccard(o.get("title"), ep.get("title")) >= 0.8:
            issues.append(f"title repeats {oid}")
        ohook = (o.get("lines") or [{}])[0].get("text", "")
        if ohook and jaccard(ohook, hook) >= 0.6:
            issues.append(f"hook repeats {oid}")
        if (o.get("topic"), o.get("character"), o.get("emotion")) == (ep.get("topic"), ep.get("character"), ep.get("emotion")) and ep.get("topic"):
            issues.append(f"topic+character+emotion repeats {oid}")
    for o in last14:
        if ref_of(o) and ref_of(o) == ref_of(ep):
            issues.append(f"scripture {ref_of(ep)} used in the last 14 by {o.get('id')}")
    return (not issues), sorted(set(issues))


def estimated_seconds(stdout):
    m = re.search(r"estimated_seconds=([0-9.]+)", stdout or "")
    return float(m.group(1)) if m else None


def words_budget(rules):
    """Rough word budget for the target length: default timing is 2.3 words/s plus ~3 s of
    end card and gaps (src/schema.ts TimingConfig). The validator's estimate is the real check."""
    return int((rules["duration"]["target_seconds"][1] - 6) * 2.3)


def brief(ctx, eid):
    """Authoring constraints for one slot. Writes no dialogue."""
    recent = sorted(corpus(ctx, exclude=eid), key=lambda e: _jr_num(e.get("id", "")) or 0)[-14:]
    b = {"episode_id": eid, "schema": f"generated/JR-0036.json (id,title,character,topic,emotion,bible{{book,chapter,verse,version={scripture.VERSION},text}},lines[{{speaker,text}}])",
         "package_schema": "generated/JR-0036.package.json",
         "honesty_line": safety.HONESTY_LINE,
         "writer_rules": safety.WRITER_RULES,
         "avoid_titles": [e.get("title") for e in recent], "avoid_scripture": [ref_of(e) for e in recent if ref_of(e)],
         "avoid_hooks": [(e.get("lines") or [{}])[0].get("text") for e in recent],
         "recent_topics": [e.get("topic") for e in recent], "recent_emotions": [e.get("emotion") for e in recent],
         "duration_target_seconds": ctx.rules["duration"]["target_seconds"],
         "duration_ceiling_seconds": ctx.rules["duration"]["ceiling_seconds"],
         "duration_rule": (f"aim for {ctx.rules['duration']['target_seconds'][0]}-{ctx.rules['duration']['target_seconds'][1]} s "
                           f"(about {words_budget(ctx.rules)} spoken words across all lines incl. the verse); the validator "
                           f"estimates the length before rendering and rejects anything over {ctx.rules['duration']['ceiling_seconds']} s"),
         "scripture_rule": (f"{scripture.LABEL} ({scripture.VERSION}, public domain), version=\"{scripture.VERSION}\", text copied "
                            f"verbatim, character for character, from {scripture.PATH.relative_to(scripture.ROOT)} (get it with "
                            "`python3 scripts/daily/jr_daily.py verse \"Psalm 23:1\"`); never paraphrase or modernise the "
                            f"wording; label it ({scripture.VERSION}) in captions and descriptions; never NIV/ESV/NLT/BSB or any "
                            "other translation; the verse must fit its context (review rule R10); unverifiable -> BLOCKED"),
         "hook_rule": ("R11: line 1 is a confession or a statement, never a question (no '?', no 'why/how/what/is/does...' "
                       "opener). YouTube median views by hook: question 382 (n=41), statement 1,270 (n=11), confession 1,440 "
                       "(n=24); Instagram is neutral. One script feeds both platforms, so the rule holds for both. The validator fails a question opener."),
         "allowed_hook_types": list(safety.HOOK_TYPES_ALLOWED),
         "script_template": ["person: hook (confession or statement; concrete moment + what they hid, <=18 words)",
                             "person: one concrete detail", "jesus: names the hidden thing", "person: pushback",
                             "jesus: the turn", "bible_verse (KJV verbatim, R10 context)", "jesus: payoff, echoes a word from the hook",
                             "engagement: SHARE LINE (last line, R12): who needs it, fresh wording each episode, no bait"],
         "share_line_rule": ("R12: the script's last line (speaker 'engagement') is a share line in the channel voice that names "
                             "who needs it, worded differently from recent episodes; the caption carries a share line too. Examples, "
                             f"never copied verbatim every time: {list(safety.SHARE_LINE_EXAMPLES)}. Never 'type amen', 'comment', 'tag'."),
         "first_comment_rule": ("R13: package field first_comment = one easy, warm question tied to this episode, <=150 chars, "
                                "no links/hashtags/bait, e.g. 'Has someone in your family ever said this to you?'. Buffer posts it "
                                "as the Instagram first comment; the comment run posts and pins it on YouTube."),
         "caption_template": ["1 the hurt + one searchable phrase", "2 the story in a line, Jesus's reply, the verse with (KJV) and reference",
                              "3 one small, easy question", "4 SHARE LINE (R12, may match the script's last line)",
                              "5 series line", "6 honesty line (exact words, last)", "hashtags: exactly 5, in instagram_hashtags only"],
         "package_fields": ["instagram_caption", "instagram_hashtags", "youtube_title", "youtube_description", "thumbnail_text", "first_comment"]}
    lane = series_assignment(ctx, eid)
    if lane:                      # weekly series lane (e.g. family-pressure, DEC-JR-017)
        b["series"] = lane
    lp = ctx.root / "content-os/learnings.json"
    if lp.exists():               # feedback loop: analytics -> learnings -> every new brief
        L = json.loads(lp.read_text())
        b["strategy"] = {"source": "content-os/learnings.json + content-os/STRATEGY.md", "as_of": L.get("as_of"),
                         **(L.get("authoring_guidance") or {})}
    rp = ctx.root / "content-os/review-rules.json"
    if rp.exists():               # bi-weekly growth review: hand-decided rules + active experiments (DECISIONS.md)
        R = json.loads(rp.read_text())
        b["review_rules"] = {"source": "content-os/review-rules.json", "as_of": R.get("as_of"),
                             "rules": R.get("rules", []), "experiments": R.get("experiments", [])}
    p = ctx.root / "generated/briefs" / f"{eid}.brief.json"
    if not ctx.dry_run:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(b, indent=2, ensure_ascii=False) + "\n")
    return b


def series_assignment(ctx, eid):
    """The series-lane backlog entry reserved for this episode id, if any (content-os/series/*.json)."""
    for p in sorted((ctx.root / "content-os/series").glob("*.json")):
        try:
            S = json.loads(p.read_text())
        except Exception:
            continue
        for item in S.get("backlog") or []:
            if item.get("episode_id") == eid:
                return {"series": S.get("series"), "source": str(p.relative_to(ctx.root)), **item}
    for p in sorted((ctx.root / "content-os/weeks").glob("*/weekly-content-plan.json")):   # id reserved by the planner
        try:
            plan = json.loads(p.read_text())
        except Exception:
            continue
        for sl in plan.get("slots") or []:
            if sl.get("episode_id") == eid and sl.get("series"):
                return {"series": sl["series"], "source": str(p.relative_to(ctx.root)), "date": sl.get("date"),
                        "slot": sl.get("slot"), "idea": sl.get("theme"), "verse": sl.get("bible_reference"),
                        "hook_strategy": sl.get("hook_strategy")}
    return None


# ---------------------------------------------------------------- pre-Buffer steps
def step_generated(ctx, st):
    eid = st["episode_id"]
    p = ctx.ep_path(eid)
    if not (p.is_file() and p.stat().st_size > 0):
        st["generation"] = "BLOCKED"
        return ctx.store.transition(st, "BLOCKED", f"generated/{eid}.json not authored. Dialogue authoring "
                                    "needs a model call and no credential is wired into this workflow.", ctx.run_id)
    st["generation"] = "PASS"
    return ctx.store.transition(st, "GENERATED", f"generated/{eid}.json present ({p.stat().st_size} B)", ctx.run_id)


def step_validated(ctx, st):
    eid = st["episode_id"]
    ep = json.loads(ctx.ep_path(eid).read_text())
    probs = []
    if ep.get("id") != eid: probs.append(f"id {ep.get('id')} != {eid}")
    if not ep.get("lines"): probs.append("no lines")
    for f in ("title", "character", "topic", "emotion"):
        if not ep.get(f): probs.append(f"missing {f}")
    b = ep.get("bible") or {}
    if b.get("version") != scripture.VERSION or not b.get("text"): probs.append(f"scripture missing or not {scripture.VERSION}")
    r = ctx.run(["npx", "tsx", "scripts/daily/validate-episode.ts", str(ctx.ep_path(eid))])
    if r.returncode != 0: probs.append(f"schema validator: {(r.stdout or r.stderr).strip()[-300:]}")
    est = estimated_seconds(r.stdout)
    d = ctx.rules["duration"]
    if est is not None:
        st["render_facts"]["estimated_seconds"] = est
        if est > d["ceiling_seconds"]:
            probs.append(f"estimated length {est:.1f}s is over the {d['ceiling_seconds']}s ceiling "
                         f"(target {d['target_seconds'][0]}-{d['target_seconds'][1]}s); cut lines before rendering")
    ok, issues = originality(ctx, ep)
    if not ok: probs += [f"originality: {i}" for i in issues]
    if rules_v3(eid):
        probs += v3_script_problems(ctx, ep)
    probs += formats.script_problems(ep, ctx.root)      # DEC-JR-018 growth formats
    if probs:
        st["validation"] = "FAIL"
        return ctx.store.transition(st, "VALIDATION_FAILED", "; ".join(probs), ctx.run_id)
    ref = ref_of(ep)
    try:
        fetched = ctx.fetch_scripture(ref) if ctx.fetch_scripture else None
    except Exception as e:
        fetched = None
        ctx.log(f"[scripture] fetch error {type(e).__name__}")
    if not fetched:
        st["validation"] = "BLOCKED"
        return ctx.store.transition(st, "BLOCKED", f"scripture {ref} not found in the bundled {scripture.VERSION} text; not rendering", ctx.run_id)
    if norm_text(fetched) != norm_text(b["text"]):          # exact wording and case (LORD), fail closed
        st["validation"] = "FAIL"
        return ctx.store.transition(st, "VALIDATION_FAILED", f"scripture {ref} text does not match {scripture.VERSION} source", ctx.run_id)
    st["validation"] = "PASS"
    return ctx.store.transition(st, "VALIDATED", f"schema PASS, originality PASS, {scripture.VERSION} {ref} verbatim match", ctx.run_id)


def video_path(ctx, eid):
    return ctx.root / "output/videos" / f"{eid}.mp4"


def step_rendered(ctx, st):
    eid = st["episode_id"]
    v = video_path(ctx, eid)
    cmd = ["npm", "run", "jr", "--", "render", f"generated/{eid}.json", "--out-dir", "output"]
    if v.is_file() and v.stat().st_size > 0:
        how, code = "REUSED existing render", 0
    else:
        import os
        r = ctx.run(cmd, env={**os.environ, "JR_RENDER_CONCURRENCY": "2"})
        how, code = "RENDERED", r.returncode
        if code != 0 or not (v.is_file() and v.stat().st_size > 0):
            st["render"] = "FAIL"
            return ctx.store.transition(st, "RENDER_FAILED", f"cmd={' '.join(cmd)} exit={code} {(r.stderr or '')[-200:]}", ctx.run_id)
    st["render"] = "PASS"
    st["render_facts"].update({"command": " ".join(cmd), "exit": code, "path": str(v.relative_to(ctx.root)),
                               "size_bytes": v.stat().st_size, "how": how})
    return ctx.store.transition(st, "RENDERED", f"{how} {v.name} {v.stat().st_size} B", ctx.run_id)


def ffprobe(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-print_format", "json", "-show_format", "-show_streams", str(path)],
                       capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(r.stderr[-200:])
    return json.loads(r.stdout)


def step_render_qa(ctx, st):
    eid, d = st["episode_id"], ctx.rules["duration"]
    v = video_path(ctx, eid)
    probs, warn = [], []
    if not (v.is_file() and v.stat().st_size > 0):
        return ctx.store.transition(st, "RENDER_QA_FAILED", f"{v.name} missing or empty", ctx.run_id)
    with v.open("rb") as fh:
        head = fh.read(32)
    if b"ftyp" not in head:
        probs.append("no MP4 ftyp signature")
    try:
        info = (ctx.probe or ffprobe)(v)
    except Exception as e:
        st["render_qa"] = "FAIL"
        return ctx.store.transition(st, "RENDER_QA_FAILED", f"ffprobe could not read the file: {e}", ctx.run_id)
    fmt = info.get("format") or {}
    vs = [s for s in info.get("streams", []) if s.get("codec_type") == "video"]
    au = [s for s in info.get("streams", []) if s.get("codec_type") == "audio"]
    dur = float(fmt.get("duration") or 0)
    if "mp4" not in (fmt.get("format_name") or ""): probs.append(f"container {fmt.get('format_name')}")
    if not vs: probs.append("no video stream")
    if not au: probs.append("no audio stream")
    if vs:
        w, h = vs[0].get("width"), vs[0].get("height")
        if (w, h) != (ctx.rules["video"]["width"], ctx.rules["video"]["height"]): probs.append(f"resolution {w}x{h}")
        if not (h or 0) > (w or 0): probs.append("not portrait")
    if not (d["min_seconds"] <= dur <= d["ceiling_seconds"]):
        probs.append(f"duration {dur:.2f}s outside {d['min_seconds']}-{d['ceiling_seconds']}s"
                     + ("" if d.get("auto_trim") else " (auto-trim disabled by policy; dialogue is never trimmed automatically)"))
    elif dur > d["target_seconds"][1]:
        warn.append(f"duration {dur:.2f}s above target {d['target_seconds']} but under ceiling")
    if v.stem != eid: probs.append("file name does not match episode id")
    st["render_facts"].update({"duration_s": round(dur, 2), "video_codec": vs[0].get("codec_name") if vs else None,
                               "audio_codec": au[0].get("codec_name") if au else None,
                               "resolution": f"{vs[0].get('width')}x{vs[0].get('height')}" if vs else None,
                               "warnings": warn})
    if probs:
        st["render_qa"] = "FAIL"
        return ctx.store.transition(st, "RENDER_QA_FAILED", "; ".join(probs), ctx.run_id)
    st["render_qa"] = "PASS"
    return ctx.store.transition(st, "RENDER_QA_PASSED", f"{dur:.2f}s {st['render_facts']['resolution']} "
                                f"{st['render_facts']['video_codec']}/{st['render_facts']['audio_codec']} {'; '.join(warn)}", ctx.run_id)


def step_packaged(ctx, st):
    eid = st["episode_id"]
    if not ctx.pkg_path(eid).is_file():
        st["package"] = "FAIL"
        return ctx.store.transition(st, "PACKAGE_FAILED", f"generated/{eid}.package.json missing", ctx.run_id)
    st["package"] = "PASS"
    return ctx.store.transition(st, "PACKAGED", f"{eid}.package.json present", ctx.run_id)


def step_package_qa(ctx, st):
    eid, P = st["episode_id"], ctx.rules["package"]
    try:
        pk = json.loads(ctx.pkg_path(eid).read_text())
    except Exception as e:
        return ctx.store.transition(st, "PACKAGE_QA_FAILED", f"package unreadable: {e}", ctx.run_id)
    ep = json.loads(ctx.ep_path(eid).read_text())
    probs = [f"missing {f}" for f in ("instagram_caption", "instagram_hashtags", "youtube_title",
                                      "youtube_description", "thumbnail_text") if not pk.get(f)]
    if not probs:
        tags = pk["instagram_hashtags"] if isinstance(pk["instagram_hashtags"], list) else pk["instagram_hashtags"].split()
        if len(caption_text(pk)) > P["caption_max"]: probs.append("caption too long")
        if len(tags) != P["hashtag_count"]: probs.append(f"hashtag count {len(tags)}")
        v2 = new_rules(eid)
        if v2 and re.search(r"(?:^|\s)#\w", pk["instagram_caption"]): probs.append("hashtags inside caption (they are added once from instagram_hashtags)")
        if v2 and any(re.search(b, pk["instagram_caption"], re.I) for b in BAIT_PATTERNS):
            probs.append("engagement bait in caption (Instagram downranks 'comment X / tag / type amen'); ask a real question instead")
        if len(pk["youtube_title"]) > P["youtube_title_max"]: probs.append("youtube title too long")
        if len(pk["youtube_description"]) > P["youtube_description_max"]: probs.append("youtube description too long")
        book = (ep.get("bible") or {}).get("book", "")
        hay = (pk["instagram_caption"] + pk["youtube_description"]).lower()
        names = {book.lower(), book.lower()[:-1] if book.lower() == "psalms" else book.lower()}
        if book and not any(n in hay for n in names):
            probs.append(f"Bible reference {book} not in caption or description")
        wrong = sorted({t for t in re.findall(r"\b(NIV|BSB|ESV|NLT|NKJV|NASB|CSB|MSG)\b", json.dumps(pk))} - {scripture.VERSION})
        if v2 and wrong: probs.append(f"package labels another translation {wrong}; Scripture is {scripture.VERSION} only")
        if rules_v3(eid):
            probs += safety.first_comment_problems(pk.get("first_comment"))
            if not safety.share_line_of(pk["instagram_caption"]):
                probs.append("R12 share line missing from instagram_caption (e.g. 'Send this to someone who needs it today.')")
            if any(re.search(b, pk.get("first_comment") or "", re.I) for b in BAIT_PATTERNS):
                probs.append("engagement bait in first_comment")
        probs += formats.package_problems(ep, pk, ctx.root)     # DEC-JR-018
        others = set(re.findall(r"JR-\d{4}", json.dumps(pk))) - {eid}
        if others: probs.append(f"references other episodes {sorted(others)}")
        crisis, found = safety.crisis_check(ep, pk)
        lint = {**safety.jesus_lint(ep), **safety.faith_framing(ep, pk)}
        sp = safety.package_problems(pk, crisis=crisis)
        if not v2:      # queued legacy packages are already in Buffer: only the crisis line is enforced
            sp = [p for p in sp if p.startswith("crisis line")]
        probs += sp
        if (crisis or lint) and (st.get("review") or {}).get("status") != "RELEASED":
            st["review"] = {"status": "HELD_FOR_REVIEW", "at": now_iso(), "crisis": found, "jesus_lines": lint,
                            "why": "sensitive theme or a Jesus line that may promise an outcome / advise / add doctrine; "
                                   "never auto-published (DEC-JR-007). Release: jr_daily.py release-review"}
    thumbs = sorted((ctx.root / "output/thumbnails").glob(f"{eid}-thumb.png")) or sorted((ctx.root / "output/thumbnails").glob(f"{eid}.png"))
    if not thumbs: probs.append("thumbnail image not rendered")
    if probs:
        st["package_qa"] = "FAIL"
        return ctx.store.transition(st, "PACKAGE_QA_FAILED", "; ".join(probs), ctx.run_id)
    st["package_qa"] = "PASS"
    held = " HELD_FOR_REVIEW (crisis gate)" if held_for_review(st) else ""
    return ctx.store.transition(st, "PACKAGE_QA_PASSED", f"caption {len(caption_text(pk))} chars, 5 hashtags, "
                                f"title {len(pk['youtube_title'])}, thumbnail {thumbs[0].name}, honesty line OK{held}", ctx.run_id)


def http_range(url):
    req = urllib.request.Request(url, headers={"User-Agent": "jr-url-verify", "Range": "bytes=0-63"})
    with urllib.request.urlopen(req, timeout=60) as r:
        total = (r.headers.get("Content-Range") or "").split("/")[-1]
        return r.status, r.read(64), int(total) if total.isdigit() else int(r.headers.get("Content-Length") or 0)


def manifest_row(ctx, eid):
    mp = ctx.root / "generated/release-manifest.json"
    rows = [r for r in (json.loads(mp.read_text()) if mp.exists() else []) if r.get("episode_id") == eid and r.get("qa_status") == "PASS"]
    return rows[-1] if rows else None


def verify_asset(ctx, row):
    try:
        status, head, total = (ctx.http_get or http_range)(row["public_url"])
    except Exception as e:
        return False, f"unreachable {type(e).__name__}"
    ok = status in (200, 206) and b"ftyp" in head[:32] and total == row["size_bytes"] and row["public_url"].startswith("https://")
    return ok, f"http={status} ftyp={b'ftyp' in head[:32]} bytes={total}/{row['size_bytes']}"


def step_hosted(ctx, st):
    import os
    eid = st["episode_id"]
    row = manifest_row(ctx, eid)
    if row is None:
        tag = ctx.rules["hosting"]["release_tag_pattern"].format(episode_id=eid)
        if ctx.dry_run:
            ctx.log(f"[dry-run] would upload {eid}.mp4 to release {tag} and verify it anonymously")
            return st
        r = ctx.run(["python3", "scripts/release_episodes.py", eid], env={**os.environ, "TAG": tag, "REPO": ctx.repo})
        if r.returncode != 0:
            st["asset_hosting"] = "FAIL"
            return ctx.store.transition(st, "HOSTING_FAILED", f"release upload exit {r.returncode} {(r.stdout or '')[-200:]}", ctx.run_id)
        row = manifest_row(ctx, eid)
        if row is None:
            return ctx.store.transition(st, "HOSTING_FAILED", "upload reported success but no PASS manifest row", ctx.run_id)
    ok, detail = verify_asset(ctx, row)
    if not ok:
        st["asset_hosting"] = "FAIL"
        return ctx.store.transition(st, "HOSTING_FAILED", f"independent URL check failed: {detail}", ctx.run_id)
    st["asset_hosting"], st["asset_url"] = "VERIFIED", row["public_url"]
    return ctx.store.transition(st, "ASSET_HOSTED", f"{row['public_url']} {detail}", ctx.run_id)


# ---------------------------------------------------------------- Buffer steps
def check_draft(ctx, st, post, expect_text):
    probs = []
    if post.get("status") != "draft": probs.append(f"status {post.get('status')}")
    if norm_text(post.get("text")) != norm_text(expect_text): probs.append("caption/hashtags differ")
    if post.get("_asset_source") != st["asset_url"]: probs.append(f"asset {post.get('_asset_source')}")
    dur = st["render_facts"].get("duration_s")
    if dur and post.get("_duration_ms") and abs(post["_duration_ms"] / 1000 - dur) > 1: probs.append(f"durationMs {post['_duration_ms']}")
    if post.get("channelService") and post["channelService"] != ctx.rules["buffer"]["channel"]: probs.append(f"channel {post['channelService']}")
    return probs


def step_buffer_draft(ctx, st):
    eid = st["episode_id"]
    B = st["buffer"]
    if eid in ctx.legacy:
        ctx.log(f"[buffer] {eid} is a legacy post {ctx.legacy[eid]}; the daily system never mutates it")
        return st
    if B.get("pending_mutation"):
        return ctx.store.transition(st, "BLOCKED", f"an earlier {B['pending_mutation']['kind']} has an UNRESOLVED outcome; "
                                    "reconcile in Buffer before anything else", ctx.run_id)
    pkg = json.loads(ctx.pkg_path(eid).read_text())
    text = caption_text(pkg)
    fc_kw = {"first_comment": pkg["first_comment"]} if pkg.get("first_comment") else {}
    if B.get("post_id"):
        if ctx.buffer is None:
            ctx.log(f"[buffer] {eid} has post {B['post_id']}; not readable in this run, no create")
            return st
        post, d = ctx.buffer.read(B["post_id"])
        if not post:
            return ctx.store.transition(st, "BLOCKED", f"recorded post {B['post_id']} unreadable ({d}); never re-creating", ctx.run_id)
        probs = check_draft(ctx, st, post, text)
        B.update({"status": post.get("status"), "due_at": post.get("dueAt")})
        if probs:
            return ctx.store.transition(st, "BUFFER_FAILED", f"existing post {B['post_id']} read back wrong: {'; '.join(probs)}", ctx.run_id)
        ctx.store.transition(st, "BUFFER_DRAFT", f"reconciled existing draft {B['post_id']} (no create)", ctx.run_id)
        return to_waiting(ctx, st)
    if ctx.dry_run:
        ctx.log(f"[dry-run] would create ONE Instagram draft for {eid}: asset={st['asset_url']} "
                f"caption={len(text)} chars dueAt={ctx.rules['buffer']['draft_due_at']} saveToDraft=true")
        return st
    attempts = B.setdefault("create_attempts", 0)
    if attempts >= 2:
        return ctx.store.transition(st, "BLOCKED", "draft creation already failed twice; human review needed", ctx.run_id)
    B["create_attempts"] = attempts + 1
    B["pending_mutation"] = {"kind": "createPost", "at": now_iso(), "run": ctx.run_id}
    ctx.store.save(st)
    out = ctx.buffer.create_draft(text, st["asset_url"], ctx.rules["buffer"]["draft_due_at"], **fc_kw)
    ctx.log(f"[buffer] createPost {eid} -> {out.kind} {out.detail}")
    if out.kind == "REJECTED":
        B["pending_mutation"] = None
        return ctx.store.transition(st, "BUFFER_FAILED", f"createPost rejected, no object expected: {out.detail}", ctx.run_id)
    if out.kind in ("NO_POST_ID", "UNKNOWN"):
        return ctx.store.transition(st, "BLOCKED", f"createPost outcome {out.kind}: {out.detail}. Not retrying; "
                                    "the channel cannot be listed by this run to rule out an orphan.", ctx.run_id)
    B["post_id"], B["pending_mutation"] = out.post["id"], None
    ctx.store.save(st)
    post, d = ctx.buffer.read(B["post_id"])
    if not post:
        return ctx.store.transition(st, "BUFFER_FAILED", f"created {B['post_id']} but read-back failed ({d}); post id kept, never re-created", ctx.run_id)
    probs = check_draft(ctx, st, post, text)
    B.update({"status": post.get("status"), "due_at": post.get("dueAt"), "sent_at": post.get("sentAt")})
    if probs:
        return ctx.store.transition(st, "BUFFER_FAILED", f"draft {B['post_id']} read back wrong: {'; '.join(probs)}", ctx.run_id)
    ctx.store.transition(st, "BUFFER_DRAFT", f"draft {B['post_id']} read back: status draft, asset, caption, duration, channel OK", ctx.run_id)
    return to_waiting(ctx, st)


def to_waiting(ctx, st):
    st["approval"]["status"] = "WAITING_FOR_USER"
    st = ctx.store.transition(st, "WAITING_FOR_USER", "approval required: episode, date, time, timezone", ctx.run_id)
    return auto_approve(ctx, st)


def standing_authorization(ctx):
    """Selvin's standing autonomy authorization (config/content-os.json autonomy.full_autonomy)."""
    p = ctx.root / "config/content-os.json"
    try:
        return (json.loads(p.read_text()).get("autonomy") or {}).get("full_autonomy")
    except Exception:
        return None


def auto_approve(ctx, st):
    """Human gate removed 2026-10-11 (Selvin: 'complete autonomous running system').
    A draft that passed every automated gate (verse, render QA, package QA, hosting,
    draft read-back) is APPROVED under the standing authorization; the content OS
    distributor then schedules it into its reserved slot on Instagram and YouTube."""
    if ctx.rules.get("require_human_approval", True) or st["state"] != "WAITING_FOR_USER":
        return st
    if held_for_review(st):
        ctx.log(f"[approve] {st['episode_id']} is HELD_FOR_REVIEW (crisis gate); never auto-approved")
        return st
    auth = standing_authorization(ctx)
    if not auth:
        ctx.log(f"[approve] {st['episode_id']} no standing authorization recorded; stays WAITING_FOR_USER")
        return st
    st["approval"].update({"status": "APPROVED", "approved_at": now_iso(), "approved_by": "standing authorization",
                           "evidence": redact(f"{auth['given']}: {auth['quote']}")[:300]})
    return ctx.store.transition(st, "APPROVED", f"auto-approved after all QA gates under standing authorization "
                                f"{auth['given']}; slot time comes from the weekly plan", ctx.run_id)


def advance(ctx, eid):
    """Runs from the episode's CURRENT state up to WAITING_FOR_USER and stops."""
    if not ctx.store.acquire(eid, ctx.run_id, ctx.rules["lock_ttl_minutes"]):
        ctx.log(f"[lock] {eid} is locked by another run; STOP")
        return None
    try:
        st = ctx.store.load(eid)
        st = _reopen_generation_block(ctx, st)
        chain = [(states.NEW, step_generated), ("GENERATED", step_validated), ("VALIDATED", step_rendered),
                 ("RENDERED", step_render_qa), ("RENDER_QA_PASSED", step_packaged), ("PACKAGED", step_package_qa),
                 ("PACKAGE_QA_PASSED", step_hosted), ("ASSET_HOSTED", step_buffer_draft)]
        for want, fn in chain:
            if held_for_review(st) and want == "PACKAGE_QA_PASSED":
                ctx.log(f"[review] {eid} HELD_FOR_REVIEW {st['review'].get('crisis') or st['review'].get('jesus_lines')}; "
                        "not hosted, not sent to Buffer; a READY spare fills its slot")
                break
            if st["state"] == want:
                before = st["state"]
                st = fn(ctx, st)
                ctx.store.upsert_manifest(st, _title(ctx, eid))
                if st["state"] == before:      # dry-run or read-only stop
                    break
            if st["state"] in states.FAILURES or st["state"] in ("WAITING_FOR_USER", "APPROVED"):
                break
        if st["state"] == "WAITING_FOR_USER":
            st = auto_approve(ctx, st)
            ctx.store.upsert_manifest(st, _title(ctx, eid))
        return st
    finally:
        ctx.store.release(eid, ctx.run_id)


def _reopen_generation_block(ctx, st):
    """An episode BLOCKED only because it was not yet authored re-enters at NEW once the
    file exists. Never applies after any later stage or any Buffer activity."""
    B = st["buffer"]
    if (st["state"] == "BLOCKED" and st["generation"] == "BLOCKED" and st["history"]
            and st["history"][-1]["from"] == states.NEW and not B.get("post_id")
            and not B.get("pending_mutation") and ctx.ep_path(st["episode_id"]).is_file()):
        ts = now_iso()
        st["history"].append({"at": ts, "from": "BLOCKED", "to": states.NEW, "run": ctx.run_id,
                              "evidence": f"reopen: generated/{st['episode_id']}.json now authored"})
        st["state"], st["generation"], st["updated_at"] = states.NEW, "NOT_STARTED", ts
        ctx.store.save(st)
    return st


def _title(ctx, eid):
    p = ctx.ep_path(eid)
    return json.loads(p.read_text()).get("title") if p.exists() else None


# ---------------------------------------------------------------- approval, schedule, verify
def approve(ctx, eid, date, time, tz, approved_by, evidence, allow_off_slot=False):
    st = ctx.store.load(eid)
    if eid in ctx.legacy:
        raise ValueError(f"{eid} is a legacy post managed outside this system")
    if st["state"] != "WAITING_FOR_USER":
        raise ValueError(f"{eid} is {st['state']}, not WAITING_FOR_USER")
    if tz not in ("Asia/Kolkata", "IST"):
        raise ValueError("timezone must be Asia/Kolkata (IST)")
    if not re.fullmatch(r"\d{2}:\d{2}", time or ""):
        raise ValueError("time must be HH:MM")
    if not evidence or not approved_by:
        raise ValueError("approval needs who approved and the exact approval words")
    local = dt.datetime.fromisoformat(f"{date}T{time}").replace(tzinfo=IST)
    if time not in ctx.rules["slots"].values() and not allow_off_slot:
        raise ValueError(f"{time} is not a configured slot {ctx.rules['slots']}")
    if local - ctx.now() < dt.timedelta(minutes=10):
        raise ValueError(f"{local.isoformat()} is in the past or under 10 minutes away")
    due = local.astimezone(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    for r in ctx.store.load_manifest():
        o = ctx.store.load(r["episode_id"]) if r["episode_id"] != eid else None
        if o and o["approval"].get("due_at") == due and o["state"] in ("APPROVED", "SCHEDULED", "PUBLISHED", "PUBLISHED_VERIFIED"):
            raise ValueError(f"{due} is already taken by {o['episode_id']}")
    st["approval"].update({"status": "APPROVED", "approved_at": now_iso(), "approved_by": approved_by,
                           "slot_local": local.isoformat(), "due_at": due, "evidence": redact(evidence)[:300]})
    st = ctx.store.transition(st, "APPROVED", f"{approved_by}: {evidence} -> dueAt {due}", ctx.run_id)
    ctx.store.upsert_manifest(st)
    return st


def schedule(ctx, eid):
    if not ctx.store.acquire(eid, ctx.run_id, ctx.rules["lock_ttl_minutes"]):
        ctx.log(f"[lock] {eid} is locked by another run; STOP")
        return None
    try:
        st = ctx.store.load(eid)
        B, A = st["buffer"], st["approval"]
        if eid in ctx.legacy:
            raise ValueError(f"{eid} is a legacy post managed outside this system")
        if st["state"] != "APPROVED" or A.get("status") != "APPROVED" or not A.get("due_at"):
            raise ValueError(f"{eid} is {st['state']}; scheduling requires an explicit APPROVED record")
        if B.get("pending_mutation"):
            return ctx.store.transition(st, "BLOCKED", "an earlier mutation is UNRESOLVED", ctx.run_id)
        due = A["due_at"]
        if dt.datetime.fromisoformat(due.replace("Z", "+00:00")) <= ctx.now():
            return ctx.store.transition(st, "BLOCKED", f"approved time {due} has passed; needs a new approval", ctx.run_id)
        pkg = json.loads(ctx.pkg_path(eid).read_text())
        text = caption_text(pkg)
        fc_kw = {"first_comment": pkg["first_comment"]} if pkg.get("first_comment") else {}
        post, d = ctx.buffer.read(B["post_id"]) if ctx.buffer else (None, "no Buffer access")
        if not post:
            return ctx.store.transition(st, "BLOCKED", f"pre-read of {B['post_id']} failed ({d})", ctx.run_id)
        if _is_scheduled(post, due):
            ctx.log(f"[schedule] {eid} already scheduled at {due}; reconciling, no mutation")
            return _mark_scheduled(ctx, st, post, "reconciled, already scheduled")
        probs = check_draft(ctx, st, post, text)
        if probs:
            return ctx.store.transition(st, "BLOCKED", f"pre-read does not match the approved draft: {'; '.join(probs)}", ctx.run_id)
        if ctx.dry_run:
            ctx.log(f"[dry-run] would editPost {B['post_id']} dueAt={due} saveToDraft=false (text/asset/metadata unchanged)")
            return st
        attempts = B.setdefault("schedule_attempts", 0)
        if attempts >= 2:
            return ctx.store.transition(st, "BLOCKED", "scheduling failed twice; human review needed", ctx.run_id)
        B["schedule_attempts"] = attempts + 1
        B["pending_mutation"] = {"kind": "editPost", "at": now_iso(), "run": ctx.run_id}
        ctx.store.save(st)
        out = ctx.buffer.schedule(B["post_id"], text, st["asset_url"], due, **fc_kw)
        ctx.log(f"[buffer] editPost {eid} -> {out.kind} {out.detail}")
        post, d = ctx.buffer.read(B["post_id"])
        if post and _is_scheduled(post, due) and not check_after(ctx, st, post, text):
            B["pending_mutation"] = None
            return _mark_scheduled(ctx, st, post, f"mutation {out.kind}, independent read-back confirms")
        if out.kind == "REJECTED" and post and post.get("status") == "draft":
            B["pending_mutation"] = None
            return ctx.store.transition(st, "SCHEDULING_FAILED", f"editPost rejected, post still a draft: {out.detail}", ctx.run_id)
        return ctx.store.transition(st, "BLOCKED", f"editPost {out.kind}; read-back {d} status={post and post.get('status')} "
                                    f"dueAt={post and post.get('dueAt')}. Not retrying.", ctx.run_id)
    finally:
        ctx.store.release(eid, ctx.run_id)


def _is_scheduled(post, due):
    return post.get("status") == "scheduled" and (post.get("dueAt") or "").replace(".000Z", "Z") == due


def check_after(ctx, st, post, text):
    probs = []
    if norm_text(post.get("text")) != norm_text(text): probs.append("caption changed")
    if post.get("_asset_source") != st["asset_url"]: probs.append("asset changed")
    if post.get("sentAt"): probs.append("already sent")
    return probs


def _mark_scheduled(ctx, st, post, how):
    st["buffer"].update({"status": post.get("status"), "due_at": post.get("dueAt"), "sent_at": post.get("sentAt")})
    st = ctx.store.transition(st, "SCHEDULED", f"{how}: status scheduled dueAt {post.get('dueAt')} "
                              f"sentAt {post.get('sentAt') if post.get('_has_sent_at_field') else 'NOT_READABLE'}", ctx.run_id)
    ctx.store.upsert_manifest(st)
    return st


def verify_published(ctx, eid):
    st = ctx.store.load(eid)
    if st["state"] not in ("SCHEDULED", "PUBLISHED"):
        ctx.log(f"[verify] {eid} is {st['state']}; nothing to verify")
        return st
    B = st["buffer"]
    due = dt.datetime.fromisoformat(B["due_at"].replace("Z", "+00:00"))
    now = ctx.now()
    if now < due:
        ctx.log(f"[verify] {eid} NOT_DUE until {B['due_at']}; an empty sentAt is expected")
        return st
    post, d = ctx.buffer.read(B["post_id"])
    if not post:
        ctx.log(f"[verify] {eid} UNRESOLVED read ({d}); state unchanged")
        return st
    B.update({"status": post.get("status"), "sent_at": post.get("sentAt")})
    sent = post.get("status") == "sent" and (post.get("sentAt") or not post.get("_has_sent_at_field"))
    grace = dt.timedelta(minutes=ctx.rules["publish_grace_minutes"])
    if sent:
        if st["state"] == "SCHEDULED":
            st = ctx.store.transition(st, "PUBLISHED", f"Buffer status sent, sentAt {post.get('sentAt')}", ctx.run_id)
        ok = post.get("id") == B["post_id"] and post.get("_asset_source") == st["asset_url"] and post.get("sentAt")
        if ok:
            st["verification"] = {"status": "PUBLISHED_VERIFIED", "verified_at": now_iso()}
            st = ctx.store.transition(st, "PUBLISHED_VERIFIED", f"post {post['id']} sent {post['sentAt']} asset matches", ctx.run_id)
        else:
            st["verification"] = {"status": "UNVERIFIED", "verified_at": None}
            ctx.store.save(st)
    elif post.get("status") == "error" or now > due + grace:
        st["verification"] = {"status": "FAILED", "verified_at": now_iso()}
        st = ctx.store.transition(st, "PUBLISH_VERIFICATION_FAILED", f"due {B['due_at']} passed (+{grace}); status "
                                  f"{post.get('status')} sentAt {post.get('sentAt')}", ctx.run_id)
    else:
        ctx.log(f"[verify] {eid} due passed, inside grace window; status {post.get('status')}")
        ctx.store.save(st)
    ctx.store.upsert_manifest(st)
    return st


def report(st):
    rows = [("GENERATED", st["generation"]), ("VALIDATED", st["validation"]), ("RENDERED", st["render"]),
            ("RENDER_QA", st["render_qa"]), ("PACKAGED", st["package"]), ("PACKAGE_QA", st["package_qa"]),
            ("HOSTED", st["asset_hosting"]), ("BUFFER", st["buffer"]["status"] or "NOT_STARTED"),
            ("APPROVAL", st["approval"]["status"]), ("STATE", st["state"])]
    out = [st["episode_id"]] + [f"{k:<14} {v}" for k, v in rows]
    if st["errors"] and st["state"] in states.FAILURES:
        out.append(f"{'LAST_ERROR':<14} {st['errors'][-1]['detail']}")
    return "\n".join(out)


# ---------------------------------------------------------------- self-healing
def _heal_block(st):
    return st.setdefault("heal", {"attempts": 0, "exhausted": False, "log": []})


def _replace_in_package(ctx, eid, old, new):
    p = ctx.pkg_path(eid)
    if not p.is_file() or not old or old == new:
        return False
    pk = json.loads(p.read_text())
    changed = False
    for k in ("instagram_caption", "youtube_description"):
        if isinstance(pk.get(k), str) and old in pk[k]:
            pk[k] = pk[k].replace(old, new)
            changed = True
    if changed:
        p.write_text(json.dumps(pk, indent=2, ensure_ascii=False) + "\n")
    return changed


def heal(ctx, st, max_attempts=3):
    """One bounded automatic repair for a failed episode. Returns (state, action|None).
    Repairs never weaken a gate: they fix the input and send the episode back through the
    same gate. Unrepairable failures (originality, over-ceiling duration, anything with
    Buffer doubt) mark the episode exhausted so the autopilot fills its slot instead."""
    eid, s = st["episode_id"], st["state"]
    h = _heal_block(st)
    last = (st["errors"][-1]["detail"] if st["errors"] else "") or ""
    if h["exhausted"]:
        return st, None
    if h["attempts"] >= max_attempts:
        h["exhausted"] = True
        h["log"].append({"at": now_iso(), "run": ctx.run_id, "action": f"exhausted after {h['attempts']} repairs"})
        ctx.store.save(st)
        return st, None
    action, reopen_to = None, None
    B = st["buffer"]
    if s == "VALIDATION_FAILED" and "source" in last and "does not match" in last and "originality" not in last:
        ep = json.loads(ctx.ep_path(eid).read_text())
        try:
            fetched = ctx.fetch_scripture(ref_of(ep)) if ctx.fetch_scripture else None
        except Exception:
            fetched = None
        if fetched:
            fetched = norm_text(fetched)
            old = ep["bible"]["text"]
            ep["bible"]["text"] = fetched
            ctx.ep_path(eid).write_text(json.dumps(ep, indent=2, ensure_ascii=False) + "\n")
            _replace_in_package(ctx, eid, old, fetched)
            action = f"scripture text for {ref_of(ep)} replaced with the {scripture.VERSION} source wording (episode + package)"
    elif s == "BLOCKED" and st.get("validation") == "BLOCKED" and not B.get("post_id") and not B.get("pending_mutation"):
        action, reopen_to = "scripture lookup failed; retrying validation", "GENERATED"
    elif s in ("RENDER_FAILED", "RENDER_QA_FAILED"):
        if "duration" in last and "outside" in last:
            action = None            # dialogue is never trimmed automatically
        else:
            v = video_path(ctx, eid)
            if v.exists():
                v.unlink()
            action = "stale or broken render removed; re-rendering"
    elif s == "PACKAGE_QA_FAILED":
        p = ctx.pkg_path(eid)
        pk = json.loads(p.read_text()) if p.is_file() else None
        fixes = []
        if pk is not None:
            tags = pk.get("instagram_hashtags")
            tags = tags if isinstance(tags, list) else (tags or "").split()
            n = ctx.rules["package"]["hashtag_count"]
            if "hashtag count" in last and len(tags) > n:
                pk["instagram_hashtags"] = tags[:n]; fixes.append(f"hashtags trimmed to {n}")
            mx = ctx.rules["package"]["youtube_title_max"]
            if "youtube title too long" in last and len(pk.get("youtube_title", "")) > mx:
                t = pk["youtube_title"].replace(" #Shorts", "")
                t = t[:mx - 8].rsplit(" ", 1)[0] + " #Shorts"
                pk["youtube_title"] = t; fixes.append("youtube title shortened")
            if any(k in last for k in ("honesty line", "crisis line", "banned phrase")):
                crisis, _ = safety.crisis_check(json.loads(ctx.ep_path(eid).read_text()), pk)
                fixes += safety.fix_package(pk, crisis=crisis)
            if "labels another translation" in last:
                for k, v in list(pk.items()):
                    if isinstance(v, str): pk[k] = scripture.label(v)
                fixes.append(f"translation labels set to {scripture.VERSION}")
            if "Bible reference" in last:
                ep = json.loads(ctx.ep_path(eid).read_text())
                ref = ref_of(ep)
                pk["youtube_description"] = pk.get("youtube_description", "") + f"\n\n{ref} ({scripture.VERSION})"
                fixes.append(f"reference {ref} added to the description")
            if fixes:
                p.write_text(json.dumps(pk, indent=2, ensure_ascii=False) + "\n")
        if "thumbnail" in last:
            v = video_path(ctx, eid)
            if v.exists():
                v.unlink()
            fixes.append("re-render to produce the thumbnail")
            reopen_to = "VALIDATED"
        action = "; ".join(fixes) if fixes else None
    elif s in ("PACKAGE_FAILED", "HOSTING_FAILED") or (s == "BUFFER_FAILED" and not B.get("pending_mutation")):
        action = "transient step failure; retrying the same step"
    if not action:
        h["exhausted"] = True
        h["log"].append({"at": now_iso(), "run": ctx.run_id, "action": f"not auto-repairable: {s}: {last[:200]}"})
        ctx.store.save(st)
        return st, None
    h["attempts"] += 1
    h["log"].append({"at": now_iso(), "run": ctx.run_id, "action": action})
    if reopen_to:
        ts = now_iso()
        st["history"].append({"at": ts, "from": s, "to": reopen_to, "run": ctx.run_id, "evidence": f"heal: {action}"[:300]})
        st["state"], st["updated_at"] = reopen_to, ts
        ctx.store.save(st)
    else:
        ctx.store.reopen(st, f"heal: {action}", ctx.run_id)
    ctx.log(f"[heal] {eid} {s} -> {st['state']}: {action}")
    return st, action


def autoadvance(ctx, eid, max_rounds=2, max_attempts=3):
    """advance, and on a failure repair + advance again (bounded)."""
    st = advance(ctx, eid)
    rounds = 0
    while st is not None and (st["state"] in states.FAILURES) and rounds < max_rounds:
        st, action = heal(ctx, st, max_attempts)
        ctx.store.upsert_manifest(st, _title(ctx, eid))
        if not action:
            break
        rounds += 1
        st = advance(ctx, eid)
    return st
