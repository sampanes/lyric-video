"""Inspect and adjust reviewed lyric timing without hand-editing JSON."""

from __future__ import annotations

import argparse
import shutil
from datetime import datetime
from pathlib import Path

from pipeline_common import (
    load_json,
    resolve_song_dir,
    timing_gap_warnings,
    validate_timing,
    write_json,
)


DEFAULT_TIMING_PATH = "timing/reviewed/timing.json"


def format_ms(value: int) -> str:
    sign = "-" if value < 0 else ""
    value = abs(value)
    minutes, remainder = divmod(value, 60_000)
    seconds, milliseconds = divmod(remainder, 1000)
    return f"{sign}{minutes}:{seconds:02d}.{milliseconds:03d}"


def parse_ms(value: str, *, duration: bool = False) -> int:
    raw = value.strip().lower()
    sign = 1
    if raw.startswith("+"):
        raw = raw[1:]
    elif raw.startswith("-"):
        sign = -1
        raw = raw[1:]

    if not raw:
        raise argparse.ArgumentTypeError("empty time value")

    if raw.endswith("ms"):
        number = float(raw[:-2])
        return sign * int(round(number))

    if raw.endswith("s"):
        number = float(raw[:-1])
        return sign * int(round(number * 1000))

    if ":" in raw:
        parts = raw.split(":")
        if len(parts) == 2:
            minutes = int(parts[0])
            seconds = float(parts[1])
            total = (minutes * 60 + seconds) * 1000
            return sign * int(round(total))
        if len(parts) == 3:
            hours = int(parts[0])
            minutes = int(parts[1])
            seconds = float(parts[2])
            total = (hours * 3600 + minutes * 60 + seconds) * 1000
            return sign * int(round(total))
        raise argparse.ArgumentTypeError(f"invalid time value: {value}")

    if "." in raw:
        return sign * int(round(float(raw) * 1000))

    parsed = int(raw)
    if duration:
        return sign * parsed
    return sign * parsed


def load_reviewed_timing(song_ref: str) -> tuple[Path, Path, dict]:
    song_dir = resolve_song_dir(song_ref)
    config_path = song_dir / "song.json"
    if config_path.exists():
        config = load_json(config_path)
        reviewed_path = config.get("timing", {}).get("reviewed", DEFAULT_TIMING_PATH)
    else:
        reviewed_path = DEFAULT_TIMING_PATH

    timing_path = song_dir / reviewed_path
    if not timing_path.exists():
        raise SystemExit(f"Reviewed timing file does not exist: {timing_path}")
    return song_dir, timing_path, load_json(timing_path)


def segment_selector_error(selector: str, segments: list[dict]) -> SystemExit:
    examples = ", ".join(
        f"{index}:{segment.get('id', '(missing-id)')}"
        for index, segment in enumerate(segments[:5], start=1)
    )
    return SystemExit(f"Could not find timing segment '{selector}'. Examples: {examples}")


def segment_index(segments: list[dict], selector: str) -> int:
    raw = selector.strip()
    if not raw:
        raise segment_selector_error(selector, segments)

    if raw.isdigit():
        index = int(raw) - 1
        if 0 <= index < len(segments):
            return index
        raise segment_selector_error(selector, segments)

    normalized = raw.lower()
    for index, segment in enumerate(segments):
        if str(segment.get("id", "")).lower() == normalized:
            return index

    text_matches = [
        index
        for index, segment in enumerate(segments)
        if normalized in str(segment.get("text", "")).lower()
    ]
    if len(text_matches) == 1:
        return text_matches[0]
    if len(text_matches) > 1:
        matches = ", ".join(
            f"{index + 1}:{segments[index].get('id', '(missing-id)')}"
            for index in text_matches[:8]
        )
        raise SystemExit(f"Selector '{selector}' matched multiple segments: {matches}")

    raise segment_selector_error(selector, segments)


def selected_range(segments: list[dict], start_selector: str, end_selector: str | None) -> tuple[int, int]:
    start = segment_index(segments, start_selector)
    end = segment_index(segments, end_selector) if end_selector else start
    if end < start:
        raise SystemExit(
            f"Invalid range: {segments[start].get('id')} comes after {segments[end].get('id')}"
        )
    return start, end


