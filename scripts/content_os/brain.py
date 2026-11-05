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


HOOK_PLAN = ("confession", "statement")   # R11 (DEC-JR-017): no question hooks on new episodes


def lane_slots(week_start, cfg):
    """{slot position in the week: (lane name, backlog item)} for weekly series lanes (DEC-JR-017).
    A lane takes its weekday/slot only in weeks its backlog has an entry for."""
    per_day = cfg["videos_per_day"]
    names = sorted(cfg["slots"], key=lambda k: cfg["slots"][k]) if isinstance(cfg.get("slots"), dict) else []
    out = {}
    for name, lane in sorted((cfg.get("series_lanes") or {}).items()):
        item = next((b for b in lane.get("backlog") or [] if b.get("week_start") == week_start
                     and b.get("status") not in ("DONE", "DROPPED")), None)
        if not item:
            continue
        si = names.index(lane.get("slot", "MORNING")) if lane.get("slot", "MORNING") in names else 0
        pos = int(lane.get("weekday", 0)) * per_day + si
        if pos not in out:
            out[pos] = (name, item)
    return out


def build_plan(week_start, attrs, inventory, timing, research, experiments, analytics_summary, cfg, next_id, now):
    dates = week_dates(week_start)
    per_day = cfg["videos_per_day"]
    n = len(dates) * per_day
    ready = inventory["next_ready"] + [e for e in (i["episode_id"] for i in inventory["items"] if i["status"] == "READY")
                                       if e not in inventory["next_ready"]]
    lanes = lane_slots(week_start, cfg)
    lane_ids = {item.get("episode_id") for _, item in lanes.values() if item.get("episode_id")}
    lane_ids |= {b.get("episode_id") for l in (cfg.get("series_lanes") or {}).values() for b in l.get("backlog") or []
                 if b.get("episode_id") and b.get("status") not in ("DONE", "DROPPED")}
    ready = [e for e in ready if e not in lane_ids]       # a lane episode only ever fills its own lane slot
    n_open = n - len(lanes)
    pinned = [e for e in cfg.get("pinned_first", []) if e in ready]
    rest = [e for e in ready if e not in pinned]
    chosen = pinned + order_for_diversity(rest, attrs)
    chosen = (pinned + order_for_diversity([e for e in rest], attrs))[:n_open] if pinned else chosen[:n_open]
    carry = [e for e in ready if e not in chosen]
    active_exp = {e["id"]: e for e in experiments.get("experiments", []) if e.get("status") == "active"}
    slots, k, gen_id, pos, n_hook = [], 0, next_id, -1, 0
    ready_all = set(inventory["next_ready"]) | {i["episode_id"] for i in inventory["items"] if i["status"] == "READY"}
    for d in dates:
        for t in timing["slots"][:per_day]:
            pos += 1
            hh, mm = map(int, t["time"].split(":"))
            local = dt.datetime(d.year, d.month, d.day, hh, mm, tzinfo=IST)
            due = {p: iso(dt.datetime(d.year, d.month, d.day, *map(int, t["platform_times"][p].split(":")), tzinfo=IST))
                   for p in cfg["platforms"]}
            lane = lanes.get(pos)
            if lane:
                lname, item = lane
                if item.get("episode_id"):
                    eid = item["episode_id"]
                else:
                    eid = f"JR-{gen_id:04d}"
                    gen_id += 1
                a = attrs.get(eid, {})
                status = "READY" if eid in ready_all else "NEEDS_GENERATION"
                rationale = [f"weekly series lane '{lname}' (DEC-JR-017): {item.get('idea')} Verse {item.get('verse')} "
                             f"(context-checked, R10). Goes through every normal gate before it is scheduled."]
            elif k < len(chosen):
                eid = chosen[k]
                k += 1
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
            hook_strategy = a.get("hook_type")
            if status == "NEEDS_GENERATION" or not hook_strategy:
                hook_strategy = HOOK_PLAN[n_hook % len(HOOK_PLAN)]     # R11: confession / statement only
                n_hook += 1
            elif hook_strategy == "question":
                rationale.append("R11: question hook predates the rule (JR-0094+ cannot open with a question)")
            tags = []
            if "EXP-001" in active_exp and a.get("hook_type"):
                tags.append(f"EXP-001:{'control' if a['hook_type'] == 'question' else 'variant'}")
            if "EXP-002" in active_exp:
                tags.append(f"EXP-002:slot{t['slot']}")
            slots.append({"episode_id": eid, "date": d.isoformat(), "weekday": d.strftime("%A"), "slot": t["slot"],
                          "time": t["time"], "timezone": cfg["timezone"], "platform_times": t["platform_times"],
                          "due_at": due, "slot_confidence": t["confidence"], "slot_status": t["status"],
                          "theme": a.get("theme") or (lane[1].get("idea") if lane else None),
                          "hook_strategy": hook_strategy, "hook": a.get("hook"),
                          "emotional_angle": a.get("emotion"), "character": a.get("character"),
                          "bible_reference": a.get("bible_theme") or (lane[1].get("verse") if lane else None),
                          "story_type": a.get("story_type"),
                          "cta_type": a.get("cta_type"), "duration_s": a.get("duration"),
                          "platforms": list(cfg["platforms"]), "status": status, "experiments": tags,
                          "rationale": rationale, **({"series": lane[0]} if lane else {})})
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
