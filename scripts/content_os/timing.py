"""Timing engine. Own-account evidence first; external research is only a secondary note.
With thin evidence it returns test slots labelled experimental, never 'best time'."""
import datetime as dt
from statistics import median
from .analytics import parse, pick_metric

IST = dt.timezone(dt.timedelta(hours=5, minutes=30))
WINDOWS = [(6, 9), (9, 12), (12, 15), (15, 18), (18, 21), (21, 24)]


def window_of(hour):
    for a, b in WINDOWS:
        if a <= hour < b:
            return f"{a:02d}:00-{b:02d}:00"
    return "00:00-06:00"


def analyse(rows, cfg, min_age_h=168):
    out = {}
    for platform in sorted({r["platform"] for r in rows}):
        pr = [r for r in rows if r["platform"] == platform and r["episode_id"] and r["status"] == "sent"
              and (r["age_hours"] or 0) >= min_age_h]
        aliases = []
        for dim, al in cfg["metric_priority"]:
            if dim in ("reach", "views", "likes"):
                aliases += al
        m = pick_metric(pr, aliases)
        buckets = {}
        for r in pr:
            if m in r["metrics"]:
                h = parse(r["sent_at"]).astimezone(IST).hour
                buckets.setdefault(window_of(h), []).append(r["metrics"][m])
        out[platform] = {"metric": m, "posts_compared": sum(len(v) for v in buckets.values()),
                         "windows": {k: {"n": len(v), "median": median(v)} for k, v in sorted(buckets.items())}}
    return out


def confidence(n_window, n_total):
    if n_window >= 5 and n_total >= 20:
        return "medium"
    if n_window >= 3:
        return "low"
    return "insufficient"


def recommend(rows, cfg):
    an = analyse(rows, cfg)
    tz = cfg["timezone"]
    ranked = {}
    for p, a in an.items():
        ranked[p] = sorted(a["windows"].items(), key=lambda kv: -kv[1]["median"])
    best_conf = "insufficient"
    hypotheses = []
    for p, rk in ranked.items():
        if rk:
            w, v = rk[0]
            c = confidence(v["n"], an[p]["posts_compared"])
            hypotheses.append({"platform": p, "window": w, "median": v["median"], "n": v["n"],
                               "metric": an[p]["metric"], "confidence": c})
            if c != "insufficient":
                best_conf = c
    slots = []
    for i, t in enumerate(cfg["initial_test_slots"], 1):
        slots.append({"slot": i, "time": t, "timezone": tz,
                      "platform_times": {p: t for p in cfg["platforms"]},
                      "status": "experimental" if best_conf == "insufficient" else "evidence_informed",
                      "confidence": best_conf if best_conf != "insufficient" else "insufficient data",
                      "evidence": ["test slot set by Selvin on 2026-10-03",
                                   "own-account comparison too thin to override it (see analysis)"]})
    return {"slots": slots, "analysis": an, "hypotheses": hypotheses,
            "coordination": cfg.get("coordination", "same_slot"),
            "caveats": ["metrics are cumulative and confounded by topic, hook and account momentum",
                        "Buffer reports no audience-activity-by-hour; Instagram/YouTube native insights are not wired",
                        "only posts at least 7 days old are compared so totals are roughly comparable"]}
