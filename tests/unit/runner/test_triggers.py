import json
import threading
import time
from dataclasses import replace

import pytest

from evals.runner.__main__ import main
from evals.runner.client import Completion, FatalModelError, ModelError
from evals.runner.loader import EvalConfigError
from evals.runner.skills import SkillInfo
from evals.runner.triggers import (
    PickError,
    build_router_prompt,
    load_triggers,
    parse_pick,
    run_triggers,
)

NAMES = ["pr-review", "failure-analysis"]


# --- parse_pick ---


@pytest.mark.parametrize(
    "text, expected",
    [
        ("pr-review", "pr-review"),
        ("none", None),
        ("None.", None),
        ("  `pr-review`  ", "pr-review"),
        ("PR-Review", "pr-review"),
        ('"failure-analysis"', "failure-analysis"),
        ("skill: pr-review", "pr-review"),
        ("It is about a PR, so:\n\n**pr-review**", "pr-review"),
        ("pr-review\n\n", "pr-review"),
    ],
)
def test_parse_pick(text, expected):
    assert parse_pick(text, NAMES) == expected


@pytest.mark.parametrize("text", ["", "   \n", "maybe pr-review?", "other-skill"])
def test_parse_pick_rejects_unrecognized_answers(text):
    with pytest.raises(PickError):
        parse_pick(text, NAMES)


# --- loading and prompt ---


def test_loads_sample_triggers(evals_dir):
    prompts = load_triggers(evals_dir, "todo-check")
    assert sum(p.should_trigger for p in prompts) == 3
    assert sum(not p.should_trigger for p in prompts) == 4


@pytest.mark.parametrize(
    "content, message",
    [
        ("should_trigger: [a]\n", "should_not_trigger"),
        ("should_trigger: a\nshould_not_trigger: [b]\n", "should_trigger"),
        ("should_trigger: ['']\nshould_not_trigger: [b]\n", "non-empty"),
        ("should_trigger: []\nshould_not_trigger: []\n", "no trigger prompts"),
        ("- a\n- b\n", "expected a mapping"),
    ],
)
def test_invalid_triggers_file(tmp_path, content, message):
    (tmp_path / "s").mkdir()
    (tmp_path / "s" / "triggers.yaml").write_text(content)
    with pytest.raises(EvalConfigError, match=message):
        load_triggers(tmp_path, "s")


def test_missing_triggers_file(tmp_path):
    with pytest.raises(EvalConfigError, match="missing"):
        load_triggers(tmp_path, "s")


def test_router_prompt_lists_every_skill_with_description_only():
    prompt = build_router_prompt([SkillInfo("a", "a", "Does A."), SkillInfo("b", "b", "Does B.")])
    assert '<skill name="a">Does A.</skill>' in prompt
    assert '<skill name="b">Does B.</skill>' in prompt
    assert "final line" in prompt


# --- running ---


def make_skills(tmp_path):
    for name, desc in (("pr-review", "Reviews pull requests."), ("failure-analysis", "Classifies test failures.")):
        (tmp_path / "skills" / name).mkdir(parents=True)
        (tmp_path / "skills" / name / "SKILL.md").write_text(f"---\nname: {name}\ndescription: {desc}\n---\n")
    (tmp_path / "evals" / "pr-review").mkdir(parents=True)
    (tmp_path / "evals" / "pr-review" / "triggers.yaml").write_text(
        "should_trigger:\n  - review this PR\n  - check my pull request\n"
        "should_not_trigger:\n  - why did this test fail\n  - write a date parser\n"
    )
    return tmp_path / "skills", tmp_path / "evals"


class Router:
    """A router that maps keywords in the prompt to a skill, ending with the answer line."""

    def __init__(self, rules=None, fail=None):
        default = {"PR": "pr-review", "pull request": "pr-review", "fail": "failure-analysis"}
        self.rules = default if rules is None else rules
        self.fail = fail
        self.systems = []

    def complete(self, system, user):
        self.systems.append(system)
        if self.fail:
            raise self.fail
        answer = next((skill for key, skill in self.rules.items() if key in user), "none")
        return Completion(text=f"Reasoning here.\n{answer}", stop_reason="end_turn", input_tokens=4, output_tokens=2)


