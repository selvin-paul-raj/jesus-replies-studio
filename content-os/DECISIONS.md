# Jesus Replies — decisions and authorizations

Authority comes only from Selvin's own chat messages. Newest last.

| id | date | decision | source |
|----|------|----------|--------|
| DEC-JR-001 | 2026-10-03 | Test slots 08:00 and 20:30 IST, same slot on Instagram and YouTube | Selvin in chat |
| DEC-JR-002 | 2026-10-03 18:48 IST | Standing authorization for the weekly loop: "Keep the weekly batch -> scheduling -> publication -> analytics -> next-week learning loop autonomous." | config/content-os.json autonomy.standing_authorization |
| DEC-JR-003 | 2026-10-05 | QA-passed episodes go straight to the queue (Selvin: "continue") | config/content-os.json autonomy.auto_queue_on_qa_pass |
| DEC-JR-004 | 2026-10-05 | NEEDS_GENERATION slots keep their reserved id and schedule once it passes QA (referred to as DEC-018 in older files) | weekly authorization.json |
| DEC-JR-005 | 2026-10-11 20:48 IST | **Full autonomy, human gate removed.** Quote: "dont stop it continus complete automous running system i wnat it bi-weelky review it and enhance the content and enagament , qually and follow ups and crack chnaging algorthim of thsoe social medias build life long running system self correction , feeadbackloop system" | config/content-os.json autonomy.full_autonomy; config/publishing-rules.json require_human_approval=false |
| DEC-JR-007 | 2026-10-16 15:00 IST | **Deep-review fixes:** original music, BSB instead of NIV, 50-62 s / 75 s ceiling, honesty line, crisis gate (held for human review), learning loop on IG+YT with stalls excluded and n>=8, verse card as Story, one slot table. Quote: "COMPLETE DEEP UNDERSTANDING AND REVIEW AND SOLUTION" + "you do anything use anything for it" | CEO fix plan 2026-10-16; branch ceo/deep-review-fixes |

## DEC-JR-005 in practice

- An episode that passes every automated gate (NIV verse verbatim check, originality, render
  QA, package QA, hosted-asset check, Buffer draft read-back) is APPROVED under the standing
  authorization and scheduled into its reserved slot on Instagram and YouTube by the content
  OS distributor. No gate was removed except the human one.
- `jr-daily-generate.yml` runs daily at 05:00 IST and prepares reserved episodes for slots up
  to 3 days ahead, then authored spares.
- Self-correction: failed episodes get bounded automatic repairs (max 3): verse wording
  re-synced to the NIV source, broken renders re-rendered, package fixes (hashtag count,
  title length, missing reference), transient hosting/Buffer retries. Unrepairable ones are
  marked exhausted and their slot is filled from READY spares; the plan is re-hashed and
  re-authorised under this decision (previous authorizations kept in
  `authorization-history.json`).
- Feedback loop: Buffer analytics -> `content-os/learnings.json` -> STRATEGY.md auto block ->
  every new brief. Bi-weekly review on even ISO weeks.
- Limits: never spends money, never changes the Buffer plan, never deletes a published post,
  held episodes (JR-0035, JR-0036) stay held.

## DEC-JR-006 — 2026-10-16 Instagram audit changes (under DEC-JR-005 bi-weekly-review autonomy)

Requested by Selvin (main chat, 2026-10-16 14:05 IST: "use [instagram-skills] and complete deep research and analysis of my jesusrepliesofficial completely").
Applied now (hooks/captions/strategy only; no profile, money or new post types):
1. Fixed duplicate hashtag block (caption_text no longer appends tags when the caption already ends with them).
2. Package QA from JR-0064: no hashtags inside the caption body; no engagement-bait phrases.
3. STRATEGY.md: follow-conversion line, small specific comment questions, one send line, searchable phrase in first 2 lines, rotating sized 5-tag sets, avoid "waiting/unanswered prayer" angle for now.
Proposed, waiting on Selvin: display name + bio rewrite, link swap, category label, pins/highlights (need the @jesusrepliesofficial login), and stopping/reshaping the daily Bible photo posts on Instagram (avg 29 views, cluttering the grid).

