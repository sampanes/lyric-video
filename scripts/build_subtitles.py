"""Build reviewed timing and ASS subtitles for a song."""

from __future__ import annotations

import argparse

from pipeline_common import (
    build_even_timing,
    build_whisper_timing,
    ensure_song_config,
    load_json,
    normalize_render_targets,
    resolve_song_dir,
    validate_song_package,
    write_ass_file,
    write_reviewed_timing,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("song", help="Song slug, approximate name, or song folder.")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Regenerate reviewed timing even when timing/reviewed/timing.json exists.",
    )
    parser.add_argument(
        "--from-whisper",
        action="store_true",
        help="Build reviewed timing by mapping lyrics onto raw WhisperX segments.",
    )
    parser.add_argument(
        "--targets",
        nargs="+",
        default=None,
        help="Render targets to build subtitles for: horizontal, vertical, square, portrait, or all.",
    )
    parser.add_argument(
        "--layout",
        choices=("standard", "fullscreen"),
        default="standard",
        help="Lyric layout to build.",
    )
    args = parser.parse_args()

    song_dir = resolve_song_dir(args.song)
    config = ensure_song_config(song_dir)
    errors, warnings = validate_song_package(song_dir, config)
    for warning in warnings:
        print(f"Warning: {warning}")
    if errors:
        raise SystemExit("Song validation failed:\n" + "\n".join(f"- {error}" for error in errors))

    timing_path = song_dir / "timing" / "reviewed" / "timing.json"
    timing_written = False

    if timing_path.exists() and not args.force:
        timing = load_json(timing_path)
    else:
        timing = build_whisper_timing(song_dir, config) if args.from_whisper else build_even_timing(song_dir, config)
        write_reviewed_timing(song_dir, timing)
        timing_written = True

    configured_targets = config.get("output", {}).get("targets")
    targets = normalize_render_targets(args.targets if args.targets is not None else configured_targets)
    ass_paths = [write_ass_file(song_dir, timing, config, target, args.layout) for target in targets]
    print(f"{'Wrote' if timing_written else 'Using'} {timing_path}")
    for ass_path in ass_paths:
        print(f"Wrote {ass_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
