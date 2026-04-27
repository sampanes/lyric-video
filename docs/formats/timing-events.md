# Timing Events

This document defines the raw and reviewed timing model used by the pipeline.

## Purpose

Timing should keep raw evidence separate from the render-ready reviewed file.
Raw evidence can come from automatic alignment, imported timestamps, or future
human capture events.

This keeps the repo open to:

- human click capture
- keyboard-triggered capture
- automation output
- future alignment tools

Automation output should be treated as draft timing. Human-reviewed timing is
the version trusted by render scripts. Human review should eventually happen in
a GUI with playback and drag controls, not through hand-typed timestamp edits.

## Suggested Raw Event Shape

Raw capture should preserve what happened as directly as possible.

Example:

```json
{
  "session_id": "2026-04-25T10:00:00-07:00",
  "song_id": "template_song",
  "events": [
    {
      "type": "lyric_click",
      "time_ms": 12340,
      "label": "verse_01_line_01"
    }
  ]
}
```

## Suggested Reviewed Timing Shape

Reviewed timing should be normalized and easy to render from.

Example:

```json
{
  "song_id": "template_song",
  "segments": [
    {
      "id": "verse_01_line_01",
      "start_ms": 12340,
      "end_ms": 14500,
      "text": "Example lyric line"
    }
  ]
}
```

## Notes

- Raw timing is a capture artifact.
- Reviewed timing is the render source of truth.
- The reviewed file should be stable enough to regenerate subtitles.
- Keep file names and segment ids stable across revisions when possible.
- Timing review edits should preserve the original raw capture artifact.
- Timing edit tools should back up the reviewed timing file before writing.

## Review Operations

Human review can be represented as direct edits to reviewed timing or as future
operation logs.

Useful operation types:

- `nudge_range`: shift one or more lyric segments earlier or later
- `fit_range`: stretch or compress a lyric range between two anchor times
- `set_start`: set one segment start from the current playhead
- `set_end`: set one segment end from the current playhead

The current CLI helper writes the reviewed timing directly and stores backups.
A future GUI can record explicit operation logs if that becomes useful for undo,
audit, or comparison.

The CLI helper is a backend and transition path. The intended human interface is
a timing editor where the same operations happen through audio playback, active
lyric highlighting, draggable handles, and range controls.
