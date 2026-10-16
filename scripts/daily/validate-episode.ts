/** Runs the EXISTING episode validator (EpisodeInputSchema + episode builder) on one file and
 * prints the duration the render will have (same timeline maths as src/Root.tsx), so an episode
 * over the ceiling in config/publishing-rules.json is rejected BEFORE rendering.
 * Usage: npx tsx scripts/daily/validate-episode.ts generated/JR-0037.json */
import fs from "node:fs";
import { EpisodeInputSchema, buildEpisodeAndThumbnail } from "../lib/episodeInput";
import { EpisodePropsSchema } from "../../src/schema";
import { buildRevealFrames } from "../../src/timeline";

const THUMBNAIL_LEAD_FRAMES = 1; // src/Episode.tsx (not imported: it pulls in React/Remotion)
const file = process.argv[2];
try {
  const input = EpisodeInputSchema.parse(JSON.parse(fs.readFileSync(file, "utf-8")));
  const { episode } = buildEpisodeAndThumbnail(input);
  const data = EpisodePropsSchema.parse(episode);
  const fps = data.video.fps;
  const { totalFrames } = buildRevealFrames(data.lines, data.timing, fps);
  const frames = totalFrames + Math.round(data.timing.endPaddingSeconds * fps) + THUMBNAIL_LEAD_FRAMES;
  console.log(`[validate] PASS ${input.id} lines=${data.lines.length} estimated_seconds=${(frames / fps).toFixed(2)} track=${data.audio.track}`);
} catch (e) {
  console.log(`[validate] FAIL ${(e as Error).message.slice(0, 400)}`);
  process.exit(1);
}
