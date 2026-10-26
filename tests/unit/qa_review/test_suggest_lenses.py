import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[3] / "skills" / "qa-review" / "scripts" / "suggest_lenses.py"

# The skill folder name has a hyphen, so the script is loaded from its path, not imported by name.
_spec = importlib.util.spec_from_file_location("suggest_lenses", SCRIPT)
sl = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(sl)


def lens_text(name, paths='["**/*.sql"]', touches="database changes", description="Checks for a thing."):
    return (
        f"---\nname: {name}\ndescription: {description}\napplies_when:\n"
        f'  paths: {paths}\n  touches: "{touches}"\n---\n\n# {name}\n'
    )


def write_lens(folder: Path, name: str, **kwargs) -> Path:
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{name}.md"
    path.write_text(lens_text(name, **kwargs), encoding="utf-8")
    return path


# --- reading the change ---

GIT_DIFF = """\
diff --git a/src/app.py b/src/app.py
index 1..2 100644
--- a/src/app.py
+++ b/src/app.py
@@ -1 +1 @@
-x
+y
diff --git a/old/name.py b/new/name.py
similarity index 90%
rename from old/name.py
rename to new/name.py
diff --git a/docs/new.md b/docs/new.md
new file mode 100644
--- /dev/null
+++ b/docs/new.md
@@ -0,0 +1 @@
+hi
"""


def test_paths_come_from_diff_headers_and_renames_use_the_new_name():
    assert sl.changed_paths(GIT_DIFF) == ["src/app.py", "new/name.py", "docs/new.md"]


def test_paths_fall_back_to_plus_headers_for_a_diff_without_git_headers():
    diff = "--- a/x.py\n+++ b/x.py\n@@ -1 +1 @@\n-a\n+b\n--- /dev/null\n+++ b/y.py\n@@ -0,0 +1 @@\n+c\n"
    assert sl.changed_paths(diff) == ["x.py", "y.py"]


def test_a_plain_list_of_paths_is_accepted_and_cleaned():
    text = "# changed files\n./src/app.py\n\nsrc\\win.py\nsrc/app.py\n"
    assert sl.changed_paths(text) == ["src/app.py", "src/win.py"]


@pytest.mark.parametrize("text", ["", "\n\n", "   \n"])
def test_empty_input_has_no_paths(text):
    assert sl.changed_paths(text) == []


def test_a_diff_with_no_readable_header_does_not_turn_its_body_into_paths():
    assert sl.changed_paths("@@ -1 +1 @@\n-a\n+b\n") == []


# --- globs ---


@pytest.mark.parametrize(
    "pattern, path, expected",
    [
        ("**/*.sql", "a.sql", True),
        ("**/*.sql", "db/migrations/1.sql", True),
        ("**/*.sql", "db/1.sqlx", False),
        ("**/migrations/**", "migrations/1.sql", True),
        ("**/migrations/**", "db/migrations/sub/1.sql", True),
        ("**/migrations/**", "db/migration/1.sql", False),
        ("src/*.py", "src/a.py", True),
        ("src/*.py", "src/sub/a.py", False),
        ("src/**/a.py", "src/a.py", True),
        ("src/**/a.py", "src/x/y/a.py", True),
        ("docs/?.md", "docs/a.md", True),
        ("docs/?.md", "docs/ab.md", False),
        ("a+b/(c).txt", "a+b/(c).txt", True),
    ],
)
def test_glob_matching(pattern, path, expected):
    assert bool(sl.glob_to_regex(pattern).match(path)) is expected


# --- reading a lens file ---


def test_parse_lens_reads_inline_lists_and_quoted_values():
    lens = sl.parse_lens(lens_text("service", paths="[\"**/*.sql\", '**/routes/**']", touches="a, b"))
    assert lens == {
        "name": "service",
        "description": "Checks for a thing.",
        "paths": ["**/*.sql", "**/routes/**"],
        "touches": "a, b",
    }


