import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

from tests.unit.qa_review.diffs import make_diff

SCRIPT = Path(__file__).resolve().parents[3] / "skills" / "qa-review" / "scripts" / "openapi_changed.py"

# The skill folder name has a hyphen, so the script is loaded from its path, not imported by name.
_spec = importlib.util.spec_from_file_location("openapi_changed", SCRIPT)
oc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(oc)

ROUTE = '@app.get("/orders/{id}")'


def write_spec(root, name="openapi.yaml", folder=""):
    path = root / folder / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("openapi: 3.0.0\npaths: {}\n", encoding="utf-8")
    return path


def code_and_spec(route_line, spec_added=(), spec_removed=(), spec_before=(), spec_name="openapi.yaml", **kwargs):
    return make_diff("src/api.py", added=[route_line], **kwargs) + make_diff(
        spec_name, added=spec_added, removed=spec_removed, before=spec_before
    )


# --- when it does not apply ---


@pytest.mark.parametrize("text", ["", "\n", "@@ -1 +1 @@\n-a\n+b\n", "\x00\x01 binary �"])
def test_empty_and_malformed_input_is_no_input(text, tmp_path):
    report = oc.check(text, tmp_path)
    assert report["status"] == "no_input"
    assert report["routes_without_spec_change"] == []
    assert report["note"]


def test_a_repo_without_a_spec_is_not_applicable(tmp_path):
    report = oc.check(make_diff("src/api.py", added=[ROUTE]), tmp_path)
    assert report["status"] == "not_applicable"
    assert report["spec_files"] == []
    assert "no OpenAPI or Swagger spec" in report["note"]


@pytest.mark.parametrize("folder", ["node_modules/pkg", "tests/data", "fixtures", "vendor/x", ".venv/lib", "build"])
def test_specs_in_test_vendor_and_build_folders_do_not_count(tmp_path, folder):
    write_spec(tmp_path, folder=folder)
    assert oc.check(make_diff("src/api.py", added=[ROUTE]), tmp_path)["status"] == "not_applicable"


def test_a_file_that_only_looks_like_a_spec_does_not_count(tmp_path):
    for name in ("openapi.md", "openapi_notes.txt", "my-openapi.yaml", "api.yaml"):
        write_spec(tmp_path, name=name)
    assert oc.check(make_diff("src/api.py", added=[ROUTE]), tmp_path)["status"] == "not_applicable"


def test_a_missing_root_folder_is_not_applicable(tmp_path):
    assert oc.check(make_diff("src/api.py", added=[ROUTE]), tmp_path / "nope")["status"] == "not_applicable"


@pytest.mark.parametrize("folder", ["tests/fixtures", "tests/data", "fixtures", "node_modules/pkg", "vendor/x", "build", ".venv/lib"])
def test_a_changed_file_named_like_a_spec_in_a_skipped_folder_is_not_a_spec(tmp_path, folder):
    diff = make_diff("src/api.py", added=[ROUTE]) + make_diff(f"{folder}/openapi.json", added=['"/orders/{id}": {}'])
    report = oc.check(diff, tmp_path)
    assert report["status"] == "not_applicable"
    assert report["spec_files"] == []
    assert report["spec_files_changed"] == []
    assert report["routes_without_spec_change"] == []


def test_a_changed_fixture_spec_next_to_a_real_spec_is_ignored(tmp_path):
    write_spec(tmp_path, folder="docs")
    diff = make_diff("src/api.py", added=[ROUTE]) + make_diff("tests/fixtures/openapi.json", added=['"/orders/{id}": {}'])
    report = oc.check(diff, tmp_path)
    assert report["spec_files"] == ["docs/openapi.yaml"]
    assert report["spec_files_changed"] == []
    assert report["routes_with_spec_change"] == []
    assert report["routes_without_spec_change"][0]["reason"] == "no spec file changed in this change"


def test_a_spec_the_change_deletes_does_not_count(tmp_path):
    diff = make_diff("src/api.py", added=[ROUTE]) + make_diff("openapi.yaml", removed=["x"], deleted=True)
    assert oc.check(diff, tmp_path)["status"] == "not_applicable"


# --- finding the spec ---


def test_a_spec_in_the_working_tree_is_found(tmp_path):
    write_spec(tmp_path, folder="docs")
    write_spec(tmp_path, name="swagger.json")
    report = oc.check(make_diff("src/api.py", added=[ROUTE]), tmp_path)
    assert report["status"] == "ok"
    assert report["spec_files"] == ["docs/openapi.yaml", "swagger.json"]
    assert report["spec_files_changed"] == []


def test_a_spec_added_by_the_change_counts_even_when_the_tree_has_none(tmp_path):
    report = oc.check(code_and_spec(ROUTE, spec_added=["/orders/{id}:"]), tmp_path)
    assert report["status"] == "ok"
    assert report["spec_files"] == ["openapi.yaml"]
    assert report["spec_files_changed"] == ["openapi.yaml"]


