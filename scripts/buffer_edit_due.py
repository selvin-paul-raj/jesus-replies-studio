#!/usr/bin/env python3
"""ONE editPost that changes ONLY dueAt on ONE allowlisted post. Sends id + dueAt and
nothing else: no saveToDraft (optional on EditPostInput), no text, no assets, no metadata.
Never retries. Never prints the key."""
import json, os, sys, urllib.error, urllib.request
API="https://api.buffer.com"; KEY=os.environ["BUFFER_API_KEY"]
ALLOW={"6abe5636534a309fe98499bb": "JR-0035"}
pid, due = sys.argv[1], sys.argv[2]
if pid not in ALLOW: print(f"[guard] REFUSED: {pid} is not allowlisted"); raise SystemExit(9)
if due != "2026-10-02T02:30:00Z": print(f"[guard] REFUSED: dueAt {due} is not the approved slot"); raise SystemExit(9)
q = ('mutation { editPost(input: { id: %s, dueAt: %s }) { '
     '... on PostActionSuccess { post { id status dueAt } } ... on MutationError { message } } }') % (json.dumps(pid), json.dumps(due))
print(f"[mutation] editPost episode={ALLOW[pid]} id={pid} dueAt={due} fields=id,dueAt")
r=urllib.request.Request(API,data=json.dumps({"query":q}).encode(),method="POST",
    headers={"Content-Type":"application/json","Authorization":f"Bearer {KEY}"})
try:
    with urllib.request.urlopen(r,timeout=90) as x: st,js=x.status,json.loads(x.read())
except urllib.error.HTTPError as e:
    print(f"[buffer] action=FAILED http={e.code} {e.read().decode()[:300]}"); raise SystemExit(6)
except Exception as e:
    print(f"[buffer] action=UNRESOLVED reason={type(e).__name__}; reconcile, do not retry"); raise SystemExit(7)
res=(js.get("data") or {}).get("editPost") or {}
if js.get("errors") or res.get("message"):
    print(f"[buffer] action=FAILED http={st} detail={json.dumps(js.get('errors') or res)[:400]}"); raise SystemExit(6)
print(f"[buffer] action=EDITED post={json.dumps(res.get('post'))}")
