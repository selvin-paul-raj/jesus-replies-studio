# Jesus Replies — content strategy (living document)

Read by every authoring step. `python3 scripts/daily/jr_daily.py brief <id>` embeds the
auto block below (from `content-os/learnings.json`) into each brief, so new episodes are
written against the latest numbers. The auto block is rewritten every 6 hours by the content
OS cycle; the bi-weekly review (`cli.py review`, even ISO weeks, Sunday 19:30 IST) records
trends and experiment readings in `content-os/reviews/`.

## Standing guidance (from the account's own numbers, 2026-10-11)

- **Instagram is the reach engine.** Typical episode 1.2K–1.7K views; best JR-0007 (2,641,
  burnout, raw confession hook). YouTube Shorts sit far lower (mostly <350 views), so
  episodes are written for Instagram first; YouTube gets the same video.
- **What travels:** raw, specific pain told in the first person — burnout, heartbreak,
  comparison/jealousy, a parent's illness, shame, grief anniversaries. The first line names
  a concrete moment ("I parked outside...", "she left me for someone else"), not an abstract
  doctrine question.
- **What stalls:** abstract or Bible-trivia questions (why did Peter sink, why was Jesus
  sleeping in the storm), "happy" resolutions, and episodes over ~78s (JR-0022 87s, JR-0023
  83s, JR-0037 80s all underperformed). Target 50–62s; hard ceiling 75s (one setting:
  `config/publishing-rules.json` duration; the validator rejects longer scripts before rendering).
- **Saves/shares** are highest on comparison and heartbreak episodes (JR-0006, JR-0020):
  end with a line people want to keep or send to a friend.
- **Slots:** 08:00 and 20:30 IST (EXP-002). On Instagram the night slot has the steadier
  median; three early morning posts (JR-0022/0024/0037, ~200 views) underperformed, but
  later mornings (JR-0026/0028/0030) reached 1.2K–1.6K, so the slot alone does not explain
  it. On YouTube the morning slot currently does better. Slot times only change when the
  EXP-002 rule (n≥7 per arm) agrees on both platforms.
- **Engagement prompts:** close every episode with one short, personal question (comments
  are near zero across the account; this is the main open lever).
- **Variety rules (enforced by validators):** no repeated title/hook, no topic+character+
  emotion repeat, no scripture reused in the last 14 episodes; alternate emotion and
  character slot to slot.
- **Algorithm drift:** the review watches median views per platform; a fall of 30% or more
  between reviews is flagged and the next briefs lean harder on the strongest
  emotions/hooks.

## Instagram audit 2026-10-16 (instagram-skills framework; full report in the project PDF)

- **Followers are the bottleneck, not views.** ~38K Instagram views across 44 Reels, but the
  profile has 68 followers and Buffer reports 0 follows on every post. Every episode must give a
  stranger a reason to follow: a series promise ("a new question every morning and night") in the
  caption's last line, and the profile fixes Selvin approves.
- **Comments are ~0** (7 in 44 Reels) even with the question CTA added from JR-0036. Ask a
  *small, specific, answerable* question tied to the story ("Which line hit you?" / "What would
  you have said to him?"), not a reflective essay question. No engagement bait: never "comment
  amen / type a prayer / tag a friend / say X in the comments" (Instagram downranks it; package
  QA blocks it from JR-0064).
- **Sends are the weakest strong signal** (~4.6 per 1k reach vs saves ~13). End on one line
  someone would *send* to a specific person; caption can say "Send this to the friend who…" once.
- **Caption first 125 chars** = the question + the one concrete moment (keep). Put 1 searchable
  phrase people type in the first two lines ("Bible verse for jealousy", "when God feels silent").
