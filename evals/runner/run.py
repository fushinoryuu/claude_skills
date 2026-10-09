"""Run a skill's eval cases against a model and score them."""

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from evals.runner.client import FatalModelError, ModelClient, ModelError
from evals.runner.loader import (
    Case,
    Vocabulary,
    load_cases,
    load_fixture,
    load_vocabulary,
)
from evals.runner.parser import ParseError, parse_findings
from evals.runner.prompt import (
    Skill,
    build_system_prompt,
    build_user_message,
    load_skill,
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
class SkillRun:
    skill: str
    cases: list[CaseResult]
    summary: SkillSummary

    @property
    def passed(self) -> bool:
        return all(c.passed for c in self.cases)

    @property
    def input_tokens(self) -> int:
        return sum(r.input_tokens for c in self.cases for r in c.runs)

    @property
    def output_tokens(self) -> int:
        return sum(r.output_tokens for c in self.cases for r in c.runs)


def execute_run(case: Case, vocab: Vocabulary, system: str, user: str, client: ModelClient) -> RunRecord:
    """One model call, scored. Failures that are not fatal become a failed run."""
    try:
        completion = client.complete(system, user)
    except FatalModelError:
        raise
    except ModelError as e:
        return RunRecord(score=error_score(case, str(e)))

    usage = {"input_tokens": completion.input_tokens, "output_tokens": completion.output_tokens}
    if completion.stop_reason == "refusal":
        return RunRecord(score=error_score(case, "model refused"), output=completion.text, **usage)
    if completion.stop_reason == "max_tokens":
        return RunRecord(
            score=error_score(case, "output truncated at max_tokens"), output=completion.text, **usage
        )
    try:
        findings = parse_findings(completion.text)
    except ParseError as e:
        return RunRecord(score=error_score(case, f"parse_error: {e}"), output=completion.text, **usage)
    return RunRecord(score=score_run(case, vocab, findings), output=completion.text, **usage)


def prepare(skills_dir: Path, evals_dir: Path, skill_name: str, case_id: str | None):
    """Load everything a run needs. Raises EvalConfigError before any model call."""
    skill: Skill = load_skill(skills_dir, skill_name)
    vocab = load_vocabulary(evals_dir, skill_name)
    cases = load_cases(evals_dir, skill_name, vocab, case_id)
    system = build_system_prompt(skill)
    prompts = {
        case.id: build_user_message(load_fixture(evals_dir, skill_name, case.fixture), case.prompt)
        for case in cases
    }
    return vocab, cases, system, prompts


def run_skill(
    skill_name: str,
    *,
    skills_dir: Path,
    evals_dir: Path,
    client: ModelClient,
    case_id: str | None = None,
    runs: int = 1,
    threshold: float = 0.5,
    progress: Callable[[str], None] = lambda _: None,
) -> SkillRun:
    vocab, cases, system, prompts = prepare(skills_dir, evals_dir, skill_name, case_id)
    results = []
    for case in cases:
        records = []
        for i in range(1, runs + 1):
            record = execute_run(case, vocab, system, prompts[case.id], client)
            records.append(record)
            status = "pass" if record.score.passed else f"FAIL ({record.score.error or 'see output'})"
            progress(f"{case.id} run {i}/{runs}: {status}")
        results.append(summarize_case(case, records, threshold))
    return SkillRun(skill=skill_name, cases=results, summary=summarize_skill(results))
