"""Autopilot: the closed loop that keeps every slot filled without a human gate.

Authorised by Selvin on 2026-10-11 20:48 IST (see content-os/DECISIONS.md, DEC-JR-005).
Every automated QA gate stays in force; only the human approval step is gone.

  targets()      episodes the daily generator should render/advance next (reserved slots
                 inside the horizon first, then authored spares to grow the ready buffer)
  sync_states()  daily state machine follows the distributor (APPROVED -> SCHEDULED -> PUBLISHED)
  fill_slots()   a reserved episode that is unauthored, exhausted by self-healing, or still not
                 ready close to its slot is swapped for a READY spare; the plan is re-hashed and
                 re-authorised under the standing authorization (a slot is never left empty)
  buffer_report() ready-buffer count + authoring queue when it falls below target
"""
import datetime as dt, json, pathlib, re
from .brain import plan_sha
from .timing import IST
from .analytics import parse

LIVE = ("SCHEDULED", "PUBLISHED", "PUBLISHED_VERIFIED")
STD = re.compile(r"^JR-\d{4}$")


def _r(p, default=None):
    return json.loads(p.read_text()) if p.exists() else default


def _w(p, obj):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n")


def settings(cfg):
    a = dict(horizon_days=3, ready_buffer_target=6, max_heal_attempts=3, substitute_lead_hours=30,
             max_advance_per_run=4)
    a.update(cfg.get("autopilot") or {})
    return a


