#!/usr/bin/env python3
"""READ-ONLY: what PostMetric exposes, real metric values on sent JR posts, and the
metadata past YouTube posts were sent with. Mutates nothing."""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from probe import gql, fields, ORG, CH
from daily.redact import redact
pm = fields("PostMetric"); print("[type] PostMetric:", json.dumps(pm))
for t in set(v.lstrip("!") for v in pm.values()):
    f = fields(t)
    if f and t not in ("String", "Int", "Float", "Boolean", "DateTime"): print(f"[type] {t}:", json.dumps(f))
print("[type] PostMetadata:", json.dumps(fields("PostMetadata")))
for t in ("YoutubePostMetadata", "InstagramPostMetadata"): print(f"[type] {t}:", json.dumps(fields(t)))
def sub(t, depth=0):
    f = fields(t)
    if not f or "enum" in f or depth > 2: return ""
    parts = []
    for k, v in f.items():
        b = v.lstrip("!")
        if b in ("String", "Int", "Float", "Boolean", "DateTime", "ID") or "enum" in fields(b): parts.append(k)
        else:
            s = sub(b, depth + 1)
            if s: parts.append(f"{k}{{{s}}}")
    return " ".join(parts)
msel = sub("PostMetric")
print("[sel] metrics:", msel)
for name, cid in CH.items():
    q = ('query($o:OrganizationId!,$c:[ChannelId!]){ posts(first:50, input:{organizationId:$o, filter:{channelIds:$c, status:sent}})'
         '{ edges{ node{ id sentAt externalLink metricsUpdatedAt metrics{ %s } metadata{ ... on YoutubePostMetadata{ title categoryId privacy } } text } } } }' % msel)
    d = gql(q, {"o": ORG, "c": [cid]})
    if d.get("errors"):
        q2 = q.replace(" metadata{ ... on YoutubePostMetadata{ title categoryId privacy } }", "")
        print(f"[warn] {name} metadata select failed:", redact(json.dumps(d["errors"])[:300])); d = gql(q2, {"o": ORG, "c": [cid]})
    if d.get("errors"): print(f"[err] {name}", redact(json.dumps(d["errors"])[:400])); continue
    for e in d["data"]["posts"]["edges"]:
        n = e["node"]
        if not (n.get("text") or "").lstrip().startswith(("Jesus", "He ", "She ")): continue
        print(f"[m] {name} {n['id']} sent={n['sentAt']} link={bool(n.get('externalLink'))} mupd={n.get('metricsUpdatedAt')} meta={json.dumps(n.get('metadata'))[:120]} metrics={json.dumps(n.get('metrics'))[:400]}")