def test_parse_lens_reads_a_block_list():
    text = (
        "---\nname: x\ndescription: d\napplies_when:\n  paths:\n"
        '    - "**/*.tf"\n    - infra/**\n  touches: t\n---\n'
    )
    assert sl.parse_lens(text)["paths"] == ["**/*.tf", "infra/**"]


@pytest.mark.parametrize(
    "text, reason",
    [
        ("# no frontmatter", "no frontmatter"),
        ("---\nname: x\n", "not closed"),
        ("---\ndescription: d\napplies_when:\n  paths: [a]\n---\n", "'name' is missing"),
        ("---\nname: x\napplies_when:\n  paths: [a]\n---\n", "'description' is missing"),
        ("---\nname: x\ndescription: d\n---\n", "applies_when.paths"),
        ("---\nname: x\ndescription: d\napplies_when:\n  paths: nope\n---\n", "applies_when.paths"),
        ("---\nname: x\n- stray\n---\n", "unexpected list item"),
        ("---\nname x\n---\n", "cannot read"),
    ],
)
def test_parse_lens_rejects_unusable_files(text, reason):
    with pytest.raises(ValueError, match=reason):
        sl.parse_lens(text)


def test_every_bundled_lens_can_be_read_by_the_script():
    skipped = []
    lenses = sl.load_lenses(sl.BUNDLED_LENSES, "bundled", skipped)
    assert skipped == []
    assert {"service", "api-spec"} <= set(lenses)


# --- suggesting lenses ---


def suggest(text, tmp_path, *, bundled=(), project=()):
    for name, kwargs in bundled:
        write_lens(tmp_path / "bundled", name, **kwargs)
    for name, kwargs in project:
        write_lens(tmp_path / "project", name, **kwargs)
    return sl.suggest(text, tmp_path / "bundled", tmp_path / "project")


def test_matched_and_unmatched_lenses_are_split_by_path(tmp_path):
    report = suggest(
        "db/1.sql\nREADME.md\n",
        tmp_path,
        bundled=[("service", {}), ("web", {"paths": '["**/*.tsx"]', "touches": "screens"})],
    )
    assert report["status"] == "ok"
    assert [m["name"] for m in report["matched"]] == ["service"]
    assert report["matched"][0]["matched_files"] == ["db/1.sql"]
    assert [u["name"] for u in report["unmatched"]] == ["web"]
    assert report["unmatched"][0]["touches"] == "screens"
    assert "note" not in report


def test_several_lenses_can_match_one_change(tmp_path):
    report = suggest(
        "db/1.sql\nui/a.tsx\n",
        tmp_path,
        bundled=[("service", {}), ("web", {"paths": '["**/*.tsx"]'})],
    )
    assert [m["name"] for m in report["matched"]] == ["service", "web"]


def test_a_change_that_matches_nothing_lists_every_lens_as_unmatched(tmp_path):
    report = suggest("docs/guide.md\n", tmp_path, bundled=[("service", {})])
    assert report["matched"] == []
    assert [u["name"] for u in report["unmatched"]] == ["service"]


def test_a_project_lens_wins_over_a_bundled_lens_of_the_same_name(tmp_path):
    report = suggest(
        "db/1.sql\n",
        tmp_path,
        bundled=[("service", {"description": "bundled one"})],
        project=[("service", {"description": "project one", "paths": '["db/**"]'})],
    )
    [matched] = report["matched"]
    assert (matched["source"], matched["description"]) == ("project", "project one")
    assert report["overridden"] == ["service"]
    assert report["unmatched"] == []


def test_a_project_lens_with_a_new_name_is_added(tmp_path):
    report = suggest("db/1.sql\n", tmp_path, bundled=[("service", {})], project=[("billing", {"paths": '["db/**"]'})])
    assert {m["name"]: m["source"] for m in report["matched"]} == {"service": "bundled", "billing": "project"}
    assert report["overridden"] == []


