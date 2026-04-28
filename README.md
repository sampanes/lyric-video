# lyric-video-pipeline

A reusable, scriptable pipeline for building lyric videos from audio, lyrics,
timed subtitle data, and optional background assets.

This repository is meant to be a general-purpose engine, not a one-off project
for a single song.

The design goals are:

- keep the code reusable
- keep per-song inputs separate
- render consistent outputs with FFmpeg
- keep lyric timing open to automated drafts, human review, and future capture
  modes without making users type timestamp numbers
- optionally generate background stills or simple visual assets from a sibling
  ComfyUI repo
- support multiple aspect ratios and future lyric layout modes without changing
  the authoritative lyric/timing layer

---

## What This Is For

This repo is for lyric videos where the important part is:

- lyrics are accurate
- lyrics appear at the right time
- the process is repeatable
- each song can be rendered from a config and a set of inputs

This repo is not focused on full AI-generated cinematic music videos.
It is focused on a reliable lyric pipeline, with optional background
generation or visual styling layered in where useful.

---

## Core Model

The code in this repository should stay generalized.

Each song should be treated as a data package containing:

- audio
- lyrics
- timing data
- style choices
- background assets
- output settings

That way the same scripts can render many different songs without rewriting the
pipeline.

The important architectural choice is to keep:

- timing capture separate from rendering
- raw timing events separate from normalized timing files
- ComfyUI integration behind an adapter boundary

That keeps the repo flexible if the capture method changes later.

Current defaults are recorded in `docs/architecture/decisions.md`.
The product-level direction is recorded in
`docs/roadmap/product-plan.md`.

---

## Long-Term Repo Shape

```text
lyric-video-pipeline/
  README.md
  docs/
    architecture/
    formats/
    workflows/
  scripts/
    render_song.py
    build_subtitles.py
    validate_song.py
    capture_timings.py
    generate_assets.py
  src/
    lyric_video/
      cli/
      config/
      timing/
      subtitles/
      rendering/
      assets/
      integrations/
  templates/
    ass/
    ffmpeg/
  presets/
    kid_youtube_education.json
  styles/
    classic.json
    minimal.json
    karaoke.json
  workflows/
    comfyui/
      prompts/
      node-graphs/
      adapters/
  songs/
    template_song/
      song.json
      inputs/
        audio/
        lyrics/
        references/
      timing/
        raw/
        reviewed/
        derived/
      subtitles/
      assets/
        backgrounds/
        overlays/
      renders/
      exports/
      notes/
  shared_assets/
  tools/
    capture_ui/
    review_ui/
    automation/
```

### Why this split works

- `src/lyric_video/` holds reusable engine code.
- `scripts/` holds runnable entry points.
- `songs/` holds per-song data only.
- `timing/raw/` can store human clicks, automation output, or imported
  timestamps without assuming one capture method.
- `timing/reviewed/` is the cleaned-up version you trust.
- `workflows/comfyui/` keeps the ComfyUI dependency optional and swappable.
- `tools/` can hold experimental utilities without polluting the core engine.

---

## Timing Review Strategy

To leave room for automation, imported timestamps, live human clicking, and
future GUI correction, store raw timing evidence separately from reviewed
render timing.

Recommended timing flow:

1. Generate or import draft timing evidence, for example WhisperX output,
   external timestamps, click timestamps, or automation events.
2. Convert that evidence into a normalized timing file.
3. Review or edit the normalized timing file.
4. Generate ASS or another subtitle format from the reviewed timing data.
5. Render from the reviewed output, not the raw capture.

That gives you a clean path for:

- manual live clicking
- keyboard-triggered capture
- automated capture from another tool
- later reprocessing if the timing schema changes

The current CLI timing adjustment commands are a bridge, not the desired final
user experience. The durable product direction is a GUI timing editor with
audio playback, rough waveform packets, lyric rows, drag handles or sliders,
range nudges, and proof rendering.

Recommended timing file types:

- `json` for structured event data
- `csv` for quick export/import
- `ass` for the final subtitle layer

---

## ComfyUI Integration Boundary

The sibling ComfyUI repo should be treated as an external asset generator, not
a hard dependency inside the renderer.

Recommended integration approach:

