"""Feedback loop: Buffer analytics -> content-os/learnings.json -> STRATEGY.md auto block ->
episode briefs (scripts/daily/pipeline.py brief() embeds the guidance) -> next episodes.

Rules since the 2026-10-16 deep review (DEC-JR-007):
- A Reel whose reach is below the account's follower count stalled in distribution (it never
  left the follower pool); that says nothing about the content, so it is excluded from content
  learning (it is still counted in the stall rate).
- Each episode gets ONE score: the average of its view percentile on Instagram and on YouTube,
  over whichever platforms have usable data. Content dimensions are compared on that score.
- A rule (lean towards / avoid) only enters the brief when its bucket has at least MIN_N episodes.

Metrics are cumulative and confounded by topic and account momentum, so guidance is phrased as
'lean towards', never as a rule."""
import datetime as dt, json, os, pathlib, re
from statistics import median
from .analytics import parse
from .timing import IST

MIN_N = 8
MIN_AGE_H = 48
EDGE = 0.15          # a bucket must sit 15 percentile points above/below the overall median score
AUTO_START, AUTO_END = "<!-- AUTO:START (rewritten by scripts/content_os/strategy.py) -->", "<!-- AUTO:END -->"


def _root(root=None):
    return pathlib.Path(root or os.environ.get("JR_ROOT") or pathlib.Path(__file__).resolve().parents[2])


def duration_rules(root=None):
    """The one duration setting (config/publishing-rules.json duration). No second copy here."""
    return json.loads((_root(root) / "config/publishing-rules.json").read_text())["duration"]


def instagram_followers(root=None):
    """Follower count used as the stall line (config/content-os.json analytics.instagram_followers)."""
    try:
        c = json.loads((_root(root) / "config/content-os.json").read_text())
        return (c.get("analytics") or {}).get("instagram_followers")
    except Exception:
        return None


def dur_bucket(d, rules=None):
    if not d:
        return None
    rules = rules or duration_rules()
    hi, ceil = rules["target_seconds"][1], rules["ceiling_seconds"]
    return f"<={hi}s" if d <= hi else (f"{hi + 1}-{ceil}s" if d <= ceil else f">{ceil}s")


def slot_of(sent_at):
    h = parse(sent_at).astimezone(IST)
    return "morning (06-12 IST)" if 6 <= h.hour < 12 else ("night (18-24 IST)" if h.hour >= 18 else "other")


def excluded(sent_at, ranges):
    t = parse(sent_at)
    return any(parse(x["from"]) <= t < parse(x["to"]) for x in ranges or [])


def rows_for(rows, attrs, now, exclude=None):
    out, drules = [], duration_rules()
    for r in rows:
        if not (r.get("episode_id") and r.get("status") == "sent" and r.get("sent_at")):
            continue
        if excluded(r["sent_at"], exclude):
            continue
        m = r.get("metrics") or {}
        if not m.get("views") and not m.get("reach"):
            continue                                   # metrics not populated yet (YouTube lag)
        age = (now - parse(r["sent_at"])).total_seconds() / 3600
        if age < MIN_AGE_H:
            continue
        a = attrs.get(r["episode_id"].split("-M")[0], {})
        out.append({"episode_id": r["episode_id"], "platform": r["platform"], "sent_at": r["sent_at"],
                    "views": m.get("views") or 0, "reach": m.get("reach"), "saves": m.get("saves"),
                    "shares": m.get("shares"), "comments": m.get("comments"),
                    "avg_watch": m.get("averageTimeWatched"),
                    "slot": slot_of(r["sent_at"]), "emotion": a.get("emotion"), "character": a.get("character"),
                    "hook_type": a.get("hook_type"), "duration": dur_bucket(a.get("duration"), drules),
                    "bible_book": a.get("bible_book"), "theme": a.get("theme"), "hook": a.get("hook")})
    return out


DIMS = ["slot", "emotion", "character", "hook_type", "duration", "bible_book"]
CONTENT_DIMS = [d for d in DIMS if d != "slot"]


