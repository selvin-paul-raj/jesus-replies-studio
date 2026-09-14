import React from "react";
import { Composition, Still, staticFile } from "remotion";
import { getAudioDurationInSeconds } from "@remotion/media-utils";
import { EpisodeComposition } from "./Episode";
import { ThumbnailComposition } from "./Thumbnail";
import { EpisodePropsSchema, ThumbnailPropsSchema } from "./schema";
import { buildRevealFrames } from "./timeline";
import defaultEpisode from "./episodes/porch_conversation.json";

export const Root: React.FC = () => {
  return (
    <>
      <Composition
        id="Episode"
        component={EpisodeComposition}
        schema={EpisodePropsSchema}
        fps={30}
        width={1080}
        height={1920}
        durationInFrames={300}
        defaultProps={EpisodePropsSchema.parse(defaultEpisode)}
        calculateMetadata={async ({ props }) => {
          const data = EpisodePropsSchema.parse(props);
          const fps = data.video.fps;
          const { totalFrames } = buildRevealFrames(data.lines, data.timing, fps);
          const endPaddingFrames = Math.round(data.timing.endPaddingSeconds * fps);

          let audioDurationInFrames = 0;
          try {
            const audioSrc = data.audio.track.startsWith("http")
              ? data.audio.track
              : staticFile(data.audio.track);
            const seconds = await getAudioDurationInSeconds(audioSrc);
            audioDurationInFrames = Math.round((seconds ?? 0) * fps);
          } catch (e) {
            console.warn("Could not read audio duration, falling back to video length:", e);
          }

          return {
            durationInFrames: totalFrames + endPaddingFrames,
            fps,
            width: data.video.widthPx,
            height: data.video.heightPx,
            props: { ...data, audioDurationInFrames },
          };
        }}
      />
      <Still
        id="Thumbnail"
        component={ThumbnailComposition}
        schema={ThumbnailPropsSchema}
        width={1080}
        height={1920}
        defaultProps={ThumbnailPropsSchema.parse({
          title: defaultEpisode.title,
          image: defaultEpisode.background.image,
        })}
      />
    </>
  );
};
