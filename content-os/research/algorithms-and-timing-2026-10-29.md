# Algorithms & timing review — 2026-10-29

## What the platforms say (sources, fetched 2026-10-29)
**Instagram Reels** (Adam Mosseri, quoted in zoomsphere.com/blog/instagram-algorithm-2026-what-actually-gets-reach, 2026-10-28):
- Top signals: watch time, likes, sends. Likes weigh slightly more with followers, **sends weigh more for non-followers**.
- 2026-10-23: Instagram focuses "a lot more" on posts people send to a friend than on comments. Comment-bait is not the lever.
- Track: sends per reach, likes per reach, average watch time.
- More and more reach comes from recommendations to non-followers. Originality, recency, and a chance for every post ("breakouts") are also ranked.
- Does NOT change reach: scheduling ("I schedule posts all the time"), hashtags (search only), ads, engaging before posting.
- AI content is not throttled but should be labelled. **AI dubbing (12+ languages, opt-in, own voice)** is a reach lever for spoken reels.
- Trial Reels (non-followers first) are fine for testing; re-trialling the same reel is not.
- Users can pick topics in "Your Algorithm": a tight niche is easier to match.

**YouTube Shorts** (YouTube Help + Studio definitions as summarised by clyper.io, tubeanalytics.net, prepublish.ai, 2026):
- Gate signal: "How many chose to view" (viewed vs swiped away) in the first seconds, then average % viewed and average view duration, then likes and surveys.
- Since 2026-08-24 a view counts from frame one; **engaged views** exclude quick swipes and loops.
- The Shorts feed is personalised and tunes for recency; it is separate from long-form.
- Since Oct 2026: channels that mostly re-upload others' videos get less Shorts reach. Ours is original, so we're fine.

## What our own data says (publications.json, as of 2026-10-29 11:11 IST)
Instagram (n=41 reels with reach > 200):
- Median: 1,238 reach, 11.1 s avg watch, 0.48% sends/reach (shares/reach), 7.9% likes/reach, 1.1% saves/reach.
- Correlation with log views: **avg watch time r=0.40**, sends/reach r=0.27, saves/reach r=0.23, likes/reach r=-0.06. This matches Mosseri's ranking.
- Followers gained = 0 on every reel that reports it (n=35). **Reels reach strangers but don't convert them.** That is the growth bottleneck.
- Comments median 0.
- Slot: AM 1,284 vs PM 1,358 (weeks 41-43, n=20 each). No real difference.

YouTube (n=64):
- Slot: **AM 1,139 vs PM 611** (weeks 41-43, n=20 each). Morning wins about 2x, consistent with EXP-002.
- Weekday medians on n=6 per day are noise. Do not act on them.

## Decisions
1. Timing is secondary on IG (Mosseri plus our flat AM/PM). Keep 08:00 + 20:30 IST on Instagram.
2. YouTube: move the evening Short into the morning/midday band. Test 13:00 IST against 20:30 for 14 days (EXP-003), keeping 08:00.
3. New review rules R7 (send-worthy), R8 (first frame), R9 (follow reason). See review-rules.json.
4. Turn on Instagram AI dubbing (Hindi/Spanish/Portuguese where offered) as EXP-004. The user has to enable it in the app because it is opt-in.
5. Track sends/reach and watch time as the IG north-star metrics. Views and comments come second.

## Review 2026-11-12 (official changes since 2026-10-29)
**Instagram**
- 2026-10-21 Meta Q3 call (Susan Li, via smmtoolbox.com/meta-q3-reels-sequence-ranking, fetched 2026-11-12): Reels are now ranked in sequences, not one at a time; **nearly 45% of recommended Reels are under 1 day old** (+11 pts vs Q2). A Reel's first 24 h matter more than ever. Supports posting when our viewers are awake; no new "best time" rule.
- 2026-10-28 to 11-03 Mosseri with Colin & Samir (uppbeat.io/blog/creator-news/whats-working-on-instagram-right-now-carousels-and-sends-says-adam-mosseri, fetched 2026-11-12): **sends per reach** is the key metric for reaching non-followers and is coming to Insights (already in Edits). **Carousels with music now show in the Reels viewer** and can resurface on slide 2. Watch time weighed less than on rival apps. Original creators get more reach. Accounts built around an AI-generated *person* must label themselves (AI-generated profile label, creators.instagram.com/blog/ai-generated-profile-label, 2026-08-31); AI tools in the creative process don't need it. Consistent with R7/R12; no rule contradicted.
- Linked Reels in a series ended 2026-10-28 (metricool.com/instagram-news). Our series continuity relies on captions, not linked Reels, so no change.

**YouTube Shorts**
- No new Shorts ranking change since the 2026-10-01 originality update (we are original). View counting from frame one (2026-08-24) unchanged; recommendations use engaged views.
- 2026-11-03 Data API: `thumbnails.set` now supports **custom thumbnails for Shorts** (developers.google.com/youtube/v3/revision_history). Possible small lever for Shorts shelf/search; not a ranking change.

**Rules:** R1-R15 unchanged; nothing official contradicts them.

**Timing (EXP-005 interim, n<10):** IG 19:30 1,466 (n=8) = 1.08x the 20:30 control; IG 08:00 1,804.5 (n=8). YT 19:30 1,463 (n=7) = 2.39x control and above YT 08:00 1,260 (n=8). Keep 08:00 + 19:30 on both. No 13:00 test; the 05:00 YouTube idea is not supported. Next read 2026-11-26.
