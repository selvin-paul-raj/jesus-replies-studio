"""Weekly content inventory: READY / SCHEDULED / PUBLISHED / FAILED / UNUSED. Never loses an episode."""


def platform_states(dist, platforms):
    return {p: ((dist or {}).get("platforms", {}).get(p, {}) or {}).get("state", "NONE") for p in platforms}


def classify(states, published_elsewhere):
    vals = list(states.values())
    if any(v in ("UNKNOWN", "BLOCKED") for v in vals):
        return "FAILED", "unresolved platform state"
    if any(v == "FAILED" for v in vals):
        return "FAILED", "a platform publication failed"
    if all(v in ("PUBLISHED", "PUBLISHED_VERIFIED") for v in vals):
        return "PUBLISHED", "all platforms"
    if any(v == "SCHEDULED" for v in vals):
        return "SCHEDULED", ", ".join(f"{k}={v}" for k, v in states.items())
    if any(v in ("PUBLISHED", "PUBLISHED_VERIFIED") for v in vals) or published_elsewhere:
        return "PUBLISHED", "partial: " + ", ".join(f"{k}={v}" for k, v in states.items())
    return "READY", ", ".join(f"{k}={v}" for k, v in states.items())


def build(eps, assets, dists, snapshot_rows, cfg):
    published_by_ep = {}
    for r in snapshot_rows:
        if r["episode_id"] and r["status"] == "sent":
            published_by_ep.setdefault(r["episode_id"], set()).add(r["platform"])
    held = cfg.get("held_episodes", {})
    items = []
    for eid in sorted(eps):
        a = assets.get(eid)
        st = platform_states(dists.get(eid), cfg["platforms"])
        for p in published_by_ep.get(eid, ()):
            if st.get(p) in ("NONE", "DRAFT"):
                st[p] = "PUBLISHED (seen in Buffer, not tracked by the OS)"
        if not a or a.get("qa_status") != "PASS":
            status, why = ("PUBLISHED", "published before hosted assets were tracked") if published_by_ep.get(eid) else ("UNUSED", "no hosted QA-passed asset")
        else:
            status, why = classify({k: v.split(" ")[0] for k, v in st.items()}, bool(published_by_ep.get(eid)))
        if eid in held and status == "READY":
            status, why = "UNUSED", "held: " + held[eid]
        items.append({"episode_id": eid, "status": status, "why": why, "platforms": st,
                      "asset_url": (a or {}).get("public_url"), "duration_s": (a or {}).get("duration_seconds"),
                      "published_on": sorted(published_by_ep.get(eid, ()))})
    counts = {}
    for i in items:
        counts[i["status"]] = counts.get(i["status"], 0) + 1
    ready = [i["episode_id"] for i in items if i["status"] == "READY"]
    return {"counts": counts, "next_ready": ready[:14], "ready_total": len(ready), "items": items}
