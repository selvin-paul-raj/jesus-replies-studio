#!/usr/bin/env python3
"""READ-ONLY. Names the mutations a later scheduling step would need, and lists
existing posts on the Instagram channel so conflicts can be seen. Mutates nothing."""
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

st,js=gql('query { __schema { mutationType { fields { name args { name type { name kind ofType { name } } } } } } }')
mf=(((js.get("data") or {}).get("__schema") or {}).get("mutationType") or {}).get("fields") or []
print("[schema] mutations:", json.dumps(sorted(f["name"] for f in mf)))
for want in ("editPost","deletePost","movePostInQueue"):
    hit=[f for f in mf if f["name"]==want]
    if hit:
        a=hit[0]["args"][0]
        tn=a["type"].get("name") or (a["type"].get("ofType") or {}).get("name")
        st,ij=gql('query { __type(name: "%s") { inputFields { name type { name kind ofType { name } } } } }' % tn)
        fl={x["name"]:(x["type"].get("name") or (x["type"].get("ofType") or {}).get("name")) for x in ((((ij.get("data") or {}).get("__type")) or {}).get("inputFields") or [])}
        print(f"[schema] {want}({a['name']}: {tn}) ->", json.dumps(fl))

st,ij=gql('query { __type(name: "PostsInput") { inputFields { name type { name kind ofType { name } } } } }')
pin={x["name"]:(x["type"].get("name") or (x["type"].get("ofType") or {}).get("name")) for x in ((((ij.get("data") or {}).get("__type")) or {}).get("inputFields") or [])}
print("[schema] PostsInput:", json.dumps(pin))
key=next((k for k in ("channelIds","channelId") if k in pin), None)
val=f'[{json.dumps(CH)}]' if key=="channelIds" else json.dumps(CH)
st,js=gql(f'query {{ posts(first: 25, input: {{ {key}: {val} }}) {{ edges {{ node {{ id status dueAt createdAt }} }} }} }}')
d=(js.get("data") or {}).get("posts")
if d is None: print("[list] HTTP",st,json.dumps(js.get("errors") or js)[:400])
else:
    for e in d.get("edges",[]):
        n=e["node"]; print(f"[list] id={n['id']} status={n['status']} due={n.get('dueAt')} created={n.get('createdAt')}")
    print(f"[list] total_returned={len(d.get('edges',[]))}")
