import React from "react";
import { Composition, Still, staticFile } from "remotion";
import { getAudioDurationInSeconds } from "@remotion/media-utils";
import { EpisodeComposition, THUMBNAIL_LEAD_FRAMES } from "./Episode";
import { ThumbnailComposition } from "./Thumbnail";
import { BibleVersePostComposition } from "./BibleVersePost";
import { CarouselCardComposition, CarouselCardPropsSchema } from "./CarouselCard";
import { EpisodePropsSchema, ThumbnailPropsSchema, BibleVersePostPropsSchema } from "./schema";
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
            durationInFrames: totalFrames + endPaddingFrames + THUMBNAIL_LEAD_FRAMES,
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
      <Still
        id="BibleVersePost"
        component={BibleVersePostComposition}
        schema={BibleVersePostPropsSchema}
        width={1080}
        height={1440}
        defaultProps={BibleVersePostPropsSchema.parse({
          verseText: "For I know the thoughts that I think toward you, saith the LORD, thoughts of peace, and not of evil, to give you an expected end.",
          referenceText: "Jeremiah 29:11\nKJV",
        })}
      />
      {/* Same card, full-screen 9:16 for Instagram Stories (config daily_verse.instagram_post_type) */}
      <Still
        id="BibleVerseStory"
        component={BibleVersePostComposition}
        schema={BibleVersePostPropsSchema}
        width={1080}
        height={1920}
        defaultProps={BibleVersePostPropsSchema.parse({
          verseText: "For I know the thoughts that I think toward you, saith the LORD, thoughts of peace, and not of evil, to give you an expected end.",
          referenceText: "Jeremiah 29:11\nKJV",
        })}
      />
      {/* DEC-JR-018 weekly Instagram verse carousel, 4:5 portrait (1080x1350) */}
      <Still
        id="CarouselVerse"
        component={BibleVersePostComposition}
        schema={BibleVersePostPropsSchema}
        width={1080}
        height={1350}
        defaultProps={BibleVersePostPropsSchema.parse({
          verseText: "A soft answer turneth away wrath: but grievous words stir up anger.",
          referenceText: "Proverbs 15:1\nKJV",
        })}
      />
      <Still
        id="CarouselCard"
        component={CarouselCardComposition}
        schema={CarouselCardPropsSchema}
        width={1080}
        height={1350}
        defaultProps={CarouselCardPropsSchema.parse({ title: "5 verses for when family pressure hits" })}
      />
    </>
  );
};
