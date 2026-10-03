"""Buffer client for the content OS. Reads are retry-safe; mutations are never retried here.
Mutation outcome classes come from daily.buffer.Outcome (OK, REJECTED, NO_POST_ID, UNKNOWN)."""
import json, os
from daily.buffer import http_transport, Outcome
from daily.redact import redact

NODE_FULL = ("id status dueAt sentAt createdAt channelId channelService text externalLink metricsUpdatedAt "
             "metrics { type value unit } assets { ... on VideoAsset { source video { durationMs } } } "
             "metadata { ... on YoutubePostMetadata { title privacy madeForKids category { categoryId title } } }")
NODE_MIN = "id status dueAt sentAt channelId channelService text externalLink assets { ... on VideoAsset { source } }"


def norm_post(n):
    a = (n.get("assets") or [{}])[0] or {}
    n["_asset"] = a.get("source")
    n["_duration_ms"] = (a.get("video") or {}).get("durationMs")
    n["_metrics"] = {m["type"]: m["value"] for m in (n.get("metrics") or []) if m.get("type")}
    return n


class Buffer:
    def __init__(self, send, cfg):
        self.send, self.cfg = send, cfg

    @classmethod
    def from_env(cls, cfg):
        key = os.environ.get("BUFFER_API_KEY")
        if not key:
            raise RuntimeError("BUFFER_API_KEY not available to this run")
        return cls(http_transport(cfg["buffer"]["api"], key), cfg)

    def channel(self, platform):
        return self.cfg["buffer"]["channels"][platform]

    def _read(self, q_for):
        for node in (NODE_FULL, NODE_MIN):
            try:
                st, js = self.send(q_for(node))
            except Exception as e:
                return None, f"UNREADABLE {type(e).__name__}"
            if js.get("errors"):
                if node is NODE_FULL and "GRAPHQL_VALIDATION_FAILED" in json.dumps(js["errors"]):
                    continue
                if "not found" in json.dumps(js["errors"]).lower():
                    return None, "NOT_FOUND"
                return None, "UNREADABLE " + redact(json.dumps(js["errors"]))[:300]
            return js.get("data") or {}, "OK" if node is NODE_FULL else "OK_MIN"
        return None, "UNREADABLE"

    def list_posts(self, platform):
        org, ch = self.cfg["buffer"]["organization_id"], self.channel(platform)
        data, d = self._read(lambda node: 'query { posts(first: 100, input: { organizationId: %s, filter: { channelIds: [%s] } }) { edges { node { %s } } } }'
                             % (json.dumps(org), json.dumps(ch), node))
        if data is None:
            return None, d
        posts = [norm_post(e["node"]) for e in ((data.get("posts") or {}).get("edges") or [])]
        return posts, ("TRUNCATED" if len(posts) >= 100 else d)

    def read(self, post_id):
        data, d = self._read(lambda node: 'query { post(input: { id: %s }) { %s } }' % (json.dumps(post_id), node))
        if data is None:
            return None, d
        p = data.get("post")
        return (norm_post(p), "OK") if p else (None, "NOT_FOUND")

    # ---------- mutations (single attempt, caller classifies) ----------
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
        off = self.cfg.get("buffer", {}).get("thumbnail_offset_ms", 1500)
        return f'[{{ video: {{ url: {json.dumps(url)}, metadata: {{ thumbnailOffset: {off} }} }} }}]'

    def _meta(self, platform, yt):
        if platform == "instagram":
            return "{ instagram: { type: reel, shouldShareToFeed: true } }"
        return ("{ youtube: { title: %s, privacy: %s, madeForKids: %s, notifySubscribers: %s, categoryId: %s } }"
                % (json.dumps(yt["title"]), yt["privacy"], str(yt["made_for_kids"]).lower(),
                   str(yt["notify_subscribers"]).lower(), json.dumps(yt["category_id"])))

    def create_scheduled(self, platform, text, url, due_at, yt=None):
        q = f"""mutation {{ createPost(input: {{
  text: {json.dumps(text)}
  channelId: {json.dumps(self.channel(platform))}
  saveToDraft: false
  schedulingType: automatic
  mode: customScheduled
  dueAt: {json.dumps(due_at)}
  assets: {self._video(url)}
  metadata: {self._meta(platform, yt)}
}}) {{ ... on PostActionSuccess {{ post {{ id status dueAt }} }} ... on MutationError {{ message }} }} }}"""
        return self._mutate("createPost", q)

    def schedule_draft(self, post_id, platform, text, url, due_at, yt=None):
        """Whole-post edit (Buffer validates edits as whole posts). Only dueAt and saveToDraft differ."""
        q = f"""mutation {{ editPost(input: {{
  id: {json.dumps(post_id)}
  dueAt: {json.dumps(due_at)}
  text: {json.dumps(text)}
  mode: customScheduled
  schedulingType: automatic
  assets: {self._video(url)}
  metadata: {self._meta(platform, yt)}
  saveToDraft: false
}}) {{ ... on PostActionSuccess {{ post {{ id status dueAt }} }} ... on MutationError {{ message }} }} }}"""
        return self._mutate("editPost", q)
