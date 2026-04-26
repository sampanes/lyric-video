# Render Presets

Presets capture repeatable render habits without changing preserved song
inputs. Use them when a future version of you knows the format in advance, for
example "kid education horizontal only" or "shorts vertical only".

Current command shape:

```powershell
python scripts\make_videos.py "song name" --preset kid_youtube_education
```

Precedence:

- explicit CLI flags win
- then preset defaults
- then `song.json`
- then hardcoded safe defaults

Presets are render-time defaults. They should not move files, rewrite lyrics, or
replace reviewed timing.