class Autopilot:
    def __init__(self, root, cfg, eps, pkgs, assets, dist_store, daily_store, now, run="local", log=print):
        self.root, self.cfg, self.now, self.run, self.log = pathlib.Path(root), cfg, now, run, log
        self.eps = {k: v for k, v in eps.items() if STD.match(k)}     # skip variants like JR-0005-M
        self.pkgs, self.assets = pkgs, assets
        self.dists, self.daily = dist_store, daily_store
        self.s = settings(cfg)
        self.held = cfg.get("held_episodes", {})

    # ---------------------------------------------------------------- reads
    def weeks(self):
        today = self.now.astimezone(IST).date()
        monday = today - dt.timedelta(days=today.weekday())
        out = []
        for wk in (monday, monday + dt.timedelta(days=7)):
            wd = self.root / "content-os/weeks" / wk.isoformat()
            plan = _r(wd / "weekly-content-plan.json")
            if plan:
                out.append((wd, plan, _r(wd / "authorization.json")))
        return out

    def upcoming(self):
        """(week_dir, plan, slot, earliest due) for slots not yet due, earliest first."""
        rows = []
        for wd, plan, auth in self.weeks():
            for s in plan["slots"]:
                due = min(parse(v) for v in s["due_at"].values())
                if due > self.now:
                    rows.append((wd, plan, s, due))
        return sorted(rows, key=lambda r: r[3])

    def platform_states(self, eid):
        d = self.dists.load(eid)
        return {p: b["state"] for p, b in d["platforms"].items()}

    def is_ready(self, eid):
        a = self.assets.get(eid) or {}
        return eid in self.eps and eid in self.pkgs and eid not in self.held \
            and a.get("qa_status") == "PASS" and bool(a.get("public_url"))

    def exhausted(self, eid):
        st = self.daily.load(eid)
        return bool((st.get("heal") or {}).get("exhausted"))

    def status(self, eid):
        ps = self.platform_states(eid)
        if any(v in LIVE for v in ps.values()):
            return "LIVE"
        if self.is_ready(eid):
            return "READY"
        if eid in self.held:
            return "HELD"
        if eid not in self.eps:
            return "UNAUTHORED"
        if self.exhausted(eid):
            return "EXHAUSTED"
        return "IN_PIPELINE"

    def published_anywhere(self, eid):
        return any(v in ("PUBLISHED", "PUBLISHED_VERIFIED") for v in self.platform_states(eid).values())

    def reserved_ids(self):
        return {s["episode_id"] for _, _, s, _ in self.upcoming()}

    def spares(self):
        """READY episodes nobody upcoming owns, never published or scheduled anywhere."""
        res = self.reserved_ids()
        return [e for e in sorted(self.eps) if e not in res and self.status(e) == "READY"
                and all(v in ("NONE", "DRAFT") for v in self.platform_states(e).values())]

    # ---------------------------------------------------------------- targets for the generator
    def targets(self):
        horizon = self.now + dt.timedelta(days=self.s["horizon_days"])
        out = []
        for _, _, s, due in self.upcoming():
            eid = s["episode_id"]
            if due <= horizon and self.status(eid) == "IN_PIPELINE":
                out.append(eid)
        for eid in sorted(self.eps):         # then authored spares, oldest first, to grow the buffer
            if eid not in out and _num(eid) >= 38 and self.status(eid) == "IN_PIPELINE":
                out.append(eid)
        return out[: self.s["max_advance_per_run"]]

    # ---------------------------------------------------------------- state sync
    def sync_states(self, auth):
        """Daily state follows the distributor. Never mutates Buffer."""
        from daily.store import now_iso
        changed = []
        for eid in sorted(self.eps):
            p = self.daily.path(eid)
            if not p.exists():
                continue
            st = self.daily.load(eid)
            ig = self.dists.load(eid)["platforms"].get("instagram", {})
            before = st["state"]
            try:
                if st["state"] == "WAITING_FOR_USER" and auth and eid not in self.held \
                        and (st.get("review") or {}).get("status") != "HELD_FOR_REVIEW":
                    st["approval"].update({"status": "APPROVED", "approved_at": now_iso(), "approved_by": "standing authorization",
                                           "evidence": f"{auth['given']}: {auth['quote']}"[:300]})
                    self.daily.transition(st, "APPROVED", f"standing authorization {auth['given']} (human gate removed)", self.run)
                if st["state"] == "APPROVED" and ig.get("state") in LIVE:
                    st["buffer"].update(post_id=ig.get("post_id") or st["buffer"]["post_id"], status="scheduled", due_at=ig.get("due_at"))
                    st["approval"]["due_at"] = ig.get("due_at")
                    self.daily.transition(st, "SCHEDULED", f"distributor scheduled instagram {ig.get('post_id')} at {ig.get('due_at')}", self.run)
                if st["state"] == "SCHEDULED" and ig.get("state") in ("PUBLISHED", "PUBLISHED_VERIFIED"):
                    st["buffer"].update(status="sent", sent_at=ig.get("sent_at"))
                    self.daily.transition(st, "PUBLISHED", f"distributor: instagram sent {ig.get('sent_at')}", self.run)
                if st["state"] == "PUBLISHED" and ig.get("state") == "PUBLISHED_VERIFIED":
                    st["verification"] = {"status": "PUBLISHED_VERIFIED", "verified_at": now_iso()}
                    self.daily.transition(st, "PUBLISHED_VERIFIED", f"distributor verified {ig.get('external_link')}", self.run)
            except Exception as e:      # illegal edge: leave it, report it
                self.log(f"[sync] {eid} {st['state']}: {e}")
            if st["state"] != before:
                self.daily.upsert_manifest(st, self.eps[eid].get("title"))
                changed.append((eid, before, st["state"]))
        return changed

    # ---------------------------------------------------------------- slot filling
    def fill_slots(self, auth_source):
        """Swap a slot's episode for a READY spare when its own episode cannot make it."""
        lead = dt.timedelta(hours=self.s["substitute_lead_hours"])
        min_lead = dt.timedelta(minutes=self.cfg["min_lead_minutes"])
        pool = self.spares()
        swaps, touched = [], {}
        for wd, plan, s, due in self.upcoming():
            if due < self.now + min_lead:
                continue
            eid = s["episode_id"]
            st = self.status(eid)
            if st in ("LIVE", "READY"):
                continue
            ps = self.platform_states(eid)
            if any(v != "NONE" for v in ps.values()):
                continue                       # some Buffer object exists for it: never swap blindly
            if not (st in ("UNAUTHORED", "EXHAUSTED", "HELD") or (st == "IN_PIPELINE" and due - self.now <= lead)):
                continue
            if not pool:
                continue
            new = pool.pop(0)
            s.setdefault("rationale", []).append(
                f"autopilot {self.now.isoformat()}: {eid} was {st}; substituted by READY spare {new} so the slot is not empty")
            s.update(episode_id=new, status="READY", substituted_for=eid)
            swaps.append({"slot": f"{s['date']} {s['time']}", "from": eid, "from_status": st, "to": new})
            touched[str(wd)] = (wd, plan)
        for wd, plan in touched.values():
            old = plan["plan_sha256"]
            plan["plan_sha256"] = plan_sha(plan["slots"])
            plan.setdefault("revisions", []).append({"at": self.now.isoformat(), "by": "autopilot", "previous_sha256": old,
                                                     "reason": "slot substitution (self-correction)"})
            _w(wd / "weekly-content-plan.json", plan)
            self.reauthorize(wd, plan, auth_source, "plan revised by autopilot slot substitution")
        return swaps

    def reauthorize(self, wd, plan, auth, why):
        prev = _r(wd / "authorization.json")
        if prev and prev.get("plan_sha256") == plan["plan_sha256"]:
            return
        hist = _r(wd / "authorization-history.json", [])
        if prev:
            hist.append(prev)
            _w(wd / "authorization-history.json", hist)
        _w(wd / "authorization.json", {"week_start": plan["week_start"], "plan_sha256": plan["plan_sha256"],
                                       "authorized_by": "standing authorization (full autonomy)", "quote": auth["quote"],
                                       "given": auth["given"], "at": self.now.isoformat(), "why": why,
                                       "condition": "per slot: only an episode hosted with QA PASS is scheduled"})

    def ensure_authorized(self, auth):
        """A plan that exists without authorization (or with a stale hash) is authorised
        under the standing authorization, so scheduling never waits for a person."""
        out = []
        for wd, plan, a in self.weeks():
            if not a or a.get("plan_sha256") != plan["plan_sha256"]:
                self.reauthorize(wd, plan, auth, "standing authorization applied to current plan hash")
                out.append(wd.name)
        return out

    # ---------------------------------------------------------------- ready buffer
    def buffer_report(self, next_id):
        ready = [e for e in sorted(self.eps) if self.status(e) == "READY"
                 and not self.published_anywhere(e)]
        scheduled = [e for e in sorted(self.eps) if self.status(e) == "LIVE" and not self.published_anywhere(e)]
        pipeline = [e for e in sorted(self.eps) if self.status(e) == "IN_PIPELINE" and _num(e) >= 38]
        unauthored = [s["episode_id"] for _, _, s, _ in self.upcoming() if self.status(s["episode_id"]) == "UNAUTHORED"]
        have = len(ready) + len(pipeline)
        extra = max(0, self.s["ready_buffer_target"] - have)
        ids, n = list(unauthored), next_id
        while len(ids) < len(unauthored) + extra:
            eid = f"JR-{n:04d}"
            n += 1
            if eid not in ids and eid not in self.eps:
                ids.append(eid)
        return {"as_of": self.now.isoformat(), "target": self.s["ready_buffer_target"],
                "ready_unscheduled": ready, "scheduled_not_yet_published": scheduled,
                "authored_in_pipeline": pipeline, "upcoming_slots_unauthored": unauthored,
                "ready_buffer": len(ready) + len(scheduled),
                # growth-review 2026-10-18: "scheduled" above counts an episode as LIVE when ANY platform is
                # scheduled, so Instagram drafts parked at 2026-12-31 were reported as a healthy buffer (15)
                # while Instagram had only 3 real future posts. Report each platform's real queue too.
                "scheduled_by_platform": {pl: sum(1 for e in scheduled if self.platform_states(e).get(pl) == "SCHEDULED")
                                          for pl in ("instagram", "youtube")},
                "parked_drafts_by_platform": {pl: sorted(e for e in self.eps if not self.published_anywhere(e)
                                                         and self.platform_states(e).get(pl) == "DRAFT")
                                              for pl in ("instagram", "youtube")},
                "authoring_needed": ids,
                "authoring_rule": "author each id with generated/<id>.json + <id>.package.json, run "
                                  "`python3 scripts/daily/jr_daily.py brief <id>` for constraints, read content-os/STRATEGY.md "
                                  "and content-os/learnings.json, then push; the daily generator validates, renders and schedules"}


def _num(eid):
    try:
        return int(eid[3:7])
    except ValueError:
        return 0
