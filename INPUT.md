# Input Formats

This project accepts **three** distinct input shapes, each a zod schema.
This file is the exhaustive field-by-field reference for all three; see
[RUNBOOK.md](RUNBOOK.md) for how to actually invoke each one, and
[README.md](README.md) for the high-level picture.

| Format | Schema | Defined in | Consumed by |
|---|---|---|---|
| A. Raw episode props | `EpisodeSchema` / `EpisodePropsSchema` | `src/schema.ts` | Remotion Studio, `remotion render`/`still` directly |
| B. Simple CLI input (JSON or CSV) | `EpisodeInputSchema` | `scripts/lib/episodeInput.ts` | `npm run jr -- render` / `batch` |
| C. Legacy script (absolute timestamps) | `ScriptSchema` | `src/scriptAdapter.ts` | `npm run build-episode` |

B and C both compile down into A before anything renders — A is the only
shape Remotion itself ever sees.

---

## A. Raw episode props (`EpisodeSchema`)

The renderer's own native shape. Pass this directly to `remotion render`/
`still --props=`, or as `defaultProps` in `src/Root.tsx`. Every field below
lives in `src/schema.ts`; `zod` validates it at render/Studio-load time —
an invalid value (e.g. `entrance: "bounce"`) fails immediately with a clear
error, and Remotion Studio auto-builds a UI control per field.

### Top level (`EpisodeSchema`)

| Field | Type | Default | Notes |
|---|---|---|---|
| `title` | `string` | `"Untitled Episode"` | Also drives the Thumbnail's title text when built via B/C |
| `video` | `VideoConfig` | `{}` | see below |
| `background` | `BackgroundConfig` | — required | see below |
| `audio` | `AudioConfig` | — required | see below |
| `timing` | `TimingConfig` | `{}` | see below |
| `styles` | `Styles` | `{}` | per-speaker style, see below |
| `lines` | `ScriptLine[]` | — required | the actual script, see below |
| `finalLogo` | `FinalLogoConfig` | *(omit for no end card)* | see below |

`EpisodePropsSchema` extends this with one runtime-only field:
`audioDurationInFrames: number` (default `0`) — always recomputed from the
real audio file by `calculateMetadata` in `src/Root.tsx`, so whatever you
write here is ignored; never set it yourself.

### `video` (`VideoConfigSchema`)

| Field | Type | Default |
|---|---|---|
| `widthPx` | `number` | `1080` |
| `heightPx` | `number` | `1920` |
| `fps` | `number` | `30` |

### `background` (`BackgroundConfigSchema`)

| Field | Type | Default |
|---|---|---|
| `image` | `string` | — required (a `public/` path, or an `http(s)://` URL) |
| `zoomEnabled` | `boolean` | `true` |
| `zoomFromScale` | `number` (1–2) | `1` |
| `zoomToScale` | `number` (1–2) | `1.12` |
| `overlayEnabled` | `boolean` | `false` |
| `overlayColor` | color string | `"#00000000"` |
| `bottomLogo` | `string` (optional) | *(none)* — persistent bottom-of-frame logo |

### `audio` (`AudioConfigSchema`)

| Field | Type | Default |
|---|---|---|
| `track` | `string` | — required |
| `volume` | `number` (0–1) | `1` |
| `loopIfShorterThanVideo` | `boolean` | `true` |
| `fadeInSeconds` | `number` (0–5) | `1` |
| `fadeOutSeconds` | `number` (0–5) | `1.5` |

### `timing` (`TimingConfigSchema`)

| Field | Type | Default |
|---|---|---|
| `wordsPerSecond` | `number` (0.5–10) | `2.3` |
| `minLineSeconds` | `number` (0.5–10) | `2.2` |
| `gapSeconds` | `number` (0–3) | `0.35` |
| `endPaddingSeconds` | `number` (0–10) | `2` |
| `revealMode` | `"cumulative-pairs"` \| `"one-at-a-time"` \| `"all-at-once"` | `"cumulative-pairs"` |

Auto-timing: a line with no `durationInSeconds` gets
`max(minLineSeconds, wordCount / wordsPerSecond)`.

`revealMode`:
- `"cumulative-pairs"` — person's line alone, then Jesus's reply joins it,
  then clears. Person's text never remounts/re-fades when the reply joins
  (`toSpeakerSegments` in `src/timeline.ts`). Verse+reference always show
  together as one block, never sequentially (same file).
- `"one-at-a-time"` — every line shown alone.
- `"all-at-once"` — the whole script together (a still quote-card).

