"""Shared helpers for the qa-review scripts: read a change from a file or stdin and list the paths in it.

This is a module, not a command. `suggest_lenses.py` and `missing_tests.py` import it, and the
scripts that read the content of a diff will too. It sits next to them in `scripts/` and uses only the
standard library. Each script puts its own folder on `sys.path` before importing it, so it works when
run as `python3 ${CLAUDE_SKILL_DIR}/scripts/<name>.py` from any folder.

The input is either a unified diff (the changed paths come from its headers) or a plain list of paths,
one per line, such as `gh pr diff N --name-only`. A path list cannot show that a file was deleted.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

_DIFF_HEADER = re.compile(r"^diff --git a/(.+?) b/(.+)$")
_OLD_FILE = re.compile(r"^--- a/(.+?)(?:\t.*)?$")
_NEW_FILE = re.compile(r"^\+\+\+ b/(.+?)(?:\t.*)?$")


def read_input(source: str | None) -> tuple[str, str]:
    """The text of the input and a problem to report ("" when there is none).

    `source` is a file path, or None or "-" for stdin. A file that cannot be read gives empty text, so
    the script can still print a report that says so.
    """
    try:
        if source in (None, "-"):
            return sys.stdin.buffer.read().decode("utf-8", errors="replace"), ""
        return Path(source).read_text(encoding="utf-8", errors="replace"), ""
    except OSError as e:
        return "", f"Could not read the input: {e}."


def print_report(report: dict) -> None:
    """Print a report as JSON in UTF-8, whatever the terminal's encoding is."""
    sys.stdout.reconfigure(encoding="utf-8")
    print(json.dumps(report, indent=2))


def changed_files(text: str) -> tuple[list[str], set[str]]:
    """The changed paths in order, and the subset a diff shows as deleted."""
    paths: list[str] = []
    deleted: set[str] = set()

    def add(path: str) -> str | None:
        path = path.strip().strip('"').replace("\\", "/").removeprefix("./")
        if not path or path == "/dev/null":
            return None
        if path not in paths:
            paths.append(path)
        return path

    lines = text.splitlines()
    current: str | None = None
    for line in lines:
        header = _DIFF_HEADER.match(line)
        if header:
            current = add(header.group(2))
        elif line.startswith("deleted file mode") and current:
            deleted.add(current)
    if not paths:  # a diff without git headers: read the --- and +++ lines
        old: str | None = None
        for line in lines:
            old_file, new_file = _OLD_FILE.match(line), _NEW_FILE.match(line)
            if old_file:
                old = old_file.group(1)
            elif new_file:
                add(new_file.group(1))
            elif line.startswith("+++ /dev/null") and old:
                gone = add(old)
                if gone:
                    deleted.add(gone)
    if not paths and not any(line.startswith(("diff ", "--- ", "@@")) for line in lines):
        for line in lines:
            readable = not any(ch == "�" or (ch < " " and ch != "\t") for ch in line)
            if line.strip() and not line.startswith("#") and readable:
                add(line)
    return paths, deleted


def changed_paths(text: str) -> list[str]:
    """Only the changed paths, in order."""
    return changed_files(text)[0]
