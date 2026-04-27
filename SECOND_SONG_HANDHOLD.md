# Second Song Hand-Hold Guide

This guide records the repeatable second-song workflow.

The goal is to make the process repeatable without needing to remember the
conversation and without requiring an LLM to operate the pipeline.

## No-LLM Contract

The LLM is allowed to be an operator while the workflow is still maturing, but
the workflow is not allowed to depend on the LLM.

For each normal song, a human should be able to:

1. Put the audio file and raw lyric file into a song folder.
2. Run the commands in this guide.
3. Watch the generated proof video.
4. Use timing helper commands for small timing corrections.
5. Re-render and validate.

Optional LLM help:

- interpret validation errors
- suggest timing ranges after the user describes what feels early or late
- write or improve repo-owned scripts
- generate background/image prompts from `song_vibes`

Not acceptable as the only workflow:

- "the LLM moved files somehow"
- "the LLM edited timing JSON by hand"
- "the LLM remembered the command"
- "the LLM knows where outputs went"

If an LLM performs a step, it should still report the command or file operation
that a human would run next time.

## Song

Working slug:

```text
second-song-demo
```

Song folder:

```text
songs/second-song-demo/
```

## Step 1: Move Raw Inputs Into A Song Workspace

User/meatspace task:

- create or choose one folder under `songs/`
- put one audio file in it
- put one raw lyric file in it
- optionally put one style/vibe text file in it

Example source files found in a song folder or repo root:

```text
Second Song Demo.mp3
Second Song Demo.txt
```

Created directories:

```text
songs/second-song-demo/inputs/audio/
songs/second-song-demo/inputs/lyrics/
```

Moved files:

```text
Second Song Demo.mp3
-> songs/second-song-demo/inputs/audio/Second Song Demo.mp3

Second Song Demo.txt
-> songs/second-song-demo/inputs/lyrics/Second Song Demo.txt
```

Why:

- `songs/<song>/` keeps each song isolated.
- `inputs/audio/` preserves the original audio input.
- `inputs/lyrics/` preserves the original user-provided lyric text.
- Real song folders are ignored by git, so large/private source media stays
  local.
- No `song.json` was created by hand. The script should create it from the
  detected audio and lyric files during the first render/test pass.

Human command option:

```powershell
New-Item -ItemType Directory -Force songs\second-song-demo\inputs\audio
New-Item -ItemType Directory -Force songs\second-song-demo\inputs\lyrics
Move-Item "Second Song Demo.mp3" songs\second-song-demo\inputs\audio\
Move-Item "Second Song Demo.txt" songs\second-song-demo\inputs\lyrics\
```

Script option:

If the files are already somewhere under `songs/second-song-demo/`, run:

```powershell
python scripts\intake_song.py "second-song-demo"
```

That script detects a single audio file and a single lyric file, moves them into
canonical locations, asks for metadata, and writes `song.json`.

## Step 1.1: Add Optional Song Style Prompt

The canonical optional style prompt path is:

```text
songs/second-song-demo/inputs/song_style_prompt.txt
```

The second-song demo originally had:

```text
songs/second-song-demo/inputs/description.txt
```

That file was normalized to:

```text
songs/second-song-demo/inputs/song_style_prompt.txt
```

Why:

- `song_style_prompt.txt` is the stable template name.
- It is a raw user-editable creative direction file.
- It is ignored during lyric detection.
- It should be used later to guide image/background prompt generation.

Human command option:

```powershell
New-Item -ItemType Directory -Force songs\second-song-demo\inputs
notepad songs\second-song-demo\inputs\song_style_prompt.txt
```

Paste a short creative brief if you have one. Leave the file empty or absent if
you do not.

## Step 2: Inspect Without Changing Anything

Run:

```powershell
python scripts\inspect_song.py "second-song-demo"
```

Machine-readable version for future GUI/automation:

```powershell
python scripts\inspect_song.py "second-song-demo" --json
```

Self-service operator checklist:

```powershell
python scripts\guide_song.py "second-song-demo"
python scripts\guide_song.py "second-song-demo" --json
```

Expected:

- one audio candidate
- one lyric candidate
- missing `song.json`
- next command points to `make_videos.py`

If this reports ambiguity, stop and fix the folder before rendering.

Result on 2026-04-25:

```text
Audio candidates: 1
Lyric candidates: 1
Config: missing
Reviewed timing: missing
Next: python scripts\make_videos.py "second-song-demo" --force --targets horizontal
```

Interpretation:

- Missing config/timing/subtitles/exports were expected.
- They are script-generated artifacts, not user/meatspace tasks.
- The raw audio and lyrics were sufficient to start.

Human decision:

- If audio candidates is `0`, add an audio file.
- If lyric candidates is `0`, add a lyric text file.
- If either candidate count is greater than `1`, remove extras or run
  `intake_song.py` and choose the correct file when prompted.