def test_perfect_router_scores_everything(tmp_path):
    skills, evals = make_skills(tmp_path)
    result = run_triggers("pr-review", skills_dir=skills, evals_dir=evals, client=Router(), runs=2)
    assert result.passed
    assert (result.accuracy, result.trigger_recall, result.false_trigger_rate) == (1.0, 1.0, 0.0)
    assert (result.input_tokens, result.output_tokens) == (32, 16)


def test_router_sees_the_whole_catalog_but_no_skill_body(tmp_path):
    skills, evals = make_skills(tmp_path)
    router = Router()
    run_triggers("pr-review", skills_dir=skills, evals_dir=evals, client=router)
    assert '<skill name="failure-analysis">' in router.systems[0]
    assert "Reviews pull requests." in router.systems[0]


def test_router_that_never_triggers_has_zero_recall(tmp_path):
    skills, evals = make_skills(tmp_path)
    result = run_triggers("pr-review", skills_dir=skills, evals_dir=evals, client=Router(rules={"zzz": "pr-review"}))
    assert result.trigger_recall == 0.0
    assert result.false_trigger_rate == 0.0
    assert not result.passed


def test_router_that_always_triggers_has_false_triggers(tmp_path):
    skills, evals = make_skills(tmp_path)
    router = Router(rules={"": "pr-review"})
    result = run_triggers("pr-review", skills_dir=skills, evals_dir=evals, client=router)
    assert result.trigger_recall == 1.0
    assert result.false_trigger_rate == 1.0
    assert result.accuracy == 0.5


def test_picking_another_skill_counts_as_correct_for_should_not_trigger(tmp_path):
    skills, evals = make_skills(tmp_path)
    result = run_triggers("pr-review", skills_dir=skills, evals_dir=evals, client=Router())
    prompt = next(p for p in result.prompts if p.prompt.text == "why did this test fail")
    assert prompt.runs[0].picked == "failure-analysis"
    assert prompt.passed


def test_unparseable_answer_is_an_incorrect_run(tmp_path):
    skills, evals = make_skills(tmp_path)

    class Rambler:
        def complete(self, system, user):
            return Completion(text="Hmm, hard to say.", stop_reason="end_turn")

    result = run_triggers("pr-review", skills_dir=skills, evals_dir=evals, client=Rambler())
    assert all(p.runs[0].error.startswith("parse_error") for p in result.prompts)
    assert result.accuracy == 0.0


def test_non_fatal_error_is_recorded_and_fatal_aborts(tmp_path):
    skills, evals = make_skills(tmp_path)
    result = run_triggers("pr-review", skills_dir=skills, evals_dir=evals, client=Router(fail=ModelError("RateLimitError")))
    assert result.prompts[0].runs[0].error == "RateLimitError"
    with pytest.raises(FatalModelError):
        run_triggers("pr-review", skills_dir=skills, evals_dir=evals, client=Router(fail=FatalModelError("bad key")))


def test_unknown_skill_raises(tmp_path):
    skills, evals = make_skills(tmp_path)
    with pytest.raises(EvalConfigError, match="not found"):
        run_triggers("nope", skills_dir=skills, evals_dir=evals, client=Router())


# --- CLI ---


def cli(tmp_path, *extra, client=None):
    skills, evals = make_skills(tmp_path)
    argv = [
        "--skill", "pr-review", "--triggers",
        "--skills-dir", str(skills), "--evals-dir", str(evals),
        "--results-dir", str(tmp_path / "results"),
        *extra,
    ]  # fmt: skip
    return main(argv, client=client)


def test_cli_triggers_prints_summary_and_writes_results(tmp_path, capsys):
    assert cli(tmp_path, "--runs", "2", client=Router()) == 0
    out = capsys.readouterr().out
    assert "accuracy: 1.00" in out
    assert "false-trigger rate: 0.00" in out
    [path] = (tmp_path / "results").glob("*-pr-review-triggers.json")
    payload = json.loads(path.read_text())
    assert payload["mode"] == "triggers"
    assert payload["runs_per_prompt"] == 2
    assert len(payload["prompts"]) == 4


