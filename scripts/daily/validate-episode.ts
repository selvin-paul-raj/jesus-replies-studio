/** Runs the EXISTING episode validator (EpisodeInputSchema + episode builder) on one file.
 * Usage: npx tsx scripts/daily/validate-episode.ts generated/JR-0037.json */
import fs from "node:fs";
import { EpisodeInputSchema, buildEpisodeAndThumbnail } from "../lib/episodeInput";
const file = process.argv[2];
try {
  const input = EpisodeInputSchema.parse(JSON.parse(fs.readFileSync(file, "utf-8")));
  const { episode } = buildEpisodeAndThumbnail(input);
  console.log(`[validate] PASS ${input.id} lines=${(episode as any).script?.length ?? "?"}`);
} catch (e) {
  console.log(`[validate] FAIL ${(e as Error).message.slice(0, 400)}`);
  process.exit(1);
}
