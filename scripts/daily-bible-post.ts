/**
 * ============================================================================
 * DAILY BIBLE POST -- orchestrates the whole Bible Verse Post Tool pipeline:
 *   get verse -> render 9:16 still (existing Remotion pipeline) -> upload as
 *   a GitHub Release asset (public media URL) -> post to Instagram via
 *   Buffer -> record today's date so reruns are a no-op.
 *
 * Runs unattended from .github/workflows/daily-bible-post.yml. The release
 * upload step needs GITHUB_REPOSITORY + a `gh`-authenticated environment
 * (set by the workflow); running this locally will fail past that point,
 * which is expected -- use `tsx scripts/get-bible-verse.ts` and
 * `tsx scripts/publish-buffer.ts` directly to test those pieces in isolation.
 * ============================================================================
 */
import fs from "node:fs";
import path from "node:path";
import { execSync } from "node:child_process";
import { getDailyVerse, DailyVerse } from "./get-bible-verse";
import { createBufferPost } from "./publish-buffer";
import { BibleVersePostPropsSchema } from "../src/schema";

const ROOT_DIR = path.join(__dirname, "..");
const STATE_PATH = path.join(ROOT_DIR, "data", "bible-post-state.json");
const OUT_DIR = path.join(ROOT_DIR, "output", "bible_verse");

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

function buildCaption(verse: DailyVerse): string {
  return [
    `✨ Today's blessing:`,
    "",
    `"${verse.text}"`,
    "",
    `— ${verse.reference} (${verse.version})`,
    "",
    "🙏 Say Amen if you're receiving this today, and tag someone who needs it.",
    "",
    "#Bible #Jesus #Faith #Blessed #Scripture #DailyVerse #JesusRepliesOfficial",
  ].join("\n");
}

/** Writes props for the BibleVersePost Still and shells out to `remotion
 * still`, same pattern scripts/lib/renderEpisode.ts uses for Episode/Thumbnail. */
function renderVerseImage(verse: DailyVerse, id: string): string {
  const props = BibleVersePostPropsSchema.parse({
    verseText: verse.text,
    referenceText: `${verse.reference}\n${verse.version}`,
  });

  fs.mkdirSync(OUT_DIR, { recursive: true });
  const propsPath = path.join(OUT_DIR, `${id}.props.json`);
  const imagePath = path.join(OUT_DIR, `${id}.png`);
  fs.writeFileSync(propsPath, JSON.stringify(props, null, 2));

  execSync(`npx remotion still src/index.ts BibleVersePost "${imagePath}" --props="${propsPath}"`, {
    cwd: ROOT_DIR,
    stdio: "inherit",
  });

  return imagePath;
}

/** Buffer needs a public URL to fetch the media from. A dated GitHub Release
 * asset gives us that for free, no extra hosting account/secret required. */
function uploadReleaseAsset(imagePath: string, tag: string): string {
  const repo = process.env.GITHUB_REPOSITORY;
  if (!repo) throw new Error("GITHUB_REPOSITORY is not set (this step must run inside GitHub Actions with `gh` authenticated)");

  execSync(`gh release view "${tag}" || gh release create "${tag}" --title "${tag}" --notes "Daily Bible verse post"`, {
    cwd: ROOT_DIR,
    stdio: "inherit",
  });
  execSync(`gh release upload "${tag}" "${imagePath}" --clobber`, { cwd: ROOT_DIR, stdio: "inherit" });

  return `https://github.com/${repo}/releases/download/${tag}/${path.basename(imagePath)}`;
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

  const id = `bible-post-${today}`;
  console.log("[bible-post] Rendering verse image...");
  const imagePath = renderVerseImage(verse, id);

  console.log("[bible-post] Uploading media as a GitHub Release asset...");
  const mediaUrl = uploadReleaseAsset(imagePath, id);
  console.log(`[bible-post] Media URL: ${mediaUrl}`);

  const instagramChannelId = process.env.BUFFER_INSTAGRAM_CHANNEL_ID;
  if (!instagramChannelId) throw new Error("BUFFER_INSTAGRAM_CHANNEL_ID is not set");

  const caption = buildCaption(verse);

  console.log("[bible-post] Posting to Instagram via Buffer...");
  await createBufferPost({ channelId: instagramChannelId, text: caption, mediaUrl });

  writeState({ lastPostedDate: today });
  console.log(`[bible-post] Done. Recorded lastPostedDate=${today}.`);
}

main().catch((error) => {
  console.error("[bible-post] FAILED:", error instanceof Error ? error.message : error);
  process.exit(1);
});
