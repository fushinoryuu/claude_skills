import json

import pytest

from evals.runner.__main__ import main
from evals.runner.client import Completion, FatalModelError, ModelError
from evals.runner.run import run_skill

FOUND = '```json\n{"findings": [{"category": "leftover-todo", "file": "src/app.py", "severity": "low", "summary": "x"}]}\n```'
NONE = '```json\n{"findings": []}\n```'


class FakeClient:
    """Answers by looking at which fixture is in the user message, like a perfect model."""

    def __init__(self, replies=None):
        self.calls = []
        self.replies = replies  # optional {fixture marker: reply or exception}

    def complete(self, system, user):
        self.calls.append((system, user))
        reply = FOUND if "TODO: handle empty names" in user else NONE
        if self.replies:
            reply = self.replies.get("*", reply)
        if isinstance(reply, Exception):
            raise reply
        if isinstance(reply, Completion):
            return reply
        return Completion(text=f"My review.\n\n{reply}", stop_reason="end_turn", input_tokens=10, output_tokens=5)


def run(skills_dir, evals_dir, client, **kwargs):
    return run_skill("todo-check", skills_dir=skills_dir, evals_dir=evals_dir, client=client, **kwargs)


def test_perfect_model_passes_every_case(skills_dir, evals_dir):
    result = run(skills_dir, evals_dir, FakeClient(), runs=3)
    assert result.passed
    assert [c.pass_rate for c in result.cases] == [1.0, 1.0]
    assert result.summary.recall == 1.0
    assert result.summary.false_positive_rate == 0.0
    assert (result.input_tokens, result.output_tokens) == (60, 30)


def test_prompt_contains_skill_and_fixture(skills_dir, evals_dir):
    client = FakeClient()
    run(skills_dir, evals_dir, client, case_id="todo-check-has-todo-01")
    system, user = client.calls[0]
    assert "# TODO check" in system
    assert '<file name="pr.diff">' in user
    assert user.endswith("Check this diff for leftover TODOs.")


def test_model_that_always_finds_something_fails_the_clean_case(skills_dir, evals_dir):
    result = run(skills_dir, evals_dir, FakeClient({"*": FOUND}))
    by_id = {c.case.id: c for c in result.cases}
    assert by_id["todo-check-has-todo-01"].passed
    assert not by_id["todo-check-no-todo-01"].passed
    assert result.summary.false_positive_rate == 1.0


def test_model_that_misses_defects_fails_the_defect_case(skills_dir, evals_dir):
    result = run(skills_dir, evals_dir, FakeClient({"*": NONE}))
    assert not result.passed
    assert result.summary.recall == 0.0


def test_output_without_block_is_a_failed_run(skills_dir, evals_dir):
    reply = Completion(text="Looks fine to me.", stop_reason="end_turn")
    result = run(skills_dir, evals_dir, FakeClient({"*": reply}), case_id="todo-check-no-todo-01")
    record = result.cases[0].runs[0]
    assert record.score.error.startswith("parse_error")
    assert not result.passed


@pytest.mark.parametrize("stop_reason, expected", [("refusal", "model refused"), ("max_tokens", "truncated")])
def test_refusal_and_truncation_are_failed_runs(skills_dir, evals_dir, stop_reason, expected):
    reply = Completion(text=NONE, stop_reason=stop_reason)
    result = run(skills_dir, evals_dir, FakeClient({"*": reply}), case_id="todo-check-no-todo-01")
    assert expected in result.cases[0].runs[0].score.error


def test_non_fatal_model_error_is_recorded_and_eval_continues(skills_dir, evals_dir):
    result = run(skills_dir, evals_dir, FakeClient({"*": ModelError("RateLimitError: slow down")}))
    assert len(result.cases) == 2
    assert all("RateLimitError" in c.runs[0].score.error for c in result.cases)


def test_fatal_model_error_aborts(skills_dir, evals_dir):
    with pytest.raises(FatalModelError):
        run(skills_dir, evals_dir, FakeClient({"*": FatalModelError("AuthenticationError")}))


# --- CLI ---


def cli(skills_dir, evals_dir, tmp_path, *extra, client=None):
    argv = [
        "--skill", "todo-check",
        "--skills-dir", str(skills_dir),
        "--evals-dir", str(evals_dir),
        "--results-dir", str(tmp_path / "results"),
        *extra,
    ]  # fmt: skip
    return main(argv, client=client)


def test_cli_prints_summary_and_writes_results_file(skills_dir, evals_dir, tmp_path, capsys):
    code = cli(skills_dir, evals_dir, tmp_path, "--runs", "2", client=FakeClient())
    assert code == 0
    out = capsys.readouterr().out
    assert "todo-check-has-todo-01" in out
    assert "PASS" in out
    assert "recall: 1.00" in out

    [path] = (tmp_path / "results").glob("*-todo-check.json")
    payload = json.loads(path.read_text())
    assert payload["skill"] == "todo-check"
    assert payload["runs_per_case"] == 2
    assert payload["summary"]["cases_passed"] == 2
    assert len(payload["cases"][0]["runs"]) == 2


def test_cli_exit_code_is_1_when_a_case_fails(skills_dir, evals_dir, tmp_path):
    assert cli(skills_dir, evals_dir, tmp_path, client=FakeClient({"*": NONE})) == 1


def test_cli_exit_code_is_2_for_unknown_case(skills_dir, evals_dir, tmp_path, capsys):
    code = cli(skills_dir, evals_dir, tmp_path, "--case", "nope", client=FakeClient())
    assert code == 2
    assert "no case 'nope'" in capsys.readouterr().err


def test_cli_exit_code_is_2_for_fatal_model_error(skills_dir, evals_dir, tmp_path):
    client = FakeClient({"*": FatalModelError("AuthenticationError: bad key")})
    assert cli(skills_dir, evals_dir, tmp_path, client=client) == 2


def test_cli_dry_run_prints_prompts_without_calling_the_model(skills_dir, evals_dir, tmp_path, capsys):
    client = FakeClient()
    assert cli(skills_dir, evals_dir, tmp_path, "--dry-run", client=client) == 0
    out = capsys.readouterr().out
    assert "=== SYSTEM ===" in out
    assert "=== USER (todo-check-has-todo-01) ===" in out
    assert client.calls == []
    assert not (tmp_path / "results").exists()


@pytest.mark.parametrize("flag, value", [("--runs", "0"), ("--threshold", "1")])
def test_cli_rejects_bad_numbers(skills_dir, evals_dir, tmp_path, flag, value):
    with pytest.raises(SystemExit):
        cli(skills_dir, evals_dir, tmp_path, flag, value, client=FakeClient())
