# Background music licences

Every track in this folder is an **original work made for Jesus Replies** (Selvin PaulRaj K),
created on 2026-10-16. Each one was synthesised from scratch by `scripts/audio/make_bgm.py`
(numpy/scipy: warm pads, a soft bass, a piano-like arpeggio and a simple reverb). No samples,
loops, presets or recordings by anyone else were used, so there is no third-party licence to
follow and nothing for Content ID to match. Re-running the script rebuilds the same tracks.

| File | Title | Length | Key / chords | Loudness |
| --- | --- | --- | --- | --- |
| bgm-01.mp3 | Quiet Porch | 64 s | D major, I-V-vi-IV | about -20 LUFS |
| bgm-02.mp3 | Morning Light | 72 s | G major, I-IV-vi-V | about -20 LUFS |
| bgm-03.mp3 | Still Waters | 68 s | E-flat major, vi-IV-I-V | about -20 LUFS |
| bgm-04.mp3 | Evening Prayer | 64 s | C major, IV-I-V-vi | about -20 LUFS |
| bgm-05.mp3 | Held | 72 s | F major, I-vi-ii-V | about -20 LUFS |

- Owner: Selvin PaulRaj K / Jesus Replies. All rights reserved by the owner; free to use in any
  Jesus Replies video on any platform.
- Each track loops seamlessly (the reverb tail is folded back onto the start).
- Rotation: `src/assetResolver.ts` `pickBgmTrack(episode id)` (FNV-1a hash of the id modulo the
  number of tracks), so an episode always gets the same track.

## Removed

- `hallelujah.mp3` was removed on 2026-10-16 (DEC-JR-007). It was another creator's
  "all rights reserved" audio and must never be added back.
- To add a track, it must be original or carry a written licence that allows commercial use on
  Instagram and YouTube; add a row above with its source and licence, then add it to `BGM_TRACKS`.
