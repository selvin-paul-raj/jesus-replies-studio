/**
 * ============================================================================
 * BUFFER PUBLISHER -- thin client around Buffer's GraphQL API (the REST v1
 * API is deprecated and rejects "public API token" keys outright) to create
 * a post with one image on one channel. Used only by
 * scripts/daily-bible-post.ts. BUFFER_API_KEY must be a key generated for
 * the GraphQL API (Buffer settings -> API), not the old OAuth access token.
 *
 * Uses mode: customScheduled with dueAt = now + a small buffer instead of
 * addToQueue, since addToQueue posts at Buffer's next configured slot (not
 * necessarily now) -- the workflow's cron IS the desired post time. Buffer
 * rejects a dueAt that isn't strictly in the future by the time its server
 * validates the request, so a bare `new Date()` is a race Buffer usually
 * loses -- DUE_AT_BUFFER_MS pushes it far enough ahead to reliably win.
 * See scripts/list-buffer-channels.ts to look up a channel's GraphQL id.
 * ============================================================================
 */

const BUFFER_API_BASE = "https://api.buffer.com";
const DUE_AT_BUFFER_MS = 2 * 60 * 1000;

export interface BufferPostInput {
  channelId: string;
  text: string;
  mediaUrl: string;
}

export async function createBufferPost({ channelId, text, mediaUrl }: BufferPostInput): Promise<void> {
  const apiKey = process.env.BUFFER_API_KEY;
  if (!apiKey) throw new Error("BUFFER_API_KEY is not set");

  const dueAt = new Date(Date.now() + DUE_AT_BUFFER_MS).toISOString();
  const query = `
    mutation {
      createPost(input: {
        text: ${JSON.stringify(text)}
        channelId: ${JSON.stringify(channelId)}
        schedulingType: automatic
        mode: customScheduled
        dueAt: ${JSON.stringify(dueAt)}
        assets: [{ image: { url: ${JSON.stringify(mediaUrl)} } }]
        metadata: { instagram: { type: post, shouldShareToFeed: true } }
      }) {
        ... on PostActionSuccess {
          post { id status }
        }
        ... on MutationError {
          message
        }
      }
    }
  `;

  const res = await fetch(BUFFER_API_BASE, {
    method: "POST",
    headers: { "Content-Type": "application/json", Authorization: `Bearer ${apiKey}` },
    body: JSON.stringify({ query }),
  });

  const json = await res.json().catch(() => ({}));
  const result = json?.data?.createPost;
  if (!res.ok || json?.errors || result?.message) {
    throw new Error(
      `Buffer post failed for channel ${channelId}: ${JSON.stringify(json?.errors ?? result ?? json)}`
    );
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
