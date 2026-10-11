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
  83s, JR-0037 80s all underperformed). Target 50–65s; never exceed 90s.
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

## Auto-computed learnings

<!-- AUTO:START (rewritten by scripts/content_os/strategy.py) -->
_Last computed 2026-10-11T15:39Z from Buffer analytics, last 28 days, posts at least 48h old._

- **instagram**: n=22, median views 1445, best 2641, saves per 1k reach 13.2
- **youtube**: n=19, median views 229, best 1667, saves per 1k reach None

**Lean towards** (authoring reads this):
- not enough evidence yet

**Avoid / de-emphasise:**
- emotion=worried (IG median 280 vs 1445, n=4)
- duration=>78s (IG median 436 vs 1445, n=4)

**Hooks that travelled furthest (learn the shape, never copy the story):**
- JR-0007 2641 views: Jesus... I'm so tired. I keep trying and trying and nothing works.
- JR-0006 1949 views: Jesus... she left me for someone else. Just like that. Like none of it mattered.
- JR-0020 1893 views: Jesus... can I be honest? I'm tired of pretending I'm happy for everyone. 😭
- JR-0008 1724 views: Jesus... it feels like You've gone quiet. I pray and nothing comes back.
- JR-0029 1717 views: Jesus, why does everything come easy for her?

**Evidence notes:**
- instagram slot medians: morning (06-12 IST) 1436 (n=13), night (18-24 IST) 1506 (n=9)
- youtube slot medians: morning (06-12 IST) 208 (n=8), night (18-24 IST) 351 (n=11)
- average watch time is not exposed by the Buffer API for these posts; retention is judged by views/saves/shares only
- excluded 2026-09-20..2026-10-01: account-wide reach collapse: every JR post on both platforms (JR-0013..JR-0019) got under 120 views regardless of content; treated as a distribution anomaly, not a content signal (inferred 2026-10-11)
<!-- AUTO:END -->
