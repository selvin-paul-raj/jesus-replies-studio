#!/usr/bin/env python3
"""READ-ONLY. Confirms both JR drafts exist and prints EditPostInput nullability."""
import json, os, urllib.error, urllib.request
API="https://api.buffer.com"; KEY=os.environ["BUFFER_API_KEY"]
POSTS={"JR-0035":"6abe5636534a309fe98499bb","JR-0036":"6abe5dab0c33e408f7a9414b"}
def gql(q):
    r=urllib.request.Request(API,data=json.dumps({"query":q}).encode(),method="POST",
        headers={"Content-Type":"application/json","Authorization":f"Bearer {KEY}"})
    try:
        with urllib.request.urlopen(r,timeout=90) as x: return x.status,json.loads(x.read())
    except urllib.error.HTTPError as e:
        return e.code,{"_raw":e.read().decode()[:400]}
st,js=gql('query { __type(name: "EditPostInput") { inputFields { name type { kind name ofType { kind name } } } } }')
for f in js["data"]["__type"]["inputFields"]:
    t=f["type"]; req=t["kind"]=="NON_NULL"
    print(f"[schema] EditPostInput.{f['name']}: {(t.get('name') or (t.get('ofType') or {}).get('name'))}{' REQUIRED' if req else ''}")
for ep,pid in POSTS.items():
    st,js=gql('query { post(input: { id: %s }) { id status dueAt shareMode schedulingType text assets { ... on VideoAsset { source } } } }' % json.dumps(pid))
    p=(js.get("data") or {}).get("post")
    if not p: print(f"[draft] {ep} MISSING http={st} {json.dumps(js)[:300]}"); continue
    print(f"[draft] {ep} id={p['id']} status={p['status']} due={p['dueAt']} mode={p['shareMode']} sched={p['schedulingType']} asset={((p.get('assets') or [{}])[0] or {}).get('source','').split('/')[-1]} textlen={len(p['text'])}")
