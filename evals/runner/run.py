"""Run a skill's eval cases against a model and score them."""

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from evals.runner.client import FatalModelError, ModelClient, ModelError
from evals.runner.loader import (
    Case,
    Vocabulary,
    count_cases,
    load_cases,
    load_fixture,
    load_vocabulary,
)
from evals.runner.parallel import run_all
from evals.runner.parser import (
    ParseError,
    extract_comment,
    parse_findings,
    parse_lenses_applied,
)
from evals.runner.prompt import (
    Skill,
    build_system_prompt,
    build_user_message,
    load_skill,
    with_lenses,
)
from evals.runner.scorer import (
    CaseResult,
    RunRecord,
    SkillSummary,
    error_score,
    score_run,
    summarize_case,
    summarize_skill,
)


@dataclass(frozen=True)
class Selection:
    """What a partial run was limited to, so its numbers are not mistaken for a full run."""

    case: str | None
    tags: tuple[str, ...]
    available: int  # how many cases the skill has


@dataclass(frozen=True)
class SkillRun:
    skill: str
    cases: list[CaseResult]
    summary: SkillSummary
    selection: Selection | None = None  # None: every case ran

    @property
    def passed(self) -> bool:
        return all(c.passed for c in self.cases)

    @property
    def input_tokens(self) -> int:
        return sum(r.input_tokens for c in self.cases for r in c.runs)

    @property
    def output_tokens(self) -> int:
        return sum(r.output_tokens for c in self.cases for r in c.runs)

    @property
    def cache_write_tokens(self) -> int:
        return sum(r.cache_write_tokens for c in self.cases for r in c.runs)

    @property
    def cache_read_tokens(self) -> int:
        return sum(r.cache_read_tokens for c in self.cases for r in c.runs)


def execute_run(case: Case, vocab: Vocabulary, system: str, user: str, client: ModelClient) -> RunRecord:
    """One model call, scored. Failures that are not fatal become a failed run."""
    try:
        completion = client.complete(system, user)
    except FatalModelError:
        raise
    except ModelError as e:
        return RunRecord(score=error_score(case, str(e)))

    usage = {
        "input_tokens": completion.input_tokens,
        "output_tokens": completion.output_tokens,
        "cache_write_tokens": completion.cache_write_tokens,
        "cache_read_tokens": completion.cache_read_tokens,
    }
    if completion.stop_reason == "refusal":
        return RunRecord(score=error_score(case, "model refused"), output=completion.text, **usage)
    if completion.stop_reason == "max_tokens":
        return RunRecord(
            score=error_score(case, "output truncated at max_tokens"), output=completion.text, **usage
        )
    try:
        findings = parse_findings(completion.text)
        lenses_applied = parse_lenses_applied(completion.text)
    except ParseError as e:
        return RunRecord(score=error_score(case, f"parse_error: {e}"), output=completion.text, **usage)
    comment_words = None
    if case.expect.max_comment_words is not None:
        comment = extract_comment(completion.text, vocab.comment_start)
        comment_words = None if comment is None else len(comment.split())
    score = score_run(case, vocab, findings, lenses_applied, comment_words)
    return RunRecord(score=score, output=completion.text, **usage)


def prepare(
    skills_dir: Path, evals_dir: Path, skill_name: str, case_id: str | None, tags: tuple[str, ...] = ()
):
    """Load everything a run needs. Raises EvalConfigError before any model call."""
    skill: Skill = load_skill(skills_dir, skill_name)
    vocab = load_vocabulary(evals_dir, skill_name)
    cases = load_cases(evals_dir, skill_name, vocab, case_id, tags)
    systems = {case.id: build_system_prompt(with_lenses(skill, case.lenses)) for case in cases}
    prompts = {
        case.id: build_user_message(load_fixture(evals_dir, skill_name, case.fixture), case.prompt)
        for case in cases
    }
    return vocab, cases, systems, prompts


def run_skill(
    skill_name: str,
    *,
    skills_dir: Path,
    evals_dir: Path,
    client: ModelClient,
    case_id: str | None = None,
    tags: tuple[str, ...] = (),
    runs: int = 1,
    threshold: float = 0.5,
    jobs: int = 1,
    warm_cache: bool = True,
    progress: Callable[[str], None] = lambda _: None,
) -> SkillRun:
    """Run every selected case `runs` times. Results are in case order however the calls finish.

    With `jobs` above 1 the calls run at the same time. With `warm_cache` the first call for each distinct system
    prompt goes alone first, so the calls after it can read the cached prompt.
    """
    vocab, cases, systems, prompts = prepare(skills_dir, evals_dir, skill_name, case_id, tags)
    calls = [(case, i) for case in cases for i in range(1, runs + 1)]

    def report(call, record):
        case, i = call
        reason = record.score.error or record.score.lens_problem or record.score.comment_problem or "see output"
        status = "pass" if record.score.passed else f"FAIL ({reason})"
        progress(f"{case.id} run {i}/{runs}: {status}")

    records = run_all(
        calls,
        lambda call: execute_run(call[0], vocab, systems[call[0].id], prompts[call[0].id], client),
        jobs=jobs,
        warm_key=(lambda call: systems[call[0].id]) if warm_cache else None,
        done=report,
    )

    results = [
        summarize_case(case, [record for (c, _), record in zip(calls, records) if c is case], threshold)
        for case in cases
    ]
    selection = None
    if case_id is not None or tags:
        selection = Selection(case_id, tags, count_cases(evals_dir, skill_name))
    return SkillRun(skill=skill_name, cases=results, summary=summarize_skill(results), selection=selection)
