"""Berean Standard Bible (public domain), bundled at data/bible/bsb.json.

The single Scripture source for episodes and the daily verse card since 2026-10-16
(DEC-JR-007). Replaces the NIV + Bible Gateway scraping: no network, no licence limit,
no AI-use restriction. lookup() fails closed (returns None) for anything it cannot
resolve exactly, so an unknown reference is BLOCKED rather than guessed."""
import json, pathlib, re

VERSION = "BSB"
LABEL = "Berean Standard Bible"
PATH = pathlib.Path(__file__).resolve().parents[2] / "data/bible/bsb.json"

ALIASES = {"psalms": "Psalm", "psalm": "Psalm", "ps": "Psalm", "song of songs": "Song of Solomon",
           "song of solomon": "Song of Solomon", "canticles": "Song of Solomon",
           "revelations": "Revelation", "qoheleth": "Ecclesiastes", "phil": "Philippians",
           "zech": "Zechariah", "rom": "Romans", "matt": "Matthew", "isa": "Isaiah", "jer": "Jeremiah"}
_CACHE = {}


def verses(path=None):
    p = pathlib.Path(path or PATH)
    if p not in _CACHE:
        _CACHE[p] = json.loads(p.read_text(encoding="utf-8"))["verses"]
    return _CACHE[p]


def canonical_book(book):
    b = re.sub(r"\s+", " ", (book or "").strip()).rstrip(".")
    return ALIASES.get(b.lower(), b)


REF_RE = re.compile(r"^\s*(.+?)\s+(\d+):([\d\s,\-\u2013]+)$")


def parse_ref(ref):
    """'Psalms 23:1', 'Romans 8:28-29', 'Psalm 65:2,5' -> (book, chapter, [verse numbers]) or None."""
    m = REF_RE.match((ref or "").strip())
    if not m:
        return None
    nums = []
    for part in m.group(3).replace("\u2013", "-").split(","):
        part = part.strip()
        if not part:
            return None
        a, _, b = part.partition("-")
        if not a.strip().isdigit() or (b and not b.strip().isdigit()):
            return None
        v1, v2 = int(a), int(b or a)
        if v2 < v1 or v2 - v1 > 10:
            return None
        nums += list(range(v1, v2 + 1))
    return canonical_book(m.group(1)), int(m.group(2)), nums


def lookup(ref, path=None):
    """Exact BSB text for a reference (verses joined by a space), or None if any verse is missing."""
    p = parse_ref(ref)
    if not p or len(p[2]) > 12:
        return None
    book, ch, nums = p
    V = verses(path)
    out = []
    for v in nums:
        t = V.get(f"{book} {ch}:{v}")
        if t is None:
            return None
        out.append(t)
    return " ".join(out)


def ref_from_bible(b):
    """episode['bible'] -> 'Book C:V' using the BSB book name."""
    return f"{canonical_book(b.get('book'))} {b.get('chapter')}:{b.get('verse')}"
