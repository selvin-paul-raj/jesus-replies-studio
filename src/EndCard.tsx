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
 * Beat sheet: soft fade in from the previous scene -> the brand logo settles
 * in with a gentle spring (plus a slow shimmer glow and slight continuous
 * float once settled) -> the CTA line(s) stagger in underneath with a clean
 * fade + slide -> each pill gets its own "tap" beat afterward (Follow's "+"
 * pulses into a checkmark and fills solid; Save's bookmark outline fills
 * solid with a bounce), simulating the viewer actually acting on it.
 */
export const EndCard: React.FC<EndCardProps> = ({ image, ctaLabel, secondaryCtaLabel, durationInFrames }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const src = image.startsWith("http") ? image : staticFile(image);

  const cardFadeFrames = Math.min(Math.round(0.4 * fps), durationInFrames);
  const logoDelay = Math.round(0.15 * fps);
  const ctaDelay = logoDelay + Math.round(0.55 * fps);
  const secondaryDelay = ctaDelay + Math.round(0.3 * fps);
  // The "tap" beats land after each pill has finished settling in -- a
  // distinct moment afterward, not part of the entrance itself.
  const followTapDelay = ctaDelay + Math.round(0.9 * fps);
  const saveTapDelay = secondaryDelay + Math.round(0.7 * fps);

  const cardOpacity = interpolate(frame, [0, cardFadeFrames], [0, 1], { extrapolateRight: "clamp" });

  const logoSpring = spring({ frame: frame - logoDelay, fps, config: { damping: 14 } });
  const logoIn = Math.min(1, logoSpring);
  const logoScale = 0.85 + logoIn * 0.15;
  // Very subtle continuous float once the entrance has settled -- a few px,
  // slow, so it reads as "alive" without ever distracting.
  const float = logoSpring >= 1 ? Math.sin(frame / fps) * 4 : 0;
  // Soft glow that breathes behind the logo once settled -- separate sine
  // period from the float so the two don't lock into a repetitive combo.
  const glowOpacity = logoSpring >= 1 ? 0.3 + Math.sin(frame / fps / 1.4) * 0.18 : 0;

  const ctaSpring = Math.min(1, spring({ frame: frame - ctaDelay, fps, config: { damping: 16 } }));
  const secondarySpring = Math.min(1, spring({ frame: frame - secondaryDelay, fps, config: { damping: 16 } }));

  // Follow pill tap: "+" morphs into a checkmark, the pill fills from
  // outline to solid, and the whole pill does a quick confirm-pulse.
  const followTap = spring({ frame: frame - followTapDelay, fps, config: { damping: 10, mass: 0.5 } });
  const followFilled = Math.min(1, followTap);
  const followPulse = 1 + Math.sin(Math.min(1, followTap) * Math.PI) * 0.12;

  // Save pill tap: bookmark outline fills solid with a small bounce.
  const saveTap = spring({ frame: frame - saveTapDelay, fps, config: { damping: 9, mass: 0.5 } });
  const saveFilled = Math.min(1, saveTap);
  const saveBounce = 1 + Math.sin(Math.min(1, saveTap) * Math.PI) * 0.25;

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
      <div style={{ position: "relative", width: "56%", display: "flex", justifyContent: "center" }}>
        <div
          style={{
            position: "absolute",
            width: "80%",
            height: "80%",
            borderRadius: "50%",
            background: "radial-gradient(circle, rgba(255,214,120,0.6) 0%, rgba(255,214,120,0) 70%)",
            opacity: glowOpacity,
          }}
        />
        <Img
          src={src}
          style={{
            position: "relative",
            width: "100%",
            height: "auto",
            opacity: logoIn,
            transform: `scale(${logoScale}) translateY(${float}px)`,
          }}
        />
      </div>
      <div
        style={{
          display: "flex",
          flexDirection: "row",
          alignItems: "center",
          justifyContent: "center",
          flexWrap: "wrap",
          gap: 20,
          opacity: ctaSpring,
          transform: `translateY(${(1 - ctaSpring) * 24}px)`,
        }}
      >
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 12,
            padding: "16px 40px",
            borderRadius: 999,
            fontSize: 30,
            fontWeight: 700,
            fontFamily: dialogueFontFamily,
            border: "2px solid #3b2f2f",
            backgroundColor: `rgba(59,47,47,${followFilled})`,
            color: followFilled > 0.5 ? "#f5ebd7" : "#3b2f2f",
            textAlign: "center",
            transform: `scale(${followPulse})`,
          }}
        >
          <span
            style={{
              position: "relative",
              width: 22,
              height: 22,
              display: "inline-flex",
              alignItems: "center",
              justifyContent: "center",
              fontSize: 22,
              lineHeight: 1,
            }}
          >
            <span style={{ position: "absolute", opacity: 1 - followFilled }}>+</span>
            <span style={{ position: "absolute", opacity: followFilled }}>{"✓"}</span>
          </span>
          {ctaLabel}
        </div>
        {secondaryCtaLabel && (
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: 10,
              opacity: secondarySpring,
              transform: `translateY(${(1 - secondarySpring) * 16}px)`,
              fontSize: 24,
              fontWeight: 600,
              fontFamily: dialogueFontFamily,
              color: "#6b4a1e",
              textAlign: "center",
            }}
          >
            <span
              style={{
                width: 14,
                height: 18,
                display: "inline-block",
                flexShrink: 0,
                clipPath: "polygon(0 0, 100% 0, 100% 100%, 50% 75%, 0 100%)",
                border: "2px solid #6b4a1e",
                backgroundColor: saveFilled > 0 ? "#6b4a1e" : "transparent",
                transform: `scale(${saveBounce})`,
                transformOrigin: "top center",
              }}
            />
            {secondaryCtaLabel}
          </div>
        )}
      </div>
    </AbsoluteFill>
  );
};
