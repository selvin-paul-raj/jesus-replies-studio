import assert from "node:assert";
import { buildRevealFrames, toSpeakerSegments } from "../src/timeline";
import { TimingConfigSchema } from "../src/schema";

/** Self-check: when Jesus's reply joins an unchanged person line, the
 * person's text must collapse into ONE continuous segment (no remount --
 * that was the "boy text fades out then back in" bug), while Jesus still
 * gets his own fresh segment starting at the join. Run with:
 * npx tsx scripts/check-speaker-continuity.ts */
const timing = TimingConfigSchema.parse({ gapSeconds: 0 });
const fps = 30;

const { frames } = buildRevealFrames(
  [
    { speaker: "person", text: "Why haven't I succeeded?", durationInSeconds: 5 },
    { speaker: "jesus", text: "Who told you that?", durationInSeconds: 11 },
  ],
  timing,
  fps
);
const segments = toSpeakerSegments(frames);

const personSegments = segments.filter((s) => s.speaker === "person");
const jesusSegments = segments.filter((s) => s.speaker === "jesus");

assert.strictEqual(personSegments.length, 1, "person must stay ONE continuous segment across the join");
assert.strictEqual(personSegments[0].startFrame, 0);
assert.strictEqual(personSegments[0].durationInFrames, Math.round(16 * fps), "person spans the full 5s+11s");

assert.strictEqual(jesusSegments.length, 1);
assert.strictEqual(jesusSegments[0].startFrame, Math.round(5 * fps), "jesus starts fresh at the join point");
assert.strictEqual(jesusSegments[0].durationInFrames, Math.round(11 * fps));

// A genuinely new person line after jesus must NOT merge with the old one.
const { frames: nextExchange } = buildRevealFrames(
  [
    { speaker: "person", text: "Line A", durationInSeconds: 5 },
    { speaker: "jesus", text: "Reply A", durationInSeconds: 5 },
    { speaker: "person", text: "Line B", durationInSeconds: 5 },
  ],
  timing,
  fps
);
const nextSegments = toSpeakerSegments(nextExchange);
const personTexts = nextSegments.filter((s) => s.speaker === "person").map((s) => s.text);
assert.deepStrictEqual(personTexts, ["Line A", "Line B"], "different text must NOT be merged into one segment");

// Regression check: with a NON-ZERO gapSeconds (the new CLI's default,
// since it exposes no `timing` override -- see scripts/lib/episodeInput.ts)
// the person->jesus join must still be gap-free and merge into one
// continuous segment. A real gap here reintroduces the "boy text fades out
// then back in" bug even though the merge logic above is correct.
const gappyTiming = TimingConfigSchema.parse({ gapSeconds: 0.35 });
const { frames: gappyFrames } = buildRevealFrames(
  [
    { speaker: "person", text: "Why haven't I succeeded?", durationInSeconds: 5 },
    { speaker: "jesus", text: "Who told you that?", durationInSeconds: 11 },
  ],
  gappyTiming,
  fps
);
const gappySegments = toSpeakerSegments(gappyFrames);
const gappyPerson = gappySegments.filter((s) => s.speaker === "person");
assert.strictEqual(gappyPerson.length, 1, "person must still merge into ONE segment even with gapSeconds > 0");
assert.strictEqual(gappyPerson[0].durationInFrames, Math.round(16 * fps), "no dead gap between person-alone and the join");

console.log("check-speaker-continuity: OK");