def test_cli_triggers_exit_code_1_on_failure(tmp_path):
    assert cli(tmp_path, client=Router(rules={})) == 1


def test_cli_triggers_dry_run(tmp_path, capsys):
    router = Router()
    assert cli(tmp_path, "--dry-run", client=router) == 0
    out = capsys.readouterr().out
    assert "=== USER (should_trigger) ===\nreview this PR" in out
    assert "=== USER (should_not_trigger) ===" in out
    assert router.systems == []


def test_cli_rejects_case_with_triggers(tmp_path):
    with pytest.raises(SystemExit):
        cli(tmp_path, "--case", "x", client=Router())


def test_cli_rejects_tag_with_triggers(tmp_path, capsys):
    with pytest.raises(SystemExit):
        cli(tmp_path, "--tag", "defect", client=Router())
    assert "cannot be combined with --triggers" in capsys.readouterr().err


# --- running calls at the same time ---


class MeetingRouter(Router):
    """Every call waits until `n` calls are inside at once."""

    def __init__(self, n):
        super().__init__()
        self.barrier = threading.Barrier(n, timeout=5)

    def complete(self, system, user):
        self.barrier.wait()
        return super().complete(system, user)


def test_trigger_calls_overlap_when_jobs_is_more_than_one(tmp_path):
    skills, evals = make_skills(tmp_path)
    router = MeetingRouter(4)
    result = run_triggers("pr-review", skills_dir=skills, evals_dir=evals, client=router, jobs=4, warm_cache=False)
    assert result.passed


def test_trigger_results_and_progress_are_per_prompt_in_prompt_order(tmp_path):
    skills, evals = make_skills(tmp_path)
    messages = []
    result = run_triggers(
        "pr-review", skills_dir=skills, evals_dir=evals, client=Router(), runs=3, jobs=6, progress=messages.append
    )
    assert [p.prompt.text for p in result.prompts] == [
        "review this PR",
        "check my pull request",
        "why did this test fail",
        "write a date parser",
    ]
    assert all(len(p.runs) == 3 for p in result.prompts)
    assert len(messages) == 4
    assert "'review this PR': 100%" in "\n".join(messages)


def test_the_first_trigger_call_goes_alone_so_the_others_can_read_the_cache(tmp_path):
    skills, evals = make_skills(tmp_path)
    events, lock = [], threading.Lock()

    class Logging(Router):
        def complete(self, system, user):
            with lock:
                events.append("start")
            time.sleep(0.1)
            completion = super().complete(system, user)
            with lock:
                events.append("end")
            return completion

    run_triggers("pr-review", skills_dir=skills, evals_dir=evals, client=Logging(), runs=2, jobs=8)
    assert events[:2] == ["start", "end"]


def test_a_fatal_error_ends_a_parallel_trigger_run(tmp_path):
    skills, evals = make_skills(tmp_path)
    router = Router(fail=FatalModelError("bad key"))
    with pytest.raises(FatalModelError):
        run_triggers("pr-review", skills_dir=skills, evals_dir=evals, client=router, runs=2, jobs=4)


def test_cli_triggers_reports_cache_tokens_and_how_the_run_was_made(tmp_path, capsys):
    class Caching(Router):
        def complete(self, system, user):
            return replace(super().complete(system, user), cache_write_tokens=5, cache_read_tokens=7)

    assert cli(tmp_path, "--jobs", "2", client=Caching()) == 0
    out = capsys.readouterr().out
    assert "tokens: 16 in, 8 out, 20 cache write, 28 cache read" in out
    assert "jobs: 2   prompt cache: on" in out
    [path] = (tmp_path / "results").glob("*-pr-review-triggers.json")
    payload = json.loads(path.read_text())
    assert payload["summary"]["cache_read_tokens"] == 28
    assert payload["jobs"] == 2
