"""Content safety for Jesus Replies (DEC-JR-007, 2026-10-16).

1. Honesty line: every Instagram caption and YouTube description says the reply is imagined
   and the Scripture is quoted as written.
2. Crisis gate: an episode that touches self-harm, suicide or abuse is never auto-published.
   It is held for a human (Selvin) to read, a READY spare fills its slot, and its caption and
   description must carry the crisis line.
3. Jesus-line lint: Jesus's lines never promise outcomes, give medical or financial advice, or
   invent doctrine. Anything that looks like it is held for review, not silently published.

The classifier is deliberately simple and errs towards holding: a held episode costs one
slot swap; a missed one can hurt a vulnerable viewer."""
import re

# 2026-10-29 (DEC-JR-014): visuals are AI-generated and now say so openly (user decision after viewers asked).
HONESTY_LINE = "An imagined reply with AI-made visuals. The Scripture is quoted as written."
# Packages written before the AI line keep their old line: their Buffer drafts already carry that text,
# and check_draft compares text exactly, so they are accepted as-is rather than rewritten.
LEGACY_HONESTY_LINES = ("An imagined reply. The Scripture is quoted as written.",)


def has_honesty_line(text):
    return any(x in (text or "") for x in (HONESTY_LINE,) + LEGACY_HONESTY_LINES)
# Numbers verified on official pages 2026-10-16 (Research; DEC-JR-010): 988lifeline.org, samaritans.org, telemanas.mohfw.gov.in
CRISIS_LINE = ("If you are in danger, please reach a local crisis line: US 988 (call or text), "
               "UK & Ireland Samaritans 116 123, India Tele-MANAS 14416.")
BANNED_PHRASES = ("answered in His words",)
REPLACEMENTS = {"answered in His words": "answered from Scripture"}

# Category -> (strong terms: one hit flags; weak terms: two different hits flag).
CRISIS_TERMS = {
    "suicide": (
        [r"suicid\w*", r"kill(?:ing)? (?:my|him|her|them)sel(?:f|ves)", r"end(?:ing)? (?:my|it) (?:life|all)",
         r"take my (?:own )?life", r"don'?t want to (?:be alive|live|wake up)", r"better off (?:dead|without me)",
         r"want(?:ed)? to die", r"no reason to live", r"jump(?:ing)? off", r"overdos\w*", r"goodbye (?:note|letter)"],
        [r"\bdie\b", r"\bdisappear forever\b", r"\bgive up on (?:life|everything)\b", r"\bnot be here\b",
         r"\bend it\b", r"\bpills\b", r"\bbridge\b"]),
    "self_harm": (
        [r"self[- ]?harm\w*", r"cut(?:ting)? (?:my|her|him)sel(?:f|ves)", r"hurt(?:ing)? myself", r"burn(?:ing|ed)? myself",
         r"razor", r"scars? on my (?:arm|wrist|leg)s?", r"(?:my|her|his) wrists?"],
        [r"\bscars?\b", r"\bblade\b", r"\bbleed\w*\b", r"\bsleeves\b"]),
    "abuse": (
        [r"abus\w*", r"molest\w*", r"rap(?:e|ed|ist)\b", r"sexual(?:ly)? assault\w*", r"touched me", r"groom(?:ed|ing)\b",
         r"(?:hits?|hit|beats?|beat|slaps?|slapped|chokes?|choked) (?:me|my mom|my mother|her|him|us)\b",
         r"domestic violence", r"trafficked", r"incest"],
        [r"\bbruises?\b", r"\bafraid to go home\b", r"\blocked (?:me )?in\b", r"\bthreaten\w*\b", r"\bunsafe\b",
         r"\bhurts? me\b", r"\bscared of (?:him|her|my dad|my father|my husband|my stepdad)\b"]),
}

