#!/usr/bin/env python3
"""Jesus Replies daily post system CLI.

  next-id                                  print the next unused episode id
  allocate --date D --slot MORNING|NIGHT   map (date, slot) to exactly one episode id
  brief EID                                write authoring constraints (no dialogue)
  advance EID [--dry-run]                  run from current state up to the Buffer draft
                                           (auto-APPROVED under the standing authorization when
                                           publishing-rules require_human_approval=false)
  autoadvance EID                          advance + bounded self-healing repairs on failure
  approve EID --date D --time HH:MM --tz Asia/Kolkata --by NAME --evidence "words"
  schedule EID [--dry-run]                 only after APPROVED; whole-post edit + read-back
  verify EID | --all                       post-publish verification
  status EID
  release-review EID --by NAME --evidence "words"
                                           a human read a crisis-gate hold and lets it continue
  verse "Psalm 23:1"                       print the exact BSB text for a reference (authoring)
  to-bsb EID                               switch an UNPUBLISHED, not-yet-in-Buffer episode from NIV to BSB
                                           (episode text + package labels); refuses anything already drafted

--dry-run copies state to a scratch directory and never uploads, creates, schedules or
publishes. Secrets are redacted from every printed line."""
import argparse, json, os, pathlib, shutil, sys, tempfile
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from daily import pipeline as pl                      # noqa: E402
from daily.store import Store                         # noqa: E402
from daily.buffer import Buffer                       # noqa: E402
from daily import bsb                                 # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[2]


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
    ctx = pl.Ctx(ROOT, rules, store, run_id, a.dry_run, buffer, fetch_scripture=bsb.lookup)

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
    if a.cmd == "autoadvance":
        st = pl.autoadvance(ctx, a.eid)
        if st is None: return 3
        print(pl.report(st))
        h = st.get("heal") or {}
        if h.get("log"):
            print(f"{'HEAL':<14} attempts={h.get('attempts')} exhausted={h.get('exhausted')} last={h['log'][-1]['action']}")
        return 0 if st["state"] not in pl.states.FAILURES and st["state"] != "BLOCKED" else 1
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
    if a.cmd == "release-review":
        st = store.load(a.eid)
        if (st.get("review") or {}).get("status") != "HELD_FOR_REVIEW":
            print(f"[review] {a.eid} is not held"); return 1
        if not a.by or not a.evidence:
            print("[review] needs --by and --evidence (the reviewer's own words)"); return 1
        st["review"].update({"status": "RELEASED", "released_by": a.by, "released_at": pl.now_iso(),
                             "evidence": pl.redact(a.evidence)[:300]})
        store.save(st)
        print(f"[review] {a.eid} RELEASED by {a.by}; the next daily run continues it"); return 0
    if a.cmd == "verse":
        t = bsb.lookup(a.eid)
        print(t if t else f"[verse] {a.eid} not found in the BSB text")
        return 0 if t else 1
    if a.cmd == "to-bsb":
        return to_bsb(a.eid, store)
    if a.cmd == "status":
        print(pl.report(store.load(a.eid))); return 0
    ap.error(f"unknown command {a.cmd}")


def to_bsb(eid, store):
    st = store.load(eid)
    if st["buffer"].get("post_id") or st["state"] in ("SCHEDULED", "PUBLISHED", "PUBLISHED_VERIFIED", "APPROVED"):
        print(f"[to-bsb] {eid} is {st['state']} with Buffer post {st['buffer'].get('post_id')}; not touched")
        return 1
    ep_p, pk_p = ROOT / f"generated/{eid}.json", ROOT / f"generated/{eid}.package.json"
    ep = json.loads(ep_p.read_text())
    b = ep.get("bible") or {}
    text = bsb.lookup(bsb.ref_from_bible(b))
    if not text:
        print(f"[to-bsb] {eid} {bsb.ref_from_bible(b)} not in BSB"); return 1
    old = b.get("text")
    b.update({"version": bsb.VERSION, "text": text})
    ep_p.write_text(json.dumps(ep, indent=2, ensure_ascii=False) + "\n")
    if pk_p.exists():
        pk = json.loads(pk_p.read_text())
        for k in ("instagram_caption", "youtube_description", "thumbnail_text"):
            if isinstance(pk.get(k), str):
                v = pk[k].replace("(NIV)", "(BSB)").replace(" NIV", " BSB")
                pk[k] = v.replace(old, text) if old else v
        pk_p.write_text(json.dumps(pk, indent=2, ensure_ascii=False) + "\n")
    print(f"[to-bsb] {eid} now BSB {bsb.ref_from_bible(b)}; re-run advance to validate and re-render")
    return 0


if __name__ == "__main__":
    sys.exit(main())
