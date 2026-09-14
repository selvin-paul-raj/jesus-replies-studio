import React from "react";
import { AbsoluteFill, Audio, Loop, Sequence, interpolate, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import { Background } from "./Background";
import { TextBlock } from "./TextBlock";
import { BibleVerseBlock } from "./BibleVerseBlock";
import { EndCard } from "./EndCard";
import { EpisodeProps } from "./schema";
import { buildRevealFrames, toSpeakerSegments } from "./timeline";

export const EpisodeComposition: React.FC<EpisodeProps> = ({
  background,
  audio,
  lines,
  timing,
  styles,
  audioDurationInFrames,
  finalLogo,
}) => {
  const { fps, durationInFrames } = useVideoConfig();
  const currentFrame = useCurrentFrame();
  const { frames } = buildRevealFrames(lines, timing, fps);
  const segments = toSpeakerSegments(frames);
  const audioSrc = audio.track.startsWith("http") ? audio.track : staticFile(audio.track);

  const fadeInFrames = Math.round(audio.fadeInSeconds * fps);
  const fadeOutFrames = Math.round(audio.fadeOutSeconds * fps);

  // Computed once per render frame using the composition's absolute frame
  // (not the frame local to the <Loop>), so fades apply correctly at the
  // very start/end of the whole video regardless of how many times the
  // background track loops in between.
  const fadeIn = interpolate(currentFrame, [0, fadeInFrames], [0, audio.volume], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const fadeOut = interpolate(
    currentFrame,
    [durationInFrames - fadeOutFrames, durationInFrames],
    [audio.volume, 0],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
  );
  const currentVolume = Math.min(fadeIn, fadeOut);

  return (
    <AbsoluteFill>
      <Background config={background} />

      {segments.map((segment, i) => {
        // Reference is folded into its paired verse's BibleVerseBlock below
        // (see timeline.ts -- verse and reference always share the same
        // startFrame/durationInFrames), so it isn't rendered as its own block.
        if (segment.speaker === "reference") return null;

        if (segment.speaker === "verse") {
          const reference = segments.find(
            (s) =>
              s.speaker === "reference" &&
              s.startFrame === segment.startFrame &&
              s.durationInFrames === segment.durationInFrames
          );
          return (
            <Sequence key={i} from={segment.startFrame} durationInFrames={segment.durationInFrames} layout="none">
              <BibleVerseBlock
                verseText={segment.text}
                referenceText={reference?.text}
                style={styles.verse}
                durationInFrames={segment.durationInFrames}
              />
            </Sequence>
          );
        }

        return (
          <Sequence key={i} from={segment.startFrame} durationInFrames={segment.durationInFrames} layout="none">
            <TextBlock
              speaker={segment.speaker}
              text={segment.text}
              style={styles[segment.speaker]}
              durationInFrames={segment.durationInFrames}
            />
          </Sequence>
        );
      })}

      {finalLogo &&
        (() => {
          const logoFrames = Math.min(Math.round(finalLogo.durationSeconds * fps), durationInFrames);
          return logoFrames > 0 ? (
            <Sequence from={durationInFrames - logoFrames} durationInFrames={logoFrames} layout="none">
              <EndCard
                image={finalLogo.image}
                ctaLabel={finalLogo.ctaLabel}
                secondaryCtaLabel={finalLogo.secondaryCtaLabel}
                durationInFrames={logoFrames}
              />
            </Sequence>
          ) : null;
        })()}

      {audio.loopIfShorterThanVideo && audioDurationInFrames > 0 && audioDurationInFrames < durationInFrames ? (
        <Loop durationInFrames={audioDurationInFrames}>
          <Audio src={audioSrc} volume={currentVolume} />
        </Loop>
      ) : (
        <Audio src={audioSrc} volume={currentVolume} />
      )}
    </AbsoluteFill>
  );
};

