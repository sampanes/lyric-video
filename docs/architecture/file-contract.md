# File Contract

This document defines which files belong together in the lyric-video pipeline
and how song data should be organized on disk.

The main goal is to keep the repository flexible while still making the
relationships between files explicit.

## Principles

- Keep reusable engine code out of song folders.
- Keep song-specific inputs together.
- Keep raw capture, reviewed timing, and rendered outputs separate.
- Treat generated assets as reproducible artifacts with metadata.
- Allow a tracked template song later, while keeping real song workspaces local
  by default.

## Required Groupings

### 1. Song package root

Each song lives under `songs/<song_name>/`.

The song root should contain:

- `song.json` for high-level song metadata and render settings
- `inputs/` for source content
- `timing/` for raw, reviewed, and derived timing files
- `subtitles/` for generated subtitle files
- `assets/` for visual assets
- `renders/` for intermediate render outputs
- `exports/` for final deliverables
- `notes/` for human notes and work-in-progress context

The song root config is the source of truth for the song package.

### 2. Audio, lyrics, source video, and timing

These files are tightly related and should be kept within the same song
package.

Typical grouping:

- `inputs/audio/` for the source audio
- `inputs/lyrics/` for lyric text or reference lyric files
- `inputs/video/` for raw imported/user-provided source video clips, including
  ComfyUI exports before trimming, looping, cropping, or other post-processing
- `timing/raw/manual/` for human click captures
- `timing/raw/whisper/` for Whisper or WhisperX transcript artifacts
- `timing/raw/imported/` for external timing imports
- `timing/raw/automation/` for future automated capture output
- `timing/derived/lyrics_clean.txt` for machine-cleaned lyric text
- `timing/derived/lyrics_clean.json` for machine-cleaned lyric line metadata
- `timing/reviewed/` for normalized, trusted timing data

Rule of thumb:

- If you change the audio, expect to review timing again.
- If you change the lyric text, expect to review timing again.
- Raw timing should never be treated as the final source of truth.
- Transcription output is a candidate input, not the final lyric text.
- Original files under `inputs/` should not be rewritten by the pipeline.
- Machine-owned lyric cleanup belongs under `timing/derived/`.
- Raw source video clips under `inputs/video/` are preserved inputs, not
  renderer-ready assets.
- The user should not need to drag-drop generated media into these folders.
  Generators should be configured to write to the correct location, or scripts
  should place approved ad hoc media there.

### 3. Reviewed timing and subtitles

Reviewed timing and generated subtitles should live together conceptually even
if they are in different folders.

Typical grouping:

- `timing/reviewed/` for the authoritative timing source
- `subtitles/` for ASS or other subtitle outputs generated from reviewed timing

Rule of thumb:

- Subtitle files are derived artifacts.
- Target-specific subtitle files should be named like
  `lyrics.horizontal.ass`, `lyrics.vertical.ass`, `lyrics.square.ass`, and
  `lyrics.4x5.ass`.
- The reviewed timing file should be the thing you edit when a timing fix is
  needed.

### 4. Background assets and metadata

Generated backgrounds should travel with the metadata that explains how they
were made.

Typical grouping:

- `assets/backgrounds/` for render-ready background stills and processed video
  loops
- sidecar metadata files next to each asset, or a sibling metadata directory

Recommended sidecar pattern:

- `background_001.png`
- `background_001.json`
- `background_loop_001.mp4`
- `background_loop_001.json`

Raw ComfyUI or camera/source clips belong in `inputs/video/`. Cropped clips,
palindrome loops, selected final background loops, and other renderer-ready
background videos belong in `assets/backgrounds/`.

For normal automation, configure the generator or adapter to write to the
correct song package path directly. Use `scripts/import_media.py` only for
approved external media that already exists somewhere else.

The metadata should capture at least:

- source workflow or adapter
- prompt text or prompt reference
- seed
- model or checkpoint
- generation timestamp
- any post-processing notes

Recommended render metadata:

- keep a `renders/<render_id>.json` or similar metadata file for each render
- include the source config, subtitle version, and FFmpeg command
- include the render target name, ratio, width, and height when rendering
  multiple aspect ratios

### 5. Template song versus local songs

The repository may eventually include a tracked template song at
`songs/template_song/`.

That template should demonstrate:

- expected folder names
- sample config structure
- example timing files
- example subtitle outputs
- placeholder assets

Production songs should remain local workspace data and should be ignored by
default.

If a production song ever needs to be checked in, it should be an explicit
exception, not the default model.

## Suggested File Relationships

Use these pairings as the default mental model:

- `song.json` + `inputs/audio/` + `inputs/lyrics/` + `inputs/video/` = the
  source song package
- `timing/reviewed/` + `subtitles/` = the render-ready lyric timing layer
- `assets/backgrounds/` + metadata sidecars = generated visual assets
- target-specific `subtitles/` + `exports/` = platform-specific deliverables
- `renders/` + `exports/` = derived outputs that should not be manually edited

## Naming Guidance

- Prefer stable, machine-friendly filenames.
- Use zero-padded numbers for ordered sequences.
- Keep the same base name across related files when possible.

Example:

- `verse_01.ass`
- `verse_01.json`
- `verse_01.png`

This makes it easier to keep related files together when the schema evolves.
