#!/usr/bin/env python3
"""CEO decision 2026-10-23 08:46 IST: promote ready short episodes into slots whose queued
posts are blocked (IG drafts) or carry old long renders (YouTube), re-using the SAME Buffer
posts. Nothing is deleted: each existing post is edited to the new episode's video, text and
title and scheduled at the slot time. Published posts are never touched.

PLAN env: JSON list of {"slot": "<ISO Z dueAt>", "new": "JR-00NN", "old": "JR-00MM"}.
For each slot and platform the post recorded for OLD is edited to NEW.

Rate limits (Buffer has throttled reads since 2026-10-18): every call is spaced by GAP
seconds; reads retry with backoff; a mutation is re-sent ONLY when Buffer explicitly rejected
it for rate limiting (nothing changed). An unclear mutation result is reconciled by read-back,
never blindly retried. MODE=dry prints the plan only."""
import json, os, pathlib, sys, time, datetime as dt
ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from content_os.cli import cfg_load
from content_os.client import Buffer
from daily import pipeline as pl

PLAN = json.loads(os.environ["PLAN"])
MODE = os.environ.get("MODE", "dry")
GAP = int(os.environ.get("GAP", "15"))
BACKOFF = [30, 60, 120, 240, 480]
IST = dt.timezone(dt.timedelta(hours=5, minutes=30))
RUN = os.environ.get("GITHUB_RUN_ID", "local")
cfg = cfg_load()
buf = Buffer.from_env(cfg)
man = {}
for r in json.loads((ROOT / "generated/release-manifest.json").read_text()):
    if r.get("qa_status", "PASS") == "PASS":
        man[r["episode_id"]] = r  # latest PASS row wins
led_p = ROOT / "content-os/promote-2026-10-23.json"
ledger = json.loads(led_p.read_text()) if led_p.exists() else []


def now_ist():
    return dt.datetime.now(IST).strftime("%a %Y-%m-%d %-I:%M %p IST (UTC+05:30)")


def limited(x):
    s = json.dumps(x) if not isinstance(x, str) else x
    return any(k in s.lower() for k in ("too many", "rate_limit", "rate limit", "http=429"))


def read(pid):
    for i, w in enumerate([0] + BACKOFF):
        if w:
            print(f"[wait] rate limited reading {pid}, retry {i} in {w}s"); time.sleep(w)
        time.sleep(GAP)
        post, d = buf.read(pid)
        if post is not None or not limited(d):
            return post, d
    return None, "RATE_LIMITED_AFTER_BACKOFF"


def same_time(a, b):
    pa = dt.datetime.fromisoformat(a.replace("Z", "+00:00")); pb = dt.datetime.fromisoformat(b.replace("Z", "+00:00"))
    return abs((pa - pb).total_seconds()) < 60


def dist(eid):
    p = ROOT / f"episodes/{eid}/distribution.json"
    if p.exists():
        return p, json.loads(p.read_text())
    blank = lambda: {"state": "NONE", "post_id": None, "due_at": None, "sent_at": None, "external_link": None,
                     "pending_mutation": None, "attempts": 0, "error": None, "history": []}
    return p, {"episode_id": eid, "platforms": {"instagram": blank(), "youtube": blank()}}


