import { interpolate, spring } from "remotion";
import { SpeakerStyle } from "./schema";

export interface AnimatedStyle {
  opacity: number;
  transform: string;
  /** For "typewriter" entrance: how many characters of the text to show right now. */
  visibleCharCount: number | null;
}

/**
 * Computes the current opacity/transform/reveal-progress for one text block,
 * given how many frames have elapsed since it appeared (localFrame) and how
 * many frames it will stay on screen (durationInFrames). Entrance animation
 * plays over the first `entranceDurationSeconds`, exit animation plays over
 * the last `exitDurationSeconds`; the rest of the duration is a static hold.
 */
export function getAnimatedStyle(
  style: SpeakerStyle,
  localFrame: number,
  durationInFrames: number,
  fps: number
): AnimatedStyle {
  const entranceFrames = Math.max(1, Math.round(style.entranceDurationSeconds * fps));
  const exitFrames = Math.max(1, Math.round(style.exitDurationSeconds * fps));
  const exitStartFrame = Math.max(entranceFrames, durationInFrames - exitFrames);

  // Progress through entrance: 0 -> 1. Springs read as more alive than linear
  // easing -- a light natural bounce for "scale", a smooth critically-damped
  // settle (no overshoot) for everything else.
  const entranceConfig = style.entrance === "scale" ? { damping: 12 } : { damping: 200 };
  const entranceProgress = spring({
    frame: localFrame,
    fps,
    config: entranceConfig,
    durationInFrames: entranceFrames,
  });

  // Progress through exit: 0 -> 1 (0 = not exiting yet, 1 = fully exited)
  const exitProgress =
    style.exit === "none"
      ? 0
      : spring({
          frame: localFrame,
          fps,
          delay: exitStartFrame,
          config: { damping: 200 },
          durationInFrames: exitFrames,
        });

  let opacity = 1;
  let translateX = 0;
  let translateY = 0;
  let scale = 1;
  let visibleCharCount: number | null = null;

  // --- Entrance ---
  switch (style.entrance) {
    case "fade":
      opacity = entranceProgress;
      break;
    case "slide-up":
      opacity = entranceProgress;
      translateY = (1 - entranceProgress) * 40;
      break;
    case "slide-down":
      opacity = entranceProgress;
      translateY = -(1 - entranceProgress) * 40;
      break;
    case "slide-left":
      opacity = entranceProgress;
      translateX = (1 - entranceProgress) * 60;
      break;
    case "slide-right":
      opacity = entranceProgress;
      translateX = -(1 - entranceProgress) * 60;
      break;
    case "scale":
      opacity = entranceProgress;
      scale = 0.85 + entranceProgress * 0.15;
      break;
    case "typewriter":
      opacity = 1;
      visibleCharCount = null; // computed by caller using its own progress (see below)
      break;
    case "none":
    default:
      opacity = 1;
      break;
  }

  // --- Exit (multiplies on top of entrance opacity, and can add its own motion) ---
  if (style.exit === "fade") {
    opacity *= 1 - exitProgress;
  } else if (style.exit === "slide-up") {
    opacity *= 1 - exitProgress;
    translateY -= exitProgress * 40;
  } else if (style.exit === "slide-down") {
    opacity *= 1 - exitProgress;
    translateY += exitProgress * 40;
  }

  return {
    opacity,
    transform: `translate(${translateX}px, ${translateY}px) scale(${scale})`,
    visibleCharCount,
  };
}

/** Typewriter is handled separately since it reveals characters rather than
 * animating opacity/transform of the whole block. Returns how many
 * characters of `fullLength` should currently be visible. */
export function getTypewriterVisibleChars(
  fullLength: number,
  localFrame: number,
  entranceDurationSeconds: number,
  fps: number
): number {
  const entranceFrames = Math.max(1, Math.round(entranceDurationSeconds * fps));
  const progress = interpolate(localFrame, [0, entranceFrames], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  return Math.round(progress * fullLength);
}
