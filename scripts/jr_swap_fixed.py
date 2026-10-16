#!/usr/bin/env python3
"""DEC-JR-009 (2026-10-16, Selvin yes 15:54 IST via CEO): swap queued Buffer posts that still carry
the old music / NIV / no honesty line for the fixed re-render, in the SAME post and SAME slot.

- Only posts whose Buffer status is draft or scheduled are touched; anything sent/sending/error
  with a sentAt is skipped (published posts are never changed).
- dueAt and draft/scheduled status are kept; only the video asset and text change.
- MODE=dry (default) prints the plan and mutates nothing. MODE=apply edits, then reads back.
- Writes content-os/requeue-2026-10-16.json (append-only list of what was replaced)."""
import json, os, pathlib, sys
ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from content_os.cli import cfg_load
from content_os.client import Buffer
from daily import pipeline as pl

ids = [i.strip() for i in os.environ["EPISODE_IDS"].split(",") if i.strip()]
tag, mode = os.environ["TAG"], os.environ.get("MODE", "dry")
cfg = cfg_load()
buf = Buffer.from_env(cfg)
man = {r["episode_id"]: r for r in json.loads((ROOT / "generated/release-manifest.json").read_text())
       if r.get("release_tag") == tag and r.get("qa_status") == "PASS"}
led_p = ROOT / "content-os/requeue-2026-10-16.json"
ledger = json.loads(led_p.read_text()) if led_p.exists() else []
fail = 0

def targets(eid):
    out = {}
    dp = ROOT / f"episodes/{eid}/distribution.json"
    if dp.exists():
        for plat, b in json.loads(dp.read_text())["platforms"].items():
            if b.get("post_id"): out[plat] = b["post_id"]
    sp = ROOT / f"episodes/{eid}/state.json"
    if sp.exists():
        pid = (json.loads(sp.read_text()).get("buffer") or {}).get("post_id")
        if pid and "instagram" not in out: out["instagram"] = pid
    return out

for eid in ids:
    row = man.get(eid)
    if not row:
        print(f"[swap] {eid} SKIP no PASS asset in release {tag} (old version stays)"); fail += 1; continue
    pk = json.loads((ROOT / f"generated/{eid}.package.json").read_text())
    for plat, pid in targets(eid).items():
        post, d = buf.read(pid)
        if post is None:
            print(f"[swap] {eid} {plat} {pid} SKIP unreadable: {d}"); fail += 1; continue
        st, due = post.get("status"), post.get("dueAt")
        if post.get("sentAt") or st not in ("draft", "scheduled"):
            print(f"[swap] {eid} {plat} {pid} SKIP status={st} sentAt={post.get('sentAt')} (never touch published)"); continue
        if post.get("_asset") == row["public_url"]:
            print(f"[swap] {eid} {plat} {pid} already fixed"); continue
        text = pl.caption_text(pk) if plat == "instagram" else pk["youtube_description"]
        yt = dict(cfg["youtube"], title=pk["youtube_title"]) if plat == "youtube" else None
        print(f"[swap] {eid} {plat} {pid} status={st} due={due} old={str(post.get('_asset')).split('/')[-2:]} -> {tag}")
        if mode != "apply": continue
        fn = buf.to_draft if st == "draft" else buf.schedule_draft
        o = fn(pid, plat, text, row["public_url"], due, yt)
        back, _ = buf.read(pid)
        ok = o.kind == "OK" and back and back.get("_asset") == row["public_url"] and back.get("status") == st and back.get("dueAt") == due
        print(f"[swap] {eid} {plat} {pid} {'OK' if ok else 'FAILED'} outcome={o.kind} {getattr(o,'detail','') or ''}"[:400])
        if not ok: fail += 1
        ledger.append({"episode_id": eid, "platform": plat, "post_id": pid, "status_kept": st, "due_at_kept": due,
                       "old_asset": post.get("_asset"), "new_asset": row["public_url"], "result": "REPLACED" if ok else "FAILED",
                       "run": os.environ.get("GITHUB_RUN_ID", "local")})
        if ok:
            sp = ROOT / f"episodes/{eid}/state.json"
            if sp.exists():
                s = json.loads(sp.read_text()); s["asset_url"] = row["public_url"]
                sp.write_text(json.dumps(s, indent=2, ensure_ascii=False) + "\n")
if mode == "apply":
    led_p.write_text(json.dumps(ledger, indent=2, ensure_ascii=False) + "\n")
print(f"[swap] done mode={mode} failures={fail}")
sys.exit(1 if fail and mode == "apply" else 0)
