"""Compact brief for Hark scheduled runs (token saver): outliers among posts 24-72h old and slot medians.
Run by jr-content-os.yml after every cycle; Hark reads content-os/digest/hark-brief.md instead of raw analytics."""
import json, pathlib
from statistics import median
ROOT = pathlib.Path(__file__).resolve().parents[2]
CONTROL = {"instagram": 1358, "youtube": 611}  # 20:30 baseline (EXP-005)


def views(p):
    v = (p.get("latest") or {}).get("views")
    return v if isinstance(v, (int, float)) else None


def mins(t):
    try:
        h, m = str(t).split(":")[:2]; return int(h) * 60 + int(m)
    except Exception:
        return None


def near(t, slot, tol=20):
    a, b = mins(t), mins(slot)
    return a is not None and abs(a - b) <= tol


def build(pubs, as_of=""):
    out = [f"# Hark brief (as of {as_of})", ""]
    for pl in ("instagram", "youtube"):
        rows = [p for p in pubs if p.get("platform") == pl and views(p) is not None]
        if not rows:
            continue
        med = median(views(p) for p in rows)
        out.append(f"## {pl}: median views {med:.0f} (n={len(rows)})")
        recent = [p for p in rows if (p.get("latest_age_hours") or 1e9) <= 72 and (p.get("latest_age_hours") or 0) >= 24]
        for p in sorted(recent, key=views, reverse=True):
            r = views(p) / med if med else 0
            if r >= 2 or r <= 0.5:
                L = p.get("latest") or {}
                out.append(f"- {p['episode_id']} {p.get('publication_date')} {p.get('publication_time')}: {views(p)} views ({r:.1f}x), "
                           f"likes {L.get('likes')}, shares {L.get('shares')}, comments {L.get('comments')}, hook {p.get('hook_type')}")
        old = [p for p in rows if (p.get("latest_age_hours") or 0) >= 168]
        for slot in ("08:00", "19:30", "20:30"):
            v = [views(p) for p in old if near(p.get("publication_time"), slot)]
            if v:
                out.append(f"- slot {slot}: median {median(v):.0f} n={len(v)}" + (f" (control {CONTROL[pl]})" if slot == "19:30" else ""))
        out.append(f"- unanswered-comment signal: {sum(1 for p in recent if (p.get('latest') or {}).get('comments'))} recent posts have comments")
        out.append("")
    return "\n".join(out)


def main():
    d = json.loads((ROOT / "content-os/analytics/publications.json").read_text())
    (ROOT / "content-os/digest").mkdir(exist_ok=True)
    (ROOT / "content-os/digest/hark-brief.md").write_text(build(d.get("publications", []), d.get("as_of", "")) + "\n")


if __name__ == "__main__":
    main()
