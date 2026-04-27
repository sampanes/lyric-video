"""Start or check a local ComfyUI API server for headless automation."""

from __future__ import annotations

import argparse
import json
import os
import signal
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
LOCAL_CONFIG_PATH = REPO_ROOT / "LOCAL_CONFIG.json"
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8188


def load_local_config() -> dict:
    if not LOCAL_CONFIG_PATH.exists():
        return {}
    try:
        return json.loads(LOCAL_CONFIG_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Invalid local config JSON: {LOCAL_CONFIG_PATH}: {exc}") from exc


LOCAL_CONFIG = load_local_config()


def comfyui_config() -> dict:
    value = LOCAL_CONFIG.get("comfyui", {})
    return value if isinstance(value, dict) else {}


def server_url(host: str, port: int) -> str:
    return f"http://{host}:{port}"


def get_json(url: str, *, timeout: float = 5.0) -> dict:
    with urllib.request.urlopen(url, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def is_running(host: str, port: int) -> bool:
    base = server_url(host, port)
    for endpoint in ("/system_stats", "/queue"):
        try:
            get_json(base + endpoint)
            return True
        except (ConnectionError, OSError, TimeoutError, urllib.error.URLError, json.JSONDecodeError):
            continue
    return False


def resolve_comfyui_layout(value: str | None) -> dict:
    config = comfyui_config()
    raw = value or os.environ.get("COMFYUI_ROOT") or config.get("root")
    if not raw:
        raise SystemExit(
            "ComfyUI root is required. Pass --root or set COMFYUI_ROOT to the "
            "local ComfyUI repository directory."
        )
    root = Path(raw).expanduser().resolve()

    if (root / "main.py").exists():
        portable_root = root.parent if (root.parent / "python_embeded" / "python.exe").exists() else None
        if portable_root and root.name.lower() == "comfyui":
            return {
                "comfyui_root": root,
                "portable_root": portable_root,
                "launch_cwd": portable_root,
                "main_arg": str(Path("ComfyUI") / "main.py"),
                "embedded_python": portable_root / "python_embeded" / "python.exe",
                "portable": True,
            }
        return {
            "comfyui_root": root,
            "portable_root": None,
            "launch_cwd": root,
            "main_arg": "main.py",
            "embedded_python": None,
            "portable": False,
        }

    nested_main = root / "ComfyUI" / "main.py"
    if nested_main.exists():
        embedded_python = root / "python_embeded" / "python.exe"
        return {
            "comfyui_root": root / "ComfyUI",
            "portable_root": root,
            "launch_cwd": root,
            "main_arg": str(Path("ComfyUI") / "main.py"),
            "embedded_python": embedded_python if embedded_python.exists() else None,
            "portable": True,
        }

    raise SystemExit(
        f"ComfyUI main.py not found under {root}. Expected either "
        f"{root / 'main.py'} or {nested_main}."
    )


def start_process(command: list[str], cwd: Path) -> subprocess.Popen:
    kwargs = {
        "cwd": str(cwd),
        "stdin": subprocess.DEVNULL,
        "stdout": subprocess.DEVNULL,
        "stderr": subprocess.DEVNULL,
    }
    if os.name == "nt":
        kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS
    else:
        kwargs["start_new_session"] = True
    return subprocess.Popen(command, **kwargs)


def build_start_command(args: argparse.Namespace, layout: dict) -> list[str]:
    config = comfyui_config()
    python_exe = (
        args.python
        or os.environ.get("COMFYUI_PYTHON")
        or config.get("python")
        or str(layout["embedded_python"] or sys.executable)
    )
    command = [
        python_exe,
    ]
    if layout["portable"]:
        command.append("-s")
    command.extend(
        [
            layout["main_arg"],
        ]
    )
    if args.windows_standalone_build or (layout["portable"] and not args.no_windows_standalone_build):
        command.append("--windows-standalone-build")
    if args.enable_manager:
        command.append("--enable-manager")
    command.extend(
        [
            "--listen",
            args.host,
            "--port",
            str(args.port),
        ]
    )
    if args.input_directory:
        command.extend(["--input-directory", args.input_directory])
    if args.output_directory:
        command.extend(["--output-directory", args.output_directory])
    command.extend(args.extra_args)
    return command


def wait_until_running(host: str, port: int, timeout_seconds: int) -> bool:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        if is_running(host, port):
            return True
        time.sleep(1)
    return False


def command_status(args: argparse.Namespace) -> int:
    running = is_running(args.host, args.port)
    result = {
        "running": running,
        "server": server_url(args.host, args.port),
    }
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(f"ComfyUI server: {'running' if running else 'not running'} at {result['server']}")
    return 0 if running else 1


def command_start(args: argparse.Namespace) -> int:
    if is_running(args.host, args.port):
        print(f"ComfyUI server already running at {server_url(args.host, args.port)}")
        return 0

    layout = resolve_comfyui_layout(args.root)
    command = build_start_command(args, layout)
    summary = {
        "comfyui_root": str(layout["comfyui_root"]),
        "portable_root": str(layout["portable_root"]) if layout["portable_root"] else None,
        "launch_cwd": str(layout["launch_cwd"]),
        "server": server_url(args.host, args.port),
        "command": command,
    }
    if args.dry_run:
        print(json.dumps({"dry_run": True, **summary}, indent=2))
        return 0

    process = start_process(command, layout["launch_cwd"])
    summary["pid"] = process.pid
    if args.json:
        print(json.dumps(summary, indent=2))
    else:
        print(f"Started ComfyUI server process {process.pid} at {summary['server']}")

    if args.no_wait:
        return 0
    if wait_until_running(args.host, args.port, args.timeout):
        print(f"ComfyUI server is responding at {summary['server']}")
        return 0
    raise SystemExit(f"ComfyUI server did not respond within {args.timeout} seconds.")


def listening_pids_for_port(port: int) -> list[int]:
    if os.name != "nt":
        return []
    try:
        result = subprocess.run(
            ["netstat", "-ano", "-p", "TCP"],
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return []

    pids: set[int] = set()
    suffix = f":{port}"
    for line in result.stdout.splitlines():
        parts = line.split()
        if len(parts) < 5:
            continue
        proto, local_address, _foreign_address, state, pid = parts[:5]
        if proto.upper() != "TCP" or state.upper() != "LISTENING":
            continue
        if not local_address.endswith(suffix):
            continue
        try:
            pids.add(int(pid))
        except ValueError:
            continue
    return sorted(pids)


def interrupt_server(host: str, port: int) -> None:
    request = urllib.request.Request(server_url(host, port) + "/interrupt", data=b"", method="POST")
    try:
        with urllib.request.urlopen(request, timeout=10):
            return
    except urllib.error.URLError:
        return


def command_stop(args: argparse.Namespace) -> int:
    if not is_running(args.host, args.port):
        print(f"ComfyUI server is not running at {server_url(args.host, args.port)}")
        return 0

    if args.interrupt:
        interrupt_server(args.host, args.port)
        time.sleep(1)

    pids = listening_pids_for_port(args.port)
    summary = {
        "server": server_url(args.host, args.port),
        "pids": pids,
    }
    if args.dry_run:
        print(json.dumps({"dry_run": True, **summary}, indent=2))
        return 0
    if not pids:
        raise SystemExit(
            "Could not determine the ComfyUI server process id. "
            "Close it manually or use the OS process manager."
        )

    for pid in pids:
        os.kill(pid, signal.SIGTERM)

    deadline = time.time() + args.timeout
    while time.time() < deadline:
        if not is_running(args.host, args.port):
            print(f"Stopped ComfyUI server at {summary['server']} (pids: {', '.join(map(str, pids))})")
            return 0
        time.sleep(1)
    raise SystemExit(f"ComfyUI server did not stop within {args.timeout} seconds: {summary}")


def build_parser() -> argparse.ArgumentParser:
    config = comfyui_config()
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    status = subparsers.add_parser("status", help="Check whether the ComfyUI API server is reachable.")
    status.add_argument("--host", default=os.environ.get("COMFYUI_HOST", config.get("host", DEFAULT_HOST)))
    status.add_argument("--port", type=int, default=int(os.environ.get("COMFYUI_PORT", config.get("port", DEFAULT_PORT))))
    status.add_argument("--json", action="store_true")
    status.set_defaults(func=command_status)

    start = subparsers.add_parser("start", help="Start ComfyUI as a local API server.")
    start.add_argument(
        "--root",
        help="Path to the local ComfyUI repository. Defaults to COMFYUI_ROOT or LOCAL_CONFIG.json.",
    )
    start.add_argument(
        "--python",
        help="Python executable for ComfyUI. Defaults to COMFYUI_PYTHON, LOCAL_CONFIG.json, or this Python.",
    )
    start.add_argument("--host", default=os.environ.get("COMFYUI_HOST", config.get("host", DEFAULT_HOST)))
    start.add_argument("--port", type=int, default=int(os.environ.get("COMFYUI_PORT", config.get("port", DEFAULT_PORT))))
    start.add_argument(
        "--input-directory",
        default=os.environ.get("COMFYUI_INPUT_DIR", config.get("input_directory")),
        help="ComfyUI input directory. Defaults to COMFYUI_INPUT_DIR.",
    )
    start.add_argument(
        "--output-directory",
        default=os.environ.get("COMFYUI_OUTPUT_DIR", config.get("output_directory")),
        help="ComfyUI output directory. Defaults to COMFYUI_OUTPUT_DIR.",
    )
    start.add_argument(
        "--enable-manager",
        action=argparse.BooleanOptionalAction,
        default=(
            os.environ.get("COMFYUI_ENABLE_MANAGER", str(config.get("enable_manager", "1")))
            not in {"0", "false", "False"}
        ),
        help="Pass --enable-manager to ComfyUI. Enabled by default.",
    )
    start.add_argument(
        "--windows-standalone-build",
        action="store_true",
        help="Pass --windows-standalone-build even when a portable install is not detected.",
    )
    start.add_argument(
        "--no-windows-standalone-build",
        action="store_true",
        help="Do not auto-pass --windows-standalone-build for portable installs.",
    )
    start.add_argument("--timeout", type=int, default=90)
    start.add_argument("--no-wait", action="store_true", help="Do not wait for the API to respond after starting.")
    start.add_argument("--dry-run", action="store_true", help="Print the start command without launching ComfyUI.")
    start.add_argument("--json", action="store_true")
    start.add_argument("extra_args", nargs=argparse.REMAINDER, help="Extra args after -- are passed to ComfyUI main.py.")
    start.set_defaults(func=command_start)

    stop = subparsers.add_parser("stop", help="Stop the local ComfyUI API server listening on the configured port.")
    stop.add_argument("--host", default=os.environ.get("COMFYUI_HOST", config.get("host", DEFAULT_HOST)))
    stop.add_argument("--port", type=int, default=int(os.environ.get("COMFYUI_PORT", config.get("port", DEFAULT_PORT))))
    stop.add_argument("--timeout", type=int, default=30)
    stop.add_argument("--dry-run", action="store_true")
    stop.add_argument(
        "--interrupt",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="POST /interrupt before stopping the server. Enabled by default.",
    )
    stop.set_defaults(func=command_stop)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    if args.command == "start" and args.extra_args and args.extra_args[0] == "--":
        args.extra_args = args.extra_args[1:]
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
