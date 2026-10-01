import { createReadStream, statSync } from "node:fs";
import { createHash } from "node:crypto";
import { readFile } from "node:fs/promises";
import type { UploadResult } from "./storage-types.js";
import { verifyPublicUrl } from "./storage-verifier.js";

/**
 * Weekly GitHub Release as temporary public media storage.
 * ONE WEEK = ONE RELEASE = 14 VIDEOS. Idempotent by tag and by asset name: a rerun
 * reuses the release and uploads only what is missing or invalid. It never creates
 * jr-week-...-2 / -retry, and never JR-0024-1.mp4.
 * Auth: GITHUB_TOKEN with `permissions: contents: write`. Never logged.
 */
const API = "https://api.github.com";

function repo(): { owner: string; name: string } {
  const slug = process.env.GITHUB_REPOSITORY;
  if (!slug) throw new Error("GITHUB_REPOSITORY is not set");
  const [owner, name] = slug.split("/");
  return { owner, name };
}

function token(): string {
  const t = process.env.GITHUB_TOKEN;
  if (!t) throw new Error("GITHUB_TOKEN is not set");
  return t;
}

async function gh(path: string, init: RequestInit = {}): Promise<any> {
  const res = await fetch(path.startsWith("http") ? path : `${API}${path}`, {
    ...init,
    headers: {
      Authorization: `Bearer ${token()}`,
      Accept: "application/vnd.github+json",
      "X-GitHub-Api-Version": "2022-11-28",
      ...(init.headers ?? {}),
    },
  });
  if (res.status === 404) return null;
  if (!res.ok) throw new Error(`GitHub ${init.method ?? "GET"} ${path} -> ${res.status} ${(await res.text()).slice(0, 200)}`);
  return res.status === 204 ? true : res.json();
}

export function weeklyBatchId(weekStart: string): string {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(weekStart)) throw new Error(`week_start must be YYYY-MM-DD, got ${weekStart}`);
  return `jr-week-${weekStart}`;
}

export const WEEKLY_TAG_PATTERN = /^jr-week-\d{4}-\d{2}-\d{2}$/;

export function getPublicUrl(tag: string, assetName: string): string {
  const { owner, name } = repo();
  return `https://github.com/${owner}/${name}/releases/download/${encodeURIComponent(tag)}/${encodeURIComponent(assetName)}`;
}

export async function createOrGetWeeklyRelease(tag: string, body: string): Promise<any> {
  const { owner, name } = repo();
  const existing = await gh(`/repos/${owner}/${name}/releases/tags/${encodeURIComponent(tag)}`);
  if (existing) {
    console.log(`[storage] release=${tag} action=REUSED assets=${existing.assets?.length ?? 0}`);
    return existing;
  }
  const made = await gh(`/repos/${owner}/${name}/releases`, {
    method: "POST",
    body: JSON.stringify({ tag_name: tag, name: tag, body, draft: false, prerelease: false }),
  });
  console.log(`[storage] release=${tag} action=CREATED`);
  return made;
}

export async function getReleaseAssets(tag: string): Promise<any[]> {
  const { owner, name } = repo();
  const rel = await gh(`/repos/${owner}/${name}/releases/tags/${encodeURIComponent(tag)}`);
  return rel?.assets ?? [];
}

async function sha256(file: string): Promise<string> {
  const h = createHash("sha256");
  await new Promise<void>((ok, bad) =>
    createReadStream(file).on("data", (c) => h.update(c)).on("end", ok).on("error", bad));
  return h.digest("hex");
}

/** Upload one MP4. Reuses a valid existing asset; replaces one that fails verification. */
export async function uploadVideo(tag: string, assetName: string, file: string): Promise<UploadResult> {
  const { owner, name } = repo();
  const rel = await gh(`/repos/${owner}/${name}/releases/tags/${encodeURIComponent(tag)}`);
  if (!rel) throw new Error(`release ${tag} does not exist; call createOrGetWeeklyRelease first`);
  const size = statSync(file).size;
  const prior = (rel.assets ?? []).find((a: any) => a.name === assetName);

  if (prior) {
    const check = await verifyPublicUrl(getPublicUrl(tag, assetName));
    if (check.ok && prior.size === size) {
      console.log(`[storage] asset=${assetName} action=REUSED_EXISTING bytes=${prior.size}`);
      return { asset_name: assetName, action: "REUSED_EXISTING", public_url: getPublicUrl(tag, assetName), size_bytes: prior.size };
    }
    console.log(`[storage] asset=${assetName} action=REPLACING reason=${check.ok ? "size mismatch" : check.failures.join("; ")}`);
    await gh(`/repos/${owner}/${name}/releases/assets/${prior.id}`, { method: "DELETE" });
  }

  const up = rel.upload_url.replace(/\{\?.*\}$/, "") + `?name=${encodeURIComponent(assetName)}`;
  await gh(up, {
    method: "POST",
    headers: { "Content-Type": "video/mp4", "Content-Length": String(size) },
    body: await readFile(file),
  });
  console.log(`[storage] asset=${assetName} action=UPLOADED bytes=${size} sha256=${(await sha256(file)).slice(0, 12)}…`);
  return { asset_name: assetName, action: prior ? "REPLACED_INVALID" : "UPLOADED", public_url: getPublicUrl(tag, assetName), size_bytes: size };
}

/** Upload a whole batch, skipping what is already there. Resumable by construction. */
export async function uploadWeeklyBatch(tag: string, files: { asset_name: string; file: string }[]): Promise<UploadResult[]> {
  const out: UploadResult[] = [];
  for (const f of files) {
    try {
      out.push(await uploadVideo(tag, f.asset_name, f.file));
    } catch (err) {
      console.log(`[storage] asset=${f.asset_name} action=FAILED`);
      out.push({ asset_name: f.asset_name, action: "FAILED", public_url: null, size_bytes: null, reason: (err as Error).message.slice(0, 200) });
    }
  }
  return out;
}

/** Fails closed: refuses anything that is not an exact weekly tag. */
export async function cleanupWeeklyRelease(tag: string, safe: boolean, reason: string): Promise<"DELETED" | "KEPT"> {
  if (!WEEKLY_TAG_PATTERN.test(tag)) {
    console.log(`[cleanup] release=${tag} action=KEEP reason=tag is not a Jesus Replies weekly release`);
    return "KEPT";
  }
  if (!safe) {
    console.log(`[cleanup] release=${tag} action=KEEP reason=${reason}`);
    return "KEPT";
  }
  const { owner, name } = repo();
  const rel = await gh(`/repos/${owner}/${name}/releases/tags/${encodeURIComponent(tag)}`);
  if (!rel) { console.log(`[cleanup] release=${tag} action=KEEP reason=already absent`); return "KEPT"; }
  await gh(`/repos/${owner}/${name}/releases/${rel.id}`, { method: "DELETE" });
  console.log(`[cleanup] release=${tag} action=DELETE videos=${rel.assets?.length ?? 0}`);
  return "DELETED";
}