## DEC-JR-007 — 2026-10-16 deep-review fixes (CEO, under Selvin's 15:00 IST go-ahead)

1. **Music:** the third-party track is removed from rendering and from the repo; 5 original tracks
   (`public/audio/bgm-01..05.mp3`, made by `scripts/audio/make_bgm.py`, ~-20 LUFS, loopable) rotate
   by a hash of the episode id. Licence notes: `public/audio/LICENSES.md`.
2. **Length:** `config/publishing-rules.json` duration is the only setting: target 50-62 s, ceiling
   75 s. The validator estimates length before rendering and rejects anything over the ceiling.
3. **Scripture:** Berean Standard Bible (public domain) bundled at `data/bible/bsb.json`; verbatim
   check is local; Bible Gateway scraping removed; labels say (BSB); daily cards move to release
   `bible-posts-v2` (must be built once with the "Build Bible Posts" workflow).
4. **Honesty line** on every caption and YouTube description from JR-0064: "An imagined reply. The
   Scripture is quoted as written." "answered in His words" -> "answered from Scripture".
5. **Crisis gate:** self-harm / suicide / abuse themes, or a Jesus line that promises outcomes, gives
   medical/financial advice or adds doctrine, are HELD_FOR_REVIEW: never hosted, never sent to Buffer,
   never auto-approved; a READY spare fills the slot. Release only with
   `jr_daily.py release-review EID --by NAME --evidence "words"`; released ones must carry "If you are
   in danger, please reach a local crisis line."
6. **Learning loop:** IG Reels with reach below followers (`config/content-os.json`
   analytics.instagram_followers) are stalls, excluded from content learning; each episode is scored on
   the mean IG/YT view percentile; a rule needs n>=8. Old avoid rules (confession hook, worried, Isaiah)
   are gone.
7. **Daily verse** posts as an Instagram Story (`daily_verse.instagram_post_type`), 06:37 IST.
8. **Slots:** one table, `publishing-rules.json` slots 08:00 / 20:30 IST; crons moved off :00.
9. Every workflow that writes to main has a concurrency group.

Queued episodes JR-0047..JR-0063 were already rendered and in Buffer before this change; they keep
their NIV text, old captions and old music until replaced (not touched automatically).


## DEC-JR-008 — Master plan adopted (2026-10-16)
Selvin's Jesus Replies Master Plan (via CEO, 15:56 IST) replaces the CEO fix plan where they differ. Slice (a) done: caption order (hurt + search phrase, story/reply/verse BSB, small question, send line, honesty line, series line, 5 tags) and the 14-a-week topic mix (heartbreak 5, burnout 3, jealousy 3, family/illness 2, faith doubt 1, trivia 0; 2 Real-question Fridays inside it) written into STRATEGY.md and config weekly_mix. Queued JR-0047..JR-0063 untouched pending Selvin.

## DEC-JR-009 — Old queued versions swapped for fixed ones (2026-10-16)
Selvin said yes (15:54 IST, via CEO) to replacing queued old-version episodes and clearing parked drafts. JR-0047..JR-0063 source files converted to BSB with (BSB) labels, the honesty line, "answered from Scripture", and no comment bait (scripts/migrate_v2_queue.py). Workflow jr-swap-fixed.yml re-renders them with the original music, uploads to new release tags (old assets kept), then edits the SAME Buffer posts in the SAME slots; drafts stay drafts. The 11 parked IG drafts (JR-0052..58, JR-0060..63) are the next fortnight's episodes, so they are swapped to fixed versions rather than deleted; JR-0036 (held) and JR-0038 drafts untouched pending CEO. Published posts never touched. Ledger: content-os/requeue-2026-10-16.json.

## DEC-JR-010 — Evidence playbook on top of the master plan (CEO, 2026-10-16 16:45 IST)
Selvin's STRATEGY.md playbook wins where it differs from the master plan. Length now 45-55 s target, 60 s hard ceiling (config/publishing-rules.json). JR-0047..JR-0051 rewritten to the 7-beat story template (hook, detail, validate, turn, BSB verse, payoff, one CTA) at 44-49 s estimated, with new captions (search phrase, small question, send/save line, honesty line, series line) before swapping; the 67-74 s re-renders are never swapped in. Slots move to 07:30 / 17:30 IST after the current queue clears; hooks, variation, CTA rotation, Stories, series and the 30-day test follow as later slices.


