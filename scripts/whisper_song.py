"""Run WhisperX for a song and store raw transcript artifacts."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
from pathlib import Path

from pipeline_common import config_path, ensure_song_config, resolve_song_dir, song_relative, write_json


DEFAULT_WHISPERX_COMMAND = "whisperx"
LOCAL_CONFIG_PATH = Path(__file__).resolve().parents[1] / "LOCAL_CONFIG.json"


def _local_whisperx_exe() -> str | None:
    if not LOCAL_CONFIG_PATH.exists():
        return None
    try:
        data = json.loads(LOCAL_CONFIG_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    section = data.get("whisperx")
    if isinstance(section, dict):
        exe = section.get("exe")
        if isinstance(exe, str) and exe.strip():
            return exe.strip()
    return None


def resolve_whisperx_executable() -> str:
    configured = os.environ.get("WHISPERX_EXE") or _local_whisperx_exe()
    if configured:
        configured_path = Path(configured).expanduser()
        if configured_path.exists():
            return str(configured_path)
        configured_on_path = shutil.which(configured)
        if configured_on_path:
            return configured_on_path
        raise SystemExit(
            f"WhisperX executable not found at configured path: {configured}. "
            "Update WHISPERX_EXE or LOCAL_CONFIG.json's whisperx.exe."
        )

    whisperx = shutil.which(DEFAULT_WHISPERX_COMMAND)
    if whisperx:
        return whisperx

    raise SystemExit(
        "WhisperX executable not found. Set WHISPERX_EXE, add a "
        "\"whisperx\": {\"exe\": \"...\"} block to LOCAL_CONFIG.json, "
        "or put whisperx on PATH."
    )


def build_initial_prompt(song_dir: Path, config: dict) -> str:
    lyrics_path = config_path(song_dir, config, "lyrics")
    lines = []
    for raw_line in lyrics_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or (line.startswith("[") and line.endswith("]")):
            continue
        lines.append(line)
    return " ".join(lines)[:1200]


def run_whisperx(
    song_dir: Path,
    config: dict,
    *,
    model: str = "medium",
    device: str = "cpu",
    compute_type: str = "int8",
    align: bool = False,
    cache_only: bool = True,
) -> dict:
    audio_path = config_path(song_dir, config, "audio")
    output_dir = song_dir / "timing" / "raw" / "whisper"
    output_dir.mkdir(parents=True, exist_ok=True)

    whisperx = resolve_whisperx_executable()

    command = [
        whisperx,
        str(audio_path),
        "--model",
        model,
        "--model_cache_only",
        "True" if cache_only else "False",
        "--device",
        device,
        "--compute_type",
        compute_type,
        "--language",
        "en",
        "--output_dir",
        str(output_dir),
        "--output_format",
        "json",
        "--initial_prompt",
        build_initial_prompt(song_dir, config),
    ]
    if not align:
        command.append("--no_align")

    env = os.environ.copy()
    # WhisperX prints model-generated transcript text. Force UTF-8 so Windows
    # console/codepage settings do not crash on punctuation like prime marks.
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"
    subprocess.run(command, check=True, env=env)

    metadata = {
        "song_id": config["id"],
        "source_audio": song_relative(audio_path, song_dir),
        "output_dir": song_relative(output_dir, song_dir),
        "tool": "whisperx",
        "model": model,
        "device": device,
        "compute_type": compute_type,
        "alignment_enabled": align,
        "model_cache_only": cache_only,
        "command": command,
    }
    metadata_path = output_dir / "whisperx_run.json"
    write_json(metadata_path, metadata)

    return {
        "output_dir": output_dir,
        "metadata_path": metadata_path,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("song", help="Song slug, approximate name, or song folder.")
    parser.add_argument("--model", default="medium", help="WhisperX model name.")
    parser.add_argument("--device", default="cpu", help="WhisperX device, such as cpu or cuda.")
    parser.add_argument(
        "--compute-type",
        default="int8",
        help="WhisperX compute type. int8 is a conservative CPU default.",
    )
    parser.add_argument(
        "--align",
        action="store_true",
        help="Run WhisperX alignment. Default skips alignment to avoid extra model downloads.",
    )
    parser.add_argument(
        "--no-cache-only",
        action="store_true",
        help="Allow WhisperX to download missing models.",
    )
    args = parser.parse_args()

    song_dir = resolve_song_dir(args.song)
    config = ensure_song_config(song_dir)
    result = run_whisperx(
        song_dir,
        config,
        model=args.model,
        device=args.device,
        compute_type=args.compute_type,
        align=args.align,
        cache_only=not args.no_cache_only,
    )

    print(f"Wrote WhisperX output under {result['output_dir']}")
    print(f"Wrote {result['metadata_path']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
