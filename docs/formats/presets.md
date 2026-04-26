# Presets

Presets are named render-time defaults stored under `presets/`.

They are for repeatable habits, not song identity. A preset can say "horizontal
kid education format with this readable font"; the song package still owns the
audio, lyrics, timing, title, style prompt, and final exports.

## Current Fields

```json
{
  "id": "kid_youtube_education",
  "label": "Kid YouTube Education",
  "description": "Human-readable purpose",
  "layout": "standard",
  "output": {
    "targets": ["horizontal"],
    "fps": 30
  },
  "subtitle_style": "kid_readable",
  "subtitle": {
    "font": "Arial Rounded MT Bold",
    "primary_colour": "&H00FFFFFF",
    "outline_colour": "&H00412C12",
    "back_colour": "&H99000000",
    "bold": true
  },
  "prompt_defaults": {
    "audience": "kids",
    "mood": "bright, clear, friendly, educational"
  }
}
```

## Precedence

- CLI flags override presets.
- Presets override matching render defaults from `song.json`.
- `song.json` remains the persistent song-level source of truth.
- Hardcoded script defaults are only used when neither CLI nor preset nor config
  provides a value.

## Currently Applied

The current basic renderer applies:

- `layout`
- `output.targets`
- `output.fps`
- `subtitle_style`
- `subtitle.font`
- ASS subtitle colors and bold setting under `subtitle`

Supported layout values are:

- `standard`
- `fullscreen`
- `soft_scroll`

## Future Use

`prompt_defaults` exists for the future ComfyUI adapter. It should be combined
with song-specific `song_vibes` and `inputs/song_style_prompt.txt`, not used as
a replacement for them.
