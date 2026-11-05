"""The one Scripture source for episodes, daily verse cards and the Bible Month series.

Which translation is used is a single setting: config/content-os.json "scripture_version"
(KJV since 2026-11-05, DEC-JR-016; BSB 2026-10-16..11-04, DEC-JR-007; NIV before that).
Text is bundled locally (data/bible/<version>.json): no network, no licence limit, no AI-use
restriction. lookup() fails closed (returns None) for anything it cannot resolve exactly, so
an unknown reference is BLOCKED rather than guessed."""
import json, pathlib, re

ROOT = pathlib.Path(__file__).resolve().parents[2]
BIBLES = {
    "KJV": ("King James Version", "data/bible/kjv.json"),
    "BSB": ("Berean Standard Bible", "data/bible/bsb.json"),   # kept for the record; not the active text
}


def configured_version():
    try:
        v = json.loads((ROOT / "config/content-os.json").read_text(encoding="utf-8")).get("scripture_version")
    except (OSError, ValueError):
        v = None
    if v not in BIBLES:
        raise RuntimeError(f"config/content-os.json scripture_version={v!r} is not one of {sorted(BIBLES)}")
    return v


VERSION = configured_version()
LABEL = BIBLES[VERSION][0]
PATH = ROOT / BIBLES[VERSION][1]

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
    """Exact text of the active translation for a reference (verses joined by a space), or None."""
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
    """episode['bible'] -> 'Book C:V' using the bundled book names."""
    return f"{canonical_book(b.get('book'))} {b.get('chapter')}:{b.get('verse')}"


def label(text):
    """Swap an older translation tag for the active one in caption/description text."""
    for old in ("BSB", "NIV"):
        if old != VERSION:
            text = text.replace(f"({old})", f"({VERSION})").replace(f" {old}\n", f" {VERSION}\n")
            text = re.sub(rf"\b{old}\b", VERSION, text)
    return text
