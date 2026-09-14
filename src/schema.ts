import { z } from "zod";
import { zColor } from "@remotion/zod-types";
import { dialogueFontFamily } from "./fonts";
import { SAFE_LINE_PERCENT, VERSE_TOP_PERCENT } from "./safeArea";

/**
 * ============================================================================
 * JESUS'S REPLIES -- FULL TEMPLATE SCHEMA
 * ============================================================================
 * Every visual and timing property in the video is driven by this schema.
 * Nothing is hardcoded in the React components -- text size, color, position,
 * animation style, background zoom, audio volume/fades, and timing all come
 * from data that matches this shape. Remotion Studio reads this schema and
 * auto-generates on-screen controls (sliders, color pickers, dropdowns) for
 * every field, so you can tune the look live without touching code.
 * ============================================================================
 */

export const SpeakerEnum = z.enum(["person", "jesus", "verse", "reference", "engagement"]);
export type Speaker = z.infer<typeof SpeakerEnum>;

export const EntranceAnimationEnum = z.enum([
  "none",
  "fade",
  "slide-up",
  "slide-down",
  "slide-left",
  "slide-right",
  "scale",
  "typewriter",
]);

export const ExitAnimationEnum = z.enum(["none", "fade", "slide-up", "slide-down"]);

/** Optional pill/box drawn behind the text -- useful over busy photo backgrounds. */
export const TextBackgroundSchema = z.object({
  enabled: z.boolean().default(false),
  color: zColor().default("#00000055"),
  paddingPx: z.number().min(0).default(20),
  borderRadiusPx: z.number().min(0).default(16),
});

export const SpeakerStyleSchema = z.object({
  // Typography
  fontSize: z.number().min(10).max(200).default(52),
  fontFamily: z.string().default(dialogueFontFamily),
  fontWeight: z.enum(["normal", "bold"]).default("bold"),
  fontStyle: z.enum(["normal", "italic"]).default("normal"),
  color: zColor().default("#3b2f2f"),
  lineHeightMultiplier: z.number().min(1).max(3).default(1.3),
  letterSpacingPx: z.number().min(-5).max(20).default(0),

  // Position (all percentages of the frame, matching CSS-style box positioning)
  textAlign: z.enum(["left", "right", "center"]).default("center"),
  /** "top": topPercent is the block's top edge, grows downward as text wraps.
   * "bottom": topPercent is the block's BOTTOM edge (measured from the top),
   * grows upward as text wraps -- use for text sitting just above art that
   * must never be overrun by a longer-than-usual line. */
  anchor: z.enum(["top", "bottom"]).default("top"),
  topPercent: z.number().min(0).max(100).default(30),
  leftPercent: z.number().min(0).max(100).default(7),
  rightPercent: z.number().min(0).max(100).default(7),

  // Readability aid over photo backgrounds
  textShadowEnabled: z.boolean().default(true),
  textBackground: TextBackgroundSchema.default({}),

  // Animation
  entrance: EntranceAnimationEnum.default("fade"),
  exit: ExitAnimationEnum.default("fade"),
  entranceDurationSeconds: z.number().min(0).max(6).default(0.35),
  exitDurationSeconds: z.number().min(0).max(3).default(0.25),
});
export type SpeakerStyle = z.infer<typeof SpeakerStyleSchema>;

export const StylesSchema = z.object({
  // Defaults place all five in one cluster just above the characters (see
  // reference mockups) -- any episode gets this look for free unless it
  // overrides a field. person/jesus/engagement are bottom-anchored so a
  // longer-than-usual line grows up into empty sky instead of down into the
  // characters' heads.
  // textAlign is intentionally omitted everywhere below -- the base schema
  // default is "center" and every speaker uses it, for a clean centered
  // short-form look. Never override person/jesus back to left/right.
  person: SpeakerStyleSchema.default({ anchor: "bottom", topPercent: SAFE_LINE_PERCENT, leftPercent: 4, rightPercent: 56 }),
  jesus: SpeakerStyleSchema.default({ anchor: "bottom", topPercent: SAFE_LINE_PERCENT, leftPercent: 56, rightPercent: 4 }),
  verse: SpeakerStyleSchema.default({
    fontStyle: "italic",
    topPercent: VERSE_TOP_PERCENT,
    entrance: "slide-up",
    entranceDurationSeconds: 0.5,
  }),
  // Bottom-anchored (like person/jesus/engagement) instead of a fixed top
  // offset -- pins to the same safe line so a long verse quote growing down
  // from above can never collide with its own citation.
  reference: SpeakerStyleSchema.default({ fontSize: 30, anchor: "bottom", topPercent: SAFE_LINE_PERCENT, letterSpacingPx: 1 }),
  // The comment/engagement CTA: bold (not italic -- distinct from the
  // reflective tone "reflection" used to have), a notch larger for strong
  // hierarchy, typewriter reveal for attention.
  engagement: SpeakerStyleSchema.default({
    fontSize: 44,
    anchor: "bottom",
    topPercent: SAFE_LINE_PERCENT,
    entrance: "typewriter",
    entranceDurationSeconds: 1.6,
    exitDurationSeconds: 0.4,
  }),
});
export type Styles = z.infer<typeof StylesSchema>;