JESUS_LINT = {
    "promised_outcome": [
        r"\byou will (?:get|pass|be healed|recover|find (?:a|the) (?:job|husband|wife)|be rich|win|get married|get the job)\b",
        r"\bi (?:will|promise to) (?:heal|cure|fix|give you|make (?:him|her|them) (?:come back|love you))\b",
        r"\bi promise (?:you )?(?:it|he|she|they|this) will\b", r"\bguarantee\w*\b",
        r"\b(?:he|she|they) will come back\b", r"\bthe test results will\b"],
    "medical_advice": [
        r"\b(?:stop|quit|skip) (?:taking )?(?:your|the) (?:medicine|medication|meds|pills|treatment|therapy)\b",
        r"\byou don'?t need (?:a )?(?:doctor|therapist|counsell?or|medication|meds|treatment)\b",
        r"\binstead of (?:a )?(?:doctor|therapy|therapist|medication|treatment)\b", r"\bdosage\b", r"\bmg\b",
        r"\bprayer (?:will )?(?:cure|replaces?)\b"],
    "financial_advice": [
        r"\binvest (?:in|your)\b", r"\b(?:buy|sell) (?:stocks?|shares|crypto|bitcoin|gold)\b", r"\btake (?:a|the) loan\b",
        r"\bborrow (?:money|from)\b", r"\bquit your job\b", r"\blottery\b", r"\bgive (?:all )?your money\b"],
    "invented_doctrine": [
        r"\b(?:i|god) (?:never|no longer) (?:judges?|forgives?)\b", r"\ball religions\b", r"\breincarnat\w*\b",
        r"\bkarma\b", r"\bnew commandment\b", r"\bthe bible is wrong\b", r"\bscripture (?:doesn'?t|does not) matter\b",
        r"\bi am (?:not|no longer) (?:the son|god)\b", r"\bsalvation (?:through|by) (?:works|money|giving)\b"],
}


# R5 (2026-10-29, Selvin): no other-faith festivals, rituals or practices. Viewers read a Jesus reply set
# around Diwali/puja/lamps as Jesus endorsing another religion's worship (Exodus 20:3 comment on YouTube,
# JR-0071..JR-0078). Any hit holds the episode for review; a READY spare fills the slot.
FAITH_FRAMING = [
    r"\bdiwali\b", r"\bdeepavali\b", r"\bdhanteras\b", r"\bbhai dooj\b", r"\bpu?ja\b", r"\bpooja\b",
    r"\brangoli\b", r"\bdiyas?\b", r"\bnavratri\b", r"\bdurga\b", r"\bganesh\w*", r"\bganpati\b",
    r"\bdussehra\b", r"\bholi\b", r"\bkarva chauth\b", r"\braksha bandhan\b", r"\brakhi\b", r"\bonam\b",
    r"\bpongal\b", r"\bsankranti\b", r"\bchhath\b", r"\blakshmi\b", r"\beid\b", r"\bramadan\b", r"\biftar\b",
    r"\btemple\b", r"\bmandir\b", r"\baarti\b", r"\bprasad\w*", r"\bkarma\b", r"\bastrolog\w*",
    r"\bhoroscope\w*", r"\bkundli\b", r"\bmuhurat\w*", r"\bfestival lamps?\b", r"\blit the lamps\b"]


def faith_framing(ep, pkg=None):
    """-> {"faith_framing": [matched patterns]} over the whole episode and package, or {}."""
    text = episode_text(ep, pkg)
    if pkg:
        text += "\n" + " ".join(pkg.get("instagram_hashtags") or [])
    h = _hits(text, FAITH_FRAMING)
    return {"faith_framing": h} if h else {}


def _hits(text, patterns):
    t = text.lower()
    return sorted({p for p in patterns if re.search(p, t)})


def episode_text(ep, pkg=None):
    parts = [ep.get("title", ""), ep.get("topic", ""), (ep.get("bible") or {}).get("text", "")]
    parts += [l.get("text", "") for l in ep.get("lines") or []]
    if pkg:
        parts += [pkg.get("instagram_caption", ""), pkg.get("youtube_description", ""), pkg.get("youtube_title", "")]
    return "\n".join(p for p in parts if p)


