/**
 * ============================================================================
 * BUILD ALL BIBLE POSTS -- one-off batch render of all 365 verse cards from
 * bible.json, bundling the Remotion project ONCE and reusing that bundle for
 * every render (unlike the daily job's old approach of shelling out to
 * `remotion still` per run, which rebundles from scratch and redownloads the
 * ~90MB headless Chrome shell every single day for output that only differs
 * by text). Run manually whenever bible.json changes -- see the
 * "Build Bible Posts" workflow (.github/workflows/build-bible-posts.yml) or
 * run locally:
 *   npx tsx scripts/build-all-bible-posts.ts
 * Then upload output/bible_verse_batch/ as GitHub Release assets (the
 * workflow does this automatically); scripts/daily-bible-post.ts references
 * those asset URLs directly instead of rendering.
 * ============================================================================
 */
import fs from "node:fs";
import path from "node:path";
import { bundle } from "@remotion/bundler";
import { renderStill, selectComposition, openBrowser } from "@remotion/renderer";
import bibleData from "./bible.json";
import { BibleVersePostPropsSchema } from "../src/schema";

const ROOT_DIR = path.join(__dirname, "..");
const OUT_DIR = path.join(ROOT_DIR, "output", "bible_verse_batch");
const ENTRY_POINT = path.join(ROOT_DIR, "src", "index.ts");

interface VerseEntry {
  id: number;
  reference: string;
  text: string;
}

const VERSES = (bibleData as { promises: VerseEntry[] }).promises;

/** GitHub Release tag holding all 365 pre-built images as assets -- both
 * this script (uploader) and scripts/daily-bible-post.ts (consumer) need to
 * agree on it. Bump the suffix if bible.json's verses are ever reordered in
 * a way that changes which index maps to which verse. */
export const BATCH_RELEASE_TAG = "bible-posts-v1";

/** File name for a given 0-based index into VERSES -- get-bible-verse.ts's
 * dayIndex (dayOfYear % VERSES.length) is exactly that index, so
 * daily-bible-post.ts can call this directly with verse.dayIndex. */
export function assetFileName(index: number): string {
  return `bible-post-day-${index + 1}.png`;
}

async function main(): Promise<void> {
  fs.mkdirSync(OUT_DIR, { recursive: true });

  console.log(`[build-all] Bundling once for ${VERSES.length} verses...`);
  const bundleLocation = await bundle({ entryPoint: ENTRY_POINT });

  // One browser instance reused across all 365 renders -- selectComposition
  // must be called PER VERSE (with that verse's inputProps) since it's what
  // resolves `composition.props`, the actual props renderStill uses; calling
  // it once outside the loop would bake in only the Still's default props.
  const puppeteerInstance = await openBrowser("chrome");
  try {
    for (let i = 0; i < VERSES.length; i++) {
      const verse = VERSES[i];
      const outputPath = path.join(OUT_DIR, assetFileName(i));
      const inputProps = BibleVersePostPropsSchema.parse({
        verseText: verse.text.replace(/\s+/g, " ").trim(),
        referenceText: `${verse.reference}\n${process.env.BIBLE_VERSION_LABEL || "NIV"}`,
      });

      console.log(`[build-all] (${i + 1}/${VERSES.length}) ${verse.reference}...`);
      const composition = await selectComposition({
        serveUrl: bundleLocation,
        id: "BibleVersePost",
        inputProps,
        puppeteerInstance,
      });
      await renderStill({ composition, serveUrl: bundleLocation, output: outputPath, inputProps, puppeteerInstance });
    }
  } finally {
    await puppeteerInstance.close({ silent: false });
  }

  console.log(`[build-all] Done. ${VERSES.length} images written to ${OUT_DIR}`);
}

if (require.main === module) {
  main().catch((error) => {
    console.error("[build-all] FAILED:", error instanceof Error ? error.message : error);
    process.exit(1);
  });
}
