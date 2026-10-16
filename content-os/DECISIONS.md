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

