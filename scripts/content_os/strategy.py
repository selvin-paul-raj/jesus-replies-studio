"""Feedback loop: Buffer analytics -> content-os/learnings.json -> STRATEGY.md auto block ->
episode briefs (scripts/daily/pipeline.py brief() embeds the guidance) -> next episodes.

Honest by construction: a group is only called stronger/weaker with n >= MIN_N on both sides,
and every claim carries its n. Metrics are cumulative and confounded by topic and account
momentum, so guidance is phrased as 'lean towards', never as a rule."""
import datetime as dt, json, pathlib, re
from statistics import median
from .analytics import parse
from .timing import IST

MIN_N = 3
MIN_AGE_H = 48
AUTO_START, AUTO_END = "<!-- AUTO:START (rewritten by scripts/content_os/strategy.py) -->", "<!-- AUTO:END -->"


def duration_rules(root=None):
    """The one duration setting (config/publishing-rules.json duration). No second copy here."""
    import os
    root = pathlib.Path(root or os.environ.get("JR_ROOT") or pathlib.Path(__file__).resolve().parents[2])
    return json.loads((root / "config/publishing-rules.json").read_text())["duration"]


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


def compare(rs, dim):
    g = {}
    for r in rs:
        if r.get(dim):
            g.setdefault(r[dim], []).append(r["views"])
    return {k: {"n": len(v), "median_views": median(v)} for k, v in sorted(g.items())}


def learnings(rows, attrs, now, window_days=28, exclude=None):
    since = now - dt.timedelta(days=window_days)
    allr = rows_for(rows, attrs, now, exclude)
    out = {"as_of": now.isoformat(), "window_days": window_days, "min_n": MIN_N, "platforms": {},
           "excluded_ranges": exclude or []}
    guidance = {"lean_towards": [], "avoid": [], "evidence_notes": []}
    for platform in ("instagram", "youtube"):
        rs = [r for r in allr if r["platform"] == platform and parse(r["sent_at"]) >= since]
        if not rs:
            out["platforms"][platform] = {"n": 0}
            continue
        med = median(r["views"] for r in rs)
        dims = {d: compare(rs, d) for d in DIMS}
        strong, weak = [], []
        for d, groups in dims.items():
            for k, v in groups.items():
                if v["n"] >= MIN_N and med:
                    ratio = v["median_views"] / med
                    item = {"dimension": d, "value": k, "n": v["n"], "median_views": v["median_views"], "vs_overall": round(ratio, 2)}
                    if ratio >= 1.15:
                        strong.append(item)
                    elif ratio <= 0.7:
                        weak.append(item)
        top = sorted(rs, key=lambda r: -r["views"])[:5]
        bottom = sorted(rs, key=lambda r: r["views"])[:5]
        saves_rate = [r["saves"] / r["reach"] * 1000 for r in rs if r.get("reach") and r.get("saves") is not None]
        out["platforms"][platform] = {
            "n": len(rs), "median_views": med, "max_views": max(r["views"] for r in rs),
            "saves_per_1k_reach_median": round(median(saves_rate), 1) if saves_rate else None,
            "avg_watch_time_available": any(r.get("avg_watch") for r in rs),
            "by_dimension": dims, "stronger": strong, "weaker": weak,
            "top": [{k: r[k] for k in ("episode_id", "views", "saves", "shares", "theme", "emotion", "hook", "slot", "duration")} for r in top],
            "bottom": [{k: r[k] for k in ("episode_id", "views", "theme", "emotion", "hook", "slot", "duration")} for r in bottom]}
        if platform == "instagram":          # Instagram is the reach engine; authoring follows it
            for s in strong:
                if s["dimension"] != "slot":
                    guidance["lean_towards"].append(f"{s['dimension']}={s['value']} (IG median {s['median_views']:.0f} vs {med:.0f}, n={s['n']})")
            for w in weak:
                if w["dimension"] != "slot":
                    guidance["avoid"].append(f"{w['dimension']}={w['value']} (IG median {w['median_views']:.0f} vs {med:.0f}, n={w['n']})")
            guidance["top_hooks_to_learn_from"] = [f"{t['episode_id']} {t['views']} views: {t['hook']}" for t in top if t.get("hook")]
    ig, yt = out["platforms"].get("instagram", {}), out["platforms"].get("youtube", {})
    for name, p in (("instagram", ig), ("youtube", yt)):
        sl = (p.get("by_dimension") or {}).get("slot", {})
        if len([v for v in sl.values() if v["n"] >= MIN_N]) >= 2:
            guidance["evidence_notes"].append(f"{name} slot medians: " + ", ".join(f"{k} {v['median_views']:.0f} (n={v['n']})" for k, v in sl.items()))
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
                     f"saves per 1k reach {p.get('saves_per_1k_reach_median')}")
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
