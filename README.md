# Jesus's Replies — Fully Customizable Video Template

Turn a short "person asks, Jesus replies, Bible verse, engagement question"
script into a finished 9:16 vertical video (+ matching thumbnail), with
**zero React/TypeScript required** to make a new episode or restyle an
existing one. Every visual property — typography, position, color,
animation, background zoom, audio fades, timing — is data-driven from a zod
schema (`src/schema.ts`), which is also what lets Remotion Studio build live
on-screen controls for all of it.

For a step-by-step, task-oriented walkthrough of every command (preview,
single render, CSV batch, troubleshooting), see **[RUNBOOK.md](RUNBOOK.md)**.
This file is the reference: what exists, how it fits together, and why.

## Two ways to produce a video

| | Legacy script pipeline | New CLI |
|---|---|---|
| Input | Absolute-timestamp `Script` JSON (`scene.start`/`scene.end`) | Simple JSON (`{speaker,text}` lines, auto-timed) or a CSV row |
| Entry point | `npm run build-episode -- <script.json>` | `npm run jr -- render <input.json>` / `npm run jr -- batch <input.csv>` |
| Batch | one file at a time, loop yourself | built in (`batch <csv>`) |
| Style/animation overrides | none — always schema defaults | per-episode `styles` field |
| Timing overrides (`gapSeconds`, `wordsPerSecond`, `revealMode`, ...) | full `timing` field available | **not yet exposed** — always format A's defaults |
| Also produces | `.social.json` (IG/YouTube captions) | not yet wired up |
| Code | `src/scriptAdapter.ts`, `scripts/build-episode.ts` | `scripts/lib/episodeInput.ts`, `scripts/cli.ts` |

Both funnel into the exact same two Remotion compositions (`Episode`,
`Thumbnail`, registered in `src/Root.tsx`) — they only differ in how the
input script gets turned into `EpisodeProps`/`ThumbnailProps`. Use the CLI
for everyday episodes (see RUNBOOK.md); the legacy pipeline exists for
scripts that already come from an upstream tool with real start/end
timestamps and need social captions generated too.

## Quick start

```bash
npm install
npm run preview        # Remotion Studio — drag sliders, watch it update live
```

First render/preview downloads a headless Chrome (~200MB, needs internet).

## What's fully customizable

Everything below lives in the episode data (JSON field or CSV `styles`
cell) — `src/schema.ts` is the single source of truth for the exact shape
and allowed values.

### Per speaker (`person`, `jesus`, `verse`, `reference`, `engagement`)
- **Typography**: `fontSize`, `fontFamily`, `fontWeight`, `fontStyle`, `color`,
  `lineHeightMultiplier`, `letterSpacingPx`
- **Position**: `textAlign`, `anchor` (`top`/`bottom`), `topPercent`,
  `leftPercent`, `rightPercent` — percentages of the frame, works at any
  resolution
- **Readability**: `textShadowEnabled`, optional `textBackground` pill
  (color/padding/corner radius) for busy photo backgrounds
- **Animation**: `entrance` (`fade`, `slide-up`, `slide-down`, `slide-left`,
  `slide-right`, `scale`, `typewriter`, `none`), `exit` (`fade`, `slide-up`,
  `slide-down`, `none`), independent `entranceDurationSeconds` /
  `exitDurationSeconds`
  - Conversation (`person`/`jesus`) defaults to a plain fade in → hold →
    fade out — no bounce, no slide, no typewriter.
  - `engagement` (the comment-CTA line) defaults to `typewriter` — it's the
    one line meant to draw the eye.

> `reference`'s own style fields (color, font size) are **not** used for
> rendering any more — see "The Bible verse block" below. They're kept only
> so old episode data still validates.

### Background
`image`, `zoomEnabled` + `zoomFromScale`/`zoomToScale` (Ken Burns), optional
`overlayEnabled`/`overlayColor` wash, `bottomLogo`.

