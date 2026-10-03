"""Episode catalogue + structured content attributes (sidecar files, the episode schema is untouched)."""
import json, re, pathlib

EP_RE = re.compile(r"^JR-\d{4}(-[A-Z])?\.json$")


def load_catalogue(root):
    root = pathlib.Path(root)
    eps, pkgs = {}, {}
    for d in ("Input", "generated"):
        for f in sorted((root / d).glob("JR-*.json")):
            if EP_RE.match(f.name):
                e = json.loads(f.read_text())
                eps[e["id"]] = e
    for f in sorted((root / "generated").glob("JR-*.package.json")):
        pkgs[f.name.split(".")[0]] = json.loads(f.read_text())
    assets = {}
    mf = root / "generated/release-manifest.json"
    if mf.exists():
        for r in json.loads(mf.read_text()):
            assets[r["episode_id"]] = r
    return eps, pkgs, assets


def hook_of(ep):
    for l in ep.get("lines", []):
        if l.get("speaker") == "person" and l.get("text"):
            return l["text"]
    return ""


def derive_attributes(ep, pkg=None, asset=None, platforms=("instagram", "youtube")):
    lines = ep.get("lines", [])
    hook = hook_of(ep)
    if "?" in hook:
        hook_type = "question"
    elif re.match(r"^jesus[.\u2026,\s]*(i|i'm|my|tomorrow)\b", hook, re.I):
        hook_type = "confession_statement"
    else:
        hook_type = "statement"
    first_j = next((i for i, l in enumerate(lines) if l.get("speaker") == "jesus"), len(lines))
    pushbacks = sum(1 for l in lines[first_j:] if l.get("speaker") == "person")
    story_type = "full_arc_two_pushbacks" if pushbacks >= 2 else ("one_pushback" if pushbacks == 1 else "direct_answer")
    eng = next((l.get("text", "") for l in lines if l.get("speaker") == "engagement"), "")
    sentences = [s for s in re.split(r"(?<=[.?!])\s+", eng.strip()) if s]
    if not eng:
        cta_type = "none"
    elif "?" in eng and len(sentences) > 1:
        cta_type = "comment_question_plus_action"
    elif "?" in eng:
        cta_type = "comment_question"
    else:
        cta_type = "reflection_statement"
    b = ep.get("bible") or {}
    return {
        "episode_id": ep["id"], "theme": ep.get("topic"), "emotion": ep.get("emotion"),
        "character": ep.get("character"), "hook_type": hook_type, "hook": hook,
        "story_type": story_type, "audience_problem": ep.get("topic"),
        "bible_theme": f"{b.get('book')} {b.get('chapter')}:{b.get('verse')}" if b else None,
        "bible_book": b.get("book"), "cta_type": cta_type,
        "duration": (asset or {}).get("duration_seconds"), "platforms": list(platforms),
        "has_package": pkg is not None, "hosted_url": (asset or {}).get("public_url"),
        "derived_by": "content_os.episodes.derive_attributes v1",
        "inferred_fields": ["hook_type", "story_type", "cta_type", "audience_problem"],
    }


def write_attributes(root, eps, pkgs, assets):
    out = pathlib.Path(root) / "generated/attributes"
    out.mkdir(parents=True, exist_ok=True)
    attrs = {}
    for eid, ep in sorted(eps.items()):
        a = derive_attributes(ep, pkgs.get(eid), assets.get(eid))
        attrs[eid] = a
        (out / f"{eid}.attributes.json").write_text(json.dumps(a, indent=2, ensure_ascii=False) + "\n")
    return attrs