def test_the_search_stops_after_the_folder_limit(tmp_path, monkeypatch):
    for i in range(4):
        (tmp_path / f"d{i}").mkdir()
    monkeypatch.setattr(oc, "FOLDER_LIMIT", 2)
    report = oc.check(make_diff("src/api.py", added=[ROUTE]), tmp_path)
    assert report["status"] == "not_applicable"
    assert "stopped after 2 folders" in report["note"]


def test_only_the_first_twenty_specs_are_listed(tmp_path):
    for i in range(25):
        write_spec(tmp_path, folder=f"s{i:02d}")
    report = oc.check(make_diff("src/api.py", added=[ROUTE]), tmp_path)
    assert len(report["spec_files"]) == 20
    assert "25 spec files were found" in report["note"]


# --- matching routes with the spec change ---


def test_a_route_with_no_spec_change_is_named_with_the_reason(tmp_path):
    write_spec(tmp_path)
    report = oc.check(make_diff("src/api.py", added=[ROUTE]), tmp_path)
    assert report["routes_changed"] == 1
    assert report["routes_without_spec_change"] == [
        {"file": "src/api.py", "route": "GET /orders/{id}", "change": "added", "line": 10,
         "reason": "no spec file changed in this change"}
    ]  # fmt: skip
    assert report["routes_with_spec_change"] == []


def test_a_route_whose_path_is_on_an_added_spec_line_matches(tmp_path):
    report = oc.check(code_and_spec(ROUTE, spec_added=["  /orders/{id}:", "    get:"]), tmp_path)
    assert report["routes_without_spec_change"] == []
    assert report["routes_with_spec_change"] == [
        {"file": "src/api.py", "route": "GET /orders/{id}", "change": "added", "line": 10, "spec": "openapi.yaml"}
    ]


def test_a_route_whose_path_is_on_a_removed_spec_line_matches(tmp_path):
    diff = make_diff("src/api.py", removed=[ROUTE]) + make_diff("openapi.yaml", removed=["  /orders/{id}:"])
    report = oc.check(diff, tmp_path)
    assert [r["route"] for r in report["routes_with_spec_change"]] == ["GET /orders/{id}"]


@pytest.mark.parametrize(
    ("route_line", "spec_line"),
    [
        ('@app.route("/orders/<id>")', '  "/orders/{id}": {'),
        ('@app.get("/orders/<int:pk>")', "  /orders/{orderId}:"),
        ("app.get('/orders/:id', h)", "  /orders/{id}:"),
        ('@app.get("/orders/{id}/")', "  /orders/{id}:"),
        ('@app.get("/orders")', "  /api/v1/orders:"),
        ('@app.get("/orders")', '    "/orders": {'),
    ],
)
def test_parameters_slashes_and_prefixes_do_not_stop_a_match(tmp_path, route_line, spec_line):
    path = "src/api.js" if route_line.startswith("app.") else "src/api.py"
    diff = make_diff(path, added=[route_line]) + make_diff("openapi.yaml", added=[spec_line])
    report = oc.check(diff, tmp_path)
    assert len(report["routes_with_spec_change"]) == 1, report


def test_a_django_path_without_a_leading_slash_matches(tmp_path):
    diff = make_diff("shop/urls.py", added=['    path("orders/<int:pk>/", views.detail),']) + make_diff(
        "openapi.yaml", added=["  /orders/{id}:"]
    )
    assert len(oc.check(diff, tmp_path)["routes_with_spec_change"]) == 1


def test_a_rails_resources_route_matches_the_paths_below_it(tmp_path):
    diff = make_diff("config/routes.rb", added=["  resources :orders"]) + make_diff(
        "openapi.yaml", added=["  /orders/{id}:"]
    )
    assert [r["route"] for r in oc.check(diff, tmp_path)["routes_with_spec_change"]] == ["resources orders"]


def test_a_longer_word_that_ends_the_same_is_not_a_match(tmp_path):
    report = oc.check(code_and_spec('@app.get("/orders")', spec_added=["  /myorders:"]), tmp_path)
    assert report["routes_with_spec_change"] == []
    assert len(report["routes_without_spec_change"]) == 1


def test_a_spec_change_that_does_not_name_the_path_is_a_gap_with_its_own_reason(tmp_path):
    report = oc.check(code_and_spec(ROUTE, spec_added=["  /customers:"]), tmp_path)
    assert report["routes_with_spec_change"] == []
    assert report["routes_without_spec_change"][0]["reason"] == "a spec file changed, but its changed lines do not name this path"


def test_a_path_that_is_only_context_next_to_changed_lines_is_not_a_match(tmp_path):
    diff = make_diff("src/api.py", added=[ROUTE]) + make_diff(
        "openapi.yaml", before=["  /orders/{id}:"], added=["    description: new words"]
    )
    reason = oc.check(diff, tmp_path)["routes_without_spec_change"][0]["reason"]
    assert reason.startswith("the path appears only on unchanged lines")


def test_references_and_media_types_in_the_spec_are_not_paths(tmp_path):
    spec_lines = ["$ref: '#/components/schemas/orders'", "content: application/json", "url: https://example.com/orders"]
    report = oc.check(code_and_spec('@app.get("/orders")', spec_added=spec_lines), tmp_path)
    assert report["routes_with_spec_change"] == []


