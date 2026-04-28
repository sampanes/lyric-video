# Product Plan

This is the product-level plan for the lyric-video pipeline. It sits above the
workflow docs and should guide implementation order.

## Product Promise

The product should let a user say:

```text
I added a song, lyrics, and a vibe description. Make me lyric videos.
```

Then it should guide the project from raw inputs to usable exports with the
least possible hand work.

The final product is not "AI makes a whole music video." The durable product is
a local production assistant for lyric videos:

- preserve the user's audio, lyrics, and style intent
- generate useful draft timing
- make human timing correction fast and visual
- generate or import low-distraction background visuals
- render clean exports for common platforms
- keep every repeatable action scriptable without requiring an LLM

## User Promise

The user should not need to:

- remember folder architecture
- type subtitle timestamps by hand
- manually drag ComfyUI outputs into song folders
- know which script runs next
- trust Whisper text over their real lyrics
- rebuild commands from chat history
- use a full NLE for basic lyric-video work

The user should still be expected to:

- provide or approve the real lyrics
- listen to timing drafts and decide what feels early or late
- approve generated visuals
- choose the final output target and style when defaults are not enough

## Product Modes

The GUI should present these modes as an ordered stepper with tabs across the
top and clear next/back arrows. Users should be able to jump around when needed,
but the default path should make the next step obvious.

The stepper is not a rigid wizard. It should support optional steps, skipped
steps, and substeps. More steps are acceptable when they reduce confusion or
prevent accidental approval. Fewer steps are acceptable for a quick draft path.

Suggested top-level steps:

1. `Song`
2. `Lyrics`
3. `Timing`
4. `Sections`
5. `Prompts`
6. `Pictures`
7. `Video Background`
8. `Style`
9. `Render`
10. `Review`

Each step should show:

- what is already present
- what is missing
- what is approved
- the next recommended action
- whether the user can safely continue
- whether the step is optional, skipped, blocked, candidate, approved, or final

Do not hide the underlying scriptable workflow. Each step should map to
repo-owned files and commands.

Possible optional/future steps:

- `Stems`: import or generate vocals-only/instrumental stems for better timing
- `Transcript`: inspect Whisper/stable-ts evidence before timing review
- `Variants`: compare prompt/image/video candidates across seeds and settings
- `Crop`: check safe areas for horizontal, vertical, square, and portrait
- `Fonts`: verify fonts and stress-test subtitle readability
- `Package`: collect final exports and metadata for publishing or archiving

The product should allow presets to collapse steps. Example: a trusted
still-only preset can skip `Video Background`; a no-visual draft can skip
`Prompts`, `Pictures`, and `Video Background`; a manually supplied background
can skip image generation but still require visual approval.

### Autopilot Draft Mode

Goal: get from raw song folder to watchable proof quickly.

Inputs:

- one audio file
- one lyric file
- optional `inputs/song_style_prompt.txt`
- optional preset

Outputs:

- `song.json`
- derived clean lyric artifacts
- draft reviewed timing
- subtitles
- basic MP4 exports

This mode can be good enough for rough sharing, but it is not expected to be
ship-ready timing.

### Timing Review Mode

Goal: turn draft timing into approved timing without typing numbers.

This is the first real GUI product.

Timing review is audio-first. Lyric timing depends on words matching sounds,
not on the background video. Video should be a proof render after timing edits,
not the main correction surface.

Core interactions:

- play/pause audio
- show rough waveform packets or amplitude blocks from the source audio
- show lyric rows from `timing/reviewed/timing.json`
- highlight the active line
- drag starts and ends
- nudge selected ranges earlier/later
- fit a selected range between two playhead anchors
- save with automatic backup
- proof-render the current state

CLI helpers such as `timing_adjust.py` remain the backend contract, but the
normal user interaction should be visual.

### Visual Assist Mode

Goal: create background visuals that support the lyrics without becoming a full
AI-video project.

Default strategy:

- generate stills first
- approve stills
- generate subtle loops only when useful
- use FFmpeg for deterministic looping, bounce loops, crops, fades, and final
  assembly