def crisis_check(ep, pkg=None):
    """-> (flagged, {category: [matched patterns]}). Strong term: flag. Two different weak terms: flag."""
    text = episode_text(ep, pkg)
    # the required crisis line itself must never trigger the gate
    text = text.replace(CRISIS_LINE, " ")
    found = {}
    for cat, (strong, weak) in CRISIS_TERMS.items():
        s, w = _hits(text, strong), _hits(text, weak)
        if s or len(w) >= 2:
            found[cat] = s + w
    return bool(found), found


def jesus_lint(ep):
    """-> {problem: [matched patterns]} over Jesus's lines only."""
    jesus = "\n".join(l.get("text", "") for l in ep.get("lines") or [] if l.get("speaker") == "jesus")
    out = {}
    for cat, pats in JESUS_LINT.items():
        h = _hits(jesus, pats)
        if h:
            out[cat] = h
    return out


def package_problems(pkg, crisis=False):
    """Honesty / crisis / banned-phrase problems in a package (empty list = pass)."""
    probs = []
    for field in ("instagram_caption", "youtube_description"):
        v = pkg.get(field) or ""
        if not has_honesty_line(v):
            probs.append(f"honesty line missing from {field}")
        if crisis and CRISIS_LINE not in v:
            probs.append(f"crisis line missing from {field} (sensitive episode)")
    blob = " ".join(str(pkg.get(k) or "") for k in ("instagram_caption", "youtube_description", "youtube_title"))
    for b in BANNED_PHRASES:
        if b.lower() in blob.lower():
            probs.append(f"banned phrase '{b}' (use '{REPLACEMENTS[b]}')")
    return probs


def fix_package(pkg, crisis=False):
    """Bounded self-heal: swap banned phrases, append the required lines once. Returns fixes made."""
    fixes = []
    for field in ("instagram_caption", "youtube_description", "youtube_title"):
        v = pkg.get(field)
        if not isinstance(v, str):
            continue
        for b, r in REPLACEMENTS.items():
            if re.search(re.escape(b), v, re.I):
                v = re.sub(re.escape(b), r, v, flags=re.I)
                fixes.append(f"{field}: '{b}' -> '{r}'")
        if field != "youtube_title":
            need = ([] if has_honesty_line(v) else [HONESTY_LINE]) + ([CRISIS_LINE] if crisis else [])
            add = [x for x in need if x not in v]
            if add:
                v = v.rstrip() + "\n\n" + "\n".join(add)
                fixes.append(f"{field}: added {', '.join('honesty line' if a == HONESTY_LINE else 'crisis line' for a in add)}")
        pkg[field] = v
    return fixes


# ---------------------------------------------------------------- 2026-11-05 upgrades (DEC-JR-017)
# R11: no question hooks. One script feeds both platforms, so the opener is a confession or a
# statement everywhere. YouTube Shorts by hook type (median views): question 382 (n=41),
# statement 1,270 (n=11), confession 1,440 (n=24). Instagram is neutral (question 1,526,
# statement 1,559, confession 1,319), so nothing is lost there.
HOOK_TYPES_ALLOWED = ("confession", "statement")
_QWORDS = r"(?:why|how|what|when|where|who|whom|whose|which|is|am|are|was|were|do|does|did|can|could|should|would|will|shall|have|has|may|might|must)"


def hook_kind(text):
    """-> 'question' | 'confession' | 'statement' for an opening line ("Jesus... <hook>")."""
    t = re.sub(r"^\s*jesus\s*[.\u2026,!:-]*\s*", "", (text or "").strip(), flags=re.I)
    t = re.sub(r"[\U0001F000-\U0001FFFF\u2600-\u27BF\uFE0F\u200d]", "", t).strip()
    if "?" in t or re.match(rf"^{_QWORDS}(?:n'?t)?\b", t, re.I):
        return "question"
    if re.match(r"^(?:i|i'm|i've|i'd|i'll|im|my|me|we|we're|our|today i|tonight i|last night i)\b", t, re.I):
        return "confession"
    return "statement"


