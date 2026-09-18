import React from "react";
import { AbsoluteFill, Img, staticFile } from "remotion";
import { BibleVerseBlock } from "./BibleVerseBlock";
import { BibleVersePostProps, StylesSchema } from "./schema";
import { calmSerifFontFamily } from "./fonts";

/** Calm sage accent (replaces the old gold) for the eyebrow label, divider,
 * frame border, and ornaments -- SAGE_DARK is used where more contrast is
 * needed (reference/version text), mirroring the old gold/darker-gold split. */
const SAGE = "#7c9070";
const SAGE_DARK = "#5c6f50";

/** Same "verse" look every episode uses (schema.ts StylesSchema.verse), minus
 * the entrance/exit animation (a single-frame Still would otherwise freeze
 * mid-transition) and moved down from VERSE_TOP_PERCENT (14%, tuned for a
 * video with character art starting at ~55%) to sit centered in the gap
 * between the eyebrow label and the bottom logo -- this card has no art
 * filling that space, so the block itself must. Font swapped to the softer,
 * rounder calmSerifFontFamily for this card's relaxed look. */
const VERSE_STYLE = StylesSchema.shape.verse.parse({
  entrance: "none",
  exit: "none",
  topPercent: 38,
  fontFamily: calmSerifFontFamily,
});

/** Small leaf-flourish ornament mirrored into all four corners via CSS
 * transforms -- one CC0 asset (public/branding/corner-flourish.svg, from
 * OpenClipart, recolored to SAGE) instead of four separate images, matching
 * the reference card's corner ornaments. Lower opacity + slightly smaller
 * than the original gold version for a softer, quieter feel. */
const CornerFlourish: React.FC<{ corner: "tl" | "tr" | "bl" | "br" }> = ({ corner }) => {
  const transform =
    corner === "tr" ? "scaleX(-1)" : corner === "bl" ? "scaleY(-1)" : corner === "br" ? "scale(-1, -1)" : undefined;
  const position: React.CSSProperties = {
    position: "absolute",
    top: corner === "tl" || corner === "tr" ? 40 : undefined,
    bottom: corner === "bl" || corner === "br" ? 40 : undefined,
    left: corner === "tl" || corner === "bl" ? 40 : undefined,
    right: corner === "tr" || corner === "br" ? 40 : undefined,
    width: 40,
    height: "auto",
    opacity: 0.55,
    transform,
  };
  return <Img src={staticFile("branding/corner-flourish.svg")} style={position} />;
};

/** A short rule with a small round accent at its center (a circle instead of
 * the old diamond), matching the card's softer, calmer look. */
const AccentDivider: React.FC = () => (
  <div style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: 8, margin: "14px auto 0" }}>
    <div style={{ width: 32, height: 1, background: SAGE, borderRadius: 1 }} />
    <div style={{ width: 6, height: 6, background: SAGE, borderRadius: "50%" }} />
    <div style={{ width: 32, height: 1, background: SAGE, borderRadius: 1 }} />
  </div>
);

/** Standalone 3:4 daily Bible verse card: eyebrow label, verse + reference
 * (via BibleVerseBlock, unmodified), and the bottom logo over a plain
 * brand-colored background with a decorated frame. Registered as its own
 * Still in Root.tsx -- does not touch Episode/Thumbnail. */
export const BibleVersePostComposition: React.FC<BibleVersePostProps> = ({
  verseText,
  referenceText,
  eyebrowLabel,
  backgroundColor,
  logoImage,
}) => {
  return (
    <AbsoluteFill
      style={{ background: `radial-gradient(ellipse at 50% 38%, #fbfdf7 0%, ${backgroundColor} 75%)` }}
    >
      {/* Thin inset frame with rounded corners -- softer, calmer edge than
          the original sharp-cornered rectangle. */}
      <div
        style={{
          position: "absolute",
          inset: 36,
          border: `2px solid ${SAGE}55`,
          borderRadius: 28,
        }}
      />
      <CornerFlourish corner="tl" />
      <CornerFlourish corner="tr" />
      <CornerFlourish corner="bl" />
      <CornerFlourish corner="br" />

      {/* One small floral accent (public/branding/flower-accent.svg, CC0 from
          openclipart, recolored to SAGE) tucked behind the bottom-left of the
          frame -- mirrors the reference card's wheat sprig without competing
          with the verse text, so it stays a single minimal touch. */}
      <Img
        src={staticFile("branding/flower-accent.svg")}
        style={{ position: "absolute", bottom: 30, left: 30, width: 60, height: "auto", opacity: 0.45 }}
      />

      {eyebrowLabel && (
        <div style={{ position: "absolute", top: "8%", left: 0, right: 0, textAlign: "center" }}>
          <p
            style={{
              margin: 0,
              fontFamily: calmSerifFontFamily,
              fontWeight: "bold",
              fontSize: 24,
              letterSpacing: 4,
              textTransform: "uppercase",
              color: SAGE_DARK,
            }}
          >
            {eyebrowLabel}
          </p>
          <AccentDivider />
        </div>
      )}

      <BibleVerseBlock
        verseText={verseText}
        referenceText={referenceText}
        style={VERSE_STYLE}
        durationInFrames={1}
        dividerColor={SAGE}
        citationColor={SAGE_DARK}
      />

      {logoImage && (
        <Img
          src={logoImage.startsWith("http") ? logoImage : staticFile(logoImage)}
          style={{
            position: "absolute",
            bottom: "4%",
            left: "50%",
            transform: "translateX(-50%)",
            width: "52%",
            height: "auto",
            opacity: 0.75,
          }}
        />
      )}
    </AbsoluteFill>
  );
};
