"""Report which changed HTTP routes have no matching change to the OpenAPI or Swagger spec. A signal, not a verdict.

Runs only when the repo has a spec. A spec is a file named `openapi*` or `swagger*` with a .json,
.yaml or .yml extension, found in the working tree (the folder given with --root, the current folder
by default) or among the files of the change. A file in a test or fixture folder (test, tests,
__tests__, testdata, fixtures), node_modules, vendor or a build folder is never a spec, whether it is
searched for or changed by the change. A folder called spec or specs is not skipped. When there is
no spec, the status is `not_applicable`.

Reads a unified diff from a file or stdin. The routes come from `changed_interfaces.py`, so the same
limits apply: only changed lines are read, and only HTTP routes are compared. Flags, commands and
configuration keys are not described by an OpenAPI spec, so they are not checked here.

How a route is matched. A route matches when a line the diff adds to or removes from a spec file names
the same path. Parameters are written differently in code and in a spec (`<id>`, `<int:pk>`, `:id`,
`{id}`), so all of them are compared as `{}`. The spec path may carry a prefix the code does not know
(`/api/v1/orders` for a route `/orders`), so the end of the path is compared. A Rails `resources
orders` also matches `/orders/{id}`. The HTTP method is not compared, so a spec change for the
same path with another method counts as a match. The script cannot tell whether the spec change is
the right one.

Output is JSON on stdout. The exit code is 0 whenever the script ran, even when it could not tell.
Anything that goes wrong is reported in the output and never stops the review.

  {
    "status": "ok" | "not_applicable" | "no_input",
        "not_applicable": the repo has no spec, so there is nothing to compare
        "no_input":       no changed path was found in the input
    "spec_files": ["docs/openapi.yaml"],       specs found (at most 20)
    "spec_files_changed": ["docs/openapi.yaml"],   specs that are in the change
    "routes_changed": 3,                       how many changed routes were compared
    "routes_without_spec_change": [            routes with no matching spec change; check each one
      {"file": "src/orders.py", "route": "DELETE /orders/{id}", "change": "added", "line": 12,
       "reason": "..."}
    ],
    "routes_with_spec_change": [               routes whose path is named by a changed spec line
      {"file": "src/orders.py", "route": "GET /orders", "change": "modified", "line": 8,
       "spec": "docs/openapi.yaml"}
    ],
    "routes_not_compared": [                   routes with no path in the change to look for
      {"file": "src/orders.py", "route": "GET", "reason": "..."}
    ],
    "note": "..."                              present when there is something to know
  }
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path, PurePosixPath

sys.path.insert(0, str(Path(__file__).resolve().parent))  # the other scripts sit next to this one
import changed_interfaces
from diff_reader import changed_files, file_diffs, print_report, read_input

SPEC_EXTENSIONS = frozenset({".json", ".yaml", ".yml"})
SPEC_LIMIT = 20
FOLDER_LIMIT = 5000  # stop looking after this many folders, in case the script is run from a huge folder
SKIPPED_FOLDERS = frozenset(
    {".git", "node_modules", "vendor", "dist", "build", "target", ".venv", "venv", "__pycache__", ".tox", ".mypy_cache"}
) | changed_interfaces.FIXTURE_FOLDERS  # not spec or specs: a spec is often kept in one of those

_PATH_IN_LINE = re.compile(r"(?<![\w#.:/])/[\w\-.~%/{}<>:$]*")
_PARAM = re.compile(r"\{[^}/]*\}|<[^>/]*>|(?<=/):[\w\-]+|(?<=/)\$\{[^}/]*\}")


def is_spec(path: str) -> bool:
    pure = PurePosixPath(path.lower())
    return pure.suffix in SPEC_EXTENSIONS and pure.name.startswith(("openapi", "swagger"))


def in_skipped_folder(path: str) -> bool:
    """True when a folder above the file is a test, fixture, vendor or build folder."""
    return any(part.lower() in SKIPPED_FOLDERS for part in PurePosixPath(path).parts[:-1])


def normalize(path: str) -> str:
    """A path with every parameter written as {}, a leading slash and no trailing slash."""
    path = _PARAM.sub("{}", path.strip().strip("'\"`").split("?")[0])
    return "/" + path.strip("/")


def find_specs(root: Path) -> tuple[list[str], bool]:
    """Spec files under `root`, as forward-slash paths relative to it, sorted. True when the search stopped early."""
    found: list[str] = []
    for count, (folder, dirs, files) in enumerate(os.walk(root)):
        if count >= FOLDER_LIMIT:
            return sorted(found), True
        dirs[:] = sorted(d for d in dirs if d.lower() not in SKIPPED_FOLDERS)
        for name in sorted(files):
            if is_spec(name):
                found.append((Path(folder) / name).relative_to(root).as_posix())
    return sorted(found), False


def route_path(name: str) -> tuple[str, bool]:
    """The path of a route name like `GET /orders/{id}` or `resources orders`, and whether it is a resources route."""
    first, _, rest = name.partition(" ")
    if first.upper() in {m.upper() for m in changed_interfaces.HTTP_METHODS}:
        name = rest
    elif first in {"resources", "resource"}:
        return (normalize(rest), True) if rest else ("", True)
    elif first in changed_interfaces.LABELLED_WORDS:
        name = rest
    return (normalize(name), False) if name.strip() else ("", False)


def spec_paths(lines: list[str]) -> set[str]:
    """Every path-like string in these spec lines, normalized."""
    out: set[str] = set()
    for line in lines:
        for found in _PATH_IN_LINE.findall(line):
            found = found.rstrip(":")  # a YAML key: `/orders/{id}:`
            if len(found) > 1:
                out.add(normalize(found))
    return out


def matches(route: str, resources: bool, paths: set[str]) -> bool:
    for path in paths:
        if path == route or path.endswith(route):
            return True
        if resources and (path.startswith(route + "/") or (route + "/") in path):
            return True
    return False


def check(text: str, root: Path) -> dict:
    paths, _ = changed_files(text)
    report: dict = {
        "status": "ok",
        "spec_files": [],
        "spec_files_changed": [],
        "routes_changed": 0,
        "routes_without_spec_change": [],
        "routes_with_spec_change": [],
        "routes_not_compared": [],
    }
    if not paths:
        report["status"] = "no_input"
        report["note"] = "No changed file paths were found in the input. Compare the routes with the spec by hand."
        return report

    diffs = {d.path: d for d in file_diffs(text)}
    changed_specs = [p for p in paths if is_spec(p) and not in_skipped_folder(p)]
    in_tree, stopped = find_specs(root) if root.is_dir() else ([], False)
    specs = sorted({*in_tree, *(p for p in changed_specs if not (p in diffs and diffs[p].deleted))})
    if not specs:
        report["status"] = "not_applicable"
        report["note"] = "The repo has no OpenAPI or Swagger spec, so there is nothing to compare."
        if stopped:
            report["note"] += f" The search stopped after {FOLDER_LIMIT} folders, so run the script from the root of the repo."
        return report
    report["spec_files"] = specs[:SPEC_LIMIT]
    report["spec_files_changed"] = changed_specs

    # The path-like strings on changed spec lines, and on the unchanged lines next to them.
    changed_by_spec: dict[str, set[str]] = {}
    for spec in changed_specs:
        diff = diffs.get(spec)
        if diff is not None:
            changed_by_spec[spec] = spec_paths([x.text for x in diff.lines if x.kind != " "])
    context_paths: set[str] = set()
    for spec in changed_specs:
        diff = diffs.get(spec)
        if diff is not None:
            context_paths |= spec_paths([x.text for x in diff.lines if x.kind == " "])

    routes = [e for e in changed_interfaces.check(text)["interfaces"] if e["kind"] == "http_route"]
    report["routes_changed"] = len(routes)
    for entry in routes:
        route, resources = route_path(entry["name"])
        base = {"file": entry["file"], "route": entry["name"], "change": entry["change"], "line": entry["line"]}
        if route in ("", "/"):
            report["routes_not_compared"].append(
                {"file": entry["file"], "route": entry["name"], "reason": "the change shows no path for this route to look for"}
            )
            continue
        hit = next((spec for spec, found in changed_by_spec.items() if matches(route, resources, found)), None)
        if hit:
            report["routes_with_spec_change"].append({**base, "spec": hit})
        elif not changed_specs:
            report["routes_without_spec_change"].append({**base, "reason": "no spec file changed in this change"})
        elif matches(route, resources, context_paths):
            reason = "the path appears only on unchanged lines next to changed spec lines; check that its entry was updated"
            report["routes_without_spec_change"].append({**base, "reason": reason})
        else:
            reason = "a spec file changed, but its changed lines do not name this path"
            report["routes_without_spec_change"].append({**base, "reason": reason})

    notes = []
    if stopped:
        notes.append(f"The search for specs stopped after {FOLDER_LIMIT} folders; run the script from the root of the repo.")
    if len(specs) > SPEC_LIMIT:
        notes.append(f"{len(specs)} spec files were found; the first {SPEC_LIMIT} are listed.")
    if not routes:
        notes.append("No changed HTTP route was found in the change, so nothing was compared with the spec.")
    if notes:
        report["note"] = " ".join(notes)
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="openapi_changed.py",
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("input", nargs="?", help="a diff; read from stdin when omitted or '-'")
    parser.add_argument("--root", type=Path, default=Path(), help="the repo to search for a spec (default: the current folder)")
    args = parser.parse_args(argv)

    text, read_error = read_input(args.input)
    report = check(text, args.root)
    if read_error:
        report["note"] = f"{read_error} {report.get('note', '')}".strip()
    print_report(report)
    return 0


if __name__ == "__main__":
    sys.exit(main())
