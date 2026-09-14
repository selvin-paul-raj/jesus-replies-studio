import React from "react";
import { AbsoluteFill, Img, interpolate, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import { BackgroundConfig } from "./schema";

export const Background: React.FC<{ config: BackgroundConfig }> = ({ config }) => {
  const frame = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();

  const scale = config.zoomEnabled
    ? interpolate(frame, [0, durationInFrames], [config.zoomFromScale, config.zoomToScale], {
        extrapolateRight: "clamp",
      })
    : 1;

  const src = config.image.startsWith("http") ? config.image : staticFile(config.image);

  return (
    <AbsoluteFill style={{ overflow: "hidden", backgroundColor: "#f5ebd7" }}>
      <Img
        src={src}
        style={{
          width: "100%",
          height: "100%",
          objectFit: "cover",
          transform: `scale(${scale})`,
          transformOrigin: "center center",
        }}
      />
      {config.overlayEnabled && (
        <AbsoluteFill style={{ backgroundColor: config.overlayColor }} />
      )}
      {config.bottomLogo && (
        <Img
  src={config.bottomLogo.startsWith("http") ? config.bottomLogo : staticFile(config.bottomLogo)}
  style={{
    position: "absolute",
    bottom: "4%",
    left: "50%",
    transform: "translateX(-50%)",
    width: "36%",
    height: "auto",
    translate: "0px -50.7px"
  }}
/>
      )}
    </AbsoluteFill>
  );
};
