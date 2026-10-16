/** Audio rotation check (DEC-JR-007): run with `npx tsx scripts/check-audio-rotation.ts`.
 * Exits non-zero if a track is missing, the pick is not deterministic, the rotation never
 * uses a track, or a non-licensed track path can still reach a render. */
import fs from "node:fs";
import path from "node:path";
import { BGM_TRACKS, pickBgmTrack, resolveTrack } from "../src/assetResolver";

const PUBLIC = path.join(__dirname, "..", "public");
const fail = (m: string) => { console.error(`[audio-check] FAIL ${m}`); process.exit(1); };

const licences = fs.readFileSync(path.join(PUBLIC, "audio", "LICENSES.md"), "utf8");
for (const t of BGM_TRACKS) {
  if (!fs.existsSync(path.join(PUBLIC, t))) fail(`${t} missing`);
  if (!licences.includes(path.basename(t))) fail(`${t} not listed in LICENSES.md`);
}
const used = new Set<string>();
for (let n = 1; n <= 120; n++) {
  const id = `JR-${String(n).padStart(4, "0")}`;
  const a = pickBgmTrack(id);
  if (a !== pickBgmTrack(id)) fail(`${id} not deterministic`);
  used.add(a);
}
if (used.size !== BGM_TRACKS.length) fail(`rotation used ${used.size}/${BGM_TRACKS.length} tracks`);
if (resolveTrack("audio/removed-third-party.mp3", undefined, "JR-0064") !== pickBgmTrack("JR-0064")) fail("unlicensed track not rejected");
if (resolveTrack("audio/bgm-03.mp3", undefined, "JR-0064") !== "audio/bgm-03.mp3") fail("licensed explicit track not honoured");
console.log(`[audio-check] PASS ${BGM_TRACKS.length} tracks, deterministic, all used across 120 ids, unlicensed paths rejected`);
