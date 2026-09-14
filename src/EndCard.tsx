import React from "react";
import { AbsoluteFill, Img, interpolate, spring, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import { dialogueFontFamily } from "./fonts";

export type EndCardProps = {
  image: string;
  ctaLabel: string;
  secondaryCtaLabel?: string;
  durationInFrames: number;
};

/**
 * Professional closing card, reusable as-is for every future episode --
 * only `image` / `ctaLabel` / `secondaryCtaLabel` ever change.
 *
 * Beat sheet: soft fade in from the previous scene -> the brand logo
 * settles in with a gentle spring (plus a very slight continuous float once
 * settled) -> the CTA line(s) stagger in underneath with a clean fade +
 * slide. No emojis, no particles, no zoom punches -- just a calm, branded
 * finish that reads well on a phone screen.
 */
export const EndCard: React.FC<EndCardProps> = ({ image, ctaLabel, secondaryCtaLabel, durationInFrames }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const src = image.startsWith("http") ? image : staticFile(image);

  const cardFadeFrames = Math.min(Math.round(0.4 * fps), durationInFrames);
  const logoDelay = Math.round(0.15 * fps);
  const ctaDelay = logoDelay + Math.round(0.55 * fps);
  const secondaryDelay = ctaDelay + Math.round(0.3 * fps);

  const cardOpacity = interpolate(frame, [0, cardFadeFrames], [0, 1], { extrapolateRight: "clamp" });

  const logoSpring = spring({ frame: frame - logoDelay, fps, config: { damping: 14 } });
  const logoIn = Math.min(1, logoSpring);
  const logoScale = 0.85 + logoIn * 0.15;
  // Very subtle continuous float once the entrance has settled -- a few px,
  // slow, so it reads as "alive" without ever distracting.
  const float = logoSpring >= 1 ? Math.sin(frame / fps) * 4 : 0;

  const ctaSpring = Math.min(1, spring({ frame: frame - ctaDelay, fps, config: { damping: 16 } }));
  const secondarySpring = Math.min(1, spring({ frame: frame - secondaryDelay, fps, config: { damping: 16 } }));

  return (
    <AbsoluteFill
      style={{
        backgroundColor: "#f5ebd7",
        justifyContent: "center",
        alignItems: "center",
        flexDirection: "column",
        gap: 36,
        opacity: cardOpacity,
      }}
    >
      <Img
        src={src}
        style={{
          width: "56%",
          height: "auto",
          opacity: logoIn,
          transform: `scale(${logoScale}) translateY(${float}px)`,
        }}
      />
      <div
        style={{
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          gap: 14,
          opacity: ctaSpring,
          transform: `translateY(${(1 - ctaSpring) * 24}px)`,
        }}
      >
        <div
          style={{
            padding: "16px 40px",
            borderRadius: 999,
            fontSize: 30,
            fontWeight: 700,
            fontFamily: dialogueFontFamily,
            border: "2px solid #3b2f2f",
            color: "#3b2f2f",
            textAlign: "center",
          }}
        >
          {ctaLabel}
        </div>
        {secondaryCtaLabel && (
          <div
            style={{
              opacity: secondarySpring,
              transform: `translateY(${(1 - secondarySpring) * 16}px)`,
              fontSize: 24,
              fontWeight: 600,
              fontFamily: dialogueFontFamily,
              color: "#6b4a1e",
              textAlign: "center",
            }}
          >
            {secondaryCtaLabel}
          </div>
        )}
      </div>
    </AbsoluteFill>
  );
};
