#!/usr/bin/env python3
"""Exact-passage scripture resolution from Bible Gateway (NIV), the same source used
for JR-0021 to JR-0023. No API key, no model. Fails closed: if the exact reference
cannot be read, the episode is left UNRESOLVED and must not render."""
import re, sys, json, urllib.request, html

UA = {"User-Agent": "Mozilla/5.0 (jesus-replies-studio scripture resolver)"}

def fetch(ref, version="NIV"):
    url = f"https://www.biblegateway.com/passage/?search={urllib.parse.quote(ref)}&version={version}"
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=40) as r:
        page = r.read().decode("utf8", "replace")
    m = re.search(r'<div class=["\']passage-text["\']>(.*?)</div>\s*</div>', page, re.S)
    if not m: return None
    body = m.group(1)
    body = re.sub(r"<sup[^>]*>.*?</sup>", " ", body, flags=re.S)       # verse numbers
    body = re.sub(r"<h[1-6][^>]*>.*?</h[1-6]>", " ", body, flags=re.S) # section titles
    body = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", body, flags=re.S)
    text = html.unescape(re.sub(r"<[^>]+>", " ", body))
    text = re.sub(r"\s+", " ", text).strip()
    text = re.sub(r"\s*(Read full chapter|Footnotes).*$", "", text).strip()
    return text or None

if __name__ == "__main__":
    out = {}
    for ref in sys.argv[1:]:
        t = fetch(ref)
        out[ref] = t
        print(f"{'OK  ' if t else 'FAIL'} {ref}: {(t or 'unresolved')[:90]}")
    print(json.dumps(out), file=sys.stderr)
