/** Daily verse settings from config/publishing-rules.json (daily_verse). One place, read by
 * the batch renderer and the daily poster. */
import fs from "node:fs";
import path from "node:path";

export type InstagramVerseType = "story" | "post";

export function verseInstagramType(): InstagramVerseType {
  const rules = JSON.parse(fs.readFileSync(path.join(__dirname, "..", "..", "config", "publishing-rules.json"), "utf-8"));
  const t = rules?.daily_verse?.instagram_post_type ?? "story";
  if (t !== "story" && t !== "post") throw new Error(`daily_verse.instagram_post_type must be "story" or "post", got ${JSON.stringify(t)}`);
  return t;
}

/** Story cards are full-screen 9:16; feed cards keep the 3:4 layout. */
export function verseCompositionId(type: InstagramVerseType): string {
  return type === "story" ? "BibleVerseStory" : "BibleVersePost";
}
