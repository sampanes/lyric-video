"""Local HTTP server for the timing review UI."""

from __future__ import annotations

import json
import mimetypes
import shutil
import subprocess
import sys
from datetime import datetime
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse


REPO_ROOT = Path(__file__).resolve().parents[2]
STATIC_ROOT = Path(__file__).resolve().parent / "static"
SCRIPTS_ROOT = REPO_ROOT / "scripts"
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from inspect_song import build_song_inspection  # noqa: E402
from pipeline_common import (  # noqa: E402
    ensure_song_config,
    load_json,
    resolve_song_dir,
    song_relative,
    validate_timing,
    write_json,
)


DEFAULT_TIMING_PATH = "timing/reviewed/timing.json"


def json_bytes(data: object) -> bytes:
    return (json.dumps(data, indent=2) + "\n").encode("utf-8")


def safe_static_path(raw_path: str) -> Path | None:
    route = raw_path.lstrip("/") or "index.html"
    if route == "":
        route = "index.html"
    candidate = (STATIC_ROOT / route).resolve()
    try:
        candidate.relative_to(STATIC_ROOT.resolve())
    except ValueError:
        return None
    if candidate.is_dir():
        candidate = candidate / "index.html"
    return candidate


def list_song_names() -> list[str]:
    songs_root = REPO_ROOT / "songs"
    if not songs_root.exists():
        return []
    return sorted(
        path.name
        for path in songs_root.iterdir()
        if path.is_dir() and path.name != "template_song"
    )


def timing_path_for_song(song_dir: Path) -> Path:
    config_path = song_dir / "song.json"
    if config_path.exists():
        config = load_json(config_path)
        reviewed = config.get("timing", {}).get("reviewed", DEFAULT_TIMING_PATH)
    else:
        reviewed = DEFAULT_TIMING_PATH
    return song_dir / reviewed


def backup_file(path: Path) -> Path:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    backup_dir = path.parent / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    backup_path = backup_dir / f"{path.stem}.{stamp}{path.suffix}"
    shutil.copy2(path, backup_path)
    return backup_path


