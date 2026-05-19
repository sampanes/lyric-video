# ComfyUI Vibe Motion Workflow

This workflow captures the long-term plan for subtle, song-aware background
videos generated through a sibling ComfyUI setup.

The goal is not a full cinematic music video. The goal is a cohesive moving
texture that supports the lyrics without competing with them.

## Intended End State

Given one song folder, the pipeline should be able to use:

- source audio
- reviewed lyric timing
- `song_vibes`
- optional `inputs/song_style_prompt.txt`
- optional `bpm`
- render target aspect ratio
- a ComfyUI workflow JSON exported by the user

and produce target-aware background videos or stills under:

```text
songs/<song>/assets/backgrounds/
```

Generated assets should have metadata sidecars that record prompt, seed, model,
workflow, target, BPM, and any adapter settings.

## File Placement

Use this split for every song:

- `inputs/video/` stores raw imported/user-provided video clips, including
  ComfyUI MP4 outputs exactly as produced.
- `assets/backgrounds/` stores renderer-ready stills, selected clips, cropped
  clips, palindrome loops, and their sidecar metadata.
- `exports/` stores final lyric-video deliverables.

Do not point future automation at random MP4s in the song root or directly
under `inputs/`. A ComfyUI adapter should set output paths deliberately and
write raw preserved clips into `inputs/video/` only when they need to be kept.
Render-ready background assets should be written into `assets/backgrounds/`.

The user should approve generated media, not manually move it. For the normal
future path, the adapter should write approved outputs directly to their final
song-package location. For one-off external files that already exist elsewhere,
an import step is available:

Set `COMFYUI_OUTPUT_DIR` locally or record it in ignored `LOCAL_PATHS.md`.

```powershell
python scripts\import_media.py "song name" --latest-from "$env:COMFYUI_OUTPUT_DIR" --type video --dry-run
python scripts\import_media.py "song name" "$env:COMFYUI_OUTPUT_DIR\ComfyUI_00004_.mp4" --role source-video
```

For an approved still image that is already renderer-ready:

```powershell
python scripts\import_media.py "song name" "$env:COMFYUI_OUTPUT_DIR\ComfyUI_00001_.png" --role background --name bg-main
```

Use `--dry-run` when the agent needs to show the candidate path for approval.

## Practical First Step

The first ComfyUI integration should be still-image generation, not animation.

Expected user handoff:

1. Build a generic workflow in ComfyUI UI.
2. Export the workflow JSON.
3. Put the workflow JSON under `workflows/comfyui/node-graphs/`.
4. Tell the agent which fields should be song-driven:
   - prompt
   - negative prompt
   - seed
   - width and height
   - output path
   - checkpoint or model
   - sampler settings, if relevant

The first adapter should replace those fields and call ComfyUI through its API.

Prompt planning should use:

- `song_vibes` from `song.json`
- raw visual/style direction from `inputs/song_style_prompt.txt` when present
- reviewed lyric sections once section modeling exists

The style prompt is user-provided creative direction. It should guide image
generation, but it should not replace reviewed lyrics or timing.

## ComfyUI Walkthrough Guidance

When another assistant is helping the user inside ComfyUI, its job is to guide
UI setup and workflow export, not to write this repo's Python code.

The walkthrough should produce one of these deliverables:

- a basic still-image workflow JSON
- a still-image workflow JSON that can switch between supported render target
  sizes
- later, a short loop workflow JSON for subtle motion textures

When the workflow works, record:

- workflow filename
- model or checkpoint used
- custom nodes required
- where prompt and negative prompt text live
- where width and height live
- where seed lives
- where output path or filename prefix lives
- whether the workflow needs extra model files
- whether it is suitable for low-VRAM use

Avoid ComfyUI workflows that generate captions, signs, lyric text, subtitles,
title cards, characters, faces, hands, or narrative action. The repo overlays
lyrics itself.

## Animation Plan

After still generation works, add subtle motion.

Candidate ComfyUI stack:

- `AnimateDiff-Evolved` for local animation
- Motion LoRAs for small camera moves such as zoom or pan
- `IP-Adapter-Plus` to keep animation cohesive with one reference still
- `VideoLinearCFGGuidance` to reduce long-clip melting

