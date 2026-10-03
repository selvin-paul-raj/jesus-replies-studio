"""Per-publication ledger and the 08:00 vs 20:30 slot test. Every platform publication is its own row.
A metric the platform does not expose through Buffer is written as "UNAVAILABLE", never 0."""
import datetime as dt
from statistics import median
from .analytics import parse
from .timing import IST

FIELDS = {"reach": ["reach"], "views": ["views"], "watch_time_avg": ["averageTimeWatched"],
          "watch_time_total": ["totalTimeWatched"], "shares": ["shares"], "saves": ["saves"],
          "likes": ["reactions", "likes"], "comments": ["comments"],
          "followers_or_subscribers_gained": ["follows", "freeSubscriptions"], "engagement_rate": ["engagementRate"]}


def pick(metrics, aliases):
    for a in aliases:
        if a in metrics:
            return metrics[a]
    return "UNAVAILABLE"


def slot_label(t_ist, test_slots):
    hm = t_ist.strftime("%H:%M")
    for s in test_slots:
        h, m = map(int, s.split(":"))
        target = t_ist.replace(hour=h, minute=m, second=0, microsecond=0)
        if abs((t_ist - target).total_seconds()) <= 15 * 60:
            return s
    return f"other ({hm})"


def build(rows, history, attrs, cfg):
    out = []
    for r in rows:
        if not (r["episode_id"] and r["status"] == "sent" and r["sent_at"]):
            continue
        t = parse(r["sent_at"]).astimezone(IST)
        a = attrs.get(r["episode_id"], {})
        h = history.get(f"{r['platform']}:{r['post_id']}", {}).get("checkpoints", {})
        cps = {}
        for c in ("24h", "72h", "168h"):
            if c in h:
                cps[c] = {k: pick(h[c]["metrics"], al) for k, al in FIELDS.items()}
                cps[c]["observed_age_hours"] = h[c]["observed_age_hours"]
            else:
                cps[c] = "NOT_YET" if (r["age_hours"] or 0) < int(c[:-1]) else "MISSED (no snapshot after this age)"
        out.append({"platform": r["platform"], "episode_id": r["episode_id"], "post_id": r["post_id"],
                    "publication_date": t.date().isoformat(), "publication_time": t.strftime("%H:%M"), "timezone": "Asia/Kolkata",
                    "slot": slot_label(t, cfg["initial_test_slots"]),
                    "theme": a.get("theme"), "hook_type": a.get("hook_type"), "emotion": a.get("emotion"),
                    "bible_theme": a.get("bible_theme"), "latest": {k: pick(r["metrics"], al) for k, al in FIELDS.items()},
                    "latest_age_hours": r["age_hours"], "checkpoints": cps, "permalink": r.get("external_link")})
    return sorted(out, key=lambda x: (x["publication_date"], x["publication_time"], x["platform"]))


def slot_test(ledger, cfg, min_n=7):
    a, b = cfg["initial_test_slots"]
    res = {"slots": [a, b], "decision_rule": f"7-day checkpoint medians per platform once each slot has >= {min_n} publications",
           "audience_activity": {"youtube": "UNAVAILABLE: 'When your viewers are on YouTube' is not exposed through Buffer; needs a YouTube Analytics connection",
                                 "instagram": "UNAVAILABLE: follower online-times are not exposed through Buffer; historical post performance used instead"},
           "platforms": {}}
    for p in sorted({l["platform"] for l in ledger}):
        arms = {s: [l for l in ledger if l["platform"] == p and l["slot"] == s and isinstance(l["checkpoints"]["168h"], dict)] for s in (a, b)}
        entry = {"n_7d": {s: len(v) for s, v in arms.items()}}
        if min(len(v) for v in arms.values()) < min_n:
            entry["verdict"] = "insufficient data"
        else:
            cmp = {}
            for f in ("reach", "views", "watch_time_avg", "shares", "saves", "comments", "likes", "engagement_rate"):
                vals = {s: [l["checkpoints"]["168h"][f] for l in v if l["checkpoints"]["168h"][f] != "UNAVAILABLE"] for s, v in arms.items()}
                if all(len(x) >= min_n for x in vals.values()):
                    cmp[f] = {s: median(x) for s, x in vals.items()}
            lead = {f: max(v, key=v.get) for f, v in cmp.items() if len(set(v.values())) > 1}
            entry.update(medians_7d=cmp, ahead_on=lead,
                         verdict="current evidence suggests " + ", ".join(f"{s} ahead on {f}" for f, s in lead.items()) if lead else "no difference observed")
        res["platforms"][p] = entry
    return res
