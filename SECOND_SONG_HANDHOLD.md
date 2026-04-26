# Second Song Hand-Hold Guide

This guide records the exact second-song workflow as we do it.

The goal is to make the process repeatable without needing to remember the
conversation.

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

Source files found in the repo root:

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

## Step 2: Inspect Without Changing Anything

Run:

```powershell
python scripts\inspect_song.py "second-song-demo"
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

## Current Rule Of Thumb

Start boring:

1. inspect
2. fast horizontal draft
3. validate
4. Whisper/all-target pass
5. optional fullscreen draft

Do not start with ComfyUI or GUI work until the song package passes the basic
pipeline.
