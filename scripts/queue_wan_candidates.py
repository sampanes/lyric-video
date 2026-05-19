"""Animate every Flux still that has a matching prompt file.

For each `inputs/prompts/<concept>.txt` in a song folder, this script:

1. Finds the matching still under `assets/backgrounds/still-<concept>_*.png`
   (preferring the highest-numbered / most recent generation).
2. Reads `inputs/prompts/<concept>.motion.txt` for the Wan motion prompt
   if it exists; otherwise uses a Wan-safe generic default.
3. Queues `basic_wan_i2v_subtle-3.api.json` at length=33 steps=8 with
   `wan-<concept>` as the filename prefix.
4. Smooth-loops each new clip via scripts/make_smooth_loop.py unless
   `--no-smooth-loop` is set.

Sequential; ComfyUI queues that way regardless. Each clip is roughly
4 minutes on this machine, so the whole batch is `N * 4 min`.

The batcher is intentionally scoped via the prompts directory: stale
stills in `assets/backgrounds/` that don't have a prompt file are
ignored. That keeps the batch tied to the active candidates rather
than every PNG that ever landed in the folder.
"""

from __future__ import annotations

import argparse
import hashlib
import re
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from pipeline_common import resolve_song_dir  # noqa: E402


DEFAULT_WORKFLOW = REPO_ROOT / "workflows" / "comfyui" / "node-graphs" / "basic_wan_i2v_subtle-3.api.json"
DEFAULT_LENGTH = 33
DEFAULT_STEPS = 8
DEFAULT_TIMEOUT = 1800

DEFAULT_MOTION_PROMPT = (
    "very subtle ambient motion, gentle natural drift, soft light flicker, "
    "almost static, stable composition, locked camera, fixed composition, "
    "no camera movement"
)

STILL_PATTERN = re.compile(r"^still-(?P<concept>.+)_(?P<index>\d+)_\.png$")


def stable_seed(name: str) -> int:
    digest = hashlib.sha256(name.encode("utf-8")).hexdigest()
    return int(digest[:8], 16)


def find_latest_still(backgrounds_dir: Path, concept: str) -> Path | None:
    """Return the highest-indexed still-<concept>_NNNNN_.png in the dir."""
    candidates: list[tuple[int, Path]] = []
    for path in backgrounds_dir.glob(f"still-{concept}_*_.png"):
        match = STILL_PATTERN.match(path.name)
        if not match or match.group("concept") != concept:
            continue
        candidates.append((int(match.group("index")), path))
    if not candidates:
        return None
    candidates.sort()
    return candidates[-1][1]


