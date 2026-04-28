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
- loads `timing/reviewed/timing.json`
- lets the user select lyric rows
- lets the user set starts/ends from the playhead
- lets the user drag selected start/end handles on the waveform
- saves reviewed timing with a backup
- can run a proof render through `scripts/render_song.py`

This is intentionally not a full GUI yet. It is the command-launched timing
review foundation.
