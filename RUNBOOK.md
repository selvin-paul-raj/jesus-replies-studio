# Runbook

Operational, task-oriented companion to [README.md](README.md) (the
reference). Every command here has been run and verified against this
codebase. Copy-paste them.

## 0. Prerequisites

- Node.js 18+ (Node 24 verified).
- `npm install` once.
- First `preview`/`render`/`still` downloads a headless Chrome (~200MB,
  needs internet) — normal, one-time.
- You'll see a `zod` version-mismatch warning from Remotion on every render
  (`installed 3.25.76, required 4.5.4`). It's pre-existing/cosmetic — every
  render in this runbook completes fine despite it. Ignore it unless a
  render actually fails.

## 1. Preview live (best way to tune styles)

```bash
npm run preview
```

Opens Remotion Studio. Because the whole config is the `EpisodeSchema` zod
schema, Studio auto-builds sliders/color-pickers/dropdowns for every field —
drag one, watch the video update, no re-render. Default props come from
`src/episodes/porch_conversation.json`.

## 2. Render the default example (raw Remotion CLI)

```bash
npx remotion render src/index.ts Episode out/porch_conversation.mp4 \
  --props=src/episodes/porch_conversation.json
npx remotion still src/index.ts Thumbnail out/porch_conversation-thumb.png \
  --props=src/episodes/porch_conversation.json
```

