"""List changed source files that have no matching test file in the same change. A signal for the reviewer, not a verdict.

Reads the change from a file or stdin. The input is either a unified diff (the changed paths are taken
from its headers) or a plain list of paths, one per line, such as `gh pr diff N --name-only`. A path
list cannot show that a file was deleted, so a deleted file may be reported as missing a test.

The script compares file names only. It never reads the tests, so it cannot say whether a test is
any good, and a test in a file with another name (a shared test file, say) is not seen as a match.
It sees only the change, not the project, so it cannot tell whether the project has tests at all: in
a project with none, every changed source file is listed as missing a test. The reviewer decides.

How a source file is matched. Each language has test-file patterns that contain `{name}`, which stands
for the source file's name without its extension, for example:
  python      **/test_{name}.py   **/{name}_test.py
  go          **/{name}_test.go
A changed test file matches when it fits a pattern and its `{name}` is the source file's name. Case,
`-`, `_` and `.` are ignored when names are compared. The folders must agree too, so that
tests/b/test_utils.py does not cover src/a/utils.py. Folders such as src, lib, test, tests, spec,
__tests__ and unit are ignored, and one folder path has to end with the other (a test with no folders
left, like tests/test_utils.py, agrees with every source file). Files under a folder called test,
tests, __tests__, spec, specs or e2e count as test files too, so they are never reported as source.
Documentation, configuration (including *.config.* and *.setup.* files), type declarations (.d.ts),
lock files, generated files and assets are not checked.

Options change the patterns. A pattern is a glob: `*` stays inside one folder, `**` crosses folders,
`?` is one character. A pattern without `{name}` only marks files as tests.
  --test-pattern GLOB   add a pattern, for example 'spec/{name}_spec.rb'. It applies to every source file (repeat for several)
  --no-default-patterns use only the patterns given with --test-pattern
  --source-ext .EXT     treat this extension as source code (repeat it for several)
  --project-patterns FILE  a file of patterns for one project (default: .claude/qa-review/test-patterns
                        in the current directory; a missing file is fine)

The project file has one glob per line, like --test-pattern. Blank lines and lines starting with # are
ignored, and a line like `source-ext: .gleam, .res` adds source extensions. The skill runs the script
from the root of the repo being reviewed, so a team commits this file once and every review uses it.

Output is JSON on stdout. The exit code is 0 whenever the script ran, even when it could not tell.
Anything that goes wrong is reported in the output and never stops the review.

  {
    "status": "ok" | "no_input" | "could_not_tell",
        "no_input":       no changed path was found in the input; look for the tests by hand
        "could_not_tell": there are source files, but none could be matched to a test by name
    "changed_files": ["src/app.py", "tests/test_app.py"],
    "missing_test_change": [          source files with no matching test file in the change
      {"file": "src/text.py", "language": "python", "expected_tests": ["**/test_text.py"],
       "same_name_tests_elsewhere": ["tests/b/test_text.py"]}    present only when a changed test has the
    ],                                                           same name but sits in another folder
    "has_test_change": [              source files with a matching test file in the change
      {"file": "src/app.py", "language": "python", "tests": ["tests/test_app.py"],
       "ambiguous_with": ["lib/app.py"]}                         present only when another source file with
    ],                                                           the same name matches the same test
    "test_files_changed": ["tests/test_app.py"],   every changed file that counts as a test
    "could_not_tell": [               source files the script cannot judge by name
      {"file": "src/lib.rs", "reason": "..."}
    ],
    "not_checked": [                  files that need no test: documentation, configuration, ...
      {"file": "README.md", "reason": "documentation"}
    ],
    "project_patterns_file": ".claude/qa-review/test-patterns",   present when a project file was read
    "note": "..."                     present when there is something to know
  }
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path, PurePosixPath
from typing import NamedTuple

_DIFF_HEADER = re.compile(r"^diff --git a/(.+?) b/(.+)$")
_OLD_FILE = re.compile(r"^--- a/(.+?)(?:\t.*)?$")
_NEW_FILE = re.compile(r"^\+\+\+ b/(.+?)(?:\t.*)?$")

TEST_FOLDERS = frozenset(
    {"test", "tests", "__tests__", "spec", "specs", "e2e", "testdata", "fixtures", "__fixtures__", "__snapshots__", "__mocks__"}
)
TEST_SUPPORT_FILES = frozenset({"conftest.py"})
# Folders that only say where code lives or what kind of test it is, so they do not help tell two modules apart.
STRUCTURE_FOLDERS = frozenset(
    {"src", "source", "sources", "lib", "main", "java", "kotlin", "test", "tests", "spec", "specs", "__tests__",
     "e2e", "unit", "integration", "functional", "it"}
)  # fmt: skip
DEFAULT_PROJECT_PATTERNS = Path(".claude") / "qa-review" / "test-patterns"


class Language(NamedTuple):
    name: str
    extensions: tuple[str, ...]
    patterns: tuple[str, ...]


LANGUAGES = (
    Language("python", (".py",), ("**/test_{name}.py", "**/{name}_test.py", "**/tests.py")),
    Language(
        "javascript/typescript",
        (".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs"),
        ("**/{name}.test.*", "**/{name}.spec.*", "**/__tests__/{name}.*"),
    ),
    Language(
        "java", (".java",), ("**/{name}Test.java", "**/{name}Tests.java", "**/{name}IT.java", "**/Test{name}.java")
    ),
    Language("kotlin", (".kt",), ("**/{name}Test.kt", "**/{name}Tests.kt")),
    Language("go", (".go",), ("**/{name}_test.go",)),
    Language("ruby", (".rb",), ("**/{name}_spec.rb", "**/{name}_test.rb", "**/test_{name}.rb")),
    Language("csharp", (".cs",), ("**/{name}Test.cs", "**/{name}Tests.cs")),
    Language("php", (".php",), ("**/{name}Test.php",)),
    Language("swift", (".swift",), ("**/{name}Tests.swift", "**/{name}Test.swift")),
)

# Source files that are known, but where the name says nothing about the tests.
NO_NAME_CONVENTION = {
    ".rs": "Rust usually keeps unit tests inside the source file, so a file name comparison says nothing. "
    "Look for a #[cfg(test)] block in the diff, or a file under tests/",
}

DOC_EXTENSIONS = frozenset({".md", ".mdx", ".rst", ".txt", ".adoc", ".org"})
DOC_NAMES = frozenset({"license", "licence", "notice", "authors", "codeowners", "changelog", "contributing"})
CONFIG_EXTENSIONS = frozenset(
    {".json", ".yaml", ".yml", ".toml", ".ini", ".cfg", ".conf", ".properties", ".env", ".xml", ".gradle", ".csproj", ".sln"}
)
CONFIG_NAMES = frozenset({"dockerfile", "makefile", "procfile", "gemfile", "rakefile", "justfile"})
ASSET_EXTENSIONS = frozenset(
    {".png", ".jpg", ".jpeg", ".gif", ".svg", ".ico", ".pdf", ".woff", ".woff2", ".ttf", ".eot", ".csv", ".tsv"}
)
LOCK_NAMES = frozenset({"go.sum", "npm-shrinkwrap.json"})
GENERATED_FOLDERS = frozenset({"node_modules", "vendor", "dist", "build", "generated", "__generated__"})
GENERATED_MARKERS = (".min.js", ".min.css", ".map", ".snap", "_pb2.py", "_pb2_grpc.py", ".pb.go", ".g.dart", ".generated.")
DOC_FOLDERS = frozenset({"docs", "doc"})
CONFIG_FILE_NAME = re.compile(r"\.(?:config|setup)\.[^.]+$")  # webpack.config.js, jest.setup.js


# --- reading the change ---


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


# --- patterns ---


def pattern_regex(pattern: str) -> re.Pattern[str]:
    """A glob turned into a regex. `{name}` becomes the group `name`, `*` stays in one folder, `**` crosses."""
    out = []
    i = 0
    named = False
    while i < len(pattern):
        if pattern.startswith("{name}", i):
            out.append("[^/]+?" if named else "(?P<name>[^/]+?)")
            named = True
            i += 6
        elif pattern.startswith("**/", i):
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
    return re.compile("".join(out) + r"\Z", re.IGNORECASE)


def same_name(a: str, b: str) -> bool:
    def normal(s: str) -> str:
        return re.sub(r"[-_.\s]", "", s).lower()

    return normal(a) == normal(b)


def extension(path: str) -> str:
    return PurePosixPath(path).suffix.lower()


def stem(path: str) -> str:
    return PurePosixPath(path).stem


def folder_key(path: str) -> list[str]:
    """The folders of a path that tell modules apart: structure folders are dropped, and `AppTests` becomes `app`."""
    key = []
    for folder in path.lower().split("/")[:-1]:
        for suffix in ("tests", "test"):
            if folder.endswith(suffix) and len(folder) > len(suffix):
                folder = folder[: -len(suffix)].rstrip("_-.")
                break
        if folder and folder not in STRUCTURE_FOLDERS:
            key.append(folder)
    return key


def folders_agree(source: str, test: str) -> bool:
    """True when the test could belong to the source file's module: one folder path ends with the other.

    A path with no telling folders (tests/test_utils.py) agrees with everything.
    """
    a, b = folder_key(source), folder_key(test)
    if not a or not b:
        return True
    short, long = sorted((a, b), key=len)
    return long[-len(short) :] == short


# --- sorting the files ---


def is_test_file(path: str, patterns: list[re.Pattern[str]]) -> bool:
    parts = path.lower().split("/")
    return (
        any(part in TEST_FOLDERS for part in parts[:-1])
        or parts[-1] in TEST_SUPPORT_FILES
        or any(rx.match(path) for rx in patterns)
    )


def not_checked_reason(path: str) -> str | None:
    """Why a file needs no test, or None when it might."""
    parts = path.lower().split("/")
    name, ext = parts[-1], extension(path)
    if name.endswith((".lock", "-lock.json", "-lock.yaml")) or name in LOCK_NAMES:
        return "lock file"
    if any(part in GENERATED_FOLDERS for part in parts[:-1]) or any(m in name for m in GENERATED_MARKERS):
        return "generated or bundled file"
    if ext in DOC_EXTENSIONS or name in DOC_NAMES or (len(parts) > 1 and parts[0] in DOC_FOLDERS):
        return "documentation"
    if ext in CONFIG_EXTENSIONS or name in CONFIG_NAMES or name.startswith(".") or CONFIG_FILE_NAME.search(name):
        return "configuration"
    if name.endswith(".d.ts"):
        return "type declarations"
    if ext in ASSET_EXTENSIONS:
        return "asset or data file"
    if name == "__init__.py":
        return "package marker"
    return None


def check(text: str, patterns: list[tuple[Language | None, list[str]]], source_extensions: set[str]) -> dict:
    """Sort the changed files and match each source file to a changed test file.

    `patterns` pairs a language (None for patterns from the command line, which apply to every source
    file) with its globs. `source_extensions` are the extra extensions to treat as source.
    """
    paths, deleted = changed_files(text)
    report: dict = {
        "status": "ok" if paths else "no_input",
        "changed_files": paths,
        "missing_test_change": [],
        "has_test_change": [],
        "test_files_changed": [],
        "could_not_tell": [],
        "not_checked": [],
    }
    if not paths:
        report["note"] = "No changed file paths were found in the input, so nothing could be checked. Look for the tests by hand."
        return report

    compiled = [(lang, glob, pattern_regex(glob)) for lang, globs in patterns for glob in globs]
    all_regexes = [rx for _, _, rx in compiled]
    known_source = {ext for language in LANGUAGES for ext in language.extensions}
    known_source |= set(NO_NAME_CONVENTION) | source_extensions

    tests = [p for p in paths if p not in deleted and is_test_file(p, all_regexes)]
    report["test_files_changed"] = tests
    judged = 0
    covered: dict[str, list[str]] = {}
    for path in paths:
        if path in tests:
            continue
        reason = "deleted" if path in deleted else not_checked_reason(path)
        if reason:
            report["not_checked"].append({"file": path, "reason": reason})
            continue
        ext = extension(path)
        if ext not in known_source:
            report["could_not_tell"].append({"file": path, "reason": f"unrecognized file type '{ext or path}'"})
            continue
        rules = [(lang, glob, rx) for lang, glob, rx in compiled if lang is None or ext in lang.extensions]
        rules = [r for r in rules if "{name}" in r[1]]
        if not rules:
            reason = NO_NAME_CONVENTION.get(ext, f"no test-file pattern for '{ext}' files; add one with --test-pattern")
            report["could_not_tell"].append({"file": path, "reason": reason})
            continue
        judged += 1
        name = stem(path)
        matches, elsewhere = [], []
        for test in tests:
            for _, _, rx in rules:
                found = rx.match(test)
                if found and same_name(found.group("name"), name):
                    (matches if folders_agree(path, test) else elsewhere).append(test)
                    break
        language = next((lang.name for lang, _, _ in rules if lang), "custom pattern")
        if matches:
            covered[path] = matches
            report["has_test_change"].append({"file": path, "language": language, "tests": matches})
        else:
            expected = [glob.replace("{name}", name) for _, glob, _ in rules]
            entry = {"file": path, "language": language, "expected_tests": expected}
            if elsewhere:
                entry["same_name_tests_elsewhere"] = elsewhere
            report["missing_test_change"].append(entry)

    for entry in report["has_test_change"]:  # one test claimed by several same-named source files
        shared = [
            other
            for other, other_tests in covered.items()
            if other != entry["file"]
            and same_name(stem(other), stem(entry["file"]))
            and set(other_tests) & set(entry["tests"])
        ]
        if shared:
            entry["ambiguous_with"] = shared

    notes = []
    if not judged and report["could_not_tell"]:
        report["status"] = "could_not_tell"
        notes.append("No changed source file could be matched to a test by name, so look for the tests by hand.")
    elif not judged:
        notes.append("No changed source files to check.")
    if report["missing_test_change"] and tests:
        notes.append(
            "Some test files changed but matched no source file by name. They may still cover the files listed as "
            "missing a test change, so read them before reporting a gap."
        )
    if any("ambiguous_with" in entry for entry in report["has_test_change"]):
        notes.append("A test that matches several source files of the same name may cover only one of them.")
    if notes:
        report["note"] = " ".join(notes)
    return report


def extensions_from(values: list[str]) -> set[str]:
    return {e.lower() if e.startswith(".") else f".{e.lower()}" for e in values if e}


def read_project_patterns(path: Path) -> tuple[list[str], set[str], str]:
    """Patterns and source extensions from a project file, and a problem to report ("" when there is none).

    A file that does not exist is fine and gives nothing.
    """
    if not path.is_file():
        return [], set(), ""
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError) as e:
        return [], set(), f"Could not read the project patterns file {path.as_posix()}: {e}."
    globs: list[str] = []
    extensions: list[str] = []
    for raw in lines:
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.lower().startswith("source-ext:"):
            extensions.extend(re.split(r"[,\s]+", line.partition(":")[2].strip()))
        else:
            globs.append(line)
    return globs, extensions_from(extensions), ""


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="missing_tests.py",
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("input", nargs="?", help="a diff or a list of paths; read from stdin when omitted or '-'")
    parser.add_argument(
        "--test-pattern", action="append", default=[], metavar="GLOB", help="a test-file pattern to add (repeatable)"
    )
    parser.add_argument(
        "--no-default-patterns", action="store_true", help="use only the patterns given with --test-pattern"
    )
    parser.add_argument(
        "--source-ext", action="append", default=[], metavar=".EXT", help="an extension to treat as source (repeatable)"
    )
    parser.add_argument(
        "--project-patterns",
        type=Path,
        default=DEFAULT_PROJECT_PATTERNS,
        metavar="FILE",
        help=f"a file of patterns for one project (default: {DEFAULT_PROJECT_PATTERNS.as_posix()} in the current directory)",
    )
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

    project_globs, project_extensions, project_problem = read_project_patterns(args.project_patterns)
    custom = [*project_globs, *args.test_pattern]
    patterns: list[tuple[Language | None, list[str]]] = []
    if not args.no_default_patterns:
        patterns.extend((language, list(language.patterns)) for language in LANGUAGES)
    if custom:
        patterns.append((None, custom))
    extensions = extensions_from(args.source_ext) | project_extensions

    report = check(text, patterns, extensions)
    if args.project_patterns.is_file() and not project_problem:
        report["project_patterns_file"] = args.project_patterns.as_posix()
    problems = " ".join(p for p in (read_error, project_problem) if p)
    if problems:
        report["note"] = f"{problems} {report.get('note', '')}".strip()
    sys.stdout.reconfigure(encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
