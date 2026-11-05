# JR strategist loop: self-evaluating, self-learning, self-reviewing

Runs on top of the content OS (`scripts/content_os/`), which already snapshots Buffer analytics
every 6h into `content-os/analytics/` and rewrites `content-os/learnings.json`.

Each cycle (the weekly review, plus any time on request):
1. **Read the numbers.** `learnings.json` (per-platform medians, slot medians, top themes, stalls),
   `analytics/publications.json` (per-episode views/likes/comments/saves at 24h/72h/7d).
2. **Self-check the tools.** `python3 scripts/content_os/skill_review.py --calibrate`. A generic skill
   signal becomes a rule only at |r| ≥ 0.3 with n ≥ 30 on that platform; otherwise advisory.
3. **Read the audience.** Comment triage (`comment-replies.md`): repeated questions and critiques
   are the strongest qualitative signal (e.g. the Diwali critique led to R5).
4. **Read trends.** Christian calendar ahead (Global Bible Month in Nov, Thanksgiving, Advent,
   Christmas), and what is rising in Christian Shorts/Reels (deep-research / web search), filtered
   through R1–R6. Never chase a trend that breaks R5 or the verbatim-scripture rule (KJV, exact wording, DEC-JR-016).
5. **Decide.** Update `review-rules.json` (each rule cites evidence; keep / change / drop),
   `STRATEGY.md`, and log the decision in `DECISIONS.md` with its reason.
6. **Author.** New episodes via `reel-script.md`; run `skill_review.py` + validator before commit.
7. **Review published work.** At 72h, compare each episode to the platform median; write the
   lesson into the next review, not into a one-off rule.

## Standing items (DEC-JR-017, 2026-11-05)
- Hooks: confession or statement only (R11). Re-check the hook-type medians per platform at each review.
- Family-pressure lane: one per week, Monday 08:00 (`content-os/series/family-pressure.json`). Keep at least
  2 weeks of backlog with context-checked verses (R10). Mark items DONE once published.
- EXP-005 read (2026-11-12): also weigh moving YouTube's evening post to 05:00 IST against 19:30 (see the
  experiments.json EXP-005 review_notes). Change slots only at n>=10, only for posts not yet in Buffer, and never
  touch the Instagram slots in this read.

## Standing items (DEC-JR-018, 2026-11-05)
- Weekly lanes: comment-replies (Thu 19:30), subtitles-ta (Wed 19:30), subtitles-hi (Sat 19:30). Check `ready-buffer.json lane_gaps`
  each cycle and author the missing week (see `growth-formats.md`). Part 2s go in `content-os/series/sequels.json` when an episode breaks out.
- Saturday 12:30 Instagram carousel: author + render + push one `content-os/carousels/CAR-<date>.json` each week.
- Sunday: the compilation release appears as `jr-compilation-<week>`; tell Selvin it is ready for a YouTube Studio upload.
- After 4 weeks, read subtitle versions and comment replies against the weekly median; drop or keep with evidence.