def is_stall(r, followers):
    return bool(r["platform"] == "instagram" and followers and r.get("reach") is not None and r["reach"] < followers)


def percentiles(rs):
    """episode_id -> view percentile in 0..1 (mid-rank, ties share a rank) within one platform."""
    vals = sorted(r["views"] for r in rs)
    n = len(vals)
    out = {}
    for r in rs:
        below = sum(1 for v in vals if v < r["views"])
        equal = sum(1 for v in vals if v == r["views"])
        out[r["episode_id"]] = (below + (equal - 1) / 2) / (n - 1) if n > 1 else 0.5
    return out


def episode_scores(rs, followers):
    """-> ({episode_id: {score, platforms, ...attrs}}, stalls). Score = mean percentile over platforms with data."""
    stalls = [r for r in rs if is_stall(r, followers)]
    usable = [r for r in rs if not is_stall(r, followers)]
    per = {p: percentiles([r for r in usable if r["platform"] == p]) for p in ("instagram", "youtube")}
    eps = {}
    for r in usable:
        e = eps.setdefault(r["episode_id"], {"episode_id": r["episode_id"], "pct": {}, "views": {},
                                             **{d: r.get(d) for d in CONTENT_DIMS + ["theme", "hook", "slot"]}})
        e["pct"][r["platform"]] = per[r["platform"]][r["episode_id"]]
        e["views"][r["platform"]] = r["views"]
    for e in eps.values():
        e["score"] = round(sum(e["pct"].values()) / len(e["pct"]), 3)
        e["platforms"] = sorted(e["pct"])
    return eps, stalls


def compare(rs, dim, key="views"):
    g = {}
    for r in rs:
        if r.get(dim):
            g.setdefault(r[dim], []).append(r[key])
    name = "median_views" if key == "views" else f"median_{key}"
    return {k: {"n": len(v), name: median(v)} for k, v in sorted(g.items())}


