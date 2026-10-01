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

/**
 * ----------------------------------------------------------------------------
 * VIDEO POSTS (Jesus Replies, System B)
 *
 * Extends this client rather than replacing it: createBufferPost above stays
 * exactly as the Bible post path uses it. Video assets use the documented
 * shape assets[].video.url with VideoMetadataInput.thumbnailOffset in ms.
 * video.thumbnailUrl is rejected for video assets, so it is never sent.
 *
 * Idempotency and reconciliation: a post id already recorded for this
 * (episode, platform) is reused and no request is sent. If a request's
 * outcome cannot be read (timeout, unparseable body), the result is recorded
 * UNRESOLVED and the caller must NOT retry: a duplicate public post cannot be
 * undone, so this fails closed and asks for reconciliation instead.
 * ----------------------------------------------------------------------------
 */

const THUMBNAIL_OFFSET_MS = 1500;

export type VideoPlatform = "instagram" | "youtube";

export interface BufferVideoPostInput {
  channelId: string;
  platform: VideoPlatform;
  text: string;
  videoUrl: string;
  dueAt: string;                 // ISO, the slot's scheduled publish time
  youtubeTitle?: string;
  existingPostId?: string | null; // from JOE state; set means do not send
}

export type BufferVideoResult =
  | { outcome: "REUSED_EXISTING"; postId: string; status: string | null }
  | { outcome: "CREATED"; postId: string; status: string | null }
  | { outcome: "UNRESOLVED"; postId: null; detail: string }
  | { outcome: "FAILED"; postId: null; detail: string };

function videoPostMutation(input: BufferVideoPostInput): string {
  const metadata =
    input.platform === "instagram"
      ? "metadata: { instagram: { type: reel, shouldShareToFeed: true } }"
      : `metadata: { youtube: { title: ${JSON.stringify(input.youtubeTitle ?? "")} } }`;
  return `
    mutation {
      createPost(input: {
        text: ${JSON.stringify(input.text)}
        channelId: ${JSON.stringify(input.channelId)}
        schedulingType: automatic
        mode: customScheduled
        dueAt: ${JSON.stringify(input.dueAt)}
        assets: [{ video: { url: ${JSON.stringify(input.videoUrl)}, metadata: { thumbnailOffset: ${THUMBNAIL_OFFSET_MS} } } }]
        ${metadata}
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
}

/** Build the payload without sending it. Used by the dry run. */
export function buildVideoPayload(input: BufferVideoPostInput): { query: string; platform: VideoPlatform; asset_field: string; thumbnail_offset_ms: number } {
  return {
    query: videoPostMutation(input),
    platform: input.platform,
    asset_field: "assets[].video.url",
    thumbnail_offset_ms: THUMBNAIL_OFFSET_MS,
  };
}

export async function createBufferVideoPost(input: BufferVideoPostInput): Promise<BufferVideoResult> {
  if (input.existingPostId) {
    console.log(`[buffer] platform=${input.platform} action=REUSED_EXISTING post_id=${input.existingPostId}`);
    return { outcome: "REUSED_EXISTING", postId: input.existingPostId, status: null };
  }
  const apiKey = process.env.BUFFER_API_KEY;
  if (!apiKey) throw new Error("BUFFER_API_KEY is not set");
  if (!input.videoUrl.startsWith("https://")) throw new Error("video URL must be public HTTPS");

  let res: Response;
  try {
    res = await fetch(BUFFER_API_BASE, {
      method: "POST",
      headers: { "Content-Type": "application/json", Authorization: `Bearer ${apiKey}` },
      body: JSON.stringify({ query: videoPostMutation(input) }),
    });
  } catch (err) {
    // The request may or may not have reached Buffer. Never retry blind.
    const detail = `request did not complete: ${(err as Error).message.slice(0, 160)}`;
    console.log(`[buffer] platform=${input.platform} action=UNRESOLVED reason=${detail}`);
    return { outcome: "UNRESOLVED", postId: null, detail };
  }

  let json: any;
  try {
    json = await res.json();
  } catch {
    const detail = `HTTP ${res.status} with an unreadable body; the post may exist`;
    console.log(`[buffer] platform=${input.platform} action=UNRESOLVED reason=${detail}`);
    return { outcome: "UNRESOLVED", postId: null, detail };
  }

  const result = json?.data?.createPost;
  if (!res.ok || json?.errors || result?.message) {
    const detail = JSON.stringify(json?.errors ?? result ?? json).slice(0, 300);
    console.log(`[buffer] platform=${input.platform} action=FAILED`);
    return { outcome: "FAILED", postId: null, detail };
  }

  const postId = result?.post?.id;
  if (!postId) {
    const detail = "success response carried no post id; reconcile before any retry";
    console.log(`[buffer] platform=${input.platform} action=UNRESOLVED reason=${detail}`);
    return { outcome: "UNRESOLVED", postId: null, detail };
  }

  console.log(`[buffer] platform=${input.platform} action=CREATED post_id=${postId} status=${result.post.status ?? "unknown"}`);
  return { outcome: "CREATED", postId, status: result.post.status ?? null };
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
