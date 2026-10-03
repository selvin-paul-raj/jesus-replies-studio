#!/usr/bin/env python3
"""Content OS entry point.
  snapshot              read Buffer (both channels), store metrics + availability + checkpoint history
  attributes            write generated/attributes/*.attributes.json
  inventory             content-os/inventory.json
  plan --week D         content-os/weeks/D/weekly-content-plan.json (PROPOSED)
  report --week D       content-os/weeks/D/weekly-performance-report.json
  authorize --week D --by NAME --quote TEXT   record the user's weekly authorization for the exact plan hash
  schedule --week D [--dry-run]   schedule the authorized week on both platforms
  verify                read back every tracked platform publication
  weekly --week D       snapshot, attributes, inventory, plan, previous-week report, schedule dry run
Buffer mutations happen only in `schedule` without --dry-run, and only for an authorized plan."""
import argparse, datetime as dt, json, os, pathlib, sys, urllib.request
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from content_os import analytics, timing, inventory as inv_mod, brain, learn, episodes, ledger
from content_os.distribute import Distributor, DistStore
from content_os.client import Buffer
from daily import pipeline as pl

ROOT = pathlib.Path(os.environ.get("JR_ROOT", pathlib.Path(__file__).resolve().parents[2]))
OS_DIR = ROOT / "content-os"


def cfg_load():
    c = json.loads((ROOT / "config/content-os.json").read_text())
    c["buffer"] = json.loads((ROOT / "config/publishing-rules.json").read_text())["buffer"]
    return c


def wjson(p, obj):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n")


def rjson(p, default=None):
    return json.loads(p.read_text()) if p.exists() else default


