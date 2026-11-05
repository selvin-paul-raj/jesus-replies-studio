import React from "react";
import { AbsoluteFill, interpolate, useCurrentFrame } from "remotion";
import { dialogueFontFamily } from "./fonts";

/** DEC-JR-018 "Jesus replies to your comment": the viewer's comment as a card at the top of
 * the frame for the opening exchange (readable on mute, R8). The handle is never drawn unless
 * the label itself carries it, and the label is written by policy (handle hidden by default). */
export const CommentCard: React.FC<{ label: string; text: string; durationInFrames: number }> = ({ label, text, durationInFrames }) => {
  const frame = useCurrentFrame();
  const opacity = interpolate(frame, [0, 8, Math.max(9, durationInFrames - 8), durationInFrames], [0, 1, 1, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  return (
    <AbsoluteFill style={{ alignItems: "center", paddingTop: "7%", opacity }}>
      <div
        style={{
          width: "84%",
          background: "rgba(255,255,255,0.94)",
          borderRadius: 26,
          padding: "22px 30px",
          boxShadow: "0 8px 28px rgba(0,0,0,0.25)",
          fontFamily: dialogueFontFamily,
          color: "#2b2b2b",
        }}
      >
        <div style={{ fontSize: 26, fontWeight: 700, letterSpacing: 1, color: "#7a6a58", marginBottom: 8 }}>{label}</div>
        <div style={{ fontSize: 36, lineHeight: 1.35 }}>{`\u201c${text}\u201d`}</div>
      </div>
    </AbsoluteFill>
  );
};
