"""Shared helpers for the lightweight script-based pipeline."""

from __future__ import annotations

import difflib
import json
import math
import re
import shutil
import subprocess
import textwrap
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SONGS_ROOT = REPO_ROOT / "songs"
PRESETS_ROOT = REPO_ROOT / "presets"
TEMPLATE_CONFIG = SONGS_ROOT / "template_song" / "song.json"

AUDIO_EXTENSIONS = {".wav", ".mp3", ".flac", ".m4a", ".aac", ".ogg", ".opus"}
LYRIC_EXTENSIONS = {".txt", ".md", ".lrc"}
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}
VIDEO_EXTENSIONS = {".mp4", ".mov", ".webm", ".mkv"}
SONG_STYLE_PROMPT_FILENAME = "song_style_prompt.txt"
LAYOUTS = ("standard", "fullscreen", "soft_scroll")
SUSPICIOUS_TEXT_MARKERS = {
    "\ufffd": "Unicode replacement character",
    "â€œ": "mojibake for left double quote",
    "â€\u009d": "mojibake for right double quote",
    "â€™": "mojibake for apostrophe/right single quote",
    "â€˜": "mojibake for left single quote",
    "â€¦": "mojibake for ellipsis",
    "Ã©": "mojibake marker for accented UTF-8 text",
    "Â ": "mojibake non-breaking-space marker",
    "ƒ?": "mojibake marker seen in some console/codepage displays",
}
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
REQUIRED_SONG_DIRECTORIES = (
    "inputs/audio",
    "inputs/lyrics",
    "inputs/prompts",
    "inputs/references",
    "inputs/video",
    "timing/raw/automation",
    "timing/raw/imported",
    "timing/raw/manual",
    "timing/raw/whisper",
    "timing/reviewed",
    "timing/derived",
    "subtitles",
    "assets/backgrounds",
    "assets/overlays",
    "renders",
    "exports",
    "notes",
)

RENDER_TARGETS = {
    "horizontal": {
        "label": "Horizontal",
        "ratio": "16:9",
        "width": 1920,
        "height": 1080,
        "suffix": "horizontal",
        "bottom_margin_pct": 0.13,
        "font_divisor": 16,
    },
    "vertical": {
        "label": "Vertical",
        "ratio": "9:16",
        "width": 1080,
        "height": 1920,
        "suffix": "vertical",
        "bottom_margin_pct": 0.24,
        "font_divisor": 18,
    },
    "square": {
        "label": "Square",
        "ratio": "1:1",
        "width": 1080,
        "height": 1080,
        "suffix": "square",
        "bottom_margin_pct": 0.18,
        "font_divisor": 18,
    },
    "portrait": {
        "label": "Portrait",
        "ratio": "4:5",
        "width": 1080,
        "height": 1350,
        "suffix": "4x5",
        "bottom_margin_pct": 0.21,
        "font_divisor": 18,
    },
}

TARGET_ALIASES = {
    "16:9": "horizontal",
    "16x9": "horizontal",
    "youtube": "horizontal",
    "9:16": "vertical",
    "9x16": "vertical",
    "shorts": "vertical",
    "reels": "vertical",
    "tiktok": "vertical",
    "1:1": "square",
    "1x1": "square",
    "4:5": "portrait",
    "4x5": "portrait",
}


def slugify(value: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip().lower())
    return re.sub(r"-+", "-", cleaned).strip("-")


def caps_version(value: str) -> str:
    cleaned = value.replace("_", " ").replace("-", " ")
    parts = [part for part in cleaned.split() if part]
    return " ".join(part[:1].upper() + part[1:] for part in parts)


def available_render_targets() -> str:
    return ", ".join(RENDER_TARGETS)


def available_layouts() -> str:
    return ", ".join(LAYOUTS)


def preset_key(value: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9]+", "_", value.strip().lower())
    return re.sub(r"_+", "_", cleaned).strip("_")


def available_presets() -> list[str]:
    if not PRESETS_ROOT.exists():
        return []
    return sorted(path.stem for path in PRESETS_ROOT.glob("*.json") if path.is_file())


def load_preset(preset_ref: str | None) -> dict:
    if not preset_ref:
        return {}

    raw_path = Path(preset_ref)
    candidates: list[Path] = []
    if raw_path.suffix.lower() == ".json":
        candidates.append(raw_path if raw_path.is_absolute() else REPO_ROOT / raw_path)
        candidates.append(PRESETS_ROOT / raw_path.name)
    else:
        candidates.append(PRESETS_ROOT / f"{preset_key(preset_ref)}.json")
        candidates.append(PRESETS_ROOT / f"{slugify(preset_ref)}.json")

    for candidate in candidates:
        if candidate.exists():
            preset = load_json(candidate)
            preset["_preset_path"] = str(candidate.relative_to(REPO_ROOT)).replace("\\", "/")
            return preset

    known = available_presets()
    known_text = f" Known presets: {', '.join(known)}." if known else ""
    raise SystemExit(f"Unknown preset '{preset_ref}'.{known_text}")


def apply_preset_to_config(config: dict, preset: dict) -> dict:
    if not preset:
        return config

    merged = deepcopy(config)
    merged["_render_preset"] = preset.get("id") or preset.get("name") or Path(preset.get("_preset_path", "")).stem
    merged["_render_preset_path"] = preset.get("_preset_path")

    preset_output = preset.get("output", {})
    if isinstance(preset_output, dict):
        output = dict(merged.get("output", {}))
        for key in ("targets", "fps"):
            if key in preset_output:
                output[key] = preset_output[key]
        merged["output"] = output

    if "subtitle_style" in preset:
        merged["subtitle_style"] = preset["subtitle_style"]

    preset_subtitle = preset.get("subtitle", {})
    if isinstance(preset_subtitle, dict):
        subtitle = dict(merged.get("subtitle", {}))
        subtitle.update(preset_subtitle)
        merged["subtitle"] = subtitle

    if "background_mode" in preset and not merged.get("background_mode"):
        merged["background_mode"] = preset["background_mode"]

    return merged


