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
   through R1–R6. Never chase a trend that breaks R5 or the verbatim-scripture rule.
5. **Decide.** Update `review-rules.json` (each rule cites evidence; keep / change / drop),
   `STRATEGY.md`, and log the decision in `DECISIONS.md` with its reason.
6. **Author.** New episodes via `reel-script.md`; run `skill_review.py` + validator before commit.
7. **Review published work.** At 72h, compare each episode to the platform median; write the
   lesson into the next review, not into a one-off rule.