class ReviewUiHandler(BaseHTTPRequestHandler):
    server_version = "LyricReviewUI/0.1"

    def log_message(self, format: str, *args: object) -> None:
        print(f"[review-ui] {self.address_string()} - {format % args}")

    def send_json(self, data: object, status: int = HTTPStatus.OK) -> None:
        body = json_bytes(data)
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def send_error_json(self, message: str, status: int = HTTPStatus.BAD_REQUEST) -> None:
        self.send_json({"error": message}, status=status)

    def read_json_body(self) -> dict:
        length = int(self.headers.get("Content-Length", "0"))
        if length <= 0:
            return {}
        raw = self.rfile.read(length)
        return json.loads(raw.decode("utf-8"))

    def query(self) -> dict[str, list[str]]:
        return parse_qs(urlparse(self.path).query)

    def query_value(self, name: str, default: str | None = None) -> str | None:
        values = self.query().get(name)
        if not values:
            return default
        return values[0]

    def require_song_ref(self) -> str:
        song_ref = self.query_value("song") or self.query_value("ref")
        if not song_ref:
            raise ValueError("Missing song query parameter.")
        return unquote(song_ref)

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        try:
            if parsed.path == "/api/health":
                return self.send_json(
                    {
                        "ok": True,
                        "repo_root": str(REPO_ROOT),
                        "python": sys.executable,
                    }
                )
            if parsed.path == "/api/songs":
                return self.send_json({"songs": list_song_names()})
            if parsed.path == "/api/song":
                song_ref = self.require_song_ref()
                state = build_song_inspection(song_ref, check_tools=False)
                if state.get("exists") and state.get("config", {}).get("present"):
                    song_dir = resolve_song_dir(song_ref)
                    config = ensure_song_config(song_dir)
                    audio = song_dir / config["audio"]
                    timing_path = timing_path_for_song(song_dir)
                    state["review_ui"] = {
                        "audio_url": f"/api/song/audio?song={song_dir.name}",
                        "timing_url": f"/api/song/timing?song={song_dir.name}",
                        "audio_path": song_relative(audio, song_dir) if audio.exists() else config["audio"],
                        "timing_path": (
                            song_relative(timing_path, song_dir)
                            if timing_path.exists()
                            else str(timing_path.relative_to(song_dir)).replace("\\", "/")
                        ),
                    }
                return self.send_json(state)
            if parsed.path == "/api/song/timing":
                song_ref = self.require_song_ref()
                song_dir = resolve_song_dir(song_ref)
                timing_path = timing_path_for_song(song_dir)
                if not timing_path.exists():
                    return self.send_error_json(
                        f"Reviewed timing file does not exist: {timing_path}",
                        HTTPStatus.NOT_FOUND,
                    )
                timing = load_json(timing_path)
                return self.send_json(
                    {
                        "song": song_dir.name,
                        "path": song_relative(timing_path, song_dir),
                        "timing": timing,
                    }
                )
            if parsed.path == "/api/song/audio":
                song_ref = self.require_song_ref()
                return self.send_audio(song_ref)
            if parsed.path.startswith("/api/"):
                return self.send_error_json("Unknown API endpoint.", HTTPStatus.NOT_FOUND)
            return self.send_static(parsed.path)
        except Exception as exc:  # pragma: no cover - local UI safety net
            return self.send_error_json(str(exc), HTTPStatus.INTERNAL_SERVER_ERROR)

    def do_HEAD(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        try:
            if parsed.path == "/api/song/audio":
                song_ref = self.require_song_ref()
                return self.send_audio(song_ref, head_only=True)
            if parsed.path.startswith("/api/"):
                body = json_bytes({"ok": True})
                self.send_response(HTTPStatus.OK)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                return None
            return self.send_static(parsed.path, head_only=True)
        except Exception as exc:  # pragma: no cover - local UI safety net
            return self.send_error_json(str(exc), HTTPStatus.INTERNAL_SERVER_ERROR)

    def do_POST(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        try:
            if parsed.path == "/api/song/timing":
                return self.save_timing()
            if parsed.path == "/api/song/render-proof":
                return self.render_proof()
            return self.send_error_json("Unknown API endpoint.", HTTPStatus.NOT_FOUND)
        except Exception as exc:  # pragma: no cover - local UI safety net
            return self.send_error_json(str(exc), HTTPStatus.INTERNAL_SERVER_ERROR)

    def send_static(self, raw_path: str, *, head_only: bool = False) -> None:
        path = safe_static_path(raw_path)
        if path is None or not path.exists() or not path.is_file():
            self.send_error(HTTPStatus.NOT_FOUND)
            return

        body = path.read_bytes()
        content_type, _encoding = mimetypes.guess_type(path.name)
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type or "application/octet-stream")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        if not head_only:
            self.wfile.write(body)

    def send_audio(self, song_ref: str, *, head_only: bool = False) -> None:
        song_dir = resolve_song_dir(song_ref)
        config = ensure_song_config(song_dir)
        audio_path = (song_dir / config["audio"]).resolve()
        try:
            audio_path.relative_to(song_dir.resolve())
        except ValueError:
            raise ValueError(f"Configured audio path escapes song directory: {audio_path}")
        if not audio_path.exists():
            self.send_error_json(f"Audio file does not exist: {audio_path}", HTTPStatus.NOT_FOUND)
            return

        file_size = audio_path.stat().st_size
        range_header = self.headers.get("Range")
        content_type, _encoding = mimetypes.guess_type(audio_path.name)
        content_type = content_type or "application/octet-stream"

        start = 0
        end = file_size - 1
        status = HTTPStatus.OK
        if range_header and range_header.startswith("bytes="):
            status = HTTPStatus.PARTIAL_CONTENT
            raw_range = range_header.removeprefix("bytes=").split(",", 1)[0]
            raw_start, _, raw_end = raw_range.partition("-")
            if raw_start:
                start = int(raw_start)
            if raw_end:
                end = int(raw_end)
            end = min(end, file_size - 1)

        length = end - start + 1
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Content-Length", str(length))
        if status == HTTPStatus.PARTIAL_CONTENT:
            self.send_header("Content-Range", f"bytes {start}-{end}/{file_size}")
        self.end_headers()
        if head_only:
            return

        with audio_path.open("rb") as handle:
            handle.seek(start)
            remaining = length
            while remaining > 0:
                chunk = handle.read(min(64 * 1024, remaining))
                if not chunk:
                    break
                self.wfile.write(chunk)
                remaining -= len(chunk)

    def save_timing(self) -> None:
        song_ref = self.require_song_ref()
        body = self.read_json_body()
        timing = body.get("timing")
        if not isinstance(timing, dict):
            return self.send_error_json("Expected JSON body with a timing object.")

        song_dir = resolve_song_dir(song_ref)
        timing_path = timing_path_for_song(song_dir)
        errors = validate_timing(timing, timing_path)
        if errors:
            return self.send_error_json(
                "Timing is invalid:\n" + "\n".join(errors),
                HTTPStatus.BAD_REQUEST,
            )

        if timing_path.exists():
            backup_path = backup_file(timing_path)
            backup_rel = song_relative(backup_path, song_dir)
        else:
            backup_rel = None
        write_json(timing_path, timing)
        self.send_json(
            {
                "ok": True,
                "song": song_dir.name,
                "path": song_relative(timing_path, song_dir),
                "backup": backup_rel,
            }
        )

    def render_proof(self) -> None:
        body = self.read_json_body()
        song_ref = body.get("song") or self.query_value("song") or self.query_value("ref")
        if not song_ref:
            return self.send_error_json("Missing song.")
        target = body.get("target") or "horizontal"
        layout = body.get("layout") or "soft_scroll"
        command = [
            sys.executable,
            str(REPO_ROOT / "scripts" / "render_song.py"),
            str(song_ref),
            "--targets",
            str(target),
            "--layout",
            str(layout),
        ]
        result = subprocess.run(
            command,
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=900,
        )
        self.send_json(
            {
                "ok": result.returncode == 0,
                "command": command,
                "returncode": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
            },
            status=HTTPStatus.OK if result.returncode == 0 else HTTPStatus.BAD_REQUEST,
        )


def serve(host: str = "127.0.0.1", port: int = 8765, repo_root: Path | None = None) -> None:
    global REPO_ROOT
    if repo_root is not None:
        REPO_ROOT = repo_root

    server = ThreadingHTTPServer((host, port), ReviewUiHandler)
    try:
        server.serve_forever()
    finally:
        server.server_close()