def preset_layout(preset: dict) -> str | None:
    value = preset.get("layout") if preset else None
    if value is None:
        return None
    if value not in LAYOUTS:
        raise SystemExit(f"Preset layout must be one of {available_layouts()}, got {value!r}.")
    return value


def resolve_layout(cli_layout: str | None, preset: dict | None, config: dict) -> str:
    layout = cli_layout or preset_layout(preset or {}) or config.get("layout") or "standard"
    if layout not in LAYOUTS:
        raise SystemExit(f"Unknown lyric layout '{layout}'. Expected one of: {available_layouts()}.")
    return layout


def normalize_render_targets(raw_targets: str | list[str] | None) -> list[str]:
    if not raw_targets:
        return ["horizontal"]
    if isinstance(raw_targets, str):
        raw_targets = [raw_targets]

    normalized: list[str] = []
    for raw_target in raw_targets:
        if not isinstance(raw_target, str):
            raise SystemExit(f"Render target must be a string, got {raw_target!r}.")
        target_key = raw_target.strip().lower()
        if not target_key:
            continue
        if target_key == "all":
            expanded = list(RENDER_TARGETS)
        else:
            expanded = [TARGET_ALIASES.get(target_key, target_key)]

        for target_name in expanded:
            if target_name not in RENDER_TARGETS:
                raise SystemExit(
                    f"Unknown render target '{raw_target}'. "
                    f"Expected one of: {available_render_targets()}, all."
                )
            if target_name not in normalized:
                normalized.append(target_name)

    return normalized or ["horizontal"]


def render_target(target_name: str) -> dict:
    normalized = TARGET_ALIASES.get(target_name.lower(), target_name.lower())
    try:
        return dict(RENDER_TARGETS[normalized])
    except KeyError as exc:
        raise SystemExit(
            f"Unknown render target '{target_name}'. "
            f"Expected one of: {available_render_targets()}, all."
        ) from exc


def resolve_song_dir(song_ref: str) -> Path:
    direct = SONGS_ROOT / song_ref
    if direct.exists():
        return direct

    slug = slugify(song_ref)
    slug_path = SONGS_ROOT / slug
    if slug_path.exists():
        return slug_path

    existing = sorted(path for path in SONGS_ROOT.iterdir() if path.is_dir())
    names = [path.name for path in existing if path.name != "template_song"]
    direct_hits = [name for name in names if slug in name or name in slug]
    if len(direct_hits) == 1:
        return SONGS_ROOT / direct_hits[0]

    close = difflib.get_close_matches(slug, names, n=1, cutoff=0.6)
    if close:
        return SONGS_ROOT / close[0]

    return slug_path


def is_song_vibes_file(path: Path) -> bool:
    return path.name.lower() in SONG_VIBES_FILENAMES


def is_under_managed_scan_dir(path: Path, song_dir: Path) -> bool:
    try:
        parts = path.relative_to(song_dir).parts[:-1]
    except ValueError:
        return False
    return any(part.lower() in MANAGED_INPUT_SCAN_DIRS for part in parts)


def collect_candidates(
    song_dir: Path,
    extensions: set[str],
    *,
    exclude_song_vibes: bool = False,
) -> list[Path]:
    candidates: list[Path] = []
    for path in song_dir.rglob("*"):
        if not path.is_file() or path.name.startswith("."):
            continue
        if is_under_managed_scan_dir(path, song_dir):
            continue
        if path.name.lower() == "readme.md":
            continue
        if exclude_song_vibes and is_song_vibes_file(path):
            continue
        if path.suffix.lower() in extensions:
            candidates.append(path)
    return sorted(candidates)


def require_unique(candidates: list[Path], label: str, song_dir: Path) -> Path:
    if len(candidates) == 1:
        return candidates[0]
    if not candidates:
        raise SystemExit(f"No {label} file found under {song_dir}.")

    details = "\n".join(f"- {path.relative_to(song_dir)}" for path in candidates)
    raise SystemExit(f"Multiple {label} files found under {song_dir}:\n{details}")


def ensure_canonical_input(source: Path, target_dir: Path) -> Path:
    """Move a newly discovered input into its canonical song-package folder."""

    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / source.name
    if source.resolve() == target.resolve():
        return target
    if target.exists():
        raise SystemExit(
            f"Cannot normalize input because destination already exists: {target}"
        )
    shutil.move(str(source), str(target))
    return target


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def song_relative(path: Path, song_dir: Path) -> str:
    return str(path.relative_to(song_dir)).replace("\\", "/")


def missing_song_directories(song_dir: Path) -> list[Path]:
    return [song_dir / directory for directory in REQUIRED_SONG_DIRECTORIES if not (song_dir / directory).is_dir()]


def ensure_song_structure(song_dir: Path) -> None:
    for directory in REQUIRED_SONG_DIRECTORIES:
        (song_dir / directory).mkdir(parents=True, exist_ok=True)


def ffmpeg_input_path(path: Path, cwd: Path) -> str:
    try:
        return str(path.resolve().relative_to(cwd.resolve())).replace("\\", "/")
    except ValueError:
        return str(path)


def extract_song_vibes(lyrics_path: Path) -> str:
    vibe_lines = []
    for line in lyrics_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped.startswith("[") and stripped.endswith("]"):
            vibe_lines.append(stripped[1:-1].strip())
    return " | ".join(vibe_lines)


