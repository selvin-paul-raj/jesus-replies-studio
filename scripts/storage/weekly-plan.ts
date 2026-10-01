import { readdirSync, readFileSync, existsSync } from "node:fs";
import { weekPlan } from "./weekly-batch.js";
import type { Slot } from "./storage-types.js";

/**
 * Diversity-constrained briefs for the 14 slots of a week.
 *
 * This does NOT write dialogue. It reads the Input/ corpus plus anything already
 * authored for this batch, then hands each slot the constraints an episode must satisfy:
 * which topics, verses, emotions and characters are spent, and what the word budget is.
 * Authoring stays with the existing Phase 1 path; this only stops the week turning into
 * 14 variations of one idea.
 */
const EMOTIONS = ["neutral", "happy", "sad", "crying", "angry", "scared", "hopeful"];
const WORDS_TARGET: [number, number] = [141, 166];
const WORDS_MAX = 187;

interface Prior {
  topic?: string; emotion?: string; character?: string; title?: string;
  // Historical Input/ shape, confirmed against all 21 corpus files.
  bible?: { book?: string; chapter?: number | string; verse?: string; version?: string };
  // Shape used by newer generated/ episodes.
  bible_verse?: { reference?: string; book?: string };
}

function readCorpus(dirs: string[]): Prior[] {
  const out: Prior[] = [];
  for (const d of dirs) {
    if (!existsSync(d)) continue;
    for (const f of readdirSync(d).filter((f) => f.endsWith(".json"))) {
      try { out.push(JSON.parse(readFileSync(`${d}/${f}`, "utf8")) as Prior); } catch { /* skip unreadable */ }
    }
  }
  return out;
}

/** Psalm and Psalms are the same book; normalise so diversity counts them once. */
function normaliseBook(raw?: string | null): string | null {
  if (!raw) return null;
  const b = raw.trim().replace(/\s+/g, " ");
  const canon: Record<string, string> = { Psalm: "Psalms", Song: "Song of Songs", Revelations: "Revelation" };
  return canon[b] ?? b;
}

/** Reads the real corpus field first, then the newer reference string. */
function bookOf(p: Prior): string | null {
  if (p.bible?.book) return normaliseBook(p.bible.book);
  if (p.bible_verse?.book) return normaliseBook(p.bible_verse.book);
  const ref = p.bible_verse?.reference;
  return ref ? normaliseBook(ref.match(/^([1-3]?\s?[A-Za-z ]+?)\s*\d/)?.[1] ?? null) : null;
}

export interface SlotBrief {
  date: string; slot: Slot; position: number;
  spent_topics: string[]; spent_books: string[]; recent_hooks: string[];
  emotion_options: string[]; character_suggestion: string;
  words_target: [number, number]; words_max: number;
  rule: string;
}

export function weeklyBriefs(weekStart: string, corpusDirs = ["Input", "generated"]): SlotBrief[] {
  const prior = readCorpus(corpusDirs);
  const spentTopics = new Set(prior.map((p) => p.topic).filter(Boolean) as string[]);
  const spentBooks = new Set(prior.map(bookOf).filter(Boolean) as string[]);
  const hooks = prior.map((p) => p.title).filter(Boolean).slice(-8) as string[];
  const emotionCounts = new Map(EMOTIONS.map((e) => [e, prior.filter((p) => p.emotion === e).length]));
  const chars = prior.map((p) => p.character).filter(Boolean) as string[];
  const boys = chars.filter((c) => c === "boy").length;

  return weekPlan(weekStart).map((s, i) => {
    // Least-used emotions first, so a week spreads across the allowed set.
    const emotions = [...emotionCounts.entries()].sort((a, b) => a[1] - b[1]).map(([e]) => e).slice(0, 4);
    return {
      date: s.date, slot: s.slot, position: i + 1,
      spent_topics: [...spentTopics], spent_books: [...spentBooks], recent_hooks: hooks,
      emotion_options: emotions,
      // Alternate so the week does not skew to one character.
      character_suggestion: (i + (boys > chars.length / 2 ? 1 : 0)) % 2 === 0 ? "girl" : "boy",
      words_target: WORDS_TARGET, words_max: WORDS_MAX,
      rule: `Slot ${i + 1}/14. Topic must not repeat any spent topic or any topic used earlier in this batch. ` +
            `Bible book must not repeat a spent book. Hook must be a question and must not echo recent hooks. ` +
            `Spoken words ${WORDS_TARGET[0]}-${WORDS_TARGET[1]}, never above ${WORDS_MAX}.`,
    };
  });
}

if (process.argv[1]?.endsWith("weekly-plan.ts")) {
  const weekStart = process.argv[2];
  if (!weekStart) { console.error("usage: tsx scripts/storage/weekly-plan.ts YYYY-MM-DD"); process.exit(1); }
  const briefs = weeklyBriefs(weekStart);
  console.log(`[weekly] week_start=${weekStart} slots=${briefs.length}`);
  console.log(`[weekly] spent_topics=${briefs[0].spent_topics.length} spent_books=${briefs[0].spent_books.length}`);
  console.log(JSON.stringify(briefs, null, 2));
}