- If config is missing but there is exactly one audio and one lyric file, that
  is fine.

## Step 3: Fast Draft Render

Run:

```powershell
python scripts\make_videos.py "second-song-demo" --force --targets horizontal
```

Expected outputs:

```text
songs/second-song-demo/song.json
songs/second-song-demo/timing/derived/lyrics_clean.txt
songs/second-song-demo/timing/derived/lyrics_clean.json
songs/second-song-demo/timing/reviewed/timing.json
songs/second-song-demo/subtitles/lyrics.horizontal.ass
songs/second-song-demo/exports/second-song-demo.horizontal.mp4
```

This uses even timing. It is only a structure/render smoke test, not final
timing.

If you know the output should follow a repeatable habit, use a preset instead:

```powershell
python scripts\make_videos.py "second-song-demo" --preset kid_youtube_education
```

The first preset is a horizontal kid-education render style with a readable
rounded font. It does not change the preserved audio, lyrics, timing, or
`inputs/song_style_prompt.txt`.

Result on 2026-04-25:

```text
Wrote songs/second-song-demo/timing/reviewed/timing.json
Wrote songs/second-song-demo/subtitles/lyrics.horizontal.ass
Wrote songs/second-song-demo/exports/second-song-demo.horizontal.mp4
```

Output file:

```text
songs/second-song-demo/exports/second-song-demo.horizontal.mp4
```

Human decision:

- Open the MP4 and confirm the song plays, text renders, and output path makes
  sense.
- Do not judge final timing from this pass unless you intentionally used even
  timing as a placeholder.

## Step 4: Validate The Song Package

Run:

```powershell
python scripts\validate_song.py "second-song-demo" --require-timing --check-tools
```

Expected:

```text
Song validation passed
```

If validation fails, fix that before running Whisper or all aspect ratios.

Result on 2026-04-25:

```text
Song validation passed: songs/second-song-demo
```

Generated config:

- `title`: `Second Song Demo`
- `audio`: `inputs/audio/Second Song Demo.mp3`
- `lyrics`: `inputs/lyrics/Second Song Demo.txt`
- `background_mode`: `solid`
- `song_vibes`: seeded from bracketed lyric tags

Text encoding note:

- A PowerShell `Get-Content` display made some curly quotes look like
  mojibake, but byte/Unicode inspection confirmed the raw lyric file is valid
  UTF-8.
- Example confirmed source line:
  `“Hey, that one’s different”?`
- The pipeline preserved the proper curly quotes in derived lyrics and ASS
  subtitles.
- Validation now warns only if actual suspicious mojibake markers are present
  in the UTF-8 file content.

Human decision:

- A validation failure is a blocker.
- A warning is reviewable context; fix it if it points to a real input problem.

## Step 5: Whisper-Assisted Timing Pass

Run:

```powershell
python scripts\make_videos.py "second-song-demo" --refresh-whisper --targets all
```

Expected:

- raw WhisperX output under `timing/raw/whisper/`
- reviewed timing regenerated under `timing/reviewed/timing.json`
- exports for `horizontal`, `vertical`, `square`, and `portrait`

This is still a draft. Whisper timing is a head start, not ship-ready truth.

Human decision:

- Watch the generated proof video.
- Write down the first bad range using lyric text or line ids.
- Do not expect Whisper to produce final music timing.

First run result on 2026-04-25:

```text
WhisperX failed with UnicodeEncodeError while printing transcript text to the
Windows console/codepage.
```

Fix applied:

- `scripts/whisper_song.py` now sets `PYTHONIOENCODING=utf-8` and
  `PYTHONUTF8=1` for the external WhisperX subprocess.
- This fixes Windows console encoding crashes without changing lyric text.

Second run result on 2026-04-25:

```text
Wrote timing/raw/whisper/Second Song Demo.json
Wrote timing/raw/whisper/whisperx_run.json
Wrote timing/reviewed/timing.json
Wrote subtitles/lyrics.horizontal.ass
Wrote subtitles/lyrics.vertical.ass
Wrote subtitles/lyrics.square.ass
Wrote subtitles/lyrics.4x5.ass
Wrote exports/second-song-demo.horizontal.mp4
Wrote exports/second-song-demo.vertical.mp4
Wrote exports/second-song-demo.square.mp4
Wrote exports/second-song-demo.4x5.mp4
```

Validation after Whisper/all-target render:

```text
Song validation passed: songs/second-song-demo
```

Non-fatal note:

- WhisperX printed a `torchcodec is not installed correctly` warning from its
  external environment, but the run still completed and produced JSON timing
  output plus all target renders.

## Step 5.1: Human Timing Review

Run a readable timing report around the first bad lyric:

```powershell
python scripts\timing_adjust.py report "second-song-demo" --around line_020
```

If the lyric phrase repeats, use the segment id or one-based line number instead
of a text phrase.

Preview a small nudge without writing:

