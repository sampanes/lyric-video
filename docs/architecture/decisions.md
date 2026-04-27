# Project Decisions

This document records the current defaults for the repo.

The goal is to keep implementation choices explicit and stable.

## Current Defaults

- Config format: `JSON`
- Song package root: `songs/<song_name>/`
- Template song: `songs/template_song/`
- Timing model: raw capture first, reviewed timing second, derived subtitles last
- Subtitle format: `ASS`
- Timing capture: automation-assisted draft timing first, GUI-assisted reviewed
  timing next, live click capture later as an optional input mode
- Transcription assist: Whisper/WhisperX as optional rough transcription and
  timestamp capture, not the final lyrics source
- Original inputs: preserve raw user-provided audio, lyrics, and vibe text;
  write cleaned or inferred files under derived/reviewed folders
- Visuals: one still background first, section-based swaps later
- Output targets: `horizontal`, `vertical`, `square`, and `portrait`, with
  `horizontal` as the default
- Lyric layouts: `standard`, `fullscreen`, and `soft_scroll` now, with
  `rolling` and `karaoke` documented as future modes
- BPM: optional user-provided metadata first, automatic estimation later
- Script UX: separate validate, subtitle-build, asset-generate, and render
  scripts, with `make_videos.py` as the stable high-level entrypoint and
  `make_basic_video.py` as the current implementation behind it
- Validation: early schema validation is worth doing
- ComfyUI integration: optional adapter boundary, not a hard dependency
- Future GUI: orchestration, review, approval, and status layer over scripts;
  not a replacement for the scriptable pipeline

## Scope Boundary

This repo is the lyric-video pipeline. It should not become the master project
for local song generation, voice conversion, DAW workflows, model inventories,
or AI-audio experiments.

Those systems can feed this repo through stable artifacts:

- final or draft audio files under `inputs/audio/`
- optional vocal or instrumental stems under future song-local input folders
- authoritative user lyrics under `inputs/lyrics/`
- timing evidence under `timing/raw/`
- approved visual assets under `assets/backgrounds/`

If a separate AI-audio lab or notes repo exists, it should own model install
notes, launch recipes, voice-conversion experiments, and heavy storage maps.
This repo should own the repeatable path from song package to lyric video.

## What This Means In Practice

### Config

The primary song config file is `song.json` at the song root.

That file should describe:

- song metadata
- file paths
- timing source references
- style selection
- output settings
- background strategy

### Timing

Timing starts as draft evidence and becomes reviewed timing before rendering.

This supports:

- Whisper/WhisperX or future known-lyrics alignment
- imported timestamps
- future keyboard or click capture
- GUI-assisted correction

The reviewed timing file is the thing we trust for rendering.

Human timing review is not a workaround; it is part of the expected workflow for
music. Automation should produce a useful draft, then repo-owned tools should
make small corrections cheap. The long-term correction surface should be a GUI
with playback, lyric rows, sliders or drag handles, range nudges, and safe
backups. Normal users should not need to type timestamp numbers.

### Transcription Assist

Whisper and WhisperX can be used to generate a rough transcript with
timestamps.

That transcript should be treated as a head start for lyric entry and timing
alignment, not as the authoritative lyrics source.

Use the existing external environment by path or env var instead of duplicating
it inside this repo.

Current local dependencies are:

- external venv outside this repo
- package: `openai-whisper`
- package: `faster-whisper`
- package: `whisperx`

Runtime configuration:

- set `WHISPERX_EXE` when `whisperx` is not already on `PATH`
- keep Whisper and Hugging Face model caches outside this repo
- keep machine-specific absolute paths in ignored local environment files or
  shell profiles, or ignored `LOCAL_PATHS.md`, not tracked repo files

This keeps the repo from owning large model files while still making the local
setup reproducible.

There is no dedicated music mode exposed by the current WhisperX CLI. For songs,
use the written lyrics as an initial prompt and expect the transcript to need a
merge/review pass.

When a rendered proof is close but still feels wrong, shift or fit reviewed
timing ranges rather than continuing to overfit transcription alignment.

### Visuals

The first render target should be simple:

- one background still
- clean lyric presentation
- deterministic FFmpeg composition

More complex visual modes can be layered in later without changing the base
pipeline.

Subtle background motion should start from a still-image workflow exported from
ComfyUI. Animation and BPM-synced motion should be added only after the still
adapter is reliable.

### Outputs

Initial output assumptions should favor widescreen lyric videos when no target
is specified.

Vertical, square, and 4:5 portrait exports are separate render targets. They
share the same reviewed timing and authoritative lyric text, but each target
gets its own ASS subtitle file and MP4 output.

### Logging and Metadata

Derived outputs should carry enough information to reproduce them.

Record at least:

- render timestamp
- source song config
- timing file version
- subtitle file version
- background asset metadata
- FFmpeg command or command template used

## Open-Ended Areas

These are intentionally not frozen yet:

- exact schema field names
- exact capture UI implementation
- exact ComfyUI adapter mechanism
- exact review workflow UX
- exact candidate/approved/final artifact state schema
- exact section data model
- exact lyric layout CLI and output naming for fullscreen or rolling layouts
- exact BPM detection implementation

The repo should keep those flexible, but the defaults above should remain
stable.
