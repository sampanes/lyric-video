# LLM Instructions

This repository is meant to be worked by future LLMs and agents directly.

Use this file as the operating guide when you are asked to make changes in the
repo.

## Repo Goal

Build a reusable lyric-video pipeline that works from per-song inputs:

- audio
- lyrics
- timing data
- background assets
- render settings

The repo should stay generalized. Do not hardcode a single song into engine
code.

## Default Workflow

When a user refers to a song by slug or name, for example
`man-behind-the-bar`, do this:

1. Search `songs/` for the matching folder.
2. If the folder exists, inspect its current contents and follow the file
   contract.
3. If the folder does not exist, copy the structure from `songs/template_song/`.
4. If metadata is missing, ask the user for:
   - song title
   - artist or creator name if relevant
   - a `song_vibes` description
   - `bpm` if the user already knows it
   - any render or style preferences that matter
5. Default the song title to a Caps Version of the folder name when the user
   does not provide one.
6. Detect a unique audio file and a unique lyric file when they exist anywhere
   in the song folder.
7. Ignore `inputs/song_style_prompt.txt` and known vibe/description aliases
   such as `song-vibes.txt`, `vibes.txt`, `description.txt`, or `prompt.txt`
   during lyric-file detection.
8. Normalize audio and lyrics into `inputs/audio/` and `inputs/lyrics/` when
   possible.
9. Use bracketed lyric tags and/or `inputs/song_style_prompt.txt` to populate
   `song_vibes` when config is created or refreshed automatically.
10. Ask only when the audio or lyric input is ambiguous.
11. Put rough transcription or capture artifacts in `timing/raw/`.
12. Put reviewed timing in `timing/reviewed/`.
13. Put derived subtitles in `subtitles/`.
14. Put raw/imported source video clips in `inputs/video/`.
15. Put processed renderer-ready background stills and loops in
    `assets/backgrounds/`.
16. Put render outputs in `renders/` and final deliverables in `exports/`.
17. Remove copied `.gitkeep` files from real song folders. Keep them in
    `songs/template_song/`.
18. Use `presets/` for repeatable output habits instead of hardcoding one
    format into a song or script.

## Timing and Lyrics Rules

- Treat actual lyrics as authoritative.
- Treat Whisper or WhisperX output as a helper input, not the final lyric text.
- Use raw transcript output as a head start for review and alignment.
- Keep raw timing separate from reviewed timing.
- Treat Whisper timing as a draft for sung audio. When timing is close but not
  good enough, prefer reviewed timing edits over repeated mapper tweaks.
- Preserve original inputs under `inputs/`.
- Write cleaned lyric artifacts under `timing/derived/`.

## Whisper / WhisperX Rules

If transcription is useful:

- use an existing external Whisper/WhisperX environment instead of duplicating
  it in this repo
- set `WHISPERX_EXE` to the local `whisperx` executable when it is not already
  on `PATH`
- do not duplicate that environment in this repo
- do not check large model files into this repo
- keep model caches outside this repo; use normal user cache locations or local
  environment variables such as `HF_HOME` when needed

Store Whisper output under `songs/<song>/timing/raw/whisper/`.

Use `scripts\whisper_song.py` for the current WhisperX pass. The local WhisperX
CLI has no dedicated music mode, so use the written lyrics as prompt context and
expect the output to be a rough timing aid.

## File Contract

Use the docs in `docs/architecture/` and `docs/formats/` as the source of
truth for:

- song config shape
- timing event shape
- file pairings
- render metadata
- workflow assumptions

## ComfyUI Rules

ComfyUI is optional.

Use it as an adapter for background stills or simple assets, not as the core
renderer.

Routine ComfyUI use should be command-driven through the local API server. Do
not require the user to click around the ComfyUI browser UI for normal
generation. Use `scripts\comfyui_server.py` to check/start the server and
`scripts\comfyui_queue.py` to queue exported API workflow JSON. Machine-local
ComfyUI paths may live in ignored `LOCAL_CONFIG.json`.

When the user provides a ComfyUI workflow exported from the UI, put durable
copies under `workflows/comfyui/node-graphs/` and document which node fields are
song-driven. See `docs/workflows/comfyui-vibe-motion.md` for the background
motion plan.

When the user provides ComfyUI output media, keep raw MP4 exports under
`songs/<song>/inputs/video/`. Put bounce loops, cropped versions, selected
background clips, and stills that the renderer should use under
`songs/<song>/assets/backgrounds/`.

Do not ask the user to drag-drop generated media into the repo. Normal ComfyUI
automation should set output paths directly or use a repo-owned adapter that
writes to the correct song package paths. If media already exists in a generator
output folder because of a one-off/manual experiment, `scripts\import_media.py`
can preview and import approved files, but it is not the intended normal path.

