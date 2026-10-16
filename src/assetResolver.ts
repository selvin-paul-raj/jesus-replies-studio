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

/** Original background tracks (public/audio/LICENSES.md). Made for this project by
 * scripts/audio/make_bgm.py; replaced a third-party track on 2026-10-16
 * (DEC-JR-007). Episodes rotate through them deterministically by episode id. */
export const BGM_TRACKS: readonly string[] = [
  "audio/bgm-01.mp3",
  "audio/bgm-02.mp3",
  "audio/bgm-03.mp3",
  "audio/bgm-04.mp3",
  "audio/bgm-05.mp3",
];

/** FNV-1a 32-bit -- small, stable across Node versions, mirrored in Python tests. */
export function fnv1a(text: string): number {
  let h = 0x811c9dc5;
  for (const ch of Buffer.from(text, "utf8")) {
    h ^= ch;
    h = Math.imul(h, 0x01000193) >>> 0;
  }
  return h >>> 0;
}

/** Same episode id -> same track, every render. */
export function pickBgmTrack(seed: string): string {
  return BGM_TRACKS[fnv1a(seed) % BGM_TRACKS.length];
}

/** music.type is kept for old episode files: every known type now maps to the rotation. */
const MUSIC_TYPES = new Set(["soft_christian_instrumental", "soft_worship_ambient"]);

export function resolveMusicFile(type: string | undefined, seed: string): string {
  if (type && !MUSIC_TYPES.has(type)) {
    console.warn(`[assetResolver] unknown music type "${type}", using the original-track rotation`);
  }
  return pickBgmTrack(seed);
}

/** An explicit `track` wins only if it is one of the licensed tracks in public/audio/LICENSES.md
 * (BGM_TRACKS) or a remote URL; anything else (e.g. removed third-party audio) falls back. */
export function resolveTrack(track: string | undefined, type: string | undefined, seed: string): string {
  if (track && (track.startsWith("http") || (BGM_TRACKS.includes(track) && fs.existsSync(path.join(PUBLIC_DIR, track))))) {
    return track;
  }
  if (track) console.warn(`[assetResolver] track "${track}" is not a licensed project track; using the original-track rotation`);
  return resolveMusicFile(type, seed);
}

/** Brand assets used by the end card / bottom logo -- fixed paths, kept here
 * so EndCard/Background/scriptAdapter never hardcode public/ paths inline. */
export const BRAND_ASSETS = {
  bottomLogo: "branding/bottom.png",
  followLogo: "branding/follow.png",
};
