# Render Targets

Render targets define the output aspect ratio, resolution, export suffix, and
subtitle layout rules for platform-specific lyric videos.

## Supported Targets

| Target | Ratio | Resolution | Export suffix | Typical use |
| --- | --- | --- | --- | --- |
| `horizontal` | `16:9` | `1920x1080` | `horizontal` | YouTube, TV |
| `vertical` | `9:16` | `1080x1920` | `vertical` | Shorts, TikTok, Reels |
| `square` | `1:1` | `1080x1080` | `square` | Instagram feed, previews |
| `portrait` | `4:5` | `1080x1350` | `4x5` | Instagram and Facebook feed |

Aliases such as `16:9`, `9:16`, `1:1`, and `4x5` are accepted by the scripts,
but docs and config should prefer the named target values.

## Commands

Render one target:

```powershell
python scripts\make_videos.py "song name" --targets vertical
```

Render all targets:

```powershell
python scripts\make_videos.py "song name" --targets all
```

Run WhisperX first, then render all targets:

```powershell
python scripts\make_videos.py "song name" --refresh-whisper --targets all
```

## Output Files

The current naming convention is:

- `exports/song-name.horizontal.mp4`
- `exports/song-name.vertical.mp4`
- `exports/song-name.square.mp4`
- `exports/song-name.4x5.mp4`

Subtitles are generated per target:

- `subtitles/lyrics.horizontal.ass`
- `subtitles/lyrics.vertical.ass`
- `subtitles/lyrics.square.ass`
- `subtitles/lyrics.4x5.ass`

`subtitles/lyrics.ass` is still written as a horizontal compatibility copy.

## Text Rules

The lyrics source of truth remains the reviewed timing file, whose text comes
from the authoritative lyric input. Whisper or WhisperX text is not used as the
rendered lyric source.

Each target gets its own ASS subtitle file because line wrapping, font sizing,
and safe margins are aspect-ratio dependent.

Current layout defaults:

- 10 percent left and right margin
- up to two rendered text lines per lyric segment
- target-specific bottom margin
- dynamic font reduction for unusually long lines

## Background Rules

If `song.json` points to an existing image in `backgrounds`, the basic renderer
uses that image and center-crops it to fill the selected target without
stretching.

If no background image exists, the renderer uses a generated dark solid color.

ComfyUI source video clips should first land in `inputs/video/`. Processed,
target-aware, renderer-ready stills or loops should live in
`assets/backgrounds/`, ideally with the same prompt and seed across aspect
ratios where possible.
