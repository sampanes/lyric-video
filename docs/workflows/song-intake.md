# Song Intake Workflow

This workflow defines the first questions an agent should ask when starting a
new song from a folder.

## Goal

Collect the minimum metadata needed to make the song usable without locking the
repo into any specific upstream source or generator.

## Ask First

When a new song folder is being created or updated, ask for:

- song folder name or slug
- song title
- artist or creator name if relevant
- `song_vibes`
- optional `bpm` if the user already knows it
- any style or render preferences that matter

## File Detection

If the song folder already contains source files:

- auto-detect a single audio file when there is exactly one clear match
- auto-detect a single lyric file when there is exactly one clear match
- ignore `inputs/song_style_prompt.txt` and known vibe/description text aliases
  such as `song-vibes.txt`, `vibes.txt`, `description.txt`, or `prompt.txt`
  during lyric detection
- move or normalize those files into the canonical `inputs/audio/` and
  `inputs/lyrics/` folders when possible
- create canonical song-package directories from the file contract when the
  pipeline touches a song
- ask only when there is no clear unique match

## Default Behavior

- If the user does not provide a title, use a Caps Version of the folder name.
- If the user does not provide an artist, leave it blank or use `Unknown Artist`
  depending on the context.
- If the user provides a loose vibe prompt, store it in `song_vibes`.
- If the user provides visual/style direction in `inputs/song_style_prompt.txt`,
  keep it as a raw input and use it to seed `song_vibes`/future image prompts.
- If the user provides BPM, store it in `bpm`. Do not block intake if BPM is
  unknown.
- Keep the vibe text in the config, not in a throwaway note.
- Remove copied `.gitkeep` files from real song folders after intake. They are
  useful in the tracked template but not needed in ignored production song
  folders.

## Recommended Intake Output

Create or update `songs/<song_name>/song.json` with the agreed metadata.

The expected result is a repo-owned record of:

- the song identity
- the creative direction
- optional BPM for future beat-synced visuals
- the source files that will be added next
- the canonical audio and lyric file locations

## Example

If the folder is `man-behind-the-bar`, a good default intake result would be:

- `title`: `Man Behind The Bar`
- `song_vibes`: `high energy, male vocalist, gritty bar-room feel`
- `bpm`: `null` unless known

## Notes

- Do not name this field after a specific upstream tool.
- Treat `song_vibes` as the user-facing creative brief for the song.
- Use the file contract in `docs/architecture/file-contract.md` for the rest of
  the folder layout.

## One-Shot Draft Render

After audio and lyrics exist in a song folder, the current draft render command
is:

```powershell
python scripts\make_videos.py "man behind the bar" --force
```

That command creates missing config, builds fallback line timing, writes ASS
subtitles, and renders a basic MP4.

When config is created by the render path, unique audio and lyric files are
normalized into `inputs/audio/` and `inputs/lyrics/`.

The render path also populates `song_vibes` from bracketed lyric tags and/or
`inputs/song_style_prompt.txt`.

If a copied song folder still has placeholder files, remove them with:

```powershell
python scripts\prune_gitkeep.py "man behind the bar"
```
