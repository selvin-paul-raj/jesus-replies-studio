/**
 * Storage layer for Jesus Replies weekly batches.
 *
 * ONE WEEK = ONE RELEASE = 14 VIDEOS. A GitHub Release is temporary public media
 * storage so Buffer can fetch the MP4s; it is never the canonical content store.
 * JOE holds state, this repo holds generation, `Input/` stays read-only history.
 */
export type Slot = "morning" | "night";

export type VideoStatus =
  | "PENDING" | "RENDERED" | "UPLOADING" | "UPLOADED" | "VERIFIED"
  | "SCHEDULING" | "SCHEDULED" | "PUBLISHING" | "PUBLISHED" | "FAILED" | "SKIPPED";

export type PlatformStatus =
  | "SKIPPED" | "READY" | "SCHEDULING" | "SCHEDULED" | "PUBLISHING" | "PUBLISHED" | "FAILED";

export type BatchStatus =
  | "GENERATING" | "VALIDATING" | "RENDERING" | "QA" | "UPLOADING" | "VERIFYING_ASSETS"
  | "SCHEDULING" | "SCHEDULED" | "PUBLISHING" | "COMPLETED" | "FAILED" | "PARTIAL_FAILURE"
  | "CLEANUP_PENDING" | "CLEANED";

export interface BatchVideo {
  episode_id: string;          // JR-XXXX, from the existing id mechanism. Never reused.
  date: string;                // YYYY-MM-DD, the publishing day
  slot: Slot;
  asset_name: string;          // JR-XXXX.mp4 — deterministic, no -1/-retry suffixes
  public_url: string | null;
  sha256: string | null;
  size_bytes: number | null;
  duration_s: number | null;
  status: VideoStatus;
  verification: "UNKNOWN" | "VERIFIED" | "FAILED";
  scheduled_at: string | null; // ISO, the Buffer due time
  buffer: {
    instagram: { post_id: string | null; status: PlatformStatus };
    youtube: { post_id: string | null; status: PlatformStatus };
  };
}

export interface WeeklyBatch {
  batch_id: string;            // jr-week-YYYY-MM-DD
  week_start: string;
  week_end: string;
  release_tag: string;         // identical to batch_id
  expected_videos: 14;
  status: BatchStatus;
  created_at: string;
  last_scheduled_at: string | null;  // drives retention: delete only well past this
  videos: BatchVideo[];
}

export interface UploadResult {
  asset_name: string;
  action: "UPLOADED" | "REUSED_EXISTING" | "REPLACED_INVALID" | "FAILED";
  public_url: string | null;
  size_bytes: number | null;
  reason?: string;
}

export interface UrlVerification {
  url: string;
  ok: boolean;
  http_status: number | null;
  content_type: string | null;
  failures: string[];
}
