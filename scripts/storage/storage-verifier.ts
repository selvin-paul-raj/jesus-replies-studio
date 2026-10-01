import type { UrlVerification } from "./storage-types.js";

/**
 * Verify a release asset URL the way Buffer will: anonymously, no token, no API.
 * Buffer has no upload endpoint, so the URL must be public HTTPS serving the file
 * directly. GitHub API metadata is NOT accepted as proof the URL works.
 */
export async function verifyPublicUrl(url: string): Promise<UrlVerification> {
  const failures: string[] = [];
  if (!url.toLowerCase().startsWith("https://")) failures.push("not HTTPS");

  let status: number | null = null;
  let contentType: string | null = null;
  try {
    // Range request: prove bytes are actually served without pulling the whole file.
    const res = await fetch(url, { headers: { Range: "bytes=0-1023" }, redirect: "follow" });
    status = res.status;
    contentType = res.headers.get("content-type");
    const head = Buffer.from(await res.arrayBuffer()).subarray(0, 512).toString("utf8").toLowerCase();
    if (![200, 206].includes(res.status)) failures.push(`HTTP ${res.status}`);
    if (!contentType || !/^(video|application\/octet-stream|image)/.test(contentType))
      failures.push(`content-type ${contentType ?? "absent"} is not media`);
    if (head.includes("<html")) failures.push("HTML body: login or preview page, not the file");
    if (head.includes("sign in to github")) failures.push("GitHub sign-in page: asset is not public");
    if (/[?&](x-amz-signature|expires)=/i.test(url))
      failures.push("signed or expiring URL; it must stay reachable until the post publishes");
  } catch (err) {
    failures.push(`unreachable: ${(err as Error).message.slice(0, 120)}`);
  }
  return { url, ok: failures.length === 0, http_status: status, content_type: contentType, failures };
}

export async function verifyAll(urls: string[]): Promise<UrlVerification[]> {
  const out: UrlVerification[] = [];
  for (const u of urls) out.push(await verifyPublicUrl(u));   // sequential: kinder to the CDN
  return out;
}
