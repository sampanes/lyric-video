# Transcript Assist

This document describes the rough transcript artifacts produced by Whisper or
WhisperX.

## Purpose

Transcription is an acceleration step.

It can help produce:

- rough lyric text
- rough timestamps
- candidate alignment data for later review

It is not the source of truth for lyrics.

## Intended Use

Use transcription output in one of two ways:

1. As a head start when entering lyrics manually.
2. As an alignment aid when reconciling generated text with actual lyrics.

## Recommended Artifact Shape

Store transcription output under `songs/<song>/timing/raw/whisper/`.

Example:

```json
{
  "song_id": "template_song",
  "source": "whisperx",
  "model": "medium",
  "segments": [
    {
      "start_ms": 1200,
      "end_ms": 2400,
      "text": "rough generated lyric text"
    }
  ]
}
```

If word-level timestamps are available, keep them in the same artifact or a
sidecar file.

The current helper merge writes `timing/derived/whisper_line_mapping.json`.
That file records which authoritative lyric lines were assigned to each raw
Whisper segment. It is a review/debug artifact, not the final render source.

## Notes

- Keep the raw transcription artifact separate from reviewed timing.
- Do not overwrite actual lyrics with generated text.
- Use the same base filename when pairing transcript, timing, and review data.
- Whisper output can be wrong on sung audio and unusual words. Use actual lyrics
  as the authoritative text when merging.
- Render from `timing/reviewed/timing.json`, not directly from raw Whisper
  output or the derived mapping file.
