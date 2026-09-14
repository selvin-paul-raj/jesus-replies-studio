import assert from "node:assert";
import { parseCsv, csvToObjects } from "./lib/csv";
import { EpisodeInputSchema, buildEpisodeAndThumbnail } from "./lib/episodeInput";

/** Self-check for the new CLI's two non-trivial pieces: the CSV parser
 * (quoted commas/embedded JSON) and the episode-input builder (bible_verse
 * marker expansion + safe style-override merging). Run with:
 * npx tsx scripts/check-cli-input.ts */

// --- CSV: quoted commas and embedded JSON must survive intact ---
const csv = [
  "id,title,scenes",
  'JR-9001,"Why, Lord?","[{""speaker"":""person"",""text"":""Why, Lord?""}]"',
].join("\n");
const rows = csvToObjects(csv);
assert.strictEqual(rows.length, 1);
assert.strictEqual(rows[0].title, "Why, Lord?");
const parsedScenes = JSON.parse(rows[0].scenes);
assert.strictEqual(parsedScenes[0].text, "Why, Lord?");

// A lone header with no data rows must not throw / must return [].
assert.deepStrictEqual(csvToObjects("id,title"), []);
assert.deepStrictEqual(parseCsv(""), []);

// --- episodeInput: bible_verse marker expands into verse+reference, and a
// partial style override doesn't clobber the curated person/jesus layout ---
const input = EpisodeInputSchema.parse({
  id: "JR-9001",
  title: "Why, Lord?",
  character: "boy",
  topic: "faith",
  bible: { book: "Matthew", chapter: 18, verse: 20, version: "KJV", text: "For where two or three..." },
  lines: [
    { speaker: "person", text: "Why, Lord?" },
    { speaker: "jesus", text: "I am with you." },
    { speaker: "bible_verse" },
    { speaker: "engagement", text: "Share your thoughts." },
  ],
  styles: { verse: { color: "#123456" } },
});

const { episode } = buildEpisodeAndThumbnail(input);

assert.strictEqual(episode.lines.length, 5, "bible_verse must expand into verse+reference (2 lines)");
assert.strictEqual(episode.lines[2].speaker, "verse");
assert.strictEqual(episode.lines[2].text, "For where two or three...");
assert.strictEqual(episode.lines[3].speaker, "reference");
assert.strictEqual(episode.lines[3].text, "Matthew 18:20\nKJV");

// The override applied...
assert.strictEqual(episode.styles.verse.color, "#123456");
// ...but curated positions the override didn't touch survived (the bug this
// merge exists to prevent: a partial override silently resetting anchor/position).
assert.strictEqual(episode.styles.person.leftPercent, 4);
assert.strictEqual(episode.styles.person.anchor, "bottom");
assert.strictEqual(episode.styles.verse.entrance, "slide-up");

console.log("check-cli-input: OK");
