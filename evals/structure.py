"""Deterministic structure checks for skills and their eval kits.

Each check returns human-readable problems instead of raising, so a test can
report everything wrong with a skill at once. Run by tests/structure/.
"""

import posixpath
import re
from pathlib import Path

from evals.runner.loader import (
    EvalConfigError,
    load_cases,
    load_fixture,
    load_vocabulary,
)
from evals.runner.skills import parse_frontmatter
from evals.runner.triggers import load_triggers

MAX_SKILL_LINES = 500
MAX_NAME_LENGTH = 64
MIN_DESCRIPTION_LENGTH = 30
MAX_DESCRIPTION_LENGTH = 1024
MAX_CLEAN_FINDINGS = 2

_KEBAB = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
_LINK = re.compile(r"\[[^\]]*\]\(([^)\s]+)\)")
_URL_OR_SCHEME = re.compile(r"^[a-z][a-z0-9+.-]*:", re.IGNORECASE)
# Skill-relative paths such as references/x.md. Not matched when part of a longer path.
_PATH = re.compile(r"(?<![\w./-])((?:references|scripts|assets)/[\w./-]*\w)")


def find_skill_folders(skills_dir: Path) -> list[str]:
    """Every non-hidden folder under skills/, so a folder without SKILL.md is reported."""
    if not skills_dir.is_dir():
        return []
    return sorted(p.name for p in skills_dir.iterdir() if p.is_dir() and not p.name.startswith("."))


def referenced_paths(text: str) -> set[str]:
    """Paths SKILL.md points at: relative markdown links, and references/, scripts/, assets/ paths."""
    refs = set()
    for target in _LINK.findall(text):
        target = target.split("#")[0]
        if target and not _URL_OR_SCHEME.match(target):
            refs.add(posixpath.normpath(target))
    refs.update(_PATH.findall(text))
    return refs


def check_frontmatter(folder: str, text: str) -> list[str]:
    try:
        meta = parse_frontmatter(text, f"{folder}/SKILL.md")
    except EvalConfigError as e:
        return [str(e)]

    problems = []
    name = meta.get("name")
    if not isinstance(name, str) or not name:
        problems.append(f"{folder}: frontmatter 'name' is missing")
    else:
        if name != folder:
            problems.append(f"{folder}: name '{name}' must match the folder name")
        if not _KEBAB.match(name) or len(name) > MAX_NAME_LENGTH:
            problems.append(
                f"{folder}: name '{name}' must be lowercase kebab-case, at most {MAX_NAME_LENGTH} characters"
            )

    description = meta.get("description")
    if not isinstance(description, str) or not description.strip():
        problems.append(f"{folder}: frontmatter 'description' is missing")
    else:
        length = len(" ".join(description.split()))
        if length < MIN_DESCRIPTION_LENGTH:
            problems.append(
                f"{folder}: description is {length} characters; say what the skill does and when to use it "
                f"(at least {MIN_DESCRIPTION_LENGTH})"
            )
        if length > MAX_DESCRIPTION_LENGTH:
            problems.append(f"{folder}: description is {length} characters (maximum {MAX_DESCRIPTION_LENGTH})")
    return problems


def check_size(folder: str, text: str) -> list[str]:
    lines = len(text.splitlines())
    if lines > MAX_SKILL_LINES:
        return [f"{folder}: SKILL.md is {lines} lines (budget {MAX_SKILL_LINES}); move detail into references/"]
    return []


def check_references(folder: str, root: Path, text: str) -> list[str]:
    problems = []
    refs = referenced_paths(text)
    resolved_root = root.resolve()

    for ref in sorted(refs):
        target = (root / ref).resolve()
        if not target.is_relative_to(resolved_root):
            problems.append(f"{folder}: SKILL.md references '{ref}', which is outside the skill folder")
        elif not target.exists():
            problems.append(f"{folder}: SKILL.md references '{ref}', which does not exist")

    ref_dir = root / "references"
    if ref_dir.is_dir():
        for path in sorted(ref_dir.rglob("*")):
            if path.is_file() and path.name != ".gitkeep":
                rel = path.relative_to(root).as_posix()
                if rel not in refs:
                    problems.append(f"{folder}: {rel} exists but SKILL.md never mentions it")
    return problems


def check_evals(folder: str, evals_dir: Path) -> list[str]:
    problems = []
    try:
        vocab = load_vocabulary(evals_dir, folder)
        cases = load_cases(evals_dir, folder, vocab)
    except EvalConfigError as e:
        problems.append(f"{folder}: {e}")
        cases = []

    for case in cases:
        try:
            load_fixture(evals_dir, folder, case.fixture)
        except EvalConfigError as e:
            problems.append(f"{folder}: case {case.id}: {e}")
        if "clean" in case.tags and case.expect.findings:
            problems.append(f"{folder}: case {case.id} is tagged 'clean' but expects findings")

    if cases and not any(
        "clean" in c.tags and not c.expect.findings and c.expect.max_findings <= MAX_CLEAN_FINDINGS
        for c in cases
    ):
        problems.append(
            f"{folder}: needs a clean case (tag 'clean', findings: [], max_findings <= {MAX_CLEAN_FINDINGS})"
        )

    try:
        prompts = load_triggers(evals_dir, folder)
    except EvalConfigError as e:
        problems.append(f"{folder}: {e}")
    else:
        if not any(p.should_trigger for p in prompts):
            problems.append(f"{folder}: triggers.yaml has no should_trigger prompts")
        if not any(not p.should_trigger for p in prompts):
            problems.append(f"{folder}: triggers.yaml has no should_not_trigger prompts")
    return problems


def check_skill(skills_dir: Path, evals_dir: Path, folder: str) -> list[str]:
    """All structure problems for one skill folder. Empty means it passes."""
    root = skills_dir / folder
    skill_md = root / "SKILL.md"
    if not skill_md.is_file():
        return [f"{folder}: missing SKILL.md"]
    text = skill_md.read_text(encoding="utf-8")
    return (
        check_frontmatter(folder, text)
        + check_size(folder, text)
        + check_references(folder, root, text)
        + check_evals(folder, evals_dir)
    )