### `styles` (`StylesSchema`) — one `SpeakerStyleSchema` per speaker

Keys: `person`, `jesus`, `verse`, `reference`, `engagement`. Every field
below applies to each; the *defaults differ per speaker* (curated cluster
layout) — see the "curated defaults" table after.

| Field | Type | Generic default |
|---|---|---|
| `fontSize` | `number` (10–200) | `52` |
| `fontFamily` | `string` | Lora (`dialogueFontFamily`) |
| `fontWeight` | `"normal"` \| `"bold"` | `"bold"` |
| `fontStyle` | `"normal"` \| `"italic"` | `"normal"` |
| `color` | color string | `"#3b2f2f"` |
| `lineHeightMultiplier` | `number` (1–3) | `1.3` |
| `letterSpacingPx` | `number` (-5–20) | `0` |
| `textAlign` | `"left"` \| `"right"` \| `"center"` | `"center"` |
| `anchor` | `"top"` \| `"bottom"` | `"top"` |
| `topPercent` | `number` (0–100) | `30` |
| `leftPercent` | `number` (0–100) | `7` |
| `rightPercent` | `number` (0–100) | `7` |
| `textShadowEnabled` | `boolean` | `true` |
| `textBackground` | `{enabled, color, paddingPx, borderRadiusPx}` | disabled pill, see below |
| `entrance` | `"none"\|"fade"\|"slide-up"\|"slide-down"\|"slide-left"\|"slide-right"\|"scale"\|"typewriter"` | `"fade"` |
| `exit` | `"none"\|"fade"\|"slide-up"\|"slide-down"` | `"fade"` |
| `entranceDurationSeconds` | `number` (0–6) | `0.35` |
| `exitDurationSeconds` | `number` (0–3) | `0.25` |

`textBackground`: `{enabled: false, color: "#00000055", paddingPx: 20, borderRadiusPx: 16}`.

**Curated per-speaker defaults** (only the fields each speaker overrides from the generic table above):

| Speaker | anchor | topPercent | leftPercent | rightPercent | fontSize | fontStyle | entrance | entranceDurationSeconds | exitDurationSeconds |
|---|---|---|---|---|---|---|---|---|---|
| `person` | bottom | 42 (`SAFE_LINE_PERCENT`) | 4 | 56 | 52 | normal | fade | 0.35 | 0.25 |
| `jesus` | bottom | 42 | 56 | 4 | 52 | normal | fade | 0.35 | 0.25 |
| `verse` | top | 14 (`VERSE_TOP_PERCENT`) | 7 | 7 | 52 | **italic** | **slide-up** | **0.5** | 0.25 |
| `reference` | bottom | 42 | 7 | 7 | **30** | normal | fade | 0.35 | 0.25 |
| `engagement` | bottom | 42 | 7 | 7 | **44** | normal | **typewriter** | **1.6** | **0.4** |

> `reference`'s own style is **not actually used for rendering** — the
> verse+reference+version render together as one composed card
> (`src/BibleVerseBlock.tsx`, fixed gold-divider design, not schema-driven).
> `reference`'s entry above is kept only for backward-compatible validation
> of older episode data.

### `lines` (`ScriptLineSchema[]`)

| Field | Type | Notes |
|---|---|---|
| `speaker` | `"person"\|"jesus"\|"verse"\|"reference"\|"engagement"` | |
| `text` | `string` | required, non-empty |
| `durationInSeconds` | `number` (optional) | overrides auto-timing for this line |

A `verse` line and the `reference` line immediately after it are always
displayed together (see `revealMode` note above) — write the full verse
text once, in the `verse` line, and the citation (`"Book ch:vs\nVERSION"`)
in the `reference` line that follows it.

### `finalLogo` (`FinalLogoConfigSchema`, optional)

| Field | Type | Default |
|---|---|---|
| `image` | `string` | — required if `finalLogo` is present at all (no fallback) |
| `durationSeconds` | `number` (0–10) | `3` |
| `ctaLabel` | `string` | `"Follow for more Bible conversations"` |
| `secondaryCtaLabel` | `string` (optional) | *(none — single CTA line)* |

### Full example

See `src/episodes/porch_conversation.json` (every field set explicitly) or
`out/*.episode-props.json` after any render — both are valid `EpisodeProps`
you can pass straight back to `remotion render --props=`.

### `ThumbnailPropsSchema` (the `Thumbnail` still)

| Field | Type |
|---|---|
| `title` | `string` |
| `image` | `string` (same background path convention as above) |

---

