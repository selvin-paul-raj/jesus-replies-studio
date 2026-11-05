import { z } from "zod";
import {
  EpisodeSchema,
  ThumbnailPropsSchema,
  StylesSchema,
  SpeakerStyleSchema,
  BackgroundConfigSchema,
  FinalLogoConfigSchema,
} from "../../src/schema";
import { resolveBackgroundImage, resolveTrack, BRAND_ASSETS } from "../../src/assetResolver";
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
  /** Optional mood variant of the resolved character/variant art, e.g.
   * "sad" -> boy_1_sad.png / girl_2_sad.png. One of "neutral" (no art of
   * its own -- same as omitting it), "happy", "sad", "crying", "worried",
   * "angry", "hopeful". */
  emotion: z.string().optional(),
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
  // .partial(): every episode gets an end card by default (branding/follow.png,
  // "Stay with Jesus" / "Carry this with you" -- see buildEpisodeAndThumbnail),
  // same auto-resolve-then-override pattern as `background`. Any field here
  // overrides just that one.
  finalLogo: FinalLogoConfigSchema.partial().optional(),
  /** DEC-JR-018 subtitle version: lines[] aligned 1:1 with `lines` (null for bible_verse);
   * verse_text is the bundled IRV text (checked verbatim by the Python validator). */
  subtitles: z
    .object({
      lang: z.enum(["ta", "hi"]),
      bible: z.string().optional(),
      attribution: z.string().optional(),
      verse_text: z.string(),
      verse_label: z.string(),
      lines: z.array(z.string().nullable()),
    })
    .optional(),
  variant_of: z.string().optional(),
  /** DEC-JR-018 "Jesus replies to your comment". */
  format: z.string().optional(),
  comment: z
    .object({
      text: z.string().min(1),
      platform: z.string().optional(),
      date: z.string().optional(),
      handle: z.string().nullable().optional(),
      show_handle: z.boolean().default(false),
      source: z.string().optional(),
    })
    .optional(),
  series: z.string().optional(),
  part: z.number().optional(),
  part_of: z.string().optional(),
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

  const subs = input.subtitles;
  if (subs && subs.lines.length !== input.lines.length) {
    throw new Error(`subtitles.lines has ${subs.lines.length} entries for ${input.lines.length} lines (must align 1:1)`);
  }
  input.lines.forEach((line, i) => {
    const sub = subs ? subs.lines[i] ?? undefined : undefined;
    if (line.speaker === "bible_verse") {
      if (!input.bible) {
        throw new Error(`line "bible_verse" used but no top-level "bible" object was given`);
      }
      lines.push({ speaker: "verse", text: input.bible.text, durationInSeconds: line.durationInSeconds, subtitle: subs?.verse_text });
      lines.push({ speaker: "reference", text: formatBibleRef(input.bible), subtitle: subs?.verse_label });
    } else {
      if (subs && !sub) throw new Error(`subtitles.lines[${i}] missing for a ${line.speaker} line`);
      lines.push({ speaker: line.speaker, text: requireLineText(line), durationInSeconds: line.durationInSeconds, subtitle: sub });
    }
  });
  const c = input.comment;
  const commentCard = c
    ? { label: c.show_handle && c.handle ? `${c.handle} commented` : `A viewer commented${c.platform ? ` on ${c.platform}` : ""}`, text: c.text }
    : undefined;

  const bg = input.background;
  const background = {
    image: bg?.image ?? resolveBackgroundImage(input.character, input.topic, input.emotion),
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
      track: resolveTrack(input.music?.track, input.music?.type, input.id),
      volume: input.music?.volume,
    },
    styles: mergeStyles(input.styles),
    lines,
    finalLogo: {
      image: input.finalLogo?.image ?? BRAND_ASSETS.followLogo,
      durationSeconds: input.finalLogo?.durationSeconds,
      ctaLabel: input.finalLogo?.ctaLabel ?? "Stay with Jesus",
      secondaryCtaLabel: input.finalLogo?.secondaryCtaLabel ?? "Carry this with you",
    },
    subtitles: subs ? { lang: subs.lang } : undefined,
    commentCard,
  } satisfies z.input<typeof EpisodeSchema>);

  const thumbnail = ThumbnailPropsSchema.parse({ title: input.title, image: background.image });

  return { episode, thumbnail };
}
