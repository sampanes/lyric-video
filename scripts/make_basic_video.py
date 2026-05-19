"""One-shot basic lyric video pipeline for a song folder."""

from __future__ import annotations

import argparse

from pipeline_common import (
    apply_preset_to_config,
    build_even_timing,
    build_whisper_timing,
    ensure_song_config,
    find_whisper_transcript,
    load_json,
    load_preset,
    normalize_render_targets,
    render_basic_video,
    render_video_background,
    resolve_layout,
    resolve_song_dir,
    validate_song_package,
    write_ass_file,
    write_reviewed_timing,
)
from whisper_song import run_whisperx


def main(description: str | None = None) -> int:
    parser = argparse.ArgumentParser(description=description or __doc__)
    parser.add_argument("song", help="Song slug, approximate name, or song folder.")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Regenerate reviewed timing before rendering.",
    )
    parser.add_argument(
        "--timing-source",
        choices=("auto", "even", "whisper"),
        default="auto",
        help="Timing source for reviewed timing. auto uses Whisper when available.",
    )
    parser.add_argument(
        "--targets",
        nargs="+",
        default=None,
        help="Video targets to render: horizontal, vertical, square, portrait, or all.",
    )
    parser.add_argument(
        "--preset",
        default=None,
        help="Render preset name or JSON path, for repeatable habits such as kid_youtube_education.",
    )
    parser.add_argument(
        "--layout",
        choices=("standard", "fullscreen", "soft_scroll"),
        default=None,
        help="Lyric layout to render. Overrides preset layout when provided.",
    )
    parser.add_argument(
        "--refresh-whisper",
        action="store_true",
        help="Run WhisperX first, then rebuild timing and render.",
    )
    parser.add_argument("--whisper-model", default="medium", help="WhisperX model name.")
    parser.add_argument("--whisper-device", default="cpu", help="WhisperX device, such as cpu or cuda.")
    parser.add_argument(
        "--whisper-compute-type",
        default="int8",
        help="WhisperX compute type. int8 is a conservative CPU default.",
    )
    parser.add_argument(
        "--whisper-align",
        action="store_true",
        help="Run WhisperX alignment during --refresh-whisper.",
    )
    parser.add_argument(
        "--whisper-allow-download",
        action="store_true",
        help="Allow WhisperX to download missing models during --refresh-whisper.",
    )
    args = parser.parse_args()

    song_dir = resolve_song_dir(args.song)
    preset = load_preset(args.preset)
    config = apply_preset_to_config(ensure_song_config(song_dir), preset)
    errors, warnings = validate_song_package(song_dir, config, check_tools=True)
    for warning in warnings:
        print(f"Warning: {warning}")
    if errors:
        raise SystemExit("Song validation failed:\n" + "\n".join(f"- {error}" for error in errors))
    if preset:
        preset_name = config.get("_render_preset") or args.preset
        preset_path = config.get("_render_preset_path")
        print(f"Using preset {preset_name}" + (f" from {preset_path}" if preset_path else ""))

    timing_path = song_dir / "timing" / "reviewed" / "timing.json"
    timing_written = False

    if args.refresh_whisper:
        result = run_whisperx(
            song_dir,
            config,
            model=args.whisper_model,
            device=args.whisper_device,
            compute_type=args.whisper_compute_type,
            align=args.whisper_align,
            cache_only=not args.whisper_allow_download,
        )
        print(f"Wrote WhisperX output under {result['output_dir']}")
        print(f"Wrote {result['metadata_path']}")

    if args.force or args.refresh_whisper or not timing_path.exists():
        timing_source = args.timing_source
        if timing_source == "auto":
            try:
                find_whisper_transcript(song_dir)
            except SystemExit:
                timing_source = "even"
            else:
                timing_source = "whisper"

        timing = build_whisper_timing(song_dir, config) if timing_source == "whisper" else build_even_timing(song_dir, config)
        write_reviewed_timing(song_dir, timing)
        timing_written = True
    else:
        timing = load_json(timing_path)

    layout = resolve_layout(args.layout, preset, config)
    configured_targets = config.get("output", {}).get("targets")
    targets = normalize_render_targets(args.targets if args.targets is not None else configured_targets)
    use_video_bg = config.get("background_mode") == "video" and config.get("background_video")
    bg_video_path = (song_dir / config["background_video"]) if use_video_bg else None
    variant = config.get("background_variant") if use_video_bg else None
    outputs = []
    ass_paths = []
    for target in targets:
        ass_path = write_ass_file(song_dir, timing, config, target, layout)
        if use_video_bg:
            output_path = render_video_background(
                song_dir,
                config,
                ass_path,
                bg_video_path,
                target_name=target,
                layout=layout,
                variant=variant,
            )
        else:
            output_path = render_basic_video(song_dir, config, ass_path, target, layout)
        ass_paths.append(ass_path)
        outputs.append(output_path)

    print(f"{'Wrote' if timing_written else 'Using'} {timing_path}")
    for ass_path in ass_paths:
        print(f"Wrote {ass_path}")
    for output_path in outputs:
        print(f"Wrote {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