def test_an_unusable_lens_is_skipped_and_the_rest_still_work(tmp_path):
    (tmp_path / "bundled").mkdir()
    (tmp_path / "bundled" / "broken.md").write_text("no frontmatter")
    (tmp_path / "bundled" / "wrong.md").write_text(lens_text("other"))
    report = suggest("db/1.sql\n", tmp_path, bundled=[("service", {})])
    assert [m["name"] for m in report["matched"]] == ["service"]
    reasons = {Path(s["file"]).name: s["reason"] for s in report["skipped"]}
    assert "no frontmatter" in reasons["broken.md"]
    assert "must equal the file name" in reasons["wrong.md"]


def test_the_lens_readme_is_not_a_lens(tmp_path):
    (tmp_path / "bundled").mkdir()
    (tmp_path / "bundled" / "README.md").write_text("# Lenses\n")
    report = suggest("db/1.sql\n", tmp_path, bundled=[("service", {})])
    assert report["skipped"] == []
    assert [m["name"] for m in report["matched"]] == ["service"]


def test_missing_lens_folders_give_a_core_only_note(tmp_path):
    report = sl.suggest("src/a.py\n", tmp_path / "nope", tmp_path / "also-nope")
    assert report["matched"] == [] and report["unmatched"] == []
    assert "core review applies" in report["note"]


def test_empty_input_reports_no_input_and_still_lists_the_lenses(tmp_path):
    report = suggest("", tmp_path, bundled=[("service", {})])
    assert report["status"] == "no_input"
    assert [u["name"] for u in report["unmatched"]] == ["service"]
    assert "No changed file paths" in report["note"]


# --- the command line ---


def run_cli(*args, stdin=b"", cwd=None):
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        input=stdin,
        capture_output=True,
        cwd=cwd,
        check=False,
    )


def test_cli_reads_stdin_and_prints_json_with_the_bundled_lenses():
    result = run_cli(stdin=b"db/migrations/1.sql\n")
    assert result.returncode == 0
    report = json.loads(result.stdout)
    assert [m["name"] for m in report["matched"]] == ["service"]
    assert report["changed_files"] == ["db/migrations/1.sql"]


def test_cli_reads_a_file_and_finds_project_lenses_in_the_working_directory(tmp_path):
    write_lens(tmp_path / ".claude" / "qa-review" / "lenses", "billing", paths='["billing/**"]')
    change = tmp_path / "change.diff"
    change.write_text("diff --git a/billing/x.py b/billing/x.py\n", encoding="utf-8")
    report = json.loads(run_cli(str(change), cwd=tmp_path).stdout)
    assert {m["name"]: m["source"] for m in report["matched"]} == {"billing": "project"}


def test_cli_project_lenses_option_points_at_another_folder(tmp_path):
    write_lens(tmp_path / "mine", "billing", paths='["billing/**"]')
    result = run_cli("--project-lenses", str(tmp_path / "mine"), stdin=b"billing/x.py\n")
    assert "billing" in [m["name"] for m in json.loads(result.stdout)["matched"]]


def test_cli_with_a_missing_input_file_still_exits_cleanly_with_a_note(tmp_path):
    result = run_cli(str(tmp_path / "absent.diff"))
    assert result.returncode == 0
    report = json.loads(result.stdout)
    assert report["status"] == "no_input"
    assert "Could not read the input" in report["note"]


def test_cli_survives_binary_garbage_on_stdin():
    result = run_cli(stdin=b"\xff\xfe\x00\x01")
    assert result.returncode == 0
    assert json.loads(result.stdout)["status"] == "no_input"


def test_cli_help_documents_the_output():
    result = run_cli("--help")
    assert result.returncode == 0
    text = result.stdout.decode("utf-8")
    assert "matched_files" in text
    assert "project lens wins" in text
