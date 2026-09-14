import { z } from "zod";
import { EpisodeSchema, ThumbnailPropsSchema } from "./schema";
import { resolveBackgroundImage, resolveMusicFile, BRAND_ASSETS } from "./assetResolver";

/**
 * ============================================================================
 * SCRIPT ADAPTER -- converts an authored script (absolute-timestamp scenes,
 * as produced upstream) into the Episode/Thumbnail props this renderer
 * consumes. Kept separate from schema.ts: that file defines the renderer's
 * own shape, this file only knows how to translate one external format into
 * it. Node-only -- never imported by the Remotion components.
 * ============================================================================
 */

/** `text` is optional: "bible_verse" resolves from `video.bible.text` and
 * "brand" needs no text at all (the logo image already carries the brand
 * name) -- see scriptToEpisode for which speakers actually require it. */
export const SceneSchema = z.object({
  start: z.number().min(0),
  end: z.number().min(0),
  speaker: z.string(),
  text: z.string().optional(),
});

export const ScriptSchema = z.object({
  id: z.string(),
  video: z.object({
    duration: z.number().min(0),
    language: z.string().optional(),
    /** The speaker value in `scenes` that represents the human character.
     * Accepted as either the literal "person" or this value itself (e.g.
     * "boy"), for back-compat with older scripts. */
    character: z.string(),
    topic: z.string(),
    title: z.string(),
    scenes: z.array(SceneSchema).min(1),
    bible: z
      .object({
        book: z.string(),
        chapter: z.union([z.number(), z.string()]),
        verse: z.union([z.number(), z.string()]),
        version: z.string().optional(),
        /** The actual verse text. Required for "bible_verse" scenes that
         * omit their own `text` -- see scriptToEpisode. */
        text: z.string().optional(),
      })
      .optional(),
    music: z
      .object({
        type: z.string(),
        volume: z.number().min(0).max(1).default(1),
      })
      .optional(),
  }),
});
export type Script = z.infer<typeof ScriptSchema>;

/** "Matthew 18:20\nKJV" -- used only when a "reference" scene omits its own
 * `text`; if the script already writes the reference out, that's used as-is.
 * Stacked on its own line (TextBlock renders each "\n"-separated segment as
 * its own line) so book+chapter:verse and the version read as one cohesive
 * two-line citation under the verse, not a single run-on line. */
export function formatBibleRef(bible: { book: string; chapter: number | string; verse: number | string; version?: string }): string {
  const ref = `${bible.book} ${bible.chapter}:${bible.verse}`;
  return bible.version ? `${ref}\n${bible.version}` : ref;
}

/**
 * Converts one authored script into the Episode shape the renderer consumes.
 * Reuses the existing cumulative-pairs reveal logic (timeline.ts) unchanged
 * by giving each line its own authored duration (scene.end - scene.start)
 * and zeroing the auto-timing gap, so playback matches the scenes' start/end
 * exactly instead of being recomputed from word count.
 */
/** Scene text is required for these speakers -- there's no sensible
 * auto-generated fallback for what a person actually says. */
function requireText(scene: z.infer<typeof SceneSchema>, context: string): string {
  if (!scene.text || !scene.text.trim()) {
    throw new Error(`Scene "${context}" (${scene.start}-${scene.end}s) requires non-empty text`);
  }
  return scene.text;
}

export function scriptToEpisode(script: Script): z.input<typeof EpisodeSchema> {
  const { video } = script;
  const lines: z.input<typeof EpisodeSchema>["lines"] = [];
  let finalLogoDuration = 0;

  for (const scene of video.scenes) {
    const durationInSeconds = scene.end - scene.start;
    // "person" is the canonical speaker value; video.character (e.g. "boy")
    // is accepted too for older scripts that used it as both the speaker
    // label and the background-art selector.
    const isPerson = scene.speaker === "person" || scene.speaker === video.character;

    if (isPerson) {
      lines.push({ speaker: "person", text: requireText(scene, "person"), durationInSeconds });
    } else if (scene.speaker === "jesus") {
      lines.push({ speaker: "jesus", text: requireText(scene, "jesus"), durationInSeconds });
    } else if (scene.speaker === "bible_verse" || scene.speaker === "bible") {
      // Always prefer the real, full verse from video.bible.text over
      // whatever the scene itself carries -- a scene's own text is often
      // just the reference (or omitted entirely) and must never stand in
      // for the actual quote. "verse" only stages the quote text
      // (timeline.ts holds it until the paired "reference" line, which
      // carries the actual on-screen duration).
      const verseText = video.bible?.text ?? scene.text;
      if (!verseText || !verseText.trim()) {
        throw new Error(
          `"bible_verse" scene (${scene.start}-${scene.end}s) has no text and video.bible.text is missing`
        );
      }
      // Own duration matters: the verse is visible alone for its full
      // authored slice, same pattern as person -> jesus (see timeline.ts),
      // then "reference" joins it for reference's own slice.
      lines.push({ speaker: "verse", text: verseText, durationInSeconds });
    } else if (scene.speaker === "reference") {
      lines.push({
        speaker: "reference",
        text: scene.text?.trim() ? scene.text : video.bible ? formatBibleRef(video.bible) : "",
        durationInSeconds,
      });
    } else if (scene.speaker === "engagement") {
      lines.push({ speaker: "engagement", text: requireText(scene, "engagement"), durationInSeconds });
    } else if (scene.speaker === "brand") {
      finalLogoDuration += durationInSeconds;
    } else {
      throw new Error(
        `Unrecognized scene speaker "${scene.speaker}" (expected "person" (or "${video.character}"), "jesus", ` +
          `"bible_verse"/"bible", "reference", "engagement", or "brand")`
      );
    }
  }

  return {
    title: video.title,
    background: {
      image: resolveBackgroundImage(video.character, video.topic),
      bottomLogo: BRAND_ASSETS.bottomLogo,
    },
    audio: {
      track: video.music ? resolveMusicFile(video.music.type) : "hallelujah.mp3",
      volume: video.music?.volume ?? 1,
    },
    timing: {
      gapSeconds: 0,
      endPaddingSeconds: finalLogoDuration > 0 ? finalLogoDuration : 2,
    },
    lines,
    finalLogo:
      finalLogoDuration > 0
        ? {
            image: BRAND_ASSETS.followLogo,
            durationSeconds: finalLogoDuration,
            ctaLabel: "Follow for more Bible conversations",
            secondaryCtaLabel: "Save this for later",
          }
        : undefined,
  };
}

export function scriptToThumbnail(script: Script): z.input<typeof ThumbnailPropsSchema> {
  return {
    title: script.video.title,
    image: resolveBackgroundImage(script.video.character, script.video.topic),
  };
}
