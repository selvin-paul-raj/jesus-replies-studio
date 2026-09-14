import fs from "node:fs";
import path from "node:path";

const PUBLIC_DIR = path.join(__dirname, "..", "public");

/**
 * ============================================================================
 * ASSET RESOLVER -- maps script-level identifiers (character, topic, music
 * type) to actual files under public/. Centralized here so scriptAdapter.ts
 * and any future script source stay agnostic of the public/ folder layout.
 * Node-only (uses fs) -- never imported by the Remotion components.
 * ============================================================================
 */

/** public/backgrounds/<character>_<topic>.png, falling back to
 * public/backgrounds/<character>.png, then the default boy art -- add more
 * files (e.g. girl.png) as new character/topic art is made. */
export function resolveBackgroundImage(character: string, topic: string): string {
  const candidates = [`backgrounds/${character}_${topic}.png`, `backgrounds/${character}.png`];
  for (const candidate of candidates) {
    if (fs.existsSync(path.join(PUBLIC_DIR, candidate))) return candidate;
  }
  console.warn(
    `[assetResolver] no background art for character "${character}"/topic "${topic}", falling back to backgrounds/boy.png`
  );
  return "backgrounds/boy.png";
}

/** music.type -> public/audio/ filename. Extend as more tracks are added. */
const MUSIC_TYPE_FILES: Record<string, string> = {
  soft_christian_instrumental: "audio/hallelujah.mp3",
};

export function resolveMusicFile(type: string): string {
  const file = MUSIC_TYPE_FILES[type];
  if (file) return file;
  console.warn(`[assetResolver] no music mapped for type "${type}", falling back to audio/hallelujah.mp3`);
  return "audio/hallelujah.mp3";
}

/** Brand assets used by the end card / bottom logo -- fixed paths, kept here
 * so EndCard/Background/scriptAdapter never hardcode public/ paths inline. */
export const BRAND_ASSETS = {
  bottomLogo: "branding/bottom.png",
  followLogo: "branding/follow.png",
};
