#!/usr/bin/env python3
"""Authoring gate for the manual render workflow. Fails closed."""
import json, pathlib, sys

ids = [i.strip() for i in sys.argv[1].split(",") if i.strip()]
if not ids:
    print("[gate] no episode ids given"); sys.exit(1)
bad = False
for eid in ids:
    p = pathlib.Path(f"generated/{eid}.json")
    if not p.is_file() or p.stat().st_size == 0:
        print(f"[gate] {eid} MISSING generated/{eid}.json"); bad = True; continue
    ep = json.loads(p.read_text())
    b = ep.get("bible") or {}
    if not b.get("text") or b.get("version") != "NIV":
        print(f"[gate] {eid} scripture missing or not NIV"); bad = True; continue
    if not ep.get("lines"):
        print(f"[gate] {eid} no lines"); bad = True; continue
    print(f"[gate] {eid} OK scripture={b['book']} {b['chapter']}:{b['verse']} lines={len(ep['lines'])}")
sys.exit(1 if bad else 0)
