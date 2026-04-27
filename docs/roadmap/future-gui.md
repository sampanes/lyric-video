# Future GUI Roadmap

This document captures the durable GUI and orchestration plan for the repo.
Temporary scratch notes should be absorbed here or deleted instead of tracked
as source files.

It is not a commitment to build a GUI next. The current priority remains the
scriptable `make_videos.py` path plus cheap human timing review. The GUI should
eventually wrap that pipeline as an orchestration, review, approval, and status
layer.

## Current Plan Overlap

These ideas are already part of the repo direction:

- Lyrics are authoritative; Whisper and other transcripts are timing evidence,
  not source text.
- Whisper timing is a head start, not a ship-ready result for sung audio.
- FFmpeg is the deterministic render and assembly backend.
- ComfyUI is optional and belongs behind an adapter boundary.
- Visuals should support lyrics, not compete with them.
- Stable stills and subtle loops are preferred over complex AI video.
- Multiple render targets matter: `horizontal`, `vertical`, `square`, and
  `portrait`.
- Bounce loops are a practical postprocess for subtle motion clips.
- Workflow JSONs should be stored under `workflows/comfyui/node-graphs/`.
- A headless ComfyUI queue/download proof should exist before GUI background
  controls.
- Routine ComfyUI use should be API-server-driven from Python commands, not UI
  clicking.
- Generated assets need sidecar metadata with prompt, seed, workflow, target,
  and render settings.
- Real commands should live in scripts, not in LLM memory.

## New Or Sharpened Ideas

These are useful additions that were not fully captured before:

- Candidate, approved, final, rejected, and needs-attention states should exist
  across lyrics, prompts, visual assets, subtitle styles, and renders.
- Safe crop preview should show the same background across all supported target
  ratios with subtitle-safe zones overlaid.
- Subtitle proof mode should render representative frozen frames with the real
  FFmpeg subtitle styling before final render.
- A section timeline should model intro, verse, chorus, bridge, and outro
  blocks without becoming a full NLE.
- Section visuals should support still, subtle loop, inherited baseline, and
  rare hero-shot modes.
- Prompt and settings diff views should show what changed between variants or
  workflow iterations.
- Variant generation should support "make N candidates for this section" with
  winner/reject marking.
- A project memory pane should expose approved lyrics, prompts, section notes,
  workflows, assets, and rejected experiments.
- Job batching should group similar backend work, such as all Flux stills, then
  all Wan loops, then FFmpeg assembly.
- Verified font previews are needed because GUI font lists may not match what
  FFmpeg can actually render.
- A font stress test should preview long, awkward, punctuated, repeated, or
  all-caps lyric lines across all target ratios.
- A review queue should surface low readability, missing approval, missing
  background, failed jobs, seam issues, and crop issues.
- A "what changed" card should be written after each run, with workflow, seed,
  size, prompt delta, result path, and quick approval/rejection note.
- Timing review should become a first-class interaction with audio playback,
  lyric rows, drag handles, range nudges, and reviewed-timing backups.

## Timing Editor Priority

The first GUI that materially improves the product is a timing editor, not a
full video editor.

Timing review should be audio-first. The user is aligning words to sounds; the
background video is irrelevant until proof render time. The GUI should load the
song audio directly and show rough waveform packets or amplitude blocks as
landmarks.

The user should not need to type timestamp numbers for normal correction. CLI
commands such as `scripts/timing_adjust.py nudge` and `fit` are useful
transitional tools and a stable backend contract, but the long-term interaction
should be visual:

- play/pause the song
- see rough waveform or amplitude landmarks
- see the current lyric line highlighted
- drag line starts and ends
- select a verse or chorus and shift it earlier/later
- pin a bad section between two anchors and let the tool distribute the lines
- save reviewed timing with automatic backup
- re-render a proof video from the same screen

Live click-along capture can remain a later input mode. It is not the primary
answer to timing correction because the normal correction task is "this section
is early or late," not "manually perform the whole song again."

## Data Model Implications

The GUI needs a clear project data model before it grows.

Core entities:

- `song`
- `section`
- `lyrics_artifact`
- `timing_artifact`
- `prompt_artifact`
- `visual_asset`
- `workflow_reference`
- `render_target`
- `approval_record`
- `job_record`

Artifact states:

- `candidate`
- `approved`
- `final`
- `rejected`
- `needs_attention`

Approval gates worth modeling:

- lyrics approved
- timings approved
- section prompts approved
- subtitle style approved
- background assets approved
- final render approved

Do not render from candidate lyrics. Rendering should use reviewed timing and
approved lyric text.

## GUI MVP Shape

A practical first GUI should stay small:

- load or inspect a song folder
- show detected audio, lyrics, `song_vibes`, timing, subtitles, and exports
- run the same commands exposed by `scripts/make_videos.py`
- show validation status from `scripts/validate_song.py`
- show a read-only next-step summary similar to `scripts/inspect_song.py`
- show reviewed timing in a lyric row list
- provide audio playback with active-line highlighting
- allow simple timing nudges and start/end anchor edits
- preview subtitle placement on representative frames
- expose explicit approval states, even if stored in simple JSON first

Do not start with a full editor, NLE timeline, asset browser, and backend
manager at once.

## Stepper Navigation

The GUI should be organized as tabs across the top with next/back arrows. The
default path should feel like a production checklist:

1. Song
2. Lyrics
3. Timing
4. Sections
5. Prompts
6. Pictures
7. Video Background
8. Style
9. Render
10. Review

The user can jump between tabs, but the UI should always show the next
recommended step and whether the current step is missing, candidate, approved,
or blocked.

Visual generation should not be a single magic button. The user should first
pick or approve prompts by section, then approve pictures, then choose which
picture should become the video background source.

The stepper should remain flexible. It is acceptable to add more steps or
substeps when they make the workflow clearer. It should also be possible for
presets or user choices to skip steps intentionally, such as skipping generated
video backgrounds for a still-only render.

Useful states for each step:

- missing
- candidate
- needs review
- approved
- skipped
- blocked
- final

## Later GUI Panels

Possible panels after the MVP:

- Lyrics and transcript alignment review
- Waveform-backed fine timing editor
- Sections and prompt notes
- Background still and loop review
- Crop and safe-zone preview
- Font and subtitle style proofing
- Approval checklist
- Jobs and backend progress
- Run history and prompt/settings diffs
- Final render summary

## Backend Strategy

The GUI should call repo-owned scripts and adapters.

Preferred path:

- GUI calls Python scripts or imports repo modules.
- ComfyUI adapter submits exported API workflow JSON to a live local ComfyUI
  backend.
- FFmpeg remains the final deterministic renderer.
- LLMs help with prompts, transcript reconciliation, critique, and summaries.

Avoid making terminal puppeting the main infrastructure. Local LLM CLIs can be
useful helper providers, but they should not be required for deterministic
render success.

## Priority Order

Near-term scriptable foundation:

1. Keep `make_videos.py`, `inspect_song.py`, `validate_song.py`, and
   `smoke_test.py` healthy.
2. Keep timing review helpers stable as the backend for visual timing edits.
3. Add a minimal timing review GUI around reviewed timing, audio playback, and
   safe backups.
4. Add explicit approval/status files before building complex visual UI.
5. Add section data model.
6. Add safe-crop and subtitle-proof output generation through scripts.
7. Prove a minimal headless ComfyUI background-video queue/download path.
8. Build ComfyUI still-image and image-to-video adapters around the generic
   queue helper.
9. Add variant metadata and prompt/settings diffs.

## Risks And Guardrails

State explosion is the main risk. Songs, sections, targets, prompts, workflows,
variants, seeds, approvals, fonts, jobs, and outputs will get messy without
strict data contracts.

Guardrails:

- Candidate artifacts must never masquerade as approved artifacts.
- Draft timing must never masquerade as human-reviewed timing.
- GUI previews must be marked as previews unless they are generated by the same
  render path as final output.
- Prompt edits need shared song-level visual anchors to prevent drift.
- Workflow automation should avoid fragile assumptions about ComfyUI node IDs
  where possible.
- Approval gates should happen at meaningful stages only; too many gates cause
  blind clicking.
- Generated assets need strict naming and metadata or asset sprawl will win.
- Birthday-party shortcuts should be labeled as one-offs, not architecture.

## Based

Highest-value ideas:

- Safe-crop preview across all target ratios.
- Fast human timing review with sliders, nudge controls, and audio playback.
- Subtitle proof frames using real FFmpeg styling.
- Candidate, approved, final, rejected, and needs-attention states everywhere.
- Prompt/settings diff views.
- Variant generation with winner/reject selection.
- Project memory/audit trail.
- Job batching by model family.
- Verified FFmpeg font list and font stress test.
- Section-level visual planning instead of line-level visual generation.
- Bounce-loop toggle for subtle motion clips.

## Cringe Or Not Yet

Ideas to defer or treat carefully:

- Full NLE-style timeline. Too much scope.
- Per-line or per-stanza visual generation by default. Too much asset churn and
  too much visual inconsistency.
- Premium hero-shot mode as a normal path. It should stay rare and optional.
- Terminal puppeting as core infrastructure. Fine for exploration, brittle for
  production.
- API-avoidance as an absolute rule. Local-first is correct, but adapter
  boundaries matter more than whether a backend is local or remote.
- Approval for every tiny action. Approval fatigue will make approvals
  meaningless.
- Too many user-facing knobs. Defaults should stay beginner-safe with advanced
  controls hidden.