Conservative local plan:

- Generate a high-quality still first.
- Animate short clips, for example 32 frames.
- Use an SD1.5 animation backbone for lower VRAM pressure.
- Keep motion LoRA weights low, roughly `0.3` to `0.5`.
- Prefer subtle texture, slow camera movement, and low visual contrast behind
  lyrics.

## Current Wan Image-To-Video Baseline

The current reusable image-to-video API workflow is:

```text
workflows/comfyui/node-graphs/basic_wan_i2v_subtle-3.api.json
```

It came from the user's third local Wan image-to-video iteration:

- `JS-image_to_video_basic.json`: usable original subtle atmospheric loop.
- `JS-image_to_video_basic-2.json`: visually failed/trash iteration. Do not use
  it as a baseline.
- `JS-image_to_video_basic-3.json`: recovery iteration. Less happens, but the
  catastrophic visual breakdown from `*-2` is gone. This is the current useful
  subtle-motion baseline.

Important implementation differences observed:

| Workflow | Visual status | Seed | Denoise | Length | FPS | Prompt direction |
| --- | --- | --- | --- | --- | --- | --- |
| original | usable | `356364759852153` | `1` | `49` | `8` | dust motes, subtle natural motion, gentle light flicker |
| `*-2` | failed/trash | `1062137494137418` | `0.6` | `33` | `8` | locked camera, almost static, only slow dust, faint smoke |
| `*-3` | current subtle baseline | `216408885202616` | `1` | `33` | `8` | faint particles, very subtle natural motion, ambient light flicker |

The `*-3` negative prompt adds explicit artifact guards such as `melting`,
`stretching`, `streaks`, and `artifacts`. The prompt text itself is not source
of truth and should become song-driven later. The practical lesson is that local
Wan image-to-video is useful for tiny atmospheric motion, not for semantically
specific action like reliable falling dust.

Preserve numbered workflow iterations when experimenting so failures and
recoveries can be compared.

## Headless MVP Before GUI

Before building GUI controls for backgrounds, prove that this repo can queue a
ComfyUI workflow without using the ComfyUI browser UI.

Routine generation should not require clicking around ComfyUI. ComfyUI is used
as a local API server. The browser UI is only for creating or debugging exported
workflow JSONs.

Check whether the API server is already responding:

```powershell
python scripts\comfyui_server.py status
```

Start the local server from the sibling ComfyUI repository:

```powershell
$env:COMFYUI_ROOT = "path\to\ComfyUI"
python scripts\comfyui_server.py start
```

For this repo, machine-specific defaults may also live in ignored
`LOCAL_CONFIG.json`:

```json
{
  "comfyui": {
    "root": "<COMFYUI_PORTABLE_ROOT>",
    "python": "<COMFYUI_PORTABLE_PYTHON>",
    "input_directory": "<COMFYUI_INPUT_DIR>",
    "output_directory": "<COMFYUI_OUTPUT_DIR>"
  }
}
```

When that file exists, this is enough:

```powershell
python scripts\comfyui_server.py start
```

Stop a stuck backend:

```powershell
python scripts\comfyui_server.py stop
```

If ComfyUI needs a specific Python executable or venv:

```powershell
$env:COMFYUI_PYTHON = "path\to\ComfyUI\venv\Scripts\python.exe"
python scripts\comfyui_server.py start
```

Pass extra ComfyUI `main.py` arguments after `--`:

```powershell
python scripts\comfyui_server.py start -- --lowvram
```

Current generic queue helper:

```powershell
python scripts\comfyui_queue.py workflows\comfyui\node-graphs\basic_wan_i2v_subtle-3.api.json --song "song name" --dry-run
```

That command does not contact ComfyUI. It verifies that the workflow file can be
loaded and shows where outputs would be downloaded.

Normal generation order:

1. Generate a still image with the Flux text-to-image workflow.
2. Approve or reject the still.
3. Animate the approved still with the Wan image-to-video workflow.
4. Optionally bounce-loop the resulting clip.
5. Render lyrics over the approved background.

