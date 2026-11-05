"""DEC-JR-018 weekly Instagram verse carousel ("5 verses for when family pressure hits").

content-os/carousels/<id>.json holds the slides (cover, 5-7 total, closing share slide), caption, hashtags,
first comment and the slot. Gates (fail closed, same spirit as the episode gates):
  every verse slide is verbatim KJV from data/bible/kjv.json and carries an r10_context note (R10);
  5-7 slides, cover first, share slide last; caption has a share line (R12), the KJV label, exactly 5
  hashtags, no bait; first_comment passes R13; slot is the config weekly_carousel slot and never 08:00/19:30/08:05.
Images are rendered by scripts/content_os/render_carousel.ts into content-os/carousels/<id>/ and hosted from the
public repo at the commit that added them (raw.githubusercontent.com/<repo>/<sha>/...), so the URL never changes.
schedule() creates ONE Buffer post (Instagram, type carousel), reads it back, and records the post id; a post
whose text is already in Buffer is adopted, never duplicated. Nothing already in Buffer is edited or deleted."""
import datetime as dt, json, pathlib, re, subprocess, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from daily import scripture, safety
from daily.pipeline import BAIT_PATTERNS

REPO = "selvin-paul-raj/jesus-replies-studio"
BUSY = {"08:00", "19:30", "08:05"}       # Reel slots + daily verse Story (publishing-rules.json)


def load(root, cid):
    return json.loads((pathlib.Path(root) / "content-os/carousels" / f"{cid}.json").read_text(encoding="utf-8"))


def caption(c):
    return c["caption"].rstrip() + "\n\n" + " ".join(c["hashtags"])


def problems(c, cfg=None):
    probs = []
    slides = c.get("slides") or []
    lo, hi = ((cfg or {}).get("weekly_carousel") or {}).get("slides", [5, 7])
    if not lo <= len(slides) <= hi:
        probs.append(f"{len(slides)} slides (need {lo}-{hi})")
    if not slides or slides[0].get("kind") != "cover":
        probs.append("first slide must be the cover")
    if not slides or slides[-1].get("kind") != "share":
        probs.append("last slide must be the share slide")
    verses = [s for s in slides if s.get("kind") == "verse"]
    if len(verses) < 3:
        probs.append("fewer than 3 verse slides")
    refs = set()
    for s in verses:
        ref = s.get("ref", "")
        want = scripture.lookup(ref)
        if want is None:
            probs.append(f"{ref}: not found in the bundled KJV")
        elif s.get("text") != want:
            probs.append(f"{ref}: text is not verbatim KJV")
        if not (s.get("r10_context") or "").strip():
            probs.append(f"{ref}: r10_context missing (the verse must mean this in its own passage)")
        if ref in refs:
            probs.append(f"{ref}: repeated")
        refs.add(ref)
    cap = c.get("caption") or ""
    if "(KJV)" not in cap and "KJV" not in cap:
        probs.append("caption must label the Scripture KJV")
    if not safety.share_line_of(cap):
        probs.append("R12 share line missing from caption")
    if any(re.search(b, cap, re.I) for b in BAIT_PATTERNS) or re.search(r"(?:^|\s)#\w", cap):
        probs.append("bait or hashtags inside the caption body")
    if len(c.get("hashtags") or []) != 5:
        probs.append("exactly 5 hashtags")
    probs += safety.first_comment_problems(c.get("first_comment"))
    t = (c.get("slot") or {}).get("time")
    if t in BUSY:
        probs.append(f"slot {t} collides with a Reel or the verse Story")
    wc = (cfg or {}).get("weekly_carousel") or {}
    if wc and t and t != wc.get("time"):
        probs.append(f"slot time {t} is not the weekly_carousel time {wc.get('time')}")
    return probs


def image_paths(root, c):
    d = pathlib.Path(root) / "content-os/carousels" / c["id"]
    return [d / f"slide-{i + 1}.png" for i in range(len(c["slides"]))]


def hosted_urls(root, c, sha=None):
    paths = image_paths(root, c)
    missing = [p.name for p in paths if not p.is_file()]
    if missing:
        raise RuntimeError(f"slides not rendered: {missing}")
    if sha is None:
        rel = str(paths[0].parent.relative_to(root))
        sha = subprocess.run(["git", "log", "-1", "--format=%H", "--", rel], cwd=root, capture_output=True, text=True).stdout.strip()
        if not sha:
            raise RuntimeError("slides are not committed yet; push them first (the URL pins the commit)")
    return [f"https://raw.githubusercontent.com/{REPO}/{sha}/{p.relative_to(root)}" for p in paths]


def schedule(root, c, buffer, now, http_status, dry_run=True, min_lead_minutes=45, sha=None):
    """-> (result, record). Results: ALREADY_SCHEDULED, ADOPTED, SCHEDULED, DRY_RUN, BLOCKED:<why>, REJECTED:<why>."""
    rec = c.setdefault("buffer", {})
    if rec.get("post_id") and rec.get("state") in ("SCHEDULED", "SENT"):
        return "ALREADY_SCHEDULED", rec
    probs = problems(c, json.loads((pathlib.Path(root) / "config/content-os.json").read_text()))
    if probs:
        return "BLOCKED:" + "; ".join(probs), rec
    due = dt.datetime.fromisoformat(c["slot"]["due_at"])
    if due - now < dt.timedelta(minutes=min_lead_minutes):
        return "BLOCKED:slot is in the past or under the lead time", rec
    try:
        urls = hosted_urls(root, c, sha)
    except RuntimeError as e:
        return f"BLOCKED:{e}", rec
    bad = [u for u in urls if http_status(u) not in (200, 206)]
    if bad:
        return f"BLOCKED:{len(bad)} slide URL(s) not reachable", rec
    text = caption(c)
    posts, note = buffer.list_posts("instagram")
    if posts is None:
        return f"BLOCKED:Buffer list unreadable {note}", rec
    same = [p for p in posts if (p.get("text") or "").strip() == text.strip() and p.get("status") in ("scheduled", "sent", "draft")]
    if same:
        rec.update({"post_id": same[0]["id"], "state": same[0]["status"].upper(), "how": "ADOPTED existing Buffer post"})
        return "ADOPTED", rec
    if dry_run:
        return "DRY_RUN", rec
    out = buffer.create_carousel("instagram", text, urls, due.isoformat(), first_comment=c.get("first_comment"))
    if out.kind != "OK":
        rec.update({"state": "REJECTED", "detail": out.detail[:400]})
        return "REJECTED:" + out.detail[:200], rec
    post, how = buffer.read(out.post["id"])
    rec.update({"post_id": out.post["id"], "state": ((post or {}).get("status") or out.post.get("status") or "").upper(),
                "due_at": (post or out.post).get("dueAt"), "first_comment": "SET" if (post or {}).get("_first_comment") else "UNVERIFIED",
                "read_back": how, "image_urls": urls, "at": now.isoformat()})
    return "SCHEDULED", rec


def pending(root):
    for p in sorted((pathlib.Path(root) / "content-os/carousels").glob("CAR-*.json")):
        yield p, json.loads(p.read_text(encoding="utf-8"))