def learnings(rows, attrs, now, window_days=28, exclude=None, followers=None):
    since = now - dt.timedelta(days=window_days)
    followers = followers if followers is not None else instagram_followers()
    allr = [r for r in rows_for(rows, attrs, now, exclude) if parse(r["sent_at"]) >= since]
    out = {"as_of": now.isoformat(), "window_days": window_days, "min_n": MIN_N, "platforms": {},
           "excluded_ranges": exclude or [], "stall_rule": f"Instagram reach < followers ({followers}) = stalled, "
           "excluded from content learning", "scoring": "mean of Instagram and YouTube view percentiles where data exists"}
    guidance = {"lean_towards": [], "avoid": [], "evidence_notes": []}
    for platform in ("instagram", "youtube"):
        rs_all = [r for r in allr if r["platform"] == platform]
        rs = [r for r in rs_all if not is_stall(r, followers)]
        if not rs_all:
            out["platforms"][platform] = {"n": 0}
            continue
        med = median(r["views"] for r in rs) if rs else 0
        top = sorted(rs, key=lambda r: -r["views"])[:5]
        bottom = sorted(rs, key=lambda r: r["views"])[:5]
        saves_rate = [r["saves"] / r["reach"] * 1000 for r in rs if r.get("reach") and r.get("saves") is not None]
        stalled = [r["episode_id"] for r in rs_all if is_stall(r, followers)]
        out["platforms"][platform] = {
            "n": len(rs), "n_stalled": len(stalled), "stalled": stalled,
            "stall_rate": round(len(stalled) / len(rs_all), 2),
            "median_views": med, "max_views": max((r["views"] for r in rs), default=0),
            "saves_per_1k_reach_median": round(median(saves_rate), 1) if saves_rate else None,
            "avg_watch_time_available": any(r.get("avg_watch") for r in rs),
            "by_dimension": {"slot": compare(rs, "slot")},
            "top": [{k: r[k] for k in ("episode_id", "views", "saves", "shares", "theme", "emotion", "hook", "slot", "duration")} for r in top],
            "bottom": [{k: r[k] for k in ("episode_id", "views", "theme", "emotion", "hook", "slot", "duration")} for r in bottom]}
    eps, _ = episode_scores(allr, followers)
    E = list(eps.values())
    content = {"n_episodes": len(E), "both_platforms": sum(1 for e in E if len(e["platforms"]) == 2)}
    if E:
        overall = median(e["score"] for e in E)
        content["median_score"] = overall
        content["by_dimension"] = {d: compare(E, d, "score") for d in CONTENT_DIMS}
        for d, groups in content["by_dimension"].items():
            for k, v in groups.items():
                if v["n"] < MIN_N:
                    continue
                diff = v["median_score"] - overall
                item = f"{d}={k} (episode score {v['median_score']:.2f} vs {overall:.2f}, n={v['n']}, IG+YT percentile)"
                if diff >= EDGE:
                    guidance["lean_towards"].append(item)
                elif diff <= -EDGE:
                    guidance["avoid"].append(item)
        ranked = sorted(E, key=lambda e: -e["score"])
        content["top"] = [{"episode_id": e["episode_id"], "score": e["score"], "views": e["views"], "hook": e.get("hook")} for e in ranked[:5]]
        guidance["top_hooks_to_learn_from"] = [f"{e['episode_id']} score {e['score']:.2f} "
                                               f"({', '.join(f'{p} {v}' for p, v in sorted(e['views'].items()))} views): {e['hook']}"
                                               for e in ranked[:5] if e.get("hook")]
    out["content"] = content
    ig, yt = out["platforms"].get("instagram", {}), out["platforms"].get("youtube", {})
    for name, p in (("instagram", ig), ("youtube", yt)):
        sl = (p.get("by_dimension") or {}).get("slot", {})
        if len([v for v in sl.values() if v["n"] >= MIN_N]) >= 2:
            guidance["evidence_notes"].append(f"{name} slot medians: " + ", ".join(f"{k} {v['median_views']:.0f} (n={v['n']})" for k, v in sl.items()))
    if ig.get("n_stalled"):
        guidance["evidence_notes"].append(f"instagram: {ig['n_stalled']} of {ig['n'] + ig['n_stalled']} Reels stalled (reach under "
                                          f"{followers} followers) and were left out of content learning: {', '.join(ig['stalled'])}")
    guidance["evidence_notes"].append(f"rules need n>={MIN_N} episodes per bucket; smaller buckets are reported only")
    if not ig.get("avg_watch_time_available"):
        guidance["evidence_notes"].append("average watch time is not exposed by the Buffer API for these posts; retention is judged by views/saves/shares only")
    out["authoring_guidance"] = guidance
    return out


def render_auto_block(L):
    g = L["authoring_guidance"]
    lines = [AUTO_START, f"_Last computed {L['as_of'][:16]}Z from Buffer analytics, last {L['window_days']} days, posts at least {MIN_AGE_H}h old._", ""]
    for name, p in L["platforms"].items():
        if not p.get("n"):
            lines.append(f"- **{name}**: no comparable posts yet.")
            continue
        lines.append(f"- **{name}**: n={p['n']}, median views {p['median_views']:.0f}, best {p['max_views']}, "
                     f"saves per 1k reach {p.get('saves_per_1k_reach_median')}, stalled {p.get('n_stalled', 0)} (excluded)")
    c = L.get("content") or {}
    if c.get("n_episodes"):
        lines.append(f"- **episodes scored** (IG + YT percentile): {c['n_episodes']}, {c['both_platforms']} with both platforms")
    lines += ["", "**Lean towards** (authoring reads this):"] + [f"- {x}" for x in g["lean_towards"] or ["not enough evidence yet"]]
    lines += ["", "**Avoid / de-emphasise:**"] + [f"- {x}" for x in g["avoid"] or ["nothing with enough evidence"]]
    lines += ["", "**Hooks that travelled furthest (learn the shape, never copy the story):**"] + [f"- {x}" for x in g.get("top_hooks_to_learn_from", [])]
    lines += ["", "**Evidence notes:**"] + [f"- {x}" for x in g["evidence_notes"]]
    lines += [f"- excluded {x['from'][:10]}..{x['to'][:10]}: {x['reason']}" for x in L.get("excluded_ranges", [])]
    lines.append(AUTO_END)
    return "\n".join(lines)


