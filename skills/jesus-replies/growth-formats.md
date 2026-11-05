# Growth formats (DEC-JR-018, 2026-11-05)

All five go through the normal gates. Scripture is verbatim KJV and must mean in its own passage what the post uses it for (R10).

## Part 2 (sequel)
- Trigger: a breakout (>= 5x platform median). Same character, new KJV verse (not used in the last 14), confession/statement hook (R11), share line (R12), first_comment (R13).
- Add a backlog item to `content-os/series/sequels.json` with its own `weekday`/`slot` (next open slot, never the Monday family-pressure slot) and the `episode_id`. Episode fields: `series: "sequels"`, `part: 2`, `part_of`.
- Caption: "Part 2." + "Missed Part 1? \"<Part 1 title>\" is on our page." Never write the other episode's id (package QA rejects it). YouTube description: link the Part 1 Short (Buffer post `externalLink`).

## Jesus replies to your comment (Thursday 19:30)
- Source: a comment logged in `content-os/community/replies-log.md` or `ideas.md`, quoted exactly as logged. Respectful pain/question comments only. Never a crisis comment (self-harm, suicide, abuse: reply with the helpline line instead), a critique, an AI accusation, a song-name ask or bait.
- Episode: `format: "comment-reply"`, `series: "comment-replies"`, `comment: {text, platform, date, handle: null, show_handle: false, source}`. The renderer shows the comment card at the top ("A viewer commented on YouTube"); the handle stays hidden unless config `comment_reply.show_handle` is true AND the commenter agreed (record it in the episode).
- Add the backlog item to `content-os/series/comment-replies.json`; `ready-buffer.json lane_gaps` lists weeks still missing one.
- Instagram's native "reply to comment with a Reel" is NOT in the Buffer API. Post it as a normal Reel/Short; after it goes live, the comment run may reply to the original comment with a short note that the video is up (no link pasting on Instagram).

## Tamil / Hindi subtitle versions (Wed 19:30 Tamil, Sat 19:30 Hindi)
- Opt-in by `config/content-os.json subtitle_versions` (default ON, one per week per language).
- Pick: config `subtitle_versions.pick_rule` (best last-7-days performer, not held, not already subtitled in that language, verse passes a fresh R10 read). Use different source episodes for Tamil and Hindi in the same week.
- New episode id; copy the source lines unchanged, `variant_of: <source id>`, `series: "subtitles-<lang>"`, verse re-quoted in KJV, and
  `subtitles: {lang, bible: data/bible/<lang>-irv.json, attribution: <bundle attribution_line>, verse_text: <bundle text for the same ref, verbatim>, verse_label: "<Ref> (IRV Tamil|Hindi)", lines: [one natural human translation per script line, null at bible_verse]}`.
- Story lines: natural spoken Tamil/Hindi (colloquial is fine), no emoji. Scripture: only the bundled IRV text, never translated by hand or machine.
- Caption and description: "With Tamil/Hindi subtitles." line + the attribution line (CC BY-SA 4.0 requires it) + the honesty line.
- Licence: IRV Tamil/Hindi © Bridge Connectivity Solutions, CC BY-SA 4.0 (eBible.org). Rebuild with `scripts/subtitles/build_irv_bibles.py`.

## Weekly YouTube compilation (Sunday 21:00, automatic)
- `.github/workflows/jr-weekly-compilation.yml` -> release `jr-compilation-<week_start>` (mp4 + compilation.json + description.txt). Buffer is Shorts-only, so upload it in YouTube Studio by hand: title and description from the release, category 27, not made for kids. Nothing is posted automatically.

## Weekly Instagram verse carousel (Saturday 12:30)
- Author `content-os/carousels/CAR-<date>.json` (cover, 3-5 verse slides with `ref`, verbatim KJV `text`, `label`, `r10_context`, closing share slide; caption with share line and KJV labels; 5 hashtags; first_comment).
- `npx tsx scripts/content_os/render_carousel.ts CAR-<date>` -> slides PNG; commit and push (URLs pin that commit); the content-OS cycle (or `python3 scripts/content_os/cli.py carousel`) schedules it once.
