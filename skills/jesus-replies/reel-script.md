# JR reel / short script (adapts /ig-reel + /yt-script + /yt-shorts)

1. Read `voice.md`, `content-os/STRATEGY.md`, `content-os/review-rules.json` (R1–R6) and
   `content-os/learnings.json` (auto block). Our own numbers beat any generic rule in the packs.
2. Pick ONE concrete moment of hidden pain (R1). No other-faith festivals/rituals (R5).
3. Hooks are a confession or a statement only, never a question (R11, DEC-JR-017; YouTube question hooks
   median 382 views vs 1,270 statement / 1,440 confession; the validator fails a question opener).
   Write 3 hook options (different formulas from `vendor/.../ig-reel/hooks.json`), each ≤12 words,
   concrete moment + what they pretended. Score with `hookscore.py`, but treat the score as advisory:
   calibration shows it does not predict our views (`content-os/reviews/skill-calibration.json`).
4. Script: 9 lines, 95–120 spoken words incl. the verse (R6), no line over ~10 words where possible.
   Jesus names the hidden thing; verse verbatim KJV (label "(KJV)", never modernised or trimmed; the wording runs longer, so budget for it inside R6) and meaning in its own passage what the episode uses it for (R10); last line = a share line, speaker `engagement` (R12): "Send this to <who needs it>", worded freshly
   each episode (the validator rejects a word-for-word repeat of the last 7), no "type amen"/comment bait.
   Echo one word from the hook in the closing Jesus line (loop).
5. Run `beats.py --wpm 150 --target 50`, fix long beats, then `/ig-human` / avoid-ai-writing pass.
6. Package: YouTube title `Jesus... <moment> <emoji> | <Ref> #Shorts` (≤100 chars); IG caption opens
   with the moment + one searchable phrase; exactly 5 hashtags (not in caption); disclaimer line
   the honesty line `An imagined reply with AI-made visuals. The Scripture is quoted as written.` last; a share line
   in the caption (R12); no comment-bait. Add `first_comment` (R13): one easy, warm question tied to the
   episode, at most 150 chars ("Has someone in your family ever said this to you?"). Buffer posts it on
   Instagram; the comment run pins it on YouTube.
6b. Family-pressure lane (Monday 08:00): take the week's idea and verse from `content-os/series/family-pressure.json`
   (the brief shows it as `series`), then set that backlog item's `episode_id`/`status` when you author it.
6c. Growth formats (DEC-JR-018): Part 2s, comment replies, Tamil/Hindi subtitle versions and the weekly carousel follow
   `growth-formats.md`. A comment-reply episode posts as a normal Reel (Instagram's 'reply with Reel' is not in the Buffer API).
7. `python3 scripts/content_os/skill_review.py <id>` then the pipeline validator.
