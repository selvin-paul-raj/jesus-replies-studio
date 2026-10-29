# skills/ — creator skill library for Jesus Replies

Everything here is reusable by any agent (Hark, Claude Code, Codex). Vendored packs keep
their original MIT/Apache licenses next to them.

| Folder | What it is | Source / license |
| --- | --- | --- |
| `jesus-replies/voice.md` | Channel voice profile. Every skill reads it. | ours |
| `jesus-replies/*.md` | JR-adapted playbooks: reel/short script, comment replies, strategist loop | ours (built on the packs below) |
| `vendor/instagram-agent-skill/` | `/ig-reel` `/ig-caption` `/ig-reply` `/ig-comment` `/ig-human` `/ig-audit` `/ig-plan` `/ig-viral` `/ig-story` `/ig-carousel` `/ig-dm` `/ig-profile` `/ig-repurpose` | github.com/Jakeschincariol/instagram-agent-skill (MIT) |
| `vendor/youtube-agent-skill/` | `/yt-script` `/yt-shorts` `/yt-comment` `/yt-package` `/yt-seo` `/yt-retention` `/yt-audit` `/yt-plan` `/yt-viral` `/yt-chapters` `/yt-edit` | github.com/Jakeschincariol/youtube-agent-skill (MIT) |
| `vendor/instagram-skills/` | ig-audience-insights, ig-caption-writer, ig-hashtag-strategist, ig-hook-extractor, ig-humanizer, ig-content-planner, ig-profile-optimizer, ig-repurposer, ig-carousel-planner (+ Codex plugin manifests) | github.com/sergebulaev/instagram-skills (MIT) |
| `vendor/creator/avoid-ai-writing/` | AI-pattern detector + voice-preserving rewriter | github.com/conorbronsdon/avoid-ai-writing |
| `vendor/creator/persona/` | audience persona builder | github.com/takechanman1228/claude-persona |
| `vendor/creator/brainstorming/` | structured ideation | github.com/obra/superpowers |
| `vendor/creator/brand-guidelines/`, `skill-creator/` | brand rules, build-your-own-skill | github.com/anthropics/skills |
| `vendor/creator/youtube-transcript/`, `article-extractor/` | research inputs | github.com/michalparkola/tapestry-skills-for-claude-code |
| `vendor/creator/deep-research/` | structured research reports | github.com/sanjay3290/ai-skills |

Picked from the "50 Claude skills for content creators" list (dkspeaks, Jun 2026): only the
ones that serve this channel. Skipped: docx/pptx/xlsx/epub, email marketing, TTS/music
(we already have TTS + BGM in `scripts/audio`), image/video generators.

## Install for Claude Code / Codex

```bash
bash skills/install.sh          # links packs into ~/.claude/skills and voice.md into place
# Codex (sergebulaev pack):
cd skills/vendor/instagram-skills && codex plugin marketplace add . && codex plugin add instagram-skills@instagram-skills
```

## Verified tools (2026-10-29)

```bash
python3 skills/vendor/instagram-agent-skill/skills/ig-reel/hookscore.py --hook "..."   # /ig-reel hook scorer
python3 skills/vendor/instagram-agent-skill/skills/ig-reel/beats.py script.txt --target 50 --wpm 150
python3 skills/vendor/youtube-agent-skill/skills/yt-script/hookscore.py --hook "..."   # /yt-script hook scorer
python3 scripts/content_os/skill_review.py JR-0083 ...      # runs both on episodes -> content-os/reviews/
python3 scripts/content_os/skill_review.py --calibrate      # self-check vs real views
```

**Calibration matters:** on our own 47+47 published episodes, the generic hook score does not
predict views (IG r=0.19, YT r=-0.30), but script length does (IG r=-0.43). So length/beat
flags feed rule R6; the hook score is advisory only. Re-run `--calibrate` each review.
