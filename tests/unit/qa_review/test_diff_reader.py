import ast
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[3] / "skills" / "qa-review" / "scripts"

# The skill folder name has a hyphen, so the module is loaded from its path, not imported by name.
_spec = importlib.util.spec_from_file_location("diff_reader", SCRIPTS / "diff_reader.py")
dr = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(dr)

GIT_DIFF = """\
diff --git a/src/app.py b/src/app.py
index 111..222 100644
--- a/src/app.py
+++ b/src/app.py
@@ -1 +1 @@
-a
+b
diff --git a/old.py b/old.py
deleted file mode 100644
index 333..000
--- a/old.py
+++ /dev/null
@@ -1 +0,0 @@
-x
diff --git a/old.md b/new/name.md
similarity index 90%
rename from old.md
rename to new/name.md
"""


# --- reading the change ---


def test_a_git_diff_gives_the_new_paths_and_the_deleted_ones():
    paths, deleted = dr.changed_files(GIT_DIFF)
    assert paths == ["src/app.py", "old.py", "new/name.md"]
    assert deleted == {"old.py"}


def test_a_diff_without_git_headers_is_read_from_the_file_lines():
    diff = "--- a/x.py\t2026-01-01\n+++ b/x.py\t2026-01-02\n@@ -1 +1 @@\n-a\n+b\n--- a/gone.py\n+++ /dev/null\n@@ -1 +0,0 @@\n-a\n"
    paths, deleted = dr.changed_files(diff)
    assert paths == ["x.py", "gone.py"]
    assert deleted == {"gone.py"}


def test_a_plain_list_of_paths_is_cleaned_and_deduplicated():
    paths, deleted = dr.changed_files("# changed files\n./src/app.py\n\nsrc\\win.py\nsrc/app.py\n")
    assert paths == ["src/app.py", "src/win.py"]
    assert deleted == set()


@pytest.mark.parametrize("text", ["", "\n\n", "@@ -1 +1 @@\n-a\n+b\n", "\x00\x01 binary �"])
def test_empty_and_malformed_input_gives_no_paths(text):
    assert dr.changed_files(text) == ([], set())


def test_changed_paths_is_the_path_half_of_changed_files():
    assert dr.changed_paths(GIT_DIFF) == dr.changed_files(GIT_DIFF)[0]


# --- reading the lines ---

LINES_DIFF = """\
diff --git a/src/app.py b/src/app.py
index 111..222 100644
--- a/src/app.py
+++ b/src/app.py
@@ -3,4 +3,4 @@ def f():
 keep
-old
-- not a header
+new
+new two
 tail
\\ No newline at end of file
diff --git a/old.py b/old.py
deleted file mode 100644
--- a/old.py
+++ /dev/null
@@ -1 +0,0 @@
-x
"""


def lines_of(diff):
    return [(line.kind, line.number, line.text) for line in diff.lines]


def test_file_diffs_gives_each_file_with_its_numbered_lines():
    app, old = dr.file_diffs(LINES_DIFF)
    assert (app.path, app.deleted) == ("src/app.py", False)
    assert lines_of(app) == [
        (" ", 3, "keep"),
        ("-", 4, "old"),
        ("-", 5, "- not a header"),
        ("+", 4, "new"),
        ("+", 5, "new two"),
        (" ", 6, "tail"),
    ]
    assert (old.path, old.deleted) == ("old.py", True)
    assert lines_of(old) == [("-", 1, "x")]


def test_a_removed_line_that_looks_like_a_file_header_is_still_a_line():
    diff = "diff --git a/a.sql b/a.sql\n--- a/a.sql\n+++ b/a.sql\n@@ -1,2 +1,1 @@\n--- a comment\n+x\n y\n"
    (only,) = dr.file_diffs(diff)
    assert [line.kind for line in only.lines] == ["-", "+", " "]


def test_a_diff_without_git_headers_is_split_by_its_file_lines():
    diff = "--- a/x.py\t2026-01-01\n+++ b/x.py\t2026-01-02\n@@ -1 +1 @@\n-a\n+b\n--- a/y.py\n+++ b/y.py\n@@ -1 +1 @@\n-c\n+d\n"
    first, second = dr.file_diffs(diff)
    assert (first.path, second.path) == ("x.py", "y.py")
    assert lines_of(second) == [("-", 1, "c"), ("+", 1, "d")]


