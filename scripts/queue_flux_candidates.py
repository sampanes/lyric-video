"""Queue a Flux candidate still for every prompt under inputs/prompts/.

For a song folder, this script reads every `*.txt` file under
`songs/<slug>/inputs/prompts/` and queues one Flux text-to-image run
per file. The file stem becomes the candidate label and the
`--filename-prefix` suffix, so outputs land as
`assets/backgrounds/still-<stem>_00001_.png`. The seed for each run is
derived deterministically from the stem so a re-run reproduces the
same image when the prompt text hasn't changed.

The Flux server (ComfyUI) must already be running. Run this in the
background and come back to a folder of candidate stills.
"""

from __future__ import annotations

import argparse
import hashlib
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from pipeline_common import resolve_song_dir  # noqa: E402


DEFAULT_WORKFLOW = REPO_ROOT / "workflows" / "comfyui" / "node-graphs" / "basic_flux_t2i.api.json"
DEFAULT_WIDTH = 832
DEFAULT_HEIGHT = 480

# Flux happily renders fake text (signs, banners, watermarks) unless told
# otherwise, which destroys the background under a lyric overlay. Append this
# unless --no-anti-text is set.
ANTI_TEXT_SUFFIX = (
    "no text, no letters, no words, no signs, no captions, no subtitles, "
    "no watermarks, no signatures, no logos, no writing, no graffiti, "
    "no posters, no labels, no billboards"
)


def stable_seed(name: str) -> int:
    digest = hashlib.sha256(name.encode("utf-8")).hexdigest()
    return int(digest[:8], 16)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("song", help="Song slug or approximate name (fuzzy match).")
    parser.add_argument("--width", type=int, default=DEFAULT_WIDTH)
    parser.add_argument("--height", type=int, default=DEFAULT_HEIGHT)
    parser.add_argument(
        "--workflow",
        default=str(DEFAULT_WORKFLOW),
        help="Flux workflow JSON to queue. Defaults to basic_flux_t2i.api.json.",
    )
    parser.add_argument(
        "--prompts-subdir",
        default="inputs/prompts",
        help="Subdirectory under the song folder to scan for *.txt prompts.",
    )
    parser.add_argument(
        "--prefix-template",
        default="lyric-video/{song}/still-{concept}",
        help="ComfyUI filename-prefix template. {song} and {concept} are substituted.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the per-candidate comfyui_queue command without running it.",
    )
    parser.add_argument(
        "--no-anti-text",
        action="store_true",
        help="Skip the default anti-text suffix. Use only if you actually want Flux to render text on the still.",
    )
    args = parser.parse_args()

    song_dir = resolve_song_dir(args.song)
    prompts_dir = song_dir / args.prompts_subdir
    if not prompts_dir.is_dir():
        raise SystemExit(
            f"Prompts directory not found: {prompts_dir}\n"
            f"Create it and drop one prompt per candidate (e.g. cave.txt, forest.txt)."
        )

    prompt_files = sorted(prompts_dir.glob("*.txt"))
    if not prompt_files:
        raise SystemExit(
            f"No *.txt prompt files in {prompts_dir}. "
            f"Drop one prompt per candidate; the filename becomes the label."
        )

    queue_script = str(SCRIPTS_DIR / "comfyui_queue.py")
    queued: list[str] = []
    failed: list[str] = []

    for prompt_file in prompt_files:
        text = prompt_file.read_text(encoding="utf-8").strip()
        if not text:
            print(f"Skipping empty prompt: {prompt_file.name}")
            continue
        if not args.no_anti_text:
            text = f"{text.rstrip(',. ').rstrip()}. {ANTI_TEXT_SUFFIX}"
        concept = prompt_file.stem
        seed = stable_seed(concept)
        filename_prefix = args.prefix_template.format(song=song_dir.name, concept=concept)
        command = [
            sys.executable,
            queue_script,
            args.workflow,
            "--song", song_dir.name,
            "--wait",
            "--filename-prefix", filename_prefix,
            "--positive-prompt", text,
            "--seed", str(seed),
            "--width", str(args.width),
            "--height", str(args.height),
        ]
        print(f"\n=== {concept}  seed={seed} ===")
        if args.dry_run:
            print(" ".join(command))
            queued.append(concept)
            continue
        result = subprocess.run(command, cwd=REPO_ROOT)
        if result.returncode == 0:
            queued.append(concept)
        else:
            failed.append(concept)
            print(f"FAILED: {concept} (comfyui_queue exit {result.returncode})")

    print("")
    if queued:
        print(f"Queued {len(queued)} candidate(s): {', '.join(queued)}")
        print(f"Stills are under: {song_dir / 'assets' / 'backgrounds'}")
    if failed:
        print(f"{len(failed)} candidate(s) failed: {', '.join(failed)}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
