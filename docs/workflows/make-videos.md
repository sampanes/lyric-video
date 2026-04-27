# Make Videos Workflow

This is the default operator path when the user says:

```text
I added a song, lyrics, and a basic description. Let's make videos.
```

The long-term goal is that repeatable actions live in scripts, not in an LLM's
memory. The LLM may help with prompts, rough transcript reconciliation, and
judgment calls, but routine commands should be runnable without an LLM.

## Required User Inputs

A song folder under `songs/` should contain, somewhere inside it:

- one audio file: `.wav`, `.mp3`, `.flac`, `.m4a`, `.aac`, `.ogg`, or `.opus`
- one lyric file: `.txt`, `.md`, or `.lrc`
- optional visual/style prompt file at `inputs/song_style_prompt.txt`
- legacy/alias vibe files named like `song-vibes.txt`, `vibes.txt`,
  `description.txt`, or `prompt.txt`
- optional `song.json` with title, artist, `song_vibes`, `bpm`, and targets

If `song.json` does not exist, the script can create a basic one from the
unique audio and lyric files. If more than one audio or lyric file exists, the
operator must resolve the ambiguity.

Known style/vibe filenames are ignored during lyric-file detection, so the user
can provide both `lyrics.txt` and `inputs/song_style_prompt.txt` without
creating an ambiguous lyric input.

## Default Command

Use this first for a no-drama draft:

```powershell
python scripts\make_videos.py "song name" --refresh-whisper --targets all
```

This delegates to the current basic pipeline and should:

- resolve the song folder from an approximate name
- create missing canonical song directories from the file contract
- create missing config when possible
- move newly discovered unique audio and lyric files into `inputs/audio/` and
  `inputs/lyrics/` when creating config
- populate `song_vibes` from bracketed lyric tags and/or a known
  style prompt file
- add `style_prompt` to `song.json` when `inputs/song_style_prompt.txt` exists
- validate required paths and local FFmpeg tools before rendering
- run WhisperX when requested
- keep Whisper output under `timing/raw/whisper/`
- derive cleaned lyric artifacts under `timing/derived/`
- write reviewed timing under `timing/reviewed/`
- generate target-specific ASS subtitles under `subtitles/`
- write final MP4 deliverables under `exports/`

## Faster Draft Command

When WhisperX is not needed or is too slow:

```powershell
python scripts\make_videos.py "song name" --force --targets horizontal
```

This creates even fallback timing. It is useful for confirming the file
structure, renderer, fonts, and output naming before investing in timing.

## Habit Presets

Use presets when the desired output format is a repeatable habit, for example
"kid education videos are always horizontal with this readable font":

```powershell
python scripts\make_videos.py "song name" --preset kid_youtube_education
```

The first tracked preset is:

```text
presets/kid_youtube_education.json
```

It currently sets horizontal output, 30 fps, standard layout, and a rounded
readable subtitle font/color treatment. Future ComfyUI prompt defaults can also
live in the preset, but song-specific `song_vibes` and
`inputs/song_style_prompt.txt` still carry the actual creative direction.

Precedence is:

- explicit CLI flags
- preset defaults
- `song.json`
- hardcoded safe defaults

## Layout Options

The default lyric layout is `standard`.

For a large centered lyric treatment:

```powershell
python scripts\make_videos.py "song name" --force --targets horizontal --layout fullscreen
```

Fullscreen layout exports add the layout name to the filename, for example:

```text
exports/song-name.horizontal.fullscreen.mp4
```

For a gentle scrolling lyric treatment:

```powershell
python scripts\make_videos.py "song name" --force --targets horizontal --layout soft_scroll
```

Soft-scroll exports include the layout name:

```text
exports/song-name.horizontal.soft_scroll.mp4
```

## Timing Responsibility

The source lyric file is authoritative. Whisper/WhisperX output is evidence,
not rendered text.

Whisper timing should be treated as a draft. For sung audio, the expected
workflow is to generate a rough first pass, review it by listening, then make
small human corrections to `timing/reviewed/timing.json`. Do not treat bad
Whisper alignment as a reason to keep rewriting the mapper indefinitely.

Current automated timing choices:

