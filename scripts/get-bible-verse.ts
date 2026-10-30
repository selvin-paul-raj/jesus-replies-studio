/**
 * ============================================================================
 * DAILY BIBLE VERSE -- picks one entry from the curated scripts/bible.json
 * (365 promises, one for every day of the year, Berean Standard Bible wording,
 * public domain since 2023) by day-of-year,
 * so the same date always yields the same verse (reruns are idempotent).
 * Local data, no network call -- used only by scripts/daily-bible-post.ts.
 * ============================================================================
 */
import bibleData from "./bible.json";
import seriesData from "../content-os/series/global-bible-month-2026.json";

interface VerseEntry {
  id: number;
  reference: string;
  text: string;
}

const VERSES = (bibleData as { promises: VerseEntry[] }).promises;

export interface DailyVerse {
  reference: string;
  version: string;
  text: string;
  /** 0-based index into VERSES for this date -- lets callers locate the
   * matching pre-built image from scripts/build-all-bible-posts.ts's batch
   * (see assetFileName there) without re-deriving the day-of-year math. */
  dayIndex: number;
  /** Set when a dated series (content-os/series) overrides this date. */
  series?: { tag: string; releaseTag: string; day: number; eyebrow: string; hashtags: string };
}

interface SeriesDay { date: string; day: number; reference: string; text: string }
const SERIES = seriesData as { series: string; release_tag: string; eyebrow: string; hashtags: string; days: SeriesDay[] };

/** Dated override (Global Bible Month 2026). Date is the UTC calendar day, matching the poster. */
export function seriesVerseForDate(date: Date): DailyVerse | null {
  const iso = date.toISOString().slice(0, 10);
  const hit = SERIES.days.find((d) => d.date === iso);
  if (!hit) return null;
  return {
    reference: hit.reference,
    version: "BSB",
    text: hit.text.replace(/\s+/g, " ").trim(),
    dayIndex: -1,
    series: {
      tag: SERIES.series,
      releaseTag: SERIES.release_tag,
      day: hit.day,
      eyebrow: SERIES.eyebrow.replace("{day}", String(hit.day)),
      hashtags: SERIES.hashtags,
    },
  };
}

function dayIndexForDate(date: Date): number {
  const startOfYear = Date.UTC(date.getUTCFullYear(), 0, 0);
  const today = Date.UTC(date.getUTCFullYear(), date.getUTCMonth(), date.getUTCDate());
  const dayOfYear = Math.floor((today - startOfYear) / 86_400_000);
  return dayOfYear % VERSES.length;
}

export async function getDailyVerse(date: Date = new Date()): Promise<DailyVerse> {
  const seriesHit = seriesVerseForDate(date);
  if (seriesHit) return seriesHit;
  const dayIndex = dayIndexForDate(date);
  const picked = VERSES[dayIndex];
  return {
    reference: picked.reference,
    version: "BSB",
    text: picked.text.replace(/\s+/g, " ").trim(),
    dayIndex,
  };
}

if (require.main === module) {
  getDailyVerse()
    .then((verse) => console.log(JSON.stringify(verse, null, 2)))
    .catch((error) => {
      console.error("[get-bible-verse] FAILED:", error instanceof Error ? error.message : error);
      process.exit(1);
    });
}
