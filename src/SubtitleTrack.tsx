import React from "react";
import { AbsoluteFill, Sequence, interpolate, useCurrentFrame, useVideoConfig } from "remotion";
import { ScriptLine } from "./schema";
import { RevealFrame } from "./timeline";
import { tamilFontFamily, devanagariFontFamily } from "./fonts";

/** DEC-JR-018: burned-in Tamil/Hindi captions. One cue per reveal frame, showing the
 * translation of what is NEW on screen in that frame (person alone -> person; person+jesus ->
 * jesus; verse+reference -> the verse in the bundled IRV text + its label; engagement).
 * Story lines are human translations; the verse cue is the bundled IRV text, verbatim. */
const PRIORITY = ["engagement", "verse", "jesus", "person"] as const;

export function subtitleCues(frames: RevealFrame[], lines: ScriptLine[]) {
  const byText = new Map<string, Map<string, string>>();
  for (const l of lines) {
    if (!l.subtitle) continue;
    if (!byText.has(l.speaker)) byText.set(l.speaker, new Map());
    byText.get(l.speaker)!.set(l.text, l.subtitle);
  }
  const cues: { text: string; startFrame: number; durationInFrames: number; verse: boolean }[] = [];
  for (const f of frames) {
    for (const sp of PRIORITY) {
      const en = f.slots[sp];
      if (en === undefined) continue;
      let sub = byText.get(sp)?.get(en);
      if (sp === "verse" && f.slots.reference !== undefined) {
        const ref = byText.get("reference")?.get(f.slots.reference);
        sub = [sub, ref].filter(Boolean).join("\n");
      }
      if (sub) cues.push({ text: sub, startFrame: f.startFrame, durationInFrames: f.durationInFrames, verse: sp === "verse" });
      break;
    }
  }
  return cues;
}

const Cue: React.FC<{ text: string; lang: "ta" | "hi"; durationInFrames: number; verse: boolean }> = ({ text, lang, durationInFrames, verse }) => {
  const frame = useCurrentFrame();
  const { height } = useVideoConfig();
  const opacity = interpolate(frame, [0, 6, Math.max(7, durationInFrames - 6), durationInFrames], [0, 1, 1, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const long = text.length > 140;
  return (
    // Band between (the verse cue sits a little lower, clear of the KJV reference that pins at 42%)
    // Band between the dialogue safe line (42%) and the characters (55.4%): never over the art or the bottom logo.
    <AbsoluteFill style={{ justifyContent: "flex-start", alignItems: "center", paddingTop: Math.round(height * (verse ? 0.445 : 0.432)), opacity }}>
      <div
        style={{
          maxWidth: "88%",
          background: "rgba(0,0,0,0.7)",
          borderRadius: 18,
          padding: "12px 24px",
          color: "#fff",
          fontFamily: lang === "ta" ? tamilFontFamily : devanagariFontFamily,
          fontWeight: 600,
          fontSize: long || verse ? 28 : lang === "ta" ? 32 : 36,
          lineHeight: 1.45,
          textAlign: "center",
          whiteSpace: "pre-line",
        }}
      >
        {text}
      </div>
    </AbsoluteFill>
  );
};

export const SubtitleTrack: React.FC<{ frames: RevealFrame[]; lines: ScriptLine[]; lang: "ta" | "hi"; offset: number }> = ({
  frames,
  lines,
  lang,
  offset,
}) => (
  <>
    {subtitleCues(frames, lines).map((c, i) => (
      <Sequence key={`sub-${i}`} from={c.startFrame + offset} durationInFrames={c.durationInFrames} layout="none">
        <Cue text={c.text} lang={lang} durationInFrames={c.durationInFrames} verse={c.verse} />
      </Sequence>
    ))}
  </>
);
