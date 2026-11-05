#!/usr/bin/env python3
"""Bundle the Tamil and Hindi Indian Revised Version (IRV) texts like data/bible/kjv.json (DEC-JR-018).

Source: eBible.org VPL archives (tam2017_vpl.zip, hin2017_vpl.zip), (c) 2017-2019 Bridge Connectivity
Solutions, licensed CC BY-SA 4.0. Keys are the English keys of data/bible/kjv.json ("Psalm 23:1"), so a
subtitle version looks up the same reference as the episode's KJV verse.

Processing (the only change to the text, recorded in the file and in every caption attribution):
  hin2017 only: inline cross-reference brackets such as "(इब्रा. 1:10, इब्रा. 11:3)" are removed.
  Wording is otherwise byte-for-byte as eBible prints it (Psalm superscriptions stay in verse 1).
Usage: python3 scripts/subtitles/build_irv_bibles.py /path/tam2017_vpl.txt /path/hin2017_vpl.txt"""
import json, pathlib, re, sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
XREF = re.compile(r"\s*\((?=[^()]*\d+:\d+)[^()]*\)")
META = {
    "ta": {"id": "tam2017", "file": "data/bible/ta-irv.json",
           "translation": "Tamil Indian Revised Version (IRV Tamil, இண்டியன் ரிவைஸ்டு வெர்ஸன்)",
           "copyright": "Copyright © 2017, 2019 Bridge Connectivity Solutions Pvt. Ltd."},
    "hi": {"id": "hin2017", "file": "data/bible/hi-irv.json",
           "translation": "Hindi Indian Revised Version (IRV Hindi, इंडियन रिवाइज्ड वर्जन)",
           "copyright": "Copyright © 2017, 2018, 2019 Bridge Connectivity Solutions Pvt. Ltd."},
}


def kjv_books():
    seen = []
    for k in json.loads((ROOT / "data/bible/kjv.json").read_text(encoding="utf-8"))["verses"]:
        b = k.rsplit(" ", 1)[0]
        if b not in seen:
            seen.append(b)
    return seen


def parse(vpl, strip_xref):
    books, out, changed = kjv_books(), {}, 0
    order = []
    for line in pathlib.Path(vpl).read_text(encoding="utf-8").splitlines():
        m = re.match(r"^([1-3A-Z]{3}) (\d+):(\d+) (.*)$", line.strip())
        if not m:
            continue
        ab, ch, v, text = m.groups()
        if ab not in order:
            order.append(ab)
        if len(order) > len(books):
            raise SystemExit(f"more books than the KJV canon at {ab}")
        if strip_xref:
            new = XREF.sub("", text).strip()
            changed += new != text
            text = new
        out[f"{books[order.index(ab)]} {int(ch)}:{int(v)}"] = text.strip()
    return out, changed, order


def verse_count_check(verses):
    kjv = set(json.loads((ROOT / "data/bible/kjv.json").read_text(encoding="utf-8"))["verses"])
    mine = set(verses)
    return {"verses": len(verses), "kjv_verses": len(kjv), "missing_vs_kjv": sorted(kjv - mine),
            "extra_vs_kjv": sorted(mine - kjv), "empty": sorted(k for k, t in verses.items() if not t)}


def main(tam, hin):
    for lang, vpl in (("ta", tam), ("hi", hin)):
        M = META[lang]
        verses, changed, order = parse(vpl, strip_xref=(lang == "hi"))
        check = verse_count_check(verses)
        doc = {"translation": M["translation"], "language": lang, "copyright": M["copyright"],
               "license": "Creative Commons Attribution-ShareAlike 4.0 International (CC BY-SA 4.0), https://creativecommons.org/licenses/by-sa/4.0/",
               "source": f"https://ebible.org/Scriptures/{M['id']}_vpl.zip (eBible.org, details https://ebible.org/find/details.php?id={M['id']}; downloaded 2026-11-05)",
               "attribution_line": ATTR[lang],
               "processing": ("66 books, keys mapped by canonical order to data/bible/kjv.json book names. " +
                              (f"Inline cross-reference brackets removed from {changed} verses; wording otherwise unchanged. "
                               if lang == "hi" else "Text unchanged. ") +
                              "Psalm superscriptions stay in verse 1 as eBible prints them."),
               "share_alike": "This bundled file is a lightly processed copy of a CC BY-SA 4.0 text and is itself CC BY-SA 4.0.",
               "verification": check, "verses": verses}
        p = ROOT / M["file"]
        p.write_text(json.dumps(doc, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
        print(lang, p.relative_to(ROOT), "verses", check["verses"], "missing", len(check["missing_vs_kjv"]),
              "extra", len(check["extra_vs_kjv"]), "empty", len(check["empty"]), "xref-stripped", changed)


ATTR = {
    "ta": "Tamil Scripture: IRV Tamil © 2017, 2019 Bridge Connectivity Solutions, CC BY-SA 4.0 (ebible.org).",
    "hi": "Hindi Scripture: IRV Hindi © 2017-2019 Bridge Connectivity Solutions, CC BY-SA 4.0 (ebible.org); cross-references omitted.",
}

if __name__ == "__main__":
    main(*sys.argv[1:3])
