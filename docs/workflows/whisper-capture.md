# Whisper Capture Workflow

This workflow uses Whisper or WhisperX to generate a rough transcript with
timestamps and then turns that into a reviewed lyric timing file.

## Why This Exists

Whisper can speed up the first pass on a song by producing candidate text and
timestamps.

The useful output is not the raw transcript itself. The useful output is the
reviewed alignment after the transcript is compared against the real lyrics.

## Current Local Setup

Use an existing external environment instead of duplicating it.

Recommended local setup:

- keep the Whisper/WhisperX venv outside this repo
- install `openai-whisper`, `faster-whisper`, and `whisperx` there
- set `WHISPERX_EXE` to that venv's `whisperx` executable when it is not on
  `PATH`
- keep Whisper and Hugging Face model caches outside this repo

PowerShell example:

```powershell
$env:WHISPERX_EXE = "path\to\whisper-env\Scripts\whisperx.exe"
```

## Recommended Workflow

1. Normalize the source audio if needed.
2. Run Whisper or WhisperX from the existing venv.
3. Save the raw transcript and timestamps into `songs/<song>/timing/raw/`.
   Prefer `timing/raw/whisper/` for Whisper outputs.
4. Keep the actual lyric text in `songs/<song>/inputs/lyrics/`.
5. Use a merge or alignment step to compare generated text against the real
   lyrics.
6. Review the merged result and write the result into
   `songs/<song>/timing/reviewed/`.
7. Generate ASS subtitles from the reviewed timing.
8. Render the final video.

The current one-shot version of that workflow is:

```powershell
python scripts\make_videos.py "man behind the bar" --refresh-whisper
```

That command preserves the raw audio and raw lyric file, writes WhisperX output
under `timing/raw/whisper/`, writes cleaned lyric artifacts under
`timing/derived/`, writes merged timing under `timing/reviewed/`, and renders
the MP4 under `exports/`.

## Merge Strategy

The merge step should treat the generated transcript as a candidate, not as
truth.

Reasonable inputs to the merge step:

- generated transcript with timestamps
- actual lyric text
- optional human corrections

Reasonable outputs from the merge step:

- cleaned lyric lines
- aligned segment timing
- review notes for uncertain sections

## Practical Notes

- Do not copy the venv into this repo.
- Do not check model files into this repo.
- Link to the existing environment by path or by an environment variable such
  as `WHISPERX_EXE`.
- If a machine-specific install location is needed, keep it in an ignored local
  environment file, shell profile, or ignored `LOCAL_PATHS.md`, not in tracked
  repo docs or scripts.
- WhisperX does not have a dedicated music mode in the local CLI. Start with
  English transcription plus an initial prompt derived from the written lyrics.
- Preserve the raw user files. Put cleaned lyric artifacts under
  `timing/derived/`.

Current command:

```powershell
python scripts\whisper_song.py "man behind the bar"
```

Current render-from-Whisper command:

```powershell
python scripts\make_videos.py "man behind the bar" --refresh-whisper
```