- **Hashtags: exactly 5, added once** (bug fixed: 11 posts JR-0024..JR-0034 went out with the same
  5 tags twice). Mix: #JesusReplies (always) + 1-2 niche/topic (e.g. #UnansweredPrayer,
  #ChristianAnxiety, #FaithDoubts, #GriefAndFaith) + 1 mid (#ChristianReels 1.1M, #ChristianLiving
  2.8M, #BibleVerses 1.15M — rotate, don't repeat the same mid tag every post) + at most 1 huge
  (#Jesus / #Faith / #Prayer). Never #reels/#explore/#fyp.
- **Stall pattern:** 1 in 5 Reels stalls under 100 views (JR-0033, JR-0041, JR-0042 recently) with
  no caption difference; "waiting / unanswered prayer" stories stalled 3 of 3 times (JR-0009,
  JR-0016, JR-0033). Avoid that theme until a stronger angle exists; lean on named, concrete
  moments (sister, parents fighting, a secret told, a parent's illness).
- **Morning slot** is now the stronger one on both platforms (IG median 1,448 vs 1,332; YouTube
  528 vs 224). Keep 08:00 and 20:30 for now; next review tests 06:00 IST (≈8:30 pm US East)
  against 08:00 if the morning lead holds.

## Deep review 2026-10-16 (DEC-JR-007) — rules every episode follows

- **Scripture:** Berean Standard Bible (public domain), copied verbatim from `data/bible/bsb.json`
  (`python3 scripts/daily/jr_daily.py verse "Psalm 23:1"`). Label it **(BSB)**. NIV is no longer used.
- **Length:** 50–62 s target, 75 s hard ceiling (`config/publishing-rules.json` duration, the only
  place it is set). The validator estimates the length before rendering.
- **Honesty line** at the end of every Instagram caption and YouTube description:
  "An imagined reply. The Scripture is quoted as written." Say "answered from Scripture", never
  "answered in His words". Package QA fails without it (from JR-0064).
- **Jesus's lines** never promise an outcome, never give medical, mental-health, legal or
  financial advice, never tell anyone to skip a doctor or treatment, and never invent doctrine.
- **Crisis gate:** self-harm, suicide or abuse themes (and any Jesus line the lint flags) are held
  for Selvin's review and never auto-published; a READY spare fills the slot. If released, the
  caption and description must also carry "If you are in danger, please reach a local crisis line."
- **Music:** original tracks only (`public/audio/LICENSES.md`), rotated by episode id.

## Master plan 2026-10-16 (DEC-JR-008) — captions and weekly mix

**Every Instagram caption, in this order** (YouTube description uses lines 1, 2, 5, 6 plus the
Instagram link):
1. First line: the hurt plus one searchable phrase people type ("Bible verse for jealousy",
   "prayer for anxiety", "when God feels silent").
2. The story in a line or two, Jesus's reply, the verse with **(BSB)**.
3. One small, easy question: "Which line hit you?" / "What would you have said to her?" Never a
   big reflective one ("Who in your family is carrying something?").
4. One send line: "Send this to the sister who needs it." (name a specific person.)
5. *An imagined reply. The Scripture is quoted as written.*
6. *New question every morning and night.*
7. Exactly 5 hashtags: #JesusReplies + 1-2 topic + 1 mid-size + 1 big. Never "type amen" or
   "tag a friend".

**Weekly mix — 14 episodes** (writer plans each week to this; `config/content-os.json` weekly_mix):

| Topic | Per week |
|---|---|
| Heartbreak and relationships | 5 |
| Burnout and tiredness | 3 |
| Jealousy and comparison | 3 |
| Family and illness | 2 |
| Faith doubt | 1 |
| Bible trivia | 0 |

From the week of 2026-10-19, 2 of the 14 are **Real-question Friday** episodes built from real
questions sent through the profile form (credit the question, never the person's name). Winners
(top 10% by IG+YT score) get a "Part 2" follow-up within two weeks, counted inside the mix.

## Research checks 2026-10-16 (content-os/research/research-faith-studio-checks-2026-10-16.md)
- Crisis line (safety.CRISIS_LINE) now names US 988, Samaritans 116 123, Tele-MANAS 14416. Philippines NCMH 1553 and Nigeria Lagos Lifeline 070 0000 6463 are verified backups for audience-specific posts.
- Trial Reels: Buffer composer supports them (not the API), and Instagram needs 200+ followers on a professional account. At 68 followers we are not eligible: post normal Reels; revisit at 200.
- YouTube "Generic or repetitive content": each episode needs a distinct question and story, and outcomes must vary (no same-situation, same-outcome template). Variation rules are the top monetisation risk.

## Auto-computed learnings

<!-- AUTO:START (rewritten by scripts/content_os/strategy.py) -->
_Last computed 2026-10-17T10:36Z from Buffer analytics, last 28 days, posts at least 48h old._

- **instagram**: n=23, median views 1451, best 1907, saves per 1k reach 14.6, stalled 3 (excluded)
- **youtube**: n=24, median views 351, best 1925, saves per 1k reach None, stalled 0 (excluded)
- **episodes scored** (IG + YT percentile): 26, 21 with both platforms

**Lean towards** (authoring reads this):
- not enough evidence yet

**Avoid / de-emphasise:**
- nothing with enough evidence

**Hooks that travelled furthest (learn the shape, never copy the story):**
- JR-0041 score 1.00 (youtube 1925 views): Jesus... I said yes again. I didn't want to. I never do. 😔
- JR-0042 score 0.91 (youtube 1483 views): Jesus... my grandmother didn't know who I was today. She called me by my uncle's name. 😔
- JR-0040 score 0.84 (instagram 1656, youtube 1196 views): Jesus... why do my parents only fight when they think I'm asleep? 😔
- JR-0032 score 0.80 (instagram 1592, youtube 1477 views): Jesus, is it wrong that I feel this proud?
- JR-0034 score 0.77 (instagram 1510, youtube 1675 views): Jesus, what if I stopped believing tomorrow?

**Evidence notes:**
- instagram slot medians: morning (06-12 IST) 1457 (n=12), night (18-24 IST) 1333 (n=11)
- youtube slot medians: morning (06-12 IST) 529 (n=11), night (18-24 IST) 298 (n=13)
- instagram: 3 of 26 Reels stalled (reach under 68 followers) and were left out of content learning: JR-0042, JR-0041, JR-0033
- rules need n>=8 episodes per bucket; smaller buckets are reported only
- average watch time is not exposed by the Buffer API for these posts; retention is judged by views/saves/shares only
- excluded 2026-09-20..2026-10-01: account-wide reach collapse: every JR post on both platforms (JR-0013..JR-0019) got under 120 views regardless of content; treated as a distribution anomaly, not a content signal (inferred 2026-10-11)
<!-- AUTO:END -->