def http_status(url):
    try:
        req = urllib.request.Request(url, method="GET", headers={"Range": "bytes=0-0", "User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status
    except urllib.error.HTTPError as e:
        return e.code
    except Exception:
        return None


def asset_check(url, size):
    def f():
        try:
            req = urllib.request.Request(url, headers={"Range": "bytes=0-63"})
            with urllib.request.urlopen(req, timeout=60) as r:
                head = r.read(64)
                total = int((r.headers.get("Content-Range") or "/0").split("/")[-1] or 0)
                ok = r.status in (200, 206) and b"ftyp" in head[:32] and (not size or total == size)
                return ok, f"http={r.status} ftyp={b'ftyp' in head[:32]} bytes={total}/{size}"
        except Exception as e:
            return False, f"asset unreadable: {type(e).__name__}"
    return f


def latest_snapshot():
    snaps = sorted((OS_DIR / "analytics/snapshots").glob("*.json"))
    return rjson(snaps[-1]) if snaps else {"rows": []}


def ctx_for_factory(eps, pkgs, assets):
    def ctx_for(eid):
        pk, a = pkgs.get(eid) or {}, assets.get(eid) or {}
        return {"asset_url": a.get("public_url"), "instagram_text": pl.caption_text(pk) if pk else "",
                "youtube_text": pk.get("youtube_description", ""), "youtube_title": pk.get("youtube_title", ""),
                "asset_check": asset_check(a.get("public_url"), a.get("size_bytes")) if a else (lambda: (False, "no asset"))}
    return ctx_for


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd")
    ap.add_argument("--week")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--by")
    ap.add_argument("--quote")
    ap.add_argument("--episode")
    ap.add_argument("--platform")
    a = ap.parse_args()
    cfg = cfg_load()
    now = dt.datetime.now(dt.timezone.utc)
    run = os.environ.get("GITHUB_RUN_ID", "local")
    eps, pkgs, assets = episodes.load_catalogue(ROOT)
    attrs = {e: episodes.derive_attributes(ep, pkgs.get(e), assets.get(e)) for e, ep in eps.items()}
    store = DistStore(ROOT, cfg["platforms"])
    week_dir = OS_DIR / "weeks" / (a.week or "none")

    def snapshot():
        buf = Buffer.from_env(cfg)
        posts, notes = {}, {}
        for p in cfg["platforms"]:
            posts[p], notes[p] = buf.list_posts(p)
            if posts[p] is None:
                print(f"[snapshot] {p} UNREADABLE {notes[p]}"); posts[p] = []
        rows = analytics.snapshot(posts, eps, pkgs, now, cfg["checkpoints_hours"])
        snap = {"taken_at": now.isoformat(), "source": "Buffer GraphQL posts list", "list_status": notes, "rows": rows}
        wjson(OS_DIR / f"analytics/snapshots/{now.date().isoformat()}.json", snap)
        wjson(OS_DIR / "analytics/availability.json", {"as_of": now.isoformat(), **analytics.availability(rows)})
        hist = rjson(OS_DIR / "analytics/metrics-history.json", {})
        added = analytics.update_history(hist, rows, cfg["checkpoints_hours"])
        wjson(OS_DIR / "analytics/metrics-history.json", hist)
        led = ledger.build(rows, hist, attrs, cfg)
        wjson(OS_DIR / "analytics/publications.json", {"as_of": now.isoformat(), "publications": led})
        wjson(OS_DIR / "analytics/slot-test.json", {"as_of": now.isoformat(), **ledger.slot_test(led, cfg)})
        jr = [r for r in rows if r["episode_id"]]
        cats = sorted({r["youtube_category"] for r in rows if r.get("youtube_category")})
        print(f"[snapshot] rows={len(rows)} jr_matched={len(jr)} lists={notes} history_added={added} youtube_categories_seen={cats}")
        return snap

    if a.cmd == "snapshot":
        snapshot(); return 0
    if a.cmd == "attributes":
        episodes.write_attributes(ROOT, eps, pkgs, assets); print(f"[attributes] {len(eps)} written"); return 0
    if a.cmd in ("inventory", "plan", "weekly", "report"):
        snap = snapshot() if a.cmd == "weekly" else latest_snapshot()
        if a.cmd == "weekly":
            episodes.write_attributes(ROOT, eps, pkgs, assets)
        dists = {d["episode_id"]: d for d in store.all()}
        inv = inv_mod.build(eps, assets, dists, snap["rows"], cfg)
        inv["as_of"] = now.isoformat()
        wjson(OS_DIR / "inventory.json", inv)
        print(f"[inventory] {inv['counts']} next_ready={inv['next_ready']}")
        if a.cmd == "inventory":
            return 0
        if a.cmd in ("plan", "weekly"):
            tm = timing.recommend(snap["rows"], cfg)
            research = rjson(OS_DIR / f"research/{a.week}.research.json", {})
            research["_path"] = f"content-os/research/{a.week}.research.json" if research else None
            exps = rjson(OS_DIR / "experiments.json", {"experiments": []})
            nums = [int(e[3:7]) for e in eps if e[3:7].isdigit()]
            plan = brain.build_plan(a.week, attrs, inv, tm, research, exps,
                                    analytics.summarize(snap["rows"], cfg), cfg, max(nums) + 1, now)
            wjson(week_dir / "weekly-content-plan.json", plan)
            print(f"[plan] {a.week} sha={plan['plan_sha256'][:12]} ready={sum(s['status']=='READY' for s in plan['slots'])} "
                  f"needs_generation={plan['generation_needed']} carry={plan['carry_over_ready']}")
            for s in plan["slots"]:
                print(f"[slot] {s['date']} {s['weekday'][:3]} {s['time']} {s['episode_id']} {s['status']} {s['emotional_angle']} {s['hook_strategy']} | {s['theme']}")
        prev = (dt.date.fromisoformat(a.week) - dt.timedelta(days=7)).isoformat()
        rep_week = a.week if a.cmd == "report" else prev
        plan_prev = rjson(OS_DIR / f"weeks/{rep_week}/weekly-content-plan.json")
        rep = learn.weekly_report(rep_week, snap["rows"], attrs, plan_prev, cfg, now)
        wjson(OS_DIR / f"weeks/{rep_week}/weekly-performance-report.json", rep)
        print(f"[report] {rep_week} published={len(rep['published_posts'])} patterns={sum(p['finding'].startswith('pattern') for p in rep['patterns'])}")
        for r in rep["NEXT_WEEK_RECOMMENDATIONS"]:
            print(f"[rec] {r}")
        if a.cmd != "weekly":
            return 0
        auto = cfg["autonomy"].get("standing_authorization")
        plan_now = rjson(week_dir / "weekly-content-plan.json")
        if auto and cfg["autonomy"]["scheduler_enabled"] and plan_now and plan_now["generation_needed"] == 0 \
                and not (week_dir / "authorization.json").exists():
            wjson(week_dir / "authorization.json", {"week_start": a.week, "plan_sha256": plan_now["plan_sha256"],
                                                    "authorized_by": "standing authorization", "quote": auto["quote"],
                                                    "given": auto["given"], "at": now.isoformat(),
                                                    "condition": "every slot READY (hosted, QA PASS); no generation pending"})
            print(f"[authorize] standing authorization applied to {plan_now['plan_sha256'][:12]}")
        a.dry_run = not (week_dir / "authorization.json").exists()
    if a.cmd == "authorize":
        plan = rjson(week_dir / "weekly-content-plan.json")
        if not plan or not a.by or not a.quote:
            print("[authorize] need --week with a plan, --by and --quote"); return 2
        wjson(week_dir / "authorization.json", {"week_start": a.week, "plan_sha256": plan["plan_sha256"],
                                                "authorized_by": a.by, "quote": a.quote, "at": now.isoformat(),
                                                "scope": {"platforms": cfg["platforms"], "slots": len(plan["slots"])}})
        print(f"[authorize] recorded for {plan['plan_sha256'][:12]}"); return 0
    if a.cmd in ("schedule", "weekly"):
        plan = rjson(week_dir / "weekly-content-plan.json")
        auth = rjson(week_dir / "authorization.json")
        if a.dry_run and not auth:
            auth = {"plan_sha256": plan["plan_sha256"], "dry_run_only": True}
        if not a.dry_run and not cfg["autonomy"]["scheduler_enabled"]:
            print("[schedule] scheduler_enabled=false in config/content-os.json: WAITING_FOR_USER"); return 3
        d = Distributor(ROOT, Buffer.from_env(cfg), cfg, http_status, run, now, dry_run=a.dry_run)
        res = d.schedule_week(plan, ctx_for_factory(eps, pkgs, assets), auth)
        wjson(week_dir / ("schedule-dry-run.json" if a.dry_run else f"schedule-run-{run}.json"), res)
        print(f"[schedule] {res['status']} {res.get('reason', '')}")
        for r in res["results"]:
            print(f"[sched] {r.get('episode_id')} {r.get('platform', '-')} {r.get('due_at', '')} {r['result']} state={r.get('state')} post={r.get('post_id')}")
        return 0 if res["status"] in ("DONE", "DRY_RUN") else 4
    if a.cmd == "cycle":
        snapshot()
        d = Distributor(ROOT, Buffer.from_env(cfg), cfg, http_status, run, now, dry_run=True)
        for o in d.verify_all(ctx_for_factory(eps, pkgs, assets)):
            print(f"[verify] {o['episode_id']} {o['platform']} {o['state']} {o['post_id']}")
        today = now.astimezone(timing.IST).date()
        monday = today - dt.timedelta(days=today.weekday())
        for wk in (monday, monday + dt.timedelta(days=7)):
            wd = OS_DIR / "weeks" / wk.isoformat()
            plan, auth = rjson(wd / "weekly-content-plan.json"), rjson(wd / "authorization.json")
            if not (plan and auth and cfg["autonomy"]["scheduler_enabled"]):
                continue
            d2 = Distributor(ROOT, Buffer.from_env(cfg), cfg, http_status, run, now, dry_run=False)
            res = d2.schedule_week(plan, ctx_for_factory(eps, pkgs, assets), auth)
            changed = [r for r in res["results"] if r["result"] not in ("ALREADY_SCHEDULED", "ALREADY_PUBLISHED", "MISSED_SLOT", "QUOTA_DEFERRED")]
            print(f"[topup] {wk} {res['status']} changed={len(changed)} deferred={sum(r['result']=='QUOTA_DEFERRED' for r in res['results'])}")
            for r in changed:
                print(f"[sched] {r.get('episode_id')} {r.get('platform','-')} {r.get('due_at','')} {r['result']} state={r.get('state')} post={r.get('post_id')}")
            if res["status"] == "STOPPED":
                return 4
        return 0
    if a.cmd == "hold":
        d = Distributor(ROOT, Buffer.from_env(cfg), cfg, http_status, run, now, dry_run=a.dry_run)
        r, blk = d.hold(a.episode, a.platform, ctx_for_factory(eps, pkgs, assets)(a.episode))
        print(f"[hold] {a.episode} {a.platform} {r} state={blk['state']} post={blk['post_id']}"); return 0
    if a.cmd == "verify":
        d = Distributor(ROOT, Buffer.from_env(cfg), cfg, http_status, run, now, dry_run=True)
        out = d.verify_all(ctx_for_factory(eps, pkgs, assets))
        for o in out:
            print(f"[verify] {o['episode_id']} {o['platform']} {o['state']} {o['post_id']}")
        return 0
    print(__doc__); return 2


if __name__ == "__main__":
    sys.exit(main())
