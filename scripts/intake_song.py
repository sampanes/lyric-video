"""Interactively create or update a song config from basic metadata.

This script asks for the minimum information needed to start a song workspace.
It auto-detects the source audio and lyric files when there is a clear match
and only asks for clarification when the input is ambiguous.
"""

from __future__ import annotations

import argparse
import json
import shutil
import difflib
import re
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SONGS_ROOT = REPO_ROOT / "songs"
TEMPLATE_CONFIG = SONGS_ROOT / "template_song" / "song.json"

if str(REPO_ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "scripts"))
from pipeline_common import ensure_song_structure  # noqa: E402

AUDIO_EXTENSIONS = {".wav", ".mp3", ".flac", ".m4a", ".aac", ".ogg", ".opus"}
LYRIC_EXTENSIONS = {".txt", ".md", ".lrc"}
SONG_STYLE_PROMPT_FILENAME = "song_style_prompt.txt"
SONG_VIBES_FILENAMES = {
    "description.md",
    "description.txt",
    "prompt.md",
    "prompt.txt",
    "song-description.md",
    "song-description.txt",
    "song-vibes.md",
    "song-vibes.txt",
    "song_description.md",
    "song_description.txt",
    "song-style-prompt.md",
    "song-style-prompt.txt",
    "song_style_prompt.md",
    "song_style_prompt.txt",
    "song_vibes.md",
    "song_vibes.txt",
    "vibes.md",
    "vibes.txt",
}
MANAGED_INPUT_SCAN_DIRS = {
    "assets",
    "exports",
    "notes",
    "renders",
    "subtitles",
    "timing",
}


def caps_version(value: str) -> str:
    cleaned = value.replace("_", " ").replace("-", " ")
    parts = [part for part in cleaned.split() if part]
    return " ".join(part[:1].upper() + part[1:] for part in parts)


def slugify(value: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip().lower())
    return re.sub(r"-+", "-", cleaned).strip("-")


def prompt(label: str, default: str | None = None) -> str:
    suffix = f" [{default}]" if default else ""
    value = input(f"{label}{suffix}: ").strip()
    if value:
        return value
    if default is not None:
        return default
    return ""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "song_slug",
        nargs="?",
        help="Song folder slug under songs/ (for example man-behind-the-bar).",
    )
    parser.add_argument(
        "--keep-gitkeep",
        action="store_true",
        help="Do not remove copied .gitkeep files from the real song folder.",
    )
    return parser.parse_args()


def collect_candidates(song_dir: Path, extensions: set[str]) -> list[Path]:
    candidates: list[Path] = []
    for path in song_dir.rglob("*"):
        if not path.is_file():
            continue
        try:
            parts = path.relative_to(song_dir).parts[:-1]
        except ValueError:
            parts = ()
        if any(part.lower() in MANAGED_INPUT_SCAN_DIRS for part in parts):
            continue
        if path.name.startswith("."):
            continue
        if extensions == LYRIC_EXTENSIONS and path.name.lower() in SONG_VIBES_FILENAMES:
            continue
        if path.suffix.lower() not in extensions:
            continue
        candidates.append(path)
    return sorted(candidates)


def list_song_folders() -> list[Path]:
    folders = []
    for path in SONGS_ROOT.iterdir():
        if path.is_dir() and path.name != "template_song":
            folders.append(path)
    return sorted(folders)


def resolve_song_dir(user_value: str) -> Path:
    direct = SONGS_ROOT / user_value
    if direct.exists():
        return direct

    slug = slugify(user_value)
    slug_path = SONGS_ROOT / slug
    if slug_path.exists():
        return slug_path

    existing = list_song_folders()
    names = [path.name for path in existing]
    if names:
        direct_hits = [path for path in existing if slug in path.name or path.name in slug]
        if len(direct_hits) == 1:
            return direct_hits[0]

        close = difflib.get_close_matches(slug, names, n=3, cutoff=0.6)
        if len(close) == 1:
            return SONGS_ROOT / close[0]

        if len(close) > 1:
            print("Multiple close song matches found:")
            for index, name in enumerate(close, start=1):
                print(f"  {index}. {name}")
            response = prompt("Choose a song folder or press Enter to create a new one")
            if response:
                chosen = SONGS_ROOT / response
                if chosen.exists():
                    return chosen
                raise SystemExit(f"Song folder not found: {chosen}")

    return slug_path


def resolve_typed_path(response: str, song_dir: Path) -> Path | None:
    candidate = Path(response)
    if not candidate.is_absolute():
        candidate = song_dir / response
    if not candidate.exists():
        print(f"Path not found: {candidate}")
        return None
    if not candidate.is_file():
        print(f"Path is not a file: {candidate}")
        return None
    return candidate