- keep a small adapter in this repo that knows how to call ComfyUI
- keep prompts and node graphs versioned under `workflows/comfyui/`
- write generated images into `songs/<song>/assets/backgrounds/`
- store the prompt, seed, model, and node-graph metadata alongside each asset

This makes it possible to:

- swap ComfyUI workflows later
- regenerate backgrounds without touching render code
- keep background generation optional
- support simple stills first, then more complex visuals later if needed

---

## Practical Defaults

- Config files are JSON and should live at the song root as `song.json`.
- The first supported render target is widescreen `16:9`.
- The first visual setup should be one still background per song or section.
- Separate scripts should stay separate: validate, build subtitles, capture
  timing, generate assets, and render.
- Render metadata and derived asset metadata should be kept alongside the
  outputs.
- Agent instructions live in [LLM.md](LLM.md).
- Song intake starts with `scripts/intake_song.py`, which auto-detects unique
  audio and lyric files and only asks if the input is ambiguous.
- Optional visual direction belongs in `inputs/song_style_prompt.txt` and can
  seed `song_vibes` plus future image-generation prompts.
- The current one-shot draft render command is
  `python scripts\make_videos.py "man behind the bar" --force`.
- The current one-shot Whisper-assisted render command is
  `python scripts\make_videos.py "man behind the bar" --refresh-whisper`.
- Multi-aspect output is available with
  `python scripts\make_videos.py "man behind the bar" --targets all`.
- Machine-readable song status is available with
  `python scripts\inspect_song.py "man behind the bar" --json`.
- A self-service operator checklist is available with
  `python scripts\guide_song.py "man behind the bar"` or `--json`.
- The first local timing review GUI launches with
  `python scripts\launch_review_ui.py --song "man behind the bar"`.
- A gentle scrolling lyric display is available with
  `python scripts\make_videos.py "man behind the bar" --layout soft_scroll`.
- Repeatable output habits are captured as presets, for example
  `python scripts\make_videos.py "man behind the bar" --preset kid_youtube_education`.
- A self-service, no-LLM-required song checklist lives in
  [SECOND_SONG_HANDHOLD.md](SECOND_SONG_HANDHOLD.md).
- A synthetic end-to-end smoke test is available with
  `python scripts\smoke_test.py`.
- A pre-push privacy scan is available with
  `python scripts\privacy_check.py --include-untracked`.
- The pre-GUI ComfyUI headless proof starts with
  `python scripts\comfyui_queue.py workflows\comfyui\node-graphs\basic_flux_t2i.api.json --song "man behind the bar" --dry-run`.
- ComfyUI background generation should run still image first, then
  a tiny image-to-video probe from the approved still. `832x480` remains a
  valid baseline size; the probe isolates prompt/source/runtime issues before
  spending a long Wan run.
- ComfyUI should be treated as a local API server, not a UI-clicking workflow.
  Check it with `python scripts\comfyui_server.py status` and start it with
  `python scripts\comfyui_server.py start` after setting `COMFYUI_ROOT` or
  ignored `LOCAL_CONFIG.json`.

---

## Tools I Would Expect To Need

Core tools:

- `ffmpeg` and `ffprobe` for render and validation
- Python for orchestration and file transforms
- a lockfile-based Python workflow such as `uv` or `poetry`
- `pysubs2` or an equivalent ASS/subtitle library
- `pydantic` or a similar schema library for config validation
- `typer` or `click` for CLI commands

Timing capture tools:

- a small local timing review UI, likely browser-based or desktop-based
- a simple event schema for clicks and automation output
- optional hotkey support if you want faster capture
- Whisper or WhisperX transcription assist for rough text and timestamps

ComfyUI tools:

- a lightweight HTTP client for the ComfyUI API
- prompt/workflow templates
- metadata capture for seeds, checkpoints, and node graphs
- optional BPM metadata or BPM detection for beat-synced background motion

Helpful but optional:

- `watchdog` for file watching and auto-rebuilds
- `rich` for readable CLI output
- `pytest` for validation and regression tests

---

## Recommended Design Rules

This repo should favor:

- repeatability
- clear file structure
- song-specific config files
- small, scriptable steps
- easy reruns
- easy extension later

This repo should avoid:

- hardcoding one song into the engine
- burying song assets inside scripts
- relying on manual clicking or hand-typed timestamp editing for core rendering
  steps
