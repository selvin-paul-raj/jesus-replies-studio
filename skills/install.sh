#!/usr/bin/env bash
# Link the skill packs into Claude Code's skill dir and put the channel voice in place.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
DEST="${CLAUDE_SKILLS_DIR:-$HOME/.claude/skills}"
mkdir -p "$DEST" "$HOME/.claude/instagram" "$HOME/.claude/youtube"
for d in "$HERE"/vendor/instagram-agent-skill/skills/* "$HERE"/vendor/youtube-agent-skill/skills/* \
         "$HERE"/vendor/instagram-skills/skills/* "$HERE"/vendor/creator/*; do
  [ -f "$d/SKILL.md" ] || continue
  ln -sfn "$d" "$DEST/$(basename "$d")"
done
for d in "$HERE"/vendor/creator/avoid-ai-writing/*; do [ -f "$d/SKILL.md" ] && ln -sfn "$d" "$DEST/$(basename "$d")"; done
ln -sfn "$HERE/jesus-replies/voice.md" "$HOME/.claude/instagram/voice.md"
ln -sfn "$HERE/jesus-replies/voice.md" "$HOME/.claude/youtube/voice.md"
echo "linked $(ls "$DEST" | wc -l) skills into $DEST; voice.md in ~/.claude/{instagram,youtube}/"
