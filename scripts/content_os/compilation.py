#!/usr/bin/env python3
"""DEC-JR-018 weekly YouTube compilation: the week's published Shorts stitched into one 6-8 minute
HORIZONTAL video (1920x1080, each vertical Short centred over a blurred fill), with chapter timestamps.

Why horizontal: YouTube treats any vertical/square upload of 3 minutes or less as a Short; a 16:9 file is
long-form regardless of length, so the 6-8 minute compilation is unambiguously a regular video.
Why not Buffer: Buffer publishes YouTube Shorts only ("Buffer currently supports YouTube Shorts only. We do
not support long-form YouTube videos at this time.", support.buffer.com, checked 2026-11-05), so the file,
title, description and chapters are stored as a GitHub release asset (jr-compilation-<week_start>) for a
manual YouTube Studio upload. config weekly_compilation.buffer_youtube_longform_supported stays false until
Buffer supports it; this script never posts anything.

  python3 scripts/content_os/compilation.py --week 2026-11-02 [--plan-only]"""
import argparse, datetime as dt, json, pathlib, subprocess, sys, urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
from content_os import episodes  # noqa: E402

HONESTY = "An imagined reply with AI-made visuals. The Scripture is quoted as written."


def ts(sec):
    sec = int(round(sec))
    h, m, s = sec // 3600, (sec % 3600) // 60, sec % 60
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


def published_in_week(pubs, week_start, platform="youtube"):
    d0 = dt.date.fromisoformat(week_start)
    days = {(d0 + dt.timedelta(days=i)).isoformat() for i in range(7)}
    best = {}
    for p in pubs:
        if p.get("platform") != platform or p.get("publication_date") not in days or not p.get("episode_id"):
            continue
        v = (p.get("latest") or {}).get("views")
        best[p["episode_id"]] = {"episode_id": p["episode_id"], "date": p["publication_date"], "time": p.get("publication_time", ""),
                                 "views": v if isinstance(v, (int, float)) else 0}
    return sorted(best.values(), key=lambda r: (r["date"], r["time"]))


def select(cands, durations, min_s=360, max_s=480, intro_s=0.0):
    """Most-viewed first until the next clip would pass max_s; result in publication order.
    -> (clips, total_seconds, ok) where ok means min_s <= total <= max_s."""
    total, chosen = intro_s, []
    for c in sorted(cands, key=lambda r: -r["views"]):
        d = durations.get(c["episode_id"])
        if not d:
            continue
        if total + d <= max_s:
            chosen.append(c)
            total += d
    chosen.sort(key=lambda r: (r["date"], r["time"]))
    return chosen, total, min_s <= total <= max_s


def chapter_title(ep):
    b = ep.get("bible") or {}
    book = "Psalm" if b.get("book") == "Psalms" else b.get("book")
    t = (ep.get("title") or "").split(" | ")[0].strip()
    ver = "KJV" if b.get("version") == "KJV" else b.get("version", "")
    return f"{t} | {book} {b.get('chapter')}:{b.get('verse')} ({ver})"


def chapters(clips, durations, eps):
    """YouTube chapters: first at 0:00, at least 3, each >= 10 s."""
    out, t = [], 0.0
    for c in clips:
        out.append((ts(t), chapter_title(eps.get(c["episode_id"], {}))))
        t += durations[c["episode_id"]]
    return out


VERSION_NAMES = {"KJV": "King James Version (KJV)", "BSB": "Berean Standard Bible (BSB)"}


def scripture_line(clips, eps):
    """Label what is actually on screen: Shorts published before 2026-11-05 show the BSB (DEC-JR-016)."""
    vs = sorted({(eps.get(c["episode_id"], {}).get("bible") or {}).get("version") or "KJV" for c in clips}, key=lambda v: v != "KJV")
    return "Scripture: " + " and ".join(VERSION_NAMES.get(v, v) for v in vs) + ", quoted as written (each chapter names its version)."


def eligible(eid, eps, pkgs, held):
    """Never re-publish a held/pulled episode (R5 Diwali pulls, crisis holds) or anything the faith-framing lint flags."""
    from daily import safety
    if eid in held or eid not in eps:
        return False
    return not safety.faith_framing(eps[eid], pkgs.get(eid))


