"""Capture or import raw lyric timing events."""

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
        "Timing capture is not implemented yet. Planned role: write raw human "
        "click or automation events under songs/<song>/timing/raw/ for later "
        "normalization into timing/reviewed/timing.json."
    )
    return 0 if args.todo else 2


if __name__ == "__main__":
    raise SystemExit(main())
