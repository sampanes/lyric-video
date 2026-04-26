"""Import approved image/video media into a song package."""

from __future__ import annotations

import argparse
import shutil
from datetime import datetime, timezone
from pathlib import Path

from pipeline_common import (
    IMAGE_EXTENSIONS,
    REPO_ROOT,
    VIDEO_EXTENSIONS,
    resolve_song_dir,
    slugify,
    song_relative,
    write_json,
)


MEDIA_EXTENSIONS = IMAGE_EXTENSIONS | VIDEO_EXTENSIONS


def media_kind(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix in IMAGE_EXTENSIONS:
        return "image"
    if suffix in VIDEO_EXTENSIONS:
        return "video"
    raise SystemExit(f"Unsupported media extension: {path.suffix}")


def resolve_source(args: argparse.Namespace) -> Path:
    if args.source and args.latest_from:
        raise SystemExit("Use either SOURCE or --latest-from, not both.")
    if not args.source and not args.latest_from:
        raise SystemExit("Provide SOURCE or --latest-from.")

    if args.source:
        source = Path(args.source)
        if not source.exists():
            raise SystemExit(f"Source media not found: {source}")
        if not source.is_file():
            raise SystemExit(f"Source media is not a file: {source}")
        media_kind(source)
        return source

    search_root = Path(args.latest_from)
    if not search_root.exists():
        raise SystemExit(f"Search directory not found: {search_root}")

    extensions = MEDIA_EXTENSIONS
    if args.type == "image":
        extensions = IMAGE_EXTENSIONS
    elif args.type == "video":
        extensions = VIDEO_EXTENSIONS

    iterator = search_root.rglob(args.pattern) if args.recursive else search_root.glob(args.pattern)
    candidates = [
        path
        for path in iterator
        if path.is_file() and path.suffix.lower() in extensions
    ]
    if not candidates:
        raise SystemExit(f"No matching media found under {search_root}")
    return max(candidates, key=lambda path: path.stat().st_mtime)


def destination_dir(song_dir: Path, source: Path, role: str) -> Path:
    kind = media_kind(source)
    if role == "auto":
        role = "source-video" if kind == "video" else "background"

    if role == "source-video":
        if kind != "video":
            raise SystemExit("--role source-video requires a video file.")
        return song_dir / "inputs" / "video"
    if role == "background":
        return song_dir / "assets" / "backgrounds"
    if role == "reference":
        return song_dir / "inputs" / "references"

    raise SystemExit(f"Unknown role: {role}")


def destination_path(song_dir: Path, source: Path, role: str, name: str | None) -> Path:
    dest_dir = destination_dir(song_dir, source, role)
    filename = f"{slugify(name)}{source.suffix.lower()}" if name else source.name
    return dest_dir / filename


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("song", help="Song slug, approximate name, or song folder.")
    parser.add_argument("source", nargs="?", help="Source image/video path to import.")
    parser.add_argument(
        "--latest-from",
        help="Find and import the newest matching media file from this directory.",
    )
    parser.add_argument(
        "--pattern",
        default="*",
        help="Glob pattern used with --latest-from. Defaults to all files.",
    )
    parser.add_argument(
        "--recursive",
        action="store_true",
        help="Search --latest-from recursively.",
    )
    parser.add_argument(
        "--type",
        choices=("any", "image", "video"),
        default="any",
        help="Media type filter for --latest-from.",
    )
    parser.add_argument(
        "--role",
        choices=("auto", "source-video", "background", "reference"),
        default="auto",
        help=(
            "Destination role. auto puts videos in inputs/video and images in "
            "assets/backgrounds."
        ),
    )
    parser.add_argument(
        "--name",
        help="Stable destination basename without extension. Defaults to source filename.",
    )
    parser.add_argument(
        "--move",
        action="store_true",
        help="Move instead of copy. Default is copy to preserve generator output.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite an existing imported media file and metadata sidecar.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the selected source and destination without copying.",
    )
    parser.add_argument(
        "--approval-note",
        default="approved for import by user/agent workflow",
        help="Short note written into the import metadata sidecar.",
    )
    args = parser.parse_args()

    song_dir = resolve_song_dir(args.song)
    if not song_dir.exists():
        raise SystemExit(f"Song folder not found: {song_dir}")

    source = resolve_source(args)
    dest = destination_path(song_dir, source, args.role, args.name)
    metadata_path = dest.with_suffix(".json")

    if dest.exists() and not args.force:
        raise SystemExit(f"Destination already exists, pass --force to overwrite: {dest}")
    if metadata_path.exists() and not args.force:
        raise SystemExit(
            f"Metadata sidecar already exists, pass --force to overwrite: {metadata_path}"
        )

    operation = "move" if args.move else "copy"
    print(f"Song: {song_dir}")
    print(f"Source: {source}")
    print(f"Destination: {dest}")
    print(f"Operation: {operation}")
    if args.dry_run:
        return 0

    dest.parent.mkdir(parents=True, exist_ok=True)
    if args.move:
        shutil.move(str(source), str(dest))
    else:
        shutil.copy2(source, dest)

    write_json(
        metadata_path,
        {
            "created_at": datetime.now(timezone.utc).isoformat(),
            "source_path": str(source),
            "destination": song_relative(dest, song_dir),
            "operation": operation,
            "role": args.role,
            "media_kind": media_kind(dest),
            "approval_note": args.approval_note,
            "repo_root": str(REPO_ROOT),
        },
    )

    print(f"Wrote {dest}")
    print(f"Wrote {metadata_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