# R12: every Reel/Short ends on a share line in the channel voice, worded differently each time.
SHARE_LINE_EXAMPLES = (
    "Send this to someone who needs it today.",
    "Send this to the friend who always says she's fine.",
    "Share this with the brother who carries it alone.",
    "Pass this to the daughter still sitting at that table.",
)
_SHARE_RE = re.compile(r"^\W*(?:send|share|pass|forward)\s+(?:this|it)\s+(?:to|with)\b", re.I)
_BAIT_WORDS = re.compile(r"\b(?:amen|comment|comments|type|tag|like this|double tap|follow for)\b", re.I)


def is_share_line(text):
    """A share line names who to send it to and carries no engagement bait."""
    t = (text or "").strip()
    return bool(_SHARE_RE.search(t)) and not _BAIT_WORDS.search(t) and 4 <= len(t.split()) <= 18


def share_line_of(text_block):
    """First share line found in a caption/description, or None."""
    for ln in (text_block or "").splitlines():
        if is_share_line(ln):
            return ln.strip()
    return None


# R13: each new post carries a first comment: one easy, warm question tied to the episode.
def first_comment_problems(fc):
    probs = []
    fc = (fc or "").strip()
    if not fc:
        return ["first_comment missing (one easy, warm question tied to the episode)"]
    if not fc.endswith(("?", "?\U0001F447", "? \U0001F447")) and "?" not in fc[-3:]:
        probs.append("first_comment must be one question ending in '?'")
    if fc.count("?") > 1:
        probs.append("first_comment asks more than one question")
    if len(fc) > 150:
        probs.append(f"first_comment {len(fc)} chars (max 150)")
    if re.search(r"https?://|#\w|@\w", fc):
        probs.append("first_comment has a link, hashtag or mention")
    if _BAIT_WORDS.search(fc):
        probs.append("first_comment is engagement bait (no 'amen / comment / type / tag')")
    return probs


WRITER_RULES = [
    f"End every instagram_caption and youtube_description with the line: \"{HONESTY_LINE}\" (exact words; hashtags are added after it automatically).",
    "Never write 'answered in His words'; say 'answered from Scripture'.",
    "Jesus's lines never promise an outcome (a job, a healing, a person coming back, an exam result).",
    "Jesus's lines never give medical, mental-health, legal or financial advice and never tell anyone to stop treatment or avoid a doctor; point gently to trusted people and real help instead.",
    "Jesus's lines never invent doctrine: stay inside what the quoted Scripture and the plain Gospel say; no new teachings, no karma/reincarnation, no 'God no longer judges'.",
    "Jesus's words are an imagined reply, not a quotation; only the verse block is quoted Scripture.",
    "R5 (2026-10-29): never set an episode in another faith's festival, ritual or practice (Diwali, puja, lamps for a festival, rangoli, Holi, Navratri, Eid, temple visits, karma, astrology). The audience is Christian and reads it as Jesus approving other worship. Indian family life is welcome (Amma, Appa, aunties, trains home, office life); use neutral moments or the Christian calendar (Sunday church, Advent, Christmas, Good Friday, Easter, a church wedding).",
    "R11 (2026-11-05): the first line is a confession (\"Jesus... I said yes again.\") or a statement (\"Jesus... my brother's EMI is on my card now.\"), never a question. On YouTube question hooks get about a third of the views (median 382 vs 1,270 statement, 1,440 confession); one script feeds both platforms. The validator fails a question opener.",
    "R12 (2026-11-05): the last line of the script is a share line (speaker 'engagement') in the channel voice, worded freshly each time and naming who needs it (\"Send this to someone who needs it today.\", \"Pass this to the daughter still sitting at that table.\"). The caption carries a share line too. Never 'type amen', 'comment', 'tag', or any engagement bait.",
    "R13 (2026-11-05): the package has first_comment: one easy, warm question tied to the episode, under 150 characters, no links/hashtags/bait (\"Has someone in your family ever said this to you?\"). Instagram posts it through Buffer; on YouTube the comment run posts and pins it.",
    f"Self-harm, suicide or abuse stories are held for Selvin's review before publishing and their caption and description must also carry: \"{CRISIS_LINE}\". Prefer other themes for the daily slots.",
]
