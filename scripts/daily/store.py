"""Per-episode state files, the canonical manifest, and per-episode locks."""
import datetime as dt, json, os, pathlib, re, tempfile
from . import states
from .redact import redact

ID_RE = re.compile(r"^JR-(\d{4})$")


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _atomic_write(path: pathlib.Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=".tmp-")
    with os.fdopen(fd, "w") as f:
        f.write(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
    os.replace(tmp, path)


def blank_state(eid: str) -> dict:
    return {"episode_id": eid, "state": states.NEW, "updated_at": None, "slot": None,
            "target_date": None, "generation": "NOT_STARTED", "validation": "NOT_STARTED",
            "render": "NOT_STARTED", "render_qa": "NOT_STARTED", "package": "NOT_STARTED",
            "package_qa": "NOT_STARTED", "asset_hosting": "NOT_STARTED", "asset_url": None,
            "render_facts": {}, "buffer": {"post_id": None, "status": None, "due_at": None,
                                           "sent_at": None, "pending_mutation": None},
            "approval": {"status": "NOT_REQUESTED", "approved_at": None, "approved_by": None,
                         "slot_local": None, "due_at": None, "evidence": None},
            "verification": {"status": "NOT_VERIFIED", "verified_at": None},
            "errors": [], "history": []}


class Store:
    def __init__(self, root=".", state_dir="episodes", dry_run=False):
        self.root = pathlib.Path(root)
        self.state_dir = self.root / state_dir
        self.dry_run = dry_run

    # ---------- state ----------
    def path(self, eid):
        if not ID_RE.match(eid):
            raise ValueError(f"bad episode id {eid!r}")
        return self.state_dir / eid / "state.json"

    def load(self, eid) -> dict:
        p = self.path(eid)
        return json.loads(p.read_text()) if p.exists() else blank_state(eid)

    def save(self, st: dict) -> None:
        _atomic_write(self.path(st["episode_id"]), st)

    def transition(self, st: dict, to: str, evidence: str, run_id: str = "local") -> dict:
        frm = st["state"]
        states.check(frm, to)
        ts = now_iso()
        st["history"].append({"at": ts, "from": frm, "to": to, "run": run_id,
                              "evidence": redact(evidence)[:500]})
        st["state"], st["updated_at"] = to, ts
        if to in states.FAILURES:
            st["errors"].append({"at": ts, "state": to, "detail": redact(evidence)[:500]})
        self.save(st)
        return st

    def reopen(self, st: dict, reason: str, run_id="local") -> dict:
        """Re-enter a failed episode at the step that failed (never past it)."""
        back = states.RETRY_FROM.get(st["state"])
        if back is None:
            raise states.TransitionError(f"{st['state']} cannot be reopened automatically")
        ts = now_iso()
        st["history"].append({"at": ts, "from": st["state"], "to": back, "run": run_id,
                              "evidence": f"reopen: {redact(reason)[:300]}"})
        st["state"], st["updated_at"] = back, ts
        self.save(st)
        return st

    # ---------- locks ----------
    def _lock_path(self, eid):
        return self.state_dir / eid / ".lock"

    def acquire(self, eid, run_id, ttl_minutes=90) -> bool:
        lp = self._lock_path(eid)
        lp.parent.mkdir(parents=True, exist_ok=True)
        if lp.exists():
            cur = json.loads(lp.read_text() or "{}")
            exp = dt.datetime.fromisoformat(cur.get("expires_at", "1970-01-01T00:00:00+00:00").replace("Z", "+00:00"))
            if cur.get("run_id") != run_id and exp > dt.datetime.now(dt.timezone.utc):
                return False
            lp.unlink()
        exp = dt.datetime.now(dt.timezone.utc) + dt.timedelta(minutes=ttl_minutes)
        try:
            fd = os.open(lp, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            return False
        with os.fdopen(fd, "w") as f:
            json.dump({"run_id": run_id, "acquired_at": now_iso(),
                       "expires_at": exp.replace(microsecond=0).isoformat()}, f)
        return True

    def release(self, eid, run_id) -> None:
        lp = self._lock_path(eid)
        if lp.exists() and json.loads(lp.read_text() or "{}").get("run_id") == run_id:
            lp.unlink()

    # ---------- manifest ----------
    def manifest_path(self):
        return self.root / "manifests" / "episodes.json"

    def load_manifest(self) -> list:
        p = self.manifest_path()
        return json.loads(p.read_text()) if p.exists() else []

    def upsert_manifest(self, st: dict, title=None) -> None:
        rows = self.load_manifest()
        ids = [r["episode_id"] for r in rows]
        if len(ids) != len(set(ids)):
            raise RuntimeError("manifest already contains duplicate episode ids")
        row = next((r for r in rows if r["episode_id"] == st["episode_id"]), None)
        if row is None:
            row = {"episode_id": st["episode_id"], "created_at": now_iso()}
            rows.append(row)
        row.update({"title": title or row.get("title"), "slot": st.get("slot"),
                    "target_date": st.get("target_date"), "state": st["state"],
                    "asset_url": st.get("asset_url"), "buffer_post_id": st["buffer"]["post_id"],
                    "scheduled_at": st["buffer"]["due_at"] if st["state"] in
                    ("SCHEDULED", "PUBLISHED", "PUBLISHED_VERIFIED") else None,
                    "published_at": st["buffer"]["sent_at"],
                    "verification_status": st["verification"]["status"]})
        rows.sort(key=lambda r: r["episode_id"])
        _atomic_write(self.manifest_path(), rows)

    def slot_owner(self, date: str, slot: str):
        for r in self.load_manifest():
            if r.get("target_date") == date and r.get("slot") == slot:
                return r["episode_id"]
        return None
