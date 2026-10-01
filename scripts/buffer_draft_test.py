#!/usr/bin/env python3
"""ONE controlled Buffer mutation: create a DRAFT for a single episode on Instagram.

Order of operations, fail-closed at every step:
  1. introspect CreatePostInput + the mode/status enums (read-only) so the draft
     field is DISCOVERED, never guessed;
  2. if no draft capability exists, stop BEFORE mutating;
  3. send exactly one createPost mutation;
  4. read the post back by id and report its real state.

Never prints the API key. Never retries a mutation: an unreadable outcome is
reported UNRESOLVED for human reconciliation.
"""
import json, os, sys, urllib.error, urllib.request

API = "https://api.buffer.com"
KEY = os.environ["BUFFER_API_KEY"]
CHANNEL = os.environ["BUFFER_INSTAGRAM_CHANNEL_ID"]
EID = sys.argv[1]
THUMB_MS = 1500

def gql(query, tag):
    body = json.dumps({"query": query}).encode()
    req = urllib.request.Request(API, data=body, method="POST", headers={
        "Content-Type": "application/json", "Authorization": f"Bearer {KEY}"})
    try:
        with urllib.request.urlopen(req, timeout=90) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        raw = e.read().decode()[:400]
        try:
            return e.code, json.loads(raw)
        except Exception:
            return e.code, {"_raw": raw}
    except Exception as e:
        print(f"[buffer] {tag} action=UNRESOLVED reason=request-did-not-complete: {type(e).__name__}")
        raise SystemExit(2)

# ---------- 1. introspection, read-only ----------
INTRO = """
query { __type(name: "CreatePostInput") { inputFields { name type { name kind ofType { name kind } } } } }
"""
st, js = gql(INTRO, "introspect")
print(f"[auth] introspection HTTP {st}")
if st == 401 or (js.get("errors") and "auth" in json.dumps(js["errors"]).lower()):
    print("[auth] FAILED: Buffer rejected the credential. Key in GitHub Secrets is not accepted.")
    print("[auth] detail:", json.dumps(js.get("errors") or js)[:300])
    raise SystemExit(3)
t = (js.get("data") or {}).get("__type")
if not t:
    print("[introspect] no CreatePostInput type returned:", json.dumps(js)[:400]); raise SystemExit(4)
fields = {f["name"]: (f["type"].get("name") or (f["type"].get("ofType") or {}).get("name")) for f in t["inputFields"]}
print("[introspect] CreatePostInput fields:", json.dumps(fields, sort_keys=True))

draft_field = None
for cand in ("saveToDraft", "isDraft", "draft", "status", "mode"):
    if cand in fields:
        enum = fields[cand]
        if cand in ("saveToDraft", "isDraft", "draft"):
            draft_field = (cand, "true"); break
        st2, js2 = gql(f'query {{ __type(name: "{enum}") {{ enumValues {{ name }} }} }}', "enum")
        vals = [v["name"] for v in (((js2.get("data") or {}).get("__type") or {}).get("enumValues") or [])]
        print(f"[introspect] {cand}:{enum} values={vals}")
        hit = [v for v in vals if "draft" in v.lower()]
        if hit:
            draft_field = (cand, hit[0]); break
if not draft_field:
    print("[draft] STOP BEFORE MUTATION: no draft capability found on CreatePostInput.")
    raise SystemExit(5)
name, value = draft_field
print(f"[draft] using {name}: {value}")

# ---------- 2. payload ----------
pkg = json.load(open(f"generated/{EID}.package.json"))
man = {r["episode_id"]: r for r in json.load(open("generated/release-manifest.json"))}
url = man[EID]["public_url"]
assert url.startswith("https://"), "asset URL must be public https"
tags = pkg["instagram_hashtags"]
tags = " ".join(tags) if isinstance(tags, list) else tags
text = pkg["instagram_caption"] + "\n\n" + tags

# discover Post fields so the selection set cannot invalidate the mutation
st, pj = gql('query { __type(name: "Post") { fields { name } } }', "postfields")
pfields = [f["name"] for f in ((((pj.get("data") or {}).get("__type")) or {}).get("fields") or [])]
want = [f for f in ("id","status","dueAt","text","channelId","mode","schedulingType","isDraft","draft","via","createdAt") if f in pfields]
if "id" not in want: want = ["id"]
print("[introspect] Post fields:", json.dumps(pfields))
print("[introspect] selecting:", want)
SEL = " ".join(want)

MUT = f"""
mutation {{
  createPost(input: {{
    text: {json.dumps(text)}
    channelId: {json.dumps(CHANNEL)}
    saveToDraft: true
    schedulingType: automatic
    mode: customScheduled
    dueAt: "2026-12-31T00:00:00Z"
    assets: [{{ video: {{ url: {json.dumps(url)}, metadata: {{ thumbnailOffset: {THUMB_MS} }} }} }}]
    metadata: {{ instagram: {{ type: reel, shouldShareToFeed: true }} }}
  }}) {{
    ... on PostActionSuccess {{ post {{ {SEL} }} }}
    ... on MutationError {{ message }}
  }}
}}
"""
print(f"[mutation] episode={EID} channel=instagram asset={url}")
st, js = gql(MUT, "createPost")
res = (js.get("data") or {}).get("createPost") or {}
if js.get("errors") or res.get("message") or st >= 400:
    print(f"[buffer] action=FAILED http={st} detail={json.dumps(js.get('errors') or res)[:400]}")
    raise SystemExit(6)
post = res.get("post") or {}
pid = post.get("id")
if not pid:
    print("[buffer] action=UNRESOLVED reason=no-post-id-in-success-response; reconcile before any retry")
    raise SystemExit(7)
print(f"[buffer] action=CREATED post_id={pid} post={json.dumps(post)}")

# ---------- 3. read it back ----------
st, qj = gql('query { __schema { queryType { fields { name args { name } } } } } ', "qfields")
qfields = {f["name"]: [a["name"] for a in f["args"]]
           for f in ((((qj.get("data") or {}).get("__schema") or {}).get("queryType") or {}).get("fields") or [])}
print("[verify] query fields:", json.dumps(sorted(qfields)))
verified = None
if "post" in qfields and "id" in qfields["post"]:
    st, js = gql(f'query {{ post(id: {json.dumps(pid)}) {{ {SEL} }} }}', "verify")
    verified = (js.get("data") or {}).get("post")
    print(f"[verify] HTTP {st} {json.dumps(verified or js.get('errors') or js)[:700]}")
else:
    print("[verify] NOT_VERIFIED: no post(id:) query field on this schema")

json.dump({"episode": EID, "post_id": pid, "status": post.get("status"), "asset_url": url,
           "draft_field": f"{name}={value}", "verify": verified},
          open("buffer-draft-result.json", "w"), indent=2)
