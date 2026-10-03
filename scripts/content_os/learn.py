"""Weekly learning loop: weekly-performance-report.json + NEXT_WEEK_RECOMMENDATIONS.
Patterns are only claimed where both compared groups have n >= 3; otherwise 'insufficient data'."""
import datetime as dt
from statistics import median
from .analytics import parse, pick_metric
from .timing import IST, window_of

DIMS = ["hook_type", "emotion", "story_type", "cta_type", "character", "slot_window", "weekday"]


def enrich(rows, attrs):
    out = []
    for r in rows:
        if not (r["episode_id"] and r["status"] == "sent"):
            continue
        a = attrs.get(r["episode_id"], {})
        t = parse(r["sent_at"]).astimezone(IST)
        out.append(dict(r, **{k: a.get(k) for k in ("hook_type", "emotion", "story_type", "cta_type", "character", "theme")},
                        slot_window=window_of(t.hour), weekday=t.strftime("%A")))
    return out


def patterns(rows, cfg, min_n=3, min_age=72):
    res = []
    for platform in sorted({r["platform"] for r in rows}):
        pr = [r for r in rows if r["platform"] == platform and (r["age_hours"] or 0) >= min_age]
        for dim_name, aliases in cfg["metric_priority"]:
            m = pick_metric(pr, aliases)
            if not m:
                continue
            for dim in DIMS:
                groups = {}
                for r in pr:
                    if r.get(dim) is not None and m in r["metrics"]:
                        groups.setdefault(r[dim], []).append(r["metrics"][m])
                big = {g: v for g, v in groups.items() if len(v) >= min_n}
                entry = {"platform": platform, "objective": dim_name, "metric": m, "dimension": dim,
                         "groups": {g: {"n": len(v), "median": median(v)} for g, v in groups.items()}}
                if len(big) >= 2:
                    best = max(big, key=lambda g: median(big[g]))
                    worst = min(big, key=lambda g: median(big[g]))
                    entry.update(finding="pattern", stronger=best, weaker=worst)
                else:
                    entry["finding"] = "insufficient data"
                res.append(entry)
    return res


def weekly_report(week_start, rows, attrs, plan, cfg, now):
    d0 = dt.datetime.fromisoformat(week_start).replace(tzinfo=IST)
    d1 = d0 + dt.timedelta(days=7)
    ev = enrich(rows, attrs)
    in_week = [r for r in ev if d0 <= parse(r["sent_at"]) < d1]
    failed = [r for r in rows if r["status"] == "error" and r.get("due_at") and d0 <= parse(r["due_at"]) < d1]
    totals = {}
    for r in in_week:
        t = totals.setdefault(r["platform"], {})
        for k, v in r["metrics"].items():
            if k != "engagementRate":
                t[k] = t.get(k, 0) + v
    pats = patterns(ev, cfg)
    found = [p for p in pats if p["finding"] == "pattern"]
    recs = []
    for p in found:
        recs.append(f"{p['platform']} {p['objective']} ({p['metric']}): '{p['stronger']}' beat '{p['weaker']}' on {p['dimension']} "
                    f"(n={p['groups'][p['stronger']]['n']} vs {p['groups'][p['weaker']]['n']}). Generalise the pattern, do not copy the story.")
    if not found:
        recs.append("Not enough comparable posts for any pattern claim; keep the controlled experiments running another week.")
    recs.append("Keep at most two variables under test (hook type, slot); hold emotion, CTA and duration steady.")
    return {"week_start": week_start, "week_end": (d1 - dt.timedelta(days=1)).date().isoformat(), "generated_at": now.isoformat(),
            "planned_posts": [{"episode_id": s["episode_id"], "date": s["date"], "slot": s["slot"]} for s in plan["slots"]] if plan else "UNKNOWN (no content-OS plan existed for this week)",
            "published_posts": [{"platform": r["platform"], "episode_id": r["episode_id"], "post_id": r.get("post_id"),
                                 "sent_at": r["sent_at"], "metrics": r["metrics"]} for r in in_week],
            "failed_posts": [{"platform": r["platform"], "post_id": r.get("post_id")} for r in failed],
            "totals_by_platform": totals, "patterns": pats,
            "best_performing_patterns": [p for p in found], "weak_patterns": [{"platform": p["platform"], "dimension": p["dimension"], "weaker": p["weaker"], "metric": p["metric"]} for p in found],
            "timing_observations": "see weekly-content-plan.json timing.hypotheses",
            "content_gaps": "see research file opportunities",
            "NEXT_WEEK_RECOMMENDATIONS": recs}