def clipped_text(value: str, width: int = 58) -> str:
    normalized = " ".join(value.split())
    if len(normalized) <= width:
        return normalized
    return normalized[: width - 3] + "..."


def print_report(segments: list[dict], start: int, end: int, gap_threshold_ms: int) -> None:
    print(f"{'#':>3}  {'id':<10}  {'start':>9}  {'end':>9}  {'dur':>8}  {'gap':>8}  text")
    for index in range(start, end + 1):
        segment = segments[index]
        previous = segments[index - 1] if index > 0 else None
        start_ms = int(segment["start_ms"])
        end_ms = int(segment["end_ms"])
        duration_ms = end_ms - start_ms
        gap_ms = start_ms - int(previous["end_ms"]) if previous else 0
        gap = format_ms(gap_ms) if previous else ""
        if previous and gap_ms > gap_threshold_ms:
            gap = f"{gap} !"
        if previous and gap_ms < 0:
            gap = f"{gap} overlap"

        note = segment.get("allocation_note") or segment.get("review_note") or ""
        text = clipped_text(str(segment.get("text", "")))
        if note:
            text = f"{text} [{note}]"

        print(
            f"{index + 1:>3}  {str(segment.get('id', '')):<10}  "
            f"{format_ms(start_ms):>9}  {format_ms(end_ms):>9}  "
            f"{format_ms(duration_ms):>8}  {gap:>8}  {text}"
        )


def backup_timing(timing_path: Path) -> Path:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup_dir = timing_path.parent / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    backup_path = backup_dir / f"{timing_path.stem}.{stamp}{timing_path.suffix}"
    shutil.copy2(timing_path, backup_path)
    return backup_path


def validate_or_exit(timing: dict, timing_path: Path) -> None:
    errors = validate_timing(timing, timing_path)
    if errors:
        raise SystemExit("Timing edit would create invalid timing:\n" + "\n".join(errors))


def print_warnings(timing: dict, timing_path: Path, threshold_ms: int = 5000) -> None:
    warnings = timing_gap_warnings(timing, timing_path, threshold_ms=threshold_ms)
    segments = timing.get("segments", [])
    if isinstance(segments, list):
        for previous, current in zip(segments, segments[1:]):
            previous_end = previous.get("end_ms")
            current_start = current.get("start_ms")
            if not isinstance(previous_end, int) or not isinstance(current_start, int):
                continue
            overlap_ms = previous_end - current_start
            if overlap_ms > 0:
                warnings.append(
                    f"{timing_path}: {overlap_ms / 1000:.3f}s overlap after "
                    f"{previous.get('id', '(unknown)')} before {current.get('id', '(unknown)')}"
                )
    for warning in warnings:
        print(f"Warning: {warning}")


def command_report(args: argparse.Namespace) -> None:
    _song_dir, timing_path, timing = load_reviewed_timing(args.song)
    segments = timing.get("segments", [])
    if args.around:
        center = segment_index(segments, args.around)
        start = max(0, center - args.context)
        end = min(len(segments) - 1, center + args.context)
    elif args.start:
        start, end = selected_range(segments, args.start, args.end)
    else:
        start, end = 0, len(segments) - 1

    print(f"Timing: {timing_path}")
    print_report(segments, start, end, args.gap_threshold)


def command_nudge(args: argparse.Namespace) -> None:
    _song_dir, timing_path, timing = load_reviewed_timing(args.song)
    segments = timing["segments"]
    start, end = selected_range(segments, args.start, args.end)
    shift_ms = parse_ms(args.shift, duration=True)

    for index in range(start, end + 1):
        segments[index]["start_ms"] += shift_ms
        segments[index]["end_ms"] += shift_ms

    validate_or_exit(timing, timing_path)
    print_report(segments, max(0, start - 2), min(len(segments) - 1, end + 2), args.gap_threshold)

    if args.dry_run:
        print("Dry run only; no files changed.")
        return

    backup_path = backup_timing(timing_path)
    write_json(timing_path, timing)
    print(f"Backed up {backup_path}")
    print(f"Wrote {timing_path}")
    print_warnings(timing, timing_path, threshold_ms=args.gap_threshold)


