"""Skill-based self-review of authored episodes (advisory, never blocks).

Runs the vendored creator skills' own scorers on every episode script:
  - ig-reel/hookscore.py  -> hook score on the first person line (5 properties)
  - ig-reel/beats.py      -> timed beat sheet at the TTS pace (150 wpm)
and writes content-os/reviews/skill-review-<date>.json so the bi-weekly growth
review can correlate hook score / beat flags with real views, saves and sends.

Usage:
  python3 scripts/content_os/skill_review.py JR-0083 JR-0084 ...
  python3 scripts/content_os/skill_review.py --all-unpublished
"""
from __future__ import annotations

import argparse
import datetime as _dt
import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REEL = ROOT / "skills/vendor/instagram-agent-skill/skills/ig-reel"
WPM = 150
TARGET = 50


def _load(name: str):
    spec = importlib.util.spec_from_file_location(f"jr_{name}", REEL / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


def script_lines(ep: dict) -> list[str]:
    out = []
    for ln in ep.get("lines", []):
        if ln.get("speaker") == "bible_verse":
            out.append((ep.get("bible") or {}).get("text", ""))
        elif ln.get("text"):
            out.append(ln["text"])
    return [x for x in out if x]


def review(ep: dict, hookscore, beats) -> dict:
    lines = script_lines(ep)
    hook = lines[0] if lines else ""
    results, overall, verdict, flags = hookscore.run(hook)
    sheet = beats.analyse("\n".join(lines), wpm=WPM, target=TARGET) or {}
    weakest = min(results, key=lambda k: results[k][0]) if results else None
    return {
        "id": ep.get("id"),
        "title": ep.get("title"),
        "hook": hook,
        "hook_score": round(overall, 1),
        "hook_verdict": verdict,
        "hook_weakest": weakest,
        "hook_flags": flags,
        "seconds_est": sheet.get("total_seconds"),
        "words": sheet.get("total_words"),
        "long_beats": [b["n"] for b in sheet.get("beats", []) if b.get("flags")],
        "loops_to_hook": any(n.startswith("Loops:") for n in sheet.get("notes", [])),
        "notes": sheet.get("notes", []),
    }


def _corr(a, b):
    import statistics
    if len(a) < 3:
        return 0.0
    ma, mb = statistics.mean(a), statistics.mean(b)
    num = sum((x - ma) * (y - mb) for x, y in zip(a, b))
    den = (sum((x - ma) ** 2 for x in a) * sum((y - mb) ** 2 for y in b)) ** 0.5
    return round(num / den, 2) if den else 0.0


def calibrate(hookscore, beats) -> int:
    """Self-check: does the generic scorer predict OUR views? Writes calibration file."""
    import math
    pubs = json.loads((ROOT / "content-os/analytics/publications.json").read_text())
    rows = {p.stem: review(json.loads(p.read_text()), hookscore, beats)
            for p in (ROOT / "generated").glob("JR-*.json") if ".package" not in p.name}
    out = {"as_of": _dt.date.today().isoformat(), "metric": "pearson r vs log(views+1)", "platforms": {}}
    allp = [x for v in pubs.values() if isinstance(v, list) for x in v]
    for plat in sorted({x.get("platform") for x in allp if x.get("platform")}):
        items = [x for x in allp if x.get("platform") == plat]
        pairs = [(rows[x["episode_id"]], (x.get("latest") or {}).get("views")) for x in items
                 if x.get("episode_id") in rows and isinstance((x.get("latest") or {}).get("views"), (int, float))]
        if len(pairs) < 5:
            continue
        y = [math.log(v + 1) for _, v in pairs]
        out["platforms"][plat] = {
            "n": len(pairs),
            "hook_score": _corr([r["hook_score"] for r, _ in pairs], y),
            "seconds_est": _corr([r["seconds_est"] or 0 for r, _ in pairs], y),
            "long_beats": _corr([len(r["long_beats"]) for r, _ in pairs], y),
            "loops_to_hook": _corr([1 if r["loops_to_hook"] else 0 for r, _ in pairs], y),
        }
    out["reading"] = ("Only treat a signal as a rule when |r| >= 0.3 on n >= 30 on that platform; "
                      "otherwise it stays advisory. The generic hookscore was built for business Reels.")
    dest = ROOT / "content-os/reviews/skill-calibration.json"
    dest.write_text(json.dumps(out, indent=2) + "\n")
    print(json.dumps(out, indent=2))
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("ids", nargs="*")
    ap.add_argument("--out", default=None)
    ap.add_argument("--calibrate", action="store_true",
                    help="correlate scores with real views (content-os/analytics/publications.json)")
    a = ap.parse_args(argv)
    hookscore, beats = _load("hookscore"), _load("beats")
    if a.calibrate:
        return calibrate(hookscore, beats)
    ids = a.ids or sorted(p.stem for p in (ROOT / "generated").glob("JR-*.json") if ".package" not in p.name)
    rows = []
    for i in ids:
        p = ROOT / "generated" / f"{i}.json"
        if not p.exists():
            print(f"[skill-review] missing {p}", file=sys.stderr)
            continue
        rows.append(review(json.loads(p.read_text()), hookscore, beats))
    today = _dt.date.today().isoformat()
    out = Path(a.out) if a.out else ROOT / "content-os/reviews" / f"skill-review-{today}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"as_of": today, "wpm": WPM, "target_s": TARGET,
                               "advisory": True, "episodes": rows}, indent=2, ensure_ascii=False) + "\n")
    for r in rows:
        print(f"{r['id']}  hook {r['hook_score']:>5} {r['hook_verdict']:<6} weakest={r['hook_weakest']:<12} "
              f"~{r['seconds_est']}s  long_beats={r['long_beats']}  loop={r['loops_to_hook']}")
    print(f"[skill-review] wrote {out.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
