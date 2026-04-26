"""Scan tracked repo text for private names and machine-specific paths."""

from __future__ import annotations

import argparse
import re
import subprocess
from pathlib import Path

from pipeline_common import REPO_ROOT


LOCAL_TERMS_FILE = REPO_ROOT / "LOCAL_PRIVACY_TERMS.txt"
DEFAULT_BLOCKED_TERMS: list[str] = []

DEFAULT_PATTERNS = {
    "windows_absolute_path": re.compile(r"\b[A-Za-z]:\\"),
    "windows_user_profile": re.compile(r"\bUsers\\[^\\\s]+", re.IGNORECASE),
    "posix_user_home": re.compile(r"/(?:Users|home)/[^/\s]+"),
}


def git_files(*args: str) -> list[Path]:
    result = subprocess.run(
        ["git", "ls-files", "-z", *args],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
    )
    paths = [Path(raw.decode("utf-8")) for raw in result.stdout.split(b"\0") if raw]
    return paths


def tracked_paths(include_untracked: bool) -> list[Path]:
    paths = git_files()
    if include_untracked:
        paths.extend(git_files("--others", "--exclude-standard"))
    return sorted(set(paths))


def is_probably_text(data: bytes) -> bool:
    return b"\0" not in data


def scan_path(path: Path, blocked_terms: list[str]) -> list[str]:
    full_path = REPO_ROOT / path
    if not full_path.is_file():
        return []

    data = full_path.read_bytes()
    if not is_probably_text(data):
        return []

    text = data.decode("utf-8", errors="replace")
    findings: list[str] = []
    term_patterns = [
        (term, re.compile(rf"(?<![A-Za-z0-9]){re.escape(term)}(?![A-Za-z0-9])", re.IGNORECASE))
        for term in blocked_terms
        if term
    ]
    for line_number, line in enumerate(text.splitlines(), start=1):
        for term, pattern in term_patterns:
            if pattern.search(line):
                findings.append(f"{path}:{line_number}: blocked term '{term}'")
        for label, pattern in DEFAULT_PATTERNS.items():
            if pattern.search(line):
                findings.append(f"{path}:{line_number}: {label}")
    return findings


def load_local_terms() -> list[str]:
    if not LOCAL_TERMS_FILE.exists():
        return []
    terms = []
    for line in LOCAL_TERMS_FILE.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            terms.append(stripped)
    return terms


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--include-untracked",
        action="store_true",
        help="Also scan untracked non-ignored files.",
    )
    parser.add_argument(
        "--term",
        action="append",
        default=[],
        help="Additional case-insensitive blocked term. Can be repeated.",
    )
    parser.add_argument(
        "--no-local-terms",
        action="store_true",
        help="Do not load ignored LOCAL_PRIVACY_TERMS.txt.",
    )
    args = parser.parse_args()

    blocked_terms = (
        DEFAULT_BLOCKED_TERMS
        + ([] if args.no_local_terms else load_local_terms())
        + args.term
    )
    findings: list[str] = []
    for path in tracked_paths(args.include_untracked):
        findings.extend(scan_path(path, blocked_terms))

    if findings:
        print("Privacy check failed:")
        for finding in findings:
            print(f"- {finding}")
        return 1

    scope = "tracked and untracked non-ignored files" if args.include_untracked else "tracked files"
    print(f"Privacy check passed: {scope}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