results, fail = [], 0
for item in PLAN:
    slot, new, old = item["slot"], item["new"], item["old"]
    row = man.get(new)
    pk = json.loads((ROOT / f"generated/{new}.package.json").read_text())
    _, dold = dist(old)
    dnp, dnew = dist(new)
    for plat in ("instagram", "youtube"):
        tag = f"[promote] {slot} {plat} {old}->{new}"
        if not row:
            print(f"{tag} SKIP: no QA-passed render for {new}"); fail += 1; results.append((slot, plat, "NO_ASSET")); continue
        if dnew["platforms"][plat].get("post_id"):
            print(f"{tag} SKIP: {new} already has a {plat} post {dnew['platforms'][plat]['post_id']}")
            results.append((slot, plat, "ALREADY")); continue
        # Instagram: schedule NEW's own parked draft (old IG drafts stay parked, untouched).
        # YouTube: re-use the post queued for OLD (its long render is pulled by the edit).
        if plat == "instagram":
            src_ep = new
            pid = (json.loads((ROOT / f"episodes/{new}/state.json").read_text()).get("buffer") or {}).get("post_id")
        else:
            src_ep = old
            pid = dold["platforms"][plat].get("post_id")
        if not pid:
            print(f"{tag} SKIP: {src_ep} has no {plat} post"); fail += 1; results.append((slot, plat, "NO_POST")); continue
        post, d = read(pid)
        if post is None:
            print(f"{tag} UNCONFIRMED: cannot read {pid}: {d}"); fail += 1; results.append((slot, plat, "UNCONFIRMED")); continue
        st, src = post.get("status"), post.get("_asset") or ""
        if post.get("sentAt") or st not in ("draft", "scheduled"):
            print(f"{tag} SKIP: {pid} status={st} sentAt={post.get('sentAt')} (never touch published)"); fail += 1
            results.append((slot, plat, "PUBLISHED")); continue
        if src == row["public_url"] and st == "scheduled" and same_time(post["dueAt"], slot):
            print(f"{tag} already done"); ok = True
        else:
            if not src.endswith(f"/{src_ep}.mp4"):
                print(f"{tag} REFUSED: {pid} asset is {src}, not {src_ep}"); fail += 1; results.append((slot, plat, "GUARD")); continue
            if st == "scheduled" and not same_time(post["dueAt"], slot):
                print(f"{tag} REFUSED: {pid} is scheduled at {post['dueAt']}, not this slot"); fail += 1
                results.append((slot, plat, "GUARD")); continue
            text = pl.caption_text(pk) if plat == "instagram" else pk["youtube_description"]
            yt = dict(cfg["youtube"], title=pk["youtube_title"]) if plat == "youtube" else None
            print(f"{tag} post={pid} status={st} due={post['dueAt']} old={src.split('/')[-1]} -> {row['public_url'].split('/')[-1]} at {slot}")
            if MODE != "apply":
                results.append((slot, plat, "DRY")); continue
            o = None
            for i, w in enumerate([0] + BACKOFF):
                if w:
                    print(f"[wait] edit rate limited, retry {i} in {w}s"); time.sleep(w)
                time.sleep(GAP)
                o = buf.schedule_draft(pid, plat, text, row["public_url"], slot, yt)
                if not (o.kind == "REJECTED" and limited(o.detail)):
                    break
            back, d2 = read(pid)
            ok = bool(back) and back.get("_asset") == row["public_url"] and back.get("status") == "scheduled" \
                and same_time(back.get("dueAt") or "1970-01-01T00:00:00Z", slot)
            print(f"{tag} {'OK' if ok else 'NOT CONFIRMED'} edit={o.kind} {o.detail or ''} readback={d2}"[:500])
        results.append((slot, plat, "OK" if ok else "UNCONFIRMED"))
        ledger.append({"at": now_ist(), "run": RUN, "slot": slot, "platform": plat, "post_id": pid,
                       "old_episode": old, "new_episode": new, "new_asset": row["public_url"],
                       "result": "PROMOTED" if ok else "UNCONFIRMED"})
        if not ok:
            fail += 1; continue
        evid = f"CEO 2026-10-23 promote: post {pid} ({'own draft' if src_ep == new else 're-used from ' + old}) scheduled {slot} (run {RUN})"
        nb = dnew["platforms"][plat]
        nb["history"].append({"at": now_ist(), "from": nb["state"], "to": "SCHEDULED", "run": RUN, "evidence": evid})
        nb.update(state="SCHEDULED", post_id=pid, due_at=slot, error=None, pending_mutation=None, attempts=nb.get("attempts", 0) + 1)
        if src_ep == new:
            sp = ROOT / f"episodes/{new}/state.json"; stj = json.loads(sp.read_text())
            stj["buffer"].update(status="scheduled", due_at=slot)
            sp.write_text(json.dumps(stj, indent=2, ensure_ascii=False) + "\n")
            continue
        ob = dold["platforms"][plat]
        ob["history"].append({"at": now_ist(), "from": ob["state"], "to": "NONE", "run": RUN,
                              "evidence": f"post {pid} handed to {new} (old long render pulled; awaiting rewrite)"})
        ob.update(state="NONE", post_id=None, due_at=None, error=None, pending_mutation=None, attempts=0, last_read_error=None)
    if MODE == "apply":
        dnp.parent.mkdir(parents=True, exist_ok=True)
        dnp.write_text(json.dumps(dnew, indent=2, ensure_ascii=False) + "\n")
        (ROOT / f"episodes/{old}/distribution.json").write_text(json.dumps(dold, indent=2, ensure_ascii=False) + "\n")
        led_p.write_text(json.dumps(ledger, indent=2, ensure_ascii=False) + "\n")

print("[promote] SUMMARY")
for s, p, r in results:
    print(f"[promote] {s} {p} {r}")
print(f"[promote] done mode={MODE} failures={fail}")
sys.exit(1 if fail and MODE == "apply" else 0)