For future image-generation prompts, use `song_vibes` plus the raw user-editable
`inputs/song_style_prompt.txt` when present. Do not treat this file as lyrics.

## Implementation Style

- Prefer repo-owned docs and code over temporary notes.
- Keep scripts small and separable.
- Validate inputs early.
- Preserve reproducibility in outputs and metadata.
- When in doubt, favor the simplest path that supports the real song data.
- Do not describe a repeatable workflow as "the LLM did it." If an agent runs a
  step, document the command, file operation, or script path a human can use
  without an LLM.
- For machine-readable state, prefer `inspect_song.py --json` and
  `guide_song.py --json`. Do not build GUI assumptions by scraping
  human-readable terminal output.

## What To Do On a Song Task

If the user says something like:

> search man-behind-the-bar in songs and make me the stuff I need

then the expected response is to:

- locate the song folder
- ask for missing metadata, especially title and `song_vibes`
- detect the audio and lyrics files, and only ask if there is ambiguity
- create any missing config or timing scaffolding from the template
- generate the derived artifacts requested by the user
- keep reviewed outputs separate from raw inputs

Do not invent a new structure if the existing template already covers the need.

For the current one-shot basic lyric video path, run:

```powershell
python scripts\make_videos.py "approximate song name" --force
```

For the current one-shot Whisper-assisted path, run:

```powershell
python scripts\make_videos.py "approximate song name" --refresh-whisper
```

That command should be preferred when the user wants better-than-even timing and
is willing to wait for WhisperX. It preserves raw inputs, writes Whisper output
under `timing/raw/whisper/`, writes machine-cleaned lyric artifacts under
`timing/derived/`, writes merged timing under `timing/reviewed/`, and renders a
basic MP4 under `exports/`.

If the user reports that a section is early, late, blank, or shifted after the
Whisper-assisted pass, use the timing review helper before editing JSON:

```powershell
python scripts\timing_adjust.py report "approximate song name" --around "unique lyric text"
python scripts\timing_adjust.py nudge "approximate song name" --from line_020 --to line_026 --shift +0.35s
python scripts\timing_adjust.py fit "approximate song name" --from line_020 --to line_026 --start-at 0:37.900 --end-at 0:47.800
```

Use `--dry-run` first when the edit is uncertain. Each write backs up the
previous reviewed timing under `timing/reviewed/backups/`.

For multi-aspect output, add render targets:

```powershell
python scripts\make_videos.py "approximate song name" --targets all
```

Supported targets are `horizontal`, `vertical`, `square`, and `portrait`.
`--targets all` renders all of them. Rendered lyric text must come from the
authoritative reviewed timing, not from Whisper text. Each target gets its own
ASS subtitle file and MP4 export.

For large centered lyrics, add:

```powershell
python scripts\make_videos.py "approximate song name" --force --targets horizontal --layout fullscreen
```

For a gentle scrolling lyric treatment, add:

```powershell
python scripts\make_videos.py "approximate song name" --force --targets horizontal --layout soft_scroll
```

For a repeatable format habit, use a preset:

```powershell
python scripts\make_videos.py "approximate song name" --preset kid_youtube_education
```

Preset defaults are render-time only. CLI flags override presets, presets
override matching render defaults from `song.json`, and `song.json` still owns
song-specific identity and file paths.

Before GUI work, prove the ComfyUI background path headlessly:

```powershell
python scripts\comfyui_queue.py workflows\comfyui\node-graphs\basic_flux_t2i.api.json --song "approximate song name" --dry-run
```

Normal order is still image first, then image-to-video from the approved still.
Using an existing still image is acceptable for a queue-path test only. For the
first I2V attempt, use tiny probe settings such as `--length 9` and
`--set "3.inputs.steps=4"` with a song-specific positive prompt. Do not treat
`832x480` as bad by default; it has worked before. The probe is for isolating
prompt/source/runtime problems before spending a full Wan run.

Only run without `--dry-run` when a local ComfyUI server is running and the
workflow's source image/model requirements are satisfied.

For repo health checks without a real song, run:

```powershell
python scripts\smoke_test.py
```

Before public pushes or commits intended for GitHub, run:

```powershell
python scripts\privacy_check.py --include-untracked
```

To inspect a song folder without changing it, run:

```powershell
python scripts\inspect_song.py "approximate song name"
python scripts\inspect_song.py "approximate song name" --json
python scripts\guide_song.py "approximate song name"
```

For read-only validation after a song has config, run:

```powershell
python scripts\validate_song.py "approximate song name" --require-timing --check-tools
```

For copied placeholder cleanup, run:

```powershell
python scripts\prune_gitkeep.py "approximate song name"
```

For future lyric display modes, use `docs/formats/lyric-layouts.md` as the
source of truth. Rolling lyrics are intended to reduce sensitivity to
micro-timing issues; karaoke lyrics require word-level timing and should remain
optional.
