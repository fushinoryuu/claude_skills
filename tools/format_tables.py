"""Align GitHub-flavored Markdown pipe tables so long rows stay readable.

    uv run poe fmt-tables       rewrite tracked .md files in place
    uv run poe check-tables     exit 1 if any table is not aligned (changes nothing)

Only table blocks outside code fences are touched. Indentation and line endings are kept.
"""

import argparse
import re
import subprocess
import sys
import unicodedata
from pathlib import Path

DELIMITER_CELL = re.compile(r"^:?-+:?$")
UNESCAPED_PIPE = re.compile(r"(?<!\\)\|")
FENCES = ("```", "~~~")
MIN_COLUMN_WIDTH = 3


def display_width(text: str) -> int:
    """Terminal cells the text takes up: wide characters such as emoji count as two."""
    return sum(2 if unicodedata.east_asian_width(char) in "WF" else 1 for char in text)


def split_row(line: str) -> list[str]:
    body = line.strip().removeprefix("|")
    if body.endswith("|") and not body.endswith("\\|"):
        body = body[:-1]
    return [cell.strip() for cell in UNESCAPED_PIPE.split(body)]


def is_table_line(line: str) -> bool:
    return line.lstrip().startswith("|") and line.rstrip().endswith("|")


def alignment(delimiter_cell: str) -> str:
    left, right = delimiter_cell.startswith(":"), delimiter_cell.endswith(":")
    if left and right:
        return "center"
    return "right" if right else "left" if left else "none"


def delimiter(align: str, width: int) -> str:
    if align == "center":
        return ":" + "-" * (width - 2) + ":"
    if align == "right":
        return "-" * (width - 1) + ":"
    if align == "left":
        return ":" + "-" * (width - 1)
    return "-" * width


def pad(text: str, width: int, align: str) -> str:
    gap = width - display_width(text)
    if align == "right":
        return " " * gap + text
    if align == "center":
        return " " * (gap // 2) + text + " " * (gap - gap // 2)
    return text + " " * gap


def format_block(lines: list[str]) -> list[str]:
    """Align one run of table-looking lines. Anything that is not a well-formed table is returned unchanged."""
    rows = [split_row(line) for line in lines]
    if len(rows) < 2 or not all(DELIMITER_CELL.match(cell) for cell in rows[1]):
        return lines
    columns = len(rows[0])
    if any(len(row) != columns for row in rows):
        return lines

    indent = lines[0][: len(lines[0]) - len(lines[0].lstrip())]
    aligns = [alignment(cell) for cell in rows[1]]
    content = rows[:1] + rows[2:]
    widths = [max(MIN_COLUMN_WIDTH, *(display_width(row[i]) for row in content)) for i in range(columns)]

    formatted = []
    for index, row in enumerate(rows):
        if index == 1:
            cells = [delimiter(aligns[i], widths[i]) for i in range(columns)]
        else:
            cells = [pad(row[i], widths[i], aligns[i]) for i in range(columns)]
        formatted.append(indent + "| " + " | ".join(cells) + " |")
    return formatted


def format_text(text: str) -> str:
    eol = "\r\n" if "\r\n" in text else "\n"
    out: list[str] = []
    block: list[str] = []
    fence: str | None = None

    def flush() -> None:
        out.extend(format_block(block))
        block.clear()

    for line in text.split(eol):
        marker = line.lstrip()[:3]
        if marker in FENCES and fence in (None, marker):
            flush()
            fence = None if fence else marker
            out.append(line)
        elif fence is None and is_table_line(line):
            block.append(line)
        else:
            flush()
            out.append(line)
    flush()
    return eol.join(out)


def tracked_markdown(root: Path) -> list[Path]:
    listing = subprocess.run(
        ["git", "ls-files", "*.md"], cwd=root, capture_output=True, text=True, check=True
    ).stdout
    return [root / name for name in listing.splitlines()]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("paths", nargs="*", type=Path, help="files to format (default: every tracked .md file)")
    parser.add_argument("--check", action="store_true", help="report unaligned files and exit 1 instead of rewriting")
    args = parser.parse_args(argv)

    changed = []
    for path in args.paths or tracked_markdown(Path.cwd()):
        original = path.read_bytes().decode("utf-8")
        formatted = format_text(original)
        if formatted != original:
            changed.append(path)
            if not args.check:
                path.write_bytes(formatted.encode("utf-8"))

    for path in changed:
        print(f"{'would reformat' if args.check else 'formatted'} {path}")
    return 1 if args.check and changed else 0


if __name__ == "__main__":
    sys.exit(main())
