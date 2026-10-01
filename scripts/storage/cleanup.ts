import { existsSync, readFileSync } from "node:fs";
import type { WeeklyBatch } from "./storage-types.js";
import { WEEKLY_TAG_PATTERN, cleanupWeeklyRelease } from "./github-release.js";
import { manifestPath, retentionSafe } from "./weekly-batch.js";

/**
 * Retention decision for one weekly release. Fails closed on anything uncertain:
 * a tag that is not jr-week-YYYY-MM-DD, a missing manifest, no recorded last schedule,
 * or any upcoming Buffer post all mean KEEP. A release is only ever deleted whole.
 */
export function decide(tag: string, graceHours = 24, now = new Date()): { action: "DELETE" | "KEEP"; reason: string; videos: number; last_schedule: string | null; upcoming: number } {
  if (!WEEKLY_TAG_PATTERN.test(tag))
    return { action: "KEEP", reason: "not a Jesus Replies weekly release", videos: 0, last_schedule: null, upcoming: 0 };

  const p = manifestPath(tag);
  if (!existsSync(p))
    return { action: "KEEP", reason: "no batch manifest; state is ambiguous", videos: 0, last_schedule: null, upcoming: 0 };

  const batch = JSON.parse(readFileSync(p, "utf8")) as WeeklyBatch;
  const upcoming = batch.videos.filter((v) => v.scheduled_at && new Date(v.scheduled_at) > now).length;
  const unresolved = batch.videos.filter(
    (v) => !["PUBLISHED", "FAILED", "SKIPPED"].includes(v.buffer.instagram.status) ||
           !["PUBLISHED", "FAILED", "SKIPPED"].includes(v.buffer.youtube.status)).length;

  if (unresolved)
    return { action: "KEEP", reason: `${unresolved} post(s) not yet resolved`, videos: batch.videos.length, last_schedule: batch.last_scheduled_at, upcoming };

  const ret = retentionSafe(batch, graceHours, now);
  return { action: ret.safe ? "DELETE" : "KEEP", reason: ret.reason, videos: batch.videos.length, last_schedule: batch.last_scheduled_at, upcoming };
}

async function main(): Promise<void> {
  const tags = process.argv.slice(2);
  if (!tags.length) { console.error("usage: tsx scripts/storage/cleanup.ts <tag> [tag...]"); process.exit(1); }
  const apply = process.env.CLEANUP_APPLY === "true";
  for (const tag of tags) {
    const d = decide(tag);
    console.log(`[cleanup] release=${tag}`);
    console.log(`[cleanup] videos=${d.videos}`);
    console.log(`[cleanup] last_schedule=${d.last_schedule ?? "UNKNOWN"}`);
    console.log(`[cleanup] upcoming_posts=${d.upcoming}`);
    console.log(`[cleanup] retention_safe=${d.action === "DELETE"}`);
    console.log(`[cleanup] action=${d.action}${d.action === "KEEP" ? ` reason=${d.reason}` : ""}`);
    if (apply) await cleanupWeeklyRelease(tag, d.action === "DELETE", d.reason);
    else console.log("[cleanup] report only: nothing deleted");
  }
}

if (process.argv[1]?.endsWith("cleanup.ts")) {
  main().catch((err) => { console.error(`[cleanup] FAILED: ${(err as Error).message}`); process.exit(1); });
}
