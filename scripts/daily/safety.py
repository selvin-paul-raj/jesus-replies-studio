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

HONESTY_LINE = "An imagined reply. The Scripture is quoted as written."
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
        if HONESTY_LINE not in v:
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
            need = [HONESTY_LINE] + ([CRISIS_LINE] if crisis else [])
            add = [x for x in need if x not in v]
            if add:
                v = v.rstrip() + "\n\n" + "\n".join(add)
                fixes.append(f"{field}: added {', '.join('honesty line' if a == HONESTY_LINE else 'crisis line' for a in add)}")
        pkg[field] = v
    return fixes


WRITER_RULES = [
    f"End every instagram_caption and youtube_description with the line: \"{HONESTY_LINE}\" (exact words; hashtags are added after it automatically).",
    "Never write 'answered in His words'; say 'answered from Scripture'.",
    "Jesus's lines never promise an outcome (a job, a healing, a person coming back, an exam result).",
    "Jesus's lines never give medical, mental-health, legal or financial advice and never tell anyone to stop treatment or avoid a doctor; point gently to trusted people and real help instead.",
    "Jesus's lines never invent doctrine: stay inside what the quoted Scripture and the plain Gospel say; no new teachings, no karma/reincarnation, no 'God no longer judges'.",
    "Jesus's words are an imagined reply, not a quotation; only the verse block is quoted Scripture.",
    "R5 (2026-10-29): never set an episode in another faith's festival, ritual or practice (Diwali, puja, lamps for a festival, rangoli, Holi, Navratri, Eid, temple visits, karma, astrology). The audience is Christian and reads it as Jesus approving other worship. Indian family life is welcome (Amma, Appa, aunties, trains home, office life); use neutral moments or the Christian calendar (Sunday church, Advent, Christmas, Good Friday, Easter, a church wedding).",
    f"Self-harm, suicide or abuse stories are held for Selvin's review before publishing and their caption and description must also carry: \"{CRISIS_LINE}\". Prefer other themes for the daily slots.",
]
