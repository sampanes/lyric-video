"""Render lyrics over a looping background video."""

from __future__ import annotations

import argparse
from pathlib import Path

from pipeline_common import (
    ensure_song_config,
    load_json,
    render_video_background,
    resolve_song_dir,
    validate_song_package,
    write_ass_file,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("song", help="Song slug, approximate name, or song folder.")
    parser.add_argument("background_video", help="Background video path.")
    parser.add_argument("--target", default="horizontal", help="Render target.")
    parser.add_argument(
        "--layout",
        choices=("standard", "fullscreen"),
        default="standard",
        help="Lyric layout to render.",
    )
    parser.add_argument("--variant", default="vibe", help="Output variant suffix.")
    args = parser.parse_args()

    song_dir = resolve_song_dir(args.song)
    config = ensure_song_config(song_dir)
    errors, warnings = validate_song_package(song_dir, config, require_timing=True, check_tools=True)
    for warning in warnings:
        print(f"Warning: {warning}")
    if errors:
        raise SystemExit("Song validation failed:\n" + "\n".join(f"- {error}" for error in errors))

    timing_path = song_dir / config.get("timing", {}).get("reviewed", "timing/reviewed/timing.json")
    if not timing_path.exists():
        raise SystemExit(f"Reviewed timing file not found: {timing_path}")

    background_video_path = Path(args.background_video)
    if not background_video_path.is_absolute():
        song_relative = song_dir / background_video_path
        repo_relative = Path.cwd() / background_video_path
        background_video_path = song_relative if song_relative.exists() else repo_relative
    if not background_video_path.exists():
        raise SystemExit(f"Background video not found: {background_video_path}")

    timing = load_json(timing_path)
    ass_path = write_ass_file(song_dir, timing, config, args.target, args.layout)
    output_path = render_video_background(
        song_dir,
        config,
        ass_path,
        background_video_path,
        target_name=args.target,
        variant=args.variant,
    )
    print(f"Using {timing_path}")
    print(f"Wrote {ass_path}")
    print(f"Wrote {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