The existing Wan workflow references an older output image,
`Flux2-Klein_00002_.png [output]`. That is acceptable only as a queue-path test.
For real song work, produce a fresh still first and pass that image into the
image-to-video workflow.

Dry-run still generation:

```powershell
python scripts\comfyui_queue.py workflows\comfyui\node-graphs\basic_flux_t2i.api.json --song "song name" --dry-run --filename-prefix "lyric-video/song-name/still-mvp"
```

When the local ComfyUI API server is running, queue the still workflow:

```powershell
python scripts\comfyui_queue.py workflows\comfyui\node-graphs\basic_flux_t2i.api.json --song "song name" --wait --filename-prefix "lyric-video/song-name/still-mvp"
```

Then queue image-to-video using the approved still image:

```powershell
python scripts\comfyui_queue.py workflows\comfyui\node-graphs\basic_wan_i2v_subtle-3.api.json --song "song name" --wait --filename-prefix "lyric-video/song-name/wan-mvp"
```

For first I2V tests on a new song/source image, run a small probe first:

```powershell
python scripts\comfyui_queue.py workflows\comfyui\node-graphs\basic_wan_i2v_subtle-3.api.json --song "song name" --wait --timeout 900 --filename-prefix "lyric-video/song-name/wan-probe" --positive-prompt "gentle sparkles, soft ambient shimmer, almost static, stable background, no camera movement" --length 9 --set "3.inputs.steps=4" --set "56.inputs.image=lyric-video/song-name/still-mvp_00001_.png [output]"
```

Only increase `length` or steps after that probe completes. `832x480` has
worked before and remains the baseline size; the probe is about isolating
prompt/source/runtime issues, not declaring that resolution invalid.

`comfyui_queue.py` interrupts on timeout by default. If `/interrupt` does not
clear the running job, stop and restart the backend:

```powershell
python scripts\comfyui_server.py stop
python scripts\comfyui_server.py start
```

If the workflow depends on a specific source image, override the `LoadImage`
node with a ComfyUI-visible image name:

```powershell
python scripts\comfyui_queue.py workflows\comfyui\node-graphs\basic_wan_i2v_subtle-3.api.json --song "song name" --wait --set "56.inputs.image=Flux2-Klein_00002_.png [output]"
```

Completed output assets are downloaded into:

```text
songs/<song>/assets/backgrounds/
```

Each downloaded asset gets a `.comfyui.json` sidecar with the prompt id,
workflow path, server, source asset, and overrides.

This is intentionally low ambition. Success means "repo command can make or
retrieve a rough moving background," not "the background is good."

## Failure Log

### 2026-04-26 Wan MVP timeout on second real song

Successful part:

- `basic_flux_t2i.api.json` generated a clean still image through the API.
- Prompt id: `ac82f1b4-631d-473a-9fec-54348091614f`
- ComfyUI output path shape:
  `<COMFYUI_OUTPUT_DIR>/lyric-video/<song>/still-mvp_00001_.png`
- Repo download:
  `songs/<song>/assets/backgrounds/still-mvp_00001_.png`
- The still was MVP-safe: abstract, colorful, no text, no characters.

Failed or inconclusive part:

- `basic_wan_i2v_subtle-3.api.json` was queued against that still.
- Prompt id: `f26db8d9-dd23-4637-8490-12c91716e0ef`
- Settings inherited from the baseline:
  - `width`: `832`
  - `height`: `480`
  - `length`: `33`
  - `fps`: `8`
  - `steps`: `20`
  - `cfg`: `5`
  - `seed`: `216408885202616`
  - model: `wan2.2_ti2v_5B_fp16.safetensors`
- The source image override worked:
  `lyric-video/<song>/still-mvp_00001_.png [output]`
- The positive prompt was wrong because it came from the old bar-room baseline:
  `A moody 1920s bar interior...`
- The queue was still running after the script's 1800-second timeout. Later
  successful lower-step runs suggest `steps=20` may simply require a timeout
  greater than 1800 seconds on this machine, not that the workflow is invalid.
- No `wan-mvp` video output appeared under
  `<COMFYUI_OUTPUT_DIR>/lyric-video/<song>/`.
