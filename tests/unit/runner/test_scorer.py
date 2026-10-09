from evals.runner.loader import Case, Expect, Vocabulary
from evals.runner.scorer import (
    RunRecord,
    error_score,
    score_run,
    summarize_case,
    summarize_skill,
)

VOCAB = Vocabulary(key_field="category", values=frozenset({"a", "b", "c"}))


def make_case(findings=(), must_not_flag=(), max_findings=5, tags=()):
    return Case(
        id="skill-fixture-01",
        skill="skill",
        fixture="fixture",
        prompt="p",
        expect=Expect(
            findings=tuple(findings),
            must_not_flag=frozenset(must_not_flag),
            max_findings=max_findings,
        ),
        tags=tuple(tags),
    )


def finding(category, file="src/x.py", **extra):
    return {"category": category, "file": file, **extra}


def test_exact_match_passes():
    case = make_case([{"category": "a", "file": "src/x.py"}])
    score = score_run(case, VOCAB, [finding("a")])
    assert (score.matched, score.unexpected, score.recall) == (1, 0, 1.0)
    assert score.passed


def test_missing_expected_finding_fails_with_partial_recall():
    case = make_case([{"category": "a"}, {"category": "b"}])
    score = score_run(case, VOCAB, [finding("a")])
    assert score.recall == 0.5
    assert not score.passed


def test_unexpected_finding_is_counted_but_does_not_fail_within_limit():
    case = make_case([{"category": "a"}], max_findings=3)
    score = score_run(case, VOCAB, [finding("a"), finding("b")])
    assert score.unexpected == 1
    assert score.passed


def test_exceeding_max_findings_fails():
    case = make_case([{"category": "a"}], max_findings=1)
    assert not score_run(case, VOCAB, [finding("a"), finding("b")]).passed


def test_clean_case_with_no_findings_passes():
    score = score_run(make_case(max_findings=0), VOCAB, [])
    assert score.recall == 1.0
    assert score.passed


def test_clean_case_with_invented_finding_fails():
    score = score_run(make_case(max_findings=0), VOCAB, [finding("a")])
    assert score.unexpected == 1
    assert not score.passed


def test_must_not_flag_fails_even_within_limit():
    case = make_case([{"category": "a"}], must_not_flag=["b"], max_findings=5)
    score = score_run(case, VOCAB, [finding("a"), finding("b")])
    assert score.forbidden == 1
    assert not score.passed


def test_file_paths_are_normalized():
    case = make_case([{"category": "a", "file": "src/x.py"}])
    assert score_run(case, VOCAB, [finding("a", file=".\\src\\x.py")]).matched == 1


def test_wrong_file_does_not_match():
    case = make_case([{"category": "a", "file": "src/x.py"}])
    assert score_run(case, VOCAB, [finding("a", file="src/y.py")]).matched == 0


def test_unspecified_fields_are_not_checked():
    case = make_case([{"category": "a"}])
    score = score_run(case, VOCAB, [finding("a", file="anything.py", severity="high", line=9)])
    assert score.matched == 1


def test_matching_is_one_to_one():
    case = make_case([{"category": "a"}], max_findings=5)
    score = score_run(case, VOCAB, [finding("a"), finding("a")])
    assert (score.matched, score.unexpected) == (1, 1)


def test_more_specific_expectation_matched_first():
    case = make_case([{"category": "a"}, {"category": "a", "file": "src/x.py"}])
    score = score_run(case, VOCAB, [finding("a", file="src/x.py"), finding("a", file="src/y.py")])
    assert score.matched == 2


def test_out_of_vocabulary_category_is_reported_and_unexpected():
    score = score_run(make_case(max_findings=0), VOCAB, [finding("made-up")])
    assert score.invalid_categories == ("made-up",)
    assert score.unexpected == 1


def test_finding_without_key_field_is_unexpected():
    score = score_run(make_case([{"category": "a"}]), VOCAB, [{"file": "src/x.py"}])
    assert score.matched == 0
    assert score.invalid_categories == ("None",)


def test_error_score_never_passes():
    score = error_score(make_case(max_findings=0), "parse_error: nope")
    assert not score.passed
    assert score.error == "parse_error: nope"


def test_error_score_on_defect_case_has_zero_recall():
    assert error_score(make_case([{"category": "a"}]), "x").recall == 0.0


def record(case, findings):
    return RunRecord(score=score_run(case, VOCAB, findings))


def test_case_passes_on_majority_of_runs():
    case = make_case([{"category": "a"}])
    runs = [record(case, [finding("a")]), record(case, [finding("a")]), record(case, [])]
    result = summarize_case(case, runs, threshold=0.5)
    assert result.pass_rate == 2 / 3
    assert result.passed


def test_case_with_exactly_half_passing_does_not_pass():
    case = make_case([{"category": "a"}])
    runs = [record(case, [finding("a")]), record(case, [])]
    assert not summarize_case(case, runs, threshold=0.5).passed


def test_case_counts_runs_with_unexpected_findings():
    case = make_case(max_findings=0)
    runs = [record(case, []), record(case, [finding("a")])]
    assert summarize_case(case, runs, 0.5).unexpected_runs == 1


def test_skill_summary_splits_recall_and_false_positive_measures():
    defect = make_case([{"category": "a"}], tags=["defect"])
    clean = make_case(max_findings=0, tags=["clean"])
    results = [
        summarize_case(defect, [record(defect, [finding("a")]), record(defect, [])], 0.5),
        summarize_case(clean, [record(clean, []), record(clean, [finding("b")])], 0.5),
    ]
    summary = summarize_skill(results)
    assert summary.recall == 0.5
    assert summary.false_positive_rate == 0.5
    assert (summary.cases_passed, summary.cases_total) == (0, 2)


def test_skill_summary_reports_none_when_no_applicable_cases():
    defect = make_case([{"category": "a"}], tags=["defect"])
    summary = summarize_skill([summarize_case(defect, [record(defect, [finding("a")])], 0.5)])
    assert summary.false_positive_rate is None
    clean = make_case(max_findings=0, tags=["clean"])
    summary = summarize_skill([summarize_case(clean, [record(clean, [])], 0.5)])
    assert summary.recall is None
