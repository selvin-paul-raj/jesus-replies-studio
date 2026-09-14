import React, { useMemo } from "react";
import { AbsoluteFill, Img, staticFile, useVideoConfig } from "remotion";
import { titleFontFamily } from "./fonts";
import { ThumbnailProps } from "./schema";
import { SAFE_CONTENT_BOTTOM_PERCENT, TOP_MARGIN_PERCENT } from "./safeArea";
import { fitFontSizeToBox } from "./textFit";

const TITLE_WIDTH_PERCENT = 84;
const MAX_TITLE_FONT_SIZE = 96;
const MIN_TITLE_FONT_SIZE = 48;
const TITLE_LETTER_SPACING_PX = 2;

/** Static thumbnail card: episode title in a bold white/black-outline style
 * over the background image, matching the "WHY WASH FEET?" reference look.
 * The title lives in the empty sky area above the characters (same
 * character-safe ceiling the video's verse text uses) and auto-shrinks to
 * fit any title length instead of a fixed font size risking overlap. */
export const ThumbnailComposition: React.FC<ThumbnailProps> = ({ title, image }) => {
  const { width, height } = useVideoConfig();
  const src = image.startsWith("http") ? image : staticFile(image);

  const maxWidthPx = (TITLE_WIDTH_PERCENT / 100) * width;
  const maxHeightPx = ((SAFE_CONTENT_BOTTOM_PERCENT - TOP_MARGIN_PERCENT) / 100) * height;

  const fontSize = useMemo(
    () =>
      fitFontSizeToBox({
        text: title,
        fontFamily: titleFontFamily,
        fontWeight: "normal",
        fontStyle: "normal",
        letterSpacingPx: TITLE_LETTER_SPACING_PX,
        lineHeightMultiplier: 1.05,
        authoredFontSize: MAX_TITLE_FONT_SIZE,
        maxWidthPx,
        maxHeightPx,
        minFontSize: MIN_TITLE_FONT_SIZE,
      }),
    [title, maxWidthPx, maxHeightPx]
  );

  return (
    <AbsoluteFill style={{ backgroundColor: "#f5ebd7" }}>
      <Img src={src} style={{ width: "100%", height: "100%", objectFit: "cover" }} />
      <AbsoluteFill
        style={{
          // AbsoluteFill defaults height to "100%"; left unset here, that
          // plus an explicit top+bottom is CSS-over-constrained and the
          // browser silently ignores `bottom`, so this box must set its own
          // height to auto to actually respect both edges.
          height: "auto",
          top: `${TOP_MARGIN_PERCENT}%`,
          bottom: `${100 - SAFE_CONTENT_BOTTOM_PERCENT}%`,
          justifyContent: "center",
          alignItems: "center",
        }}
      >
        <div
          style={{
            width: `${TITLE_WIDTH_PERCENT}%`,
            fontFamily: titleFontFamily,
            fontSize,
            lineHeight: 1.05,
            color: "#ffffff",
            textAlign: "center",
            textTransform: "uppercase",
            letterSpacing: TITLE_LETTER_SPACING_PX,
            WebkitTextStroke: "7px #000000",
            paintOrder: "stroke fill",
            textShadow: "0 10px 24px rgba(0,0,0,0.35)",
          }}
        >
          {title}
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
