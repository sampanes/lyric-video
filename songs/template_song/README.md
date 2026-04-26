# Example Song

Template song package showing the expected long-term layout.

Start here when creating a real song folder:

- copy this folder to a new song slug
- run `python scripts/intake_song.py man-behind-the-bar` to create or update
  `song.json`
- fill in `song.json`
- set `title` to the Caps Version of the folder name if needed
- record the creative brief in `song_vibes`
- paste optional visual/style direction into `inputs/song_style_prompt.txt`;
  aliases such as `song-vibes.txt`, `vibes.txt`, `description.txt`, or
  `prompt.txt` are also recognized and ignored during lyric detection
- use `output.targets` for default render targets, or override with the
  `--targets` CLI flag
- add audio and raw lyrics anywhere in the song folder if you want the intake
  script to auto-detect them
- or place them directly under `inputs/audio/` and `inputs/lyrics/`
- put raw/imported source video clips, such as ComfyUI MP4 exports, under
  `inputs/video/`
- put processed render-ready background loops or stills under
  `assets/backgrounds/`
- final videos always go under `exports/`
