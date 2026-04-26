"""Render a song from reviewed timing, subtitles, audio, and assets."""

from __future__ import annotations

import argparse

from pipeline_common import (
    apply_preset_to_config,
    ensure_song_config,
    load_json,
    load_preset,
    normalize_render_targets,
    render_basic_video,
    resolve_layout,
    resolve_song_dir,
    validate_song_package,
    write_ass_file,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("song", help="Song slug, approximate name, or song folder.")
    parser.add_argument(
        "--targets",
        nargs="+",
        default=None,
        help="Video targets to render: horizontal, vertical, square, portrait, or all.",
    )
    parser.add_argument(
        "--preset",
        default=None,
        help="Render preset name or JSON path.",
    )
    parser.add_argument(
        "--layout",
        choices=("standard", "fullscreen", "soft_scroll"),
        default=None,
        help="Lyric layout to render. Overrides preset layout when provided.",
    )
    args = parser.parse_args()

    song_dir = resolve_song_dir(args.song)
    preset = load_preset(args.preset)
    config = apply_preset_to_config(ensure_song_config(song_dir), preset)
    errors, warnings = validate_song_package(song_dir, config, require_timing=True, check_tools=True)
    for warning in warnings:
        print(f"Warning: {warning}")
    if errors:
        raise SystemExit("Song validation failed:\n" + "\n".join(f"- {error}" for error in errors))

    reviewed_timing = config.get("timing", {}).get("reviewed", "timing/reviewed/timing.json")
    timing_path = song_dir / reviewed_timing
    if not timing_path.exists():
        raise SystemExit(f"Reviewed timing file not found: {timing_path}")

    timing = load_json(timing_path)
    configured_targets = config.get("output", {}).get("targets")
    targets = normalize_render_targets(args.targets if args.targets is not None else configured_targets)
    layout = resolve_layout(args.layout, preset, config)
    for target in targets:
        ass_path = write_ass_file(song_dir, timing, config, target, layout)
        output_path = render_basic_video(song_dir, config, ass_path, target, layout)
        print(f"Wrote {ass_path}")
        print(f"Wrote {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
