#!/usr/bin/env python3
"""READ-ONLY. Fetches one Buffer post by id and prints its real state. No mutations."""
import json, os, sys, urllib.error, urllib.request
API="https://api.buffer.com"; KEY=os.environ["BUFFER_API_KEY"]; PID=sys.argv[1]

def gql(q):
    r=urllib.request.Request(API,data=json.dumps({"query":q}).encode(),method="POST",
        headers={"Content-Type":"application/json","Authorization":f"Bearer {KEY}"})
    try:
        with urllib.request.urlopen(r,timeout=90) as x: return x.status,json.loads(x.read())
    except urllib.error.HTTPError as e:
        raw=e.read().decode()[:400]
        try: return e.code,json.loads(raw)
        except Exception: return e.code,{"_raw":raw}

st,js=gql('query { __schema { queryType { fields { name args { name type { name kind ofType { name } } } } } } }')
f=[x for x in ((((js.get("data") or {}).get("__schema") or {}).get("queryType") or {}).get("fields") or []) if x["name"]=="post"]
print("[schema] Query.post args:", json.dumps([{a["name"]:(a["type"].get("name") or (a["type"].get("ofType") or {}).get("name"))} for a in f[0]["args"]]) if f else "ABSENT")
arg=f[0]["args"][0]["name"] if f and f[0]["args"] else None
if not arg: print("[verify] NOT_VERIFIED: Query.post takes no id-like argument"); raise SystemExit(3)

st,aj=gql('query { __type(name: "VideoAsset") { fields { name } } }')
vfields=[x["name"] for x in ((((aj.get("data") or {}).get("__type")) or {}).get("fields") or [])]
print("[schema] VideoAsset fields:", json.dumps(vfields))
asset_sel = ("assets { ... on VideoAsset { " + " ".join([v for v in ("url","thumbnailUrl","duration","size") if v in vfields]) + " } }") if vfields else ""

q=f'query {{ post({arg}: {json.dumps(PID)}) {{ id status dueAt text schedulingType shareMode isCustomScheduled notificationStatus via createdAt channelService {asset_sel} }} }}'
st,js=gql(q)
post=(js.get("data") or {}).get("post")
print(f"[verify] HTTP {st}")
print("[verify]", json.dumps(post if post is not None else (js.get("errors") or js))[:1500])
