"""Run a synthetic end-to-end smoke test of the local lyric-video pipeline."""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from pipeline_common import REPO_ROOT, SONGS_ROOT, load_json


def safe_remove_smoke_song(song_dir: Path) -> None:
    resolved = song_dir.resolve()
    songs_root = SONGS_ROOT.resolve()
    if resolved.parent != songs_root or not resolved.name.startswith("_smoke_test_"):
        raise SystemExit(f"Refusing to remove non-smoke-test directory: {resolved}")
    shutil.rmtree(resolved)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--keep",
        action="store_true",
        help="Keep the generated ignored smoke-test song folder for inspection.",
    )
    parser.add_argument(
        "--target",
        default=None,
        help="Render target for the smoke test. Defaults to preset/config target.",
    )
    parser.add_argument(
        "--preset",
        default=None,
        help="Optional render preset to exercise during the smoke test.",
    )
    parser.add_argument(
        "--layout",
        choices=("standard", "fullscreen"),
        default=None,
        help="Lyric layout for the smoke test. Defaults to preset/script layout.",
    )
    args = parser.parse_args()

    slug = f"_smoke_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid4().hex[:8]}"
    song_dir = SONGS_ROOT / slug
    song_dir.mkdir(parents=True, exist_ok=False)

    audio_path = song_dir / "smoke_song.wav"
    lyrics_path = song_dir / "smoke_lyrics.txt"
    vibes_path = song_dir / "inputs" / "song_style_prompt.txt"
    vibes_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        subprocess.run(
            [
                "ffmpeg",
                "-hide_banner",
                "-loglevel",
                "warning",
                "-y",
                "-f",
                "lavfi",
                "-i",
                "sine=frequency=220:duration=8",
                "-c:a",
                "pcm_s16le",
                str(audio_path),
            ],
            check=True,
        )
        lyrics_path.write_text(
            "\n".join(
                [
                    "[Smoke test, synthetic audio, no real song]",
                    "This is the first smoke test line",
                    "The renderer should make a draft video",
                    "The files should land in the right folders",
                    "",
                ]
            ),
            encoding="utf-8",
        )
        vibes_path.write_text(
            "Synthetic smoke-test description used to verify song_vibes ingestion.\n",
            encoding="utf-8",
        )

        command = [
            sys.executable,
            "scripts\\make_videos.py",
            slug,
            "--force",
        ]
        if args.layout:
            command.extend(["--layout", args.layout])
        if args.target:
            command.extend(["--targets", args.target])
        if args.preset:
            command.extend(["--preset", args.preset])
        subprocess.run(command, cwd=REPO_ROOT, check=True)
        config = load_json(song_dir / "song.json")
        if not config.get("audio", "").startswith("inputs/audio/"):
            raise SystemExit(f"Smoke test failed: audio was not normalized in {song_dir}")
        if not config.get("lyrics", "").startswith("inputs/lyrics/"):
            raise SystemExit(f"Smoke test failed: lyrics were not normalized in {song_dir}")
        if "Synthetic smoke-test description" not in config.get("song_vibes", ""):
            raise SystemExit(f"Smoke test failed: song_vibes file was not ingested in {song_dir}")
        subprocess.run(
            [
                sys.executable,
                "scripts\\validate_song.py",
                slug,
                "--require-timing",
                "--check-tools",
            ],
            cwd=REPO_ROOT,
            check=True,
        )

        print(f"Smoke test passed: {song_dir}")
        if args.keep:
            print(f"Kept smoke-test song folder: {song_dir}")
        return 0
    finally:
        if not args.keep and song_dir.exists():
            safe_remove_smoke_song(song_dir)


if __name__ == "__main__":
    raise SystemExit(main())
