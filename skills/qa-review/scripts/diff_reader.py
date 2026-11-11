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
from dataclasses import dataclass, field
from pathlib import Path
from typing import NamedTuple

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


# --- reading the lines of a diff ---

_HUNK = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")


class DiffLine(NamedTuple):
    kind: str  # "+" added, "-" removed, " " unchanged context
    number: int  # the line number in the new file for "+" and " ", in the old file for "-"
    text: str


@dataclass
class FileDiff:
    path: str
    deleted: bool = False
    lines: list[DiffLine] = field(default_factory=list)
    marked: bool = False  # the --- and +++ lines were seen


def _clean_path(raw: str) -> str:
    path = raw.split("\t")[0].strip().strip('"').replace("\\", "/")
    for prefix in ("a/", "b/", "./"):
        path = path.removeprefix(prefix)
    return path


def file_diffs(text: str) -> list[FileDiff]:
    """The changed files of a unified diff with their lines. A plain list of paths has no lines and gives [].

    Hunk lengths are counted, so a removed line that starts with `-- ` is not taken for a file header.
    """
    files: list[FileDiff] = []
    current: FileDiff | None = None
    old_path = ""
    old_left = new_left = old_no = new_no = 0
    for line in text.splitlines():
        if current is not None and (old_left > 0 or new_left > 0) and not line.startswith(("diff --git ", "@@ ")):
            if line.startswith("\\"):  # "\ No newline at end of file"
                continue
            if line.startswith("+") and new_left > 0:
                current.lines.append(DiffLine("+", new_no, line[1:]))
                new_no += 1
                new_left -= 1
            elif line.startswith("-") and old_left > 0:
                current.lines.append(DiffLine("-", old_no, line[1:]))
                old_no += 1
                old_left -= 1
            else:
                current.lines.append(DiffLine(" ", new_no, line[1:]))
                old_no += 1
                new_no += 1
                old_left -= 1
                new_left -= 1
            continue
        header = _DIFF_HEADER.match(line)
        hunk = _HUNK.match(line)
        if header:
            old_left = new_left = 0  # a hunk that is shorter than it says ends here
            current = FileDiff(_clean_path(header.group(2)))
            files.append(current)
        elif line.startswith("deleted file mode") and current is not None:
            current.deleted = True
        elif line.startswith("--- "):
            old_path = _clean_path(line[4:])
        elif line.startswith("+++ "):
            new_path = _clean_path(line[4:])
            if current is None or current.marked:  # a diff without "diff --git" lines
                current = FileDiff(old_path if new_path == "/dev/null" else new_path)
                files.append(current)
            current.marked = True
            if new_path == "/dev/null":
                current.deleted = True
        elif hunk and current is not None:
            old_no, new_no = int(hunk.group(1)), int(hunk.group(3))
            old_left = int(hunk.group(2) or 1)
            new_left = int(hunk.group(4) or 1)
    return [f for f in files if f.path and f.path != "/dev/null"]
