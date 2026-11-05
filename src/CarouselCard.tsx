import React from "react";
import { AbsoluteFill, Img, staticFile } from "remotion";
import { z } from "zod";
import { calmSerifFontFamily } from "./fonts";

/** DEC-JR-018 weekly verse carousel: cover and closing slides in the same card style as
 * BibleVersePost (sage frame, cream radial background, Domine). Verse slides use
 * BibleVersePost itself at 1080x1350 (Still "CarouselVerse"). */
export const CarouselCardPropsSchema = z.object({
  eyebrow: z.string().default(""),
  title: z.string(),
  body: z.string().default(""),
  footer: z.string().default(""),
  backgroundColor: z.string().default("#eef1e7"),
  logoImage: z.string().default("branding/bottom.png"),
});
export type CarouselCardProps = z.infer<typeof CarouselCardPropsSchema>;

const SAGE = "#7c9070";
const SAGE_DARK = "#5c6f50";

export const CarouselCardComposition: React.FC<CarouselCardProps> = ({ eyebrow, title, body, footer, backgroundColor, logoImage }) => (
  <AbsoluteFill style={{ background: `radial-gradient(ellipse at 50% 38%, #fbfdf7 0%, ${backgroundColor} 75%)` }}>
    <div style={{ position: "absolute", inset: 36, border: `2px solid ${SAGE}55`, borderRadius: 28 }} />
    <Img src={staticFile("branding/flower-accent.svg")} style={{ position: "absolute", bottom: 30, left: 30, width: 60, opacity: 0.45 }} />
    <AbsoluteFill style={{ justifyContent: "center", alignItems: "center", padding: "0 110px", textAlign: "center", fontFamily: calmSerifFontFamily }}>
      {eyebrow && (
        <p style={{ margin: 0, fontWeight: "bold", fontSize: 26, letterSpacing: 4, textTransform: "uppercase", color: SAGE_DARK }}>{eyebrow}</p>
      )}
      <h1 style={{ margin: "34px 0 0", fontSize: 82, lineHeight: 1.15, color: "#2f3a2a", fontWeight: 700 }}>{title}</h1>
      {body && <p style={{ margin: "40px 0 0", fontSize: 38, lineHeight: 1.45, color: "#46523f", whiteSpace: "pre-line" }}>{body}</p>}
      {footer && <p style={{ margin: "46px 0 0", fontSize: 28, letterSpacing: 2, color: SAGE_DARK }}>{footer}</p>}
    </AbsoluteFill>
    {logoImage && (
      <Img src={staticFile(logoImage)} style={{ position: "absolute", bottom: "4%", left: "50%", transform: "translateX(-50%)", width: "40%" }} />
    )}
  </AbsoluteFill>
);
