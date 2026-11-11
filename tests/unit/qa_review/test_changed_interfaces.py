import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

from tests.unit.qa_review.diffs import make_diff

SCRIPT = Path(__file__).resolve().parents[3] / "skills" / "qa-review" / "scripts" / "changed_interfaces.py"

# The skill folder name has a hyphen, so the script is loaded from its path, not imported by name.
_spec = importlib.util.spec_from_file_location("changed_interfaces", SCRIPT)
ci = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ci)


def found(path, added=(), removed=(), **kwargs):
    """(kind, name, change) of every interface the script lists for one file."""
    report = ci.check(make_diff(path, added=added, removed=removed, **kwargs))
    return [(e["kind"], e["name"], e["change"]) for e in report["interfaces"]]


# --- HTTP routes ---

ROUTES = [
    ("app.py", '@app.route("/orders/<id>", methods=["GET"])', "/orders/<id>"),
    ("api/orders.py", '@router.post("/orders", status_code=201)', "POST /orders"),
    ("api/orders.py", "@app.get('/orders/{id}')", "GET /orders/{id}"),
    ("shop/urls.py", '    path("orders/<int:pk>/", views.detail),', "orders/<int:pk>/"),
    ("server.js", "app.get('/users/:id', handler);", "GET /users/:id"),
    ("src/routes.ts", 'userRouter.delete("/users/:id", remove)', "DELETE /users/:id"),
    ("src/orders.controller.ts", "  @Post('items')", "POST items"),
    ("src/orders.controller.ts", "  @Get()", "GET"),
    ("src/orders.controller.ts", "@Controller('orders')", "orders"),
    ("Orders.java", '    @GetMapping("/orders/{id}")', "GET /orders/{id}"),
    ("Orders.java", '@RequestMapping(value = "/api/orders")', "/api/orders"),
    ("Orders.kt", "    @PostMapping", "POST"),
    ("Orders.java", '@Path("/orders")', "/orders"),
    ("main.go", 'mux.HandleFunc("/health", health)', "/health"),
    ("main.go", 'r.GET("/ping", ping)', "GET /ping"),
    ("config/routes.rb", "  resources :orders", "resources orders"),
    ("config/routes.rb", "  get '/health', to: 'health#show'", "GET /health"),
    ("OrdersController.cs", '    [HttpGet("orders/{id}")]', "GET orders/{id}"),
    ("Program.cs", 'app.MapPost("/orders", Create);', "POST /orders"),
    ("routes/web.php", "Route::get('/orders', [OrderController::class, 'index']);", "GET /orders"),
    ("src/main.rs", '#[get("/orders")]', "GET /orders"),
    ("src/main.rs", 'let app = Router::new().route("/orders", get(list));', "/orders"),
]


@pytest.mark.parametrize(("path", "line", "name"), ROUTES, ids=[r[2] + "@" + r[0] for r in ROUTES])
def test_a_route_is_recognized(path, line, name):
    assert found(path, added=[line]) == [("http_route", name, "added")]


def test_a_get_call_on_an_http_client_is_not_a_route():
    assert found("src/client.js", added=["const r = await api.get('/users');", "client.get('/orders')"]) == []


def test_a_call_with_a_path_that_is_not_a_url_is_not_a_route():
    assert found("src/cache.js", added=["app.get('theme')", "cache.get('/x')"]) == []


# --- command-line flags and commands ---

FLAGS = [
    ("cli.py", 'parser.add_argument("--exclude", action="append")', "--exclude"),
    ("cli.py", 'parser.add_argument("-v", "--verbose", action="store_true")', "--verbose"),
    ("cli.py", 'parser.add_argument("folder", help="folder to count")', "folder"),
    ("cli.py", 'sub.add_parser("build", help="build it")', "command build"),
    ("cli.py", '@click.option("--port", default=8080)', "--port"),
    ("cli.py", '@cli.command("serve")', "command serve"),
    ("cli.js", "program.option('-p, --port <number>', 'port to use')", "--port"),
    ("cli.js", "program.command('serve')", "command serve"),
    ("cli.js", "yargs.option('verbose', { type: 'boolean' })", "verbose"),
    ("cmd/root.go", 'rootCmd.Flags().String("output", "", "where to write")', "output"),
    ("cmd/root.go", 'verbose := flag.Bool("verbose", false, "chatty")', "verbose"),
    ("cmd/root.go", 'flags.StringVar(&cfg.Out, "out", "", "x")', None),
    ("cmd/serve.go", '\tUse:   "serve [flags]",', "command serve"),
    ("Cli.java", '@Option(names = {"-v", "--verbose"}, description = "chatty")', "--verbose"),
    ("Cli.java", '@Command(name = "serve")', "command serve"),
    ("src/cli.rs", 'let a = Arg::new("verbose").long("verbose");', "verbose"),
    ("src/cli.rs", 'let c = Command::new("serve");', "command serve"),
    ("Program.cs", 'var port = new Option<int>("--port", "the port");', "--port"),
]