def write(root, L):
    root = pathlib.Path(root)
    (root / "content-os/learnings.json").write_text(json.dumps(L, indent=2, ensure_ascii=False) + "\n")
    p = root / "content-os/STRATEGY.md"
    doc = p.read_text() if p.exists() else f"# Jesus Replies strategy\n\n{AUTO_START}\n{AUTO_END}\n"
    if AUTO_START not in doc:
        doc += f"\n{AUTO_START}\n{AUTO_END}\n"
    pre, rest = doc.split(AUTO_START, 1)
    post = rest.split(AUTO_END, 1)[1] if AUTO_END in rest else ""
    p.write_text(pre + render_auto_block(L) + post)


def review(root, L, experiments, cfg, now, force=False):
    """Bi-weekly review (even ISO weeks, or force). Records what changed since the last review,
    evaluates the slot experiment by its own decision rule, and lists bounded actions."""
    root = pathlib.Path(root)
    wk = now.astimezone(IST).isocalendar()[1]
    if not force and wk % 2:
        return None
    rdir = root / "content-os/reviews"
    prev = sorted(rdir.glob("*.json"))
    prev = json.loads(prev[-1].read_text()) if prev else None
    actions = []
    for name, p in L["platforms"].items():
        sl = {k: v for k, v in (p.get("by_dimension") or {}).get("slot", {}).items() if k != "other"}
        if len(sl) == 2 and all(v["n"] >= 7 for v in sl.values()):
            (a, va), (b, vb) = sorted(sl.items(), key=lambda kv: -kv[1]["median_views"])
            verdict = f"{name}: {a} median {va['median_views']:.0f} vs {b} {vb['median_views']:.0f} (n={va['n']}/{vb['n']})"
            actions.append({"type": "experiment_reading", "experiment": "EXP-002", "detail": verdict})
            for e in experiments.get("experiments", []):
                if e["id"] == "EXP-002":
                    e.setdefault("readings", []).append({"at": now.isoformat(), "reading": verdict})
    g = L["authoring_guidance"]
    actions.append({"type": "authoring_emphasis", "detail": {"lean_towards": g["lean_towards"], "avoid": g["avoid"]},
                    "applied": "STRATEGY.md auto block + every new brief"})
    if prev:
        for name, p in L["platforms"].items():
            pp = (prev.get("platforms") or {}).get(name, {})
            if pp.get("median_views") and p.get("median_views"):
                ch = p["median_views"] / pp["median_views"] - 1
                actions.append({"type": "trend", "detail": f"{name} median views {pp['median_views']:.0f} -> {p['median_views']:.0f} ({ch:+.0%}) since {prev['as_of'][:10]}"})
                if ch <= -0.3:
                    actions.append({"type": "alert", "detail": f"{name} median views fell {ch:.0%}; next briefs lean harder on the strongest emotions/hooks and the review flags it in the report"})
    rep = {"as_of": now.isoformat(), "iso_week": wk, "platforms": {k: {kk: v.get(kk) for kk in ("n", "median_views", "max_views", "saves_per_1k_reach_median")} for k, v in L["platforms"].items()},
           "actions": actions, "slot_policy": "slot times change only when both platforms agree with n>=7 per arm (EXP-002 rule); otherwise recorded as a reading"}
    rdir.mkdir(parents=True, exist_ok=True)
    (rdir / f"{now.astimezone(IST).date().isoformat()}.json").write_text(json.dumps(rep, indent=2, ensure_ascii=False) + "\n")
    return rep