Visuals should usually be atmospheric, low motion, subtitle-safe, and
non-narrative.

The visual workflow should be staged:

1. Choose or generate section prompts.
2. Approve prompts for the relevant song sections.
3. Generate still pictures from approved prompts.
4. Approve pictures.
5. Choose which approved picture becomes the basis for a video background.
6. Generate subtle video loops only from approved pictures.
7. Approve the loop or fall back to still/FFmpeg motion.

This prevents an unapproved prompt from silently becoming a final video asset.

### Format Habit Mode

Goal: make repeated output habits one command or one preset.

Examples:

- kid education horizontal format
- shorts vertical format
- square social preview
- large fullscreen lyrics
- soft-scroll lyrics

Presets should encode repeatable style and platform defaults. Song-specific
lyrics, timing, and vibe stay in the song folder.

### Director Toolkit Mode

Goal: let the user make better work without turning the repo into a DAW, music
generator, or Blender pipeline.

This repo can accept outputs from other systems:

- final mixes
- vocal stems
- instrumental stems
- imported timing
- generated stills
- generated loops

It should not own model inventories, voice-conversion workflows, FL Studio
notes, or general AI audio experiments. Those belong in a separate notes repo or
heavy local workspace.

## Product Boundary

This repo owns:

- song intake
- song package validation
- lyric cleaning for render use
- draft transcript/timing capture
- reviewed timing
- subtitle generation
- ComfyUI workflow queueing for lyric-video backgrounds
- background import/postprocess helpers
- FFmpeg rendering
- render targets and presets
- future timing-review GUI

This repo does not own:

- generating songs from scratch
- DAW session management
- vocal tuning or voice conversion
- model download inventories
- general AI-audio lab notes
- complex character animation
- full NLE editing
- Blender production management

The boundary is artifact-based. External tools can hand this repo audio,
lyrics, stems, timing evidence, images, or loops.

## Release Sequence

### R0: Scriptable Proof

Status: mostly exists.

Definition:

- new song folder can become a basic video
- WhisperX can produce a draft timing pass
- multiple aspect ratios can render
- soft-scroll/fullscreen layouts exist
- smoke test exists
- privacy check exists
- ComfyUI can be started/queued headlessly

Main gap:

- the user still needs CLI/LLM help for many next-step decisions.

### R1: No-Amnesia Operator

Goal: make the scriptable path self-explanatory.

Deliverables:

- stronger `guide_song.py --json`
- clear next-step machine state
- explicit failure categories
- one command for "make draft"
- one command for "validate ready"
- one command for "render proof"
- one command for "render final targets"
- docs that match the scripts

Definition of done:

- a future user can run a second or third song without reading chat history.

### R2: Timing GUI MVP

Goal: eliminate hand-typed timestamp correction as normal workflow.

Deliverables:

- local GUI under `tools/review_ui/` or equivalent
- load song by approximate name or folder
- play audio
- display reviewed timing rows
- active line highlight
- drag or slider controls for line start/end
- selected range nudge
- selected range fit between anchors
- save with backup
- run proof render

Definition of done:

- the user can fix an obviously shifted chorus without opening JSON or typing a
  timestamp.

### R3: Approval And State Layer

Goal: distinguish draft, candidate, approved, rejected, and final artifacts.

Deliverables:

- simple song-local state file
- approval records for lyrics, timing, subtitle style, visuals, and final render
- review queue for needs-attention items
- generated asset metadata normalized enough for GUI display

Definition of done:

- the product can say what is blocking a final render.

### R4: Visual Asset Assistant

Goal: make background generation repeatable and reviewable.

Deliverables:

- still-image adapter around `comfyui_queue.py`
- image-to-video adapter around known-good subtle workflow
- sidecar metadata for every generated asset
- variant generation by seed count
- winner/reject marking
- bounce-loop integration
- safe-crop preview frames
- subtitle proof frames

Definition of done:

- the user can generate several background candidates, approve one, and render
  it without manual file movement.

### R5: Format Preset Studio

Goal: make repeatable posting formats easy.