@pytest.mark.parametrize(
    ("path", "line", "name"),
    [f for f in FLAGS if f[2]],
    ids=[f"{f[2]}@{f[0]}" for f in FLAGS if f[2]],
)
def test_a_flag_or_command_is_recognized(path, line, name):
    assert found(path, added=[line]) == [("cli", name, "added")]


def test_a_flag_split_over_several_lines_is_read_once():
    lines = ["parser.add_argument(", '    "--exclude",', '    action="append",', '    help="skip files",', ")"]
    assert found("cli.py", added=lines) == [("cli", "--exclude", "added")]


def test_a_flag_whose_call_starts_on_an_unchanged_line_is_still_read_from_the_lines_after_it():
    assert found("cli.py", added=['    "--exclude",'], before=["parser.add_argument("]) == []
    assert found("cli.py", added=["parser.add_argument(", '    "--exclude",']) == [("cli", "--exclude", "added")]


def test_two_added_lines_are_never_blamed_on_each_other():
    report = ci.check(make_diff("api.py", added=['@app.get("/a")', "def a(): ...", '@app.get("/b")']))
    assert [e["name"] for e in report["interfaces"]] == ["GET /a", "GET /b"]
    assert [e["line"] for e in report["interfaces"]] == [10, 12]


# --- configuration ---

ENV_READS = [
    ("settings.py", 'URL = os.environ["ORDERS_URL"]', "ORDERS_URL"),
    ("settings.py", 'TOKEN = os.environ.get("API_TOKEN", "")', "API_TOKEN"),
    ("settings.py", "PORT = int(os.getenv('PORT', 80))", "PORT"),
    ("src/config.ts", "const port = process.env.PORT;", "PORT"),
    ("src/config.ts", "const key = process.env['API_KEY'];", "API_KEY"),
    ("src/config.ts", "const mode = import.meta.env.VITE_MODE;", "VITE_MODE"),
    ("main.go", 'addr := os.Getenv("ADDR")', "ADDR"),
    ("App.java", 'String s = System.getenv("SECRET");', "SECRET"),
    ("App.java", '@Value("${server.port:8080}")', "server.port"),
    ("app.rb", "url = ENV.fetch('DATABASE_URL')", "DATABASE_URL"),
    ("Program.cs", 'var s = Environment.GetEnvironmentVariable("SECRET");', "SECRET"),
    ("app.php", "$x = getenv('APP_KEY');", "APP_KEY"),
    ("src/main.rs", 'let x = env::var("APP_KEY")', "APP_KEY"),
]


@pytest.mark.parametrize(("path", "line", "name"), ENV_READS, ids=[f"{r[2]}@{r[0]}" for r in ENV_READS])
def test_a_setting_read_in_code_is_recognized(path, line, name):
    assert found(path, added=[line]) == [("config_key", name, "added")]


def test_keys_of_a_dot_env_file_are_listed():
    assert found(".env.example", added=["# comment", "API_KEY=", "export DB_URL=postgres://x", "", "PORT=80"]) == [
        ("config_key", "API_KEY", "added"),
        ("config_key", "DB_URL", "added"),
        ("config_key", "PORT", "added"),
    ]


def test_keys_of_a_settings_file_are_listed_and_comments_are_not():
    assert found("config/settings.yaml", added=["# the port", "timeout: 30", "  retries: 3", "- item: x"]) == [
        ("config_key", "timeout", "added"),
        ("config_key", "retries", "added"),
    ]


def test_keys_of_a_json_settings_file_and_an_ini_file_are_listed():
    assert found("appsettings.json", added=['  "ConnectionStrings": {']) == [("config_key", "ConnectionStrings", "added")]
    assert found("app.ini", added=["[server]", "port = 80"]) == [("config_key", "port", "added")]