### Audio
`track`, `volume`, `loopIfShorterThanVideo`, `fadeInSeconds`, `fadeOutSeconds`.

### Timing
- `wordsPerSecond` / `minLineSeconds` — auto-timing model (or set
  `durationInSeconds` on any line to override it)
- `gapSeconds` between reveals, `endPaddingSeconds` of hold time at the end
- `revealMode`:
  - `"cumulative-pairs"` (default) — person's line shows alone, then Jesus's
    reply joins it, then it clears for the next exchange. The person's text
    stays mounted continuously across the join (see "Continuity fix" below)
    — it never re-fades when the reply appears.
  - `"one-at-a-time"` — every line shown alone in sequence
  - `"all-at-once"` — the whole script appears together (a still quote-card)

### Video
`widthPx`, `heightPx`, `fps`.

## The Bible verse block

The verse, its reference, and its version render as **one cohesive card**
(`src/BibleVerseBlock.tsx`), not three independent pieces:

```
"For where two or three are gathered
 together in my name, there am I in
 the midst of them."
 ────────────                        <- thin gold divider
    MATTHEW 18:20                     <- small-caps, letter-spaced, gold
        KJV                          <- smaller gold tag
```

Two things make this work correctly, both fixed as real bugs during
development — worth knowing if you're editing this component or `timeline.ts`:

1. **Timing**: `src/timeline.ts`'s `buildRevealFrames` buffers the verse
   until its `reference` line arrives, then pushes both together for their
   *combined* duration. Without this, the verse would show alone first and
   the reference would "join" later, reading as a separate scene.
2. **Layout**: verse → divider → reference → version render in one normal
   document flow inside `BibleVerseBlock`, not as two independently
   absolutely-positioned boxes. That's what keeps the gap between them
   fixed and small instead of an unpredictable dead space. The verse's
   `fitFontSizeToBox` call reserves a fixed pixel budget for the
   divider+reference+version *before* sizing the verse text, so a long
   verse still can't push the citation (or itself) past the character-safe
   line (`src/safeArea.ts`).

