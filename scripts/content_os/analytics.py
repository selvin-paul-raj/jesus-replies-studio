"""Account analytics from Buffer (the only metrics source wired). Never invents a value:
a metric Buffer did not return is absent, and availability is recorded per platform."""
import re, datetime as dt
from statistics import median

EXCLUDE_PREFIXES = ("\u2728 Today's blessing",)
BUFFER_METRIC_TYPES = ["averageTimeWatched", "clicks", "comments", "engagementRate", "follows", "freeSubscriptions",
                       "impressions", "likes", "paidSubscriptions", "postCount", "quotes", "reach", "reactions",
                       "reposts", "saves", "shares", "totalTimeWatched", "viewers", "views"]
NO_SOURCE = ["retention_curve", "early_drop_off", "non_follower_reach", "discovery_source", "profile_visits",
             "channel_visits", "swipe_away_rate", "engaged_views", "average_percentage_watched"]


def parse(ts):
    return dt.datetime.fromisoformat(ts.replace("Z", "+00:00")) if ts else None


def tokens(s):
    return set(re.findall(r"[a-z']+", (s or "").lower())) - {"jesus", "i", "the", "a", "to", "and", "my", "you", "me", "it", "is"}


def norm_text(s):
    return re.sub(r"\s+", " ", (s or "").replace("\u2026", "...")).strip().lower()


def match_episode(post, eps, pkgs):
    text = post.get("text") or ""
    if text.lstrip().startswith(EXCLUDE_PREFIXES):
        return None, 0.0
    nt = norm_text(text)
    for eid, pk in pkgs.items():
        for k in ("instagram_caption", "youtube_description"):
            c = norm_text(pk.get(k))
            if c and nt[:120] == c[:120]:
                return eid, 1.0
    head = " ".join(text.strip().splitlines()[:1])
    best, score = None, 0.0
    ht = tokens(head)
    for eid, ep in eps.items():
        hook = next((l.get("text", "") for l in ep.get("lines", []) if l.get("speaker") == "person"), "")
        for cand in (hook, ep.get("title", "")):
            ct = tokens(cand)
            if ht and ct:
                j = len(ht & ct) / len(ht | ct)
                if j > score:
                    best, score = eid, j
    return (best, round(score, 3)) if score >= 0.5 else (None, round(score, 3))


def checkpoint(age_h, cps):
    hit = [c for c in cps if age_h >= c]
    return f"{max(hit)}h" if hit else "pre-24h"


def snapshot(posts_by_platform, eps, pkgs, now, cps=(24, 72, 168)):
    rows = []
    for platform, posts in posts_by_platform.items():
        for p in posts or []:
            eid, sc = match_episode(p, eps, pkgs)
            sent = parse(p.get("sentAt"))
            age = round((now - sent).total_seconds() / 3600, 1) if sent else None
            rows.append({"platform": platform, "post_id": p["id"], "status": p.get("status"),
                         "due_at": p.get("dueAt"), "sent_at": p.get("sentAt"), "external_link": p.get("externalLink"),
                         "asset": p.get("_asset"), "episode_id": eid, "match_score": sc,
                         "kind": "daily_bible" if (p.get("text") or "").lstrip().startswith(EXCLUDE_PREFIXES) else "jesus_replies_or_other",
                         "metrics": p.get("_metrics") or {}, "metrics_updated_at": p.get("metricsUpdatedAt"),
                         "youtube_category": ((p.get("metadata") or {}).get("category") or {}).get("categoryId"),
                         "age_hours": age, "checkpoint": checkpoint(age, cps) if age is not None else None})
    return rows


def availability(rows):
    out = {}
    for platform in sorted({r["platform"] for r in rows}):
        sent = [r for r in rows if r["platform"] == platform and r["status"] == "sent"]
        seen = sorted({k for r in sent for k in r["metrics"]})
        out[platform] = {
            "AVAILABLE": seen,
            "UNAVAILABLE_VIA_BUFFER": [m for m in BUFFER_METRIC_TYPES if m not in seen],
            "UNAVAILABLE_NO_SOURCE": NO_SOURCE,
            "UNKNOWN": ["follower_or_subscriber_totals", "audience_activity_by_hour"],
            "sent_posts_with_metrics": sum(1 for r in sent if r["metrics"]),
            "sent_posts": len(sent),
        }
    return out


def update_history(history, rows, cps=(24, 72, 168)):
    added = 0
    for r in rows:
        if r["status"] != "sent" or r["age_hours"] is None or not r["metrics"]:
            continue
        key = f"{r['platform']}:{r['post_id']}"
        h = history.setdefault(key, {"episode_id": r["episode_id"], "platform": r["platform"], "sent_at": r["sent_at"], "checkpoints": {}})
        for c in cps:
            if r["age_hours"] >= c and f"{c}h" not in h["checkpoints"]:
                h["checkpoints"][f"{c}h"] = {"metrics": r["metrics"], "observed_age_hours": r["age_hours"],
                                              "note": "first snapshot after the checkpoint; exact-time capture not possible"}
                added += 1
    return added


def pick_metric(rows, aliases):
    for a in aliases:
        have = [r for r in rows if a in r["metrics"]]
        if rows and len(have) >= max(1, len(rows) // 2):
            return a
    return None


def summarize(rows, cfg):
    jr = [r for r in rows if r["episode_id"] and r["status"] == "sent"]
    out = {}
    for platform in sorted({r["platform"] for r in jr}):
        pr = [r for r in jr if r["platform"] == platform]
        dims = {}
        for dim, aliases in cfg["metric_priority"]:
            m = pick_metric(pr, aliases)
            vals = [r["metrics"][m] for r in pr if m and m in r["metrics"]]
            dims[dim] = {"metric": m, "n": len(vals), "median": median(vals) if vals else None,
                         "max": max(vals) if vals else None} if m else {"metric": None, "status": "UNAVAILABLE"}
        out[platform] = {"jr_posts_sent": len(pr), "dimensions": dims}
    return out
