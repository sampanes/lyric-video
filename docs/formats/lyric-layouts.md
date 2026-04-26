# Lyric Layouts

Lyric layout defines how reviewed lyric timing is presented on screen. It is
separate from render target. A vertical video can use the same timing as a
horizontal video while choosing a different layout.

## Current Layout

`standard`

- Shows the current lyric line or phrase.
- Uses target-specific margins and wrapping.
- Keeps open space for subtle background visuals.
- This is the default layout used by the current scripts.

`fullscreen`

- Makes lyrics the dominant visual element.
- Uses larger type and more central placement.
- Useful when the background is simple or when readability matters more than
  atmosphere.

`soft_scroll`

- Moves each lyric line gently upward with fade-in/fade-out.
- Uses reviewed timing and authoritative lyrics.
- Keeps the feel closer to readable lyric flow than novelty crawl text.
- This is a first implementation, not final karaoke/word-level timing.

Current helper:

```powershell
python scripts\make_videos.py "song name" --force --targets horizontal --layout fullscreen
python scripts\make_videos.py "song name" --force --targets horizontal --layout soft_scroll
python scripts\render_vibe_video.py "song name" assets\backgrounds\clip.mp4 --layout fullscreen --variant vibe-fullscreen
```

## Planned Layouts

`rolling`

- Shows nearby lyric context instead of only the active line.
- Can reduce the need for perfect micro-timing because the viewer sees the
  current lyric in sequence with surrounding lines.
- Should still render from reviewed timing and authoritative lyrics.
- A first version can highlight the current line while showing previous and
  next lines at lower opacity.

`karaoke`

- Highlights words or syllables over time.
- This requires word-level timing, so it should remain a later feature unless
  WhisperX alignment or manual review makes word timing cheap enough.

## Rules

- Rendered text must come from authoritative lyrics, not Whisper transcript
  text.
- Layout modes should not change the reviewed timing file.
- If a layout mode produces a distinct output, include the layout name in the
  export metadata and, when useful, the filename.
- Rolling, soft-scroll, and karaoke layouts should be optional. The base
  pipeline should stay simple and readable.