Author the actual verse text and reference **once**, in `video.bible` /
`bible` (never duplicate it in the scene text) — both the legacy adapter
(`scriptAdapter.ts`'s `formatBibleRef`) and the new CLI (`episodeInput.ts`)
build the on-screen `"Book ch:vs\nVERSION"` reference string from it.

## Continuity fix (person/jesus reveal)

Two fixes in `src/timeline.ts` work together so the person's line never
visibly flickers when Jesus's reply joins it:

1. **No gap on the join.** In `buildRevealFrames`, a person line immediately
   followed by a `jesus` line pushes with `gapAfter: false` — the join
   frame starts exactly where the person-alone frame ends, no matter what
   `timing.gapSeconds` is configured to. `gapSeconds` is breathing room
   *between* exchanges, not *inside* one; without this, the new CLI's
   default `gapSeconds` (0.35s, since it exposes no `timing` override — see
   INPUT.md) put real dead air between "person alone" and "person+jesus",
   which is exactly what reintroduced the bug below in practice.
2. **No remount across the (now gap-free) join.** `toSpeakerSegments()`
   collapses a speaker's entries across adjacent reveal frames into one
   continuous segment whenever the text is unchanged and there's no gap
   between them. Without it, `Episode.tsx` would mount a fresh `<Sequence>`
   (and thus a fresh entrance animation) for the person's line the instant
   Jesus's reply joined it — a visible fade-out/fade-in flicker on text
   that hadn't actually changed. `Episode.tsx` renders one `<Sequence>` per
   *segment*, not per reveal frame, so unchanged text never remounts and
   only genuinely new text gets a fresh entrance.

Both matter: (1) alone still leaves a remount at zero distance (a
one-frame flicker); (2) alone only works if frames happen to be
contiguous, which isn't guaranteed unless `gapSeconds` is 0.

## Character-safe area (`src/safeArea.ts`)

All text positioning is anchored off measured constants, not hand-picked
pixels, so any script's dialogue/verse/citation — however long —
structurally stops short of the characters:

- `CHARACTER_TOP_PERCENT` (55.4%) — measured from `public/backgrounds/boy/boy_1.png`
- `SAFE_LINE_PERCENT` (42%) — the dialogue/reference floor, well clear of
  the characters on purpose (a visible gap, not just barely clear)
- `TOP_MARGIN_PERCENT` (9%) — ceiling for how far bottom-anchored text may
  grow up
- `VERSE_TOP_PERCENT` (14%) / `SAFE_CONTENT_BOTTOM_PERCENT` (37%) — the
  verse's own region, growing down, capped short of the dialogue floor

If the background art ever changes, re-measure and update
`CHARACTER_TOP_PERCENT`/`SAFE_LINE_PERCENT` — nothing else needs to change.

## Project structure

```
src/
  schema.ts            -- single source of truth: every field, type, range, default
  animations.ts         -- entrance/exit choice -> per-frame opacity/transform
  textFit.ts            -- shrink-to-fit font sizing via Canvas text measurement
  safeArea.ts            -- character-safe positioning constants
  timeline.ts             -- script -> timed "reveal frames" (+ per-speaker
                              continuity segments) per revealMode
  fonts.ts               -- Google Fonts (Lora for dialogue, Anton for titles)
  assetResolver.ts        -- character/topic/emotion -> background art, music type -> file
  Background.tsx          -- fixed (opt-in zoom) background + optional overlay + bottom logo
  TextBlock.tsx            -- one speaker's text: typography/position/shadow/anim
  BibleVerseBlock.tsx       -- verse+divider+reference+version as one cohesive card
  EndCard.tsx              -- closing brand card (logo + CTA lines)
  Episode.tsx               -- wires background + reveal segments + audio together
  Thumbnail.tsx             -- static title-card still, same safe-area ceiling
  Root.tsx                 -- registers "Episode"/"Thumbnail" compositions
  scriptAdapter.ts          -- legacy Script (absolute timestamps) -> Episode
  socialMeta.ts             -- legacy pipeline only: IG/YouTube captions
  episodes/porch_conversation.json -- example episode (Studio's default props)
scripts/
  cli.ts                  -- new CLI entry point (render / batch)
  lib/episodeInput.ts       -- simple input schema + bible_verse expansion + style merge
  lib/csv.ts                -- CSV parser for batch mode
  lib/renderEpisode.ts       -- shared write-props + `remotion render`/`still`
  build-episode.ts          -- legacy pipeline entry (Script -> video+thumb+social)
  examples/JR-0001.json      -- example legacy Script input (absolute timestamps)
  examples/JR-0002.json       -- example new-CLI input (simple lines, bible_verse marker)
  check-*.ts                -- self-checks for timeline.ts/episodeInput.ts logic
public/
  backgrounds/boy/, backgrounds/girl/ (boy_1.png, boy_1_sad.png, ...),
  audio/hallelujah.mp3, branding/{bottom,follow}.png
out/                       -- legacy build-episode.ts output (git-ignored): <id>.mp4,
                              <id>-thumb.png, <id>.episode-props.json, <id>.thumbnail-props.json
output/                    -- npm run jr render output (git-ignored, default --out-dir):
                              videos/<id>.mp4, thumbnails/<id>-thumb.png,
                              props/<id>.episode-props.json, props/<id>.thumbnail-props.json
```

## Why this approach

- **One schema, enforced.** `EpisodeSchema` is validated with zod at render
  time — a typo'd field or invalid value (`entrance: "bounce"`) fails
  immediately with a clear error instead of silently rendering wrong.
- **Studio controls come for free.** Because it's a zod schema, Remotion
  Studio renders real UI controls (sliders, color pickers, dropdowns) for
  every field with no extra work.
- **Defaults mean less typing.** A CLI episode needs only `id`, `title`,
  and `lines`; everything else — position, color, animation, background —
  falls back to the curated defaults in `src/schema.ts`.
- **No hardcoded pixels.** Every position is a percentage, so the same
  episode renders correctly at any `widthPx`/`heightPx`.

## Next step: distribution

Once episodes are rendered, the natural next step is scheduling them
across YouTube Shorts / Instagram Reels / Facebook Reels via Buffer — ask
when you're ready to wire that up.

## Bible Verse Post Tool

A separate, isolated pipeline that posts a daily Bible verse card — it does
not touch the Episode/Thumbnail rendering above. It picks a verse, renders a
3:4 still with the same `BibleVerseBlock`/logo/brand look, and publishes it
to Instagram through Buffer, fully unattended, every day at 6:30 AM IST.

**Pieces:**
- `scripts/bible.json` — 365 curated promises/blessings (NIV wording), one
  per day of the year — deliberately no narrative/story verses, every entry
  is meant to stand alone and invite a reaction.
- `scripts/get-bible-verse.ts` — picks that day's entry from `bible.json` by
  day-of-year (local data, no network call).
- `src/BibleVersePost.tsx` (+ `BibleVersePostPropsSchema` in `src/schema.ts`,
  registered as the `BibleVersePost` Still in `src/Root.tsx`) — the 3:4
  (1080x1440) card.
- `scripts/publish-buffer.ts` — creates a Buffer update on one channel.
- `scripts/daily-bible-post.ts` — orchestrates all of the above, saves the
  rendered image to `output/bible_verse/`, uploads it as a GitHub Release
  asset (so Buffer has a public URL to fetch it from), and records the date
  in `data/bible-post-state.json` so the same day never posts twice.
- `.github/workflows/daily-bible-post.yml` — runs it daily at 6:30 AM IST
  (01:00 UTC cron), plus a manual `workflow_dispatch` (with a `force` input
  to bypass the dedupe check) for testing.

**Setup:**
1. Get a Buffer **GraphQL API key** from Buffer's account/API settings
   (`developers.buffer.com`) — the old REST/OAuth access token is deprecated
   and is rejected outright by `createPost`, so it must be a key issued for
   the GraphQL API.
2. Copy `.env.example` to `.env`, set `BUFFER_API_KEY` to that key, then run
   `npx tsx --env-file=.env scripts/list-buffer-channels.ts` to print every
   connected channel's GraphQL `id` — use your Instagram channel's `id` as
   `BUFFER_INSTAGRAM_CHANNEL_ID` (this id is not the same as the old REST
   profile id).
   (`BIBLE_API_KEY` is no longer required — verses come from `bible.json` —
   but it's left in place in case you want to swap the source back later).
3. Add these as **GitHub Secrets** (Settings → Secrets and variables →
   Actions) on this repo:
   - `BUFFER_API_KEY`
   - `BUFFER_INSTAGRAM_CHANNEL_ID`
4. The repo (or the release assets) must be reachable by Buffer's servers —
   keep it public, or the media URL Buffer fetches from will 404.
5. Test locally against your real `.env` values (Node/tsx don't auto-load
   `.env`, so pass it explicitly):
   ```
   npx tsx scripts/get-bible-verse.ts                        # verse pick only, no env needed
   npx tsx --env-file=.env scripts/list-buffer-channels.ts  # look up channel ids
   npx tsx --env-file=.env scripts/daily-bible-post.ts       # full pipeline
   ```
   The full pipeline's release-upload step only works inside GitHub Actions
   where `gh` is authenticated (it needs `GITHUB_REPOSITORY` set) — run the
   workflow via **Actions → Daily Bible Verse Post → Run workflow** to test
   posting end-to-end. Locally you can still confirm the verse + rendered
   image (saved to `output/bible_verse/`) look right before that.

**Adding/editing verses:** just edit `scripts/bible.json` — each entry is
`{ "id", "reference", "text" }`; the day-of-year rotation picks by array
index, so appending entries at the end never reshuffles past dates.