def read_motion_prompt(prompts_dir: Path, concept: str, default: str) -> str:
    motion_file = prompts_dir / f"{concept}.motion.txt"
    if motion_file.exists():
        text = motion_file.read_text(encoding="utf-8").strip()
        if text:
            return text
    return default


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("song", help="Song slug or approximate name (fuzzy match).")
    parser.add_argument("--length", type=int, default=DEFAULT_LENGTH)
    parser.add_argument("--steps", type=int, default=DEFAULT_STEPS)
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT)
    parser.add_argument(
        "--workflow",
        default=str(DEFAULT_WORKFLOW),
        help="Wan i2v workflow JSON to queue.",
    )
    parser.add_argument(
        "--prompts-subdir",
        default="inputs/prompts",
        help="Subdirectory under the song folder to scan for *.txt prompts.",
    )
    parser.add_argument(
        "--backgrounds-subdir",
        default="assets/backgrounds",
        help="Subdirectory holding the Flux stills to animate.",
    )
    parser.add_argument(
        "--motion-prompt",
        default=None,
        help="Global motion prompt override applied to every candidate. Overrides per-concept *.motion.txt files.",
    )
    parser.add_argument(
        "--concept",
        action="append",
        default=None,
        help="Limit the batch to one or more concept stems. Repeatable.",
    )
    parser.add_argument(
        "--no-smooth-loop",
        action="store_true",
        help="Skip the make_smooth_loop pass on each Wan output.",
    )
    parser.add_argument(
        "--smooth-trim-start",
        type=int,
        default=2,
        help="Frames to trim from the start before smooth-looping (Wan settle flash).",
    )
    parser.add_argument(
        "--smooth-overlap",
        type=float,
        default=1.0,
        help="Crossfade overlap in seconds for smooth-loop.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the per-candidate commands without running anything.",
    )
    args = parser.parse_args()

    song_dir = resolve_song_dir(args.song)
    prompts_dir = song_dir / args.prompts_subdir
    backgrounds_dir = song_dir / args.backgrounds_subdir

    if not prompts_dir.is_dir():
        raise SystemExit(f"Prompts directory not found: {prompts_dir}")
    if not backgrounds_dir.is_dir():
        raise SystemExit(f"Backgrounds directory not found: {backgrounds_dir}")

    prompt_files = [
        path for path in sorted(prompts_dir.glob("*.txt"))
        if not path.name.endswith(".motion.txt")
    ]
    if args.concept:
        keep = set(args.concept)
        prompt_files = [p for p in prompt_files if p.stem in keep]
    if not prompt_files:
        raise SystemExit(f"No prompt files in {prompts_dir} (after filters).")

    queue_script = str(SCRIPTS_DIR / "comfyui_queue.py")
    smooth_script = str(SCRIPTS_DIR / "make_smooth_loop.py")

    queued: list[str] = []
    skipped_no_still: list[str] = []
    failed: list[str] = []

    for prompt_file in prompt_files:
        concept = prompt_file.stem
        still_path = find_latest_still(backgrounds_dir, concept)
        if still_path is None:
            print(f"Skipping {concept}: no still-{concept}_*.png in {backgrounds_dir}")
            skipped_no_still.append(concept)
            continue

        motion_text = (
            args.motion_prompt
            if args.motion_prompt is not None
            else read_motion_prompt(prompts_dir, concept, DEFAULT_MOTION_PROMPT)
        )
        seed = stable_seed(concept)
        filename_prefix = f"lyric-video/{song_dir.name}/wan-{concept}"
        comfy_image_ref = f"lyric-video/{song_dir.name}/{still_path.name} [output]"

        wan_command = [
            sys.executable,
            queue_script,
            args.workflow,
            "--song", song_dir.name,
            "--wait",
            "--timeout", str(args.timeout),
            "--filename-prefix", filename_prefix,
            "--positive-prompt", motion_text,
            "--length", str(args.length),
            "--set", f"3.inputs.steps={args.steps}",
            "--set", f"3.inputs.seed={seed}",
            "--set", f"56.inputs.image={comfy_image_ref}",
        ]
        print(f"\n=== {concept}  still={still_path.name}  seed={seed} ===")
        if args.dry_run:
            print("WAN:    " + " ".join(wan_command))
        else:
            result = subprocess.run(wan_command, cwd=REPO_ROOT)
            if result.returncode != 0:
                failed.append(concept)
                print(f"FAILED: {concept} (comfyui_queue exit {result.returncode})")
                continue

        # Smooth-loop pass.
        if args.no_smooth_loop:
            queued.append(concept)
            continue
        wan_output = backgrounds_dir / f"wan-{concept}_00001_.mp4"
        if not args.dry_run and not wan_output.exists():
            # Wan might have auto-incremented; pick the latest wan-<concept>_*.mp4
            wan_outputs = sorted(backgrounds_dir.glob(f"wan-{concept}_*_.mp4"))
            wan_output = wan_outputs[-1] if wan_outputs else wan_output
        smooth_command = [
            sys.executable,
            smooth_script,
            str(wan_output),
            "--trim-start", str(args.smooth_trim_start),
            "--overlap", str(args.smooth_overlap),
        ]
        if args.dry_run:
            print("SMOOTH: " + " ".join(smooth_command))
            queued.append(concept)
            continue
        smooth_result = subprocess.run(smooth_command, cwd=REPO_ROOT)
        if smooth_result.returncode != 0:
            print(f"WARN: smooth-loop failed for {concept}; raw Wan output remains.")
        queued.append(concept)

    print("")
    if queued:
        print(f"Queued {len(queued)} candidate(s): {', '.join(queued)}")
        print(f"Outputs are under: {backgrounds_dir}")
    if skipped_no_still:
        print(f"{len(skipped_no_still)} skipped (no matching still): {', '.join(skipped_no_still)}")
    if failed:
        print(f"{len(failed)} failed: {', '.join(failed)}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
