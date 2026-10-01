#!/usr/bin/env python3
"""READ-ONLY. Lists posts on one channel so orphans can be detected. No mutations."""
import json, os, urllib.error, urllib.request
API="https://api.buffer.com"; KEY=os.environ["BUFFER_API_KEY"]; CH=os.environ["BUFFER_INSTAGRAM_CHANNEL_ID"]
def gql(q):
    r=urllib.request.Request(API,data=json.dumps({"query":q}).encode(),method="POST",
        headers={"Content-Type":"application/json","Authorization":f"Bearer {KEY}"})
    try:
        with urllib.request.urlopen(r,timeout=90) as x: return x.status,json.loads(x.read())
    except urllib.error.HTTPError as e:
        raw=e.read().decode()[:600]
        try: return e.code,json.loads(raw)
        except Exception: return e.code,{"_raw":raw}
st,js=gql('query { __schema { queryType { fields { name args { name type { name kind ofType { name } } } } } } }')
f=[x for x in ((((js.get("data") or {}).get("__schema") or {}).get("queryType") or {}).get("fields") or []) if x["name"]=="posts"]
print("[schema] Query.posts args:", json.dumps([{a["name"]:(a["type"].get("name") or (a["type"].get("ofType") or {}).get("name"))} for a in (f[0]["args"] if f else [])]))
argname=f[0]["args"][0]["name"]; argtype=f[0]["args"][0]["type"].get("name") or (f[0]["args"][0]["type"].get("ofType") or {}).get("name")
st,ij=gql('query { __type(name: "%s") { inputFields { name type { name kind ofType { name } } } } }' % argtype)
infields={x["name"]:(x["type"].get("name") or (x["type"].get("ofType") or {}).get("name")) for x in ((((ij.get("data") or {}).get("__type")) or {}).get("inputFields") or [])}
print("[schema]", argtype, json.dumps(infields))
chkey=next((k for k in ("channelIds","channelId","channels") if k in infields), None)
val=f'[{json.dumps(CH)}]' if chkey and chkey.endswith("s") else json.dumps(CH)
inner=f"{chkey}: {val}" if chkey else ""
st,js=gql(f'query {{ posts({argname}: {{ {inner} }}) {{ edges {{ node {{ id status createdAt dueAt assets {{ ... on VideoAsset {{ source }} }} }} }} }} }}')
data=(js.get("data") or {}).get("posts")
if data is None:
    print("[list] HTTP", st, json.dumps(js.get("errors") or js)[:600]); raise SystemExit(0)
for e in data.get("edges", []):
    n=e["node"]; src=((n.get("assets") or [{}])[0] or {}).get("source")
    print(f"[list] id={n['id']} status={n['status']} created={n.get('createdAt')} due={n.get('dueAt')} asset={(src or '').split('/')[-1]}")