def test_the_method_is_not_compared(tmp_path):
    report = oc.check(code_and_spec('@app.delete("/orders")', spec_added=["  /orders:", "    get:"]), tmp_path)
    assert len(report["routes_with_spec_change"]) == 1


def test_a_route_with_no_path_is_not_compared(tmp_path):
    write_spec(tmp_path)
    report = oc.check(make_diff("src/orders.controller.ts", added=["  @Get()"]), tmp_path)
    assert report["routes_without_spec_change"] == []
    assert report["routes_not_compared"] == [
        {"file": "src/orders.controller.ts", "route": "GET", "reason": "the change shows no path for this route to look for"}
    ]


def test_each_route_is_judged_on_its_own(tmp_path):
    diff = make_diff("src/api.py", added=['@app.get("/a")', "def a(): ...", '@app.post("/b")']) + make_diff(
        "openapi.yaml", added=["  /a:"]
    )
    report = oc.check(diff, tmp_path)
    assert [r["route"] for r in report["routes_with_spec_change"]] == ["GET /a"]
    assert [r["route"] for r in report["routes_without_spec_change"]] == ["POST /b"]
    assert report["routes_changed"] == 2


def test_a_changed_file_that_is_not_named_like_a_spec_is_not_a_spec_change(tmp_path):
    write_spec(tmp_path)
    diff = make_diff("src/api.py", added=[ROUTE]) + make_diff("api.yaml", added=["  /orders/{id}:"])
    assert len(oc.check(diff, tmp_path)["routes_without_spec_change"]) == 1


def test_flags_and_settings_are_not_compared_with_the_spec(tmp_path):
    write_spec(tmp_path)
    report = oc.check(make_diff("cli.py", added=['parser.add_argument("--exclude")', 'os.getenv("X")']), tmp_path)
    assert report["status"] == "ok"
    assert report["routes_changed"] == 0
    assert "No changed HTTP route" in report["note"]


def test_a_list_of_paths_has_no_routes_to_compare(tmp_path):
    write_spec(tmp_path)
    report = oc.check("src/api.py\nopenapi.yaml\n", tmp_path)
    assert report["status"] == "ok"
    assert report["spec_files_changed"] == ["openapi.yaml"]
    assert report["routes_changed"] == 0


# --- running it ---


def run_cli(*args, stdin="", cwd=None):
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args], input=stdin, capture_output=True, text=True, check=False, cwd=cwd
    )


def test_it_reads_stdin_looks_in_the_given_root_and_exits_0(tmp_path):
    write_spec(tmp_path)
    result = run_cli("--root", str(tmp_path), stdin=make_diff("src/api.py", added=[ROUTE]))
    report = json.loads(result.stdout)
    assert result.returncode == 0
    assert report["status"] == "ok"
    assert len(report["routes_without_spec_change"]) == 1


def test_by_default_it_looks_in_the_current_folder(tmp_path):
    write_spec(tmp_path)
    report = json.loads(run_cli(stdin=make_diff("src/api.py", added=[ROUTE]), cwd=tmp_path).stdout)
    assert report["spec_files"] == ["openapi.yaml"]


def test_it_reads_a_file(tmp_path):
    path = tmp_path / "pr.diff"
    path.write_text(make_diff("src/api.py", added=[ROUTE]), encoding="utf-8")
    assert json.loads(run_cli(str(path), cwd=tmp_path).stdout)["status"] == "not_applicable"


def test_a_missing_file_exits_0_with_a_note(tmp_path):
    result = run_cli(str(tmp_path / "missing.diff"), cwd=tmp_path)
    report = json.loads(result.stdout)
    assert result.returncode == 0
    assert report["status"] == "no_input"
    assert "Could not read the input" in report["note"]


def test_help_documents_the_output():
    result = run_cli("--help")
    assert result.returncode == 0
    for text in ("not_applicable", "no_input", "routes_without_spec_change", "routes_with_spec_change", "--root"):
        assert text in result.stdout


# --- the fixtures that hold this script's output ---

FIXTURES = Path(__file__).resolve().parents[3] / "evals" / "qa-review" / "fixtures"
WITH_OUTPUT = sorted(path.parent.name for path in FIXTURES.glob("*/openapi_changed.json"))


def test_some_fixtures_hold_the_output():
    assert {"interface-without-docs", "mixed-lens-change"} <= set(WITH_OUTPUT)


@pytest.mark.parametrize("fixture", WITH_OUTPUT)
def test_the_output_file_is_what_the_script_prints_for_the_fixture_diff(fixture, tmp_path):
    """The fixture has no repo around it, so the spec search runs in an empty folder."""
    diff = (FIXTURES / fixture / "pr.diff").read_text(encoding="utf-8")
    expected = json.loads((FIXTURES / fixture / "openapi_changed.json").read_text(encoding="utf-8"))
    assert oc.check(diff, tmp_path) == expected