- A POST to `/interrupt` returned successfully but the job still appeared in
  `/queue`.
- The ComfyUI Python process had to be force-stopped.

Lessons:

- Still generation first is correct.
- `832x480` is not the known problem; it worked in earlier local tests.
- Do not assume a full Wan baseline fits within a 30-minute timeout on every
  new source image/prompt.
- Do not reuse a stale baseline prompt for a different song.
- Add song-specific prompt overrides every time.
- Start I2V with tiny probe settings, such as `length=9` and `steps=4`.
- Treat API timeout as a first-class failure mode; query `/queue`, check output
  folders, then restart the backend if interrupt does not clear the job.
- The queue helper now has timeout interruption enabled by default; use
  `--no-interrupt-on-timeout` only when intentionally leaving a long render
  running.

Next iteration plan:

1. Restart the ComfyUI API server cleanly.
2. Queue a tiny I2V probe with the approved still and a song-specific prompt.
3. If the probe finishes, repeat at `832x480`, `length=33`, and low steps.
4. If that finishes, increase steps toward the useful baseline.
5. Keep each run's prompt id, source image, length, steps, runtime, and output
   path in the failure/success log.

Follow-up successful passes:

| Prompt id | Size | Length | Steps | Result | Notes |
| --- | --- | --- | --- | --- | --- |
| `63ecb2de-2937-451d-9851-7d73b3d7ff6c` | `832x480` | `9` | `4` | success | Tiny probe completed and downloaded. |
| `49460988-587e-4dcf-a7f7-df4e07e40c1f` | `832x480` | `17` | `4` | success | Longer low-step probe completed. |
| `38802c1f-2f16-4f5c-89be-d22f889bfedd` | `832x480` | `33` | `4` | success | Baseline length works at low steps. |
| `b241a79d-9e00-499c-8602-e6ebda2816b2` | `832x480` | `33` | `8` | success | Moderate-step pass completed in roughly 12 minutes. |
| `4e1ab31f-ae2b-4cf0-bfb8-08e72917a9d2` | `832x480` | `33` | `8` | success but rejected | First Human v1 with abstract pastel still + generic shimmer prompt (`wan-v2`). User rejected aesthetic as "tablemat" — too static, no theme connection. Lesson: prompt the still as a scene, not as decoration. See [[feedback_live_wallpaper_aesthetic]]. |
| `c7199eac-a685-4f93-9cc7-4c8b31759c7f` | `832x480` | `33` | `8` | partial success | First Human v3 cave scene (`wan-v3-cave`). Source: `still-v2-cave_00001_.png` (caveman silhouette by fire). Scene-specific motion prompt (smoke drift, ember rise, firelight flicker). Real visible motion, not just shimmer. **Issue 1 — settle flash:** the very first frames carry a bright firelight flash that does not match steady firelight; reads as flash photography. Cause is likely Wan's denoiser resolving into motion. Mitigation: trim the first 1–3 frames before looping. **Issue 2 — bounce-loop incompatibility:** because the motion is directional (smoke rises, embers float up), forward-then-reverse playback shows smoke falling and embers settling into the fire, which the eye reads as broken. Bounce-loop is incompatible with directional ambient motion. See [[scripts-make_smooth_loop]] for the crossfade-loop replacement. |

Current practical recommendation:

- Use `832x480`, `length=33`, `steps=8` as the first useful I2V render target
  for this baseline.
- Keep `steps=20` as a slower quality experiment with a longer timeout, not the
  first run.
- Always override the positive prompt with song-specific background motion
  language.

## Live Wallpaper Production v1 (per song)

When a Wan take is judged usable, lock it as the song's live-wallpaper baseline:

1. Append the prompt id and overrides to the table above.
2. Save the song-aware motion prompt into `songs/<song>/inputs/song_style_prompt.txt`
   under a clearly labeled `Background motion (Wan i2v):` section so the next
   re-run is reproducible from the song folder alone.
3. Use `scripts/render_vibe_video.py` with the bounce loop as the background
   and a descriptive `--variant` (e.g. `wan-v2-soft-scroll`).

Closed workflow gap:

