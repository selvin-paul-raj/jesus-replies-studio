"""Per-platform distribution state + scheduling + verification. One episode = one video,
two independent platform publications. Idempotent: an existing Buffer object is always
read back and reconciled; nothing is created while any doubt about prior state exists."""
import json, pathlib, datetime as dt
from .analytics import parse, norm_text

STATES = ["NONE", "DRAFT", "SCHEDULED", "PUBLISHED", "PUBLISHED_VERIFIED", "FAILED", "UNKNOWN", "BLOCKED"]
ALLOWED = {
    "NONE": {"DRAFT", "SCHEDULED", "PUBLISHED", "PUBLISHED_VERIFIED", "FAILED", "UNKNOWN", "BLOCKED"},
    "DRAFT": {"SCHEDULED", "PUBLISHED", "PUBLISHED_VERIFIED", "FAILED", "UNKNOWN", "BLOCKED"},
    "SCHEDULED": {"PUBLISHED", "PUBLISHED_VERIFIED", "FAILED", "UNKNOWN", "DRAFT", "BLOCKED"},
    "PUBLISHED": {"PUBLISHED_VERIFIED", "UNKNOWN"},
    "PUBLISHED_VERIFIED": set(),
    "FAILED": {"SCHEDULED", "UNKNOWN", "BLOCKED"},
    "UNKNOWN": {"DRAFT", "SCHEDULED", "PUBLISHED", "PUBLISHED_VERIFIED", "FAILED", "BLOCKED"},
    "BLOCKED": {"DRAFT", "SCHEDULED", "PUBLISHED", "PUBLISHED_VERIFIED", "FAILED", "UNKNOWN"},
}
BUFFER_STATUS = {"draft": "DRAFT", "scheduled": "SCHEDULED", "needs_approval": "SCHEDULED", "sending": "SCHEDULED",
                 "sent": "PUBLISHED", "error": "FAILED"}


def iso(t):
    return t.astimezone(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")


class IllegalTransition(Exception):
    pass


class DistStore:
    def __init__(self, root, platforms):
        self.root, self.platforms = pathlib.Path(root), platforms

    def path(self, eid):
        return self.root / "episodes" / eid / "distribution.json"

    def load(self, eid):
        p = self.path(eid)
        d = json.loads(p.read_text()) if p.exists() else {"episode_id": eid, "platforms": {}}
        for pl in self.platforms:
            d["platforms"].setdefault(pl, {"state": "NONE", "post_id": None, "due_at": None, "sent_at": None,
                                           "external_link": None, "pending_mutation": None, "attempts": 0,
                                           "error": None, "history": []})
        return d

    def save(self, d):
        p = self.path(d["episode_id"])
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(d, indent=2, ensure_ascii=False) + "\n")

    def all(self):
        return [json.loads(p.read_text()) for p in sorted((self.root / "episodes").glob("*/distribution.json"))]


def move(blk, to, evidence, run, now):
    frm = blk["state"]
    if to == frm:
        return
    if to not in ALLOWED[frm]:
        raise IllegalTransition(f"{frm} -> {to}")
    blk["history"].append({"at": iso(now), "from": frm, "to": to, "run": run, "evidence": evidence[:300]})
    blk["state"] = to


