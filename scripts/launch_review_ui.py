"""Launch the local timing review UI."""

from __future__ import annotations

import argparse
import sys
import webbrowser
from pathlib import Path
from urllib.parse import urlencode


REPO_ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Host interface for the local UI server.",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8765,
        help="Port for the local UI server.",
    )
    parser.add_argument(
        "--song",
        default=None,
        help="Optional song slug/name to load on startup.",
    )
    parser.add_argument(
        "--no-open",
        action="store_true",
        help="Start the server without opening a browser tab.",
    )
    args = parser.parse_args()

    sys.path.insert(0, str(REPO_ROOT / "tools" / "review_ui"))
    from server import serve  # noqa: PLC0415

    query = f"?{urlencode({'song': args.song})}" if args.song else ""
    url = f"http://{args.host}:{args.port}/{query}"
    print(f"Timing review UI: {url}")
    print("Press Ctrl+C to stop.")
    if not args.no_open:
        webbrowser.open(url)

    serve(host=args.host, port=args.port, repo_root=REPO_ROOT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