def song_vibes_files(song_dir: Path) -> list[Path]:
    candidates = [
        path
        for path in song_dir.rglob("*")
        if path.is_file()
        and is_song_vibes_file(path)
        and not is_under_managed_scan_dir(path, song_dir)
    ]
    return sorted(candidates, key=lambda path: (path.name.lower() != SONG_STYLE_PROMPT_FILENAME, str(path)))


def extract_song_vibes_file(song_dir: Path) -> str:
    parts = []
    for path in song_vibes_files(song_dir):
        value = path.read_text(encoding="utf-8").strip()
        if value:
            parts.append(value)
    return " | ".join(parts)


def collect_song_vibes(song_dir: Path, lyrics_path: Path) -> str:
    parts = [
        value
        for value in (extract_song_vibes(lyrics_path), extract_song_vibes_file(song_dir))
        if value
    ]
    return " | ".join(parts)


def merge_pipe_text(existing: str, discovered: str) -> str:
    parts: list[str] = []
    for value in (existing, discovered):
        for part in value.split(" | "):
            stripped = part.strip()
            if stripped and stripped not in parts:
                parts.append(stripped)
    return " | ".join(parts)


def refresh_song_vibes_from_sources(song_dir: Path, config: dict) -> dict:
    updated = dict(config)
    changed = False
    style_prompt = song_dir / "inputs" / SONG_STYLE_PROMPT_FILENAME
    if style_prompt.exists() and not updated.get("style_prompt"):
        updated["style_prompt"] = song_relative(style_prompt, song_dir)
        changed = True

    lyrics_value = config.get("lyrics")
    if not lyrics_value:
        return updated if changed else config
    lyrics_path = song_dir / lyrics_value
    if not lyrics_path.exists():
        if changed:
            write_json(song_dir / "song.json", updated)
        return updated if changed else config

    discovered = collect_song_vibes(song_dir, lyrics_path)
    if discovered:
        merged = merge_pipe_text(config.get("song_vibes", ""), discovered)
        if merged != config.get("song_vibes", ""):
            updated["song_vibes"] = merged
            changed = True

    if changed:
        write_json(song_dir / "song.json", updated)
    return updated if changed else config


def ensure_song_config(song_dir: Path) -> dict:
    ensure_song_structure(song_dir)
    config_path = song_dir / "song.json"
    if config_path.exists():
        return refresh_song_vibes_from_sources(song_dir, load_json(config_path))

    template = load_json(TEMPLATE_CONFIG)
    audio = require_unique(collect_candidates(song_dir, AUDIO_EXTENSIONS), "audio", song_dir)
    lyrics = require_unique(
        collect_candidates(song_dir, LYRIC_EXTENSIONS, exclude_song_vibes=True),
        "lyrics",
        song_dir,
    )
    audio = ensure_canonical_input(audio, song_dir / "inputs" / "audio")
    lyrics = ensure_canonical_input(lyrics, song_dir / "inputs" / "lyrics")

    config = dict(template)
    config["id"] = song_dir.name
    config["title"] = caps_version(song_dir.name)
    config["song_vibes"] = collect_song_vibes(song_dir, lyrics)
    config["audio"] = song_relative(audio, song_dir)
    config["lyrics"] = song_relative(lyrics, song_dir)
    config["backgrounds"] = []
    config["output"] = dict(template.get("output", {}))
    config["output"]["filename"] = f"{song_dir.name}.mp4"
    write_json(config_path, config)
    return config


def config_path(song_dir: Path, config: dict, key: str) -> Path:
    value = config.get(key)
    if not value:
        raise SystemExit(f"Missing config field: {key}")
    return song_dir / value


