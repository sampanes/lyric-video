# ComfyUI Workflows

Prompt templates, node graphs, and adapters for background generation live here.

The first supported handoff should be a workflow JSON exported from the ComfyUI
UI, then adapted by repo scripts so song-driven fields can be filled
automatically.

Routine generation should use ComfyUI as a local API server. The UI is for
authoring/exporting workflows, not for normal lyric-video generation.

Check or start the server:

```powershell
python scripts\comfyui_server.py status
python scripts\comfyui_server.py start
```

Machine-specific defaults can live in ignored `LOCAL_CONFIG.json`.

Store exported workflows under:

```text
workflows/comfyui/node-graphs/
```

Store prompt templates under:

```text
workflows/comfyui/prompts/
```

Design notes for subtle animated backgrounds live in
`docs/workflows/comfyui-vibe-motion.md`.

Headless queue helper:

```powershell
python scripts\comfyui_queue.py workflows\comfyui\node-graphs\basic_wan_i2v_subtle-3.api.json --song "song name" --dry-run
```

Use `--dry-run` first. Running without it requires a live local ComfyUI server.
