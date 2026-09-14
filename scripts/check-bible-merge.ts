import assert from "node:assert";
import { buildRevealFrames } from "../src/timeline";
import { TimingConfigSchema } from "../src/schema";

/** Self-check for the verse+reference merge in timeline.ts: the two must
 * appear together, exactly once, for their combined duration -- never as
 * two separate frames (that was the bug). Run with: npx tsx scripts/check-bible-merge.ts */
const timing = TimingConfigSchema.parse({ gapSeconds: 0 });
const fps = 30;

const { frames } = buildRevealFrames(
  [
    { speaker: "verse", text: "For where two or three are gathered...", durationInSeconds: 13 },
    { speaker: "reference", text: "Matthew 18:20\nKJV", durationInSeconds: 2 },
  ],
  timing,
  fps
);

assert.strictEqual(frames.length, 1, "verse+reference must collapse into ONE frame, not two");
assert.strictEqual(frames[0].slots.verse, "For where two or three are gathered...");
assert.strictEqual(frames[0].slots.reference, "Matthew 18:20\nKJV");
assert.strictEqual(frames[0].durationInFrames, Math.round(15 * fps), "duration must be the sum (13s+2s)");

// A verse with no following reference must still be shown (not dropped).
const { frames: verseOnly } = buildRevealFrames(
  [{ speaker: "verse", text: "Solo verse", durationInSeconds: 4 }],
  timing,
  fps
);
assert.strictEqual(verseOnly.length, 1);
assert.strictEqual(verseOnly[0].slots.verse, "Solo verse");
assert.strictEqual(verseOnly[0].slots.reference, undefined);

console.log("check-bible-merge: OK");
