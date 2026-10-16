#!/usr/bin/env python3
"""One-off (DEC-JR-009, 2026-10-16): bring already-written episodes JR-0047..JR-0063 up to the
deep-review rules before they are re-rendered: BSB verse text, (BSB) labels, honesty line,
'answered from Scripture', no 'in the comments' bait. Idempotent. Never touches published posts."""
import json, pathlib, re, sys
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from daily import bsb, safety
from daily.pipeline import norm_text

ROOT = pathlib.Path(__file__).resolve().parent.parent
ids = sys.argv[1:] or [f"JR-{n:04d}" for n in range(47, 64)]
H = safety.HONESTY_LINE
for eid in ids:
    ep_p, pk_p = ROOT / f"generated/{eid}.json", ROOT / f"generated/{eid}.package.json"
    ep, pk = json.loads(ep_p.read_text()), json.loads(pk_p.read_text())
    b = ep["bible"]; ref = f"{b['book']} {b['chapter']}:{b['verse']}"
    new = bsb.lookup(ref)
    if not new:
        sys.exit(f"{eid}: {ref} not in BSB")
    old = b["text"]
    b["text"], b["version"] = new, bsb.VERSION
    changes = []
    for f in ("instagram_caption", "youtube_description"):
        v = pk[f]
        for cand in {old, old.strip("\u201c\u201d\""), norm_text(old), norm_text(old).strip('"')}:
            if cand and cand in v:
                v = v.replace(cand, new.strip("\u201c\u201d\"")); break
        v = v.replace("(NIV)", "(BSB)")
        v = re.sub(r"answered in His words", "answered from Scripture", v, flags=re.I)
        v = re.sub(r"\s*Tell us in the comments\.?", "", v)
        if H not in v:
            lines = v.rstrip().split("\n")
            if f == "youtube_description" and lines and re.match(r"^\s*#\w", lines[-1]):
                v = "\n".join(lines[:-1]).rstrip() + "\n\n" + H + "\n\n" + lines[-1]
            else:
                v = v.rstrip() + "\n\n" + H
        if v != pk[f]: changes.append(f)
        pk[f] = v
    if "NIV" in json.dumps(pk) or (norm_text(old) != norm_text(new) and norm_text(old)[:40] in norm_text(json.dumps(pk, ensure_ascii=False))):
        print(f"WARN {eid}: old NIV text or label still present")
    probs = safety.package_problems(pk, safety.crisis_check(ep, pk)[0])
    ep_p.write_text(json.dumps(ep, indent=2, ensure_ascii=False) + "\n")
    pk_p.write_text(json.dumps(pk, indent=2, ensure_ascii=False) + "\n")
    print(eid, ref, "changed:", changes, "problems:", probs, "crisis:", safety.crisis_check(ep, pk))
