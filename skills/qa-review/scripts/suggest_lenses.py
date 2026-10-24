#!/usr/bin/env python3
"""Suggest which review lenses may apply to a change. A signal for the reviewer, not a verdict.

Reads the change from a file or stdin. The input is either a unified diff (the changed paths are
taken from its headers) or a plain list of paths, one per line, such as `gh pr diff N --name-only`.

Lenses are the `*.md` files in two places. The README in a lens folder is not a lens.
  bundled  <this skill>/references/lenses/
  project  <repo being reviewed>/.claude/qa-review/lenses/   (change it with --project-lenses)
When both define a lens with the same name, the project lens wins.

Each lens opens with a frontmatter block that has `applies_when.paths` (a list of globs) and
`applies_when.touches` (one plain-language line). Globs use `*` within one folder, `**` across
folders, and `?` for one character. Paths are matched with forward slashes.

Output is JSON on stdout. The exit code is 0 whenever the script ran, even when it found nothing.
Anything that goes wrong is reported in the output and never stops the review.

  {
    "status": "ok" | "no_input",      "no_input": no changed path was found; judge the lenses by hand
    "changed_files": ["src/app.py"],
    "matched": [                      lenses where a changed path matched one of the globs
      {"name": "service", "source": "bundled" | "project", "description": "...",
       "touches": "...", "matched_files": ["db/migrations/001.sql"]}
    ],
    "unmatched": [                    other lenses; judge each one from `touches`
      {"name": "api-spec", "source": "bundled", "description": "...", "touches": "..."}
    ],
    "overridden": ["service"],        bundled lenses replaced by a project lens of the same name
    "skipped": [{"file": "x.md", "reason": "..."}],   lens files that could not be used
    "note": "..."                     present when there is something to know
  }
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

LENS_INDEX = "README.md"
DEFAULT_PROJECT_LENSES = Path(".claude") / "qa-review" / "lenses"
BUNDLED_LENSES = Path(__file__).resolve().parent.parent / "references" / "lenses"

_DIFF_HEADER = re.compile(r"^diff --git a/(.+?) b/(.+)$")
_NEW_FILE = re.compile(r"^\+\+\+ b/(.+?)(?:\t.*)?$")


# --- reading the change ---


def changed_paths(text: str) -> list[str]:
    """Paths from a unified diff, or from a plain list of paths when the text has no diff headers."""
    paths: list[str] = []

    def add(path: str) -> None:
        path = path.strip().strip('"').replace("\\", "/").removeprefix("./")
        if path and path != "/dev/null" and path not in paths:
            paths.append(path)

    lines = text.splitlines()
    for line in lines:
        header = _DIFF_HEADER.match(line)
        if header:
            add(header.group(2))
    if not paths:
        for line in lines:
            new_file = _NEW_FILE.match(line)
            if new_file:
                add(new_file.group(1))
    if not paths and not any(line.startswith(("diff ", "--- ", "@@")) for line in lines):
        for line in lines:
            readable = not any(ch == "�" or (ch < " " and ch != "\t") for ch in line)
            if line.strip() and not line.startswith("#") and readable:
                add(line)
    return paths


# --- matching ---


def glob_to_regex(pattern: str) -> re.Pattern[str]:
    """`*` stays inside one folder, `**` crosses folders, `?` is one character."""
    out = []
    i = 0
    while i < len(pattern):
        if pattern.startswith("**/", i):
            out.append("(?:.*/)?")
            i += 3
        elif pattern.startswith("**", i):
            out.append(".*")
            i += 2
        elif pattern[i] == "*":
            out.append("[^/]*")
            i += 1
        elif pattern[i] == "?":
            out.append("[^/]")
            i += 1
        else:
            out.append(re.escape(pattern[i]))
            i += 1
    return re.compile("".join(out) + r"\Z")


def matching_files(paths: list[str], globs: list[str]) -> list[str]:
    patterns = [glob_to_regex(g) for g in globs]
    return [p for p in paths if any(r.match(p) for r in patterns)]


# --- reading lens files ---


def _unquote(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        return value[1:-1]
    return value


def _inline_list(value: str) -> list[str] | None:
    value = value.strip()
    if not (value.startswith("[") and value.endswith("]")):
        return None
    items = re.findall(r"""\"[^\"]*\"|'[^']*'|[^,\s][^,]*""", value[1:-1])
    return [_unquote(item) for item in items]