## B. Simple CLI input (`EpisodeInputSchema`)

The friendliest format — what `npm run jr -- render <file.json>` and
`npm run jr -- batch <file.csv>` both consume (a CSV row is mapped into
this exact shape, field-for-field, before rendering). Only `id`, `title`,
`lines` are required; everything else is optional and falls back to A's
curated defaults.

| Field | Type | Default | Notes |
|---|---|---|---|
| `id` | `string` (non-empty) | — required | used for `out/<id>.*` filenames |
| `title` | `string` | — required | |
| `character` | `string` | `"boy"` | background-art lookup key |
| `topic` | `string` | `"general"` | background-art lookup key |
| `background` | partial `BackgroundConfig` | *(auto-resolved)* | any field overrides the auto-resolved one; `image` auto-picks `backgrounds/<character>_<topic>.png` → `<character>.png` → `boy.png` |
| `bible` | `{book, chapter, verse, version?, text}` (optional) | *(none)* | `chapter`/`verse` accept `number` or `string`; `text` is the full verse — the single source of truth |
| `lines` | `EpisodeInputLine[]` (min 1) | — required | see below |
| `styles` | partial per-speaker overrides (optional) | *(curated A defaults)* | any `SpeakerStyleSchema` field, per speaker (`person`/`jesus`/`verse`/`reference`/`engagement`); merged **on top of** the curated defaults (position/anchor never reset by a partial override) |
| `music` | `{type?, track?, volume}` (optional) | `hallelujah.mp3` @ volume 1 | `type` resolves via `assetResolver.resolveMusicFile`; `track` is a direct `public/` path and wins if both given |
| `finalLogo` | full `FinalLogoConfig` (optional) | *(no end card)* | `image` required if present at all |

### `lines[]` (`EpisodeInputLineSchema`)

| Field | Type | Notes |
|---|---|---|
| `speaker` | `"person"` \| `"jesus"` \| `"bible_verse"` \| `"engagement"` | note: **no** `"verse"`/`"reference"` here — see below |
| `text` | `string` (optional) | required for every speaker except `"bible_verse"` |
| `durationInSeconds` | `number` (optional) | overrides auto-timing |

`"bible_verse"` is a **position-only marker**: no `text` field. At that
point in `lines`, it expands into a real `verse` line (`bible.text`) + a
`reference` line (`formatBibleRef(bible)` → `"Book ch:vs\nVERSION"`).
Using it requires a top-level `bible` object — an episode with no verse
just never includes a `"bible_verse"` line.

### Full JSON example

```json
{
  "id": "JR-0002",
  "title": "Why do we pray?",
  "character": "boy",
  "topic": "prayer",
  "bible": {
    "book": "Matthew", "chapter": 6, "verse": 6, "version": "KJV",
    "text": "But thou, when thou prayest, enter into thy closet, and when thou hast shut thy door, pray to thy Father which is in secret."
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

### CSV row mapping (batch mode)

One CSV row maps onto the same schema via these columns:

```
id, title, character, topic,
bible_book, bible_chapter, bible_verse, bible_version, bible_text,
scenes, styles
```

- `id`/`title`/`character`/`topic` → same-named fields (empty `character`/
  `topic` cells fall back to their defaults, same as JSON).
- `bible_book`..`bible_text` → assembled into the `bible` object; the row
  has no `bible` at all if `bible_book` is empty.
- `scenes` → **JSON-encoded** cell, same shape as `lines[]` above (including
  `"bible_verse"` markers).
- `styles` → **JSON-encoded** cell, same shape as `styles` above.

```csv
id,title,character,topic,bible_book,bible_chapter,bible_verse,bible_version,bible_text,scenes,styles
JR-0002,"Why, Lord, do we forgive?",boy,forgiveness,Matthew,6,14,KJV,"For if ye forgive men their trespasses, your heavenly Father will also forgive you.","[{""speaker"":""person"",""text"":""Why do we have to forgive, Lord?""},{""speaker"":""jesus"",""text"":""Because you were forgiven first.""},{""speaker"":""bible_verse""},{""speaker"":""engagement"",""text"":""Who do you need to forgive today?""}]","{""verse"":{""color"":""#4b2f5c""}}"
```

Standard CSV quoting: wrap any comma-containing field in `"..."`; a literal
`"` inside a quoted field is escaped as `""`.

---

## C. Legacy script (`ScriptSchema`, absolute timestamps)

For scripts that already come from an upstream tool with real scene
`start`/`end` timestamps (seconds from the start of the video), consumed by
`npm run build-episode -- <file.json>`. This is the only format that also
produces `.social.json` (Instagram/YouTube captions, via `src/socialMeta.ts`).