def metadata(week_start, clips, durations, eps):
    d0 = dt.date.fromisoformat(week_start)
    ch = chapters(clips, durations, eps)
    title = f"Jesus Replies: This Week's Conversations ({d0.strftime('%b %-d')}–{(d0 + dt.timedelta(days=6)).strftime('%b %-d')}) | Bible Verses KJV"
    desc = ("Jesus's Replies — imagined replies from Jesus, answered from Scripture. This week's Shorts in one place.\n\n"
            "Chapters\n" + "\n".join(f"{a} {b}" for a, b in ch) +
            "\n\n" + scripture_line(clips, eps) + "\n"
            "Watch more on Instagram: https://www.instagram.com/jesusrepliesofficial/\n\n"
            "Send this to someone who needs a word this week.\n\n" + HONESTY)
    return {"title": title[:100], "description": desc[:5000], "chapters": ch, "episodes": [c["episode_id"] for c in clips],
            "total_seconds": round(sum(durations[c["episode_id"]] for c in clips), 2),
            "upload": "manual (YouTube Studio): Buffer supports YouTube Shorts only", "category_id": "27", "made_for_kids": False}


def ffprobe_seconds(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", str(path)],
                       capture_output=True, text=True)
    return float(r.stdout.strip() or 0)


def render(paths, out):
    """Each Short -> 1920x1080 30fps: blurred, darkened fill + the original centred at full height; then concat."""
    parts = []
    for i, p in enumerate(paths):
        o = out.parent / f".part-{i:02d}.mp4"
        vf = ("[0:v]split=2[a][b];[a]scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,boxblur=30:2,"
              "eq=brightness=-0.12[bg];[b]scale=-2:1080[fg];[bg][fg]overlay=(W-w)/2:0,fps=30,format=yuv420p[v]")
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(p), "-filter_complex", vf, "-map", "[v]", "-map", "0:a?",
                        "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-c:a", "aac", "-b:a", "160k", "-ar", "48000", "-ac", "2",
                        str(o)], check=True)
        parts.append(o)
    lst = out.parent / ".concat.txt"
    lst.write_text("".join(f"file '{q.name}'\n" for q in parts))
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy",
                    "-movflags", "+faststart", str(out)], check=True)
    for q in parts + [lst]:
        q.unlink()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--week", required=True, help="Monday of the week (IST), e.g. 2026-11-02")
    ap.add_argument("--plan-only", action="store_true")
    a = ap.parse_args()
    full = json.loads((ROOT / "config/content-os.json").read_text())
    cfg = full.get("weekly_compilation") or {}
    held = set(full.get("held_episodes") or {}) | set(cfg.get("exclude") or {})
    if not cfg.get("enabled", False):
        print("[compilation] disabled in config"); return 0
    pubs = json.loads((ROOT / "content-os/analytics/publications.json").read_text())["publications"]
    eps, pkgs, assets = episodes.load_catalogue(ROOT)
    cands = [c for c in published_in_week(pubs, a.week) if (assets.get(c["episode_id"]) or {}).get("public_url")
             and eligible(c["episode_id"], eps, pkgs, held)]
    work = ROOT / "output/compilations" / a.week
    work.mkdir(parents=True, exist_ok=True)
    durations, paths = {}, {}
    for c in cands:
        eid = c["episode_id"]
        d = (assets.get(eid) or {}).get("duration_seconds")
        if not a.plan_only:
            p = work / f"{eid}.mp4"
            if not p.exists():
                urllib.request.urlretrieve(assets[eid]["public_url"], p)
            paths[eid], d = p, ffprobe_seconds(p)
        if d:
            durations[eid] = float(d)
    clips, total, ok = select(cands, durations, cfg.get("min_seconds", 360), cfg.get("max_seconds", 480))
    meta = metadata(a.week, clips, durations, eps)
    meta["within_6_8_min"] = ok
    (work / "compilation.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False) + "\n")
    (work / "description.txt").write_text(meta["description"] + "\n")
    print(f"[compilation] {a.week}: {len(clips)} of {len(cands)} Shorts, {ts(total)} ok={ok}")
    if len(clips) < 3:
        print("[compilation] fewer than 3 chapters; not rendering"); return 2
    if not a.plan_only:
        render([paths[c["episode_id"]] for c in clips], work / f"jr-compilation-{a.week}.mp4")
        print(f"[compilation] wrote {work / f'jr-compilation-{a.week}.mp4'}")
    return 0 if ok else 3


if __name__ == "__main__":
    sys.exit(main())
