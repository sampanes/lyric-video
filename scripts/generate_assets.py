"""Generate or fetch background and overlay assets."""

from __future__ import annotations

import argparse


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--todo",
        action="store_true",
        help="Print the planned responsibility for this future tool.",
    )
    args = parser.parse_args()
    print(
        "Asset generation is not implemented yet. Planned role: call optional "
        "generators such as ComfyUI adapters and write render-ready assets plus "
        "metadata under songs/<song>/assets/. Future prompts should use "
        "song_vibes plus inputs/song_style_prompt.txt when present."
    )
    return 0 if args.todo else 2


if __name__ == "__main__":
    raise SystemExit(main())