def ffprobe_duration(audio_path: Path) -> float:
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=nw=1:nk=1",
            str(audio_path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return float(result.stdout.strip())


def parse_lyric_lines(lyrics_path: Path) -> list[str]:
    lines: list[str] = []
    for raw_line in lyrics_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("[") and line.endswith("]"):
            continue
        lines.append(line)
    if not lines:
        raise SystemExit(f"No renderable lyric lines found in {lyrics_path}.")
    return lines


def derive_clean_lyrics(song_dir: Path, config: dict) -> dict:
    lyrics_path = config_path(song_dir, config, "lyrics")
    raw_text = lyrics_path.read_text(encoding="utf-8")
    lines: list[str] = []
    tags: list[dict] = []

    for raw_line in raw_text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("[") and line.endswith("]"):
            tags.append({"text": line[1:-1].strip()})
            continue
        lines.append(line)

    if not lines:
        raise SystemExit(f"No renderable lyric lines found in {lyrics_path}.")

    derived_dir = song_dir / "timing" / "derived"
    derived_dir.mkdir(parents=True, exist_ok=True)
    text_path = derived_dir / "lyrics_clean.txt"
    json_path = derived_dir / "lyrics_clean.json"

    text_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    artifact = {
        "song_id": config["id"],
        "source": song_relative(lyrics_path, song_dir),
        "machine_owned": True,
        "notes": "Generated from raw lyrics by removing bracketed direction tags.",
        "tags": tags,
        "lines": [{"id": f"line_{index + 1:03d}", "text": text} for index, text in enumerate(lines)],
    }
    write_json(json_path, artifact)
    return artifact


def word_count(value: str) -> int:
    return len(re.findall(r"[A-Za-z0-9']+", value))


def normalize_match_text(value: str) -> str:
    return " ".join(re.findall(r"[a-z0-9']+", value.lower()))


def normalize_match_words(value: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", value.lower())


def find_whisper_transcript(song_dir: Path) -> Path:
    whisper_dir = song_dir / "timing" / "raw" / "whisper"
    candidates = [
        path
        for path in whisper_dir.glob("*.json")
        if path.name != "whisperx_run.json" and path.is_file()
    ]
    if not candidates:
        raise SystemExit(f"No Whisper transcript JSON found under {whisper_dir}.")
    return max(candidates, key=lambda path: path.stat().st_mtime)


def line_group_text(lines: list[dict]) -> str:
    return " ".join(line["text"] for line in lines)


def score_line_group_for_whisper(line_group: list[dict], whisper_segment: dict) -> tuple[float, float]:
    whisper_text = whisper_segment.get("text", "")
    group_text = line_group_text(line_group)
    normalized_group = normalize_match_text(group_text)
    normalized_whisper = normalize_match_text(whisper_text)
    similarity = (
        difflib.SequenceMatcher(None, normalized_group, normalized_whisper).ratio()
        if normalized_group and normalized_whisper
        else 0.0
    )
    group_words = max(1, word_count(group_text))
    whisper_words = max(1, word_count(whisper_text))
    word_penalty = abs(group_words - whisper_words) / max(group_words, whisper_words)
    cost = (1.0 - similarity) * 0.8 + word_penalty * 0.2
    return cost, similarity


def best_ordered_line_match(
    line_text: str,
    whisper_words: list[str],
    cursor: int,
) -> tuple[int, int, float] | None:
    line_words = normalize_match_words(line_text)
    if not line_words or cursor >= len(whisper_words):
        return None

    target = " ".join(line_words)
    min_size = max(1, len(line_words) - 2)
    max_size = min(len(whisper_words) - cursor, len(line_words) + 3)
    if max_size < min_size:
        return None

    best: tuple[int, int, float] | None = None
    for start in range(cursor, len(whisper_words)):
        for size in range(min_size, max_size + 1):
            end = start + size
            if end > len(whisper_words):
                continue
            candidate = " ".join(whisper_words[start:end])
            score = difflib.SequenceMatcher(None, target, candidate).ratio()
            if best is None or score > best[2]:
                best = (start, end, score)
    return best


def matched_line_indices_in_whisper(group_lines: list[dict], whisper_text: str) -> list[int]:
    whisper_words = normalize_match_words(whisper_text)
    cursor = 0
    matched: list[int] = []

    for index, line in enumerate(group_lines):
        match = best_ordered_line_match(line["text"], whisper_words, cursor)
        line_word_count = len(normalize_match_words(line["text"]))
        threshold = 0.86 if line_word_count <= 3 else 0.72
        if match is None or match[2] < threshold:
            continue
        matched.append(index)
        cursor = match[1]

    return matched


def suffix_gap_start_index(group_lines: list[dict], whisper_text: str) -> int | None:
    matched = matched_line_indices_in_whisper(group_lines, whisper_text)
    if not matched:
        return None
    suffix_start = max(matched) + 1
    return suffix_start if suffix_start < len(group_lines) else None


def partition_lines_for_whisper(lines: list[dict], whisper_segments: list[dict]) -> list[tuple[int, int]]:
    line_count = len(lines)
    segment_count = len(whisper_segments)
    if line_count < segment_count:
        # Rare case: keep the partition valid by assigning one lyric line to
        # the earliest segments and allowing the remaining segments to stay empty.
        return [(index, min(index + 1, line_count)) for index in range(segment_count)]

    infinity = float("inf")
    costs = [[infinity for _ in range(line_count + 1)] for _ in range(segment_count + 1)]
    previous: list[list[int | None]] = [[None for _ in range(line_count + 1)] for _ in range(segment_count + 1)]
    costs[0][0] = 0.0

    for segment_index, whisper_segment in enumerate(whisper_segments):
        remaining_segments = segment_count - segment_index - 1
        for used_lines in range(line_count + 1):
            current_cost = costs[segment_index][used_lines]
            if current_cost == infinity:
                continue
            max_take = line_count - used_lines - remaining_segments
            for take in range(1, max_take + 1):
                end = used_lines + take
                group_cost, _similarity = score_line_group_for_whisper(lines[used_lines:end], whisper_segment)
                next_cost = current_cost + group_cost
                if next_cost < costs[segment_index + 1][end]:
                    costs[segment_index + 1][end] = next_cost
                    previous[segment_index + 1][end] = used_lines

    if previous[segment_count][line_count] is None:
        raise SystemExit("Could not partition lyric lines across Whisper segments.")

    partitions: list[tuple[int, int]] = []
    cursor = line_count
    for segment_index in range(segment_count, 0, -1):
        start = previous[segment_index][cursor]
        if start is None:
            raise SystemExit("Could not reconstruct Whisper lyric partition.")
        partitions.append((start, cursor))
        cursor = start
    return list(reversed(partitions))


def allocate_lines_to_whisper_segments(lines: list[dict], whisper_segments: list[dict]) -> list[dict]:
    groups: list[dict] = []
    partitions = partition_lines_for_whisper(lines, whisper_segments)

    for segment_index, whisper_segment in enumerate(whisper_segments):
        start, end = partitions[segment_index]
        group = lines[start:end]
        _cost, similarity = score_line_group_for_whisper(group, whisper_segment) if group else (1.0, 0.0)

        groups.append(
            {
                "whisper_segment_index": segment_index,
                "whisper_text": whisper_segment.get("text", "").strip(),
                "start_ms": int(round(float(whisper_segment["start"]) * 1000)),
                "end_ms": int(round(float(whisper_segment["end"]) * 1000)),
                "match_score": round(similarity, 3),
                "lines": group,
            }
        )

    return groups


def weighted_timing_segments(
    group_lines: list[dict],
    start_ms: int,
    end_ms: int,
    *,
    source_whisper_segment: int,
    allocation_note: str | None = None,
) -> list[dict]:
    available_ms = max(1, end_ms - start_ms)
    weights = [max(1, word_count(line["text"])) for line in group_lines]
    total_weight = sum(weights)
    cursor = start_ms
    output_segments: list[dict] = []

    for index, line in enumerate(group_lines):
        if index == len(group_lines) - 1:
            line_end = end_ms
        else:
            line_end = cursor + int(round(available_ms * (weights[index] / total_weight)))

        segment = {
            "id": line["id"],
            "start_ms": cursor,
            "end_ms": max(cursor + 250, line_end - 80),
            "text": line["text"],
            "source_whisper_segment": source_whisper_segment,
        }
        if allocation_note:
            segment["allocation_note"] = allocation_note
        output_segments.append(segment)
        cursor = line_end

    return output_segments


def build_whisper_timing(song_dir: Path, config: dict) -> dict:
    lyrics_artifact = derive_clean_lyrics(song_dir, config)
    transcript_path = find_whisper_transcript(song_dir)
    transcript = load_json(transcript_path)
    whisper_segments = transcript.get("segments", [])
    if not whisper_segments:
        raise SystemExit(f"No segments found in Whisper transcript: {transcript_path}")

    groups = allocate_lines_to_whisper_segments(lyrics_artifact["lines"], whisper_segments)
    derived_mapping_path = song_dir / "timing" / "derived" / "whisper_line_mapping.json"

    output_segments: list[dict] = []
    for group_index, group in enumerate(groups):
        group_lines = group["lines"]
        if not group_lines:
            continue
        start_ms = group["start_ms"]
        end_ms = group["end_ms"]
        next_start_ms = groups[group_index + 1]["start_ms"] if group_index + 1 < len(groups) else None
        suffix_start = suffix_gap_start_index(group_lines, group["whisper_text"])
        gap_ms = (next_start_ms - end_ms) if next_start_ms is not None else 0

        if suffix_start and gap_ms >= 1200:
            prefix_lines = group_lines[:suffix_start]
            suffix_lines = group_lines[suffix_start:]
            group["allocation"] = {
                "strategy": "suffix_gap_allocation",
                "suffix_line_ids": [line["id"] for line in suffix_lines],
                "gap_start_ms": end_ms,
                "gap_end_ms": next_start_ms,
            }
            output_segments.extend(
                weighted_timing_segments(
                    prefix_lines,
                    start_ms,
                    end_ms,
                    source_whisper_segment=group["whisper_segment_index"],
                )
            )
            output_segments.extend(
                weighted_timing_segments(
                    suffix_lines,
                    end_ms,
                    next_start_ms,
                    source_whisper_segment=group["whisper_segment_index"],
                    allocation_note="allocated_to_gap_after_whisper_segment",
                )
            )
        else:
            output_segments.extend(
                weighted_timing_segments(
                    group_lines,
                    start_ms,
                    end_ms,
                    source_whisper_segment=group["whisper_segment_index"],
                )
            )

    write_json(
        derived_mapping_path,
        {
            "song_id": config["id"],
            "source_transcript": song_relative(transcript_path, song_dir),
            "source_lyrics": "timing/derived/lyrics_clean.json",
            "strategy": "sequential_similarity_partition_with_suffix_gap_allocation",
            "groups": groups,
        },
    )

    return {
        "song_id": config["id"],
        "source": "authoritative_lyrics_mapped_to_whisper_segments",
        "lyrics_source": "timing/derived/lyrics_clean.json",
        "whisper_source": song_relative(transcript_path, song_dir),
        "mapping_source": song_relative(derived_mapping_path, song_dir),
        "segments": output_segments,
    }


def build_even_timing(song_dir: Path, config: dict) -> dict:
    audio_path = config_path(song_dir, config, "audio")
    duration = ffprobe_duration(audio_path)
    lyrics_artifact = derive_clean_lyrics(song_dir, config)
    lines = [line["text"] for line in lyrics_artifact["lines"]]

    intro = min(3.0, max(0.0, duration * 0.03))
    outro = min(3.0, max(0.0, duration * 0.03))
    available = max(1.0, duration - intro - outro)
    step = available / len(lines)

    segments = []
    for index, text in enumerate(lines):
        start = intro + index * step
        end = intro + (index + 1) * step
        segments.append(
            {
                "id": f"line_{index + 1:03d}",
                "start_ms": int(round(start * 1000)),
                "end_ms": int(round(min(end - 0.08, duration) * 1000)),
                "text": text,
            }
        )

    return {
        "song_id": config["id"],
        "source": "evenly_spaced_from_derived_clean_lyrics",
        "audio_duration_ms": int(round(duration * 1000)),
        "lyrics_source": "timing/derived/lyrics_clean.json",
        "segments": segments,
    }


def ass_time(ms: int) -> str:
    total_centiseconds = max(0, int(round(ms / 10)))
    cs = total_centiseconds % 100
    total_seconds = total_centiseconds // 100
    seconds = total_seconds % 60
    minutes = (total_seconds // 60) % 60
    hours = total_seconds // 3600
    return f"{hours}:{minutes:02d}:{seconds:02d}.{cs:02d}"


def escape_ass_text(value: str) -> str:
    return value.replace("\\", "\\\\").replace("{", "\\{").replace("}", "\\}")


def split_balanced_lines(value: str, max_lines: int = 2) -> list[str]:
    words = value.split()
    if max_lines != 2 or len(words) < 3:
        return [value]

    best_split = 1
    best_score = float("inf")
    for split_index in range(1, len(words)):
        left = " ".join(words[:split_index])
        right = " ".join(words[split_index:])
        score = abs(len(left) - len(right)) + max(len(left), len(right)) * 0.1
        if score < best_score:
            best_score = score
            best_split = split_index

    return [" ".join(words[:best_split]), " ".join(words[best_split:])]


def wrap_lyric_for_ass(value: str, wrap_chars: int, font_size: int, available_width: int) -> str:
    wrapped = textwrap.wrap(
        value,
        width=wrap_chars,
        break_long_words=False,
        break_on_hyphens=False,
    )
    if not wrapped:
        wrapped = [value]
    if len(wrapped) > 2:
        wrapped = split_balanced_lines(value)

    longest = max(len(line) for line in wrapped)
    local_font_size = font_size
    if longest:
        estimated_width = longest * font_size * 0.52
        if estimated_width > available_width:
            local_font_size = max(34, math.floor(available_width / (longest * 0.52)))

    text = r"\N".join(escape_ass_text(line) for line in wrapped)
    if local_font_size < font_size:
        text = r"{\fs" + str(local_font_size) + "}" + text
    return text


def build_ass(
    timing: dict,
    target_name: str = "horizontal",
    layout: str = "standard",
    config: dict | None = None,
) -> str:
    if layout not in LAYOUTS:
        raise SystemExit(f"Unknown lyric layout '{layout}'. Expected one of: {available_layouts()}.")

    subtitle_options = config.get("subtitle", {}) if isinstance(config, dict) else {}
    if not isinstance(subtitle_options, dict):
        subtitle_options = {}
    font_name = str(
        subtitle_options.get("font")
        or subtitle_options.get("font_family")
        or "Georgia"
    ).replace(",", " ")
    primary_colour = str(
        subtitle_options.get("primary_colour")
        or subtitle_options.get("primary_color")
        or "&H00F7F1E8"
    )
    secondary_colour = str(
        subtitle_options.get("secondary_colour")
        or subtitle_options.get("secondary_color")
        or "&H000000FF"
    )
    outline_colour = str(
        subtitle_options.get("outline_colour")
        or subtitle_options.get("outline_color")
        or "&H0017100B"
    )
    back_colour = str(
        subtitle_options.get("back_colour")
        or subtitle_options.get("back_color")
        or "&HAA000000"
    )
    bold = -1 if subtitle_options.get("bold", True) else 0

    target = render_target(target_name)
    width = int(target["width"])
    height = int(target["height"])
    margin_h = max(60, math.floor(width * (0.08 if layout in {"fullscreen", "soft_scroll"} else 0.10)))
    margin_v = max(80, math.floor(height * (0.10 if layout == "soft_scroll" else float(target["bottom_margin_pct"]))))
    available_width = width - margin_h * 2
    if layout == "fullscreen":
        font_divisor = 9
    elif layout == "soft_scroll":
        font_divisor = 13
    else:
        font_divisor = float(target["font_divisor"])
    font_size = max(42, math.floor(min(width, height) / font_divisor))
    wrap_chars = max(18, math.floor(available_width / (font_size * 0.52)))
    alignment = 5 if layout in {"fullscreen", "soft_scroll"} else 2
    outline = 5 if layout in {"fullscreen", "soft_scroll"} else 4
    shadow = 3 if layout in {"fullscreen", "soft_scroll"} else 2
    lines = [
        "[Script Info]",
        "ScriptType: v4.00+",
        f"PlayResX: {width}",
        f"PlayResY: {height}",
        "ScaledBorderAndShadow: yes",
        "WrapStyle: 2",
        "",
        "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, "
        "OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, "
        "ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, "
        "Alignment, MarginL, MarginR, MarginV, Encoding",
        f"Style: Default,{font_name},"
        f"{font_size},{primary_colour},{secondary_colour},{outline_colour},{back_colour},"
        f"{bold},0,0,0,100,100,0,0,1,{outline},{shadow},{alignment},{margin_h},{margin_h},{margin_v},1",
        "",
        "[Events]",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
    ]

    for segment in timing["segments"]:
        text = wrap_lyric_for_ass(segment["text"], wrap_chars, font_size, available_width)
        if layout == "soft_scroll":
            event_start = max(0, int(segment["start_ms"]) - 350)
            event_end = int(segment["end_ms"]) + 450
            start_y = math.floor(height * 0.68)
            end_y = math.floor(height * 0.40)
            text = (
                r"{\an5\move("
                f"{width // 2},{start_y},{width // 2},{end_y})"
                r"\fad(280,420)}"
                + text
            )
        lines.append(
            "Dialogue: 0,"
            f"{ass_time(event_start if layout == 'soft_scroll' else segment['start_ms'])},"
            f"{ass_time(event_end if layout == 'soft_scroll' else segment['end_ms'])},"
            f"Default,{segment['id']},0,0,0,,{text}"
        )
    return "\n".join(lines) + "\n"


def write_reviewed_timing(song_dir: Path, timing: dict) -> Path:
    path = song_dir / "timing" / "reviewed" / "timing.json"
    write_json(path, timing)
    return path


def write_ass_file(
    song_dir: Path,
    timing: dict,
    config: dict,
    target_name: str = "horizontal",
    layout: str = "standard",
) -> Path:
    target = render_target(target_name)
    suffix = target["suffix"]
    layout_suffix = "" if layout == "standard" else f".{layout}"
    ass_path = song_dir / "subtitles" / f"lyrics.{suffix}{layout_suffix}.ass"
    ass_path.parent.mkdir(parents=True, exist_ok=True)
    content = build_ass(timing, target_name, layout, config)
    ass_path.write_text(content, encoding="utf-8")
    if target_name == "horizontal" and layout == "standard":
        (song_dir / "subtitles" / "lyrics.ass").write_text(content, encoding="utf-8")
    return ass_path


def target_output_filename(config: dict, target_name: str) -> str:
    target = render_target(target_name)
    output = config.get("output", {})
    configured_filename = output.get("filename", f"{config['id']}.mp4")
    stem = Path(configured_filename).stem
    return f"{stem}.{target['suffix']}.mp4"


def target_variant_output_filename(config: dict, target_name: str, variant: str | None = None) -> str:
    target = render_target(target_name)
    output = config.get("output", {})
    configured_filename = output.get("filename", f"{config['id']}.mp4")
    stem = Path(configured_filename).stem
    variant_suffix = f".{variant}" if variant else ""
    return f"{stem}.{target['suffix']}{variant_suffix}.mp4"


def find_background_image(song_dir: Path, config: dict) -> Path | None:
    for background in config.get("backgrounds", []):
        path = song_dir / background
        if path.exists() and path.suffix.lower() in IMAGE_EXTENSIONS:
            return path
    return None


def render_basic_video(
    song_dir: Path,
    config: dict,
    ass_path: Path,
    target_name: str = "horizontal",
    layout: str = "standard",
) -> Path:
    target = render_target(target_name)
    output = config.get("output", {})
    width = int(target["width"])
    height = int(target["height"])
    fps = int(output.get("fps", 30))
    filename = target_variant_output_filename(
        config,
        target_name,
        None if layout == "standard" else layout,
    )
    export_dir = song_dir / output.get("directory", "exports/")
    export_dir.mkdir(parents=True, exist_ok=True)

    output_path = export_dir / filename
    audio_path = config_path(song_dir, config, "audio")
    ass_relative = song_relative(ass_path, song_dir)
    audio_relative = song_relative(audio_path, song_dir)
    output_relative = song_relative(output_path, song_dir)
    background_path = find_background_image(song_dir, config)

    if background_path:
        background_relative = song_relative(background_path, song_dir)
        video_input = [
            "-loop",
            "1",
            "-framerate",
            str(fps),
            "-i",
            background_relative,
        ]
        video_filter = (
            f"scale={width}:{height}:force_original_aspect_ratio=increase,"
            f"crop={width}:{height},subtitles={ass_relative}"
        )
        background_metadata = background_relative
    else:
        video_input = [
            "-f",
            "lavfi",
            "-i",
            f"color=c=0x17110d:s={width}x{height}:r={fps}",
        ]
        video_filter = f"subtitles={ass_relative}"
        background_metadata = "generated:solid:0x17110d"

    command = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "warning",
        "-y",
        *video_input,
        "-i",
        audio_relative,
        "-vf",
        video_filter,
        "-shortest",
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-crf",
        "22",
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "aac",
        "-b:a",
        "192k",
        output_relative,
    ]
    subprocess.run(command, cwd=song_dir, check=True)

    metadata_path = song_dir / "renders" / f"{Path(filename).stem}.render.json"
    write_json(
        metadata_path,
        {
            "rendered_at": datetime.now(timezone.utc).isoformat(),
            "song_id": config["id"],
            "target": {
                "name": target_name,
                "ratio": target["ratio"],
                "width": width,
                "height": height,
                "suffix": target["suffix"],
            },
            "layout": layout,
            "preset": config.get("_render_preset"),
            "preset_path": config.get("_render_preset_path"),
            "subtitle": config.get("subtitle", {}),
            "audio": audio_relative,
            "background": background_metadata,
            "subtitles": ass_relative,
            "output": output_relative,
            "ffmpeg_command": command,
        },
    )
    return output_path


def validate_timing(timing: dict, timing_path: Path) -> list[str]:
    errors: list[str] = []
    segments = timing.get("segments")
    if not isinstance(segments, list) or not segments:
        return [f"{timing_path}: expected non-empty 'segments' list"]

    previous_start = -1
    for index, segment in enumerate(segments, start=1):
        label = f"{timing_path}: segment {index}"
        if not isinstance(segment, dict):
            errors.append(f"{label} must be an object")
            continue
        for key in ("id", "start_ms", "end_ms", "text"):
            if key not in segment:
                errors.append(f"{label} missing '{key}'")
        if not isinstance(segment.get("text"), str) or not segment.get("text", "").strip():
            errors.append(f"{label} has empty text")
        start_ms = segment.get("start_ms")
        end_ms = segment.get("end_ms")
        if not isinstance(start_ms, int) or not isinstance(end_ms, int):
            errors.append(f"{label} start_ms/end_ms must be integers")
            continue
        if start_ms < 0:
            errors.append(f"{label} start_ms must be non-negative")
        if end_ms <= start_ms:
            errors.append(f"{label} end_ms must be greater than start_ms")
        if start_ms < previous_start:
            errors.append(f"{label} starts before a previous segment")
        previous_start = start_ms
    return errors


def timing_gap_warnings(timing: dict, timing_path: Path, threshold_ms: int = 5000) -> list[str]:
    warnings: list[str] = []
    segments = timing.get("segments")
    if not isinstance(segments, list):
        return warnings

    for previous, current in zip(segments, segments[1:]):
        previous_end = previous.get("end_ms")
        current_start = current.get("start_ms")
        if not isinstance(previous_end, int) or not isinstance(current_start, int):
            continue
        gap_ms = current_start - previous_end
        if gap_ms > threshold_ms:
            warnings.append(
                f"{timing_path}: {gap_ms / 1000:.1f}s gap after "
                f"{previous.get('id', '(unknown)')} before {current.get('id', '(unknown)')}"
            )
    return warnings


def text_health_warnings(path: Path, label: str) -> list[str]:
    warnings: list[str] = []
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        return [f"{label} is not valid UTF-8: {path}: {exc}"]

    for marker, description in SUSPICIOUS_TEXT_MARKERS.items():
        if marker in text:
            warnings.append(f"{label} contains {description}: {path}")
    return warnings


def validate_song_package(
    song_dir: Path,
    config: dict,
    *,
    require_timing: bool = False,
    check_tools: bool = False,
) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []

    if not song_dir.exists():
        errors.append(f"Song directory does not exist: {song_dir}")
    else:
        for directory in missing_song_directories(song_dir):
            warnings.append(f"Recommended song directory is missing: {directory}")

    for key in ("id", "title", "audio", "lyrics"):
        if not config.get(key):
            errors.append(f"Missing config field: {key}")

    if not config.get("song_vibes"):
        warnings.append("song_vibes is empty; generated visual prompts may need manual context.")

    for key, extensions in (("audio", AUDIO_EXTENSIONS), ("lyrics", LYRIC_EXTENSIONS)):
        value = config.get(key)
        if not value:
            continue
        path = song_dir / value
        if not path.exists():
            errors.append(f"Configured {key} file does not exist: {path}")
        elif path.suffix.lower() not in extensions:
            errors.append(f"Configured {key} has unsupported extension: {path}")
        elif key == "lyrics":
            warnings.extend(text_health_warnings(path, "Configured lyrics"))

    try:
        normalize_render_targets(config.get("output", {}).get("targets"))
    except SystemExit as exc:
        errors.append(str(exc))

    output_dir = config.get("output", {}).get("directory", "exports/")
    if not isinstance(output_dir, str) or not output_dir.strip():
        errors.append("output.directory must be a non-empty string")

    fps = config.get("output", {}).get("fps", 30)
    if not isinstance(fps, int) or fps <= 0:
        errors.append("output.fps must be a positive integer")

    for background in config.get("backgrounds", []):
        path = song_dir / background
        if not path.exists():
            warnings.append(f"Configured background does not exist yet: {path}")

    if config.get("background_mode") == "video":
        bg_video = config.get("background_video")
        if not bg_video:
            errors.append("background_mode is 'video' but background_video is not set")
        else:
            bg_path = song_dir / bg_video
            if not bg_path.exists():
                errors.append(f"Configured background_video does not exist: {bg_path}")

    reviewed = config.get("timing", {}).get("reviewed", "timing/reviewed/timing.json")
    timing_path = song_dir / reviewed
    if timing_path.exists():
        try:
            timing = load_json(timing_path)
        except json.JSONDecodeError as exc:
            errors.append(f"Reviewed timing is invalid JSON: {timing_path}: {exc}")
        else:
            errors.extend(validate_timing(timing, timing_path))
            warnings.extend(timing_gap_warnings(timing, timing_path))
    elif require_timing:
        errors.append(f"Reviewed timing file does not exist: {timing_path}")

    if check_tools:
        for tool in ("ffmpeg", "ffprobe"):
            if shutil.which(tool) is None:
                errors.append(f"Required tool is not on PATH: {tool}")

    return errors, warnings


def render_video_background(
    song_dir: Path,
    config: dict,
    ass_path: Path,
    background_video_path: Path,
    target_name: str = "horizontal",
    layout: str = "standard",
    variant: str | None = "vibe",
) -> Path:
    target = render_target(target_name)
    output = config.get("output", {})
    width = int(target["width"])
    height = int(target["height"])
    fps = int(output.get("fps", 30))
    configured_filename = output.get("filename", f"{config['id']}.mp4")
    stem = Path(configured_filename).stem
    variant_suffix = f".{variant}" if variant else ""
    filename = f"{stem}.{target['suffix']}{variant_suffix}.mp4"
    export_dir = song_dir / output.get("directory", "exports/")
    export_dir.mkdir(parents=True, exist_ok=True)

    output_path = export_dir / filename
    audio_path = config_path(song_dir, config, "audio")
    background_video_path = background_video_path.resolve()
    ass_relative = song_relative(ass_path, song_dir)
    audio_relative = song_relative(audio_path, song_dir)
    background_input = ffmpeg_input_path(background_video_path, song_dir)
    output_relative = song_relative(output_path, song_dir)

    video_filter = (
        f"scale={width}:{height}:force_original_aspect_ratio=increase,"
        f"crop={width}:{height},subtitles={ass_relative}"
    )
    command = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "warning",
        "-y",
        "-stream_loop",
        "-1",
        "-i",
        background_input,
        "-i",
        audio_relative,
        "-vf",
        video_filter,
        "-shortest",
        "-r",
        str(fps),
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-crf",
        "22",
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "aac",
        "-b:a",
        "192k",
        output_relative,
    ]
    subprocess.run(command, cwd=song_dir, check=True)

    metadata_path = song_dir / "renders" / f"{Path(filename).stem}.render.json"
    write_json(
        metadata_path,
        {
            "rendered_at": datetime.now(timezone.utc).isoformat(),
            "song_id": config["id"],
            "target": {
                "name": target_name,
                "ratio": target["ratio"],
                "width": width,
                "height": height,
                "suffix": target["suffix"],
            },
            "variant": variant,
            "layout": layout,
            "preset": config.get("_render_preset"),
            "preset_path": config.get("_render_preset_path"),
            "subtitle": config.get("subtitle", {}),
            "audio": audio_relative,
            "background_video": background_input,
            "subtitles": ass_relative,
            "output": output_relative,
            "ffmpeg_command": command,
        },
    )
    return output_path
