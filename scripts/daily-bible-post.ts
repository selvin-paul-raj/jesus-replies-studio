/**
 * ============================================================================
 * DAILY BIBLE POST -- orchestrates the daily half of the Bible Verse Post
 * Tool pipeline: get today's verse -> look up its pre-built image (from the
 * "bible-posts-v3-kjv" GitHub Release, built once by
 * scripts/build-all-bible-posts.ts) -> post to Instagram via Buffer ->
 * record today's date so reruns are a no-op.
 *
 * Deliberately does NOT render anything -- the old version shelled out to
 * `remotion still` and re-uploaded a fresh GitHub Release asset every single
 * day, which rebundled the whole project and redownloaded a ~90MB headless
 * Chrome shell daily just to change some text. Rendering happens once (or
 * whenever bible.json changes) via the separate batch script/workflow.
 *
 * Runs unattended from .github/workflows/daily-bible-post.yml.
 * ============================================================================
 */
import fs from "node:fs";
import path from "node:path";
import { getDailyVerse, DailyVerse, SCRIPTURE_VERSION } from "./get-bible-verse";
import { createBufferPost } from "./publish-buffer";
import { verseInstagramType } from "./lib/verseConfig";

const ROOT_DIR = path.join(__dirname, "..");
const STATE_PATH = path.join(ROOT_DIR, "data", "bible-post-state.json");

// Must match scripts/build-all-bible-posts.ts's BATCH_RELEASE_TAG/assetFileName --
// duplicated as plain constants (rather than imported) so this lightweight daily
// job never pulls in @remotion/bundler's dependency tree.
const BATCH_RELEASE_TAG = "bible-posts-v3-kjv"; // KJV cards (2026-11-05, DEC-JR-016); v2 (BSB) and v1 (NIV) must never be posted again
/** Only releases whose tag carries the active translation are ever posted (fail closed). */
const REQUIRED_TAG_SUFFIX = `-${SCRIPTURE_VERSION.toLowerCase()}`;
const DEFAULT_REPO = "selvin-paul-raj/jesus-replies-studio";
function assetFileName(index: number): string {
  return `bible-post-day-${index + 1}.png`;
}

interface PostState {
  lastPostedDate?: string;
}

function readState(): PostState {
  try {
    return JSON.parse(fs.readFileSync(STATE_PATH, "utf-8"));
  } catch {
    return {};
  }
}

function writeState(state: PostState): void {
  fs.mkdirSync(path.dirname(STATE_PATH), { recursive: true });
  fs.writeFileSync(STATE_PATH, JSON.stringify(state, null, 2) + "\n");
}

function todayUTC(): string {
  return new Date().toISOString().slice(0, 10);
}

// Instagram caption template -- edit the wording/hashtags here directly.
// Placeholders: {{text}} (verse text), {{reference}} (e.g. "Psalm 126:5-6"),
// {{version}} (the configured translation, "KJV").
const CAPTION_TEMPLATE = `✨ Today's blessing:

"{{text}}"

— {{reference}} ({{version}})

🙏 Keep this one close today.

#Bible #Jesus #Faith #Blessed #Scripture #DailyVerse #JesusRepliesOfficial`;

function buildCaption(verse: DailyVerse): string {
  const base = CAPTION_TEMPLATE.replace("{{text}}", verse.text)
    .replace("{{reference}}", verse.reference)
    .replace("{{version}}", verse.version);
  return verse.series ? `${base}\n\nGlobal Bible Month, Day ${verse.series.day} of 30 ${verse.series.hashtags}` : base;
}

/** The pre-built image's public URL -- no rendering, no `gh` CLI, no auth
 * needed; GitHub Release asset URLs are publicly fetchable as-is. */
function batchAssetUrl(verse: DailyVerse): string {
  const repo = process.env.GITHUB_REPOSITORY || DEFAULT_REPO;
  if (verse.series) {
    return `https://github.com/${repo}/releases/download/${verse.series.releaseTag}/${verse.series.tag}-day-${verse.series.day}.png`;
  }
  return `https://github.com/${repo}/releases/download/${BATCH_RELEASE_TAG}/${assetFileName(verse.dayIndex)}`;
}

async function main(): Promise<void> {
  const force = process.argv.includes("--force") || process.env.FORCE_POST === "true";
  const today = todayUTC();
  const state = readState();

  if (!force && state.lastPostedDate === today) {
    console.log(`[bible-post] Already posted for ${today}, skipping (rerun with --force to override).`);
    return;
  }

  console.log(`[bible-post] Fetching verse for ${today}...`);
  const verse = await getDailyVerse();
  console.log(`[bible-post] Verse: ${verse.reference} (${verse.version})`);

  const mediaUrl = batchAssetUrl(verse);
  console.log(`[bible-post] Pre-built media URL: ${mediaUrl}`);

  // Fail closed: never fall back to the old BSB (v2) or NIV (v1) cards. The KJV batch must be built
  // first (Actions -> "Build Bible Posts" / "Build Series Verse Cards" -> Run workflow).
  const tag = verse.series ? verse.series.releaseTag : BATCH_RELEASE_TAG;
  if (verse.version !== SCRIPTURE_VERSION || !tag.endsWith(REQUIRED_TAG_SUFFIX)) {
    throw new Error(`refusing to post: verse is ${verse.version} from release ${tag}; only ${SCRIPTURE_VERSION} cards from *${REQUIRED_TAG_SUFFIX} releases are posted`);
  }
  const head = await fetch(mediaUrl, { method: "HEAD", redirect: "follow" }).catch(() => null);
  if (!head || !head.ok) {
    throw new Error(
      `pre-built ${SCRIPTURE_VERSION} card not found (${head ? head.status : "unreachable"}) at ${mediaUrl}. ` +
        `Run the build workflow once to create release ${tag}.`
    );
  }

  const instagramChannelId = process.env.BUFFER_INSTAGRAM_CHANNEL_ID;
  if (!instagramChannelId) throw new Error("BUFFER_INSTAGRAM_CHANNEL_ID is not set");

  const caption = buildCaption(verse);

  const instagramType = verseInstagramType();
  console.log(`[bible-post] Posting to Instagram via Buffer as a ${instagramType}...`);
  await createBufferPost({ channelId: instagramChannelId, text: caption, mediaUrl, instagramType });

  writeState({ lastPostedDate: today });
  console.log(`[bible-post] Done. Recorded lastPostedDate=${today}.`);
}

main().catch((error) => {
  console.error("[bible-post] FAILED:", error instanceof Error ? error.message : error);
  process.exit(1);
});