```powershell
python scripts\timing_adjust.py nudge "second-song-demo" --from line_020 --to line_026 --shift +0.35s --dry-run
```

Apply it when the preview looks structurally sane:

```powershell
python scripts\timing_adjust.py nudge "second-song-demo" --from line_020 --to line_026 --shift +0.35s
```

Fit a range between two anchor times when a whole section needs stretching or
compressing:

```powershell
python scripts\timing_adjust.py fit "second-song-demo" --from line_020 --to line_026 --start-at 0:37.900 --end-at 0:47.800 --dry-run
```

Every write backs up the previous reviewed timing under:

```text
songs/second-song-demo/timing/reviewed/backups/
```

After a timing edit, re-render from reviewed timing:

```powershell
python scripts\render_song.py "second-song-demo" --targets horizontal --layout soft_scroll
```

Human decision:

- Repeat report, adjust, render until the proof is acceptable.
- This is the step that should eventually become sliders plus audio playback in
  a GUI.

## Step 6: Optional Fullscreen Lyric Draft

Run:

```powershell
python scripts\make_videos.py "second-song-demo" --force --targets horizontal --layout fullscreen
```

Expected output:

```text
songs/second-song-demo/exports/second-song-demo.horizontal.fullscreen.mp4
```

Use this when the lyric text should be the dominant visual.

## Step 7: Pre-GUI ComfyUI Headless Background MVP

Before building GUI controls for background generation, prove that the repo can
queue a ComfyUI workflow headlessly.

ComfyUI should act as a local API server. Routine generation should not require
clicking around the ComfyUI browser UI.

Check server status:

```powershell
python scripts\comfyui_server.py status
```

Start the server if needed:

```powershell
python scripts\comfyui_server.py start
```

If local paths are not configured yet, put them in ignored `LOCAL_CONFIG.json`
or set `COMFYUI_ROOT`, `COMFYUI_PYTHON`, `COMFYUI_INPUT_DIR`, and
`COMFYUI_OUTPUT_DIR` in the shell.

Dry-run first:

```powershell
python scripts\comfyui_queue.py workflows\comfyui\node-graphs\basic_flux_t2i.api.json --song "second-song-demo" --dry-run --filename-prefix "lyric-video/second-song-demo/still-mvp"
python scripts\comfyui_queue.py workflows\comfyui\node-graphs\basic_wan_i2v_subtle-3.api.json --song "second-song-demo" --dry-run
```

Generate a still first:

```powershell
python scripts\comfyui_queue.py workflows\comfyui\node-graphs\basic_flux_t2i.api.json --song "second-song-demo" --wait --filename-prefix "lyric-video/second-song-demo/still-mvp"
```

When the still is approved and visible to ComfyUI, animate it:

```powershell
python scripts\comfyui_queue.py workflows\comfyui\node-graphs\basic_wan_i2v_subtle-3.api.json --song "second-song-demo" --wait --timeout 900 --filename-prefix "lyric-video/second-song-demo/wan-probe" --positive-prompt "gentle sparkles, soft ambient shimmer, almost static, stable background, no camera movement" --length 9 --set "3.inputs.steps=4" --set "56.inputs.image=lyric-video/second-song-demo/still-mvp_00001_.png [output]"
```

If the workflow needs a specific image override:

```powershell
python scripts\comfyui_queue.py workflows\comfyui\node-graphs\basic_wan_i2v_subtle-3.api.json --song "second-song-demo" --wait --set "56.inputs.image=Flux2-Klein_00002_.png [output]"
```

Expected repo-side result:

```text
songs/second-song-demo/assets/backgrounds/<downloaded comfyui asset>
songs/second-song-demo/assets/backgrounds/<downloaded comfyui asset>.comfyui.json
```

This is not expected to be pretty yet. It only proves that a repo command can
drive ComfyUI and retrieve a rough background asset without manual drag/drop.

Do not start a new song/source-image I2V pass with the full Wan baseline. A
second-real-song test on 2026-04-26 timed out after 1800 seconds at `832x480`,
`length=33`, `steps=20`, and also reused the stale bar-room prompt from the
baseline workflow. `832x480` has worked before; the failure does not prove the
resolution is bad. The safer rule is:

- generate still first
- approve still
- run tiny I2V probe with song-specific prompt
- increase settings only after the probe completes

Follow-up passes showed that `832x480`, `length=33`, `steps=4` and `steps=8`
both complete. Treat `length=33`, `steps=8` as the first useful baseline, and
reserve `steps=20` for a slower quality test with a longer timeout.

## Current Rule Of Thumb

Start boring:

1. inspect
2. fast horizontal draft
3. validate
4. Whisper/all-target pass
5. human timing review
6. optional fullscreen or soft-scroll draft
7. headless ComfyUI background-video proof

Do not start with ComfyUI or GUI work until the song package passes the basic
pipeline.