| Field | Type | Notes |
|---|---|---|
| `id` | `string` | used for `out/<id>.*` filenames |
| `video.duration` | `number` | informational only — a mismatch with the last scene's `end` prints a warning, doesn't fail |
| `video.language` | `string` (optional) | |
| `video.character` | `string` | e.g. `"boy"` — also accepted as a scene's own `speaker` value (back-compat) |
| `video.topic` | `string` | background-art lookup key |
| `video.title` | `string` | |
| `video.scenes` | `Scene[]` (min 1) | see below |
| `video.bible` | `{book, chapter, verse, version?, text?}` (optional) | `text` required only if a `"bible_verse"`/`"bible"` scene omits its own `text` |
| `video.music` | `{type, volume}` (optional) | `volume` defaults `1`; omit entirely for the default track |

### `video.scenes[]` (`SceneSchema`)

| Field | Type | Notes |
|---|---|---|
| `start` | `number` (≥0) | seconds |
| `end` | `number` (≥0) | seconds — `end - start` becomes the line's `durationInSeconds` |
| `speaker` | `string` | one of: `"person"` (or the literal `video.character` value), `"jesus"`, `"bible_verse"`/`"bible"`, `"reference"`, `"engagement"`, `"brand"` — anything else throws |
| `text` | `string` (optional) | required for `person`/`jesus`/`engagement`; optional for `bible_verse` (falls back to `video.bible.text`) and `reference` (falls back to `formatBibleRef(video.bible)`); ignored for `brand` |

`"brand"` scenes don't become a `lines[]` entry — their durations
accumulate into the generated `finalLogo.durationSeconds` (end card shown
for that long, using the fixed `follow.png` brand asset).

### Full example

`scripts/examples/JR-0001.json`:

```json
{
  "id": "JR-0001",
  "video": {
    "duration": 60,
    "language": "English",
    "character": "boy",
    "topic": "church",
    "title": "Why do we go to church?",
    "scenes": [
      { "start": 0, "end": 5, "speaker": "person", "text": "Jesus... why do we go to church every Sunday?" },
      { "start": 5, "end": 10, "speaker": "jesus", "text": "Do you think church is only a building?" },
      { "start": 10, "end": 17, "speaker": "person", "text": "Then why do we need to gather together?" },
      { "start": 17, "end": 28, "speaker": "jesus", "text": "Where two or three are gathered in My name, there am I with them." },
      { "start": 28, "end": 41, "speaker": "bible_verse", "text": "For where two or three are gathered together in my name, there am I in the midst of them." },
      { "start": 41, "end": 43, "speaker": "reference", "text": "Matthew 18:20 • KJV" },
      { "start": 43, "end": 52, "speaker": "engagement", "text": "What does church mean to you? Share your answer in the comments." },
      { "start": 52, "end": 60, "speaker": "brand", "text": "Jesus's Replies" }
    ],
    "bible": {
      "book": "Matthew", "chapter": 18, "verse": 20, "version": "KJV",
      "text": "For where two or three are gathered together in my name, there am I in the midst of them."
    },
    "music": { "type": "soft_christian_instrumental", "volume": 0.18 }
  }
}
```

Note: this file's `reference` scene writes its own text
(`"Matthew 18:20 • KJV"`, one line, mid-dot separator) instead of omitting
it and letting `formatBibleRef` generate `"Matthew 18:20\nKJV"` (two lines,
which is what actually renders in `BibleVerseBlock`). A scene's own
`text`, if non-empty, always wins over the generated one — prefer omitting
`text` on `reference` scenes so the current two-line citation format is
used automatically instead of the older single-line one.

### `video.character` vs. scene `speaker`

A scene's `speaker` matches `"person"` if it's literally `"person"` **or**
equals `video.character` (e.g. a scene with `"speaker": "boy"` when
`video.character` is `"boy"`) — supports older scripts that used the
character name as the person-speaker label.

---

## Which format should I use?

- **Writing a new episode by hand or in a spreadsheet** → format B (JSON or
  CSV via `npm run jr`). Least boilerplate, per-episode style overrides,
  batch support.
- **You already have a full `EpisodeProps` JSON** (e.g. from a previous
  render's `out/*.episode-props.json`, or hand-tuned in Studio) → format A,
  render it directly with `remotion render`/`still`.
- **Scripts come from an upstream tool with real scene timestamps and you
  need social captions** → format C, `npm run build-episode`.
