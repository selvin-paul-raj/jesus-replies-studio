import { mkdirSync, readFileSync, writeFileSync, existsSync } from "node:fs";
import { dirname } from "node:path";
import type { BatchVideo, BatchStatus, Slot, WeeklyBatch } from "./storage-types.js";
import { weeklyBatchId } from "./github-release.js";

/**
 * The 14-video weekly manifest: 7 morning + 7 night, Monday through Sunday.
 * Merging is additive. A rerun keeps every episode that already succeeded and only
 * fills the gaps, so a half-finished week resumes instead of starting over.
 */
export const EXPECTED_VIDEOS = 14 as const;
export const SLOTS: Slot[] = ["morning", "night"];

function addDays(iso: string, n: number): string {
  const d = new Date(`${iso}T00:00:00Z`);
  d.setUTCDate(d.getUTCDate() + n);
  return d.toISOString().slice(0, 10);
}

/** The 14 (date, slot) pairs a week must fill, in publishing order. */
export function weekPlan(weekStart: string): { date: string; slot: Slot }[] {
  return Array.from({ length: 7 }, (_, day) =>
    SLOTS.map((slot) => ({ date: addDays(weekStart, day), slot }))).flat();
}

export function emptyVideo(episodeId: string, date: string, slot: Slot): BatchVideo {
  return {
    episode_id: episodeId, date, slot, asset_name: `${episodeId}.mp4`,
    public_url: null, sha256: null, size_bytes: null, duration_s: null,
    status: "PENDING", verification: "UNKNOWN", scheduled_at: null,
    buffer: { instagram: { post_id: null, status: "READY" }, youtube: { post_id: null, status: "READY" } },
  };
}

export function newBatch(weekStart: string): WeeklyBatch {
  return {
    batch_id: weeklyBatchId(weekStart), week_start: weekStart, week_end: addDays(weekStart, 6),
    release_tag: weeklyBatchId(weekStart), expected_videos: EXPECTED_VIDEOS,
    status: "GENERATING", created_at: new Date().toISOString(), last_scheduled_at: null, videos: [],
  };
}

export function manifestPath(batchId: string): string {
  return `generated/batches/${batchId}.json`;
}

export function loadBatch(weekStart: string): WeeklyBatch {
  const p = manifestPath(weeklyBatchId(weekStart));
  return existsSync(p) ? (JSON.parse(readFileSync(p, "utf8")) as WeeklyBatch) : newBatch(weekStart);
}

export function saveBatch(batch: WeeklyBatch): string {
  const p = manifestPath(batch.batch_id);
  mkdirSync(dirname(p), { recursive: true });
  writeFileSync(p, `${JSON.stringify(batch, null, 2)}\n`);
  return p;
}

/** Additive merge: an incoming row never clears a Buffer post id or a verified URL. */
export function mergeVideo(batch: WeeklyBatch, incoming: BatchVideo): WeeklyBatch {
  const at = batch.videos.findIndex((v) => v.episode_id === incoming.episode_id);
  if (at === -1) { batch.videos.push(incoming); return batch; }
  const prior = batch.videos[at];
  batch.videos[at] = {
    ...prior, ...incoming,
    public_url: incoming.public_url ?? prior.public_url,
    sha256: incoming.sha256 ?? prior.sha256,
    scheduled_at: incoming.scheduled_at ?? prior.scheduled_at,
    buffer: {
      instagram: { post_id: prior.buffer.instagram.post_id ?? incoming.buffer.instagram.post_id, status: incoming.buffer.instagram.status },
      youtube: { post_id: prior.buffer.youtube.post_id ?? incoming.buffer.youtube.post_id, status: incoming.buffer.youtube.status },
    },
  };
  return batch;
}

/** What is still outstanding, so a retry knows exactly where to pick up. */
export function gaps(batch: WeeklyBatch): { missing_slots: { date: string; slot: Slot }[]; unrendered: string[]; unverified: string[]; unscheduled: string[] } {
  const filled = new Set(batch.videos.map((v) => `${v.date}:${v.slot}`));
  return {
    missing_slots: weekPlan(batch.week_start).filter((s) => !filled.has(`${s.date}:${s.slot}`)),
    unrendered: batch.videos.filter((v) => v.status === "PENDING" || v.duration_s === null).map((v) => v.episode_id),
    unverified: batch.videos.filter((v) => v.verification !== "VERIFIED").map((v) => v.episode_id),
    unscheduled: batch.videos.filter((v) => !v.buffer.instagram.post_id && !v.buffer.youtube.post_id).map((v) => v.episode_id),
  };
}

/** 14 valid videos or no publishing. A 13-video week is a failure, never a partial post. */
export function isPublishable(batch: WeeklyBatch): { ok: boolean; reason: string } {
  if (batch.videos.length !== EXPECTED_VIDEOS)
    return { ok: false, reason: `batch has ${batch.videos.length} videos, needs ${EXPECTED_VIDEOS}` };
  const g = gaps(batch);
  if (g.unrendered.length) return { ok: false, reason: `not rendered: ${g.unrendered.join(", ")}` };
  if (g.unverified.length) return { ok: false, reason: `URL not verified: ${g.unverified.join(", ")}` };
  const dupes = batch.videos.map((v) => `${v.date}:${v.slot}`).filter((k, i, a) => a.indexOf(k) !== i);
  if (dupes.length) return { ok: false, reason: `two videos in one slot: ${dupes.join(", ")}` };
  return { ok: true, reason: "14 videos rendered and verified" };
}

export function setStatus(batch: WeeklyBatch, status: BatchStatus): WeeklyBatch {
  batch.status = status;
  const times = batch.videos.map((v) => v.scheduled_at).filter(Boolean) as string[];
  const ordered = times.sort();
  batch.last_scheduled_at = ordered.length ? ordered[ordered.length - 1] : null;
  return batch;
}

/** Retention: the release must outlive the last scheduled post by a safety margin. */
export function retentionSafe(batch: WeeklyBatch, graceHours = 24, now = new Date()): { safe: boolean; reason: string } {
  if (!batch.last_scheduled_at) return { safe: false, reason: "no last scheduled time recorded; failing closed" };
  const upcoming = batch.videos.filter((v) => v.scheduled_at && new Date(v.scheduled_at) > now).length;
  if (upcoming) return { safe: false, reason: `${upcoming} upcoming Buffer post(s)` };
  const clear = new Date(new Date(batch.last_scheduled_at).getTime() + graceHours * 3600_000);
  return now >= clear
    ? { safe: true, reason: `last schedule + ${graceHours}h has passed` }
    : { safe: false, reason: `retention until ${clear.toISOString()}` };
}
