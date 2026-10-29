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
