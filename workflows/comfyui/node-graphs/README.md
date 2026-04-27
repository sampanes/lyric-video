# ComfyUI Node Graphs

Put workflow JSON exports from the ComfyUI UI here.

When adding a workflow, document which node fields are expected to be replaced
by scripts, such as prompt, seed, width, height, output path, checkpoint, and
sampler settings.

Current baseline workflows:

- `basic_flux_t2i.api.json`: reusable Flux text-to-image API workflow export.
  Use this as step one for still background generation before adding animation
  or BPM-synced motion. Field mapping is intentionally still TODO; the JSON was
  moved here without rewriting it.
- `basic_wan_i2v_subtle-3.api.json`: current usable Wan image-to-video recovery
  iteration for subtle background motion. It is intentionally conservative and
  should be treated as a baseline to iterate from, not a final best workflow.
  The prior `*-2` attempt is documented as a failed/trash visual result in
  `docs/workflows/comfyui-vibe-motion.md`.

Dry-run a workflow through the headless queue helper:

```powershell
python scripts\comfyui_queue.py workflows\comfyui\node-graphs\basic_flux_t2i.api.json --song "song name" --dry-run
```

Normal order is text-to-image still first, then image-to-video from an approved
still.
