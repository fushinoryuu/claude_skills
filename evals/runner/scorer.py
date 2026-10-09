"""Score model output against a case. Scoring rules live in docs/eval-format.md."""

from dataclasses import dataclass

from evals.runner.loader import Case, Vocabulary

FALSE_POSITIVE_TAGS = {"clean", "tricky"}


@dataclass(frozen=True)
class RunScore:
    expected: int
    matched: int
    total: int
    unexpected: int
    forbidden: int
    max_findings: int
    invalid_categories: tuple[str, ...] = ()
    error: str | None = None

    @property
    def recall(self) -> float:
        return self.matched / self.expected if self.expected else 1.0

    @property
    def passed(self) -> bool:
        return (
            self.error is None
            and self.recall == 1.0
            and self.forbidden == 0
            and self.total <= self.max_findings
        )


@dataclass(frozen=True)
class RunRecord:
    score: RunScore
    output: str | None = None
    input_tokens: int = 0
    output_tokens: int = 0


@dataclass(frozen=True)
class CaseResult:
    case: Case
    runs: tuple[RunRecord, ...]
    pass_rate: float
    mean_recall: float
    unexpected_runs: int
    passed: bool


@dataclass(frozen=True)
class SkillSummary:
    recall: float | None
    false_positive_rate: float | None
    cases_passed: int
    cases_total: int


def _normalize_path(path: str) -> str:
    path = path.replace("\\", "/")
    return path.removeprefix("./")


def _matches(expected: dict, actual: dict) -> bool:
    """Every field named in the expectation must equal the actual field."""
    for key, want in expected.items():
        got = actual.get(key)
        if key == "file":
            if not isinstance(got, str) or _normalize_path(got) != _normalize_path(str(want)):
                return False
        elif got != want:
            return False
    return True


def score_run(case: Case, vocab: Vocabulary, findings: list[dict]) -> RunScore:
    """Match findings to expectations one-to-one, most specific expectation first."""
    unused = list(range(len(findings)))
    matched = 0
    for expected in sorted(case.expect.findings, key=len, reverse=True):
        hit = next((i for i in unused if _matches(expected, findings[i])), None)
        if hit is not None:
            unused.remove(hit)
            matched += 1

    keys = [f.get(vocab.key_field) for f in findings]
    return RunScore(
        expected=len(case.expect.findings),
        matched=matched,
        total=len(findings),
        unexpected=len(findings) - matched,
        forbidden=sum(1 for k in keys if k in case.expect.must_not_flag),
        max_findings=case.expect.max_findings,
        invalid_categories=tuple(sorted({str(k) for k in keys if k not in vocab.values})),
    )


def error_score(case: Case, error: str) -> RunScore:
    """A run that produced no usable findings (parse failure, refusal, API error)."""
    return RunScore(
        expected=len(case.expect.findings),
        matched=0,
        total=0,
        unexpected=0,
        forbidden=0,
        max_findings=case.expect.max_findings,
        error=error,
    )


def summarize_case(case: Case, runs: list[RunRecord], threshold: float) -> CaseResult:
    n = len(runs)
    pass_rate = sum(r.score.passed for r in runs) / n
    return CaseResult(
        case=case,
        runs=tuple(runs),
        pass_rate=pass_rate,
        mean_recall=sum(r.score.recall for r in runs) / n,
        unexpected_runs=sum(r.score.unexpected > 0 for r in runs),
        passed=pass_rate > threshold,
    )


def summarize_skill(results: list[CaseResult]) -> SkillSummary:
    defect_runs = [r for c in results if c.case.expect.findings for r in c.runs]
    fp_runs = [r for c in results if FALSE_POSITIVE_TAGS & set(c.case.tags) for r in c.runs]
    return SkillSummary(
        recall=sum(r.score.recall for r in defect_runs) / len(defect_runs) if defect_runs else None,
        false_positive_rate=(
            sum(r.score.unexpected > 0 for r in fp_runs) / len(fp_runs) if fp_runs else None
        ),
        cases_passed=sum(c.passed for c in results),
        cases_total=len(results),
    )