- `--timing-source even`: distribute lyric lines evenly across the song
- `--timing-source whisper`: map authoritative lyric lines onto Whisper segment
  timing
- `--timing-source auto`: use Whisper timing if available, otherwise even timing

Future improvements should still write final timing to:

```text
songs/<song>/timing/reviewed/timing.json
```

Use the timing review helper when the draft is close but not correct:

```powershell
python scripts\timing_adjust.py report "approximate song name" --around "unique lyric text"
python scripts\timing_adjust.py nudge "approximate song name" --from line_020 --to line_026 --shift +0.35s
python scripts\timing_adjust.py fit "approximate song name" --from line_020 --to line_026 --start-at 0:37.900 --end-at 0:47.800
```

Detailed timing review notes live in
[Timing Review Workflow](./timing-review.md).

## Background Responsibility

The basic pipeline can render without generated backgrounds.

ComfyUI should eventually be called through an adapter that writes directly to
the correct song package paths:

- raw source clips, if preserved: `inputs/video/`
- render-ready stills and loops: `assets/backgrounds/`
- final lyric videos: `exports/`

Do not make manual drag/drop part of the normal workflow. `scripts/import_media.py`
exists only for ad hoc external files that already exist somewhere else.

## Current Script Roles

- `make_videos.py`: high-level default entrypoint; delegates to the current
  basic renderer.
- `make_basic_video.py`: current implementation of config, timing, subtitles,
  and basic MP4 rendering.
- `validate_song.py`: read-only validator by default; pass `--create-config`
  only when config creation is intentional.
- `inspect_song.py`: read-only status command that reports detected inputs,
  timing, subtitles, exports, and the next likely command.
- `inspect_song.py --json`: machine-readable song status for future GUI and
  automation.
- `guide_song.py`: self-service operator checklist; `--json` emits the same
  checklist as structured data.
- `smoke_test.py`: creates a temporary ignored synthetic song, renders it, runs
  validation, and deletes it unless `--keep` is passed.
- `whisper_song.py`: standalone WhisperX capture when transcription output
  needs inspection.
- `render_vibe_video.py`: renders reviewed lyrics over an existing looping
  background video.
- `make_bounce_loop.py`: converts a short subtle clip into a palindrome loop.
- `import_media.py`: optional one-off importer for already-generated external
  media; not the planned normal ComfyUI path.
- `comfyui_queue.py`: generic headless ComfyUI API queue/download helper for
  pre-GUI background-generation proof work.
- `timing_adjust.py`: reports, nudges, or fits reviewed timing ranges while
  preserving backups.

## Readiness Test For A New Song

For a new song folder, a successful smoke test is:

```powershell
python scripts\make_videos.py "approximate song name" --force --targets horizontal
```

Expected output:

- `songs/<song>/song.json`
- `songs/<song>/timing/reviewed/timing.json`
- `songs/<song>/subtitles/lyrics.horizontal.ass`
- `songs/<song>/exports/<song>.horizontal.mp4`

After that works, run the fuller timing pass:

```powershell
python scripts\make_videos.py "approximate song name" --refresh-whisper --targets all
```

To test the repo without a real song:

```powershell
python scripts\smoke_test.py
```

To inspect a real song folder without changing it:

```powershell
python scripts\inspect_song.py "approximate song name"
```

## Current Gaps

The repo is ready for a second-song smoke test, but not fully hands-off for the
final long-term workflow.

Still missing or intentionally rough:

- ComfyUI is not yet called by a repo-owned adapter.
- Background prompt creation is still a human/LLM step.
- `inputs/song_style_prompt.txt` is captured for future image generation, but
  no repo-owned ComfyUI prompt adapter consumes it yet.
- Generated image/video approval is not yet represented as a first-class queue.
- Candidate/approved/final artifact states are not yet modeled.
- Section-level visual planning is not yet modeled.
- Safe-crop previews and subtitle proof frames are not yet generated.
- Whisper-to-real-lyrics alignment is intentionally a rough first pass.
- Timing review still happens through CLI helpers and proof renders, not a GUI.
- Human click timing remains a future capture mode, not the default path.

None of those block a basic draft lyric video from a new song folder.

Future GUI/state planning is tracked in
[Future GUI Roadmap](../roadmap/future-gui.md).
