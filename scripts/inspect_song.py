"""Inspect a song folder and print the next likely pipeline command."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from pipeline_common import (
    AUDIO_EXTENSIONS,
    LYRIC_EXTENSIONS,
    collect_candidates,
    load_json,
    missing_song_directories,
    resolve_song_dir,
    song_vibes_files,
    validate_song_package,
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


def paths_json(paths: list[Path], song_dir: Path) -> list[str]:
    return [rel(path, song_dir) for path in paths]


def command(value: str) -> dict:
    return {"command": value}


def determine_next_actions(state: dict) -> list[dict]:
    song_arg = state["song_dir_name"]
    if not state["exists"]:
        return [{"label": "Create the song folder and add one audio file plus one lyric file."}]

    if state["config"].get("error"):
        return [{"label": "Fix song.json before running pipeline commands."}]

    config_present = state["config"]["present"]
    audio_count = len(state["audio_candidates"])
    lyric_count = len(state["lyric_candidates"])
    timing_present = state["timing"]["present"]
    exports_present = bool(state["exports"])

    if not config_present and audio_count == 1 and lyric_count == 1:
        return [
            {
                "label": "Create config, fallback timing, subtitles, and first horizontal draft.",
                **command(f'python scripts\\make_videos.py "{song_arg}" --force --targets horizontal'),
            }
        ]
    if not config_present:
        return [
            {
                "label": "Resolve audio/lyric ambiguity and write song.json.",
                **command(f'python scripts\\intake_song.py "{song_arg}"'),
            }
        ]
    if not timing_present:
        return [
            {
                "label": "Generate reviewed timing, subtitles, and first horizontal draft.",
                **command(f'python scripts\\make_videos.py "{song_arg}" --force --targets horizontal'),
            }
        ]
    if not exports_present:
        return [
            {
                "label": "Render from reviewed timing.",
                **command(f'python scripts\\render_song.py "{song_arg}" --targets horizontal'),
            }
        ]
    return [
        {
            "label": "Validate the current song package.",
            **command(f'python scripts\\validate_song.py "{song_arg}" --require-timing --check-tools'),
        }
    ]


def build_song_inspection(song_ref: str, *, check_tools: bool = False) -> dict:
    song_dir = resolve_song_dir(song_ref)
    state: dict = {
        "song_ref": song_ref,
        "song_dir": str(song_dir),
        "song_dir_name": song_dir.name,
        "exists": song_dir.exists(),
        "config": {"present": False},
        "audio_candidates": [],
        "lyric_candidates": [],
        "style_prompt_files": [],
        "missing_recommended_directories": [],
        "timing": {"present": False},
        "subtitles": [],
        "exports": [],
        "validation": {"errors": [], "warnings": []},
        "next_actions": [],
    }

    if not song_dir.exists():
        state["status"] = "missing_song_directory"
        state["next_actions"] = determine_next_actions(state)
        return state

    config_path = song_dir / "song.json"
    config = None
    if config_path.exists():
        try:
            config = load_json(config_path)
        except json.JSONDecodeError as exc:
            state["config"] = {
                "present": True,
                "path": rel(config_path, song_dir),
                "error": str(exc),
            }
        else:
            state["config"] = {
                "present": True,
                "path": rel(config_path, song_dir),
                "title": config.get("title"),
                "audio": config.get("audio"),
                "lyrics": config.get("lyrics"),
                "style_prompt": config.get("style_prompt"),
                "song_vibes_present": bool(config.get("song_vibes")),
                "bpm": config.get("bpm"),
            }

    audio_candidates = collect_candidates(song_dir, AUDIO_EXTENSIONS)
    lyric_candidates = collect_candidates(song_dir, LYRIC_EXTENSIONS, exclude_song_vibes=True)
    vibe_files = song_vibes_files(song_dir)
    missing_dirs = missing_song_directories(song_dir)
    timing_path = song_dir / "timing" / "reviewed" / "timing.json"
    subtitles = sorted((song_dir / "subtitles").glob("*.ass")) if (song_dir / "subtitles").exists() else []
    exports = sorted((song_dir / "exports").glob("*.mp4")) if (song_dir / "exports").exists() else []

    state["audio_candidates"] = paths_json(audio_candidates, song_dir)
    state["lyric_candidates"] = paths_json(lyric_candidates, song_dir)
    state["style_prompt_files"] = paths_json(vibe_files, song_dir)
    state["missing_recommended_directories"] = paths_json(missing_dirs, song_dir)
    state["timing"] = {
        "present": timing_path.exists(),
        "path": rel(timing_path, song_dir),
    }
    if timing_path.exists():
        try:
            timing = load_json(timing_path)
        except json.JSONDecodeError as exc:
            state["timing"]["error"] = str(exc)
        else:
            state["timing"]["source"] = timing.get("source")
            state["timing"]["segment_count"] = len(timing.get("segments", []))
            state["timing"]["strategy"] = timing.get("strategy")
    state["subtitles"] = paths_json(subtitles, song_dir)
    state["exports"] = paths_json(exports, song_dir)

    if config:
        errors, warnings = validate_song_package(
            song_dir,
            config,
            require_timing=False,
            check_tools=check_tools,
        )
        state["validation"] = {"errors": errors, "warnings": warnings}

    if state["config"].get("error"):
        state["status"] = "config_error"
    elif state["validation"]["errors"]:
        state["status"] = "validation_errors"
    elif not state["config"]["present"]:
        state["status"] = "needs_config"
    elif not state["timing"]["present"]:
        state["status"] = "needs_timing"
    elif not state["exports"]:
        state["status"] = "needs_render"
    else:
        state["status"] = "has_render"

    state["next_actions"] = determine_next_actions(state)
    return state


def print_text_report(state: dict) -> None:
    song_dir = Path(state["song_dir"])
    print(f"Song directory: {song_dir}")
    if not state["exists"]:
        print("Status: missing song directory")
        print("Next: create the folder and add one audio file plus one lyric file.")
        return

    config = state["config"]
    print(f"Config: {'present' if config.get('present') else 'missing'}")
    if config.get("error"):
        print(f"Config error: {config['error']}")
    elif config.get("present"):
        print(f"Title: {config.get('title') or '(missing)'}")
        print(f"Audio: {config.get('audio') or '(missing)'}")
        print(f"Lyrics: {config.get('lyrics') or '(missing)'}")
        print(f"Style prompt: {config.get('style_prompt') or '(missing)'}")
        print(f"Song vibes: {'present' if config.get('song_vibes_present') else 'missing/empty'}")

    print_paths("Audio candidates", [song_dir / path for path in state["audio_candidates"]], song_dir)
    print_paths("Lyric candidates", [song_dir / path for path in state["lyric_candidates"]], song_dir)
    print_paths("Style prompt / vibe files", [song_dir / path for path in state["style_prompt_files"]], song_dir)
    print_paths(
        "Missing recommended directories",
        [song_dir / path for path in state["missing_recommended_directories"]],
        song_dir,
    )

    print(f"Reviewed timing: {'present' if state['timing']['present'] else 'missing'}")
    if state["timing"].get("source"):
        print(f"Timing source: {state['timing']['source']}")
    print_paths("Subtitle files", [song_dir / path for path in state["subtitles"]], song_dir)
    print_paths("Exported videos", [song_dir / path for path in state["exports"]], song_dir)

    for error in state["validation"]["errors"]:
        print(f"Validation error: {error}")
    for warning in state["validation"]["warnings"]:
        print(f"Validation warning: {warning}")

    next_action = state["next_actions"][0] if state["next_actions"] else None
    if next_action:
        print(f"Next: {next_action.get('command') or next_action['label']}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("song", help="Song slug, approximate name, or song folder.")
    parser.add_argument("--json", action="store_true", help="Print machine-readable inspection JSON.")
    parser.add_argument("--check-tools", action="store_true", help="Include ffmpeg/ffprobe checks in validation.")
    args = parser.parse_args()

    state = build_song_inspection(args.song, check_tools=args.check_tools)
    if args.json:
        print(json.dumps(state, indent=2))
    else:
        print_text_report(state)
    return 0 if state["exists"] and not state["validation"]["errors"] and not state["config"].get("error") else 1


if __name__ == "__main__":
    raise SystemExit(main())
