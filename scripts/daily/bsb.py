"""Deprecated alias kept so old imports keep working: Scripture now comes from
scripts/daily/scripture.py, whose translation is config/content-os.json "scripture_version"
(KJV since 2026-11-05, DEC-JR-016). Importing this module gives the ACTIVE translation, not BSB."""
from .scripture import *            # noqa: F401,F403
from .scripture import VERSION, LABEL, PATH, lookup, ref_from_bible, parse_ref, canonical_book, verses  # noqa: F401
