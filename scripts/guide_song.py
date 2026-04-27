"""Print a self-service operator checklist for a song package."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from inspect_song import build_song_inspection


COMFYUI_T2I_WORKFLOW = Path("workflows/comfyui/node-graphs/basic_flux_t2i.api.json")
COMFYUI_I2V_WORKFLOW = Path("workflows/comfyui/node-graphs/basic_wan_i2v_subtle-3.api.json")


def item(key: str, label: str, status: str, command: str | None = None, note: str | None = None) -> dict:
    result = {
        "key": key,
        "label": label,
        "status": status,
    }
    if command:
        result["command"] = command
    if note:
        result["note"] = note
    return result


def build_guide(song_ref: str, *, check_tools: bool = False) -> dict:
    inspection = build_song_inspection(song_ref, check_tools=check_tools)
    song = inspection["song_dir_name"]
    exists = inspection["exists"]
    config_present = inspection["config"].get("present", False) and not inspection["config"].get("error")
    audio_count = len(inspection["audio_candidates"])
    lyric_count = len(inspection["lyric_candidates"])
    timing_present = inspection["timing"]["present"]
    exports_present = bool(inspection["exports"])
    t2i_workflow_exists = COMFYUI_T2I_WORKFLOW.exists()
    i2v_workflow_exists = COMFYUI_I2V_WORKFLOW.exists()
    workflow_exists = t2i_workflow_exists and i2v_workflow_exists

    checklist: list[dict] = []
    checklist.append(
        item(
            "song_folder",
            "Create a song folder under songs/.",
            "done" if exists else "blocked",
            note=None if exists else "Add one audio file and one raw lyric file.",
        )
    )
    checklist.append(
        item(
            "source_inputs",
            "Provide exactly one source audio file and one raw lyric file.",
            "done" if audio_count == 1 and lyric_count == 1 else "needs_attention",
            command=f'python scripts\\inspect_song.py "{song}"',
            note=f"Detected {audio_count} audio candidate(s) and {lyric_count} lyric candidate(s).",
        )
    )

    if config_present:
        config_status = "done"
        config_command = None
    elif exists and audio_count == 1 and lyric_count == 1:
        config_status = "ready"
        config_command = f'python scripts\\intake_song.py "{song}"'
    else:
        config_status = "blocked"
        config_command = None
    checklist.append(
        item(
            "song_config",
            "Create or verify song.json.",
            config_status,
            command=config_command,
            note="Use intake_song.py when metadata or input paths need normalization.",
        )
    )

    draft_status = "done" if exports_present else "ready" if exists and (config_present or (audio_count == 1 and lyric_count == 1)) else "blocked"
    checklist.append(
        item(
            "draft_render",
            "Make a first horizontal proof video.",
            draft_status,
            command=f'python scripts\\make_videos.py "{song}" --force --targets horizontal'
            if draft_status == "ready"
            else None,
            note="This confirms structure and rendering; it is not final timing.",
        )
    )

    validation_errors = bool(inspection["validation"]["errors"])
    checklist.append(
        item(
            "validate",
            "Validate package structure and tools.",
            "ready" if validation_errors else "done" if timing_present else "pending",
            command=f'python scripts\\validate_song.py "{song}" --require-timing --check-tools'
            if timing_present and validation_errors
            else None,
            note="Run with --check-tools after setup changes or before a serious render." if timing_present else None,
        )
    )

    timing_source = inspection["timing"].get("source") or ""
    whisper_done = "whisper" in timing_source.lower()
    checklist.append(
        item(
            "whisper_draft_timing",
            "Generate draft timing with WhisperX when better-than-even timing is needed.",
            "done" if whisper_done else "ready" if config_present else "pending",
            command=f'python scripts\\make_videos.py "{song}" --refresh-whisper --targets all'
            if config_present and not whisper_done
            else None,
            note="Whisper timing is a head start, not final editorial timing.",
        )
    )

    checklist.append(
        item(
            "human_timing_review",
            "Review timing by listening, then adjust reviewed timing without hand-editing JSON.",
            "ready" if timing_present else "pending",
            command=f'python scripts\\timing_adjust.py report "{song}" --around line_001'
            if timing_present
            else None,
            note="Use nudge or fit after identifying the first bad line/range.",
        )
    )

    checklist.append(
        item(
            "comfyui_api_server",
            "Start or verify the local ComfyUI API server.",
            "ready" if exists and workflow_exists else "blocked",
            command="python scripts\\comfyui_server.py status",
            note=(
                "If not running, set COMFYUI_ROOT and run: python scripts\\comfyui_server.py start"
                if workflow_exists
                else f"Missing workflow: {COMFYUI_I2V_WORKFLOW}"
            ),
        )
    )

    checklist.append(
        item(
            "comfyui_headless_still_mvp",
            "Pre-GUI proof: generate a still image through ComfyUI headlessly.",
            "ready" if exists and t2i_workflow_exists else "blocked",
            command=(
                f'python scripts\\comfyui_queue.py "{COMFYUI_T2I_WORKFLOW}" '
                f'--song "{song}" --dry-run --filename-prefix "lyric-video/{song}/still-mvp"'
            )
            if exists and t2i_workflow_exists
            else None,
            note=(
                "This should be the first real background-generation step before image-to-video."
                if t2i_workflow_exists
                else f"Missing workflow: {COMFYUI_T2I_WORKFLOW}"
            ),
        )
    )

    checklist.append(
        item(
            "comfyui_headless_background_mvp",
            "Pre-GUI proof: animate an approved still image through ComfyUI headlessly.",
            "ready" if exists and i2v_workflow_exists else "blocked",
            command=(
                f'python scripts\\comfyui_queue.py "{COMFYUI_I2V_WORKFLOW}" '
                f'--song "{song}" --dry-run --timeout 900 '
                f'--filename-prefix "lyric-video/{song}/wan-probe" '
                f'--positive-prompt "gentle sparkles, soft ambient shimmer, almost static, stable background, no camera movement" '
                f'--length 33 --set "3.inputs.steps=8" '
                f'--set "56.inputs.image=lyric-video/{song}/still-mvp_00001_.png [output]"'
            )
            if exists and i2v_workflow_exists
            else None,
            note=(
                (
                    "Starts with dry-run. Actual queue requires a running local ComfyUI server."
                    if i2v_workflow_exists
                    else f"Missing workflow: {COMFYUI_I2V_WORKFLOW}"
                )
                + " Normal order is still image first, then a moderate image-to-video probe. "
                + "No ComfyUI UI clicking should be needed for routine generation."
            ),
        )
    )

    next_item = next((entry for entry in checklist if entry["status"] in {"ready", "needs_attention", "blocked"}), None)
    return {
        "song": song,
        "inspection": inspection,
        "checklist": checklist,
        "next": next_item,
    }


def print_guide(guide: dict) -> None:
    print(f"Song guide: {guide['song']}")
    print(f"Status: {guide['inspection']['status']}")
    print()
    for entry in guide["checklist"]:
        print(f"[{entry['status']}] {entry['label']}")
        if entry.get("command"):
            print(f"  {entry['command']}")
        if entry.get("note"):
            print(f"  {entry['note']}")
    if guide.get("next"):
        print()
        next_entry = guide["next"]
        print(f"Next: {next_entry.get('command') or next_entry['label']}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("song", help="Song slug, approximate name, or song folder.")
    parser.add_argument("--json", action="store_true", help="Print machine-readable checklist JSON.")
    parser.add_argument("--check-tools", action="store_true", help="Include ffmpeg/ffprobe checks.")
    args = parser.parse_args()

    guide = build_guide(args.song, check_tools=args.check_tools)
    if args.json:
        print(json.dumps(guide, indent=2))
    else:
        print_guide(guide)
    return 0 if guide["inspection"]["exists"] and not guide["inspection"]["validation"]["errors"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
