import { z } from "zod";
import {
  EpisodeSchema,
  ThumbnailPropsSchema,
  StylesSchema,
  SpeakerStyleSchema,
  BackgroundConfigSchema,
  FinalLogoConfigSchema,
} from "../../src/schema";
import { resolveBackgroundImage, resolveMusicFile, BRAND_ASSETS } from "../../src/assetResolver";
import { formatBibleRef } from "../../src/scriptAdapter";

/**
 * ============================================================================
 * CLI EPISODE INPUT -- a simpler authoring shape than scriptAdapter.ts's
 * Script (which needs absolute scene start/end timestamps from an upstream
 * tool). Here `lines` needs only {speaker, text}; duration is auto-timed the
 * same way porch_conversation.json already works. Kept in its own module,
 * separate from scriptAdapter.ts, so the existing script-based pipeline
 * (scripts/build-episode.ts) is untouched.
 * ============================================================================
 */

const StyleOverrideSchema = SpeakerStyleSchema.partial();

export const EpisodeInputBibleSchema = z.object({
  book: z.string(),
  chapter: z.union([z.number(), z.string()]),
  verse: z.union([z.number(), z.string()]),
  version: z.string().optional(),
  /** The full verse text -- the single source of truth; a "bible_verse"
   * line below never carries its own text, avoiding duplication. */
  text: z.string(),
});

export const EpisodeInputLineSchema = z.object({
  /** "bible_verse" is a position-only marker -- no text of its own -- that
   * expands into a "verse"+"reference" pair sourced from `bible` below. */
  speaker: z.enum(["person", "jesus", "bible_verse", "engagement"]),
  text: z.string().optional(),
  durationInSeconds: z.number().min(0).optional(),
});

export const EpisodeInputSchema = z.object({
  id: z.string().min(1),
  title: z.string(),
  /** Selects background art via assetResolver's character_topic.png lookup. */
  character: z.string().default("boy"),
  topic: z.string().default("general"),
  background: BackgroundConfigSchema.partial().optional(),
  bible: EpisodeInputBibleSchema.optional(),
  lines: z.array(EpisodeInputLineSchema).min(1),
  /** Per-episode color/animation overrides -- merged on top of the curated
   * per-speaker defaults (see buildEpisodeAndThumbnail), not a raw replace. */
  styles: z
    .object({
      person: StyleOverrideSchema.optional(),
      jesus: StyleOverrideSchema.optional(),
      verse: StyleOverrideSchema.optional(),
      reference: StyleOverrideSchema.optional(),
      engagement: StyleOverrideSchema.optional(),
    })
    .optional(),
  music: z
    .object({
      /** Either a known type key (assetResolver.resolveMusicFile) or a
       * direct public/ path via `track`. */
      type: z.string().optional(),
      track: z.string().optional(),
      volume: z.number().min(0).max(1).default(1),
    })
    .optional(),
  // Not .partial(): unlike background.image (auto-resolved from
  // character/topic), a final-logo image has no sensible fallback -- if
  // an episode wants an end card, it must supply the image explicitly.
  // The other fields already have their own per-field defaults.
  finalLogo: FinalLogoConfigSchema.optional(),
});
export type EpisodeInput = z.infer<typeof EpisodeInputSchema>;

function requireLineText(line: z.infer<typeof EpisodeInputLineSchema>): string {
  if (!line.text || !line.text.trim()) {
    throw new Error(`"${line.speaker}" line requires non-empty text`);
  }
  return line.text;
}

/** Deep-merge safety note: StylesSchema.person/jesus/etc. each carry a
 * curated `.default({...})` (anchor, position, entrance) that only applies
 * when the WHOLE key is absent -- passing a partial override object would
 * otherwise fall through to SpeakerStyleSchema's own generic per-field
 * defaults and silently reset position/anchor. Resolving the full curated
 * defaults first, then shallow-merging overrides on top, avoids that. */
function mergeStyles(overrides: NonNullable<EpisodeInput["styles"]> | undefined) {
  const base = StylesSchema.parse({});
  return {
    person: { ...base.person, ...overrides?.person },
    jesus: { ...base.jesus, ...overrides?.jesus },
    verse: { ...base.verse, ...overrides?.verse },
    reference: { ...base.reference, ...overrides?.reference },
    engagement: { ...base.engagement, ...overrides?.engagement },
  };
}

export function buildEpisodeAndThumbnail(input: EpisodeInput) {
  const lines: z.input<typeof EpisodeSchema>["lines"] = [];

  for (const line of input.lines) {
    if (line.speaker === "bible_verse") {
      if (!input.bible) {
        throw new Error(`line "bible_verse" used but no top-level "bible" object was given`);
      }
      lines.push({ speaker: "verse", text: input.bible.text, durationInSeconds: line.durationInSeconds });
      lines.push({ speaker: "reference", text: formatBibleRef(input.bible) });
    } else {
      lines.push({ speaker: line.speaker, text: requireLineText(line), durationInSeconds: line.durationInSeconds });
    }
  }

  const bg = input.background;
  const background = {
    image: bg?.image ?? resolveBackgroundImage(input.character, input.topic),
    zoomEnabled: bg?.zoomEnabled,
    zoomFromScale: bg?.zoomFromScale,
    zoomToScale: bg?.zoomToScale,
    overlayEnabled: bg?.overlayEnabled,
    overlayColor: bg?.overlayColor,
    bottomLogo: bg?.bottomLogo ?? BRAND_ASSETS.bottomLogo,
  };

  const episode = EpisodeSchema.parse({
    title: input.title,
    background,
    audio: {
      track: input.music?.track ?? (input.music?.type ? resolveMusicFile(input.music.type) : "audio/hallelujah.mp3"),
      volume: input.music?.volume,
    },
    styles: mergeStyles(input.styles),
    lines,
    finalLogo: input.finalLogo,
  } satisfies z.input<typeof EpisodeSchema>);

  const thumbnail = ThumbnailPropsSchema.parse({ title: input.title, image: background.image });

  return { episode, thumbnail };
}
