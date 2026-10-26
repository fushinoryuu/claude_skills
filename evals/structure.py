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
LENS_DIR = "references/lenses/"

# Words tied to one stack. A skill with lenses keeps them out of SKILL.md and its core references.
STACK_TERMS = (
    "endpoint", "controller", "terraform", "kubernetes", "docker", "react", "vue", "angular",
    "django", "rails", "openapi", "swagger", "graphql", "sql", "html", "css",
    "frontend", "front-end", "backend", "back-end",
)  # fmt: skip

_KEBAB = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
_STACK_TERM = re.compile(r"(?<![\w-])(" + "|".join(map(re.escape, STACK_TERMS)) + r")s?(?![\w-])", re.IGNORECASE)
_LENS_FILE = re.compile(r"lenses/([\w.-]+\.md)")
_CATEGORIES_SECTION = re.compile(r"^## Categories[ \t]*\r?\n(.*?)(?=^## |\Z)", re.DOTALL | re.MULTILINE)
_CATEGORY_ROW = re.compile(r"^\|\s*`([a-z0-9-]+)`\s*\|", re.MULTILINE)
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
                # Lenses are discovered by their applies_when block, not named in SKILL.md.
                if rel.startswith(LENS_DIR):
                    continue
                if rel not in refs:
                    problems.append(f"{folder}: {rel} exists but SKILL.md never mentions it")
    return problems


def check_lens_file(folder: str, path: Path) -> list[str]:
    """One lens: its frontmatter parses, its name is its file name, and applies_when has paths and touches."""
    label = f"{folder}: {LENS_DIR}{path.name}"
    try:
        meta = parse_frontmatter(path.read_text(encoding="utf-8"), label)
    except EvalConfigError as e:
        return [str(e)]

    problems = []
    if meta.get("name") != path.stem:
        problems.append(f"{label}: 'name' must equal the file name '{path.stem}'")
    if not isinstance(meta.get("description"), str) or not meta["description"].strip():
        problems.append(f"{label}: needs a non-empty 'description'")

    applies_when = meta.get("applies_when")
    if not isinstance(applies_when, dict):
        return [*problems, f"{label}: needs an 'applies_when' block with 'paths' and 'touches'"]
    paths = applies_when.get("paths")
    if not isinstance(paths, list) or not paths or not all(isinstance(p, str) and p.strip() for p in paths):
        problems.append(f"{label}: applies_when.paths must be a non-empty list of file globs")
    touches = applies_when.get("touches")
    if not isinstance(touches, str) or not touches.strip():
        problems.append(f"{label}: applies_when.touches must be one plain-language line")
    return problems


def check_lenses(folder: str, root: Path, text: str) -> list[str]:
    """For a skill that has lenses: each lens is valid, and the core text stays neutral about any one stack.

    The core text is SKILL.md and every reference outside the lens folder. It must not link a specific
    lens (removing the lens folder must not break it) or use stack-specific words.
    """
    lens_dir = root / LENS_DIR
    if not lens_dir.is_dir():
        return []

    problems = []
    for path in sorted(lens_dir.glob("*.md")):
        if path.name != "README.md":
            problems += check_lens_file(folder, path)

    core = {"SKILL.md": text}
    for path in sorted((root / "references").rglob("*.md")):
        rel = path.relative_to(root).as_posix()
        if not rel.startswith(LENS_DIR):
            core[rel] = path.read_text(encoding="utf-8")
    for rel, body in core.items():
        for lens in sorted(set(_LENS_FILE.findall(body)) - {"README.md"}):
            problems.append(f"{folder}: {rel} names the lens file '{lens}'; lenses are chosen by their applies_when block")
        for term in sorted({m.group(1).lower() for m in _STACK_TERM.finditer(body)}):
            problems.append(f"{folder}: {rel} uses the stack-specific word '{term}'; move it into a lens")
    return problems


def check_output_format(folder: str, root: Path, evals_dir: Path) -> list[str]:
    """The Categories table in references/output-format.md must list the same slugs as categories.yaml."""
    path = root / "references" / "output-format.md"
    if not path.is_file():
        return []
    try:
        vocab = load_vocabulary(evals_dir, folder)
    except EvalConfigError:
        return []  # check_evals reports an unreadable vocabulary

    label = f"{folder}: references/output-format.md"
    section = _CATEGORIES_SECTION.search(path.read_text(encoding="utf-8"))
    if not section:
        return [f"{label} needs a '## Categories' section with one table row per slug"]
    documented = set(_CATEGORY_ROW.findall(section.group(1)))
    return [
        *(f"{label}: categories.yaml has '{slug}', which the Categories table does not" for slug in sorted(vocab.values - documented)),
        *(f"{label}: the Categories table has '{slug}', which categories.yaml does not" for slug in sorted(documented - vocab.values)),
    ]  # fmt: skip


def is_manual_only(text: str) -> bool:
    """True when SKILL.md sets disable-model-invocation: the description never selects the skill, so trigger tests would test nothing."""
    try:
        return parse_frontmatter(text).get("disable-model-invocation") is True
    except EvalConfigError:
        return False


def check_evals(folder: str, evals_dir: Path, *, manual_only: bool = False) -> list[str]:
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
        if case.expect.lenses is not None and "lenses" not in case.tags:
            problems.append(f"{folder}: case {case.id} sets expect.lenses but is not tagged 'lenses'")

    if cases and not any(
        "clean" in c.tags and not c.expect.findings and c.expect.max_findings <= MAX_CLEAN_FINDINGS
        for c in cases
    ):
        problems.append(
            f"{folder}: needs a clean case (tag 'clean', findings: [], max_findings <= {MAX_CLEAN_FINDINGS})"
        )

    if manual_only:
        return problems

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
        + check_lenses(folder, root, text)
        + check_output_format(folder, root, evals_dir)
        + check_evals(folder, evals_dir, manual_only=is_manual_only(text))
    )
