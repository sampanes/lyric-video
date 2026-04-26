# Future GUI Roadmap

This document captures the useful GUI and orchestration ideas from
`gui_idea_spitballin.txt`.

It is not a commitment to build a GUI next. The current priority remains the
scriptable `make_videos.py` path. The GUI should eventually wrap that pipeline
as an orchestration, review, approval, and status layer.

## Current Plan Overlap

These ideas are already part of the repo direction:

- Lyrics are authoritative; Whisper and other transcripts are timing evidence,
  not source text.
- FFmpeg is the deterministic render and assembly backend.
- ComfyUI is optional and belongs behind an adapter boundary.
- Visuals should support lyrics, not compete with them.
- Stable stills and subtle loops are preferred over complex AI video.
- Multiple render targets matter: `horizontal`, `vertical`, `square`, and
  `portrait`.
- Bounce loops are a practical postprocess for subtle motion clips.
- Workflow JSONs should be stored under `workflows/comfyui/node-graphs/`.
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
- preview subtitle placement on representative frames
- expose explicit approval states, even if stored in simple JSON first

Do not start with a full editor, timeline, asset browser, and backend manager at
once.

## Later GUI Panels

Possible panels after the MVP:

- Lyrics and transcript alignment review
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
2. Add explicit approval/status files before building complex UI.
3. Add section data model.
4. Add safe-crop and subtitle-proof output generation through scripts.
5. Build ComfyUI still-image adapter.
6. Add variant metadata and prompt/settings diffs.
7. Add GUI only after the state model is clear.

## Risks And Guardrails

State explosion is the main risk. Songs, sections, targets, prompts, workflows,
variants, seeds, approvals, fonts, jobs, and outputs will get messy without
strict data contracts.

Guardrails:

- Candidate artifacts must never masquerade as approved artifacts.
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
