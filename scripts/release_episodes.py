#!/usr/bin/env python3
"""Create one release for a named episode list, upload the mp4s, verify the public
URLs anonymously, and merge the verified rows into generated/release-manifest.json.

Fails closed. Never touches a release tag other than the one passed in, never
deletes or recreates a release, never invents a URL."""
import hashlib, json, os, pathlib, subprocess, sys, urllib.request

tag = os.environ["TAG"]
repo = os.environ["REPO"]
ids = [i.strip() for i in sys.argv[1].split(",") if i.strip()]
PROTECTED = {"jr-week-2026-10-05"}
if tag in PROTECTED:
    sys.exit(f"[release] refusing to touch protected tag {tag}")

files = []
for eid in ids:
    f = pathlib.Path(f"output/videos/{eid}.mp4")
    if not f.exists():
        sys.exit(f"[release] missing render for {eid}")
    files.append(f)

def gh(*a, **kw):
    return subprocess.run(["gh", *a], capture_output=True, text=True, **kw)

if gh("release", "view", tag).returncode == 0:
    existing = json.loads(gh("release", "view", tag, "--json", "assets", check=True).stdout)
    names = sorted(a["name"] for a in existing["assets"] if a["name"].endswith(".mp4"))
    if names and names != sorted(f.name for f in files):
        sys.exit(f"[release] AMBIGUOUS existing release {tag} with assets {names}, failing closed")
    print(f"[release] reusing existing {tag}")
else:
    gh("release", "create", tag, "--title", f"Jesus Replies episodes {tag}",
       "--notes", "Temporary public media storage for these episodes. "
                  "Separate from the weekly batch releases.", check=True)
    print(f"[release] created {tag}")

for f in files:
    gh("release", "upload", tag, str(f), "--clobber", check=True)
    print(f"[release] uploaded {f.name}")

meta = json.loads(gh("release", "view", tag, "--json", "assets,createdAt,tagName", check=True).stdout)
assets = {a["name"]: a for a in meta["assets"] if a["name"].endswith(".mp4")}
if sorted(assets) != sorted(f.name for f in files):
    sys.exit(f"[release] asset set mismatch: {sorted(assets)}")

durs = {r["episode"]: r["duration_s"]
        for r in json.loads(pathlib.Path("output/durations.json").read_text())}

rows, fails = [], []
for f in files:
    eid, a = f.stem, assets[f.name]
    local = f.read_bytes()
    url = f"https://github.com/{repo}/releases/download/{tag}/{f.name}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "jr-url-verify"})
        with urllib.request.urlopen(req, timeout=120) as r:  # anonymous, no token
            body = r.read()
        served_sha = hashlib.sha256(body).hexdigest()
        ok = (r.status == 200 and url.startswith("https://") and b"ftyp" in body[:32]
              and served_sha == hashlib.sha256(local).hexdigest()
              and len(body) == len(local) == a["size"])
        detail = f"{len(body)}B sha_match={served_sha == hashlib.sha256(local).hexdigest()}"
    except Exception as ex:
        ok, detail, served_sha = False, f"ERROR {ex}", None
    print(f"[url] {eid} {'PASS' if ok else 'FAIL'} {detail} {url}")
    if not ok:
        fails.append(eid)
    rows.append({"release_tag": tag, "created_at": meta["createdAt"], "episode_id": eid,
                 "asset_name": f.name, "public_url": url, "duration_seconds": durs.get(eid),
                 "size_bytes": a["size"], "sha256": hashlib.sha256(local).hexdigest(),
                 "qa_status": "PASS" if ok else "FAIL"})

mp = pathlib.Path("generated/release-manifest.json")
prior = json.loads(mp.read_text()) if mp.exists() else []
kept = [r for r in prior if r.get("release_tag") != tag]
mp.write_text(json.dumps(kept + rows, indent=2) + "\n")
print(f"[manifest] prior={len(prior)} kept={len(kept)} added={len(rows)} total={len(kept)+len(rows)}")
print(f"[url] verified={len(files)-len(fails)}/{len(files)}")
sys.exit(1 if fails else 0)