## DEC-JR-011 — Bi-weekly growth review (2026-10-18, autonomous under DEC-JR-005)
- 2026-10-18 Hook rule R1 "hidden feeling" adopted (JR-0045, JR-0020, JR-0040, JR-0046); EXP-004 started, read 2026-11-01. EXP-001 folded in.
- 2026-10-18 R2: de-emphasise "worried about the future" episodes (JR-0024 247, JR-0037 198 IG views; flagged 2026-10-11 too).
- 2026-10-18 R3/R4: send line names one person, no "type a prayer"; YouTube comments (32 vs IG 4) answered from Studio by the review.
- 2026-10-18 EXP-002 concluded: platforms disagree (IG night +18%, YT morning 3.5x), both slots kept.
- 2026-10-18 JR-0052..JR-0059 rewritten to 47-54 s estimated (7-beat template, R1 hooks, new captions, rotated mid hashtags) so the stuck fixed-version swap (tag jr-fix-2026-10-16-d) can run; Instagram had no scheduled post Oct 19 20:30 - Oct 22 20:30 (7 slots parked as drafts).
- 2026-10-18 Root-cause fixes: release_episodes.py failed every batched swap ("AMBIGUOUS existing release", run 39048554952) because it demanded the exact asset set; it now accepts a subset/superset batch and keeps other episodes' manifest rows. ready-buffer.json now reports scheduled_by_platform and parked_drafts_by_platform (it said 15 while Instagram had 3 real future posts).
- 2026-10-18 New content-os/review-rules.json, embedded in every brief as review_rules (pipeline.brief).
- 2026-10-18 Root-cause fix for the recurring Buffer 24h RATE_LIMIT_EXCEEDED (again at 10:22 IST today): Distributor.reconcile now reads open posts from the one per-platform list call it already makes, and only falls back to a single-post read when the post is missing from the list, the list failed, or the run has already changed Buffer. Test T04cListCache added; 108 tests pass.
- 2026-10-18 analytics.instagram_followers 68 -> 88 (public profile count read during the review; +20 in 2 days).

## DEC-JR-012 — Faith-framing rule R5 and Diwali pull (2026-10-29, Selvin in chat)
Selvin (2026-10-29 11:53 IST), after a YouTube comment objecting to Diwali episodes: fix it, rework the content strategy, and review all schedules before planning ahead.
- JR-0076 (due 2026-10-29 20:30) and JR-0078 (due 2026-10-30 20:30) held to Buffer draft on Instagram and YouTube; JR-0079 and JR-0081 scheduled into those slots on both platforms. JR-0064, JR-0076, JR-0078, JR-0080 added to held_episodes (never scheduled).
- Rule R5 (STRATEGY.md, review-rules.json, writer rules): no other-faith festivals, rituals or practices; enforced by safety.faith_framing (any hit holds for review).
- Published Diwali episodes JR-0071..JR-0075 are left up (published posts are never deleted automatically); removing them needs Selvin's explicit go.
- Weekly plans from 2026-11-02 use the Christian calendar (Global Bible Month, Thanksgiving, Advent) for at most 2 seasonal episodes a week and rotate emotions away from all-"sad".


## DEC-JR-013 — Skill library, self-calibrating review, R6 length cap, comment replies (2026-10-29)
- Why: Selvin asked for a full strategist loop using the Instagram/YouTube agent skills and the
  creator-skill list, with genuine comment replies, all saved to GitHub for reuse.
- What: vendored skill packs (MIT/Apache, licenses kept) in `skills/`; JR playbooks; `skill_review.py`
  (advisory) with `--calibrate`; R6 (95–120 spoken words) from calibration evidence; first 4 YouTube
  comment replies posted and logged.
- Not done: hook score is not a gate (it does not predict our views). Instagram comments pending
  (Meta reCAPTCHA blocked the cloud browser on 2026-10-29).
