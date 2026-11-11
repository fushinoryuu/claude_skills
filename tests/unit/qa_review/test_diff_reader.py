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
    assert json.loads(result.stdout)["changed_files"] == ["src/app.py", "old.py", "new/name.md"]
