"""Steps of the daily post system. Every step reads state first, moves it along one
legal edge, records evidence, and stops at the first failure. External effects
(subprocess, scripture fetch, ffprobe, HTTP, Buffer) are injectable for tests."""
import datetime as dt, json, pathlib, re, subprocess, urllib.request
from zoneinfo import ZoneInfo
from . import states
from .redact import redact
from .store import Store, now_iso, ID_RE

IST = ZoneInfo("Asia/Kolkata")


# ---------------------------------------------------------------- helpers
def _jr_num(name):
    m = re.search(r"JR-(\d{4})", name)
    return int(m.group(1)) if m else None


def norm_text(s):
    s = (s or "").replace("\u201c", '"').replace("\u201d", '"').replace("\u2018", "'").replace("\u2019", "'")
    return re.sub(r"\s+", " ", s).strip()


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
    return pkg["instagram_caption"] + "\n\n" + tags


class Ctx:
    def __init__(self, root=".", rules=None, store=None, run_id="local", dry_run=False,
                 buffer=None, run=None, fetch_scripture=None, probe=None, http_get=None,
                 now=None, repo="selvin-paul-raj/jesus-replies-studio", log=print):
        self.root = pathlib.Path(root)
        self.rules = rules or json.loads((self.root / "config/publishing-rules.json").read_text())
        self.store = store or Store(root)
        self.run_id, self.dry_run, self.buffer, self.repo = run_id, dry_run, buffer, repo
        self.run = run or (lambda cmd, env=None: subprocess.run(cmd, capture_output=True, text=True, env=env))
        self.fetch_scripture = fetch_scripture
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
    issues, recent = [], corpus(ctx, exclude=ep.get("id"))
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


def brief(ctx, eid):
    """Authoring constraints for one slot. Writes no dialogue."""
    recent = sorted(corpus(ctx, exclude=eid), key=lambda e: _jr_num(e.get("id", "")) or 0)[-14:]
    b = {"episode_id": eid, "schema": "generated/JR-0036.json (id,title,character,topic,emotion,bible{book,chapter,verse,version=NIV,text},lines[{speaker,text}])",
         "package_schema": "generated/JR-0036.package.json",
         "avoid_titles": [e.get("title") for e in recent], "avoid_scripture": [ref_of(e) for e in recent if ref_of(e)],
         "avoid_hooks": [(e.get("lines") or [{}])[0].get("text") for e in recent],
         "recent_topics": [e.get("topic") for e in recent], "recent_emotions": [e.get("emotion") for e in recent],
         "duration_target_seconds": ctx.rules["duration"]["target_seconds"],
         "scripture_rule": "NIV verbatim, verified against Bible Gateway; unverifiable -> BLOCKED"}
    p = ctx.root / "generated/briefs" / f"{eid}.brief.json"
    if not ctx.dry_run:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(b, indent=2, ensure_ascii=False) + "\n")
    return b


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
    if b.get("version") != "NIV" or not b.get("text"): probs.append("scripture missing or not NIV")
    r = ctx.run(["npx", "tsx", "scripts/daily/validate-episode.ts", str(ctx.ep_path(eid))])
    if r.returncode != 0: probs.append(f"schema validator: {(r.stdout or r.stderr).strip()[-300:]}")
    ok, issues = originality(ctx, ep)
    if not ok: probs += [f"originality: {i}" for i in issues]
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
        return ctx.store.transition(st, "BLOCKED", f"scripture {ref} could not be verified (source unreadable); not rendering", ctx.run_id)
    if norm_text(fetched) != norm_text(b["text"]):
        st["validation"] = "FAIL"
        return ctx.store.transition(st, "VALIDATION_FAILED", f"scripture {ref} text does not match NIV source", ctx.run_id)
    st["validation"] = "PASS"
    return ctx.store.transition(st, "VALIDATED", f"schema PASS, originality PASS, NIV {ref} verbatim match", ctx.run_id)


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
        if len(pk["youtube_title"]) > P["youtube_title_max"]: probs.append("youtube title too long")
        if len(pk["youtube_description"]) > P["youtube_description_max"]: probs.append("youtube description too long")
        book = (ep.get("bible") or {}).get("book", "")
        if book and book.lower() not in (pk["instagram_caption"] + pk["youtube_description"]).lower():
            probs.append(f"Bible reference {book} not in caption or description")
        others = set(re.findall(r"JR-\d{4}", json.dumps(pk))) - {eid}
        if others: probs.append(f"references other episodes {sorted(others)}")
    thumbs = list((ctx.root / "output/thumbnails").glob(f"{eid}.*"))
    if not thumbs: probs.append("thumbnail image not rendered")
    if probs:
        st["package_qa"] = "FAIL"
        return ctx.store.transition(st, "PACKAGE_QA_FAILED", "; ".join(probs), ctx.run_id)
    st["package_qa"] = "PASS"
    return ctx.store.transition(st, "PACKAGE_QA_PASSED", f"caption {len(caption_text(pk))} chars, 5 hashtags, "
                                f"title {len(pk['youtube_title'])}, thumbnail {thumbs[0].name}", ctx.run_id)


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
    text = caption_text(json.loads(ctx.pkg_path(eid).read_text()))
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
    out = ctx.buffer.create_draft(text, st["asset_url"], ctx.rules["buffer"]["draft_due_at"])
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
    return ctx.store.transition(st, "WAITING_FOR_USER", "approval required: episode, date, time, timezone", ctx.run_id)


def advance(ctx, eid):
    """Runs from the episode's CURRENT state up to WAITING_FOR_USER and stops."""
    if not ctx.store.acquire(eid, ctx.run_id, ctx.rules["lock_ttl_minutes"]):
        ctx.log(f"[lock] {eid} is locked by another run; STOP")
        return None
    try:
        st = ctx.store.load(eid)
        chain = [(states.NEW, step_generated), ("GENERATED", step_validated), ("VALIDATED", step_rendered),
                 ("RENDERED", step_render_qa), ("RENDER_QA_PASSED", step_packaged), ("PACKAGED", step_package_qa),
                 ("PACKAGE_QA_PASSED", step_hosted), ("ASSET_HOSTED", step_buffer_draft)]
        for want, fn in chain:
            if st["state"] == want:
                before = st["state"]
                st = fn(ctx, st)
                ctx.store.upsert_manifest(st, _title(ctx, eid))
                if st["state"] == before:      # dry-run or read-only stop
                    break
            if st["state"] in states.FAILURES or st["state"] == "WAITING_FOR_USER":
                break
        return st
    finally:
        ctx.store.release(eid, ctx.run_id)


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
        text = caption_text(json.loads(ctx.pkg_path(eid).read_text()))
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
        out = ctx.buffer.schedule(B["post_id"], text, st["asset_url"], due)
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
    return "\n".join([st["episode_id"]] + [f"{k:<14} {v}" for k, v in rows])
