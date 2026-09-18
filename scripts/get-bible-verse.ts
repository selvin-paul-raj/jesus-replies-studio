/**
 * ============================================================================
 * DAILY BIBLE VERSE -- picks one entry from the curated scripts/bible.json
 * (365 promises, one for every day of the year, NIV wording) by day-of-year,
 * so the same date always yields the same verse (reruns are idempotent).
 * Local data, no network call -- used only by scripts/daily-bible-post.ts.
 * ============================================================================
 */
import bibleData from "./bible.json";

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
}

function pickVerseForDate(date: Date): VerseEntry {
  const startOfYear = Date.UTC(date.getUTCFullYear(), 0, 0);
  const today = Date.UTC(date.getUTCFullYear(), date.getUTCMonth(), date.getUTCDate());
  const dayOfYear = Math.floor((today - startOfYear) / 86_400_000);
  return VERSES[dayOfYear % VERSES.length];
}

export async function getDailyVerse(date: Date = new Date()): Promise<DailyVerse> {
  const picked = pickVerseForDate(date);
  return {
    reference: picked.reference,
    version: process.env.BIBLE_VERSION_LABEL || "NIV",
    text: picked.text.replace(/\s+/g, " ").trim(),
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
