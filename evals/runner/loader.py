"""Load eval definitions (vocabulary, cases, fixtures) from disk.

The on-disk format is specified in docs/eval-format.md.
"""

from dataclasses import dataclass
from pathlib import Path

import yaml

SUPPORTED_SCORERS = {"findings"}


class EvalConfigError(Exception):
    """An eval definition is missing or does not follow docs/eval-format.md."""


@dataclass(frozen=True)
class Vocabulary:
    key_field: str
    values: frozenset[str]


@dataclass(frozen=True)
class Expect:
    findings: tuple[dict, ...]
    must_not_flag: frozenset[str]
    max_findings: int


@dataclass(frozen=True)
class Case:
    id: str
    skill: str
    fixture: str
    prompt: str
    expect: Expect
    tags: tuple[str, ...]


def _read_yaml(path: Path) -> dict:
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except OSError as e:
        raise EvalConfigError(f"cannot read {path}: {e}") from e
    except yaml.YAMLError as e:
        raise EvalConfigError(f"{path}: invalid YAML: {e}") from e
    if not isinstance(data, dict):
        raise EvalConfigError(f"{path}: expected a mapping at the top level")
    return data


def load_vocabulary(evals_dir: Path, skill: str) -> Vocabulary:
    path = evals_dir / skill / "categories.yaml"
    if not path.is_file():
        raise EvalConfigError(f"missing {path}")
    data = _read_yaml(path)
    key_field = data.get("key_field")
    values = data.get("values")
    if not isinstance(key_field, str) or not key_field:
        raise EvalConfigError(f"{path}: 'key_field' must be a non-empty string")
    if not isinstance(values, list) or not values or not all(isinstance(v, str) for v in values):
        raise EvalConfigError(f"{path}: 'values' must be a non-empty list of strings")
    return Vocabulary(key_field=key_field, values=frozenset(values))


def _parse_case(path: Path, skill: str, vocab: Vocabulary) -> Case:
    data = _read_yaml(path)

    def fail(msg: str) -> EvalConfigError:
        return EvalConfigError(f"{path.name}: {msg}")

    for key in ("id", "skill", "fixture", "prompt", "expect"):
        if key not in data:
            raise fail(f"missing required field '{key}'")
    if data["id"] != path.stem:
        raise fail(f"id '{data['id']}' must equal the file name '{path.stem}'")
    if data["skill"] != skill:
        raise fail(f"skill '{data['skill']}' does not match folder '{skill}'")
    if data.get("scorer", "findings") not in SUPPORTED_SCORERS:
        raise fail(f"unsupported scorer '{data['scorer']}'")

    expect = data["expect"]
    if not isinstance(expect, dict):
        raise fail("'expect' must be a mapping")
    findings = expect.get("findings")
    if not isinstance(findings, list):
        raise fail("'expect.findings' must be a list (use [] for a clean case)")
    for item in findings:
        if not isinstance(item, dict) or vocab.key_field not in item:
            raise fail(f"each expected finding needs the key field '{vocab.key_field}'")
        if item[vocab.key_field] not in vocab.values:
            raise fail(f"'{item[vocab.key_field]}' is not in categories.yaml")
    must_not_flag = expect.get("must_not_flag") or []
    for slug in must_not_flag:
        if slug not in vocab.values:
            raise fail(f"must_not_flag '{slug}' is not in categories.yaml")
    max_findings = expect.get("max_findings")
    if not isinstance(max_findings, int) or isinstance(max_findings, bool) or max_findings < 0:
        raise fail("'expect.max_findings' must be an integer >= 0")

    return Case(
        id=data["id"],
        skill=skill,
        fixture=str(data["fixture"]),
        prompt=str(data["prompt"]),
        expect=Expect(
            findings=tuple(findings),
            must_not_flag=frozenset(must_not_flag),
            max_findings=max_findings,
        ),
        tags=tuple(data.get("tags") or ()),
    )


def load_cases(evals_dir: Path, skill: str, vocab: Vocabulary, case_id: str | None = None) -> list[Case]:
    cases_dir = evals_dir / skill / "cases"
    if case_id is not None:
        path = cases_dir / f"{case_id}.yaml"
        if not path.is_file():
            available = ", ".join(sorted(p.stem for p in cases_dir.glob("*.yaml"))) or "none"
            raise EvalConfigError(f"no case '{case_id}' for skill '{skill}' (available: {available})")
        return [_parse_case(path, skill, vocab)]
    cases = [_parse_case(p, skill, vocab) for p in sorted(cases_dir.glob("*.yaml"))]
    if not cases:
        raise EvalConfigError(f"no cases found in {cases_dir}")
    return cases


def load_fixture(evals_dir: Path, skill: str, name: str) -> dict[str, str]:
    """Return {relative posix path: text} for every file in the fixture, in sorted order."""
    root = evals_dir / skill / "fixtures" / name
    if not root.is_dir():
        raise EvalConfigError(f"missing fixture folder {root}")
    files = {}
    for path in sorted(p for p in root.rglob("*") if p.is_file() and p.name != ".gitkeep"):
        try:
            files[path.relative_to(root).as_posix()] = path.read_text(encoding="utf-8")
        except UnicodeDecodeError as e:
            raise EvalConfigError(f"{path}: fixtures must be UTF-8 text") from e
    if not files:
        raise EvalConfigError(f"fixture {root} has no files")
    return files