def parse_lens(text: str) -> dict:
    """Read the small frontmatter subset a lens uses. Raises ValueError when a required field is missing.

    Understands `key: value`, the one level of nesting under `applies_when:`, and lists written either
    as `["a", "b"]` or as `- a` lines. This is not a general YAML parser.
    """
    lines = text.lstrip("﻿").splitlines()
    if not lines or lines[0].strip() != "---":
        raise ValueError("no frontmatter")
    try:
        end = next(i for i in range(1, len(lines)) if lines[i].strip() == "---")
    except StopIteration:
        raise ValueError("frontmatter is not closed") from None

    top: dict = {}
    applies: dict = {}
    last: tuple[dict, str] | None = None  # the key a following `- item` line belongs to
    for raw in lines[1:end]:
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("- "):
            if last is None or not isinstance(last[0].get(last[1]), list):
                raise ValueError(f"unexpected list item: {line}")
            last[0][last[1]].append(_unquote(line[2:]))
            continue
        key, sep, value = line.partition(":")
        if not sep:
            raise ValueError(f"cannot read: {line}")
        key, value = key.strip(), value.strip()
        nested = len(raw) > len(raw.lstrip())
        target = applies if nested else top
        if value == "" and not nested and key == "applies_when":
            top["applies_when"] = applies
            last = None
        elif value == "":
            target[key] = []
            last = (target, key)
        else:
            as_list = _inline_list(value)
            target[key] = as_list if as_list is not None else _unquote(value)
            last = (target, key)

    for field in ("name", "description"):
        if not isinstance(top.get(field), str) or not top[field]:
            raise ValueError(f"'{field}' is missing")
    paths = applies.get("paths")
    if not isinstance(paths, list) or not all(isinstance(p, str) for p in paths):
        raise ValueError("'applies_when.paths' must be a list of globs")
    touches = applies.get("touches", "")
    return {
        "name": top["name"],
        "description": top["description"],
        "paths": paths,
        "touches": touches if isinstance(touches, str) else "",
    }


def load_lenses(folder: Path, source: str, skipped: list[dict]) -> dict[str, dict]:
    """Every usable lens in a folder, by name. A folder that is missing has no lenses."""
    lenses: dict[str, dict] = {}
    if not folder.is_dir():
        return lenses
    for path in sorted(folder.glob("*.md")):
        if path.name == LENS_INDEX:
            continue
        try:
            lens = parse_lens(path.read_text(encoding="utf-8"))
            if lens["name"] != path.stem:
                raise ValueError(f"name '{lens['name']}' must equal the file name '{path.stem}'")
        except (OSError, UnicodeDecodeError, ValueError) as e:
            skipped.append({"file": str(path), "reason": str(e)})
            continue
        lens["source"] = source
        lenses[lens["name"]] = lens
    return lenses


# --- the report ---


def suggest(text: str, bundled_dir: Path, project_dir: Path) -> dict:
    skipped: list[dict] = []
    bundled = load_lenses(bundled_dir, "bundled", skipped)
    project = load_lenses(project_dir, "project", skipped)
    overridden = sorted(set(bundled) & set(project))
    lenses = {**bundled, **project}  # the project lens replaces a bundled one of the same name

    paths = changed_paths(text)
    report: dict = {
        "status": "ok" if paths else "no_input",
        "changed_files": paths,
        "matched": [],
        "unmatched": [],
        "overridden": overridden,
        "skipped": skipped,
    }
    notes = []
    if not paths:
        notes.append("No changed file paths were found in the input, so no lens could be matched by path.")
    if not lenses:
        notes.append("No lenses were found. The core review applies.")
    for name in sorted(lenses):
        lens = lenses[name]
        entry = {
            "name": name,
            "source": lens["source"],
            "description": lens["description"],
            "touches": lens["touches"],
        }
        files = matching_files(paths, lens["paths"])
        if files:
            report["matched"].append({**entry, "matched_files": files})
        else:
            report["unmatched"].append(entry)
    if notes:
        report["note"] = " ".join(notes)
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="suggest_lenses.py",
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("input", nargs="?", help="a diff or a list of paths; read from stdin when omitted or '-'")
    parser.add_argument(
        "--project-lenses",
        type=Path,
        default=DEFAULT_PROJECT_LENSES,
        help=f"folder of project lenses (default: {DEFAULT_PROJECT_LENSES.as_posix()} in the current directory)",
    )
    parser.add_argument("--bundled-lenses", type=Path, default=BUNDLED_LENSES, help="folder of bundled lenses")
    args = parser.parse_args(argv)

    try:
        if args.input in (None, "-"):
            text = sys.stdin.buffer.read().decode("utf-8", errors="replace")
        else:
            text = Path(args.input).read_text(encoding="utf-8", errors="replace")
    except OSError as e:
        text = ""
        read_error = f"Could not read the input: {e}."
    else:
        read_error = ""

    report = suggest(text, args.bundled_lenses, args.project_lenses)
    if read_error:
        report["note"] = f"{read_error} {report.get('note', '')}".strip()
    sys.stdout.reconfigure(encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
