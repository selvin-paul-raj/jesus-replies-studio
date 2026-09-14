import { Script } from "./scriptAdapter";

/**
 * ============================================================================
 * SOCIAL METADATA -- generates Instagram/YouTube copy from the same episode
 * JSON, so nobody hand-writes captions per episode. Node-only, pure
 * functions (no fs/network) -- called from scripts/build-episode.ts.
 * ============================================================================
 */

export interface SocialMeta {
  instagram: { description: string };
  youtube: { title: string; description: string };
}

export const INSTAGRAM_DESC_MAX = 2200;
export const INSTAGRAM_HASHTAG_MAX = 30;
export const YOUTUBE_TITLE_MAX = 100;
export const YOUTUBE_DESC_MAX = 5000;

const BASE_HASHTAGS = [
  "Jesus",
  "Bible",
  "Christian",
  "Faith",
  "God",
  "Scripture",
  "BibleVerse",
  "ChristianContent",
  "JesusRepliesOfficial",
];

function topicWord(topic: string): string {
  return topic
    .split(/[\s_-]+/)
    .filter(Boolean)
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join("");
}

function buildHashtags(topic: string): string[] {
  const tags = Array.from(new Set([...BASE_HASHTAGS, topicWord(topic)])).filter(Boolean);
  return tags.slice(0, INSTAGRAM_HASHTAG_MAX).map((t) => `#${t}`);
}

function sceneText(script: Script, speaker: string): string | undefined {
  return script.video.scenes.find((s) => s.speaker === speaker)?.text?.trim();
}

function engagementText(script: Script): string {
  return sceneText(script, "engagement") ?? "What do you think? Share your answer in the comments.";
}

function bibleRef(script: Script): string {
  const bible = script.video.bible;
  if (!bible) return "";
  return `${bible.book} ${bible.chapter}:${bible.verse}${bible.version ? ` (${bible.version})` : ""}`;
}

function conversationSummary(script: Script): string {
  return script.video.scenes
    .filter((s) => s.speaker === "person" || s.speaker === script.video.character || s.speaker === "jesus")
    .map((s) => s.text?.trim())
    .filter(Boolean)
    .join(" ");
}

/**
 * Hook + short explanation + full verse/reference + engagement question +
 * comment CTA + hashtags. If the hashtag list has to shrink to fit the
 * 2200-char budget, that shrinks first (the body content is the point).
 */
export function buildInstagramDescription(script: Script): string {
  const { title, topic, bible } = script.video;
  const engagement = engagementText(script);

  const bodyLines = [
    `${title}`,
    "",
    `Is it just words on a page -- or something meant for your life today? A short conversation about ${topic}.`,
    "",
    bible ? `Jesus reminds us:\n\n“${bible.text}”` : "",
    bible ? `📖 ${bibleRef(script)}` : "",
    "",
    engagement,
    "",
    "👇",
  ];

  let hashtags = buildHashtags(topic);
  const render = () => [...bodyLines, "", hashtags.join(" ")].join("\n").trim();

  let description = render();
  while (description.length > INSTAGRAM_DESC_MAX && hashtags.length > 0) {
    hashtags = hashtags.slice(0, -1);
    description = render();
  }

  if (description.length > INSTAGRAM_DESC_MAX) {
    throw new Error(
      `Instagram description exceeds ${INSTAGRAM_DESC_MAX} characters (got ${description.length}) even with 0 hashtags`
    );
  }
  if (hashtags.length > INSTAGRAM_HASHTAG_MAX) {
    throw new Error(`Instagram hashtags exceed ${INSTAGRAM_HASHTAG_MAX} (got ${hashtags.length})`);
  }
  return description;
}

/** Topic + episode title + Bible context, capped to 100 chars -- falls back
 * to shorter candidates (never scene text truncated mid-word past that). */
export function buildYoutubeTitle(script: Script): string {
  const { title, topic, bible } = script.video;
  const candidates = [
    bible ? `${title} | What Jesus Says About ${topicWord(topic)} (${bible.book} ${bible.chapter}:${bible.verse})` : "",
    `${title} | What Jesus Says About ${topicWord(topic)}`,
    `${title} | Jesus's Replies`,
    title,
  ].filter(Boolean) as string[];

  const chosen = candidates.find((c) => c.length <= YOUTUBE_TITLE_MAX) ?? candidates[candidates.length - 1].slice(0, YOUTUBE_TITLE_MAX);
  if (chosen.length > YOUTUBE_TITLE_MAX) {
    throw new Error(`YouTube title exceeds ${YOUTUBE_TITLE_MAX} characters (got ${chosen.length})`);
  }
  return chosen;
}

/** More detailed than the Instagram caption: hook, summary, conversation
 * context, full verse, reference, engagement question, comment CTA,
 * channel context, hashtags -- capped to 5000 chars. */
export function buildYoutubeDescription(script: Script): string {
  const { title, topic, bible } = script.video;
  const engagement = engagementText(script);

  const sections = [
    title,
    "",
    `A short conversation between a boy and Jesus about ${topic}.`,
    "",
    conversationSummary(script),
    "",
    bible ? `Full verse:\n“${bible.text}”\n${bibleRef(script)}` : "",
    "",
    engagement,
    "We read every comment -- we'd love to hear from you.",
    "",
    "New Bible conversations every week. Follow Jesus's Replies for more.",
    "",
    buildHashtags(topic).join(" "),
  ].filter((s) => s !== "");

  const description = sections.join("\n");
  if (description.length > YOUTUBE_DESC_MAX) {
    throw new Error(`YouTube description exceeds ${YOUTUBE_DESC_MAX} characters (got ${description.length})`);
  }
  return description;
}

export function buildSocialMeta(script: Script): SocialMeta {
  return {
    instagram: { description: buildInstagramDescription(script) },
    youtube: { title: buildYoutubeTitle(script), description: buildYoutubeDescription(script) },
  };
}
