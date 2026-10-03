"""Weekly content brain: history + analytics + research + inventory + timing -> weekly-content-plan.json.
Ready inventory is used before anything new is generated; gaps become generation briefs."""
import json, hashlib, datetime as dt
from .timing import IST
from .distribute import iso


def week_dates(week_start):
    d0 = dt.date.fromisoformat(week_start)
    return [d0 + dt.timedelta(days=i) for i in range(7)]


def order_for_diversity(cands, attrs):
    seq, pool = [], list(cands)
    while pool:
        prev = attrs.get(seq[-1], {}) if seq else {}
        pick = next((c for c in pool if attrs.get(c, {}).get("emotion") != prev.get("emotion")
                     and attrs.get(c, {}).get("character") != prev.get("character")), None) \
            or next((c for c in pool if attrs.get(c, {}).get("emotion") != prev.get("emotion")), pool[0])
        seq.append(pick)
        pool.remove(pick)
    return seq


def plan_sha(slots):
    canon = json.dumps([{k: s[k] for k in ("episode_id", "date", "slot", "due_at", "platforms", "status")} for s in slots],
                       sort_keys=True)
    return hashlib.sha256(canon.encode()).hexdigest()


def build_plan(week_start, attrs, inventory, timing, research, experiments, analytics_summary, cfg, next_id, now):
    dates = week_dates(week_start)
    per_day = cfg["videos_per_day"]
    n = len(dates) * per_day
    ready = inventory["next_ready"] + [e for e in (i["episode_id"] for i in inventory["items"] if i["status"] == "READY")
                                       if e not in inventory["next_ready"]]
    pinned = [e for e in cfg.get("pinned_first", []) if e in ready]
    rest = [e for e in ready if e not in pinned]
    chosen = pinned + order_for_diversity(rest, attrs)
    chosen = (pinned + order_for_diversity([e for e in rest], attrs))[:n] if pinned else chosen[:n]
    carry = [e for e in ready if e not in chosen]
    active_exp = {e["id"]: e for e in experiments.get("experiments", []) if e.get("status") == "active"}
    slots, k, gen_id = [], 0, next_id
    for d in dates:
        for t in timing["slots"][:per_day]:
            hh, mm = map(int, t["time"].split(":"))
            local = dt.datetime(d.year, d.month, d.day, hh, mm, tzinfo=IST)
            due = {p: iso(dt.datetime(d.year, d.month, d.day, *map(int, t["platform_times"][p].split(":")), tzinfo=IST))
                   for p in cfg["platforms"]}
            if k < len(chosen):
                eid = chosen[k]
                a = attrs.get(eid, {})
                status = "READY"
                rationale = [f"ready inventory (hosted, QA PASS, {a.get('duration')}s)",
                             f"emotion '{a.get('emotion')}' and character '{a.get('character')}' differ from the previous slot where inventory allowed"]
                if eid in pinned:
                    rationale.insert(0, "existing Buffer Instagram draft; scheduled by edit, never recreated")
            else:
                eid = f"JR-{gen_id:04d}"
                gen_id += 1
                a, status = {}, "NEEDS_GENERATION"
                rationale = ["inventory exhausted; Fo Brain generates from research gaps, then the daily pipeline validates"]
            tags = []
            if "EXP-001" in active_exp and a.get("hook_type"):
                tags.append(f"EXP-001:{'control' if a['hook_type'] == 'question' else 'variant'}")
            if "EXP-002" in active_exp:
                tags.append(f"EXP-002:slot{t['slot']}")
            slots.append({"episode_id": eid, "date": d.isoformat(), "weekday": d.strftime("%A"), "slot": t["slot"],
                          "time": t["time"], "timezone": cfg["timezone"], "platform_times": t["platform_times"],
                          "due_at": due, "slot_confidence": t["confidence"], "slot_status": t["status"],
                          "theme": a.get("theme"), "hook_strategy": a.get("hook_type"), "hook": a.get("hook"),
                          "emotional_angle": a.get("emotion"), "character": a.get("character"),
                          "bible_reference": a.get("bible_theme"), "story_type": a.get("story_type"),
                          "cta_type": a.get("cta_type"), "duration_s": a.get("duration"),
                          "platforms": list(cfg["platforms"]), "status": status, "experiments": tags,
                          "rationale": rationale})
            k += 1
    plan = {"plan_version": 1, "week_start": week_start, "week_end": dates[-1].isoformat(), "timezone": cfg["timezone"],
            "generated_at": iso(now), "status": "PROPOSED",
            "requires_authorization": cfg["autonomy"]["weekly_plan_approval"],
            "targets": {"unique_videos": n, "instagram": n, "youtube": n, "platform_publications": 2 * n},
            "generation_needed": sum(1 for s in slots if s["status"] == "NEEDS_GENERATION"),
            "carry_over_ready": carry, "inventory_counts": inventory["counts"],
            "analytics_summary": analytics_summary, "timing": {k2: timing[k2] for k2 in ("hypotheses", "caveats", "coordination")},
            "research_ref": research.get("_path"), "research_opportunities": research.get("opportunities", []),
            "experiments_active": list(active_exp), "slots": slots}
    plan["plan_sha256"] = plan_sha(slots)
    return plan
