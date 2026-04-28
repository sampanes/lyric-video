# Timing Review Workflow

Whisper, WhisperX, even timing, and future click capture are draft timing
sources. They exist to make the first pass cheaper. They are not expected to
produce ship-ready lyric timing for sung audio.

The render source of truth remains:

```text
songs/<song>/timing/reviewed/timing.json
```

## Current Strategy

Use automation to get close, then make human correction cheap.

Recommended loop:

1. Generate draft timing with `make_videos.py`.
2. Render a proof video.
3. Watch for the first section that feels early, late, blank, or compressed.
4. Adjust the reviewed timing file with `scripts/timing_adjust.py`.
5. Re-render from reviewed timing.
6. Repeat in song-sized chunks.

Do not keep tuning Whisper alignment forever when the issue is really musical
timing. The durable product feature is a fast timing review interface.

This loop must be runnable without an LLM. The LLM can help interpret a bad
section or suggest a command, but the stable workflow is the command sequence
below.

## Review Helper

Use `timing_adjust.py` instead of editing milliseconds in JSON by hand.

Show the whole timing file:

```powershell
python scripts\timing_adjust.py report "song name"
```

Show a small window around a lyric line:

```powershell
python scripts\timing_adjust.py report "song name" --around "there was no first human"
```

Move one lyric line or a range later:

```powershell
python scripts\timing_adjust.py nudge "song name" --from line_020 --to line_026 --shift +0.35s
```

Move a range earlier:

```powershell
python scripts\timing_adjust.py nudge "song name" --from line_020 --to line_026 --shift -250ms
```

Fit a section between two anchor times while preserving relative spacing inside
the section:

```powershell
python scripts\timing_adjust.py fit "song name" --from line_020 --to line_026 --start-at 0:37.900 --end-at 0:47.800
```

Use `--dry-run` on `nudge` or `fit` to preview without writing.

Every write creates a backup under:

```text
songs/<song>/timing/reviewed/backups/
```

After a write, re-render from reviewed timing:

```powershell
python scripts\render_song.py "song name" --targets horizontal --layout soft_scroll
```

Then watch the proof again and repeat. The human judgment is listening and
deciding what feels early or late; the command performs the edit.

## Selector Rules

Line selectors can be:

- segment ids, such as `line_020`
- one-based line numbers, such as `20`
- unique text fragments, such as `there was no first human`

Text fragments must match only one segment. If a phrase repeats, use the segment
id or line number.

## Future Timing GUI

The eventual GUI should make the same edits visually.

Minimum useful timing GUI:

- audio player with waveform or progress display
- rough waveform packets or amplitude blocks from the source audio
- zoomed selected-line waveform for fine edits
- reviewed lyric rows from `timing/reviewed/timing.json`
- current playhead and active line highlight
- draggable start/end handles per line
- range selection for verse/chorus chunks
- nudge buttons for earlier/later by small increments
- separate start-only and end-only nudge controls for fine tuning
- keyboard shortcuts for play, pause, mark start, mark end, and advance line
- save button that backs up the previous reviewed timing
- proof render button that calls the existing scripts

The GUI should write reviewed timing only. It should not mutate raw lyrics,
Whisper output, or generated transcript artifacts.

Timing review should be audio-first. Generated background video is not required
for the user to correct lyric timing because the task is aligning words to
sounds. Video proof renders come after timing edits.

Current launch command:

```powershell
python scripts\launch_review_ui.py --song "song name"
```

The current GUI is intentionally narrow. It loads song state from the repo,
serves the configured audio file, displays rough browser-decoded waveform
packets, adds a zoomed selected-line waveform for fine edits, lets the user
adjust reviewed timing, saves with a backup, and can run a horizontal
soft-scroll proof render.

## Why This Matters

For music, exact lyric timing is an editorial task. Whisper is useful because it
gets the draft into the right neighborhood, but the final timing should be a
quick human review pass, not a fragile attempt to infer musical intent.
