#!/usr/bin/env python3
"""READ-ONLY capability probe for the content OS. Mutates nothing.
Answers: what analytics a Post exposes, what YouTube metadata a post needs,
whether posts can be listed per channel (duplicate detection), and JR-0035's live status."""
import json, os, sys, urllib.request, urllib.error
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from daily.redact import redact
API = "https://api.buffer.com"; KEY = os.environ["BUFFER_API_KEY"]
CFG = json.load(open("config/publishing-rules.json"))
ORG = CFG.get("buffer", {}).get("organization_id") or os.environ.get("ORG", "")
CH = CFG.get("buffer", {}).get("channels", {})
def gql(q, v=None):
    r = urllib.request.Request(API, data=json.dumps({"query": q, "variables": v or {}}).encode(), method="POST",
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {KEY}"})
    try:
        with urllib.request.urlopen(r, timeout=90) as x: return json.loads(x.read())
    except urllib.error.HTTPError as e:
        try: return json.loads(e.read().decode()[:2000])
        except Exception: return {"errors": [{"message": f"HTTP {e.code}"}]}
def fields(t):
    d = gql('query($n:String!){ __type(name:$n){ kind fields{ name type{ name kind ofType{ name kind ofType{name} } } } inputFields{ name type{ name kind ofType{ name kind ofType{name} } } } enumValues{name} } }', {"n": t})
    tt = (d.get("data") or {}).get("__type") or {}
    out = {}
    for f in (tt.get("fields") or []) + (tt.get("inputFields") or []):
        ty = f["type"]; nm = ty.get("name") or (ty.get("ofType") or {}).get("name") or ((ty.get("ofType") or {}).get("ofType") or {}).get("name")
        out[f["name"]] = ("!" if ty["kind"] == "NON_NULL" else "") + str(nm)
    if tt.get("enumValues"): out = {"enum": [e["name"] for e in tt["enumValues"]]}
    return out
for t in ("Post", "PostStatus", "PostInputMetaData", "YoutubePostMetadataInput", "PostsInput", "PostsFiltersInput", "Channel"):
    print(f"[type] {t}:", redact(json.dumps(fields(t))))
for t in ("PostStatistics", "PostMetrics", "PostAnalytics", "Statistics", "YoutubePrivacy", "YoutubeCategory"):
    f = fields(t)
    if f: print(f"[type] {t}:", json.dumps(f))
if ORG:
    for name, cid in CH.items():
        q = 'query($o:OrganizationId!,$c:[ChannelId!]){ posts(first:50, input:{organizationId:$o, filter:{channelIds:$c}}){ edges{ node{ id status dueAt sentAt channelService text } } } }'
        d = gql(q, {"o": ORG, "c": [cid]})
        if d.get("errors"):
            print(f"[list] {name} ERR", redact(json.dumps(d["errors"])[:500])); continue
        edges = d["data"]["posts"]["edges"]
        print(f"[list] {name} returned={len(edges)}")
        for e in edges:
            n = e["node"]; head = (n.get("text") or "")[:60].replace("\n", " ")
            print(f"[list] {name} {n['id']} {n['status']} due={n.get('dueAt')} sent={n.get('sentAt')} | {head}")
