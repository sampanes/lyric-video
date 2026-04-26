# Scripts

Runnable entry points for the pipeline live here.

Current tools:

- `make_videos.py` is the high-level default entrypoint for "make videos" song
  tasks. It delegates to the current basic pipeline so the command name can stay
  stable as internals evolve.
- `smoke_test.py` runs a synthetic end-to-end render and validation pass without
  needing a real song.
- `inspect_song.py` prints a read-only status summary and the next likely
  command for a song folder.
- `validate_song.py` validates a song package. It is read-only by default; pass
  `--create-config` only when config creation is intentional.
- `make_basic_video.py` runs the current one-shot basic pipeline for a song:
  config creation, timing generation, ASS subtitles, and MP4 render. Add
  `--refresh-whisper` when you want it to run WhisperX first and use that rough
  timing evidence. Add `--preset kid_youtube_education` when you want a tracked
  repeatable render habit.
- `whisper_song.py` runs WhisperX from the external venv and stores raw
  transcript artifacts under `timing/raw/whisper/`.
- `intake_song.py` creates or updates `songs/<song>/song.json`, auto-detects
  the unique audio and lyric files when possible, and only asks for clarification
  when the input is ambiguous. It also removes copied `.gitkeep` files unless
  `--keep-gitkeep` is passed.
- `prune_gitkeep.py` removes copied `.gitkeep` files from a real song folder
  without touching the tracked template by default.
- `make_bounce_loop.py` creates a forward-then-reverse palindrome loop from a
  subtle generated background clip.
- `render_vibe_video.py` renders reviewed lyrics over a looping background
  video.
- `import_media.py` copies or moves approved image/video media into the correct
  song package location and writes an import metadata sidecar. This is an
  ad hoc utility for existing external media, not the intended normal ComfyUI
  adapter path.
- `capture_timings.py` and `generate_assets.py` are future-facing placeholders
  that print their planned role instead of raising Python tracebacks.

Example:

```powershell
python scripts\make_videos.py "man behind the bar" --refresh-whisper --targets all
python scripts\make_videos.py "man behind the bar" --force --targets horizontal --layout fullscreen
python scripts\make_videos.py "man behind the bar" --preset kid_youtube_education
python scripts\inspect_song.py "man behind the bar"
python scripts\smoke_test.py
python scripts\validate_song.py "man behind the bar" --require-timing --check-tools
python scripts\make_basic_video.py "man behind the bar" --force
python scripts\make_basic_video.py "man behind the bar" --refresh-whisper
python scripts\make_basic_video.py "man behind the bar" --targets all
python scripts\prune_gitkeep.py "man behind the bar"
python scripts\import_media.py "man behind the bar" --latest-from "$env:COMFYUI_OUTPUT_DIR" --type video --dry-run
python scripts\import_media.py "man behind the bar" "$env:COMFYUI_OUTPUT_DIR\ComfyUI_00004_.mp4" --role source-video
python scripts\make_bounce_loop.py songs\man-behind-the-bar\inputs\video\ComfyUI_00004_.mp4 --output songs\man-behind-the-bar\assets\backgrounds\bar_bg_loop_bounce.mp4
python scripts\render_vibe_video.py "man behind the bar" assets\backgrounds\bar_bg_loop_bounce.mp4 --target horizontal --variant vibe
python scripts\render_vibe_video.py "man behind the bar" assets\backgrounds\bar_bg_loop_bounce.mp4 --target horizontal --layout fullscreen --variant vibe-fullscreen
```

Target options are `horizontal`, `vertical`, `square`, `portrait`, or `all`.
They produce target-specific subtitle files and MP4 exports.

Use the separate Whisper command only when you want to inspect transcription
output without rendering:

```powershell
python scripts\whisper_song.py "man behind the bar"
```
