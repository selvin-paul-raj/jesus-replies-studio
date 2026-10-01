#!/usr/bin/env python3
"""Measures real rendered durations. >90s or unreadable fails the run."""
import pathlib, struct, sys

CEILING = 90.0
ids = [i.strip() for i in sys.argv[1].split(",") if i.strip()]
bad = []
for eid in ids:
    p = pathlib.Path(f"output/videos/{eid}.mp4")
    if not p.is_file() or p.stat().st_size == 0:
        print(f"[qa] {eid} MISSING_OR_EMPTY"); bad.append(eid); continue
    data = p.read_bytes()
    i = data.find(b"mvhd")
    dur = 0.0
    if i != -1:
        ts, du = struct.unpack(">II", data[i + 12:i + 20])
        dur = round(du / ts, 2) if ts else 0.0
    status = "PASS" if 0 < dur <= CEILING else "FAIL"
    if status == "FAIL":
        bad.append(eid)
    print(f"[qa] {eid} duration={dur}s bytes={p.stat().st_size} {status}")
print(f"[qa] measured={len(ids)} failed={len(bad)}")
sys.exit(1 if bad else 0)
