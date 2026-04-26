"""Validate a song package and its inputs."""

from __future__ import annotations

import argparse

from pipeline_common import ensure_song_config, load_json, resolve_song_dir, validate_song_package


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("song", help="Song slug, approximate name, or song folder.")
    parser.add_argument(
        "--require-timing",
        action="store_true",
        help="Fail when timing/reviewed/timing.json does not exist.",
    )
    parser.add_argument(
        "--check-tools",
        action="store_true",
        help="Fail when ffmpeg or ffprobe is not on PATH.",
    )
    parser.add_argument(
        "--create-config",
        action="store_true",
        help="Create missing song.json from unique audio/lyrics before validating.",
    )
    args = parser.parse_args()

    song_dir = resolve_song_dir(args.song)
    config_path = song_dir / "song.json"
    if args.create_config:
        config = ensure_song_config(song_dir)
    elif config_path.exists():
        config = load_json(config_path)
    else:
        print(f"Song validation failed:\n- Missing song config: {config_path}")
        return 1
    errors, warnings = validate_song_package(
        song_dir,
        config,
        require_timing=args.require_timing,
        check_tools=args.check_tools,
    )

    for warning in warnings:
        print(f"Warning: {warning}")
    if errors:
        print("Song validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1

    print(f"Song validation passed: {song_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