def test_a_new_file_has_only_added_lines():
    diff = "diff --git a/n.py b/n.py\nnew file mode 100644\n--- /dev/null\n+++ b/n.py\n@@ -0,0 +1,2 @@\n+a\n+b\n"
    (new,) = dr.file_diffs(diff)
    assert lines_of(new) == [("+", 1, "a"), ("+", 2, "b")]


def test_a_hunk_shorter_than_it_says_does_not_swallow_the_next_file():
    diff = "diff --git a/a.py b/a.py\n--- a/a.py\n+++ b/a.py\n@@ -1,3 +1,3 @@\n-a\n+b\ndiff --git a/c.py b/c.py\n--- a/c.py\n+++ b/c.py\n@@ -1 +1 @@\n-c\n+d\n"
    first, second = dr.file_diffs(diff)
    assert (first.path, second.path) == ("a.py", "c.py")
    assert lines_of(second) == [("-", 1, "c"), ("+", 1, "d")]


def test_a_blank_context_line_without_its_space_is_kept():
    diff = "diff --git a/a.py b/a.py\n--- a/a.py\n+++ b/a.py\n@@ -1,3 +1,3 @@\n a\n\n-b\n+c\n"
    (only,) = dr.file_diffs(diff)
    assert lines_of(only) == [(" ", 1, "a"), (" ", 2, ""), ("-", 3, "b"), ("+", 3, "c")]


@pytest.mark.parametrize("text", ["", "src/app.py\nsrc/util.py\n", "@@ -1 +1 @@\n-a\n+b\n", "\x00\x01 binary �"])
def test_text_without_files_gives_no_file_diffs(text):
    assert dr.file_diffs(text) == []


def test_a_truncated_diff_never_raises():
    for cut in range(len(LINES_DIFF)):
        dr.file_diffs(LINES_DIFF[:cut])


# --- reading the input ---


def test_read_input_reads_a_file(tmp_path):
    path = tmp_path / "in.diff"
    path.write_text("src/app.py\n", encoding="utf-8")
    assert dr.read_input(str(path)) == ("src/app.py\n", "")


def test_read_input_reports_a_missing_file_instead_of_raising(tmp_path):
    text, problem = dr.read_input(str(tmp_path / "missing.diff"))
    assert text == ""
    assert problem.startswith("Could not read the input")


def test_read_input_reads_stdin_for_a_dash_or_none(monkeypatch):
    class FakeStdin:
        class buffer:
            @staticmethod
            def read():
                return b"src/app.py\xff\n"

    monkeypatch.setattr(dr.sys, "stdin", FakeStdin)
    assert dr.read_input("-")[0] == "src/app.py�\n"
    assert dr.read_input(None)[0] == "src/app.py�\n"


def test_print_report_prints_json(capsys):
    dr.print_report({"status": "ok", "name": "café"})
    assert json.loads(capsys.readouterr().out) == {"status": "ok", "name": "café"}


# --- the scripts that share the module ---

SCRIPT_FILES = sorted(p for p in SCRIPTS.glob("*.py"))


@pytest.mark.parametrize("script", SCRIPT_FILES, ids=lambda p: p.name)
def test_a_script_imports_only_the_standard_library_and_its_siblings(script):
    siblings = {p.stem for p in SCRIPTS.glob("*.py")}
    tree = ast.parse(script.read_text(encoding="utf-8"))
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported |= {alias.name.split(".")[0] for alias in node.names}
        elif isinstance(node, ast.ImportFrom):
            imported.add(node.module.split(".")[0])
    assert imported <= set(sys.stdlib_module_names) | siblings


COMMANDS = [p for p in SCRIPT_FILES if p.stem != "diff_reader"]


@pytest.mark.parametrize("script", COMMANDS, ids=lambda p: p.name)
def test_a_script_runs_from_another_folder(script, tmp_path):
    """The skill runs `python3 ${CLAUDE_SKILL_DIR}/scripts/<name>.py` from the repo being reviewed."""
    result = subprocess.run(
        [sys.executable, str(script)], input=GIT_DIFF, capture_output=True, text=True, cwd=tmp_path, check=False
    )
    assert result.returncode == 0, result.stderr
    assert "status" in json.loads(result.stdout)
