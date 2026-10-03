#!/usr/bin/env python3
"""Jesus Replies daily post system CLI.

  next-id                                  print the next unused episode id
  allocate --date D --slot MORNING|NIGHT   map (date, slot) to exactly one episode id
  brief EID                                write authoring constraints (no dialogue)
  advance EID [--dry-run]                  run from current state up to WAITING_FOR_USER
  approve EID --date D --time HH:MM --tz Asia/Kolkata --by NAME --evidence "words"
  schedule EID [--dry-run]                 only after APPROVED; whole-post edit + read-back
  verify EID | --all                       post-publish verification
  status EID

--dry-run copies state to a scratch directory and never uploads, creates, schedules or
publishes. Secrets are redacted from every printed line."""
import argparse, json, os, pathlib, shutil, sys, tempfile
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from daily import pipeline as pl                      # noqa: E402
from daily.store import Store                         # noqa: E402
from daily.buffer import Buffer                       # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[2]


def scripture_fetcher():
    sys.path.insert(0, str(ROOT / "scripts"))
    import importlib.util
    spec = importlib.util.spec_from_file_location("fetch_passage", ROOT / "scripts/fetch-passage.py")
    mod = importlib.util.module_from_spec(spec)
    import urllib.parse  # fetch-passage.py uses urllib.parse via urllib
    spec.loader.exec_module(mod)
    return mod.fetch


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd")
    ap.add_argument("eid", nargs="?")
    for a in ("--date", "--slot", "--time", "--tz", "--by", "--evidence"):
        ap.add_argument(a)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--allow-off-slot", action="store_true")
    a = ap.parse_args()
    run_id = os.environ.get("GITHUB_RUN_ID", "local")
    store = Store(ROOT)
    if a.dry_run:
        scratch = pathlib.Path(tempfile.mkdtemp(prefix="jr-dry-"))
        for d in ("episodes", "manifests"):
            if (ROOT / d).exists():
                shutil.copytree(ROOT / d, scratch / d)
        store = Store(ROOT)
        store.state_dir = scratch / "episodes"
        store.manifest_path = lambda: scratch / "manifests" / "episodes.json"
        print(f"[dry-run] state copied to scratch; nothing in the repo or Buffer is changed")
    rules = json.loads((ROOT / "config/publishing-rules.json").read_text())
    buffer = None
    if os.environ.get("BUFFER_API_KEY"):
        buffer = Buffer.from_env(rules)
    ctx = pl.Ctx(ROOT, rules, store, run_id, a.dry_run, buffer, fetch_scripture=scripture_fetcher())

    if a.cmd == "next-id":
        print(pl.next_episode_id(ctx)); return 0
    if a.cmd == "allocate":
        print(pl.allocate(ctx, a.date, a.slot)); return 0
    if a.cmd == "brief":
        print(json.dumps(pl.brief(ctx, a.eid), indent=2, ensure_ascii=False)); return 0
    if a.cmd == "advance":
        st = pl.advance(ctx, a.eid)
        if st is None: return 3
        print(pl.report(st))
        return 0 if st["state"] not in pl.states.FAILURES else 1
    if a.cmd == "approve":
        st = pl.approve(ctx, a.eid, a.date, a.time, a.tz, a.by, a.evidence, a.allow_off_slot)
        print(pl.report(st)); return 0
    if a.cmd == "schedule":
        if buffer is None:
            print("[schedule] BLOCKED: no Buffer access in this run"); return 1
        st = pl.schedule(ctx, a.eid)
        if st is None: return 3
        print(pl.report(st))
        return 0 if st["state"] == "SCHEDULED" or a.dry_run else 1
    if a.cmd == "verify":
        ids = [r["episode_id"] for r in store.load_manifest() if r["state"] in ("SCHEDULED", "PUBLISHED")] if a.all else [a.eid]
        bad = 0
        for eid in ids:
            st = pl.verify_published(ctx, eid)
            print(pl.report(st))
            bad += st["state"] == "PUBLISH_VERIFICATION_FAILED"
        print(f"[verify] checked={len(ids)} failed={bad}")
        return 1 if bad else 0
    if a.cmd == "read":
        # READ-ONLY independent read-back of the episode's recorded Buffer post.
        st = store.load(a.eid)
        pid = st["buffer"]["post_id"]
        if not pid or buffer is None:
            print(f"[read] {a.eid} no post id or no Buffer access"); return 1
        post, d = buffer.read(pid)
        if not post:
            print(f"[read] {a.eid} {pid} UNREADABLE {d}"); return 1
        pk = json.loads((ROOT / f"generated/{a.eid}.package.json").read_text())
        want = pl.caption_text(pk)
        tags = [w for w in post["text"].split() if w.startswith("#")]
        print(f"[read] post_id={post['id']} match={post['id'] == pid}")
        print(f"[read] status={post.get('status')} dueAt={post.get('dueAt')} channel={post.get('channelService')} shareMode={post.get('shareMode')}")
        print(f"[read] sentAt_field_in_schema={post['_has_sent_at_field']} sentAt={post.get('sentAt')}")
        print(f"[read] asset={post['_asset_source']} match={post['_asset_source'] == st['asset_url']}")
        print(f"[read] durationMs={post['_duration_ms']} rendered_s={st['render_facts'].get('duration_s')}")
        print(f"[read] caption_chars={len(post['text'])} caption_match={pl.norm_text(post['text']) == pl.norm_text(want)}")
        print(f"[read] hashtags={tags} match={tags == list(pk['instagram_hashtags'])}")
        return 0
    if a.cmd == "status":
        print(pl.report(store.load(a.eid))); return 0
    ap.error(f"unknown command {a.cmd}")


if __name__ == "__main__":
    sys.exit(main())