Deliverables:

- preset editor or preset schema hardening
- verified FFmpeg font list
- font stress tests
- target-safe subtitle preview
- horizontal/vertical/square/portrait proof outputs

Definition of done:

- "kid YouTube education song" or "shorts version" becomes a reliable preset,
  not a remembered command.

### R6: Section-Based Visual Planning

Goal: support verse/chorus/bridge visual changes without becoming an NLE.

Deliverables:

- section model
- section timeline view
- section prompt notes
- per-section still/loop/background selection
- inherit-baseline visual mode
- prompt/settings diff view

Definition of done:

- a song can have a small number of intentional visual sections with consistent
  style and reproducible assets.

## Timing GUI Product Spec

This deserves priority because timing quality is the main blocker for a lyric
video feeling finished.

The timing GUI should work directly from the song audio file. It does not need a
generated background video to review or correct timings.

## GUI Implementation Call

Build the product GUI from a clean repo-owned foundation. Do not copy the
AI Studio example app into the product path.

The example app is useful as interaction research, not as architecture. Borrow
the concepts that match the product:

- browser-based audio playback
- waveform overview plus zoomed detail
- current lyric focus
- adjacent lyric context
- keyboard shortcuts for play, navigation, and stamping
- visible per-line status dots

Do not inherit the example's product structure:

- browser-only file upload/export as the main workflow
- Gemini/API dependency
- standalone Vite app with no Python backend
- random line ids that do not match `timing/reviewed/timing.json`
- start-only stamps with no reviewed end-time model
- no song package awareness
- no backups on save
- no repo command access

Preferred foundation:

- command launcher: `python scripts\launch_review_ui.py`
- backend: Python local web server with repo-root `cwd`
- frontend: browser UI for waveform and timing interactions
- backend API reads/writes song package files directly
- backend can call existing repo scripts and later provider adapters

This preserves the useful UI lesson while avoiding broken generator app debt.

The GUI must launch from a command so it inherits the same environment as the
working scripts: Python executable, FFmpeg availability, local config files,
ComfyUI path variables, and future LLM CLI providers.

### Minimum Screen

- top: audio transport and current time
- left: lyric rows with ids and text
- center: simple timeline with waveform packets or amplitude blocks
- right: selected line/range controls
- bottom: validation messages and render/proof buttons

The waveform does not need sample-level editing precision for the MVP. It only
needs to give visual landmarks so the user can see loud/quiet sections, choruses,
breaks, and rough phrase locations while listening.

### Required Edits

- set selected line start from playhead
- set selected line end from playhead
- drag selected line start/end
- nudge selected line or range by fixed increments
- fit selected range between start and end anchors
- undo by restoring automatic backups

### Useful Defaults

- nudge buttons: `-500ms`, `-250ms`, `-100ms`, `+100ms`, `+250ms`, `+500ms`
- keyboard: space play/pause
- keyboard: arrow keys move active lyric row
- keyboard: bracket-like shortcuts for start/end anchors
- visual warning when lines overlap or have negative duration

### Non-Goals

- waveform-perfect audio editor on day one
- video-backed timing review
- word-level karaoke editing
- full multitrack editing
- video timeline editing
- replacing FFmpeg renders with GUI previews

## Data Model Priorities

Do not build a complex database first. Start with song-local JSON files.

Near-term state files:

- `song.json`: identity, paths, render defaults
- `timing/reviewed/timing.json`: render timing source of truth
- `status.json` or similar: approvals and current blockers
- sidecars next to generated assets
- render metadata next to exports or under `renders/`

Important statuses:

- `candidate`
- `approved`
- `rejected`
- `final`
- `needs_attention`

Important approvals:

- lyrics
- timing
- section plan
- prompts
- pictures
- video background
- subtitle style
- background visual
- final render

## Stepper GUI Shape

The GUI should feel like a guided production line, not a blank editor.

Use tabs across the top for the major steps and arrow buttons for normal
progression. The current step should own the main screen, while a small status
bar can show blockers from other steps.

