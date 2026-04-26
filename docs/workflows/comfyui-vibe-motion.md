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

## Bounce Loop Postprocess

For ultra-subtle generated clips that are not truly loopable, create a
palindrome bounce loop in FFmpeg:

1. play forward
2. reverse the clip
3. trim the first reversed frame to reduce duplicate seam frames
4. concatenate forward plus reverse

Current helper:

```powershell
python scripts\make_bounce_loop.py path\to\clip.mp4 --output path\to\clip.bounce.mp4
```

Use this for calm ambient motion. If the source has flicker or artifacts,
reverse playback may expose those issues, but this is still practical for quick
lyric-video background loops.

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
