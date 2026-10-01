import fs from "node:fs";
import path from "node:path";
import { execSync } from "node:child_process";
import { Episode, ThumbnailProps } from "../../src/schema";
import os from "node:os";

/** Writes the resolved props next to the render output and shells out to
 * `remotion render`/`still`, same two-artifact pattern as build-episode.ts
 * (kept there unchanged; this is the shared bit the new CLI also uses).
 * Takes `Episode` (not `EpisodeProps`): `audioDurationInFrames` is always
 * recomputed by Root.tsx's calculateMetadata from the real audio file at
 * render time, so a written placeholder is never actually used -- same as
 * the existing build-episode.ts, which also writes just `Episode`. */
/**
 * ENG-002: this was hardcoded to --concurrency=16, which hard-fails on any runner with
 * fewer cores (GitHub hosted runners included). Use what the machine actually has,
 * capped at 16 so behaviour on a big machine is unchanged. Override with JR_RENDER_CONCURRENCY.
 */
function renderConcurrency(): number {
  const override = Number(process.env.JR_RENDER_CONCURRENCY);
  if (Number.isInteger(override) && override > 0) return override;
  const cores = typeof os.availableParallelism === "function" ? os.availableParallelism() : os.cpus().length;
  return Math.max(1, Math.min(16, cores));
}

export function renderEpisode(
  episode: Episode,
  thumbnail: ThumbnailProps,
  id: string,
  outDir: string
): { videoOut: string; thumbOut: string } {
  const propsDir = path.join(outDir, "props");
  const videosDir = path.join(outDir, "videos");
  const thumbnailsDir = path.join(outDir, "thumbnails");
  fs.mkdirSync(propsDir, { recursive: true });
  fs.mkdirSync(videosDir, { recursive: true });
  fs.mkdirSync(thumbnailsDir, { recursive: true });

  const episodePropsPath = path.join(propsDir, `${id}.episode-props.json`);
  const thumbnailPropsPath = path.join(propsDir, `${id}.thumbnail-props.json`);
  fs.writeFileSync(episodePropsPath, JSON.stringify(episode, null, 2));
  fs.writeFileSync(thumbnailPropsPath, JSON.stringify(thumbnail, null, 2));

  const rootDir = path.join(__dirname, "..", "..");
  const videoOut = path.join(videosDir, `${id}.mp4`);
  const thumbOut = path.join(thumbnailsDir, `${id}-thumb.png`);

  execSync(
    `npx remotion render src/index.ts Episode "${videoOut}" --props="${episodePropsPath}" --concurrency=${renderConcurrency()}`,
    { cwd: rootDir, stdio: "inherit" }
  );
  execSync(`npx remotion still src/index.ts Thumbnail "${thumbOut}" --props="${thumbnailPropsPath}"`, {
    cwd: rootDir,
    stdio: "inherit",
  });

  return { videoOut, thumbOut };
}