@pytest.mark.parametrize(
    "path",
    [
        "package.json",
        "tsconfig.json",
        "pyproject.toml",
        "jest.config.json",
        ".github/workflows/ci.yml",
        "docker-compose.yml",
        "data/orders.json",
        "tox.ini",
    ],
)
def test_tool_and_data_files_are_not_configuration(path):
    assert found(path, added=['  "name": "x"', "key: value"]) == []


def test_a_removed_setting_is_listed_as_removed_with_its_old_line():
    report = ci.check(make_diff("settings.py", removed=['URL = os.environ["ORDERS_URL"]'], before=["import os"]))
    assert report["interfaces"] == [
        {"file": "settings.py", "kind": "config_key", "name": "ORDERS_URL", "change": "removed", "line": 11}
    ]


# --- schema files ---


@pytest.mark.parametrize(
    "path",
    ["api/orders.proto", "schema.graphql", "api/user.avsc", "docs/openapi.yaml", "swagger.json", "events/order.schema.json"],
)
def test_a_schema_file_is_listed_once_by_name(path):
    report = ci.check(make_diff(path, added=["a", "b"], removed=["c"]))
    assert report["interfaces"] == [
        {"file": path, "kind": "schema_file", "name": Path(path).name, "change": "modified", "line": None}
    ]


def test_a_schema_file_that_is_new_or_deleted_says_so():
    assert found("api/orders.proto", added=["syntax = 'proto3';"], new=True) == [("schema_file", "orders.proto", "added")]
    assert found("api/orders.proto", removed=["syntax = 'proto3';"], deleted=True) == [
        ("schema_file", "orders.proto", "removed")
    ]


def test_a_schema_file_in_a_list_of_paths_is_listed_as_changed():
    report = ci.check("api/orders.proto\nsrc/app.py\n")
    assert report["interfaces"] == [
        {"file": "api/orders.proto", "kind": "schema_file", "name": "orders.proto", "change": "changed", "line": None}
    ]
    assert report["status"] == "ok"
    assert report["could_not_tell"] == [{"file": "src/app.py", "reason": "the input has no diff lines to read"}]
    assert "list of paths" in report["note"]


# --- added, removed or modified ---


def test_the_same_route_removed_and_added_is_modified():
    old, new = '@app.get("/orders")', '@app.get("/orders", response_model=Order)'
    assert found("api.py", removed=[old], added=[new]) == [("http_route", "GET /orders", "modified")]


def test_a_route_that_is_only_removed_is_removed():
    assert found("api.py", removed=['@app.delete("/orders/{id}")']) == [("http_route", "DELETE /orders/{id}", "removed")]


def test_a_route_on_an_unchanged_line_is_not_listed():
    assert found("api.py", before=['@app.get("/orders")'], added=["def new_helper(): ..."]) == []


def test_a_renamed_route_is_one_removed_and_one_added():
    assert found("api.py", removed=['@app.get("/old")'], added=['@app.get("/new")']) == [
        ("http_route", "GET /new", "added"),
        ("http_route", "GET /old", "removed"),
    ]


def test_a_commented_out_line_is_not_an_interface_but_a_rust_attribute_is():
    assert found("api.py", added=['# @app.get("/x")']) == []
    assert found("api.js", added=["// app.get('/x', h)"]) == []
    assert found("main.rs", added=['#[get("/x")]']) == [("http_route", "GET /x", "added")]


def test_interfaces_come_in_file_and_line_order():
    diff = make_diff("b.py", added=['@app.get("/b")']) + make_diff("a.py", added=['@app.get("/a")'])
    assert [e["file"] for e in ci.check(diff)["interfaces"]] == ["b.py", "a.py"]


# --- files it skips, and when it cannot tell ---


def test_test_files_are_skipped():
    report = ci.check(
        make_diff("tests/test_app.py", added=['@app.get("/x")']) + make_diff("web/app.spec.ts", added=["app.get('/y')"])
    )
    assert report["interfaces"] == []
    assert {e["file"]: e["reason"] for e in report["not_checked"]} == {
        "tests/test_app.py": "test file",
        "web/app.spec.ts": "test file",
    }


def test_a_change_to_documentation_only_has_no_interface_and_is_not_a_failure():
    report = ci.check(make_diff("README.md", added=["more words"]))
    assert report["status"] == "ok"
    assert report["interfaces"] == []
    assert "Only documentation" in report["note"]


