"""List the externally visible interfaces a diff touches. A signal for the reviewer, not a verdict.

Reads a unified diff from a file or stdin and gives a best-effort list of HTTP routes, command-line
flags and commands, configuration keys, and schema files that the change adds, removes or modifies.
The reviewer uses it to check that each one is documented (Step 7). It never decides that a change
is breaking or that the documentation is right.

What it looks at. Only the lines the diff changes, plus the few lines after each one, so that a call
split over several lines is still read. It does not follow the code, so a new parameter on a route
handler, or a changed default that sits on an untouched line, is not seen. Test files are skipped. A
schema or API spec file is skipped only in a test or fixture folder (test, tests, __tests__, testdata,
fixtures), because a folder called spec or specs often holds the real spec.
  http_route   framework routes: Flask, FastAPI, Django urls.py, Express and similar, NestJS, Spring,
               JAX-RS, Go (net/http, gin, echo, chi), Rails routes.rb, ASP.NET, Laravel, Actix, axum
  cli          flags and commands: argparse, click, commander, yargs, cobra and the Go flag package,
               picocli, clap, System.CommandLine
  config_key   environment variables read in code, and keys in configuration files (.env files, ini,
               cfg, conf and properties files, and json, yaml or toml files named config, settings,
               application or appsettings, or kept in a config folder)
  schema_file  .proto, .graphql, .avsc, .xsd, .wsdl, .prisma, .thrift, *.schema.json, schema.json,
               and OpenAPI or Swagger files. Reported once per file, by name
A route is named like `GET /orders/{id}`; a flag like `--exclude`; a command like `command build`.

A plain list of paths (such as `gh pr diff N --name-only`) has no lines to read, so only schema files
can be recognized from it, by name.

Output is JSON on stdout. The exit code is 0 whenever the script ran, even when it could not tell.
Anything that goes wrong is reported in the output and never stops the review.

  {
    "status": "ok" | "no_input" | "could_not_tell",
        "no_input":       no changed path was found in the input; look at the interfaces by hand
        "could_not_tell": nothing was found, and the changed files are of a kind the script does
                          not know (or the input has no lines to read); look by hand
    "changed_files": ["src/app.py", "docs/api.md"],
    "interfaces": [                   what the change touches, in file and line order
      {"file": "src/app.py", "kind": "http_route", "name": "GET /orders/{id}",
       "change": "added" | "removed" | "modified" | "changed",
       "line": 12}                    the line in the new file, or in the old file for "removed";
    ],                                null for a schema file and for "changed"
    "could_not_tell": [               changed files of a kind the script does not know
      {"file": "src/lib.gleam", "reason": "..."}
    ],
    "not_checked": [                  files it skipped on purpose: tests, documentation, assets
      {"file": "tests/test_app.py", "reason": "test file"}
    ],
    "note": "..."                     present when there is something to know
  }

"modified" means the same interface is on a removed line and an added line of the same file, for
example a route whose handler or options changed. "changed" is used for a schema file in a path list.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path, PurePosixPath
from typing import NamedTuple

sys.path.insert(0, str(Path(__file__).resolve().parent))  # diff_reader.py sits next to this script
from diff_reader import (
    DiffLine,
    FileDiff,
    changed_files,
    file_diffs,
    print_report,
    read_input,
)

LOOKAHEAD = 4  # a call may be split over this many lines
HTTP_METHODS = frozenset({"get", "post", "put", "patch", "delete", "head", "options", "trace"})
LABELLED_WORDS = frozenset({"resources", "resource", "namespace", "scope", "match", "mount", "websocket"})

# Folders of test data: a schema or spec file in one is a fixture, not an interface of the project.
FIXTURE_FOLDERS = frozenset({"test", "tests", "__tests__", "testdata", "fixtures", "__fixtures__", "__mocks__"})
# Folders of test code. `spec` and `specs` also hold real API specs, so they are not in FIXTURE_FOLDERS.
TEST_FOLDERS = FIXTURE_FOLDERS | {"spec", "specs", "e2e"}
TEST_FILE = re.compile(
    r"^(?:test_.*\.py|.*_test\.(?:py|go|rb)|.*\.(?:test|spec)\.\w+|.*(?:Test|Tests|IT)\.(?:java|kt|cs|php|swift))$"
)
DOC_EXTENSIONS = frozenset({".md", ".mdx", ".rst", ".txt", ".adoc", ".org"})
DATA_EXTENSIONS = frozenset(
    {".json", ".yaml", ".yml", ".toml", ".xml", ".csv", ".tsv", ".lock", ".svg", ".png", ".jpg", ".jpeg", ".gif", ".ico"}
    | {".pdf", ".woff", ".woff2", ".ttf", ".map", ".snap", ".sql", ".html", ".css", ".scss", ".sh", ".ps1", ".bat"}
)  # fmt: skip

SCHEMA_EXTENSIONS = frozenset({".proto", ".graphql", ".gql", ".avsc", ".xsd", ".wsdl", ".prisma", ".thrift", ".smithy"})
SCHEMA_NAMES = frozenset({"schema.json", "schema.yaml", "schema.yml", "schema.graphql"})
CONFIG_PLAIN_EXTENSIONS = frozenset({".ini", ".cfg", ".conf", ".properties"})
CONFIG_DATA_EXTENSIONS = frozenset({".json", ".yaml", ".yml", ".toml"})
CONFIG_FOLDERS = frozenset({"config", "configs", "conf", "settings"})
CONFIG_STEMS = ("config", "settings", "application", "appsettings")
# Tool and build configuration is not an interface of the project.
NOT_CONFIG_NAMES = frozenset(
    {"package.json", "package-lock.json", "tsconfig.json", "composer.json", "pyproject.toml", "cargo.toml", "setup.cfg",
     "tox.ini", "pytest.ini", "mypy.ini", ".flake8", ".editorconfig", "renovate.json", "mkdocs.yml", "mkdocs.yaml"}
)  # fmt: skip
NOT_CONFIG_PARTS = ("docker-compose", ".github/", ".gitlab", "node_modules/", ".vscode/", ".eslintrc", ".prettierrc")
NOT_CONFIG_STEM = re.compile(r"(?:^|\.)(?:tsconfig|jest|vite|webpack|babel|eslint|prettier|rollup|karma)[.\-]|\.config\.")

PY = frozenset({".py"})
JS = frozenset({".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs"})
JVM = frozenset({".java", ".kt"})
GO = frozenset({".go"})
RUBY = frozenset({".rb"})
CSHARP = frozenset({".cs"})
PHP = frozenset({".php"})
RUST = frozenset({".rs"})
CODE_EXTENSIONS = PY | JS | JVM | GO | RUBY | CSHARP | PHP | RUST

_STRINGS = r"(?P<names>(?:[\"'][^\"']+[\"']\s*,?\s*){1,3})"  # one to three quoted names, as in ("-v", "--verbose")
_DQ_STRINGS = r"(?P<names>(?:\"[^\"]+\"\s*,?\s*){1,3})"


class Rule(NamedTuple):
    kind: str
    extensions: frozenset[str]
    pattern: re.Pattern[str]
    file_name: re.Pattern[str] | None = None  # when set, the rule applies only to files with a matching path


def rule(kind: str, extensions: frozenset[str], pattern: str, file_name: str | None = None, flags: int = 0) -> Rule:
    return Rule(kind, extensions, re.compile(pattern, flags), re.compile(file_name) if file_name else None)


HTTP = "http_route"
CLI = "cli"
CONFIG = "config_key"

RULES: tuple[Rule, ...] = (
    # --- HTTP routes ---
    rule(HTTP, PY, r"@\w+(?:\.\w+)*\.(?P<method>route|api_route|websocket|get|post|put|patch|delete|head|options)\(\s*[rbf]?[\"'](?P<path>[^\"']*)[\"']"),
    rule(HTTP, PY, r"\b(?:re_)?path\(\s*r?[\"'](?P<path>[^\"']*)[\"']", file_name=r"(?:^|/)urls\.py$"),
    rule(HTTP, JS, r"\b\w*(?:app|router|server|fastify|routes?)\w*\.(?P<method>get|post|put|patch|delete|head|options|all|use|route)\(\s*[\"'`](?P<path>/[^\"'`]*)[\"'`]", flags=re.IGNORECASE),
    rule(HTTP, JS, r"@(?P<method>Get|Post|Put|Patch|Delete|Head|Options|All)\(\s*(?:[\"'`](?P<path>[^\"'`]*)[\"'`])?\s*\)"),
    rule(HTTP, JS, r"@Controller\(\s*[\"'`](?P<path>[^\"'`]*)[\"'`]"),
    rule(HTTP, JVM, r"@(?P<method>Get|Post|Put|Patch|Delete|Request)Mapping\(\s*(?:(?:value|path)\s*=\s*)?\{?\s*\"(?P<path>[^\"]*)\""),
    rule(HTTP, JVM, r"@(?P<method>Get|Post|Put|Patch|Delete|Request)Mapping(?!\w|\()"),
    rule(HTTP, JVM, r"@Path\(\s*\"(?P<path>[^\"]*)\"\s*\)"),
    rule(HTTP, GO, r"\.(?P<method>Handle|HandleFunc)\(\s*\"(?P<path>[^\"]+)\""),
    rule(HTTP, GO, r"\.(?P<method>GET|POST|PUT|PATCH|DELETE|HEAD|OPTIONS|Get|Post|Put|Patch|Delete|Head|Options)\(\s*\"(?P<path>/[^\"]*)\""),
    rule(HTTP, RUBY, r"^\s*(?P<method>get|post|put|patch|delete|match|resources|resource|namespace|scope|mount)\b\s*\(?\s*[:'\"]?(?P<path>[\w/:\-.*]+)", file_name=r"(?:^|/)routes[^/]*\.rb$"),
    rule(HTTP, CSHARP, r"\[(?P<method>Http(?:Get|Post|Put|Patch|Delete|Head|Options)|Route)(?:\(\s*\"(?P<path>[^\"]*)\"[^)]*\))?\]"),
    rule(HTTP, CSHARP, r"\.Map(?P<method>Get|Post|Put|Patch|Delete)\(\s*\"(?P<path>[^\"]*)\""),
    rule(HTTP, PHP, r"Route::(?P<method>get|post|put|patch|delete|any|match|resource|apiResource)\(\s*['\"](?P<path>[^'\"]+)"),
    rule(HTTP, RUST, r"#\[(?P<method>get|post|put|delete|patch)\(\s*\"(?P<path>[^\"]+)\""),
    rule(HTTP, RUST, r"\.route\(\s*\"(?P<path>[^\"]+)\""),
    # --- command-line flags and commands ---
    rule(CLI, PY, r"\.add_argument\(\s*" + _STRINGS),
    rule(CLI, PY, r"@\w+(?:\.\w+)*\.(?:option|argument)\(\s*" + _STRINGS),
    rule(CLI, PY, r"\.add_parser\(\s*[\"'](?P<cmd>[^\"']+)[\"']"),
    rule(CLI, PY, r"@\w+(?:\.\w+)*\.(?:command|group)\(\s*[\"'](?P<cmd>[^\"']+)[\"']"),
    rule(CLI, JS, r"\.(?:option|requiredOption)\(\s*[\"'`](?P<names>-[^\"'`]+)[\"'`]"),
    rule(CLI, JS, r"\.option\(\s*[\"'`](?P<names>[\w-]+)[\"'`]\s*,\s*\{"),
    rule(CLI, JS, r"\.command\(\s*[\"'`](?P<cmd>[^\"'`]+)[\"'`]"),
    rule(CLI, GO, r"\b(?:Flags\(\)|PersistentFlags\(\)|flag)\.(?:String|Bool|Int|Int64|Uint|Float64|Duration|StringSlice|StringArray|Var)\w*\(\s*(?:&[\w.]+,\s*)?\"(?P<names>[^\"]+)\""),
    rule(CLI, GO, r"\bUse:\s*\"(?P<cmd>[^\"]+)\""),
    rule(CLI, JVM, r"@Option\(\s*names\s*=\s*\{?\s*" + _DQ_STRINGS),
    rule(CLI, JVM, r"@Command\(\s*name\s*=\s*\"(?P<cmd>[^\"]+)\""),
    rule(CLI, RUST, r"\bArg::new\(\s*\"(?P<names>[^\"]+)\""),
    rule(CLI, RUST, r"\b(?:Command|App)::new\(\s*\"(?P<cmd>[^\"]+)\""),
    rule(CLI, CSHARP, r"new\s+(?:Option|Argument)(?:<[^>]+>)?\(\s*" + _DQ_STRINGS),
    rule(CLI, CSHARP, r"new\s+Command\(\s*\"(?P<cmd>[^\"]+)\""),
    # --- configuration read in code ---
    rule(CONFIG, PY, r"\bos\.environ(?:\.get)?\s*[\[(]\s*[\"'](?P<var>[^\"']+)[\"']"),
    rule(CONFIG, PY, r"\bos\.getenv\(\s*[\"'](?P<var>[^\"']+)[\"']"),
    rule(CONFIG, JS, r"\bprocess\.env\.(?P<var>[A-Za-z_]\w*)"),
    rule(CONFIG, JS, r"\bprocess\.env\[\s*[\"'`](?P<var>[^\"'`]+)"),
    rule(CONFIG, JS, r"\bimport\.meta\.env\.(?P<var>[A-Za-z_]\w*)"),
    rule(CONFIG, GO, r"\bos\.(?:Getenv|LookupEnv)\(\s*\"(?P<var>[^\"]+)\""),
    rule(CONFIG, JVM, r"\bSystem\.getenv\(\s*\"(?P<var>[^\"]+)\""),
    rule(CONFIG, JVM, r"@Value\(\s*\"\$\{(?P<var>[^}:\"]+)"),
    rule(CONFIG, RUBY, r"\bENV(?:\.fetch)?\s*[\[(]\s*[\"'](?P<var>[^\"']+)[\"']"),
    rule(CONFIG, CSHARP, r"Environment\.GetEnvironmentVariable\(\s*\"(?P<var>[^\"]+)\""),
    rule(CONFIG, PHP, r"\bgetenv\(\s*['\"](?P<var>[^'\"]+)"),
    rule(CONFIG, PHP, r"\$_ENV\[\s*['\"](?P<var>[^'\"]+)"),
    rule(CONFIG, RUST, r"\benv::var\(\s*\"(?P<var>[^\"]+)\""),
)  # fmt: skip

# A key at the start of a line in a configuration file: KEY=value, key: value, "key": value
CONFIG_FILE_KEY = re.compile(r"^\s*(?:export\s+)?[\"']?(?P<var>[A-Za-z_][\w.\-]*)[\"']?\s*[:=]")
COMMENT_STARTS = ("//", "/*", "*", ";", "<!--")


# --- what kind of file is it ---


def is_test_file(path: str, folders: frozenset[str] = TEST_FOLDERS) -> bool:
    """A test file by its folder (one of `folders`) or by its name."""
    parts = PurePosixPath(path).parts
    return any(p.lower() in folders for p in parts[:-1]) or bool(TEST_FILE.match(parts[-1])) or parts[-1] == "conftest.py"


def is_schema_file(path: str) -> bool:
    name = PurePosixPath(path).name.lower()
    suffix = PurePosixPath(name).suffix
    if suffix in SCHEMA_EXTENSIONS or name in SCHEMA_NAMES or name.endswith((".schema.json", ".schema.yaml", ".schema.yml")):
        return True
    return suffix in CONFIG_DATA_EXTENSIONS and name.startswith(("openapi", "swagger"))


def is_config_file(path: str) -> bool:
    lowered = path.lower()
    pure = PurePosixPath(lowered)
    name, suffix = pure.name, pure.suffix
    if name in NOT_CONFIG_NAMES or any(part in lowered for part in NOT_CONFIG_PARTS) or NOT_CONFIG_STEM.search(name):
        return False
    if name == ".env" or name.startswith(".env.") or name.endswith(".env"):
        return True
    if suffix in CONFIG_PLAIN_EXTENSIONS:
        return True
    if suffix in CONFIG_DATA_EXTENSIONS and not is_schema_file(path):
        return pure.stem.startswith(CONFIG_STEMS) or any(p in CONFIG_FOLDERS for p in pure.parts[:-1])
    return False


# --- finding interfaces in the lines of one file ---


def _method_prefix(word: str) -> str:
    word = word.lower().removeprefix("http")
    if word in HTTP_METHODS:
        return word.upper() + " "
    if word in LABELLED_WORDS:
        return word + " "
    return ""


def _flag(names: str) -> str:
    quoted = re.findall(r"[\"']([^\"']+)[\"']", names) if re.search(r"[\"']", names) else [names]
    tokens = [t for q in quoted for t in re.split(r"[\s,|]+", q.strip()) if t and not t.startswith(("<", "["))]
    return next((t for t in tokens if t.startswith("--")), tokens[0] if tokens else "")


def interface_name(m: re.Match[str]) -> str:
    groups = m.groupdict()
    if groups.get("cmd"):
        return "command " + groups["cmd"].split()[0]
    if groups.get("names"):
        return _flag(groups["names"])
    if groups.get("var"):
        return groups["var"]
    return (_method_prefix(groups.get("method") or "") + (groups.get("path") or "")).strip()


def _comment(text: str) -> bool:
    stripped = text.strip()
    return stripped.startswith(COMMENT_STARTS) or (stripped.startswith("#") and not stripped.startswith("#["))


def _found(side: list[DiffLine], kind: str, rules: list[Rule], in_config_file: bool) -> dict[tuple[str, str], int]:
    """The (kind, name) of every interface that starts on a line of this kind, with its line number."""
    found: dict[tuple[str, str], int] = {}
    for i, line in enumerate(side):
        first = line.text.strip()
        if line.kind != kind or not first or (_comment(line.text) and not in_config_file):
            continue
        if in_config_file:
            if first.startswith(("#", ";", "[")) or _comment(line.text):
                continue
            m = CONFIG_FILE_KEY.match(line.text)
            if m:
                found.setdefault((CONFIG, m["var"]), line.number)
            continue
        window = " ".join(x.text.strip() for x in side[i : i + LOOKAHEAD])
        for r in rules:
            for m in r.pattern.finditer(window):
                name = interface_name(m)
                if m.start() < len(first) and name:
                    found.setdefault((r.kind, name), line.number)
    return found


def scan_file(diff: FileDiff) -> list[dict]:
    """The interfaces one changed file touches."""
    suffix = PurePosixPath(diff.path).suffix.lower()
    in_config_file = is_config_file(diff.path)
    rules = [
        r
        for r in RULES
        if suffix in r.extensions and (r.file_name is None or r.file_name.search(diff.path)) and not in_config_file
    ]
    if not rules and not in_config_file:
        return []
    new_side = [x for x in diff.lines if x.kind != "-"]
    old_side = [x for x in diff.lines if x.kind != "+"]
    added = _found(new_side, "+", rules, in_config_file)
    removed = _found(old_side, "-", rules, in_config_file)
    out = []
    for key in sorted({*added, *removed}, key=lambda k: (added.get(k) or removed[k], k)):
        change = "modified" if key in added and key in removed else "added" if key in added else "removed"
        out.append({"file": diff.path, "kind": key[0], "name": key[1], "change": change, "line": added.get(key) or removed[key]})
    return out


# --- the report ---


def _schema_change(diff: FileDiff | None) -> str:
    if diff is None:
        return "changed"
    if diff.deleted:
        return "removed"
    if diff.lines and all(x.kind == "+" for x in diff.lines):
        return "added"
    return "modified"


def check(text: str) -> dict:
    paths, _ = changed_files(text)
    diffs = {d.path: d for d in file_diffs(text)}
    report: dict = {"status": "ok", "changed_files": paths, "interfaces": [], "could_not_tell": [], "not_checked": []}
    if not paths:
        report["status"] = "no_input"
        report["note"] = "No changed file paths were found in the input. Look at the interfaces by hand."
        return report

    has_lines = any(d.lines for d in diffs.values())
    looked_at = 0  # files whose kind the script knows and could read
    for path in paths:
        suffix = PurePosixPath(path).suffix.lower()
        diff = diffs.get(path)
        schema = is_schema_file(path)
        if is_test_file(path, FIXTURE_FOLDERS if schema else TEST_FOLDERS):  # a spec/ or specs/ folder can hold a real spec
            report["not_checked"].append({"file": path, "reason": "test file"})
        elif schema:
            looked_at += 1
            report["interfaces"].append(
                {"file": path, "kind": "schema_file", "name": PurePosixPath(path).name, "change": _schema_change(diff), "line": None}
            )
        elif suffix in DOC_EXTENSIONS:
            report["not_checked"].append({"file": path, "reason": "documentation"})
        elif suffix in CODE_EXTENSIONS or is_config_file(path):
            if has_lines:
                looked_at += 1
                if diff is not None:
                    report["interfaces"].extend(scan_file(diff))
            else:
                report["could_not_tell"].append({"file": path, "reason": "the input has no diff lines to read"})
        elif suffix in DATA_EXTENSIONS or not suffix:
            report["not_checked"].append({"file": path, "reason": "data, asset or file with no known interface"})
        else:
            report["could_not_tell"].append({"file": path, "reason": f"the script has no rules for {suffix} files"})

    # Schema files come first in the list above; put the whole list in file and line order.
    order = {p: i for i, p in enumerate(paths)}
    report["interfaces"].sort(key=lambda e: (order[e["file"]], e["line"] or 0, e["name"]))

    notes = []
    if not report["interfaces"]:
        if report["could_not_tell"] and not looked_at:
            report["status"] = "could_not_tell"
            notes.append("The script could not tell what the changed files expose. Look at the interfaces by hand.")
        elif looked_at:
            notes.append("No interface was found in the changed lines. The script reads only the lines the diff changes.")
        else:
            notes.append("Only documentation, data, assets or test files changed, so there is no interface to list.")
    if not has_lines and any(s for s in (PurePosixPath(p).suffix.lower() for p in paths) if s in CODE_EXTENSIONS):
        notes.append("The input is a list of paths and not a diff, so routes, flags and config keys could not be read.")
    if notes:
        report["note"] = " ".join(notes)
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="changed_interfaces.py",
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("input", nargs="?", help="a diff; read from stdin when omitted or '-'")
    args = parser.parse_args(argv)

    text, read_error = read_input(args.input)
    report = check(text)
    if read_error:
        report["note"] = f"{read_error} {report.get('note', '')}".strip()
    print_report(report)
    return 0


if __name__ == "__main__":
    sys.exit(main())
