# ComfyUI Prompts

Store reusable prompt fragments and prompt templates for generated backgrounds
here.

Prompts should be derived from `song_vibes`, reviewed lyrics, target aspect
ratio, and any user-provided visual direction.

The canonical per-song user-editable visual direction file is:

```text
songs/<song>/inputs/song_style_prompt.txt
```

Future ComfyUI adapters should combine that file with `song_vibes`, section
notes, target ratio, and workflow-specific negative prompts.
