import { ScriptLine, Speaker, TimingConfig } from "./schema";

export function estimateDurationSeconds(text: string, timing: TimingConfig): number {
  const words = Math.max(1, text.trim().split(/\s+/).length);
  return Math.max(timing.minLineSeconds, words / timing.wordsPerSecond);
}

export interface RevealFrame {
  slots: Partial<Record<Speaker, string>>;
  startFrame: number;
  durationInFrames: number;
}

function durationFor(line: ScriptLine, timing: TimingConfig): number {
  return line.durationInSeconds ?? estimateDurationSeconds(line.text, timing);
}

/**
 * Turns a flat script (list of lines) into a list of "reveal frames" -- held
 * visual states of the video -- according to the chosen `revealMode`:
 *
 * - cumulative-pairs: person line(s) show alone, then the next jesus line
 *   joins them on screen together, then it clears for the next exchange.
 *   Verse+reference are grouped together; engagement stands alone.
 * - one-at-a-time: every line gets its own frame, shown by itself.
 * - all-at-once: the entire script is shown together for the whole video
 *   (useful for a single static quote-card style output).
 */
export function buildRevealFrames(
  lines: ScriptLine[],
  timing: TimingConfig,
  fps: number
): { frames: RevealFrame[]; totalFrames: number } {
  // Cursor is tracked in whole frames, not float seconds: rounding each
  // frame's startFrame/durationInFrames independently from a running
  // seconds total can drift by a frame (e.g. two adjacent Math.round calls
  // landing on opposite sides of a .5), so a contiguous person->jesus join
  // would occasionally fail toSpeakerSegments' `===` adjacency check and
  // remount the person's <Sequence> -- replaying its entrance animation
  // right as Jesus's reply appears. Accumulating in integer frames instead
  // makes every push's end exactly equal to the next push's start.
  let cursorFrames = 0;
  const frames: RevealFrame[] = [];
  const gapFrames = Math.round(timing.gapSeconds * fps);

  const push = (slots: Partial<Record<Speaker, string>>, durationSeconds: number, gapAfter = true) => {
    const durationInFrames = Math.round(durationSeconds * fps);
    frames.push({
      slots,
      startFrame: cursorFrames,
      durationInFrames,
    });
    cursorFrames += durationInFrames + (gapAfter ? gapFrames : 0);
  };

  if (timing.revealMode === "all-at-once") {
    const slots: Partial<Record<Speaker, string>> = {};
    let totalDuration = 0;
    for (const line of lines) {
      // last line of each speaker type wins if there are duplicates; typical
      // scripts have at most one of each in this mode.
      slots[line.speaker] = slots[line.speaker] ? `${slots[line.speaker]}\n${line.text}` : line.text;
      totalDuration += durationFor(line, timing);
    }
    push(slots, Math.max(totalDuration, timing.minLineSeconds));
  } else if (timing.revealMode === "one-at-a-time") {
    for (const line of lines) {
      push({ [line.speaker]: line.text }, durationFor(line, timing));
    }
  } else {
    // cumulative-pairs (default)
    let lastPersonText = "";
    let pendingVerse: string | null = null;
    let pendingVerseDuration = 0;

    // Unlike person -> jesus (which deliberately reveals in two stages), the
    // verse and its reference must read as ONE cohesive Bible block: the
    // verse is buffered here and only pushed once its reference arrives,
    // together, for their combined duration -- so the two never appear as
    // separate scenes and the verse is never shown without its reference.
    const flushVerse = () => {
      if (pendingVerse !== null) {
        push({ verse: pendingVerse }, pendingVerseDuration);
        pendingVerse = null;
        pendingVerseDuration = 0;
      }
    };

    for (let i = 0; i < lines.length; i++) {
      const line = lines[i];
      const dur = durationFor(line, timing);

      if (line.speaker === "person") {
        flushVerse();
        // Replace, don't accumulate: back-to-back person lines (asked before
        // Jesus replies) should each stand alone on screen, not stack into a
        // growing paragraph of every question asked so far.
        lastPersonText = line.text;
        // No gap when a jesus reply immediately joins this same exchange --
        // `timing.gapSeconds` is breathing room BETWEEN exchanges, not
        // inside one. A gap here would put real dead air between "person
        // alone" and "person+jesus", which also breaks toSpeakerSegments'
        // contiguity check and reintroduces the remount flicker it exists
        // to prevent -- independent of whatever gapSeconds the episode uses.
        const joinsJesus = lines[i + 1]?.speaker === "jesus";
        push({ person: lastPersonText }, dur, !joinsJesus);
      } else if (line.speaker === "jesus") {
        flushVerse();
        push({ person: lastPersonText, jesus: line.text }, dur);
        lastPersonText = "";
      } else if (line.speaker === "verse") {
        flushVerse(); // defensive: handles back-to-back verse lines
        pendingVerse = line.text;
        pendingVerseDuration = dur;
      } else if (line.speaker === "reference") {
        push({ verse: pendingVerse ?? "", reference: line.text }, pendingVerseDuration + dur);
        pendingVerse = null;
        pendingVerseDuration = 0;
      } else if (line.speaker === "engagement") {
        flushVerse();
        lastPersonText = "";
        push({ engagement: line.text }, dur);
      }
    }
    flushVerse(); // a verse with no following reference still gets shown
  }

  return { frames, totalFrames: cursorFrames };
}

export interface SpeakerSegment {
  speaker: Speaker;
  text: string;
  startFrame: number;
  durationInFrames: number;
}

/**
 * Collapses `frames` (which groups speakers into simultaneous on-screen
 * "states") into one continuous segment per speaker, merging a speaker's
 * entry across adjacent frames when its text is unchanged and there's no
 * gap between them. Without this, cumulative-pairs' person-alone frame and
 * its immediately-following person+jesus frame are two separate <Sequence>s
 * in Episode.tsx, so the person's (unchanged) text remounts -- fading out
 * and back in -- the instant Jesus's reply joins. Rendering one <Sequence>
 * per segment instead means the person's text mounts once, holds steady
 * through the join, and only Jesus's genuinely-new text gets a fresh
 * entrance.
 */
export function toSpeakerSegments(frames: RevealFrame[]): SpeakerSegment[] {
  const segments: SpeakerSegment[] = [];
  const open: Partial<Record<Speaker, SpeakerSegment>> = {};

  for (const frame of frames) {
    const frameEnd = frame.startFrame + frame.durationInFrames;
    for (const speaker of Object.keys(frame.slots) as Speaker[]) {
      const text = frame.slots[speaker] as string;
      const current = open[speaker];
      if (current && current.text === text && current.startFrame + current.durationInFrames === frame.startFrame) {
        current.durationInFrames = frameEnd - current.startFrame; // extend, don't remount
      } else {
        const segment: SpeakerSegment = { speaker, text, startFrame: frame.startFrame, durationInFrames: frame.durationInFrames };
        segments.push(segment);
        open[speaker] = segment;
      }
    }
    // A speaker absent from this frame has been cleared from the screen;
    // its next appearance (even with the same text) must start fresh.
    for (const speaker of Object.keys(open) as Speaker[]) {
      if (!(speaker in frame.slots)) delete open[speaker];
    }
  }

  return segments;
}