class Distributor:
    def __init__(self, root, buffer, cfg, http_check, run_id="local", now=None, dry_run=True):
        self.root, self.buf, self.cfg, self.http = pathlib.Path(root), buffer, cfg, http_check
        self.run, self.now, self.dry = run_id, now or dt.datetime.now(dt.timezone.utc), dry_run
        self.store = DistStore(root, cfg["platforms"])
        self.live = {}

    # ---------- reads ----------
    def live_posts(self, platform, refresh=False):
        if refresh or platform not in self.live:
            posts, d = self.buf.list_posts(platform)
            if posts is None:
                raise RuntimeError(f"cannot list {platform} posts: {d}")
            self.live[platform] = posts
        return self.live[platform]

    def expected_text(self, platform, ctx):
        return ctx["instagram_text"] if platform == "instagram" else ctx["youtube_text"]

    def find_matches(self, platform, ctx):
        want = norm_text(self.expected_text(platform, ctx))[:120]
        return [p for p in self.live_posts(platform)
                if (ctx.get("asset_url") and p.get("_asset") == ctx["asset_url"]) or norm_text(p.get("text"))[:120] == want]

    def verified(self, post, platform):
        link = post.get("externalLink")
        if not (post.get("sentAt") and link):
            return False, "sent but no permalink yet"
        code = self.http(link)
        if platform == "youtube":
            return code == 200, f"permalink http={code}"
        ok = (code is not None and code < 400) or bool(post.get("metricsUpdatedAt"))
        return ok, f"permalink http={code} metricsUpdatedAt={post.get('metricsUpdatedAt')}"

    def apply_post(self, blk, post, platform, why):
        st = BUFFER_STATUS.get(post.get("status"), "UNKNOWN")
        blk.update(post_id=post["id"], due_at=post.get("dueAt"), sent_at=post.get("sentAt"),
                   external_link=post.get("externalLink"))
        if st == "PUBLISHED":
            if blk["state"] != "PUBLISHED":
                move(blk, "PUBLISHED", f"{why}: status sent at {post.get('sentAt')}", self.run, self.now)
            ok, ev = self.verified(post, platform)
            if ok:
                move(blk, "PUBLISHED_VERIFIED", ev, self.run, self.now)
            return
        if st == "SCHEDULED" and post.get("dueAt"):
            grace = dt.timedelta(minutes=self.cfg["publish_grace_minutes"])
            if parse(post["dueAt"]) + grace < self.now:
                move(blk, "UNKNOWN", f"{why}: still '{post.get('status')}' after due {post['dueAt']} + grace", self.run, self.now)
                return
        if st == "FAILED":
            blk["error"] = (post.get("error") or {}).get("message") if isinstance(post.get("error"), dict) else "Buffer status error"
        move(blk, st, f"{why}: Buffer status {post.get('status')}", self.run, self.now)

    def reconcile(self, eid, platform, ctx):
        d = self.store.load(eid)
        blk = d["platforms"][platform]
        if blk["state"] == "PUBLISHED_VERIFIED":
            return d, blk
        if blk["post_id"]:
            post, det = self.buf.read(blk["post_id"])
            if post:
                self.apply_post(blk, post, platform, f"read {blk['post_id']}")
            elif det == "NOT_FOUND":
                move(blk, "BLOCKED", f"recorded post {blk['post_id']} not found in Buffer", self.run, self.now)
            else:
                move(blk, "UNKNOWN", f"read failed: {det}", self.run, self.now)
        else:
            m = self.find_matches(platform, ctx)
            if len(m) > 1:
                move(blk, "BLOCKED", f"duplicate Buffer posts for {eid}: {[p['id'] for p in m]}", self.run, self.now)
            elif len(m) == 1:
                self.apply_post(blk, m[0], platform, f"adopted existing {m[0]['id']}")
                blk["pending_mutation"] = None
            elif blk["pending_mutation"]:
                move(blk, "UNKNOWN", f"pending {blk['pending_mutation']['kind']} has no matching post", self.run, self.now)
        self.store.save(d)
        return d, blk

    # ---------- scheduling ----------
    def schedule(self, eid, platform, due_at, ctx):
        d, blk = self.reconcile(eid, platform, ctx)
        s = blk["state"]
        if eid in self.cfg.get("held_episodes", {}) and not ctx.get("held_authorized"):
            return "HELD", blk
        if s in ("UNKNOWN", "BLOCKED"):
            return "STOP", blk
        if s in ("PUBLISHED", "PUBLISHED_VERIFIED"):
            return "ALREADY_PUBLISHED", blk
        if s == "SCHEDULED":
            same = blk["due_at"] and abs((parse(blk["due_at"]) - parse(due_at)).total_seconds()) < 60
            return ("ALREADY_SCHEDULED" if same else "SCHEDULE_MISMATCH"), blk
        if s == "FAILED" and (blk["post_id"] or blk["attempts"] >= 2):
            return "NEEDS_REVIEW", blk
        if parse(due_at) < self.now + dt.timedelta(minutes=self.cfg["min_lead_minutes"]):
            return "MISSED_SLOT", blk
        ok, ev = ctx["asset_check"]()
        if not ok:
            return "ASSET_NOT_VERIFIED", blk
        yt = None
        if platform == "youtube":
            y = self.cfg["youtube"]
            if not y.get("category_id"):
                return "BLOCKED_YOUTUBE_CATEGORY", blk
            yt = dict(y, title=ctx["youtube_title"])
        text = self.expected_text(platform, ctx)
        if s == "DRAFT":
            post, det = self.buf.read(blk["post_id"])
            if not post or norm_text(post.get("text")) != norm_text(text) or post.get("_asset") != ctx["asset_url"]:
                return "DRAFT_CONTENT_MISMATCH", blk
        if self.dry:
            return ("WOULD_SCHEDULE_DRAFT" if s == "DRAFT" else "WOULD_CREATE"), blk
        kind = "schedule_draft" if s == "DRAFT" else "create_scheduled"
        blk["pending_mutation"] = {"kind": kind, "at": iso(self.now), "run": self.run, "due_at": due_at}
        self.store.save(d)
        if kind == "schedule_draft":
            out = self.buf.schedule_draft(blk["post_id"], platform, text, ctx["asset_url"], due_at, yt)
        else:
            out = self.buf.create_scheduled(platform, text, ctx["asset_url"], due_at, yt)
        blk["attempts"] += 1
        if out.kind == "OK":
            post, det = self.buf.read(out.post["id"])
            blk["pending_mutation"] = None
            if post and post.get("status") == "scheduled" and abs((parse(post["dueAt"]) - parse(due_at)).total_seconds()) < 60 \
                    and post.get("_asset") == ctx["asset_url"]:
                blk.update(post_id=post["id"], due_at=post["dueAt"])
                move(blk, "SCHEDULED", f"{kind} read back: scheduled {post['dueAt']}", self.run, self.now)
                r = "SCHEDULED"
            else:
                blk["post_id"] = out.post["id"]
                move(blk, "UNKNOWN", f"{kind} returned {out.post['id']} but read-back did not confirm ({det})", self.run, self.now)
                r = "STOP"
        elif out.kind == "REJECTED":
            blk["pending_mutation"] = None
            blk["error"] = out.detail
            if s == "DRAFT":
                blk["history"].append({"at": iso(self.now), "from": s, "to": s, "run": self.run, "evidence": f"edit rejected: {out.detail}"[:300]})
            else:
                move(blk, "FAILED", f"{kind} rejected: {out.detail}", self.run, self.now)
            r = "REJECTED"
        else:
            m = [p for p in self.live_posts(platform, refresh=True)
                 if p.get("_asset") == ctx["asset_url"] and p["id"] != (blk["post_id"] if s != "DRAFT" else None) or
                 (s == "DRAFT" and p["id"] == blk["post_id"])]
            if len(m) == 1:
                self.apply_post(blk, m[0], platform, f"{out.kind} reconciled by listing")
                blk["pending_mutation"] = None
                r = "RECONCILED_" + blk["state"]
            else:
                move(blk, "UNKNOWN", f"{kind} outcome {out.kind}; listing found {len(m)} candidates", self.run, self.now)
                r = "STOP"
        self.store.save(d)
        return r, blk

    def schedule_week(self, plan, ctx_for, authorization):
        if not authorization or authorization.get("plan_sha256") != plan.get("plan_sha256"):
            return {"status": "WAITING_FOR_USER", "reason": "week not authorized for this exact plan", "results": []}
        results = []
        for slot in plan["slots"]:
            if slot["status"] != "READY":
                results.append({"episode_id": slot["episode_id"], "result": "NOT_READY"})
                continue
            ctx = ctx_for(slot["episode_id"])
            for platform in slot["platforms"]:
                due = slot["due_at"][platform]
                r, blk = self.schedule(slot["episode_id"], platform, due, ctx)
                results.append({"episode_id": slot["episode_id"], "platform": platform, "due_at": due,
                                "result": r, "state": blk["state"], "post_id": blk["post_id"]})
                if r == "STOP":
                    return {"status": "STOPPED", "reason": f"{slot['episode_id']} {platform} unresolved", "results": results}
        return {"status": "DRY_RUN" if self.dry else "DONE", "results": results}

    def verify_all(self, ctx_for):
        out = []
        for d in self.store.all():
            for platform, blk in d["platforms"].items():
                if blk["state"] in ("DRAFT", "SCHEDULED", "PUBLISHED", "UNKNOWN") and (blk["post_id"] or blk["pending_mutation"]):
                    _, b = self.reconcile(d["episode_id"], platform, ctx_for(d["episode_id"]))
                    out.append({"episode_id": d["episode_id"], "platform": platform, "state": b["state"], "post_id": b["post_id"]})
        return out
