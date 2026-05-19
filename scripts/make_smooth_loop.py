"""Build a forward-only seamless-loop clip by crossfading tail into head.

Use this instead of `make_bounce_loop.py` when the source has directional
motion (rising smoke, floating embers, drifting mist, falling water). Reverse
playback flips that motion and reads as broken; this script keeps playback
forward-only and dissolves the tail back into the head so the loop seam is
hidden inside a short crossfade.

Optional `--trim-start` drops the first N frames, which is useful for Wan
i2v output where the denoiser settles into motion across the first 1-3
frames and produces a brightness pop that reads as flash photography.

Future direction: replace the crossfade with optical-flow / AI tween frames
(RIFE, FILM) for source material where pixel-level dissolve still reveals a
visible blur during the overlap.
"""

from __future__ import annotations

import argparse
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from pipeline_common import write_json


def probe_stream(path: Path) -> tuple[float, float, int]:
    raw = subprocess.check_output(
        [
            "ffprobe",
            "-v",
            "error",
            "-select_streams",
            "v:0",
            "-show_entries",
            "stream=duration,r_frame_rate,nb_frames",
            "-of",
            "json",
            str(path),
        ]
    )
    info = json.loads(raw)["streams"][0]
    duration = float(info["duration"])
    num, den = info["r_frame_rate"].split("/")
    fps = float(num) / float(den)
    frames = int(info.get("nb_frames") or round(duration * fps))
    return duration, fps, frames


def default_output_path(source_path: Path) -> Path:
    return source_path.with_name(f"{source_path.stem}.smooth{source_path.suffix}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", help="Source video clip.")
    parser.add_argument(
        "--output",
        help="Output path. Defaults to <source-stem>.smooth.mp4 next to the source.",
    )
    parser.add_argument(
        "--overlap",
        type=float,
        default=1.0,
        help="Crossfade duration in seconds. Default 1.0.",
    )
    parser.add_argument(
        "--trim-start",
        type=int,
        default=0,
        help="Drop N frames from the start of the clip before looping. Useful for Wan settle/flash frames.",
    )
    parser.add_argument(
        "--fps",
        type=int,
        default=30,
        help="Output frame rate. Default 30 to match the lyric-video pipeline.",
    )
    args = parser.parse_args()

    source_path = Path(args.source)
    if not source_path.exists():
        raise SystemExit(f"Source clip not found: {source_path}")
    output_path = Path(args.output) if args.output else default_output_path(source_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    duration, source_fps, frames = probe_stream(source_path)
    trim_start_s = args.trim_start / source_fps
    effective_duration = duration - trim_start_s
    if effective_duration <= args.overlap * 2:
        raise SystemExit(
            f"Clip too short for overlap={args.overlap}s after trim={trim_start_s:.3f}s. "
            f"Effective duration is {effective_duration:.3f}s; need at least {args.overlap * 2:.3f}s."
        )

    overlap = args.overlap
    head_duration = effective_duration - overlap

    filter_complex = (
        f"[0:v]split=3[s1][s2][s3];"
        f"[s1]trim=start={trim_start_s}:duration={head_duration},setpts=PTS-STARTPTS[head];"
        f"[s2]trim=start={trim_start_s + head_duration}:duration={overlap},setpts=PTS-STARTPTS[tail];"
        f"[s3]trim=start={trim_start_s}:duration={overlap},setpts=PTS-STARTPTS[loopstart];"
        f"[tail][loopstart]xfade=transition=fade:duration={overlap}:offset=0[xfaded];"
        f"[head][xfaded]concat=n=2:v=1:a=0,fps={args.fps},format=yuv420p[v]"
    )

    command = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "warning",
        "-y",
        "-i",
        str(source_path),
        "-filter_complex",
        filter_complex,
        "-map",
        "[v]",
        "-an",
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-crf",
        "20",
        "-movflags",
        "+faststart",
        str(output_path),
    ]
    subprocess.run(command, check=True)

    metadata_path = output_path.with_suffix(".json")
    write_json(
        metadata_path,
        {
            "created_at": datetime.now(timezone.utc).isoformat(),
            "source": str(source_path),
            "output": str(output_path),
            "postprocess": "tail_to_head_xfade_loop",
            "source_duration": duration,
            "source_fps": source_fps,
            "source_frames": frames,
            "trim_start_frames": args.trim_start,
            "trim_start_seconds": trim_start_s,
            "overlap_seconds": overlap,
            "output_duration": head_duration + overlap,
            "notes": [
                "Forward-only loop. Use for directional motion (smoke, embers, mist) where reverse playback would look wrong.",
                "The last `overlap` seconds are a crossfade from the source tail into the source head; the file loops cleanly when concatenated.",
            ],
            "ffmpeg_command": command,
        },
    )

    print(f"Wrote {output_path}")
    print(f"Wrote {metadata_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
