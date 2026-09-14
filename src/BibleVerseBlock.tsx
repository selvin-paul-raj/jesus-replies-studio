import React, { useMemo } from "react";
import { useCurrentFrame, useVideoConfig } from "remotion";
import { SpeakerStyle } from "./schema";
import { getAnimatedStyle } from "./animations";
import { SAFE_CONTENT_BOTTOM_PERCENT } from "./safeArea";
import { fitFontSizeToBox } from "./textFit";

/**
 * Renders the verse, a thin gold divider, the reference, and the version as
 * ONE cohesive flow-layout block (verse -> divider -> reference -> version,
 * top to bottom) instead of two independently absolutely-positioned boxes.
 * That's what makes the spacing between them fixed and consistent instead of
 * an unpredictable gap -- and lets one shared entrance/exit animate the
 * whole citation as a single visual unit.
 *
 * The citation's typography (color, letter-spacing, uppercase) is a fixed
 * design choice for this one composition, not schema-driven -- `styles.verse`
 * still governs the verse itself; `styles.reference` (schema.ts) is no
 * longer read for layout, kept only for backward-compatible validation of
 * existing episode props.
 */

const DIVIDER_COLOR = "#a9812f";
const CITATION_COLOR = "#8a6d2e";
const REFERENCE_FONT_SIZE = 26;
const VERSION_FONT_SIZE = 18;
const REFERENCE_LETTER_SPACING = 2;
const VERSION_LETTER_SPACING = 3;
const DIVIDER_MARGIN_TOP = 22;
const DIVIDER_MARGIN_BOTTOM = 22;
const DIVIDER_HEIGHT = 2;
const DIVIDER_WIDTH = 64;
const VERSION_MARGIN_TOP = 6;

// Conservative fixed budget the citation (divider + reference + version)
// reserves out of the verse's growth ceiling, so a long verse still can't
// push the citation (or itself) past the safe line -- see safeArea.ts.
const CITATION_RESERVED_PX =
  DIVIDER_MARGIN_TOP +
  DIVIDER_HEIGHT +
  DIVIDER_MARGIN_BOTTOM +
  REFERENCE_FONT_SIZE * 1.3 +
  VERSION_MARGIN_TOP +
  VERSION_FONT_SIZE * 1.3;

export const BibleVerseBlock: React.FC<{
  verseText: string;
  /** "Book chapter:verse\nVERSION", e.g. "Matthew 18:20\nKJV". Omitted for a
   * verse with no paired reference (see timeline.ts's flushVerse). */
  referenceText?: string;
  style: SpeakerStyle;
  durationInFrames: number;
}> = ({ verseText, referenceText, style, durationInFrames }) => {
  const frame = useCurrentFrame();
  const { fps, width, height } = useVideoConfig();

  const quoted = `“${verseText.replace(/^[“”"]+|[“”"]+$/g, "")}”`;
  const anim = getAnimatedStyle(style, frame, durationInFrames, fps);

  const paddingPx = style.textBackground.enabled ? style.textBackground.paddingPx : 0;
  const maxWidthPx = ((100 - style.leftPercent - style.rightPercent) / 100) * width - paddingPx * 2;
  const maxHeightPercent = SAFE_CONTENT_BOTTOM_PERCENT - style.topPercent;
  const reservedPercent = referenceText ? (CITATION_RESERVED_PX / height) * 100 : 0;
  const maxHeightPx = (Math.max(0, maxHeightPercent - reservedPercent) / 100) * height - paddingPx * 2;

  const fontSize = useMemo(
    () =>
      fitFontSizeToBox({
        text: quoted,
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
      quoted,
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

  const [refLine, versionLine] = (referenceText ?? "").split("\n");

  return (
    <div
      style={{
        position: "absolute",
        top: `${style.topPercent}%`,
        left: `${style.leftPercent}%`,
        right: `${style.rightPercent}%`,
        textAlign: "center",
        opacity: anim.opacity,
        transform: anim.transform,
      }}
    >
      {quoted.split("\n").map((para, i) => (
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

      {referenceText && (
        <>
          <div
            style={{
              width: DIVIDER_WIDTH,
              height: DIVIDER_HEIGHT,
              background: DIVIDER_COLOR,
              margin: `${DIVIDER_MARGIN_TOP}px auto ${DIVIDER_MARGIN_BOTTOM}px`,
            }}
          />
          {refLine && (
            <p
              style={{
                margin: 0,
                fontSize: REFERENCE_FONT_SIZE,
                color: CITATION_COLOR,
                fontFamily: style.fontFamily,
                fontWeight: "bold",
                textTransform: "uppercase",
                letterSpacing: REFERENCE_LETTER_SPACING,
                lineHeight: 1.3,
                textShadow,
              }}
            >
              {refLine}
            </p>
          )}
          {versionLine && (
            <p
              style={{
                margin: `${VERSION_MARGIN_TOP}px 0 0`,
                fontSize: VERSION_FONT_SIZE,
                color: CITATION_COLOR,
                fontFamily: style.fontFamily,
                fontWeight: "bold",
                textTransform: "uppercase",
                letterSpacing: VERSION_LETTER_SPACING,
                lineHeight: 1.3,
                textShadow,
              }}
            >
              {versionLine}
            </p>
          )}
        </>
      )}
    </div>
  );
};
