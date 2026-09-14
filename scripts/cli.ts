import fs from "node:fs";
import path from "node:path";
import { parseArgs } from "node:util";
import { EpisodeInputSchema, buildEpisodeAndThumbnail, EpisodeInput } from "./lib/episodeInput";
import { csvToObjects } from "./lib/csv";
import { renderEpisode } from "./lib/renderEpisode";

/**
 * ============================================================================
 * JR CLI -- render a single episode from a JSON file, or a whole batch from
 * a CSV. Both paths funnel into the same buildEpisodeAndThumbnail/
 * renderEpisode pair, so single vs. batch is purely "how many inputs", not
 * two different pipelines. Usage:
 *   npm run jr -- render <input.json> [--out-dir out]
 *   npm run jr -- batch <input.csv>   [--out-dir out]
 * ============================================================================
 */

const USAGE = `Usage:
  npm run jr -- render <input.json> [--out-dir out]
  npm run jr -- batch <input.csv> [--out-dir out]

JSON input shape:
  { "id": "JR-0002", "title": "...", "character": "boy", "topic": "prayer",
    "bible": { "book": "Matthew", "chapter": 6, "verse": 6, "version": "KJV", "text": "..." },
    "lines": [ { "speaker": "person", "text": "..." }, { "speaker": "bible_verse" }, ... ],
    "styles": { "verse": { "color": "#3b2f2f" } } }

CSV columns (batch):
  id,title,character,topic,bible_book,bible_chapter,bible_verse,bible_version,bible_text,scenes,styles
  "scenes" and "styles" are JSON-encoded cells (same shapes as above's "lines"/"styles").`;

/** A "bible_verse" line has no text of its own in either input format --
 * scenes cells only ever carry {speaker,text?} markers, same rule as the
 * JSON path (see episodeInput.ts). */
function csvRowToEpisodeInput(row: Record<string, string>): EpisodeInput {
  const toNumberOrString = (value: string) => (value.trim() !== "" && !Number.isNaN(Number(value)) ? Number(value) : value);

  const bible = row.bible_book
    ? {
        book: row.bible_book,
        chapter: toNumberOrString(row.bible_chapter),
        verse: toNumberOrString(row.bible_verse),
        version: row.bible_version || undefined,
        text: row.bible_text,
      }
    : undefined;

  return EpisodeInputSchema.parse({
    id: row.id,
    title: row.title,
    character: row.character || undefined,
    topic: row.topic || undefined,
    bible,
    lines: row.scenes ? JSON.parse(row.scenes) : [],
    styles: row.styles ? JSON.parse(row.styles) : undefined,
  });
}

function renderOne(input: EpisodeInput, outDir: string): void {
  const { episode, thumbnail } = buildEpisodeAndThumbnail(input);
  const { videoOut, thumbOut } = renderEpisode(episode, thumbnail, input.id, outDir);
  console.log(`[jr] done: ${videoOut}\n     ${thumbOut}`);
}

function main(): void {
  const [command, ...rest] = process.argv.slice(2);
  const { values, positionals } = parseArgs({
    args: rest,
    options: { "out-dir": { type: "string", default: "out" } },
    allowPositionals: true,
  });
  const outDir = path.resolve(String(values["out-dir"]));
  const target = positionals[0];

  if (!target || (command !== "render" && command !== "batch")) {
    console.error(USAGE);
    process.exit(1);
  }

  if (command === "render") {
    const input = EpisodeInputSchema.parse(JSON.parse(fs.readFileSync(target, "utf-8")));
    renderOne(input, outDir);
    return;
  }

  // batch
  const rows = csvToObjects(fs.readFileSync(target, "utf-8"));
  let succeeded = 0;
  let failed = 0;
  for (const row of rows) {
    try {
      renderOne(csvRowToEpisodeInput(row), outDir);
      succeeded += 1;
    } catch (error) {
      failed += 1;
      console.error(`[jr] FAILED row "${row.id || "?"}": ${(error as Error).message}`);
    }
  }
  console.log(`[jr] batch done: ${succeeded} succeeded, ${failed} failed`);
  if (failed > 0) process.exit(1);
}

main();
