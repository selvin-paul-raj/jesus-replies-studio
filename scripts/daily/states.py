"""Explicit episode state machine. A state can only move along ALLOWED edges."""
ORDER = ["GENERATED", "VALIDATED", "RENDERED", "RENDER_QA_PASSED", "PACKAGED",
         "PACKAGE_QA_PASSED", "ASSET_HOSTED", "BUFFER_DRAFT", "WAITING_FOR_USER",
         "APPROVED", "SCHEDULED", "PUBLISHED", "PUBLISHED_VERIFIED"]
FAILURES = {"GENERATION_FAILED", "VALIDATION_FAILED", "RENDER_FAILED", "RENDER_QA_FAILED",
            "PACKAGE_FAILED", "PACKAGE_QA_FAILED", "HOSTING_FAILED", "BUFFER_FAILED",
            "SCHEDULING_FAILED", "PUBLISH_VERIFICATION_FAILED", "BLOCKED"}
NEW = "NEW"
ALL = set(ORDER) | FAILURES | {NEW}

# Each success state may only follow the one before it; each step has its own failure.
STEP_FAILURE = {"GENERATED": "GENERATION_FAILED", "VALIDATED": "VALIDATION_FAILED",
                "RENDERED": "RENDER_FAILED", "RENDER_QA_PASSED": "RENDER_QA_FAILED",
                "PACKAGED": "PACKAGE_FAILED", "PACKAGE_QA_PASSED": "PACKAGE_QA_FAILED",
                "ASSET_HOSTED": "HOSTING_FAILED", "BUFFER_DRAFT": "BUFFER_FAILED",
                "SCHEDULED": "SCHEDULING_FAILED", "PUBLISHED": "PUBLISH_VERIFICATION_FAILED",
                "PUBLISHED_VERIFIED": "PUBLISH_VERIFICATION_FAILED"}

ALLOWED = {NEW: {"GENERATED", "GENERATION_FAILED", "BLOCKED"}}
for i, s in enumerate(ORDER):
    nxt = ORDER[i + 1] if i + 1 < len(ORDER) else None
    ALLOWED[s] = set()
    if nxt:
        ALLOWED[s].add(nxt)
        if nxt in STEP_FAILURE:
            ALLOWED[s].add(STEP_FAILURE[nxt])
    ALLOWED[s].add("BLOCKED")
ALLOWED["WAITING_FOR_USER"].discard("SCHEDULING_FAILED")
ALLOWED["APPROVED"] |= {"WAITING_FOR_USER"}      # approval withdrawn
ALLOWED["SCHEDULED"] |= {"PUBLISH_VERIFICATION_FAILED"}
# A failed/blocked episode is only re-entered at the step that failed, after a fix.
RETRY_FROM = {"GENERATION_FAILED": NEW, "VALIDATION_FAILED": "GENERATED",
              "RENDER_FAILED": "VALIDATED", "RENDER_QA_FAILED": "VALIDATED",
              "PACKAGE_FAILED": "RENDER_QA_PASSED", "PACKAGE_QA_FAILED": "RENDER_QA_PASSED",
              "HOSTING_FAILED": "PACKAGE_QA_PASSED", "BUFFER_FAILED": "ASSET_HOSTED",
              "SCHEDULING_FAILED": "APPROVED"}


class TransitionError(Exception):
    pass


def check(frm: str, to: str) -> None:
    if frm not in ALL or to not in ALL:
        raise TransitionError(f"unknown state {frm!r} -> {to!r}")
    if to not in ALLOWED.get(frm, set()):
        raise TransitionError(f"illegal transition {frm} -> {to}")


def rank(state: str) -> int:
    return ORDER.index(state) if state in ORDER else -1


def at_least(state: str, target: str) -> bool:
    return state in ORDER and rank(state) >= rank(target)
