import React, { useMemo } from "react";
import { useCurrentFrame, useVideoConfig } from "remotion";
import { Speaker, SpeakerStyle } from "./schema";
import { getAnimatedStyle, getTypewriterVisibleChars } from "./animations";
import { SAFE_CONTENT_BOTTOM_PERCENT, TOP_MARGIN_PERCENT } from "./safeArea";
import { fitFontSizeToBox } from "./textFit";

export const TextBlock: React.FC<{
  speaker: Speaker;
  text: string;
  style: SpeakerStyle;
  durationInFrames: number;
}> = ({ speaker, text, style, durationInFrames }) => {
  const frame = useCurrentFrame();
  const { fps, width, height } = useVideoConfig();

  const displayTextRaw =
    speaker === "verse" ? `\u201c${text.replace(/^[\u201c\u201d"]+|[\u201c\u201d"]+$/g, "")}\u201d` : text;

  const anim = getAnimatedStyle(style, frame, durationInFrames, fps);

  let displayText = displayTextRaw;
  if (style.entrance === "typewriter") {
    const visible = getTypewriterVisibleChars(
      displayTextRaw.length,
      frame,
      style.entranceDurationSeconds,
      fps
    );
    displayText = displayTextRaw.slice(0, visible);
  }

  // Structural character-safe box: bottom-anchored blocks only ever grow up
  // (away from the characters), so their ceiling is just the frame's top
  // margin; top-anchored blocks (the verse quote) grow down toward the
  // characters, so they're capped at SAFE_CONTENT_BOTTOM_PERCENT. Fit uses
  // the full (untyped) text so the font size never shifts mid-typewriter.
  const paddingPx = style.textBackground.enabled ? style.textBackground.paddingPx : 0;
  const maxWidthPx = ((100 - style.leftPercent - style.rightPercent) / 100) * width - paddingPx * 2;
  const maxHeightPercent =
    style.anchor === "bottom"
      ? style.topPercent - TOP_MARGIN_PERCENT
      : SAFE_CONTENT_BOTTOM_PERCENT - style.topPercent;
  const maxHeightPx = (Math.max(0, maxHeightPercent) / 100) * height - paddingPx * 2;

  const fontSize = useMemo(
    () =>
      fitFontSizeToBox({
        text: displayTextRaw,
        fontFamily: style.fontFamily,
        fontWeight: style.fontWeight,
        fontStyle: style.fontStyle,
        letterSpacingPx: style.letterSpacingPx,
        lineHeightMultiplier: style.lineHeightMultiplier,
        authoredFontSize: style.fontSize,
        maxWidthPx,
        maxHeightPx,
      }),
    [
      displayTextRaw,
      style.fontFamily,
      style.fontWeight,
      style.fontStyle,
      style.letterSpacingPx,
      style.lineHeightMultiplier,
      style.fontSize,
      maxWidthPx,
      maxHeightPx,
    ]
  );

  const textShadow = style.textShadowEnabled
    ? "0 2px 10px rgba(255,250,240,0.55), 0 1px 3px rgba(255,250,240,0.7)"
    : "none";

  return (
    <div
      style={{
        position: "absolute",
        ...(style.anchor === "bottom"
          ? { bottom: `${100 - style.topPercent}%` }
          : { top: `${style.topPercent}%` }),
        left: `${style.leftPercent}%`,
        right: `${style.rightPercent}%`,
        textAlign: style.textAlign,
        opacity: anim.opacity,
        transform: anim.transform,
        ...(style.textBackground.enabled
          ? {
              backgroundColor: style.textBackground.color,
              padding: style.textBackground.paddingPx,
              borderRadius: style.textBackground.borderRadiusPx,
              display: "inline-block",
            }
          : {}),
      }}
    >
      {displayText.split("\n").map((para, i) => (
        <p
          key={i}
          style={{
            margin: 0,
            fontSize,
            color: style.color,
            fontFamily: style.fontFamily,
            fontWeight: style.fontWeight,
            fontStyle: style.fontStyle,
            lineHeight: style.lineHeightMultiplier,
            letterSpacing: style.letterSpacingPx,
            overflowWrap: "break-word",
            textShadow,
          }}
        >
          {para}
        </p>
      ))}
    </div>
  );
};
