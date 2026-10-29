# JR reel / short script (adapts /ig-reel + /yt-script + /yt-shorts)

1. Read `voice.md`, `content-os/STRATEGY.md`, `content-os/review-rules.json` (R1–R6) and
   `content-os/learnings.json` (auto block). Our own numbers beat any generic rule in the packs.
2. Pick ONE concrete moment of hidden pain (R1). No other-faith festivals/rituals (R5).
3. Write 3 hook options (different formulas from `vendor/.../ig-reel/hooks.json`), each ≤12 words,
   concrete moment + what they pretended. Score with `hookscore.py`, but treat the score as advisory:
   calibration shows it does not predict our views (`content-os/reviews/skill-calibration.json`).
4. Script: 9 lines, 95–120 spoken words incl. the verse (R6), no line over ~10 words where possible.
   Jesus names the hidden thing; verse verbatim BSB; last line "Send this to <specific person>" (R3).
   Echo one word from the hook in the closing Jesus line (loop).
5. Run `beats.py --wpm 150 --target 50`, fix long beats, then `/ig-human` / avoid-ai-writing pass.
6. Package: YouTube title `Jesus... <moment> <emoji> | <Ref> #Shorts` (≤100 chars); IG caption opens
   with the moment + one searchable phrase; exactly 5 hashtags (not in caption); disclaimer line
   `An imagined reply. The Scripture is quoted as written.`; no comment-bait.
7. `python3 scripts/content_os/skill_review.py <id>` then the pipeline validator.