- `song.json` now supports `background_mode: "video"` + `background_video`
  pointing at the chosen loop file, plus an optional `background_variant` for
  the export-filename suffix (omit it for the canonical
  `<song>.<target>.mp4`). When `background_mode == "video"`, `make_videos.py`
  routes the per-target loop through `render_video_background` automatically;
  the `layout` field on `song.json` is honored as the default lyric layout
  too. This lets a song's "lock the cave loop" decision live in one place so
  the GUI → save → `make_videos.py "song"` cycle is one command.

Remaining known gaps:

- `scripts/make_bounce_loop.py` writes `<stem>.bounce.mp4`, while earlier
  manual files used `<stem>_bounce.mp4` (underscore). Both are valid inputs
  downstream; the dot convention is preferred for new files.
- Raw ComfyUI MP4s currently land directly in `assets/backgrounds/`. The
  doc's stated separation (raw to `inputs/video/`, curated to
  `assets/backgrounds/`) is not yet enforced by `comfyui_queue.py`.
- Non-horizontal targets crop the cave 832x480 source via center-crop; for
  songs that need vertical/square exports, plan a per-target source still.

## Loop Postprocess — Bounce vs Smooth

Two helpers exist. Pick based on whether the source motion is directional.

### Bounce (forward + reverse) — `scripts\make_bounce_loop.py`

Use only for **non-directional** ambient motion, where reversing playback is
visually neutral: pastel shimmer, two-way drift, color cycling, undirected
glow.

```powershell
python scripts\make_bounce_loop.py path\to\clip.mp4 --output path\to\clip.bounce.mp4
```

Do **not** use bounce for directional motion — rising smoke, floating embers,
drifting mist, falling water, walking dust. Reverse playback shows smoke
falling, embers settling into the fire, etc., which always reads as broken.

### Smooth crossfade (forward-only) — `scripts\make_smooth_loop.py`

Use for directional ambient motion. The tail of the clip crossfades back into
the head, so the file loops cleanly when `-stream_loop` wraps.

```powershell
python scripts\make_smooth_loop.py path\to\clip.mp4 --trim-start 2 --overlap 1.0
```

- `--trim-start N` drops the first N frames. Wan i2v often produces a
  brightness "settle flash" across the first 1–3 frames; trimming kills it
  and gives the loop a stable head frame to crossfade into.
- `--overlap S` is the crossfade duration in seconds. 1.0s is a safe default
  for an 8 fps / 33-frame Wan clip. Longer overlap hides the seam better but
  shortens the clip's "non-crossfade" section.

The output runs forward-only and loops cleanly with `-stream_loop -1` in the
final render command.

### Future direction — AI tween (backlog, nice-to-have, no due date)

The crossfade in `make_smooth_loop.py` is "passable" per the user — good
enough to ship. Better looping is a backlog item, not a blocker. Only revisit
if a future scene's motion ghosts visibly through the crossfade.

When that happens, swap the xfade for optical-flow / AI frame interpolation
(RIFE or FILM) bridging the tail back to the head. The current
`make_smooth_loop.py` filtergraph is the seam to replace; the rest of the
pipeline can stay the same.

## BPM

BPM can be provided manually in `song.json` as optional metadata.

Automatic BPM detection is possible later, but it should be treated as an
estimate. Candidate tools include:

- `librosa`
- `aubio`
- `essentia`
- DAW/manual BPM entry from the user

For generated motion, the basic scheduling formula is:

```text
frame_interval = fps * 60 / bpm
```

That interval can drive a prompt schedule or value schedule in ComfyUI, for
example a subtle pulse or motion-strength bump on beats.

## Export Naming

Background-video exports should distinguish themselves from plain lyric renders.

Suggested naming:

```text
exports/song-name.vertical.vibe.mp4
exports/song-name.horizontal.vibe.mp4
```

The final naming should remain consistent with render targets and should record
the background mode in render metadata.

## Open Questions

- Whether background videos are generated per whole song or per section.
- Whether BPM should be user-entered, auto-estimated, or both.
- Whether the first animation pass should use ComfyUI video output directly or
  FFmpeg motion from generated stills.
- How much LLM prompt interpretation should happen before calling ComfyUI.
