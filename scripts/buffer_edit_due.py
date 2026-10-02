#!/usr/bin/env python3
"""ONE editPost on ONE allowlisted post. Buffer validates edits as whole posts, so the
CURRENT text, asset URL and reel metadata are read from Buffer first and resent unchanged;
only dueAt differs. saveToDraft is not sent (optional on EditPostInput). Never retries.
Never prints the key."""
import json, os, sys, urllib.error, urllib.request
API="https://api.buffer.com"; KEY=os.environ["BUFFER_API_KEY"]
ALLOW={"6abe5636534a309fe98499bb": ("JR-0035", "2026-10-03T02:30:00Z")}
pid, due = sys.argv[1], sys.argv[2]
if pid not in ALLOW or ALLOW[pid][1] != due:
    print(f"[guard] REFUSED: {pid} / {due} is not the approved post+slot"); raise SystemExit(9)
ep = ALLOW[pid][0]
def gql(q):
    r=urllib.request.Request(API,data=json.dumps({"query":q}).encode(),method="POST",
        headers={"Content-Type":"application/json","Authorization":f"Bearer {KEY}"})
    with urllib.request.urlopen(r,timeout=90) as x: return x.status,json.loads(x.read())

st,js=gql('query { post(input: { id: %s }) { id status dueAt text shareMode schedulingType assets { ... on VideoAsset { source video { thumbnailOffset } } } } }' % json.dumps(pid))
cur=(js.get("data") or {}).get("post")
if not cur or cur["status"]!="draft":
    print(f"[guard] REFUSED: pre-read did not find a draft: {json.dumps(cur or js)[:300]}"); raise SystemExit(9)
a=(cur.get("assets") or [{}])[0]; src=a.get("source"); off=(a.get("video") or {}).get("thumbnailOffset") or 1500
if not src or not src.endswith(f"/{ep}.mp4"):
    print(f"[guard] REFUSED: asset is not {ep}.mp4: {src}"); raise SystemExit(9)
print(f"[pre] {ep} status={cur['status']} due={cur['dueAt']} asset={src.split('/')[-1]} textlen={len(cur['text'])} offset={off}")

q=f"""mutation {{ editPost(input: {{
  id: {json.dumps(pid)}
  dueAt: {json.dumps(due)}
  text: {json.dumps(cur['text'])}
  mode: {cur['shareMode']}
  schedulingType: {cur['schedulingType']}
  assets: [{{ video: {{ url: {json.dumps(src)}, metadata: {{ thumbnailOffset: {off} }} }} }}]
  metadata: {{ instagram: {{ type: reel, shouldShareToFeed: true }} }}
}}) {{ ... on PostActionSuccess {{ post {{ id status dueAt }} }} ... on MutationError {{ message }} }} }}"""
print(f"[mutation] editPost {ep} id={pid} dueAt={due} (text/asset/metadata resent unchanged, saveToDraft not sent)")
try:
    st,js=gql(q)
except urllib.error.HTTPError as e:
    print(f"[buffer] action=FAILED http={e.code} {e.read().decode()[:300]}"); raise SystemExit(6)
except Exception as e:
    print(f"[buffer] action=UNRESOLVED reason={type(e).__name__}; reconcile, do not retry"); raise SystemExit(7)
res=(js.get("data") or {}).get("editPost") or {}
if js.get("errors") or res.get("message"):
    print(f"[buffer] action=FAILED http={st} detail={json.dumps(js.get('errors') or res)[:400]}"); raise SystemExit(6)
print(f"[buffer] action=EDITED post={json.dumps(res.get('post'))}")