def test_a_known_language_with_nothing_found_says_so():
    report = ci.check(make_diff("src/util.py", added=["def helper(): ..."]))
    assert report["status"] == "ok"
    assert report["interfaces"] == []
    assert "No interface was found" in report["note"]


def test_a_language_it_does_not_know_is_could_not_tell_and_lists_nothing():
    report = ci.check(make_diff("src/main.gleam", added=['pub fn route() { "/orders" }']))
    assert report["status"] == "could_not_tell"
    assert report["interfaces"] == []
    assert report["could_not_tell"] == [{"file": "src/main.gleam", "reason": "the script has no rules for .gleam files"}]


def test_an_unknown_language_next_to_a_known_one_is_listed_without_failing_the_rest():
    report = ci.check(make_diff("src/main.gleam", added=["x"]) + make_diff("api.py", added=['@app.get("/x")']))
    assert report["status"] == "ok"
    assert [e["name"] for e in report["interfaces"]] == ["GET /x"]
    assert [e["file"] for e in report["could_not_tell"]] == ["src/main.gleam"]


def test_a_list_of_paths_with_only_code_files_is_could_not_tell():
    report = ci.check("src/app.py\nsrc/util.py\n")
    assert report["status"] == "could_not_tell"
    assert report["interfaces"] == []
    assert len(report["could_not_tell"]) == 2


@pytest.mark.parametrize("text", ["", "\n\n", "@@ -1 +1 @@\n-a\n+b\n", "\x00\x01 binary �"])
def test_empty_and_malformed_input_is_no_input(text):
    report = ci.check(text)
    assert report["status"] == "no_input"
    assert report["interfaces"] == []
    assert report["note"]


def test_a_truncated_diff_does_not_crash():
    diff = make_diff("api.py", added=['@app.get("/a")', "def a(): ..."])
    for cut in range(0, len(diff), 7):
        ci.check(diff[:cut])


# --- running it ---


def run_cli(*args, stdin=""):
    return subprocess.run([sys.executable, str(SCRIPT), *args], input=stdin, capture_output=True, text=True, check=False)


def test_it_reads_stdin_and_prints_json_and_exits_0():
    result = run_cli(stdin=make_diff("api.py", added=['@app.get("/a")']))
    assert result.returncode == 0
    assert json.loads(result.stdout)["interfaces"][0]["name"] == "GET /a"


def test_it_reads_a_file(tmp_path):
    path = tmp_path / "pr.diff"
    path.write_text(make_diff("api.py", added=['@app.get("/a")']), encoding="utf-8")
    assert json.loads(run_cli(str(path)).stdout)["status"] == "ok"


def test_a_missing_file_exits_0_with_a_note(tmp_path):
    result = run_cli(str(tmp_path / "missing.diff"))
    report = json.loads(result.stdout)
    assert result.returncode == 0
    assert report["status"] == "no_input"
    assert "Could not read the input" in report["note"]


def test_help_documents_the_output():
    result = run_cli("--help")
    assert result.returncode == 0
    for text in ("http_route", "schema_file", "could_not_tell", "no_input", "modified", "not_checked"):
        assert text in result.stdout


# --- the fixtures that hold this script's output ---

FIXTURES = Path(__file__).resolve().parents[3] / "evals" / "qa-review" / "fixtures"
WITH_OUTPUT = sorted(path.parent.name for path in FIXTURES.glob("*/changed_interfaces.json"))


def test_some_fixtures_hold_the_output():
    assert {"interface-without-docs", "mixed-lens-change"} <= set(WITH_OUTPUT)


@pytest.mark.parametrize("fixture", WITH_OUTPUT)
def test_the_output_file_is_what_the_script_prints_for_the_fixture_diff(fixture):
    diff = (FIXTURES / fixture / "pr.diff").read_text(encoding="utf-8")
    expected = json.loads((FIXTURES / fixture / "changed_interfaces.json").read_text(encoding="utf-8"))
    assert ci.check(diff) == expected


def test_the_interface_fixture_lists_the_planted_flag():
    expected = json.loads((FIXTURES / "interface-without-docs" / "changed_interfaces.json").read_text(encoding="utf-8"))
    assert [(e["kind"], e["name"], e["change"]) for e in expected["interfaces"]] == [("cli", "--exclude", "added")]