export const BackgroundConfigSchema = z.object({
  image: z.string(),
  zoomEnabled: z.boolean().default(true),
  zoomFromScale: z.number().min(1).max(2).default(1),
  zoomToScale: z.number().min(1).max(2).default(1.12),
  /** Optional color wash over the whole image -- e.g. a warm cream tint to
   * unify a photo with the brand's illustrated color palette, or a dark
   * tint to boost text contrast. */
  overlayEnabled: z.boolean().default(false),
  overlayColor: zColor().default("#00000000"),
  /** Optional brand logo pinned to the bottom-center of the frame, shown for the whole video. */
  bottomLogo: z.string().optional(),
});
export type BackgroundConfig = z.infer<typeof BackgroundConfigSchema>;

export const FinalLogoConfigSchema = z.object({
  image: z.string(),
  /** How long the closing logo card holds at the end of the video. */
  durationSeconds: z.number().min(0).max(10).default(3),
  /** Primary CTA line under the logo (e.g. "Follow for more Bible conversations"). */
  ctaLabel: z.string().default("Follow for more Bible conversations"),
  /** Optional secondary CTA line (e.g. "Save this for later"), staggered in
   * just after the primary one. Omit to show only the primary CTA. */
  secondaryCtaLabel: z.string().optional(),
});
export type FinalLogoConfig = z.infer<typeof FinalLogoConfigSchema>;

export const AudioConfigSchema = z.object({
  track: z.string(),
  volume: z.number().min(0).max(1).default(1),
  loopIfShorterThanVideo: z.boolean().default(true),
  fadeInSeconds: z.number().min(0).max(5).default(1),
  fadeOutSeconds: z.number().min(0).max(5).default(1.5),
});
export type AudioConfig = z.infer<typeof AudioConfigSchema>;

export const TimingConfigSchema = z.object({
  /** Auto-timing model: duration = max(minLineSeconds, wordCount / wordsPerSecond) */
  wordsPerSecond: z.number().min(0.5).max(10).default(2.3),
  minLineSeconds: z.number().min(0.5).max(10).default(2.2),
  gapSeconds: z.number().min(0).max(3).default(0.35),
  endPaddingSeconds: z.number().min(0).max(10).default(2),
  /** How dialogue is revealed:
   * - "cumulative-pairs": question shows alone, then question+reply together,
   *    then clears for the next exchange (matches the reference format).
   * - "one-at-a-time": every line shown alone, one after another.
   * - "all-at-once": the whole script appears together (good for a still/quote card). */
  revealMode: z.enum(["cumulative-pairs", "one-at-a-time", "all-at-once"]).default("cumulative-pairs"),
});
export type TimingConfig = z.infer<typeof TimingConfigSchema>;

export const VideoConfigSchema = z.object({
  widthPx: z.number().default(1080),
  heightPx: z.number().default(1920),
  fps: z.number().default(30),
});
export type VideoConfigInput = z.infer<typeof VideoConfigSchema>;

export const ScriptLineSchema = z.object({
  speaker: SpeakerEnum,
  text: z.string(),
  /** Optional override, in seconds. If omitted, auto-timed from word count. */
  durationInSeconds: z.number().min(0).optional(),
});
export type ScriptLine = z.infer<typeof ScriptLineSchema>;

/** The full, self-contained definition of one episode/video. Everything the
 * renderer needs -- visuals, timing, audio, and the actual script -- lives
 * in one object matching this schema. This is the "input" you pass in; the
 * rendered .mp4 is the "output". */
export const EpisodeSchema = z.object({
  title: z.string().default("Untitled Episode"),
  video: VideoConfigSchema.default({}),
  background: BackgroundConfigSchema,
  audio: AudioConfigSchema,
  timing: TimingConfigSchema.default({}),
  styles: StylesSchema.default({}),
  lines: z.array(ScriptLineSchema),
  /** Optional closing card: the final logo shown after the dialogue ends. */
  finalLogo: FinalLogoConfigSchema.optional(),
});
export type Episode = z.infer<typeof EpisodeSchema>;

/** Runtime-only extension: the real duration of the audio file, resolved by
 * `calculateMetadata` in Root.tsx (via ffprobe under the hood) and injected
 * as a prop so the player knows how long to loop the background track for. */
export const EpisodePropsSchema = EpisodeSchema.extend({
  audioDurationInFrames: z.number().default(0),
});
export type EpisodeProps = z.infer<typeof EpisodePropsSchema>;

/** Props for the standalone thumbnail still -- the bold-outline title card
 * (e.g. "WHY WASH FEET?") rendered over the episode's background image. */
export const ThumbnailPropsSchema = z.object({
  title: z.string(),
  image: z.string(),
});
export type ThumbnailProps = z.infer<typeof ThumbnailPropsSchema>;
