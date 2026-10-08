"""Read skill metadata (the SKILL.md frontmatter) for every skill in a skills folder."""

from dataclasses import dataclass
from pathlib import Path

import yaml

from evals.runner.loader import EvalConfigError


@dataclass(frozen=True)
class SkillInfo:
    folder: str
    name: str
    description: str


def parse_frontmatter(text: str, source: str = "SKILL.md") -> dict:
    """Return the YAML frontmatter of a SKILL.md as a dict."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        raise EvalConfigError(f"{source}: missing frontmatter (file must start with '---')")
    try:
        end = next(i for i, line in enumerate(lines[1:], start=1) if line.strip() == "---")
    except StopIteration:
        raise EvalConfigError(f"{source}: frontmatter is not closed with '---'") from None
    try:
        data = yaml.safe_load("\n".join(lines[1:end]))
    except yaml.YAMLError as e:
        raise EvalConfigError(f"{source}: invalid frontmatter YAML: {e}") from e
    if not isinstance(data, dict):
        raise EvalConfigError(f"{source}: frontmatter must be a mapping")
    return data


def load_catalog(skills_dir: Path) -> list[SkillInfo]:
    """Name and description of every folder under skills_dir that has a SKILL.md."""
    catalog = []
    for skill_md in sorted(skills_dir.glob("*/SKILL.md")):
        meta = parse_frontmatter(skill_md.read_text(encoding="utf-8"), str(skill_md))
        name, description = meta.get("name"), meta.get("description")
        if not isinstance(name, str) or not isinstance(description, str):
            raise EvalConfigError(f"{skill_md}: frontmatter needs string 'name' and 'description'")
        catalog.append(SkillInfo(skill_md.parent.name, name, " ".join(description.split())))
    if not catalog:
        raise EvalConfigError(f"no skills found in {skills_dir}")
    return catalog
