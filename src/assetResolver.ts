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

/** Art lives one folder per base character: public/backgrounds/<folder>/...
 * (public/backgrounds/boy/boy_1.png, public/backgrounds/girl/girl_2_sad.png,
 * etc.) -- "folder" is the character with any trailing _<n> stripped, so
 * "boy" and "boy_2" both resolve into backgrounds/boy/.
 *
 * Within that folder: <character>_<topic>.png, falling back to
 * <character>.png, then <variant>.png (the default numbered variant -- a
 * bare "boy"/"girl" character picks variant 1, while "boy_2"/"girl_2" etc.
 * picks that exact variant directly).
 *
 * `emotion` (one of "neutral", "happy", "sad", "crying", "worried", "angry",
 * "hopeful"), when given, is tried first as <variant>_<emotion>.png (e.g.
 * "sad" -> boy_1_sad.png / girl_1_sad.png); "neutral" has no art of its own
 * and -- like a missing/unmade emotion file -- falls through silently to
 * the same plain-variant candidates as no emotion at all. */
export function resolveBackgroundImage(character: string, topic: string, emotion?: string): string {
  const folder = character.replace(/_\d+$/, "");
  const variant = /_\d+$/.test(character) ? character : `${character}_1`;
  const candidates = [
    `backgrounds/${folder}/${character}_${topic}.png`,
    ...(emotion ? [`backgrounds/${folder}/${variant}_${emotion}.png`] : []),
    `backgrounds/${folder}/${character}.png`,
    `backgrounds/${folder}/${variant}.png`,
  ];
  for (const candidate of candidates) {
    if (fs.existsSync(path.join(PUBLIC_DIR, candidate))) return candidate;
  }
  console.warn(
    `[assetResolver] no background art for character "${character}"/topic "${topic}", falling back to backgrounds/boy/boy_1.png`
  );
  return "backgrounds/boy/boy_1.png";
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
