/**
 * Renders the dated verse-series Story cards (content-os/series/global-bible-month-2026.json)
 * with the "GLOBAL BIBLE MONTH · DAY N OF 30" eyebrow. Uploaded by build-series-posts.yml to the
 * series release; daily-bible-post.ts posts them on their dates.
 */
import fs from "node:fs";
import path from "node:path";
import { bundle } from "@remotion/bundler";
import { renderStill, selectComposition, openBrowser } from "@remotion/renderer";
import seriesData from "../content-os/series/global-bible-month-2026.json";
import contentOs from "../config/content-os.json";
import { BibleVersePostPropsSchema } from "../src/schema";
import { verseInstagramType, verseCompositionId } from "./lib/verseConfig";

const ROOT_DIR = path.join(__dirname, "..");
const OUT_DIR = path.join(ROOT_DIR, "output", "series");
const ENTRY_POINT = path.join(ROOT_DIR, "src", "index.ts");

async function main(): Promise<void> {
  fs.mkdirSync(OUT_DIR, { recursive: true });
  const compositionId = verseCompositionId(verseInstagramType());
  const bundleLocation = await bundle({ entryPoint: ENTRY_POINT });
  const puppeteerInstance = await openBrowser("chrome");
  try {
    const version = (contentOs as { scripture_version: string }).scripture_version;
    for (const d of seriesData.days as Array<{ day: number; reference: string; text: string; version?: string; posted?: boolean }>) {
      if (d.posted) {
        console.log(`[build-series] day ${d.day} already posted; skipped`);
        continue;
      }
      if (d.version !== version) throw new Error(`series day ${d.day} is ${d.version}, expected ${version}`);
      const inputProps = BibleVersePostPropsSchema.parse({
        verseText: d.text.replace(/\s+/g, " ").trim(),
        referenceText: `${d.reference}\n${version}`,
        eyebrowLabel: seriesData.eyebrow.replace("{day}", String(d.day)),
      });
      const composition = await selectComposition({ serveUrl: bundleLocation, id: compositionId, inputProps, puppeteerInstance });
      const output = path.join(OUT_DIR, `${seriesData.series}-day-${d.day}.png`);
      await renderStill({ composition, serveUrl: bundleLocation, output, inputProps, puppeteerInstance });
      console.log(`[build-series] day ${d.day} ${d.reference}`);
    }
  } finally {
    await puppeteerInstance.close({ silent: false });
  }
}

main().catch((e) => {
  console.error("[build-series] FAILED:", e instanceof Error ? e.message : e);
  process.exit(1);
});
