# Review UI

Local browser UI for reviewing lyric timing against song audio.

Launch from the repository root:

```powershell
python scripts\launch_review_ui.py --song "approximate song name"
```

Current scope:

- loads song package state from repo scripts
- plays the configured audio file
- shows rough waveform packets in the browser
- shows a zoomed selected-line waveform for fine edits
- loads `timing/reviewed/timing.json`
- lets the user select lyric rows
- lets the user set starts/ends from the playhead
- lets the user drag selected start/end handles on the waveform
- offers whole-line, start-only, and end-only nudge buttons down to 5ms
- saves reviewed timing with a backup
- can run a proof render through `scripts/render_song.py`

Save behavior:

- the current working file is always `timing/reviewed/timing.json`
- each save overwrites that current working file
- before overwrite, the previous version is copied into
  `timing/reviewed/backups/`
- reopening the UI loads `timing/reviewed/timing.json`, not an older backup
- unsaved edits mark the save button with `*`
- switching songs or closing the tab warns when timing edits are unsaved
- proof render prompts to save first because renders read the saved
  `timing.json`

This is intentionally not a full GUI yet. It is the command-launched timing
review foundation.
