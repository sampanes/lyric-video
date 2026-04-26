# Timing Events

This document defines the raw and reviewed timing model used by the pipeline.

## Purpose

Timing should be captured as events first, then normalized into a render-ready
file.

This keeps the repo open to:

- human click capture
- keyboard-triggered capture
- automation output
- future alignment tools

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
