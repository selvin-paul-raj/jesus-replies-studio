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
        raw=e.read().decode()[:600]
        try: return e.code,json.loads(raw)
        except Exception: return e.code,{"_raw":raw}

def tfields(name):
    st,js=gql('query { __type(name: "%s") { kind fields { name type { name kind ofType { name } } } inputFields { name type { name kind ofType { name } } } } }' % name)
    t=((js.get("data") or {}).get("__type")) or {}
    out={}
    for key in ("fields","inputFields"):
        for f in (t.get(key) or []):
            out[f["name"]]=f["type"].get("name") or (f["type"].get("ofType") or {}).get("name")
    return out

pin=tfields("PostInput")
print("[schema] PostInput:", json.dumps(pin))
va=tfields("VideoAsset")
print("[schema] VideoAsset:", json.dumps(va))
vid=tfields(va.get("video") or "")
print("[schema] Video:", json.dumps(vid))

idkey = "id" if "id" in pin else (list(pin)[0] if pin else None)
if not idkey:
    print("[verify] NOT_VERIFIED: PostInput has no fields"); raise SystemExit(3)

scalar = lambda d: [k for k,v in d.items() if v in ("String","Int","Float","Boolean","ID","DateTime","URL")]
vsel = " ".join(scalar(vid)) if vid else ""
asel = " ".join([k for k in ("id","mimeType","type","source","thumbnail") if k in va]) + (f" video {{ {vsel} }}" if vsel else "")
q = f'query {{ post(input: {{ {idkey}: {json.dumps(PID)} }}) {{ id status dueAt text schedulingType shareMode isCustomScheduled notificationStatus via createdAt channelService assets {{ ... on VideoAsset {{ {asel} }} }} }} }}'
st,js=gql(q)
post=(js.get("data") or {}).get("post")
print(f"[verify] HTTP {st}")
print("[verify]", json.dumps(post if post is not None else (js.get("errors") or js))[:2000])
