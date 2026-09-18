/**
 * ============================================================================
 * BUFFER PUBLISHER -- thin client around Buffer's public API (v1) to create
 * an update (post) on one channel. Used only by scripts/daily-bible-post.ts.
 * ============================================================================
 */

const BUFFER_API_BASE = "https://api.bufferapp.com/1";

export interface BufferPostInput {
  channelId: string;
  text: string;
  mediaUrl: string;
}

export async function createBufferPost({ channelId, text, mediaUrl }: BufferPostInput): Promise<void> {
  const accessToken = process.env.BUFFER_API_KEY;
  if (!accessToken) throw new Error("BUFFER_API_KEY is not set");

  const body = new URLSearchParams();
  body.append("access_token", accessToken);
  body.append("profile_ids[]", channelId);
  body.append("text", text);
  body.append("media[photo]", mediaUrl);
  body.append("media[thumbnail]", mediaUrl);
  body.append("now", "true");

  const res = await fetch(`${BUFFER_API_BASE}/updates/create.json`, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body,
  });

  const json = await res.json().catch(() => ({}));
  if (!res.ok || json?.success === false) {
    throw new Error(`Buffer post failed for channel ${channelId} (${res.status}): ${JSON.stringify(json)}`);
  }
}

if (require.main === module) {
  const [channelId, text, mediaUrl] = process.argv.slice(2);
  if (!channelId || !text || !mediaUrl) {
    console.error("Usage: tsx scripts/publish-buffer.ts <channelId> <text> <mediaUrl>");
    process.exit(1);
  }
  createBufferPost({ channelId, text, mediaUrl })
    .then(() => console.log("[publish-buffer] Posted."))
    .catch((error) => {
      console.error("[publish-buffer] FAILED:", error instanceof Error ? error.message : error);
      process.exit(1);
    });
}