Use this path when you already have a full `EpisodeProps`-shaped JSON
(everything under `src/schema.ts`'s `EpisodeSchema`) and just want to render
it directly — no CLI wrapper needed.

## 3. The new CLI — single episode from JSON

```bash
npm run jr -- render <input.json> [--out-dir output]
```

Minimal input (only `id`, `title`, `lines` are required):

```json
{
  "id": "JR-0002",
  "title": "Why do we pray?",
  "lines": [
    { "speaker": "person", "text": "Jesus, why do we pray?" },
    { "speaker": "jesus", "text": "Prayer is not a performance -- it is a conversation." },
    { "speaker": "engagement", "text": "How do you pray? Share below." }
  ]
}
```

Full input, showing every optional field:

```json
{
  "id": "JR-0002",
  "title": "Why do we pray?",
  "character": "boy",
  "topic": "prayer",
  "bible": {
    "book": "Matthew", "chapter": 6, "verse": 6, "version": "KJV",
    "text": "But thou, when thou prayest, enter into thy closet..."
  },
  "lines": [
    { "speaker": "person", "text": "Jesus, why do we pray?" },
    { "speaker": "jesus", "text": "Prayer is not a performance -- it is a conversation." },
    { "speaker": "bible_verse" },
    { "speaker": "engagement", "text": "How do you pray? Share below." }
  ],
  "styles": {
    "verse": { "color": "#2f4f3b" },
    "jesus": { "color": "#2f2f4f" }
  },
  "music": { "type": "soft_christian_instrumental", "volume": 0.18 },
  "finalLogo": { "image": "branding/follow.png", "ctaLabel": "Follow for more" }
}
```

Field notes:
- **`character`/`topic`** — pick background art via
  `public/backgrounds/<character>_<topic>.png`, falling back to
  `<character>.png`, then `boy.png` (with a console warning). Default
  `character: "boy"`, `topic: "general"`.
- **`bible`** — optional. If your script has no verse, omit it and never
  use a `"bible_verse"` line.
- **`"bible_verse"` line** — a *position marker only*, no `text` field.
  It expands into a real `verse` line (`bible.text`) + `reference` line
  (`"Book ch:vs\nVERSION"`, built from `bible`) at that point in the
  conversation. **Never write the verse text into `lines` yourself** — it
  lives once, in `bible.text`.
- **`styles`** — optional, per-speaker partial overrides (any field from
  `src/schema.ts`'s `SpeakerStyleSchema`: color, fontSize, entrance/exit
  animation, position, ...). Only the fields you name change; everything
  else keeps the curated default (position/anchor won't reset).
- **`music`** — `type` maps through `src/assetResolver.ts`'s
  `resolveMusicFile` (currently only `"soft_christian_instrumental"` ->
  `audio/hallelujah.mp3`); or set `track` directly to a `public/` path.
  Defaults to `hallelujah.mp3` at volume 1 if omitted.
- **`finalLogo`** — defaults to the follow end card (`branding/follow.png`,
  "Stay with Jesus" / "Carry this with you"). Include a partial `finalLogo`
  object to override just the fields you name (e.g. `ctaLabel` only).

Run it:

```bash
npm run jr -- render my-episode.json
# -> output/JR-0002.mp4, output/JR-0002-thumb.png,
#    output/props/JR-0002.episode-props.json, output/props/JR-0002.thumbnail-props.json
```

A full working example matching this shape lives at
`scripts/examples/JR-0002.json` — run
`npm run jr -- render scripts/examples/JR-0002.json` directly to see it.

> **Gotcha**: `styles` only accepts the real `SpeakerStyleSchema` field
> names from `src/schema.ts` (`entrance`/`exit`, not `animation`). Zod
> silently drops any key it doesn't recognize — no error, no warning — so
> a typo'd field name just does nothing. If a style override doesn't seem
> to take effect, check `output/props/<id>.episode-props.json` after rendering:
> the field you meant to set should show your value there, not a default.
>
> **Known limitation**: this input has no way to override `timing`
> (`gapSeconds`, `wordsPerSecond`, `minLineSeconds`, `endPaddingSeconds`,
> `revealMode`) — every CLI-built episode uses format A's defaults
> (`gapSeconds: 0.35`, `revealMode: "cumulative-pairs"`, ...). This is safe
> for the person→jesus join specifically (`timeline.ts` always keeps that
> join gap-free regardless of `gapSeconds`), but if you need a different
> `revealMode` or timing model, hand-edit the written
> `output/props/<id>.episode-props.json` and re-render it directly (§2) instead.

## 4. The new CLI — batch from CSV

```bash
npm run jr -- batch <input.csv> [--out-dir output]
```

Columns:

```
id, title, character, topic,
bible_book, bible_chapter, bible_verse, bible_version, bible_text,
scenes, styles
```

`scenes` and `styles` are **JSON-encoded cells** — same shapes as `lines`/
`styles` in the JSON input above. A row with no Bible verse just leaves
`bible_book`..`bible_text` empty and has no `"bible_verse"` entry in `scenes`.

Example file (`episodes.csv`):

```csv
id,title,character,topic,bible_book,bible_chapter,bible_verse,bible_version,bible_text,scenes,styles
JR-0002,"Why, Lord, do we forgive?",boy,forgiveness,Matthew,6,14,KJV,"For if ye forgive men their trespasses, your heavenly Father will also forgive you.","[{""speaker"":""person"",""text"":""Why do we have to forgive, Lord?""},{""speaker"":""jesus"",""text"":""Because you were forgiven first.""},{""speaker"":""bible_verse""},{""speaker"":""engagement"",""text"":""Who do you need to forgive today?""}]","{""verse"":{""color"":""#4b2f5c""}}"
JR-0003,"What is faith?",boy,faith,,,,,,"[{""speaker"":""person"",""text"":""What does it even mean to have faith?""},{""speaker"":""jesus"",""text"":""It means trusting what you cannot yet see.""},{""speaker"":""engagement"",""text"":""What are you trusting God for right now?""}]",
```

CSV quoting rules (standard RFC4180 — the parser handles all of this):
- Wrap any field containing a comma in double quotes.
- Escape a literal `"` inside a quoted field as `""`.
- A JSON blob (`scenes`, `styles`) is just a normal quoted field — its own
  `"` characters get doubled per the rule above. Easiest to build these
  cells in Excel/Sheets/a script rather than typing the escaping by hand.

Run it:

```bash
npm run jr -- batch episodes.csv
# [jr] done: out/JR-0002.mp4 / out/JR-0002-thumb.png
# [jr] done: out/JR-0003.mp4 / out/JR-0003-thumb.png
# [jr] batch done: 2 succeeded, 0 failed
```

A bad row (invalid JSON in a cell, missing required field, unknown
speaker...) is **skipped with an error printed for that row** — the rest of
the batch still runs. The process exits non-zero if any row failed, so a CI
job can detect it; check the printed `[jr] FAILED row "<id>": ...` lines to
see which ones.

## 5. Legacy script pipeline (absolute timestamps + social captions)

Use this only for scripts that already have real `start`/`end` timestamps
per scene (e.g. from an upstream authoring tool) and where you also want
`.social.json` (Instagram/YouTube captions) generated.

```bash
npm run build-episode -- scripts/examples/JR-0001.json
# -> out/JR-0001.mp4, out/JR-0001-thumb.png,
#    out/JR-0001.episode-props.json, out/JR-0001.thumbnail-props.json,
#    out/JR-0001.social.json
```

Input shape (`src/scriptAdapter.ts`'s `ScriptSchema`) — see
`scripts/examples/JR-0001.json` for a full working example. Key
differences from the new CLI's input:
- `video.scenes[]` need absolute `start`/`end` seconds, not just text.
- A `"bible_verse"` scene *can* carry its own `text`, but `video.bible.text`
  always wins if present — never duplicate the verse in both places.
- A `"brand"` scene's duration accumulates into the closing `finalLogo`
  card's `durationSeconds` automatically.
- No `styles` override support — every episode uses `src/schema.ts`'s
  defaults as-is.

## 6. Verifying a change before you call it done

Run all three before shipping any edit to `src/timeline.ts`,
`src/BibleVerseBlock.tsx`, `src/Episode.tsx`, or `scripts/lib/episodeInput.ts`:

```bash
npx tsc --noEmit                        # typecheck everything
npx tsx scripts/check-bible-merge.ts       # verse+reference show together, once
npx tsx scripts/check-speaker-continuity.ts # person/jesus don't remount OR gap on join (incl. gapSeconds > 0)
npx tsx scripts/check-cli-input.ts          # CSV parsing + bible_verse expansion + style merge
```

All four should print `OK`/`No errors found`. Then spot-check visually —
render (or re-render) the episode and pull a couple of stills at meaningful
frames instead of trusting the numbers alone:

```bash
npx remotion still src/index.ts Episode out/check.png \
  --props=out/JR-0001.episode-props.json --frame=1000
```

Pick `--frame` from the actual timeline: with `gapSeconds: 0`, frame =
`fps * (sum of every prior line's durationInSeconds)`; add a few frames to
land mid-hold rather than exactly on a cut. Delete the check-*.png stills
afterward — they're scratch, not deliverables.

## 7. Adding new assets

- **Background art**: drop `public/backgrounds/<character>.png` (or
  `<character>_<topic>.png` for a topic-specific variant) at roughly the
  1080×1920 aspect ratio. If the composition/character silhouette differs
  meaningfully from `boy.png`, re-measure `CHARACTER_TOP_PERCENT` in
  `src/safeArea.ts` (scan the image for the first non-sky pixel) — every
  text block's growth ceiling derives from that one constant.
- **Music**: drop the file in `public/audio/`, add a `type -> path` entry
  in `MUSIC_TYPE_FILES` in `src/assetResolver.ts`, or just pass `music.track`
  directly (new CLI) pointing at the `public/` path.
- **Branding**: `public/branding/bottom.png` (persistent bottom-of-frame
  logo) and `follow.png` (end-card logo) — swap in place, same filenames.

## 8. Command cheat-sheet

```bash
npm install                                          # one-time setup
npm run preview                                       # Remotion Studio

npx remotion render src/index.ts Episode out/x.mp4 --props=path.json    # raw render
npx remotion still  src/index.ts Thumbnail out/x-thumb.png --props=path.json

npm run jr -- render <input.json> [--out-dir output]      # new CLI, single
npm run jr -- batch  <input.csv>  [--out-dir output]       # new CLI, batch

npm run build-episode -- <script.json>                  # legacy pipeline (+ social.json)

npx tsc --noEmit                                        # typecheck
npx tsx scripts/check-bible-merge.ts                      # self-checks
npx tsx scripts/check-speaker-continuity.ts
npx tsx scripts/check-cli-input.ts
```
