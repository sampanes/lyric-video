"""Queue an exported ComfyUI API workflow without depending on the ComfyUI UI."""

from __future__ import annotations

import argparse
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pipeline_common import REPO_ROOT, resolve_song_dir, write_json


DEFAULT_SERVER = "http://127.0.0.1:8188"


class ComfyUITimeoutError(RuntimeError):
    """Raised when a queued prompt does not finish before the requested timeout."""


def repo_path(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else REPO_ROOT / path


def load_workflow(path: Path) -> dict:
    if not path.exists():
        raise SystemExit(f"Workflow file does not exist: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def parse_set_value(raw: str) -> Any:
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return raw


def set_path(root: Any, dotted_path: str, value: Any) -> None:
    parts = dotted_path.split(".")
    current = root
    for part in parts[:-1]:
        if isinstance(current, list):
            current = current[int(part)]
        else:
            current = current[part]
    last = parts[-1]
    if isinstance(current, list):
        current[int(last)] = value
    else:
        current[last] = value


def apply_set_overrides(workflow: dict, values: list[str]) -> list[dict]:
    applied: list[dict] = []
    for raw in values:
        if "=" not in raw:
            raise SystemExit(f"--set must be PATH=VALUE, got: {raw}")
        path, value = raw.split("=", 1)
        parsed = parse_set_value(value)
        set_path(workflow, path, parsed)
        applied.append({"path": path, "value": parsed})
    return applied


def first_text_node(workflow: dict, kind: str) -> str | None:
    kind = kind.lower()
    fallback = None
    for node_id, node in workflow.items():
        inputs = node.get("inputs", {})
        if "text" not in inputs:
            continue
        title = node.get("_meta", {}).get("title", "").lower()
        if kind in title:
            return node_id
        if fallback is None:
            fallback = node_id
    return fallback if kind == "positive" else None


def first_node_with_input(workflow: dict, input_name: str) -> str | None:
    for node_id, node in workflow.items():
        if input_name in node.get("inputs", {}):
            return node_id
    return None


def first_primitive_value_node(workflow: dict, title: str) -> str | None:
    normalized = title.lower()
    for node_id, node in workflow.items():
        node_title = node.get("_meta", {}).get("title", "").lower()
        if normalized == node_title and "value" in node.get("inputs", {}):
            return node_id
    for node_id, node in workflow.items():
        node_title = node.get("_meta", {}).get("title", "").lower()
        if normalized in node_title and "value" in node.get("inputs", {}):
            return node_id
    return None


def apply_convenience_overrides(workflow: dict, args: argparse.Namespace) -> list[dict]:
    overrides: list[dict] = []

    def set_input(node_id: str | None, input_name: str, value: Any, label: str) -> None:
        if value is None:
            return
        if node_id is None:
            raise SystemExit(f"Could not find a ComfyUI node input for {label}. Use --set instead.")
        workflow[node_id]["inputs"][input_name] = value
        overrides.append({"path": f"{node_id}.inputs.{input_name}", "value": value, "source": label})

    set_input(first_text_node(workflow, "positive"), "text", args.positive_prompt, "--positive-prompt")
    set_input(first_text_node(workflow, "negative"), "text", args.negative_prompt, "--negative-prompt")
    seed_node = first_node_with_input(workflow, "seed")
    seed_input = "seed"
    if seed_node is None:
        seed_node = first_node_with_input(workflow, "noise_seed")
        seed_input = "noise_seed"
    set_input(seed_node, seed_input, args.seed, "--seed")

    width_node = first_primitive_value_node(workflow, "Width") or first_node_with_input(workflow, "width")
    width_input = "value" if width_node and "value" in workflow[width_node].get("inputs", {}) else "width"
    height_node = first_primitive_value_node(workflow, "Height") or first_node_with_input(workflow, "height")
    height_input = "value" if height_node and "value" in workflow[height_node].get("inputs", {}) else "height"
    set_input(width_node, width_input, args.width, "--width")
    set_input(height_node, height_input, args.height, "--height")
    set_input(first_node_with_input(workflow, "length"), "length", args.length, "--length")
    set_input(first_node_with_input(workflow, "fps"), "fps", args.fps, "--fps")
    set_input(
        first_node_with_input(workflow, "filename_prefix"),
        "filename_prefix",
        args.filename_prefix,
        "--filename-prefix",
    )
    return overrides


def post_json(url: str, payload: dict) -> dict:
    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.URLError as exc:
        raise SystemExit(
            f"Could not reach ComfyUI at {url}: {exc}. "
            "Start the local API server with scripts\\comfyui_server.py start."
        ) from exc


def post_empty(url: str) -> None:
    request = urllib.request.Request(url, data=b"", method="POST")
    try:
        with urllib.request.urlopen(request, timeout=30):
            return
    except urllib.error.URLError as exc:
        raise SystemExit(
            f"Could not reach ComfyUI at {url}: {exc}. "
            "Start the local API server with scripts\\comfyui_server.py start."
        ) from exc


def get_json(url: str) -> dict:
    try:
        with urllib.request.urlopen(url, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.URLError as exc:
        raise SystemExit(
            f"Could not reach ComfyUI at {url}: {exc}. "
            "Start the local API server with scripts\\comfyui_server.py start."
        ) from exc


def queue_prompt(server: str, workflow: dict, client_id: str) -> dict:
    return post_json(f"{server.rstrip('/')}/prompt", {"prompt": workflow, "client_id": client_id})


def interrupt(server: str) -> None:
    post_empty(f"{server.rstrip('/')}/interrupt")


def queue_status(server: str) -> dict:
    return get_json(f"{server.rstrip('/')}/queue")


def queue_prompt_ids(queue: dict, key: str) -> list[str]:
    ids: list[str] = []
    for entry in queue.get(key, []):
        if isinstance(entry, list) and len(entry) > 1:
            ids.append(str(entry[1]))
    return ids


def summarize_queue(queue: dict) -> dict:
    return {
        "running_count": len(queue.get("queue_running", [])),
        "pending_count": len(queue.get("queue_pending", [])),
        "running_prompt_ids": queue_prompt_ids(queue, "queue_running"),
        "pending_prompt_ids": queue_prompt_ids(queue, "queue_pending"),
    }


def wait_for_history(server: str, prompt_id: str, timeout_seconds: int, poll_interval: float) -> dict:
    deadline = time.time() + timeout_seconds
    history_url = f"{server.rstrip('/')}/history/{urllib.parse.quote(prompt_id)}"
    while time.time() < deadline:
        history = get_json(history_url)
        if prompt_id in history:
            return history[prompt_id]
        time.sleep(poll_interval)
    raise ComfyUITimeoutError(f"Timed out waiting for ComfyUI prompt: {prompt_id}")


def iter_assets(history: dict) -> list[dict]:
    assets: list[dict] = []
    outputs = history.get("outputs", {})
    for node_id, output in outputs.items():
        if not isinstance(output, dict):
            continue
        for output_key, value in output.items():
            if not isinstance(value, list):
                continue
            for entry in value:
                if isinstance(entry, dict) and entry.get("filename"):
                    asset = dict(entry)
                    asset["node_id"] = node_id
                    asset["output_key"] = output_key
                    assets.append(asset)
    return assets


def unique_path(path: Path) -> Path:
    if not path.exists():
        return path
    stem = path.stem
    suffix = path.suffix
    for index in range(2, 10_000):
        candidate = path.with_name(f"{stem}-{index}{suffix}")
        if not candidate.exists():
            return candidate
    raise SystemExit(f"Could not find a unique output path for {path}")


def download_asset(server: str, asset: dict, output_dir: Path, *, overwrite: bool = False) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    query = urllib.parse.urlencode(
        {
            "filename": asset["filename"],
            "subfolder": asset.get("subfolder", ""),
            "type": asset.get("type", "output"),
        }
    )
    url = f"{server.rstrip('/')}/view?{query}"
    target = output_dir / Path(asset["filename"]).name
    if not overwrite:
        target = unique_path(target)
    try:
        with urllib.request.urlopen(url, timeout=120) as response:
            target.write_bytes(response.read())
    except urllib.error.URLError as exc:
        raise SystemExit(f"Could not download ComfyUI asset from {url}: {exc}") from exc
    return target


def output_dir_from_args(args: argparse.Namespace) -> Path | None:
    if args.download_to:
        return repo_path(args.download_to)
    if args.song:
        return resolve_song_dir(args.song) / "assets" / "backgrounds"
    return None


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("workflow", help="Path to an exported ComfyUI API workflow JSON.")
    parser.add_argument("--song", help="Optional song slug used for default download placement.")
    parser.add_argument(
        "--server",
        default=os.environ.get("COMFYUI_SERVER", DEFAULT_SERVER),
        help="ComfyUI server URL. Defaults to COMFYUI_SERVER or http://127.0.0.1:8188.",
    )
    parser.add_argument("--set", dest="set_values", action="append", default=[], help="Override workflow JSON with PATH=VALUE.")
    parser.add_argument("--positive-prompt", help="Set the first positive CLIP text node.")
    parser.add_argument("--negative-prompt", help="Set the first negative CLIP text node.")
    parser.add_argument("--seed", type=int, help="Set the first seed input.")
    parser.add_argument("--width", type=int, help="Set the first width input.")
    parser.add_argument("--height", type=int, help="Set the first height input.")
    parser.add_argument("--length", type=int, help="Set the first length input.")
    parser.add_argument("--fps", type=int, help="Set the first fps input.")
    parser.add_argument("--filename-prefix", help="Set the first filename_prefix input.")
    parser.add_argument("--dry-run", action="store_true", help="Print the resolved request without contacting ComfyUI.")
    parser.add_argument("--wait", action="store_true", help="Wait for completion and inspect outputs.")
    parser.add_argument("--timeout", type=int, default=900, help="Seconds to wait when --wait is used.")
    parser.add_argument(
        "--interrupt-on-timeout",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="POST /interrupt if --wait times out. Enabled by default.",
    )
    parser.add_argument("--poll-interval", type=float, default=2.0, help="Seconds between history polls.")
    parser.add_argument("--download-to", help="Directory for completed ComfyUI output assets.")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite downloaded assets with matching names.")
    parser.add_argument("--client-id", default=None, help="Optional ComfyUI client id.")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    workflow_path = repo_path(args.workflow)
    workflow = load_workflow(workflow_path)
    overrides = []
    overrides.extend(apply_convenience_overrides(workflow, args))
    overrides.extend(apply_set_overrides(workflow, args.set_values))

    output_dir = output_dir_from_args(args)
    client_id = args.client_id or str(uuid.uuid4())
    summary = {
        "workflow": str(workflow_path),
        "server": args.server,
        "client_id": client_id,
        "song": args.song,
        "download_to": str(output_dir) if output_dir else None,
        "overrides": overrides,
        "node_count": len(workflow),
    }

    if args.dry_run:
        print(json.dumps({"dry_run": True, **summary}, indent=2))
        return 0

    queued = queue_prompt(args.server, workflow, client_id)
    prompt_id = queued.get("prompt_id")
    if not prompt_id:
        raise SystemExit(f"ComfyUI response did not include prompt_id: {queued}")
    print(f"Queued ComfyUI prompt: {prompt_id}")

    if not args.wait:
        print(json.dumps({"queued": queued, **summary}, indent=2))
        return 0

    try:
        history = wait_for_history(args.server, prompt_id, args.timeout, args.poll_interval)
    except ComfyUITimeoutError:
        before_interrupt = summarize_queue(queue_status(args.server))
        interrupted = False
        after_interrupt = before_interrupt
        if args.interrupt_on_timeout:
            interrupt(args.server)
            interrupted = True
            time.sleep(2)
            after_interrupt = summarize_queue(queue_status(args.server))
        print(
            json.dumps(
                {
                    "timeout": True,
                    "prompt_id": prompt_id,
                    **summary,
                    "interrupted": interrupted,
                    "queue_before_interrupt": before_interrupt,
                    "queue_after_interrupt": after_interrupt,
                    "note": (
                        "If the prompt remains running after interrupt, restart ComfyUI "
                        "with scripts\\comfyui_server.py stop then scripts\\comfyui_server.py start."
                    ),
                },
                indent=2,
            )
        )
        return 2

    assets = iter_assets(history)
    downloaded: list[dict] = []
    if output_dir:
        for asset in assets:
            path = download_asset(args.server, asset, output_dir, overwrite=args.overwrite)
            downloaded.append({"path": str(path), "source": asset})
            sidecar = path.with_suffix(path.suffix + ".comfyui.json")
            write_json(
                sidecar,
                {
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "prompt_id": prompt_id,
                    "workflow": str(workflow_path),
                    "server": args.server,
                    "overrides": overrides,
                    "source_asset": asset,
                },
            )

    print(
        json.dumps(
            {
                "prompt_id": prompt_id,
                **summary,
                "assets": assets,
                "downloaded": downloaded,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
