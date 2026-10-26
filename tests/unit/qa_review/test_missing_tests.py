import ast
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[3] / "skills" / "qa-review" / "scripts" / "missing_tests.py"

# The skill folder name has a hyphen, so the script is loaded from its path, not imported by name.
_spec = importlib.util.spec_from_file_location("missing_tests", SCRIPT)
mt = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(mt)


def defaults():
    return [(language, list(language.patterns)) for language in mt.LANGUAGES]


def run(paths, patterns=None, source_ext=()):
    """Run the check on a plain list of paths."""
    return mt.check("\n".join(paths) + "\n", defaults() if patterns is None else patterns, set(source_ext))


def missing(report):
    return [entry["file"] for entry in report["missing_test_change"]]


def covered(report):
    return {entry["file"]: entry["tests"] for entry in report["has_test_change"]}


def not_checked(report):
    return {entry["file"]: entry["reason"] for entry in report["not_checked"]}


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
diff --git a/src/gone.py b/src/gone.py
deleted file mode 100644
index 3..0
--- a/src/gone.py
+++ /dev/null
@@ -1 +0,0 @@
-bye
"""


def test_paths_and_deleted_files_come_from_a_git_diff():
    paths, deleted = mt.changed_files(GIT_DIFF)
    assert paths == ["src/app.py", "new/name.py", "src/gone.py"]
    assert deleted == {"src/gone.py"}


def test_a_diff_without_git_headers_is_read_from_the_plus_and_minus_lines():
    diff = "--- a/x.py\n+++ b/x.py\n@@ -1 +1 @@\n-a\n+b\n--- a/y.py\n+++ /dev/null\n@@ -1 +0,0 @@\n-c\n"
    paths, deleted = mt.changed_files(diff)
    assert paths == ["x.py", "y.py"]
    assert deleted == {"y.py"}


def test_a_plain_list_of_paths_is_accepted_and_cleaned():
    paths, deleted = mt.changed_files("# changed files\n./src/app.py\n\nsrc\\win.py\nsrc/app.py\n")
    assert paths == ["src/app.py", "src/win.py"]
    assert deleted == set()


@pytest.mark.parametrize("text", ["", "\n\n", "   \n", "@@ -1 +1 @@\n-a\n+b\n", "\x00\x01\x02\n", "ab�cd\n"])
def test_empty_and_unreadable_input_has_no_paths(text):
    assert mt.changed_files(text)[0] == []


# --- the main question: which source files have no test change ---


def test_a_source_file_with_no_matching_test_change_is_missing_a_test():
    report = run(["src/slugkit/text.py"])
    assert report["status"] == "ok"
    assert missing(report) == ["src/slugkit/text.py"]
    assert report["missing_test_change"][0]["language"] == "python"
    assert report["missing_test_change"][0]["expected_tests"] == ["**/test_text.py", "**/text_test.py"]


def test_the_same_change_with_its_test_file_is_not_missing_anything():
    report = run(["src/slugkit/text.py", "tests/test_text.py"])
    assert missing(report) == []
    assert covered(report) == {"src/slugkit/text.py": ["tests/test_text.py"]}
    assert report["test_files_changed"] == ["tests/test_text.py"]


def test_only_the_file_without_a_test_is_reported():
    report = run(["src/a.py", "src/b.py", "tests/test_a.py"])
    assert missing(report) == ["src/b.py"]
    assert list(covered(report)) == ["src/a.py"]


def test_a_test_change_for_a_differently_named_file_does_not_count_but_the_report_says_to_read_it():
    report = run(["src/a.py", "tests/test_other.py"])
    assert missing(report) == ["src/a.py"]
    assert "read them before reporting a gap" in report["note"]


@pytest.mark.parametrize(
    "source, test",
    [
        ("src/text.py", "tests/unit/test_text.py"),
        ("src/text.py", "src/text_test.py"),
        ("src/user_service.py", "tests/test_user-service.py"),
        ("web/Button.tsx", "web/Button.test.tsx"),
        ("web/button.js", "web/__tests__/button.js"),
        ("web/api.ts", "tests/api.spec.ts"),
        ("src/main/java/com/acme/Order.java", "src/test/java/com/acme/OrderTest.java"),
        ("src/main/java/com/acme/Order.java", "src/test/java/com/acme/OrderTests.java"),
        ("src/main/java/com/acme/Order.java", "src/test/java/com/acme/OrderIT.java"),
        ("pkg/files/files.go", "pkg/files/files_test.go"),
        ("app/models/user.rb", "spec/models/user_spec.rb"),
        ("src/Acme/Order.cs", "tests/Acme/OrderTests.cs"),
        ("src/Order.php", "tests/OrderTest.php"),
        ("Sources/App/Order.swift", "Tests/AppTests/OrderTests.swift"),
        ("src/Order.kt", "src/test/kotlin/OrderTest.kt"),
    ],
)
def test_default_patterns_match_the_common_test_names(source, test):
    report = run([source, test])
    assert missing(report) == []
    assert covered(report) == {source: [test]}


@pytest.mark.parametrize(
    "source, language",
    [
        ("src/a.py", "python"),
        ("src/a.ts", "javascript/typescript"),
        ("src/A.java", "java"),
        ("src/a.go", "go"),
    ],
)
def test_each_default_language_reports_a_missing_test(source, language):
    report = run([source])
    assert missing(report) == [source]
    assert report["missing_test_change"][0]["language"] == language


def test_names_are_compared_without_case_or_separators():
    assert missing(run(["src/UserService.ts", "src/user-service.test.ts"])) == []


def test_a_same_named_test_in_another_language_is_not_a_match():
    assert missing(run(["src/text.py", "web/text.test.ts"])) == ["src/text.py"]


# --- files with the same name in different folders ---


@pytest.mark.parametrize(
    "source, test, agree",
    [
        ("src/a/utils.py", "tests/b/test_utils.py", False),
        ("src/utils.py", "tests/test_utils.py", True),
        ("src/a/utils.py", "tests/test_utils.py", True),
        ("src/pkg/sub/mod.py", "tests/sub/test_mod.py", True),
        ("src/pkg/mod.py", "tests/other/test_mod.py", False),
        ("packages/a/src/index.ts", "packages/a/tests/index.test.ts", True),
        ("packages/a/src/index.ts", "packages/b/src/index.test.ts", False),
        ("Sources/App/Order.swift", "Tests/AppTests/OrderTests.swift", True),
        ("src/main/java/com/acme/Order.java", "src/test/java/com/acme/OrderTest.java", True),
        ("src/main/java/com/acme/Order.java", "src/test/java/com/other/OrderTest.java", False),
        ("app/models/user.rb", "spec/models/user_spec.rb", True),
        ("src/unit_tests/x.py", "tests/test_x.py", True),
    ],
)
def test_folders_agree_when_one_path_ends_with_the_other_once_structure_folders_are_ignored(source, test, agree):
    assert mt.folders_agree(source, test) is agree


def test_a_test_in_another_module_does_not_cover_a_same_named_source_file():
    report = run(["src/a/utils.py", "src/b/utils.py", "tests/b/test_utils.py"])
    assert missing(report) == ["src/a/utils.py"]
    assert report["missing_test_change"][0]["same_name_tests_elsewhere"] == ["tests/b/test_utils.py"]
    assert covered(report) == {"src/b/utils.py": ["tests/b/test_utils.py"]}
    assert "ambiguous_with" not in report["has_test_change"][0]


def test_a_test_with_no_telling_folder_matches_both_files_and_says_so():
    report = run(["src/a/utils.py", "src/b/utils.py", "tests/test_utils.py"])
    assert missing(report) == []
    by_file = {entry["file"]: entry for entry in report["has_test_change"]}
    assert by_file["src/a/utils.py"]["ambiguous_with"] == ["src/b/utils.py"]
    assert by_file["src/b/utils.py"]["ambiguous_with"] == ["src/a/utils.py"]
    assert "may cover only one of them" in report["note"]


def test_a_missing_test_without_a_same_name_test_elsewhere_has_no_such_key():
    assert "same_name_tests_elsewhere" not in run(["src/a.py"])["missing_test_change"][0]


# --- files that need no test ---


@pytest.mark.parametrize(
    "path, reason",
    [
        ("README.md", "documentation"),
        ("docs/install.txt", "documentation"),
        ("docs/guide/setup.png", "documentation"),
        ("LICENSE", "documentation"),
        ("pyproject.toml", "configuration"),
        ("package.json", "configuration"),
        (".github/workflows/ci.yml", "configuration"),
        (".gitignore", "configuration"),
        ("Dockerfile", "configuration"),
        ("package-lock.json", "lock file"),
        ("uv.lock", "lock file"),
        ("go.sum", "lock file"),
        ("yarn.lock", "lock file"),
        ("dist/app.js", "generated or bundled file"),
        ("web/app.min.js", "generated or bundled file"),
        ("api/user_pb2.py", "generated or bundled file"),
        ("web/logo.png", "asset or data file"),
        ("src/pkg/__init__.py", "package marker"),
    ],
)
def test_documentation_configuration_lock_and_generated_files_are_not_checked(path, reason):
    report = run([path])
    assert not_checked(report) == {path: reason}
    assert missing(report) == []
    assert report["status"] == "ok"
    assert report["note"] == "No changed source files to check."


@pytest.mark.parametrize(
    "path, reason",
    [
        ("webpack.config.js", "configuration"),
        ("web/vite.config.ts", "configuration"),
        ("next.config.mjs", "configuration"),
        ("jest.setup.js", "configuration"),
        ("src/types.d.ts", "type declarations"),
    ],
)
def test_javascript_and_typescript_configuration_and_declaration_files_are_not_checked(path, reason):
    report = run([path])
    assert not_checked(report) == {path: reason}
    assert missing(report) == []


def test_a_file_that_only_looks_like_configuration_is_still_checked():
    assert missing(run(["src/config.py", "src/setup_user.js", "src/config/loader.ts"])) == [
        "src/config.py",
        "src/setup_user.js",
        "src/config/loader.ts",
    ]


def test_a_django_style_tests_file_is_a_test_not_a_source_file():
    report = run(["app/models.py", "app/tests.py"])
    assert report["test_files_changed"] == ["app/tests.py"]
    assert missing(report) == ["app/models.py"]
    assert "read them before reporting a gap" in report["note"]


def test_a_deleted_file_needs_no_test():
    report = mt.check(GIT_DIFF, defaults(), set())
    assert not_checked(report)["src/gone.py"] == "deleted"
    assert "src/gone.py" not in missing(report)
    assert missing(report) == ["src/app.py", "new/name.py"]


def test_test_support_files_count_as_tests_not_source():
    report = run(["tests/helpers.py", "conftest.py", "tests/fixtures/data.json"])
    assert report["test_files_changed"] == ["tests/helpers.py", "conftest.py", "tests/fixtures/data.json"]
    assert missing(report) == []


# --- saying when it cannot tell ---


def test_empty_input_exits_cleanly_with_no_input_status():
    report = mt.check("", defaults(), set())
    assert report["status"] == "no_input"
    assert report["changed_files"] == []
    assert "by hand" in report["note"]


def test_a_file_type_with_no_convention_is_could_not_tell_not_missing():
    report = run(["src/lib.rs", "assets/schema.sql"])
    assert report["status"] == "could_not_tell"
    assert missing(report) == []
    reasons = {entry["file"]: entry["reason"] for entry in report["could_not_tell"]}
    assert "inside the source file" in reasons["src/lib.rs"]
    assert "unrecognized file type '.sql'" in reasons["assets/schema.sql"]
    assert "by hand" in report["note"]


def test_a_file_without_an_extension_is_could_not_tell():
    report = run(["bin/tool"])
    assert report["status"] == "could_not_tell"
    assert report["could_not_tell"][0]["reason"] == "unrecognized file type 'bin/tool'"


def test_a_change_with_no_test_files_lists_every_source_file_because_the_script_sees_only_the_change():
    # The script cannot tell a project with no tests from a change that forgot them. Step 5 decides, from Step 3.
    report = run(["src/a.py", "src/b.py"])
    assert report["status"] == "ok"
    assert missing(report) == ["src/a.py", "src/b.py"]
    assert report["test_files_changed"] == []
    assert "only the change" in mt.__doc__


def test_other_files_are_still_judged_when_one_cannot_be():
    report = run(["src/lib.rs", "src/a.py"])
    assert report["status"] == "ok"
    assert missing(report) == ["src/a.py"]
    assert [entry["file"] for entry in report["could_not_tell"]] == ["src/lib.rs"]


# --- changing the patterns ---


def test_a_pattern_from_the_command_line_extends_the_defaults():
    patterns = defaults() + [(None, ["checks/{name}.check.py"])]
    report = run(["src/a.py", "checks/a.check.py"], patterns)
    assert covered(report) == {"src/a.py": ["checks/a.check.py"]}


def test_a_new_language_needs_a_pattern_and_a_source_extension():
    patterns = defaults() + [(None, ["test/{name}_test.gleam"])]
    report = run(["src/wibble.gleam", "test/wibble_test.gleam"], patterns, source_ext=[".gleam"])
    assert covered(report) == {"src/wibble.gleam": ["test/wibble_test.gleam"]}
    assert report["missing_test_change"] == []
    assert run(["src/wibble.gleam"], patterns)["status"] == "could_not_tell"


def test_replacing_the_defaults_leaves_only_the_given_patterns():
    patterns = [(None, ["spec/{name}_spec.rb"])]
    report = run(["src/a.py", "tests/test_a.py", "lib/b.rb", "spec/b_spec.rb"], patterns)
    assert covered(report) == {"lib/b.rb": ["spec/b_spec.rb"]}
    assert missing(report) == ["src/a.py"]  # tests/test_a.py is still a test file, but no pattern links it


def test_with_no_patterns_at_all_nothing_can_be_judged():
    report = run(["src/a.py"], patterns=[])
    assert report["status"] == "could_not_tell"
    assert "--test-pattern" in report["could_not_tell"][0]["reason"]


def test_a_pattern_without_a_name_only_marks_test_files():
    patterns = defaults() + [(None, ["checks/**"])]
    report = run(["checks/anything.py", "src/a.py"], patterns)
    assert report["test_files_changed"] == ["checks/anything.py"]
    assert missing(report) == ["src/a.py"]


def test_a_project_patterns_file_gives_patterns_and_source_extensions(tmp_path):
    path = tmp_path / "test-patterns"
    path.write_text(
        "# our layout\n\nspec/{name}_spec.rb\n  checks/{name}.check.py  \nsource-ext: .gleam, res\nSOURCE-EXT: .zig\n",
        encoding="utf-8",
    )
    globs, extensions, problem = mt.read_project_patterns(path)
    assert globs == ["spec/{name}_spec.rb", "checks/{name}.check.py"]
    assert extensions == {".gleam", ".res", ".zig"}
    assert problem == ""


def test_a_missing_project_patterns_file_is_fine(tmp_path):
    assert mt.read_project_patterns(tmp_path / "nope") == ([], set(), "")
    assert mt.read_project_patterns(tmp_path) == ([], set(), "")  # a folder is not a file


def test_an_unreadable_project_patterns_file_is_reported_not_raised(tmp_path):
    path = tmp_path / "test-patterns"
    path.write_bytes(b"\xff\xfe\x00bad")
    globs, extensions, problem = mt.read_project_patterns(path)
    assert (globs, extensions) == ([], set())
    assert "Could not read the project patterns file" in problem


@pytest.mark.parametrize("pattern", ["", "{name}", "**", "[", "a{name}b{name}c", "(", "*{name}*"])
def test_odd_patterns_do_not_crash(pattern):
    report = run(["src/a.py", "src/test_a.py"], defaults() + [(None, [pattern])])
    assert report["status"] in ("ok", "could_not_tell")


# --- the command line ---


def run_cli(*args, stdin=None, cwd=None):
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        input=stdin,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=30,
        check=False,
        cwd=cwd,
    )


def test_the_project_patterns_file_in_the_current_folder_is_used_without_any_option(tmp_path):
    (tmp_path / ".claude" / "qa-review").mkdir(parents=True)
    (tmp_path / ".claude" / "qa-review" / "test-patterns").write_text(
        "spec/{name}_spec.rb\nsource-ext: .gleam\ntest/{name}_test.gleam\n", encoding="utf-8"
    )
    result = run_cli(stdin="lib/b.rb\nspec/b_spec.rb\nsrc/w.gleam\n", cwd=tmp_path)
    report = json.loads(result.stdout)
    assert result.returncode == 0
    assert [e["file"] for e in report["has_test_change"]] == ["lib/b.rb"]
    assert [e["file"] for e in report["missing_test_change"]] == ["src/w.gleam"]
    assert report["project_patterns_file"] == ".claude/qa-review/test-patterns"


def test_no_project_patterns_file_means_no_extra_key(tmp_path):
    report = json.loads(run_cli(stdin="src/a.py\n", cwd=tmp_path).stdout)
    assert "project_patterns_file" not in report


def test_the_project_patterns_option_points_at_another_file(tmp_path):
    other = tmp_path / "mine.txt"
    other.write_text("checks/{name}.check.py\n", encoding="utf-8")
    report = json.loads(run_cli("--project-patterns", str(other), stdin="src/a.py\nchecks/a.check.py\n", cwd=tmp_path).stdout)
    assert [e["file"] for e in report["has_test_change"]] == ["src/a.py"]


def test_a_broken_project_patterns_file_still_exits_zero_and_says_so(tmp_path):
    other = tmp_path / "bad.txt"
    other.write_bytes(b"\xff\xfe\x00")
    result = run_cli("--project-patterns", str(other), stdin="src/a.py\n", cwd=tmp_path)
    report = json.loads(result.stdout)
    assert result.returncode == 0
    assert "Could not read the project patterns file" in report["note"]
    assert report["missing_test_change"][0]["file"] == "src/a.py"
    assert "project_patterns_file" not in report


def test_it_reads_a_diff_from_stdin_and_prints_json():
    result = run_cli(stdin=GIT_DIFF)
    assert result.returncode == 0
    assert json.loads(result.stdout)["missing_test_change"][0]["file"] == "src/app.py"


def test_it_reads_a_path_list_from_a_file(tmp_path):
    path = tmp_path / "files.txt"
    path.write_text("src/a.py\ntests/test_a.py\n")
    report = json.loads(run_cli(str(path)).stdout)
    assert report["has_test_change"][0]["tests"] == ["tests/test_a.py"]


def test_a_missing_input_file_exits_zero_and_says_so(tmp_path):
    result = run_cli(str(tmp_path / "nope.txt"))
    assert result.returncode == 0
    report = json.loads(result.stdout)
    assert report["status"] == "no_input"
    assert "Could not read the input" in report["note"]


def test_binary_garbage_exits_zero(tmp_path):
    path = tmp_path / "junk.bin"
    path.write_bytes(bytes(range(256)) * 4)
    result = run_cli(str(path))
    assert result.returncode == 0
    assert json.loads(result.stdout)["status"] == "no_input"


def test_the_options_change_the_patterns():
    result = run_cli(
        "--no-default-patterns", "--test-pattern", "spec/{name}_spec.rb", "--source-ext", "rb",
        stdin="lib/b.rb\nspec/b_spec.rb\nsrc/a.py\n",
    )  # fmt: skip
    report = json.loads(result.stdout)
    assert [e["file"] for e in report["has_test_change"]] == ["lib/b.rb"]
    # a pattern from the command line applies to every source file
    assert report["missing_test_change"][0]["expected_tests"] == ["spec/a_spec.rb"]


def test_help_documents_the_output_and_the_options():
    result = run_cli("--help")
    assert result.returncode == 0
    for text in ("missing_test_change", "has_test_change", "could_not_tell", "no_input", "--test-pattern", "--source-ext"):
        assert text in result.stdout


def test_the_script_uses_only_the_standard_library():
    tree = ast.parse(SCRIPT.read_text(encoding="utf-8"))
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported |= {alias.name.split(".")[0] for alias in node.names}
        elif isinstance(node, ast.ImportFrom):
            imported.add(node.module.split(".")[0])
    assert imported <= set(sys.stdlib_module_names)


# --- the fixtures that hold this script's output ---

FIXTURES = Path(__file__).resolve().parents[3] / "evals" / "qa-review" / "fixtures"
WITH_OUTPUT = sorted(path.parent.name for path in FIXTURES.glob("*/missing_tests.json"))


def test_some_fixtures_hold_the_output():
    assert {"missing-tests", "clean", "docs-only"} <= set(WITH_OUTPUT)


@pytest.mark.parametrize("fixture", WITH_OUTPUT)
def test_the_output_file_is_what_the_script_prints_for_the_fixture_diff(fixture):
    diff = (FIXTURES / fixture / "pr.diff").read_text(encoding="utf-8")
    expected = json.loads((FIXTURES / fixture / "missing_tests.json").read_text(encoding="utf-8"))
    assert mt.check(diff, defaults(), set()) == expected