Each top-level step can contain substeps. Substeps are preferable to cramming
too many unrelated controls into one screen.

Allowed step states:

- `missing`
- `candidate`
- `needs_review`
- `approved`
- `skipped`
- `blocked`
- `final`

The UI should distinguish "skipped intentionally" from "not done yet."

### Step 1: Song

Purpose:

- locate or create the song folder
- detect audio, lyrics, and optional vibe description
- create or update `song.json`

Primary actions:

- inspect song
- run intake
- validate source files

### Step 2: Lyrics

Purpose:

- show raw user lyrics
- show derived render lyrics
- keep source lyrics authoritative
- approve lyric text for rendering

Primary actions:

- view source lyrics
- view cleaned candidate
- approve lyrics

### Step 3: Timing

Purpose:

- generate draft timing
- edit reviewed timing visually against audio
- approve timing

Primary actions:

- run Whisper/draft timing
- open audio-first timing editor
- save reviewed timing backup
- render timing proof
- approve timing

### Step 4: Sections

Purpose:

- group lyrics into intro, verse, chorus, bridge, outro, or custom sections
- keep visual planning section-based instead of line-based

Primary actions:

- auto-suggest sections from timing gaps/repeated lyrics
- edit section boundaries
- approve section plan

### Step 5: Prompts

Purpose:

- create visual prompts from `song_vibes`, section notes, and user direction
- keep prompts candidate until approved

Primary actions:

- draft section prompts
- edit prompt text
- approve prompts

### Step 6: Pictures

Purpose:

- generate still image candidates from approved prompts
- review which pictures are usable

Primary actions:

- queue still generations
- show variants
- approve/reject pictures
- mark baseline picture for visual continuity

### Step 7: Video Background

Purpose:

- choose approved stills for subtle motion or still-only rendering
- generate and approve loops

Primary actions:

- choose picture for video
- queue subtle image-to-video
- make bounce loop
- approve loop
- choose fallback still mode

### Step 8: Style

Purpose:

- choose subtitle layout, font, target ratios, and preset
- prove readability before final render

Primary actions:

- choose preset
- preview subtitle proof frames
- run font stress test
- approve style

### Step 9: Render

Purpose:

- render selected targets from approved timing, lyrics, style, and background

Primary actions:

- render proof
- render final targets
- open export folder

### Step 10: Review

Purpose:

- show final outputs and blockers
- record approval or needs-attention notes

Primary actions:

- approve final
- mark issue and jump back to the relevant step
- show run metadata

## LLM Role

LLMs can help with:

- prompt drafts
- transcript-to-lyric reconciliation
- explaining failures
- summarizing run metadata
- suggesting next actions
- producing candidate section prompts

LLMs should not be required for:

- locating song files
- validating the package
- rendering videos
- correcting timing once the GUI exists
- moving ComfyUI outputs
- knowing command sequences

The product should degrade to scripts and GUI when no LLM is present.

## Based

High-leverage product bets:

- timing GUI before a full GUI
- reviewed timing as source of truth
- automation as a draft, not an oracle
- presets for repeatable habits
- simple atmospheric visuals before ambitious AI video
- ComfyUI as a backend, not a manual UI dependency
- FFmpeg as deterministic final assembly
- artifact states before complex visual planning
- section-level visuals before line-level visuals

## Cringe

Avoid these traps:

- building a full NLE
- treating Whisper output as final truth
- making users type timestamps forever
- making click-along timing the default correction path
- generating visuals per line by default
- requiring manual drag/drop from ComfyUI
- using LLM memory as infrastructure
- putting AI audio lab scope into this repo
- adding approval gates so often the user ignores them
- adding knobs before defaults are reliable

## Next Product Move

The next product move should be R1 into R2:

1. Make song status and next actions more machine-readable.
2. Harden timing edit operations as reusable Python functions, not only CLI
   behavior.
3. Build the smallest timing review GUI that can load a real song, play audio,
   show lyric rows, adjust reviewed timing, save backups, and run a proof
   render.

Everything else should support that path unless a real song test exposes a more
urgent blocker.
