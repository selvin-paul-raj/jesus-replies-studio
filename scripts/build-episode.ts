import fs from "node:fs";
import path from "node:path";
import { execSync } from "node:child_process";
import { ScriptSchema, scriptToEpisode, scriptToThumbnail } from "../src/scriptAdapter";
import { EpisodeSchema, ThumbnailPropsSchema } from "../src/schema";
import { buildSocialMeta } from "../src/socialMeta";

const inputPath = process.argv[2];
if (!inputPath) {
  console.error("Usage: npm run build-episode <path-to-script.json>");
  process.exit(1);
}

const raw = JSON.parse(fs.readFileSync(inputPath, "utf-8"));
const script = ScriptSchema.parse(raw);

const lastSceneEnd = Math.max(...script.video.scenes.map((s) => s.end));
if (Math.abs(lastSceneEnd - script.video.duration) > 0.01) {
  console.warn(
    `[build-episode] video.duration (${script.video.duration}s) doesn't match the last scene's end ` +
      `(${lastSceneEnd}s) -- using the scenes' own timing.`
  );
}

const episode = EpisodeSchema.parse(scriptToEpisode(script));
const thumbnail = ThumbnailPropsSchema.parse(scriptToThumbnail(script));

const rootDir = path.join(__dirname, "..");
const outDir = path.join(rootDir, "output");
fs.mkdirSync(outDir, { recursive: true });

const episodePropsPath = path.join(outDir, `${script.id}.episode-props.json`);
const thumbnailPropsPath = path.join(outDir, `${script.id}.thumbnail-props.json`);
fs.writeFileSync(episodePropsPath, JSON.stringify(episode, null, 2));
fs.writeFileSync(thumbnailPropsPath, JSON.stringify(thumbnail, null, 2));

const videoOut = path.join(outDir, `${script.id}.mp4`);
const thumbOut = path.join(outDir, `${script.id}-thumb.png`);

console.log(`[build-episode] rendering ${videoOut} ...`);
execSync(`npx remotion render src/index.ts Episode "${videoOut}" --props="${episodePropsPath}"`, {
  cwd: rootDir,
  stdio: "inherit",
});

console.log(`[build-episode] rendering ${thumbOut} ...`);
execSync(`npx remotion still src/index.ts Thumbnail "${thumbOut}" --props="${thumbnailPropsPath}"`, {
  cwd: rootDir,
  stdio: "inherit",
});

const socialOut = path.join(outDir, `${script.id}.social.json`);
const social = buildSocialMeta(script); // throws with a clear message if any limit is exceeded
fs.writeFileSync(socialOut, JSON.stringify(social, null, 2));

console.log(`[build-episode] done:\n  ${videoOut}\n  ${thumbOut}\n  ${socialOut}`);