- tying the whole system to a single background-generation method

Whisper-based rough transcription should be treated as a helper input, not the
final lyric source or final timing authority.

---

## Suggested Workflow

1. Put song-specific input files in a dedicated song folder.
2. Generate or import draft lyric timing data.
3. Review and normalize the timing data.
4. Generate subtitle files, typically ASS.
5. Prepare visual assets such as still backgrounds, loops, or overlays.
6. Use FFmpeg to combine:
   - audio
   - subtitles
   - background visuals
   - optional transitions or overlays
7. Export a final lyric video.

Optional:

- generate background stills through ComfyUI
- generate subtle background motion through ComfyUI after still generation is
  reliable
- postprocess backgrounds before rendering
- add section-specific backgrounds for verses, choruses, and bridges

Current practical shortcut:

```powershell
python scripts\make_videos.py "approximate song name" --refresh-whisper
```

Use this when the song folder already has one audio file and one raw lyric file.
It runs WhisperX as a rough timing assist, keeps the written lyrics as the
authoritative text, and renders a basic MP4.

When timing is close but not good enough, adjust reviewed timing instead of
editing JSON by hand:

```powershell
python scripts\timing_adjust.py report "approximate song name" --around "unique lyric text"
python scripts\timing_adjust.py nudge "approximate song name" --from line_020 --to line_026 --shift +0.35s
python scripts\timing_adjust.py fit "approximate song name" --from line_020 --to line_026 --start-at 0:37.900 --end-at 0:47.800
```

Timing review is documented in `docs/workflows/timing-review.md`.

For the first command-launched timing GUI:

```powershell
python scripts\launch_review_ui.py --song "approximate song name"
```

This opens a local browser UI that reads the song package, plays the configured
audio, shows rough waveform packets, edits `timing/reviewed/timing.json`, and
saves with a backup.

For platform-specific exports:

```powershell
python scripts\make_videos.py "approximate song name" --refresh-whisper --targets all
```

Supported targets are `horizontal`, `vertical`, `square`, and `portrait`.
Target-specific subtitle files and MP4s are generated from the same reviewed
timing file.

For a large centered lyric treatment:

```powershell
python scripts\make_videos.py "approximate song name" --force --targets horizontal --layout fullscreen
```

For a gentle scrolling lyric treatment:

```powershell
python scripts\make_videos.py "approximate song name" --force --targets horizontal --layout soft_scroll
```

For a repeatable habit preset:

```powershell
python scripts\make_videos.py "approximate song name" --preset kid_youtube_education
```

Presets live under `presets/` and are documented in
`docs/formats/presets.md`. They are render-time defaults, not replacements for
song-specific lyrics, timing, or style prompt inputs.

To test the repo without a real song:

```powershell
python scripts\smoke_test.py
```

Planned display modes such as fullscreen lyrics, rolling lyrics, and karaoke
lyrics are documented in `docs/formats/lyric-layouts.md`. Rolling lyrics are a
candidate solution for reducing the cost of tiny timing corrections.

Before public pushes, run:

```powershell
python scripts\privacy_check.py --include-untracked
```

Machine-specific blocked words can live in ignored `LOCAL_PRIVACY_TERMS.txt`,
one term per line.

---

## Milestones

1. Repo scaffold

   - keep the `src/`, `scripts/`, `songs/`, `docs/`, and `workflows/` split
   - preserve the general-purpose engine layout
   - keep the ComfyUI boundary separate from the render engine
   - use `scripts/intake_song.py` to create or update `song.json`

2. Schemas and file architecture

   - define the song config schema
   - define the timing event schema
   - define the file groups that must live together
   - formalize the contract in `docs/architecture/file-contract.md`
   - document which files are paired, for example:
     - audio with lyrics and timing
     - reviewed timing with generated subtitles
     - background assets with the metadata that generated them
   - decide which song folders are tracked examples versus local working data
   - allow for a tracked `songs/template_song/` later, while ignoring actual
     production song folders by default

3. Capture and automation foundation

   - keep draft timing automation working
   - make reviewed timing cheap to correct without hand-typed timestamps
   - add a minimal GUI timing editor around playback, lyric rows, and backups
   - keep live click timing available as a later optional capture mode
   - add a small ComfyUI adapter stub for background generation
