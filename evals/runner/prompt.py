"""Assemble the eval prompt: skill text as the system prompt, fixture files in the user message."""

from dataclasses import dataclass, field
from pathlib import Path

from evals.runner.loader import EvalConfigError

PREAMBLE = """\
You are running inside an automated evaluation of an agent skill. The skill below is loaded: follow it.

The user message contains files that stand in for the results of the tool calls the skill describes (MCP servers, the gh CLI, scripts). Treat them as real tool output. Do not try to call tools or ask for more input. Work with what is provided, and say in your report where something needed is missing.

End your answer with the structured findings block the skill specifies: one fenced json block holding an object with a "findings" list."""

# Assets may be images or other binary files; only these are text the model can read.
TEXT_ASSET_SUFFIXES = frozenset({".md", ".txt", ".yaml", ".yml", ".json"})


@dataclass(frozen=True)
class Skill:
    name: str
    skill_md: str
    references: dict[str, str]
    assets: dict[str, str] = field(default_factory=dict)


def load_skill(skills_dir: Path, name: str) -> Skill:
    """Read SKILL.md, every file under references/, and the text files under assets/. Scripts are not loaded."""
    root = skills_dir / name
    skill_md = root / "SKILL.md"
    if not skill_md.is_file():
        raise EvalConfigError(f"missing {skill_md}")
    return Skill(
        name=name,
        skill_md=skill_md.read_text(encoding="utf-8"),
        references=_read_folder(root, "references", None),
        assets=_read_folder(root, "assets", TEXT_ASSET_SUFFIXES),
    )


def _read_folder(root: Path, folder: str, suffixes: frozenset[str] | None) -> dict[str, str]:
    """Map skill-relative path to text for the files in a folder; `suffixes` limits which files are read."""
    directory = root / folder
    if not directory.is_dir():
        return {}
    paths = (p for p in directory.rglob("*") if p.is_file() and p.name != ".gitkeep")
    return {
        p.relative_to(root).as_posix(): p.read_text(encoding="utf-8")
        for p in sorted(paths)
        if suffixes is None or p.suffix in suffixes
    }


def build_system_prompt(skill: Skill) -> str:
    parts = [PREAMBLE, f'<skill name="{skill.name}">\n{skill.skill_md.rstrip()}\n</skill>']
    for path, text in skill.references.items():
        parts.append(f'<reference path="{path}">\n{text.rstrip()}\n</reference>')
    for path, text in skill.assets.items():
        parts.append(f'<asset path="{path}">\n{text.rstrip()}\n</asset>')
    return "\n\n".join(parts)


def build_user_message(fixture: dict[str, str], prompt: str) -> str:
    parts = [f'<file name="{name}">\n{text.rstrip()}\n</file>' for name, text in fixture.items()]
    parts.append(prompt)
    return "\n\n".join(parts)