def choose_unique(candidates: list[Path], kind: str, song_dir: Path) -> Path:
    while True:
        if len(candidates) == 1:
            chosen = candidates[0]
            display = chosen.relative_to(song_dir)
            response = prompt(f"Use {kind} file '{display}'? [Y/n/path]", "y").strip()
            lower = response.lower()
            if lower in ("", "y", "yes"):
                return chosen
            if lower in ("n", "no"):
                manual = prompt(f"Enter {kind} path", "").strip()
                if not manual:
                    print("No path provided, rescanning instead.")
                    candidates = collect_candidates(song_dir, AUDIO_EXTENSIONS if kind == "audio" else LYRIC_EXTENSIONS)
                    continue
                typed = resolve_typed_path(manual, song_dir)
                if typed is not None:
                    return typed
                continue
            typed = resolve_typed_path(response, song_dir)
            if typed is not None:
                return typed
            continue

        if len(candidates) > 1:
            print(f"Found multiple {kind} files in {song_dir}:")
            for index, candidate in enumerate(candidates, start=1):
                print(f"  {index}. {candidate.relative_to(song_dir)}")
            response = prompt(f"Enter number, or a {kind} path", "").strip()
            if response.isdigit():
                idx = int(response) - 1
                if 0 <= idx < len(candidates):
                    return candidates[idx]
                print("Number out of range.")
                continue
            if response:
                typed = resolve_typed_path(response, song_dir)
                if typed is not None:
                    return typed
            continue

        # Zero candidates.
        print(f"No {kind} file found in:")
        print(f"  {song_dir}")
        print(f"Drop the {kind} file anywhere inside that folder.")
        response = prompt("Press Enter to rescan, type a path, or 'q' to abort", "").strip()
        if response.lower() == "q":
            raise SystemExit(f"Aborted before {kind} file was provided.")
        if response:
            typed = resolve_typed_path(response, song_dir)
            if typed is not None:
                return typed
            continue
        candidates = collect_candidates(song_dir, AUDIO_EXTENSIONS if kind == "audio" else LYRIC_EXTENSIONS)


def ensure_canonical_location(source: Path, target_dir: Path) -> Path:
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / source.name
    if source.resolve() == target.resolve():
        return target
    if target.exists():
        return target
    shutil.move(str(source), str(target))
    return target


def parse_optional_bpm(value: str) -> float | int | None:
    if not value.strip():
        return None
    try:
        bpm = float(value)
    except ValueError as exc:
        raise SystemExit(f"BPM must be numeric when provided: {value}") from exc
    if bpm <= 0:
        raise SystemExit("BPM must be greater than zero when provided.")
    if bpm.is_integer():
        return int(bpm)
    return bpm


def prune_gitkeep_files(song_dir: Path) -> int:
    count = 0
    for path in song_dir.rglob(".gitkeep"):
        if path.is_file():
            path.unlink()
            count += 1
    return count


def main() -> int:
    args = parse_args()
    template = json.loads(TEMPLATE_CONFIG.read_text(encoding="utf-8"))

    folder_input = args.song_slug or prompt("Song folder/slug")
    if not folder_input:
        raise SystemExit("Song folder/slug is required.")

    song_dir = resolve_song_dir(folder_input)
    created = not song_dir.exists()
    song_dir.mkdir(parents=True, exist_ok=True)
    ensure_song_structure(song_dir)
    style_prompt_path = song_dir / "inputs" / "song_style_prompt.txt"
    if not style_prompt_path.exists():
        style_prompt_path.touch()
    if created:
        print("")
        print(f"Created song folder:\n  {song_dir}")
        print("Drop the audio + lyric files anywhere inside that folder.")
        print(f"(Empty {style_prompt_path.relative_to(song_dir)} is ready for your background description later.)")
        input("Press Enter when the files are in place... ")
        print("")

    title_default = caps_version(song_dir.name)
    title = prompt("Song title", title_default)
    artist = prompt("Artist / creator", template.get("artist", "Unknown Artist"))
    song_vibes = prompt("Song vibes", template.get("song_vibes", ""))
    bpm = parse_optional_bpm(prompt("BPM (optional)", ""))

    audio_candidate = choose_unique(
        collect_candidates(song_dir, AUDIO_EXTENSIONS), "audio", song_dir
    )
    lyric_candidate = choose_unique(
        collect_candidates(song_dir, LYRIC_EXTENSIONS), "lyrics", song_dir
    )

    audio_target = ensure_canonical_location(audio_candidate, song_dir / "inputs" / "audio")
    lyric_target = ensure_canonical_location(lyric_candidate, song_dir / "inputs" / "lyrics")

    config = dict(template)
    config["id"] = song_dir.name
    config["title"] = title
    config["artist"] = artist
    config["song_vibes"] = song_vibes
    config["bpm"] = bpm
    config["audio"] = str(audio_target.relative_to(song_dir)).replace("\\", "/")
    config["lyrics"] = str(lyric_target.relative_to(song_dir)).replace("\\", "/")

    output = dict(template.get("output") or {})
    output["filename"] = f"{song_dir.name}.mp4"
    config["output"] = output

    config_path = song_dir / "song.json"
    config_path.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")

    print(f"Wrote {config_path}")
    print(f"Audio:  {audio_target.relative_to(song_dir)}")
    print(f"Lyrics: {lyric_target.relative_to(song_dir)}")
    if not args.keep_gitkeep:
        pruned = prune_gitkeep_files(song_dir)
        if pruned:
            print(f"Removed {pruned} copied .gitkeep files from {song_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
