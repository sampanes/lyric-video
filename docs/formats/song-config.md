# Song Config

This document defines the default shape of `songs/<song_name>/song.json`.

The schema should stay evolvable, but the repo needs a stable starting point.

## Purpose

The song config is the source of truth for:

- song metadata
- file locations
- timing source references
- visual style choices
- render settings
- background strategy
- song vibe notes

## Suggested v1 Shape

```json
{
  "id": "template_song",
  "title": "Template Song",
  "artist": "Unknown Artist",
  "song_vibes": "high energy, male vocalist, gritty bar-room feel",
  "style_prompt": "inputs/song_style_prompt.txt",
  "bpm": null,
  "audio": "inputs/audio/song.wav",
  "lyrics": "inputs/lyrics/lyrics.txt",
  "timing": {
    "raw": "timing/raw/",
    "reviewed": "timing/reviewed/timing.json"
  },
  "subtitle_style": "classic",
  "background_mode": "solid",
  "backgrounds": [],
  "output": {
    "directory": "exports/",
    "filename": "template_song.mp4",
    "targets": [
      "horizontal"
    ],
    "width": 1920,
    "height": 1080,
    "fps": 30
  }
}
```

## Notes

- Paths should be song-relative whenever possible.
- The config should not hardcode engine internals.
- The config should identify file groups, not duplicate file contents.
- Render settings should be explicit enough to reproduce a result later.
- `output.targets` is optional. If omitted, scripts default to `horizontal`.
  CLI `--targets` values override preset targets and `output.targets`.
- Presets under `presets/` may provide repeatable render defaults such as
  target, fps, layout, and subtitle font. They do not replace song-specific
  config fields.
- Optional `layout` can be set in `song.json`, supplied by a preset, or
  overridden with CLI `--layout`. Current values are `standard`, `fullscreen`,
  and `soft_scroll`.
- `song_vibes` should capture the vibe prompt or creative direction that helped
  generate or define the song.
- When config is created automatically, `song_vibes` can be seeded from
  bracketed lyric tags and `inputs/song_style_prompt.txt`.
- `style_prompt` points to the raw user-editable style prompt used later for
  image/background generation. Alias files such as `description.txt`,
  `song-vibes.txt`, `vibes.txt`, or `prompt.txt` are accepted during intake,
  but the template uses `inputs/song_style_prompt.txt`.
- `backgrounds` may be empty. When it is empty or points to no usable still,
  the basic renderer uses a solid generated background.
- `bpm` is optional. When known, it can drive future beat-synced background
  motion. If omitted, the pipeline should still render normally.
- If `title` is omitted during intake, default it to a Caps Version of the song
  folder name.

## Expected Pairings

- `audio` goes with `lyrics` and timing
- `title` goes with the song folder name when it is not explicitly supplied
- `song_vibes` and optional `bpm` go with generated background assets
- `style_prompt` goes with image-generation prompt planning
- `timing.reviewed` goes with generated subtitles
- `inputs/video/` goes with raw source clips that should be preserved
- `backgrounds` goes with render-ready background metadata and assets under
  `assets/backgrounds/`
- `output.targets` goes with target-specific subtitles and exports
- `output` goes with render logs and render metadata

## Render Targets

Supported target names are documented in [Render Targets](./render-targets.md).

Current target names:

- `horizontal`
- `vertical`
- `square`
- `portrait`
