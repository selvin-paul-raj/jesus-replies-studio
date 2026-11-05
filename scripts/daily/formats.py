"""DEC-JR-018 growth formats: checks the validator and package QA run on top of every existing gate.

1. Part 2 (sequel): `part_of` set -> the caption points back to Part 1 by title ("Part 1").
2. "Jesus replies to your comment": `format: comment-reply` + `comment` -> the comment is real (its text is in a
   community log), respectful (no crisis terms, no bait), and shown with the handle hidden unless policy allows it.
3. Subtitle versions: `subtitles` -> language enabled by config, lines align 1:1 with the script, the verse caption
   is the bundled IRV text verbatim for the SAME reference as the KJV verse, and the IRV attribution line is in the
   caption and the description. Story lines are human translations; scripture is never machine-translated.
A variant (`variant_of`) is a re-cut of an existing episode, so originality is not checked against its own source."""
import json, pathlib, re
from . import safety, scripture

ROOT = pathlib.Path(__file__).resolve().parents[2]


def _cfg(root):
    try:
        return json.loads((pathlib.Path(root) / "config/content-os.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _norm(s):
    s = (s or "").replace("\u2019", "'").replace("\u2018", "'").replace("\u201c", '"').replace("\u201d", '"')
    return re.sub(r"\s+", " ", s).strip()


def comment_problems(ep, root=ROOT):
    c = ep.get("comment") or {}
    cfg = _cfg(root).get("comment_reply") or {}
    probs = []
    text = (c.get("text") or "").strip()
    if not text:
        return ["comment-reply episode without comment.text"]
    srcs = cfg.get("sources") or ["content-os/community/replies-log.md", "content-os/community/ideas.md"]
    logged = " ".join(_norm((pathlib.Path(root) / s).read_text(encoding="utf-8")) for s in srcs if (pathlib.Path(root) / s).exists())
    if _norm(text) not in logged:
        probs.append("comment text is not in content-os/community/replies-log.md or ideas.md (only real, logged comments)")
    flagged, found = safety.crisis_check({"lines": [{"text": text}]})
    if flagged:
        probs.append(f"crisis comment {sorted(found)}: answer it with the helpline reply, never as an episode")
    if safety._BAIT_WORDS.search(text) and re.search(r"\b(?:send me|amen)\b", text, re.I):
        probs.append("bait comment ('send me this post' / 'amen') is not material")
    if re.search(r"@\w", text):
        probs.append("comment text shows a handle; hide it")
    show = bool(c.get("show_handle")) and bool(cfg.get("show_handle"))
    if c.get("show_handle") and not cfg.get("show_handle"):
        probs.append("comment.show_handle true but config comment_reply.show_handle is false (handle hidden by default)")
    if c.get("handle") and not show:
        probs.append("comment.handle is set while the handle is hidden; leave it null")
    return probs


def subtitle_problems(ep, root=ROOT):
    sub = ep.get("subtitles") or {}
    sv = _cfg(root).get("subtitle_versions") or {}
    lang = sub.get("lang")
    probs = []
    L = (sv.get("languages") or {}).get(lang) or {}
    if not (sv.get("enabled") and L.get("enabled")):
        probs.append(f"subtitle language {lang!r} is not enabled in config subtitle_versions")
        return probs
    path = pathlib.Path(root) / (L.get("bible") or f"data/bible/{lang}-irv.json")
    if not path.exists():
        return probs + [f"bundled text {path.name} missing"]
    doc = json.loads(path.read_text(encoding="utf-8"))
    lines = ep.get("lines") or []
    subs = sub.get("lines") or []
    if len(subs) != len(lines):
        probs.append(f"subtitles.lines has {len(subs)} entries for {len(lines)} script lines")
    for i, (l, s) in enumerate(zip(lines, subs)):
        if l.get("speaker") == "bible_verse":
            if s:
                probs.append(f"subtitles.lines[{i}] must be null at the verse (the verse caption comes from the bundled text)")
        elif not (s or "").strip():
            probs.append(f"subtitles.lines[{i}] empty for a {l.get('speaker')} line")
    ref = scripture.ref_from_bible(ep.get("bible") or {})
    want = doc["verses"].get(ref)
    if want is None:
        probs.append(f"{ref} not in {path.name}")
    elif (sub.get("verse_text") or "") != want:
        probs.append(f"subtitle verse for {ref} is not verbatim from {path.name} (never machine-translate scripture)")
    if ref not in (sub.get("verse_label") or ""):
        probs.append(f"subtitles.verse_label must name {ref}")
    if (sub.get("attribution") or "") != doc.get("attribution_line"):
        probs.append(f"subtitles.attribution must be exactly the bundle's attribution_line")
    return probs


def script_problems(ep, root=ROOT):
    """Validator stage."""
    probs = []
    if ep.get("format") == "comment-reply" or ep.get("comment"):
        probs += comment_problems(ep, root)
    if ep.get("subtitles"):
        probs += subtitle_problems(ep, root)
    if ep.get("variant_of") and not ep.get("subtitles"):
        probs.append("variant_of is only for subtitle versions (DEC-JR-018)")
    return probs


def package_problems(ep, pk, root=ROOT):
    """Package QA stage."""
    probs = []
    if ep.get("part_of") or (ep.get("part") or 0) >= 2:
        cap = pk.get("instagram_caption") or ""
        if not re.search(r"\bPart 2\b", cap) or not re.search(r"\bPart 1\b", cap):
            probs.append("sequel caption must say 'Part 2' and point back to 'Part 1' by its title")
        if not re.search(r"\bPart 1\b", pk.get("youtube_description") or ""):
            probs.append("sequel description must point back to Part 1")
    if ep.get("subtitles"):
        att = (ep["subtitles"].get("attribution") or "").strip()
        for f in ("instagram_caption", "youtube_description"):
            if not att or att not in (pk.get(f) or ""):
                probs.append(f"IRV attribution line missing from {f} (CC BY-SA 4.0 requires it)")
    return probs


def source_of(ep):
    """The episode a variant re-cuts (exempt from originality against itself)."""
    return ep.get("variant_of")
