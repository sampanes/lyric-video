"""Create a forward-then-reverse bounce loop from a subtle background clip."""

from __future__ import annotations

import argparse
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from pipeline_common import write_json


def default_output_path(source_path: Path) -> Path:
    return source_path.with_name(f"{source_path.stem}.bounce{source_path.suffix}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", help="Source video clip.")
    parser.add_argument(
        "--output",
        help="Output bounce-loop path. Defaults to source stem plus .bounce.mp4.",
    )
    parser.add_argument("--fps", type=int, default=30, help="Output frame rate.")
    args = parser.parse_args()

    source_path = Path(args.source)
    if not source_path.exists():
        raise SystemExit(f"Source clip not found: {source_path}")
    output_path = Path(args.output) if args.output else default_output_path(source_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    filter_complex = (
        "[0:v]split=2[fwd][rev];"
        "[fwd]setpts=PTS-STARTPTS[fwdset];"
        "[rev]reverse,trim=start_frame=1,setpts=PTS-STARTPTS[revtrim];"
        f"[fwdset][revtrim]concat=n=2:v=1:a=0,fps={args.fps},format=yuv420p[v]"
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
            "postprocess": "forward_then_reverse_bounce_loop",
            "notes": [
                "Reverse half trims the first reversed frame to avoid duplicating the forward/reverse seam frame.",
                "Use for subtle ambient motion where perfect optical looping is not required.",
            ],
            "ffmpeg_command": command,
        },
    )

    print(f"Wrote {output_path}")
    print(f"Wrote {metadata_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
