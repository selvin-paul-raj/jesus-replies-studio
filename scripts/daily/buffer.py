"""Buffer GraphQL client. Transport is injectable so tests never touch the network.

Outcome classes for a mutation:
  OK          - success response WITH a post id (still must be read back)
  REJECTED    - a GraphQL/MutationError response; no object is expected to exist
  NO_POST_ID  - success shape but no post id; must be reconciled before any retry
  UNKNOWN     - the request did not complete; never retried automatically
"""
import json, os, urllib.error, urllib.request
from .redact import redact

POST_BASE = ["id", "status", "dueAt", "text", "shareMode", "schedulingType", "channelService"]
POST_OPTIONAL = ["sentAt", "isCustomScheduled", "createdAt"]


def http_transport(api, key):
    def send(query):
        req = urllib.request.Request(api, data=json.dumps({"query": query}).encode(), method="POST",
                                     headers={"Content-Type": "application/json",
                                              "Authorization": f"Bearer {key}"})
        try:
            with urllib.request.urlopen(req, timeout=90) as r:
                return r.status, json.loads(r.read())
        except urllib.error.HTTPError as e:
            raw = e.read().decode()[:400]
            try:
                return e.code, json.loads(raw)
            except Exception:
                return e.code, {"_raw": raw}
    return send


class Outcome:
    def __init__(self, kind, post=None, detail=""):
        self.kind, self.post, self.detail = kind, post, redact(detail)[:400]

    def __repr__(self):
        return f"Outcome({self.kind}, post_id={(self.post or {}).get('id')}, {self.detail!r})"


class Buffer:
    def __init__(self, transport, channel_id=None, rules=None):
        self.send, self.channel_id = transport, channel_id
        self.rules = rules or {}
        self._post_fields = None

    @classmethod
    def from_env(cls, rules):
        key = os.environ.get("BUFFER_API_KEY")
        if not key:
            raise RuntimeError("BUFFER_API_KEY not available to this run")
        return cls(http_transport(rules["buffer"]["api"], key),
                   os.environ.get("BUFFER_INSTAGRAM_CHANNEL_ID"), rules)

    # ---------- reads ----------
    def post_fields(self):
        if self._post_fields is None:
            st, js = self.send('query { __type(name: "Post") { fields { name } } }')
            names = {f["name"] for f in (((js.get("data") or {}).get("__type") or {}).get("fields") or [])}
            self._post_fields = [f for f in POST_BASE + POST_OPTIONAL if f in names] or ["id", "status"]
        return self._post_fields

    def read(self, post_id):
        """Returns (post|None, detail). None + detail 'NOT_FOUND' or an error string."""
        sel = " ".join(self.post_fields())
        q = ('query { post(input: { id: %s }) { %s assets { ... on VideoAsset { source '
             'video { durationMs thumbnailOffset } } } } }') % (json.dumps(post_id), sel)
        try:
            st, js = self.send(q)
        except Exception as e:
            return None, f"UNREADABLE {type(e).__name__}"
        post = (js.get("data") or {}).get("post")
        if post:
            a = (post.get("assets") or [{}])[0] or {}
            post["_asset_source"] = a.get("source")
            post["_duration_ms"] = (a.get("video") or {}).get("durationMs")
            post["_has_sent_at_field"] = "sentAt" in self.post_fields()
            return post, "OK"
        if js.get("errors") and "not found" in json.dumps(js["errors"]).lower():
            return None, "NOT_FOUND"
        return None, f"UNREADABLE http={st} {redact(json.dumps(js))[:200]}"

    # ---------- mutations ----------
    def _mutate(self, name, q):
        try:
            st, js = self.send(q)
        except Exception as e:
            return Outcome("UNKNOWN", detail=f"request did not complete: {type(e).__name__}")
        res = (js.get("data") or {}).get(name) or {}
        if js.get("errors") or res.get("message") or st >= 400:
            return Outcome("REJECTED", detail=f"http={st} {json.dumps(js.get('errors') or res)}")
        post = res.get("post") or {}
        if not post.get("id"):
            return Outcome("NO_POST_ID", detail=f"http={st} success shape without id")
        return Outcome("OK", post=post)

    def _video(self, url):
        off = self.rules.get("buffer", {}).get("thumbnail_offset_ms", 1500)
        return f'[{{ video: {{ url: {json.dumps(url)}, metadata: {{ thumbnailOffset: {off} }} }} }}]'

    def create_draft(self, text, url, due_at):
        if not self.channel_id:
            return Outcome("REJECTED", detail="no Instagram channel id available")
        q = f"""mutation {{ createPost(input: {{
  text: {json.dumps(text)}
  channelId: {json.dumps(self.channel_id)}
  saveToDraft: true
  schedulingType: automatic
  mode: customScheduled
  dueAt: {json.dumps(due_at)}
  assets: {self._video(url)}
  metadata: {{ instagram: {{ type: reel, shouldShareToFeed: true }} }}
}}) {{ ... on PostActionSuccess {{ post {{ id status dueAt }} }} ... on MutationError {{ message }} }} }}"""
        return self._mutate("createPost", q)

    def schedule(self, post_id, text, url, due_at):
        """Whole-post edit (Buffer validates edits as whole posts); only dueAt and
        saveToDraft:false differ from the draft."""
        q = f"""mutation {{ editPost(input: {{
  id: {json.dumps(post_id)}
  dueAt: {json.dumps(due_at)}
  text: {json.dumps(text)}
  mode: customScheduled
  schedulingType: automatic
  assets: {self._video(url)}
  metadata: {{ instagram: {{ type: reel, shouldShareToFeed: true }} }}
  saveToDraft: false
}}) {{ ... on PostActionSuccess {{ post {{ id status dueAt }} }} ... on MutationError {{ message }} }} }}"""
        return self._mutate("editPost", q)
