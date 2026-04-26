"""Remove copied .gitkeep files from a real song workspace."""

from __future__ import annotations

import argparse

from pipeline_common import resolve_song_dir


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("song", help="Song slug, approximate name, or song folder.")
    parser.add_argument(
        "--include-template",
        action="store_true",
        help="Allow pruning songs/template_song. Normally this is refused.",
    )
    args = parser.parse_args()

    song_dir = resolve_song_dir(args.song)
    if song_dir.name == "template_song" and not args.include_template:
        raise SystemExit("Refusing to prune tracked template_song without --include-template.")

    removed = 0
    for path in song_dir.rglob(".gitkeep"):
        if path.is_file():
            path.unlink()
            removed += 1

    print(f"Removed {removed} .gitkeep files from {song_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
