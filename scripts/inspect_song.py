"""Inspect a song folder and print the next likely pipeline command."""

from __future__ import annotations

import argparse
from pathlib import Path

from pipeline_common import (
    AUDIO_EXTENSIONS,
    LYRIC_EXTENSIONS,
    collect_candidates,
    load_json,
    missing_song_directories,
    resolve_song_dir,
    song_vibes_files,
)


def rel(path: Path, root: Path) -> str:
    try:
        return str(path.relative_to(root)).replace("\\", "/")
    except ValueError:
        return str(path)


def print_paths(label: str, paths: list[Path], song_dir: Path) -> None:
    print(f"{label}: {len(paths)}")
    for path in paths:
        print(f"  - {rel(path, song_dir)}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("song", help="Song slug, approximate name, or song folder.")
    args = parser.parse_args()

    song_dir = resolve_song_dir(args.song)
    print(f"Song directory: {song_dir}")
    if not song_dir.exists():
        print("Status: missing song directory")
        print("Next: create the folder and add one audio file plus one lyric file.")
        return 1

    config_path = song_dir / "song.json"
    config = load_json(config_path) if config_path.exists() else None
    print(f"Config: {'present' if config else 'missing'}")
    if config:
        print(f"Title: {config.get('title', '(missing)')}")
        print(f"Audio: {config.get('audio', '(missing)')}")
        print(f"Lyrics: {config.get('lyrics', '(missing)')}")
        print(f"Style prompt: {config.get('style_prompt', '(missing)')}")
        if config.get("song_vibes"):
            print("Song vibes: present")
        else:
            print("Song vibes: missing/empty")

    audio_candidates = collect_candidates(song_dir, AUDIO_EXTENSIONS)
    lyric_candidates = collect_candidates(
        song_dir,
        LYRIC_EXTENSIONS,
        exclude_song_vibes=True,
    )
    vibe_files = song_vibes_files(song_dir)
    print_paths("Audio candidates", audio_candidates, song_dir)
    print_paths("Lyric candidates", lyric_candidates, song_dir)
    print_paths("Style prompt / vibe files", vibe_files, song_dir)
    missing_dirs = missing_song_directories(song_dir)
    print_paths("Missing recommended directories", missing_dirs, song_dir)

    timing_path = song_dir / "timing" / "reviewed" / "timing.json"
    exports = sorted((song_dir / "exports").glob("*.mp4")) if (song_dir / "exports").exists() else []
    subtitles = sorted((song_dir / "subtitles").glob("*.ass")) if (song_dir / "subtitles").exists() else []
    print(f"Reviewed timing: {'present' if timing_path.exists() else 'missing'}")
    print_paths("Subtitle files", subtitles, song_dir)
    print_paths("Exported videos", exports, song_dir)

    song_arg = song_dir.name
    if not config and len(audio_candidates) == 1 and len(lyric_candidates) == 1:
        print(f"Next: python scripts\\make_videos.py \"{song_arg}\" --force --targets horizontal")
    elif not config:
        print("Next: resolve audio/lyric ambiguity, then run make_videos.")
    elif not timing_path.exists():
        print(f"Next: python scripts\\make_videos.py \"{song_arg}\" --force --targets horizontal")
    elif not exports:
        print(f"Next: python scripts\\render_song.py \"{song_arg}\" --targets horizontal")
    else:
        print(f"Next: python scripts\\validate_song.py \"{song_arg}\" --require-timing --check-tools")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
