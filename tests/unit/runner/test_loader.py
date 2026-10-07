from pathlib import Path

import pytest
import yaml

from evals.runner.loader import (
    EvalConfigError,
    load_cases,
    load_fixture,
    load_vocabulary,
)

SKILL = "todo-check"


def test_loads_vocabulary(evals_dir):
    vocab = load_vocabulary(evals_dir, SKILL)
    assert vocab.key_field == "category"
    assert vocab.values == {"leftover-todo"}


def test_loads_all_sample_cases(evals_dir):
    vocab = load_vocabulary(evals_dir, SKILL)
    cases = load_cases(evals_dir, SKILL, vocab)
    assert [c.id for c in cases] == ["todo-check-has-todo-01", "todo-check-no-todo-01"]
    assert cases[0].expect.findings == ({"category": "leftover-todo", "file": "src/app.py"},)
    assert cases[1].expect.findings == ()
    assert cases[1].tags == ("clean",)


def test_loads_single_case_by_id(evals_dir):
    vocab = load_vocabulary(evals_dir, SKILL)
    cases = load_cases(evals_dir, SKILL, vocab, "todo-check-no-todo-01")
    assert [c.id for c in cases] == ["todo-check-no-todo-01"]


def test_unknown_case_lists_available_ones(evals_dir):
    vocab = load_vocabulary(evals_dir, SKILL)
    with pytest.raises(EvalConfigError, match="todo-check-has-todo-01"):
        load_cases(evals_dir, SKILL, vocab, "nope")


def test_loads_fixture_files(evals_dir):
    files = load_fixture(evals_dir, SKILL, "has-todo")
    assert list(files) == ["pr.diff"]
    assert "TODO" in files["pr.diff"]


def test_missing_fixture_raises(evals_dir):
    with pytest.raises(EvalConfigError, match="missing fixture"):
        load_fixture(evals_dir, SKILL, "absent")


def test_missing_vocabulary_raises(tmp_path):
    with pytest.raises(EvalConfigError, match="missing"):
        load_vocabulary(tmp_path, "nothing")


# --- case validation, using small throwaway eval folders ---


def write_eval(tmp_path: Path, case: dict, values=("a", "b")) -> Path:
    skill_dir = tmp_path / "s"
    (skill_dir / "cases").mkdir(parents=True)
    (skill_dir / "categories.yaml").write_text(
        yaml.safe_dump({"key_field": "category", "values": list(values)})
    )
    (skill_dir / "cases" / "s-f-01.yaml").write_text(yaml.safe_dump(case))
    return tmp_path


def good_case(**overrides) -> dict:
    case = {
        "id": "s-f-01",
        "skill": "s",
        "fixture": "f",
        "prompt": "p",
        "expect": {"findings": [{"category": "a"}], "max_findings": 3},
    }
    case.update(overrides)
    return case


def load(tmp_path: Path, case: dict):
    evals = write_eval(tmp_path, case)
    return load_cases(evals, "s", load_vocabulary(evals, "s"))


def test_valid_case_loads(tmp_path):
    assert load(tmp_path, good_case())[0].expect.max_findings == 3


@pytest.mark.parametrize("field", ["id", "skill", "fixture", "prompt", "expect"])
def test_missing_required_field(tmp_path, field):
    case = good_case()
    del case[field]
    with pytest.raises(EvalConfigError, match=f"missing required field '{field}'"):
        load(tmp_path, case)


def test_id_must_match_file_name(tmp_path):
    with pytest.raises(EvalConfigError, match="must equal the file name"):
        load(tmp_path, good_case(id="other"))


def test_skill_must_match_folder(tmp_path):
    with pytest.raises(EvalConfigError, match="does not match folder"):
        load(tmp_path, good_case(skill="other"))


def test_unknown_category_in_expectation(tmp_path):
    case = good_case(expect={"findings": [{"category": "zzz"}], "max_findings": 1})
    with pytest.raises(EvalConfigError, match="not in categories.yaml"):
        load(tmp_path, case)


def test_expected_finding_needs_key_field(tmp_path):
    case = good_case(expect={"findings": [{"file": "x.py"}], "max_findings": 1})
    with pytest.raises(EvalConfigError, match="key field"):
        load(tmp_path, case)


def test_unknown_must_not_flag_slug(tmp_path):
    case = good_case(expect={"findings": [], "must_not_flag": ["zzz"], "max_findings": 1})
    with pytest.raises(EvalConfigError, match="must_not_flag"):
        load(tmp_path, case)


@pytest.mark.parametrize("bad", [-1, "3", None, True])
def test_max_findings_must_be_non_negative_int(tmp_path, bad):
    case = good_case(expect={"findings": [], "max_findings": bad})
    with pytest.raises(EvalConfigError, match="max_findings"):
        load(tmp_path, case)


def test_unsupported_scorer(tmp_path):
    with pytest.raises(EvalConfigError, match="unsupported scorer"):
        load(tmp_path, good_case(scorer="set"))


def test_invalid_yaml(tmp_path):
    evals = write_eval(tmp_path, good_case())
    (evals / "s" / "cases" / "s-f-01.yaml").write_text("id: [unclosed")
    with pytest.raises(EvalConfigError, match="invalid YAML"):
        load_cases(evals, "s", load_vocabulary(evals, "s"))