def command_fit(args: argparse.Namespace) -> None:
    _song_dir, timing_path, timing = load_reviewed_timing(args.song)
    segments = timing["segments"]
    start, end = selected_range(segments, args.start, args.end)
    new_start_ms = parse_ms(args.start_at)
    new_end_ms = parse_ms(args.end_at)

    if new_end_ms <= new_start_ms:
        raise SystemExit("--end-at must be after --start-at")

    old_start_ms = int(segments[start]["start_ms"])
    old_end_ms = int(segments[end]["end_ms"])
    old_span = old_end_ms - old_start_ms
    new_span = new_end_ms - new_start_ms
    if old_span <= 0:
        raise SystemExit("Selected range has no duration to fit.")

    scale = new_span / old_span
    for index in range(start, end + 1):
        old_start = int(segments[index]["start_ms"])
        old_end = int(segments[index]["end_ms"])
        segments[index]["start_ms"] = int(round(new_start_ms + (old_start - old_start_ms) * scale))
        segments[index]["end_ms"] = int(round(new_start_ms + (old_end - old_start_ms) * scale))

    validate_or_exit(timing, timing_path)
    print_report(segments, max(0, start - 2), min(len(segments) - 1, end + 2), args.gap_threshold)

    if args.dry_run:
        print("Dry run only; no files changed.")
        return

    backup_path = backup_timing(timing_path)
    write_json(timing_path, timing)
    print(f"Backed up {backup_path}")
    print(f"Wrote {timing_path}")
    print_warnings(timing, timing_path, threshold_ms=args.gap_threshold)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Inspect and adjust timing/reviewed/timing.json without editing JSON by hand."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    report = subparsers.add_parser("report", help="Print a readable timing table.")
    report.add_argument("song", help="Song folder, slug, or approximate name.")
    report.add_argument("--from", dest="start", help="First segment selector: id, line number, or unique text.")
    report.add_argument("--to", dest="end", help="Last segment selector: id, line number, or unique text.")
    report.add_argument("--around", help="Center the report around this segment selector.")
    report.add_argument("--context", type=int, default=5, help="Lines before/after --around.")
    report.add_argument("--gap-threshold", type=int, default=1200, help="Flag gaps larger than this many ms.")
    report.set_defaults(func=command_report)

    nudge = subparsers.add_parser("nudge", help="Shift a line or range earlier/later by an offset.")
    nudge.add_argument("song", help="Song folder, slug, or approximate name.")
    nudge.add_argument("--from", dest="start", required=True, help="First segment selector.")
    nudge.add_argument("--to", dest="end", help="Last segment selector. Defaults to --from.")
    nudge.add_argument("--shift", required=True, help="Offset such as +400ms, -0.25s, +0.5, or -500.")
    nudge.add_argument("--gap-threshold", type=int, default=1200, help="Flag gaps larger than this many ms.")
    nudge.add_argument("--dry-run", action="store_true", help="Preview without writing timing.json.")
    nudge.set_defaults(func=command_nudge)

    fit = subparsers.add_parser("fit", help="Stretch/compress a range between two anchor times.")
    fit.add_argument("song", help="Song folder, slug, or approximate name.")
    fit.add_argument("--from", dest="start", required=True, help="First segment selector.")
    fit.add_argument("--to", dest="end", required=True, help="Last segment selector.")
    fit.add_argument("--start-at", required=True, help="New range start, such as 0:37.900 or 37.9s.")
    fit.add_argument("--end-at", required=True, help="New range end, such as 0:47.800 or 47.8s.")
    fit.add_argument("--gap-threshold", type=int, default=1200, help="Flag gaps larger than this many ms.")
    fit.add_argument("--dry-run", action="store_true", help="Preview without writing timing.json.")
    fit.set_defaults(func=command_fit)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
